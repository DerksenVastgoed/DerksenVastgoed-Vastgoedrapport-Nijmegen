#!/usr/bin/env python3
"""
Wanneer stond een pand te koop, en wanneer is het verkocht?

Het probleem: alle 505 geplakte verkopen dragen de datum waarop ze zijn
geplakt, 28 september. Dat is niet onzeker maar aantoonbaar onjuist. En bij een
deel van het aanbod kennen we de plaatsingsdatum niet, waardoor "dagen te koop"
leeg blijft; juist dat getal zegt of een pand blijft hangen.

Dit haalt een INDICATIE op met het taalmodel, dat daarbij zelf het web
doorzoekt. Vier waarborgen, want een model dat iets niet kan vinden geeft
zelden "ik weet het niet" terug maar een plausibel getal:

1. Zonder bronvermelding wordt het antwoord weggegooid. Geen bron, geen datum.
2. De bron komt mee in het bestand, zodat elk getal naar zijn herkomst wijst.
3. Datums mogen meerekenen, bedragen niet. Een datum die er een week naast zit
   verandert niets aan een doorlooptijd van drie maanden; een verkoopprijs die
   5% afwijkt verschuift de groottepremie en daarmee elke ontwikkelcase.
4. Dit overschrijft nooit een Kadastercijfer of iets wat Mark zelf heeft
   ingevoerd. Komt er later een echte levering, dan vervangt die deze regels.

LET OP: deze stap staat uit in de workflow. Per pand een vraag met webzoeken
kostte ongeveer twintig euro per run, en dat staat in geen verhouding tot wat
het aan de brief toevoegt. Het script blijft bruikbaar voor een handmatige
ronde; de gegevens worden voorlopig vanuit de chat aangevuld, waar het zoeken
niets kost. De verkoopgeschiedenis van een pand verandert vrijwel nooit, dus
het is een eenmalige inhaalslag en geen dagelijkse taak.

Gebruik:
  python verkoopdatum_model.py --steekproef 20  twintig panden, niets bewaren
  python verkoopdatum_model.py --proef          meet de eigen logica na
  python verkoopdatum_model.py --per-ronde 50 vijftig panden, wel bewaren
  python verkoopdatum_model.py --controle     toetsen aan wat we al weten
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request


import pandsleutel as _psl
UIT_PAD = "verkoopdatums_model.json"
AANBOD_PAD = "verkopen.txt"
API = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_PER_RONDE = 50

VRAAG = """Zoek op funda.nl of een andere openbare bron wanneer de woning op dit \
adres MEEST RECENT te koop is aangeboden en wanneer die is verkocht:

{adres}, Nijmegen
{hint}

Let op: van veel adressen staan ook oude advertenties online, soms van tien \
jaar geleden. Wij willen de meest recente plaatsing. Vind je alleen een oude \
advertentie, zet dan zeker op laag en vermeld het jaartal in de bron.

Geef ALLE plaatsingen en verkopen die je vindt, niet alleen de laatste. Een
woning kan in tien jaar meerdere keren zijn verkocht, en elke keer telt.

Antwoord met ALLEEN een JSON-object, zonder tekst eromheen:
{{"gebeurtenissen": [
   {{"soort": "te koop of verkocht",
     "datum": "JJJJ-MM-DD",
     "vraagprijs": getal of null,
     "bron": "de url of de naam van de pagina waar je dit vond",
     "zeker": "hoog, midden of laag"}}
 ]}}

