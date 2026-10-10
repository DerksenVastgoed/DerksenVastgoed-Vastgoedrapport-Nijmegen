#!/usr/bin/env python3
"""
Telt per ringbuurt hoeveel adressen er zijn en levert de postcodes als
werkvoorraad.

Bron: de PDOK-locatieserver, dezelfde dienst die marktprijzen_bag.py al
gebruikt om de buurt van een adres op te zoeken. Open data, geen sleutel, en
hij kan filteren op buurtnaam.

WAAROM DIT BESTAAT. De gegevens over oppervlakte en energielabel komen nu
binnen op het moment dat een pand te koop staat. Daardoor kennen we de voorraad
alleen voor zover die in de verkoop is geweest: 1.260 panden met 6.338
adressen. Een vraag als "welke panden in Bottendaal zijn groter dan 150 m2 met
label E of slechter" is daarmee niet te stellen, en dat is precies de vraag die
een acquisitielijst oplevert in plaats van een reactie op het aanbod.

WAT DE EERSTE METING OPLEVERDE, op 9 oktober 2026, en waarom dit script er nu
anders uitziet dan toen:

  1. De locatieserver levert GEEN pand-id. Het veld pandid werd gevraagd en
     kwam bij geen enkel adres terug. De eerste opzet haalde alle adressen op
     om daaruit de panden te verzamelen, en kwam dus op nul panden uit. Dat het
     script opschreef welke gevraagde velden ontbraken, is wat dat aan het
     licht bracht in plaats van een stille nul.
  2. De paginering loopt vast bij tienduizend. Stadscentrum meldde 11.975
     adressen en leverde er 10.100; dat is de grens die Solr aan diep
     doorbladeren stelt. De meting was daar dus onvolledig.
  3. Een adres is niet een woning. De zes buurten leverden samen 34.946
     adressen, terwijl het CBS er 19.061 woningen telt. In type:adres zitten
     ook winkels, kantoren, garageboxen en bergingen. Benedenstad is het
     uiterste: 5.098 adressen tegen 1.639 woningen.

Daarom haalt dit script nu twee dingen op, en geen adressen meer. Het aantal
adressen per buurt komt uit het veld numFound van een vraag met rows=0: één
verzoek, geen paginering, dus ook geen grens van tienduizend. En de postcodes
komen uit type:postcode, een paar honderd per buurt, ruim onder die grens en
dus compleet.

Die postcodes zijn de werkvoorraad voor de volgende stap. Een BAG-vraag met
postcode levert alle adressen in die postcode mét pandIdentificatie,
oppervlakte en gebruiksdoel in één keer. Dat is ongeveer 1.750 vragen voor de
hele ring, in plaats van een vraag per adres, en het levert meteen het
onderscheid tussen een woning en een garagebox.

Gebruik:
  python buurtinventaris.py                 # alle zes buurten
  python buurtinventaris.py --buurt Biezen  # een enkele buurt, om te proeven
  python buurtinventaris.py --uit elders.json
"""

import argparse
import datetime as dt
import json
import sys
import time

import requests

PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
PDOK_HEADERS = {"User-Agent": "NijmegenVastgoedMonitor/1.0"}
UIT = "buurtinventaris.json"
GESCHIEDENIS = "pandgeschiedenis.json"

# Honderd per vraag is wat de locatieserver aan een gewone zoekopdracht geeft.
PER_VRAAG = 100

# Noodrem tegen een eindeloze lus. Een Nijmeegse buurt heeft een paar honderd
# postcodes; vijfduizend is ruim en blijft onder de grens die Solr aan diep
# doorbladeren stelt.
MAX_PER_BUURT = 5000


def buurten_lijst():
    """
    De zes ringbuurten, uit marktprijzen_bag.py.

    Eén plek waar die namen staan. Twee lijsten gaan uit elkaar lopen, en dan
    meet dit script een andere ring dan de brief beschrijft.
    """
    try:
        from marktprijzen_bag import FOCUS_BUURTEN
        return list(FOCUS_BUURTEN)
    except Exception as e:
        print(f"Kon FOCUS_BUURTEN niet importeren ({e}); eigen lijst gebruikt",
              file=sys.stderr)
        return ["Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
                "Altrade", "Biezen"]


def _vraag(params):
    """Eén verzoek aan de locatieserver, of None bij een fout."""
    try:
        r = requests.get(PDOK, params=params, headers=PDOK_HEADERS, timeout=30)
        r.raise_for_status()
        return r.json().get("response", {})
    except Exception as e:
        print(f"  locatieserver: {e}", file=sys.stderr)
        return None


def aantal_adressen(buurt):
    """
    Hoeveel adresseerbare objecten deze buurt heeft, uit numFound.

    Met rows=0 vraagt dit alleen de telling op en geen records. Eén verzoek,
    dus geen paginering en geen grens van tienduizend. Let op wat het telt:
    adressen, niet woningen. Winkels, kantoren, garageboxen en bergingen
    hebben ook een adres.
    """
    antwoord = _vraag({"q": "*", "fq": ["type:adres", f'buurtnaam:"{buurt}"'],
                       "rows": 0, "wt": "json"})
    return None if antwoord is None else antwoord.get("numFound")


