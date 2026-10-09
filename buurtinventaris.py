#!/usr/bin/env python3
"""
Telt op welke adressen en panden er in de zes ringbuurten staan.

Bron: de PDOK-locatieserver, dezelfde dienst die marktprijzen_bag.py al
gebruikt om de buurt van een adres op te zoeken. Open data, geen sleutel, en
hij kan filteren op buurtnaam. Daarmee weten we welke panden er in een buurt
staan zonder te wachten tot er een op Funda komt.

WAAROM DIT BESTAAT. De gegevens over oppervlakte en energielabel komen nu
binnen op het moment dat een pand te koop staat. Daardoor kennen we de voorraad
alleen voor zover die in de verkoop is geweest: 1.260 panden met 6.338
adressen, terwijl het CBS 19.061 woningen in de zes buurten telt. Een vraag als
"welke panden in Bottendaal zijn groter dan 150 m2 met label E of slechter" is
daarmee niet te stellen, en dat is precies de vraag die een acquisitielijst
oplevert in plaats van een reactie op het aanbod.

DIT SCRIPT MEET ALLEEN. Het haalt per buurt de adressen op met hun pand-id en
legt vast hoeveel er zijn en hoeveel we er al kennen uit pandgeschiedenis.json.
Het haalt zelf geen oppervlakten en geen labels op: dat is de volgende stap en
die kost per pand een BAG-aanroep en per adres een EP-Online-aanroep. Eerst
willen we weten hoe groot die stap werkelijk is, met gemeten aantallen in plaats
van een deling.

De lijst met pand-ids per buurt is de werkvoorraad voor die volgende stap en
staat daarom in de uitvoer. De adressen zelf niet: die zijn gratis opnieuw op te
halen en zouden het bestand ruim een megabyte groter maken.

Gebruik:
  python buurtinventaris.py                 # alle zes buurten
  python buurtinventaris.py --buurt Biezen  # een enkele buurt, om te proeven
  python buurtinventaris.py --uit elders.json
"""

import argparse
import datetime as dt
import json
import os
import sys
import time

import requests

PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
PDOK_HEADERS = {"User-Agent": "NijmegenVastgoedMonitor/1.0"}
UIT = "buurtinventaris.json"
GESCHIEDENIS = "pandgeschiedenis.json"

# Honderd per vraag is wat de locatieserver aan een gewone zoekopdracht geeft.
# Hoger gevraagd wordt stil afgekapt, en dan mis je adressen zonder dat je het
# ziet. Daarom tellen we achteraf of we er evenveel hebben als de server zegt.
PER_VRAAG = 100

# Een buurt heeft in Nijmegen maximaal ruim vijfduizend woningen. Deze grens
# is een noodrem tegen een eindeloze lus bij een onverwachte respons, niet een
# verwachting.
MAX_PER_BUURT = 12000

# De velden die we willen. Komt een veld niet terug, dan staat dat in de
# uitvoer onder "velden_gemist", zodat de eerste run vertelt wat de dienst
# werkelijk levert in plaats van dat ik het hier gok.
VELDEN = ("id", "type", "weergavenaam", "straatnaam", "huis_nlt", "postcode",
          "buurtnaam", "wijknaam", "adresseerbaarobject_id",
          "nummeraanduiding_id", "pandid")


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


def _pandids(doc):
    """
    De pand-ids uit een adresrecord.

    De locatieserver geeft dit veld soms als lijst en soms als losse waarde,
    en een adres kan in meer dan één pand liggen, bijvoorbeeld bij een
    doorgebroken woning. Allebei de vormen leveren hier een lijst op.
    """
    ruw = doc.get("pandid")
    if ruw is None:
        return []
    if isinstance(ruw, (list, tuple)):
        return [str(x) for x in ruw if x]
    return [str(ruw)]


def haal_buurt(naam, pauze=0.2):
    """
    Alle adressen van één buurt, met paginering.

    Geeft (adressen, gemeld_totaal, velden_gezien) terug. Het gemelde totaal is
    wat de server zegt te hebben; dat vergelijken we met wat we binnenhaalden,
    want een stil afgekapte pagina is anders niet te zien.
    """
    adressen, gemeld, velden_gezien = [], None, set()
    start = 0
    while start < MAX_PER_BUURT:
        params = {
            "q": "*",
            "fq": ["type:adres", f'buurtnaam:"{naam}"'],
            "rows": PER_VRAAG,
            "start": start,
            "fl": " ".join(VELDEN),
            "wt": "json",
        }
        try:
            r = requests.get(PDOK, params=params, headers=PDOK_HEADERS,
                             timeout=30)
            r.raise_for_status()
            antwoord = r.json().get("response", {})
        except Exception as e:
            print(f"  {naam}: fout bij start={start}: {e}", file=sys.stderr)
            break
        docs = antwoord.get("docs") or []
        if gemeld is None:
            gemeld = antwoord.get("numFound")
        for d in docs:
            velden_gezien.update(d.keys())
            adressen.append(d)
        if len(docs) < PER_VRAAG:
            break
        start += PER_VRAAG
        time.sleep(pauze)
    return adressen, gemeld, velden_gezien