Regels die je strikt volgt:
- Vind je niets, geef dan een lege lijst. Verzin niets.
- Elke gebeurtenis krijgt zijn eigen bron. Zonder bron laat je hem weg.
- Alleen bronnen met een verkoopgeschiedenis: funda, een makelaarssite of een \
woningplatform. Geen video's, sociale media of marktplaatsen.
- Leid een datum nooit af uit "128 days ago" of iets dergelijks; dan is het \
geen gevonden datum maar een berekening.
- Een datum die je afleidt uit "3 maanden te koop" zonder dat de datum er \
letterlijk staat, is een afleiding: zet zeker op laag.
- Een bedrag op funda bij een verkochte woning is de laatste vraagprijs, niet \
de verkoopprijs. Vul dat in als vraagprijs.
- Zet de gebeurtenissen op datum, oudste eerst."""


def _sleutel(adres):
    """Een van de veertien sleutelfuncties in elf bestanden die allemaal hetzelfde
    bedoelden en op drie punten uiteenliepen. De functie blijft staan omdat
    de aanroepers hem gebruiken, maar hij rekent niet meer zelf."""
    return _psl.sleutel(adres)


def lees(pad=UIT_PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def wat_wij_weten(pad=AANBOD_PAD):
    """
    De vraagprijs en de status zoals wij die kennen, per adres.

    Dit is de controle die we gratis hebben: wijkt de prijs die het model
    terugmeldt sterk af van wat wij zien, dan heeft het een andere, meestal
    oudere advertentie gevonden. Dat bleek in de proef bij de St.
    Stephanusstraat 13, waar een plaatsing uit 2016 terugkwam.

    DE DATUM BESLIST, NIET DE PLAATS IN HET BESTAND. Hier won de laatste regel
    in het bestand. Dat klopte zolang verkopen.txt alleen achteraan werd
    aangevuld met waarnemingen van vandaag, en breekt zodra we oude mails
    inhalen: dan zou een "te koop" van 25 augustus de "verkocht" van 1 oktober
    overschrijven en zou deze controle het model vergelijken met een status
    die wij al niet meer geloven. Een regel zonder datum telt als de oudste.
    """
    beste = {}
    try:
        with open(pad, encoding="utf-8") as f:
            for n, regel in enumerate(f):
                regel = regel.strip()
                if not regel or regel.startswith("#"):
                    continue
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 4:
                    continue
                try:
                    prijs = int(re.sub(r"[^\d]", "", v[2]))
                except ValueError:
                    continue
                sl = _sleutel(v[0])
                rang = ((v[4] if len(v) > 4 else ""), n)
                if sl not in beste or rang >= beste[sl][0]:
                    beste[sl] = (rang, {"prijs": prijs, "status": v[3].lower()})
    except FileNotFoundError:
        return {}
    return {k: w for k, (_, w) in beste.items()}


def toets(rijen, bekend_pand):
    """
    De gebeurtenissen naast wat wij weten leggen.

    De bedoeling is niet om oude plaatsingen weg te gooien, want die zijn juist
    waardevol: een pand dat in 2016 voor €360.000 wegging en nu €625.000 vraagt,
    is een gemeten prijsontwikkeling van datzelfde pand. Het gaat erom ze te
    HERKENNEN als een eerdere advertentie, zodat ze niet worden aangezien voor
    de plaatsing die wij nu volgen.
    """
    if not rijen or not bekend_pand:
        return rijen
    onze = bekend_pand.get("prijs")
    nu_te_koop = bekend_pand.get("status", "").startswith(("te koop", "nieuw"))
    for r in rijen:
        prijs = r.get("vraagprijs")
        # Vijf procent en niet tien: allebei de bedragen horen de laatste
        # vraagprijs te zijn. Bij Marienburg 20 scheelde het 8,6% en dat bleek
        # een andere advertentie.
        if prijs and onze and abs(prijs - onze) / onze > 0.05:
            r["eerdere_advertentie"] = True
        try:
            oud = (dt.date.today() - dt.date.fromisoformat(r["datum"])).days > 730
        except ValueError:
            oud = False
        if nu_te_koop and oud and r["soort"] == "te koop":
            r["eerdere_advertentie"] = True
    return rijen


def te_doen(pad=AANBOD_PAD, bekend=None, alles=False):
    """
    Panden waarvan we de datum niet betrouwbaar kennen.

    Dat zijn de geplakte verkopen, die allemaal de plakdatum dragen, en de
    panden in het aanbod zonder plaatsingsdatum.
    """
    bekend = bekend or {}
    uit, gezien = [], set()
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 6:
                    continue
                adres, status, bron = v[0], v[3].lower(), v[5].lower()
                sleutel = _sleutel(adres)
                if sleutel in gezien or sleutel in bekend:
                    continue
                verdacht = ("plak" in bron
                            or status.startswith("verkocht")
                            or not v[4])
                if alles or verdacht:
                    gezien.add(sleutel)
                    uit.append(adres)
    except FileNotFoundError:
        return []
    return uit


def _vraag_model(adres, sleutel, hint=""):
    """Een pand voorleggen, met webzoeken aan, en het antwoord lezen."""
    body = {
        "model": MODEL,
        "max_tokens": 600,
        "messages": [{"role": "user",
                      "content": VRAAG.format(adres=adres, hint=hint)}],
        "tools": [{"type": "web_search_20250305", "name": "web_search",
                   "max_uses": 4}],
    }
    verzoek = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json",
                 "x-api-key": sleutel,
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(verzoek, timeout=120) as r:
        antwoord = json.load(r)
    tekst = "".join(blok.get("text", "") for blok in antwoord.get("content", [])
                    if blok.get("type") == "text")
    m = re.search(r"\{.*\}", tekst, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# Bronnen waar geen verkoopgeschiedenis in staat. Dit kwam uit de praktijk:
# een datum werd afgeleid uit een YouTube-video met de tekst "128 days ago".
# Zo'n regel heeft wel een bron en komt dus door een controle die alleen op
# aanwezigheid toetst.
SLECHTE_BRONNEN = ("youtube.", "youtu.be", "facebook.", "instagram.",
                   "tiktok.", "marktplaats.", "linkedin.", "pinterest.",
                   "twitter.", "x.com", "reddit.")
# Een datum die uit een relatieve tijdsaanduiding is afgeleid, is een
# berekening van het model en geen gevonden datum.
RELATIEVE_TIJD = ("ago", "geleden", "maanden terug", "vorig jaar", "weken")


def bron_deugt(bron):
    """Of deze bron een verkoopgeschiedenis kan bevatten."""
    laag = (bron or "").lower()
    if not laag:
        return False
    if any(d in laag for d in SLECHTE_BRONNEN):
        return False
    if any(t in laag for t in RELATIEVE_TIJD):
        return False
    return True


def _geldig(d):
    """
    De gebeurtenissen die een bron en een bruikbare datum hebben.

    Een pand kan in tien jaar meerdere keren zijn verkocht, dus dit geeft een
    lijst terug en niet een enkele datum. Elke gebeurtenis wordt afzonderlijk
    beoordeeld: een regel zonder bron valt af, de rest blijft staan.
    """
    if not isinstance(d, dict):
        return []
    uit = []
    for g in (d.get("gebeurtenissen") or []):
        if not isinstance(g, dict) or not bron_deugt(g.get("bron")):
            continue
        datum = g.get("datum")
        if not (isinstance(datum, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum)):
            continue
        try:
            dt.date.fromisoformat(datum)
        except ValueError:
            continue
        soort = str(g.get("soort", "")).lower()
        soort = "verkocht" if "verkocht" in soort else "te koop"
        # Een datum van 1 januari is vrijwel altijd een jaartal dat als exacte
        # datum is opgeschreven. Dat kwam terug bij de Graafsedwarsstraat en de
        # Bloemerstraat. Zo'n regel blijft bruikbaar voor het jaar, maar mag
        # niet voor een dag doorgaan.
        bijbenadering = datum.endswith("-01-01")
        rij = {"soort": soort, "datum": datum,
               "jaar_bij_benadering": bijbenadering,
               "bron": str(g.get("bron"))[:200],
               "zeker": "laag" if bijbenadering else (g.get("zeker") or "laag"),
               "herkomst": "model met webzoeken",
               "opgehaald": dt.date.today().isoformat()}
        # Het bedrag gaat mee als context en wordt nergens in meegerekend.
        prijs = g.get("vraagprijs")
        if isinstance(prijs, (int, float)) and 20000 < prijs < 5000000:
            rij["vraagprijs"] = int(prijs)
        uit.append(rij)
    # Volgorde toetsen: een verkoop kan niet voor de plaatsing liggen die erbij
    # hoort. Bij de Graafsedwarsstraat stond verkocht in januari 2022 en te koop
    # in september 2022; dan klopt minstens een van de twee niet.
    uit = sorted(uit, key=lambda r: r["datum"])
    for i, r in enumerate(uit):
        if r["soort"] != "verkocht":
            continue
        eerder = [x for x in uit[:i] if x["soort"] == "te koop"]
        later = [x for x in uit[i + 1:] if x["soort"] == "te koop"]
        # Geen eerdere plaatsing, wel een latere binnen hetzelfde jaar: dan
        # staan ze vermoedelijk omgekeerd.
        if not eerder and later and later[0]["datum"][:4] == r["datum"][:4]:
            r["volgorde_onlogisch"] = True
            later[0]["volgorde_onlogisch"] = True
    return uit


def proef():
    """
    Nameten wat deze module over verkopen.txt beweert, zonder enige bron.

    Eén ding, en dat is het ding dat hier fout zat: welke waarneming geldt als
    er meer dan een regel voor hetzelfde adres staat.
    """
    fouten = []
    pad = "/tmp/verkoopdatum_model_proef.txt"
    nieuwste = ("Teststraat 1 | Nijmegen | 539000 | verkocht | 2026-10-01 "
                "| funda-mail | 135 | 6524HB")
    ouder = ("Teststraat 1 | Nijmegen | 539000 | te koop | 2026-08-25 "
             "| funda-mail | 135 | 6524HB")
    met_hand = "Teststraat 1 | Nijmegen | 539000 | te koop"
    for regels, naam in (([nieuwste, ouder], "oude regel achteraan"),
                         ([ouder, nieuwste], "oude regel vooraan"),
                         ([nieuwste, met_hand], "regel zonder datum achteraan"),
                         ([met_hand, nieuwste], "regel zonder datum vooraan")):
        with open(pad, "w", encoding="utf-8") as f:
            f.write("# kop\n" + "\n".join(regels) + "\n")
        uit = wat_wij_weten(pad)
        w = uit.get(_sleutel("Teststraat 1")) or {}
        if w.get("status") != "verkocht":
            fouten.append(f"met {naam} geldt status {w.get('status')!r}; de "
                           f"nieuwste waarneming is verkocht")
        if w.get("prijs") != 539000:
            fouten.append(f"met {naam} is de prijs {w.get('prijs')!r}")
    # Een prijs met punten of een euroteken mag niet stil wegvallen.
    with open(pad, "w", encoding="utf-8") as f:
        f.write("Teststraat 2 | Nijmegen | € 425.000 | verkocht | 2026-10-01 "
                "| x | 80 | \n")
    uit = wat_wij_weten(pad)
    if (uit.get(_sleutel("Teststraat 2")) or {}).get("prijs") != 425000:
        fouten.append(f"een prijs met punten wordt niet gelezen: {uit}")
    try:
        os.remove(pad)
    except OSError:
        pass
    print(f"Proef verkoopdatum_model: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    # STEEKPROEF EN NIET PROEF. Deze vlag heette --proef en nam een aantal
    # panden. In dit project betekent --proef overal "meet je eigen logica na",
    # zonder waarde, en eisen.py draait hem automatisch op elke module die een
    # proef heeft. Twee betekenissen achter een naam is precies de fout die we
    # hier al vaker hebben opgeruimd.
    ap.add_argument("--steekproef", type=int, default=0,
                    help="zoveel panden proberen en tonen, niets bewaren")
    ap.add_argument("--proef", action="store_true",
                    help="meet de eigen logica na; raakt geen enkele bron")
    ap.add_argument("--per-ronde", type=int, default=MAX_PER_RONDE)
    ap.add_argument("--controle", action="store_true",
                    help="toetsen aan panden waarvan we de datum al kennen")
    args = ap.parse_args()
    if args.proef:
        return proef()

    sleutel = os.environ.get("ANTHROPIC_API_KEY")
    if not sleutel:
        print("Geen ANTHROPIC_API_KEY; stap overgeslagen", file=sys.stderr)
        return 0

    bekend = lees()
    onze = wat_wij_weten()
    wachtrij = te_doen(bekend=bekend if not args.steekproef else {})
    aantal = args.steekproef or args.per_ronde
    wachtrij = wachtrij[:aantal]
    if not wachtrij:
        print("Niets te doen", file=sys.stderr)
        return 0

    raak = mis = 0
    for adres in wachtrij:
        pand = onze.get(_sleutel(adres)) or {}
        hint = (f"Volgens onze gegevens staat dit pand nu te koop voor "
                f"€{pand['prijs']}. Hoort de advertentie die je vindt daarbij?"
                if pand.get("status", "").startswith(("te koop", "nieuw")) else "")
        try:
            rauw = _vraag_model(adres, sleutel, hint)
        except Exception as e:
            print(f"  {adres}: {str(e)[:80]}", file=sys.stderr)
            mis += 1
            continue
        rijen = toets(_geldig(rauw), pand)
        if not rijen:
            mis += 1
            print(f"  {adres}: niets bruikbaars", file=sys.stderr)
            continue
        raak += 1
        print(f"  {adres}: {len(rijen)} gebeurtenissen", file=sys.stderr)
        for r in rijen:
            print(f"    {r['datum']} {r['soort']:9} "
                  f"{('€%d' % r['vraagprijs']) if r.get('vraagprijs') else '':>10} "
                  f"zeker {r['zeker']}"
                  + ("  [eerdere advertentie]"
                     if r.get("eerdere_advertentie") else ""),
                  file=sys.stderr)
        if not args.steekproef:
            bekend[_sleutel(adres)] = {"adres": adres, "gebeurtenissen": rijen,
                                       "opgehaald": dt.date.today().isoformat()}

    if not args.steekproef:
        with open(UIT_PAD, "w", encoding="utf-8") as f:
            json.dump(bekend, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Verkoopdatums: {raak} gevonden, {mis} niet, "
          f"{len(bekend)} in het bestand"
          + (" (steekproef, niets bewaard)" if args.steekproef else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