def postcodes_van(buurt, pauze=0.2):
    """
    De postcodes van een buurt, met paginering.

    Geeft (postcodes, gemeld) terug. Het gemelde aantal is wat de server zegt
    te hebben; dat vergelijken we met wat we ophaalden, want een stil afgekapte
    pagina is anders niet te zien.
    """
    gevonden, gemeld, start = set(), None, 0
    while start < MAX_PER_BUURT:
        antwoord = _vraag({
            "q": "*",
            "fq": ["type:postcode", f'buurtnaam:"{buurt}"'],
            "rows": PER_VRAAG, "start": start,
            "fl": "postcode buurtnaam wijknaam", "wt": "json",
        })
        if antwoord is None:
            break
        if gemeld is None:
            gemeld = antwoord.get("numFound")
        docs = antwoord.get("docs") or []
        for d in docs:
            pc = (d.get("postcode") or "").replace(" ", "").upper()
            if pc:
                gevonden.add(pc)
        if len(docs) < PER_VRAAG:
            break
        start += PER_VRAAG
        time.sleep(pauze)
    return sorted(gevonden), gemeld


def bekend_uit_geschiedenis():
    """Wat we al hebben nagekeken, uit pandgeschiedenis.json."""
    try:
        with open(GESCHIEDENIS, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return 0, 0
    panden = d.get("_panden") or {}
    adressen = sum(len(v.get("bag_eenheden") or []) for v in panden.values()
                   if isinstance(v, dict))
    return len(panden), adressen


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uit", default=UIT)
    p.add_argument("--buurt", action="append",
                   help="Alleen deze buurt; meerdere keren te geven")
    p.add_argument("--pauze", type=float, default=0.2,
                   help="Seconden tussen twee pagina's")
    args = p.parse_args()

    buurten = args.buurt or buurten_lijst()
    panden_bekend, adressen_bekend = bekend_uit_geschiedenis()
    print(f"Al nagekeken: {panden_bekend} panden met {adressen_bekend} "
          f"adressen", file=sys.stderr)

    per_buurt, postcodes_per_buurt, alle_postcodes = {}, {}, set()
    for naam in buurten:
        adressen = aantal_adressen(naam)
        postcodes, gemeld = postcodes_van(naam, args.pauze)
        alle_postcodes |= set(postcodes)
        postcodes_per_buurt[naam] = postcodes
        per_buurt[naam] = {
            "adressen": adressen,
            "postcodes": len(postcodes),
            "postcodes_gemeld": gemeld,
            "volledig": (gemeld is not None and len(postcodes) >= gemeld),
        }
        print(f"{naam}: {adressen} adressen, {len(postcodes)} postcodes"
              + (f" van {gemeld} gemeld" if gemeld is not None else "")
              + ("" if per_buurt[naam]["volledig"] else "  LET OP: onvolledig"),
              file=sys.stderr)

    totaal_adressen = sum(g["adressen"] or 0 for g in per_buurt.values())
    uit = {
        "opgehaald": dt.date.today().isoformat(),
        "bron": "PDOK locatieserver v3_1, filter op buurtnaam",
        "let_op": ("adressen is het aantal adresseerbare objecten en niet het "
                   "aantal woningen: winkels, kantoren en garageboxen hebben "
                   "ook een adres. Het onderscheid komt uit het gebruiksdoel "
                   "in de BAG, en dat zit niet in deze dienst."),
        "per_buurt": per_buurt,
        "totaal": {
            "adressen": totaal_adressen,
            "postcodes": len(alle_postcodes),
            "buurten_volledig": sum(1 for g in per_buurt.values()
                                    if g["volledig"]),
            "buurten_gevraagd": len(per_buurt),
            "panden_al_nagekeken": panden_bekend,
            "adressen_al_nagekeken": adressen_bekend,
        },
        "postcodes_per_buurt": postcodes_per_buurt,
    }

    if not len(alle_postcodes):
        print("Geen enkele postcode opgehaald; bestand niet overschreven.",
              file=sys.stderr)
        return 1

    try:
        with open(args.uit, "w", encoding="utf-8") as f:
            json.dump(uit, f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Kon {args.uit} niet schrijven: {e}", file=sys.stderr)
        return 1

    t = uit["totaal"]
    print(f"\n{t['adressen']} adressen en {t['postcodes']} postcodes in "
          f"{t['buurten_gevraagd']} buurten, waarvan "
          f"{t['buurten_volledig']} volledig opgehaald. Al nagekeken: "
          f"{t['adressen_al_nagekeken']} adressen in "
          f"{t['panden_al_nagekeken']} panden.", file=sys.stderr)
    print(f"Weggeschreven naar {args.uit}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