def bekende_panden():
    """De pand-ids die we al hebben nagekeken, uit pandgeschiedenis.json."""
    try:
        with open(GESCHIEDENIS, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return set(), 0
    panden = d.get("_panden") or {}
    adressen = sum(len(v.get("bag_eenheden") or []) for v in panden.values()
                   if isinstance(v, dict))
    return set(panden), adressen


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uit", default=UIT)
    p.add_argument("--buurt", action="append",
                   help="Alleen deze buurt; meerdere keren te geven")
    p.add_argument("--pauze", type=float, default=0.2,
                   help="Seconden tussen twee pagina's")
    args = p.parse_args()

    buurten = args.buurt or buurten_lijst()
    al_bekend, al_adressen = bekende_panden()
    print(f"Al nagekeken: {len(al_bekend)} panden met {al_adressen} adressen",
          file=sys.stderr)

    per_buurt, panden_per_buurt = {}, {}
    velden_gezien, alle_panden = set(), set()
    for naam in buurten:
        adressen, gemeld, velden = haal_buurt(naam, args.pauze)
        velden_gezien |= velden
        panden = set()
        for d in adressen:
            panden.update(_pandids(d))
        alle_panden |= panden
        postcodes = {d.get("postcode") for d in adressen if d.get("postcode")}
        bekend = len(panden & al_bekend)
        per_buurt[naam] = {
            "adressen": len(adressen),
            "adressen_gemeld": gemeld,
            "volledig": (gemeld is not None and len(adressen) >= gemeld),
            "panden": len(panden),
            "panden_al_nagekeken": bekend,
            "panden_nog_te_doen": len(panden) - bekend,
            "postcodes": len(postcodes),
            "zonder_pandid": sum(1 for d in adressen if not _pandids(d)),
        }
        panden_per_buurt[naam] = sorted(panden)
        g = per_buurt[naam]
        print(f"{naam}: {g['adressen']} adressen"
              + (f" van {gemeld} gemeld" if gemeld is not None else "")
              + f", {g['panden']} panden, {bekend} al nagekeken,"
              f" {g['postcodes']} postcodes", file=sys.stderr)

    nagekeken = len(alle_panden & al_bekend)
    uit = {
        "opgehaald": dt.date.today().isoformat(),
        "bron": "PDOK locatieserver v3_1, filter op buurtnaam",
        "per_buurt": per_buurt,
        "totaal": {
            "adressen": sum(g["adressen"] for g in per_buurt.values()),
            "panden": len(alle_panden),
            "panden_al_nagekeken": nagekeken,
            "panden_nog_te_doen": len(alle_panden) - nagekeken,
            "buurten_volledig": sum(1 for g in per_buurt.values()
                                    if g["volledig"]),
            "buurten_gevraagd": len(per_buurt),
        },
        "velden_gevraagd": list(VELDEN),
        "velden_gemist": sorted(set(VELDEN) - velden_gezien),
        "panden_per_buurt": panden_per_buurt,
    }

    if not uit["totaal"]["adressen"]:
        print("Geen enkel adres opgehaald; bestand niet overschreven.",
              file=sys.stderr)
        return 1

    try:
        with open(args.uit, "w", encoding="utf-8") as f:
            json.dump(uit, f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Kon {args.uit} niet schrijven: {e}", file=sys.stderr)
        return 1

    t = uit["totaal"]
    print(f"\n{t['adressen']} adressen en {t['panden']} panden in "
          f"{t['buurten_gevraagd']} buurten. Al nagekeken: "
          f"{t['panden_al_nagekeken']} panden, nog te doen: "
          f"{t['panden_nog_te_doen']}.", file=sys.stderr)
    if uit["velden_gemist"]:
        print("Velden die de dienst niet leverde: "
              + ", ".join(uit["velden_gemist"]), file=sys.stderr)
    print(f"Weggeschreven naar {args.uit}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
