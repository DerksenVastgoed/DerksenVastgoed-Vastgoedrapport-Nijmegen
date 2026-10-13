#!/usr/bin/env python3
"""
Wat een bekendmaking zegt over de uitkomst, en tot wanneer de stukken open staan.

WAAROM DIT BESTAAT. Wij volgen aanvragen en besluiten al, maar bewaren er
alleen datum, titel, soort en url van. De tekst van de publicatie zegt veel
meer, en die tekst halen wij al op.

DRIE DINGEN DIE ERIN STAAN EN DIE WIJ NIET GEBRUIKTEN:

  1. DE UITKOMST. De titel zegt alleen "Besluit voor het splitsen van ...".
     Van 37 besluiten noemde er twee het woord verleend. De tekst zegt het
     wel, in de eerste zin: "Gemeente Nijmegen verleende een
     omgevingsvergunning." Zonder die uitkomst valt er niets te leren van
     onze eigen voorspellingen, want dan weten wij nooit of we het goed
     zagen.

  2. HET ZAAKNUMMER. De aanvraag zegt "geregistreerd onder kenmerk
     Z2026-00005538", het besluit zegt "voor de aanvraag met zaaknummer
     Z2025-00011358". Daarmee horen aanvraag en besluit bij elkaar zonder
     dat wij op adres of datum hoeven te gissen. Nu koppelen wij op de
     pandsleutel, en dan hoort een tweede aanvraag voor hetzelfde pand bij
     het verkeerde besluit.

  3. TOT WANNEER DE STUKKEN TE ZIEN ZIJN. Het besluit zegt: "U kunt de
     gemeente tot 13 november 2026 laten weten dat u het niet eens bent met
     het besluit... In deze periode kunt u de documenten met informatie over
     het besluit bekijken via de link op deze pagina." De stukken staan dus
     open tijdens de bezwaartermijn en daarna niet meer. Dat verklaart
     waarom Mark zei dat het maar een paar weken kan.

WAT DIT NIET DOET. Het haalt die stukken niet op. De link waarmee dat zou
moeten staat niet in de broncode van de pagina; hij wordt door de browser
ingeladen en wij hebben hem niet kunnen vinden. Zie bijlagen.py. Wat deze
module wel kan is zeggen welke dossiers nu open staan en tot welke dag, zodat
het klikwerk een korte lijst met een deadline is in plaats van een zoektocht.
"""

import argparse
import json
import re
import sys

# De zinnen zoals ze er werkelijk staan. Afgelezen van drie besluiten en twee
# aanvragen van gemeente Nijmegen, niet bedacht. Een patroon bouwen tegen een
# zin die niemand schrijft, vangt niets.
RE_ZAAK = re.compile(r"\b(Z\d{4}-\d{6,})\b")
RE_VERLEEND = re.compile(r"verleende een omgevingsvergunning", re.I)
RE_TOESTEMMING = re.compile(r"geeft hiermee toestemming", re.I)
RE_BESLUITDATUM = re.compile(
    r"Dit besluit namen wij op (\d{1,2} \w+ \d{4})", re.I)
RE_BEZWAAR_TOT = re.compile(
    r"laten weten dat u het niet eens bent[^.]*?tot (\d{1,2} \w+ \d{4})", re.I)
RE_BEZWAAR_TOT2 = re.compile(r"tot (\d{1,2} \w+ \d{4}) laten weten dat u het "
                             r"niet eens bent", re.I)
RE_ONTVANGEN = re.compile(r"ontving de aanvraag op (\d{1,2} \w+ \d{4})", re.I)
RE_VERWACHT = re.compile(
    r"neemt daarover waarschijnlijk (\d{1,2} \w+ \d{4})", re.I)

# Woorden die een andere afloop aankondigen. Deze heb ik NIET in een echte
# publicatie gezien; ze staan hier omdat een besluit ook negatief kan zijn en
# wij anders elke uitkomst "verleend" zouden noemen. Daarom geven zij geen
# uitkomst maar de uitkomst "anders", met de zin erbij, zodat de eerste echte
# weigering in het rapport opduikt en wij het patroon dan uit dat geval
# halen in plaats van uit mijn fantasie.
ANDERS = ("weigerde", "geweigerd", "wijzen wij af", "afgewezen",
          "buiten behandeling", "ingetrokken", "van rechtswege")

MAANDEN = {"januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5,
           "juni": 6, "juli": 7, "augustus": 8, "september": 9,
           "oktober": 10, "november": 11, "december": 12}


def datum(tekst):
    """"13 november 2026" wordt 2026-11-13. Onbekend blijft leeg."""
    m = re.match(r"\s*(\d{1,2})\s+(\w+)\s+(\d{4})\s*$", tekst or "")
    if not m:
        return ""
    maand = MAANDEN.get(m.group(2).lower())
    if not maand:
        return ""
    return f"{int(m.group(3)):04d}-{maand:02d}-{int(m.group(1)):02d}"


def velden_uit(tekst):
    """
    De velden die in een publicatie staan. Wat ontbreekt blijft leeg.

    Nooit een aanname: staat er geen uitkomst in, dan is de uitkomst
    onbekend en niet "verleend". Een besluit dat wij verkeerd als verleend
    tellen, maakt onze voorspelling beter dan zij is, en dat is de enige
    fout die een lerend model niet zelf kan herstellen.
    """
    t = re.sub(r"\s+", " ", tekst or "")
    zaak = RE_ZAAK.search(t)
    uit = {
        "zaaknummer": zaak.group(1) if zaak else "",
        "uitkomst": "",
        "uitkomst_reden": "",
        "besluitdatum": "",
        "bezwaar_tot": "",
        "ontvangen": "",
        "verwacht_besluit": "",
    }
    anders = [w for w in ANDERS if w in t.lower()]
    if RE_VERLEEND.search(t) or RE_TOESTEMMING.search(t):
        uit["uitkomst"] = "verleend"
        if anders:
            # Allebei: dan zegt deze tekst twee dingen en kies ik niet.
            uit["uitkomst"] = "onduidelijk"
            uit["uitkomst_reden"] = (f"zowel verleend als {', '.join(anders)} "
                                     f"komt voor")
    elif anders:
        uit["uitkomst"] = "anders"
        uit["uitkomst_reden"] = ", ".join(anders)
    for sleutel, patroon in (("besluitdatum", RE_BESLUITDATUM),
                             ("ontvangen", RE_ONTVANGEN),
                             ("verwacht_besluit", RE_VERWACHT)):
        m = patroon.search(t)
        if m:
            uit[sleutel] = datum(m.group(1))
    for patroon in (RE_BEZWAAR_TOT, RE_BEZWAAR_TOT2):
        m = patroon.search(t)
        if m:
            uit["bezwaar_tot"] = datum(m.group(1))
            break
    return uit


def open_dossiers(rijen, vandaag):
    """
    Welke dossiers nu nog in hun bezwaartermijn zitten, aflopend op deadline.

    Dit is de lijst die het klikwerk kort maakt: alleen deze dossiers hebben
    hun stukken nog open staan. Een dossier zonder bezwaardatum staat er niet
    in, en dat is iets anders dan een dossier dat gesloten is; daarom telt de
    oproeper die apart.
    """
    uit = []
    for r in rijen:
        tot = r.get("bezwaar_tot") or ""
        if not tot:
            continue
        if tot >= vandaag:
            uit.append(r)
    return sorted(uit, key=lambda r: r["bezwaar_tot"])


def koppel(aanvragen, besluiten):
    """
    Aanvraag en besluit aan elkaar via het zaaknummer.

    WAAROM NIET OP PAND. Nu koppelen wij op de pandsleutel en op datum: het
    eerste besluit na een aanvraag. Bij twee aanvragen voor hetzelfde pand
    hoort de tweede dan bij het besluit van de eerste. Het zaaknummer staat
    in beide publicaties en laat geen ruimte.
    """
    per = {}
    for a in aanvragen:
        if a.get("zaaknummer"):
            per.setdefault(a["zaaknummer"], {})["aanvraag"] = a
    for b in besluiten:
        if b.get("zaaknummer"):
            per.setdefault(b["zaaknummer"], {})["besluit"] = b
    paren, alleen_a, alleen_b = [], [], []
    for nummer, d in per.items():
        if "aanvraag" in d and "besluit" in d:
            paren.append((nummer, d["aanvraag"], d["besluit"]))
        elif "aanvraag" in d:
            alleen_a.append((nummer, d["aanvraag"]))
        else:
            alleen_b.append((nummer, d["besluit"]))
    return paren, alleen_a, alleen_b


def proef():
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. EEN BESLUIT ZOALS HET ER WERKELIJK STAAT.
    # Dit is de tekst van het besluit over Hatertseweg 338, afgelezen van de
    # publicatie. Niet geparafraseerd: de patronen moeten tegen deze zinnen
    # werken en niet tegen zinnen die ik mooier vond.
    besluit = ("Besluit voor Het verbouwen en uitbreiden tot 6 zelfstandige "
               "woonruimtes, aan Hatertseweg 338, 6533GP Nijmegen Gemeente "
               "Nijmegen verleende een omgevingsvergunning. De gemeente geeft "
               "hiermee toestemming voor Het verbouwen en uitbreiden tot 6 "
               "zelfstandige woonruimtes aan Hatertseweg 338, 6533GP "
               "Nijmegen. Dit besluit namen wij op 14 september 2026 voor de "
               "aanvraag met zaaknummer Z2025-00011358. Bent u het niet eens "
               "met het besluit? U kunt de gemeente tot 13 november 2026 "
               "laten weten dat u het niet eens bent met het besluit. Dit "
               "heet bezwaar maken. In deze periode kunt u de documenten met "
               "informatie over het besluit bekijken via de link op deze "
               "pagina.")
    v = velden_uit(besluit)
    check("zaaknummer", v["zaaknummer"], "Z2025-00011358")
    check("uitkomst", v["uitkomst"], "verleend")
    check("besluitdatum", v["besluitdatum"], "2026-09-14")
    check("bezwaar tot", v["bezwaar_tot"], "2026-11-13")

    # 2. EEN AANVRAAG ZOALS ZIJ ER WERKELIJK STAAT.
    aanvraag = ("Gemeente Nijmegen ontving een aanvraag voor een "
                "omgevingsvergunning. De aanvraag is geregistreerd onder "
                "kenmerk Z2026-00005538. De gemeente ontving de aanvraag op "
                "22 september 2026. De gemeente neemt daarover waarschijnlijk "
                "17 november 2026 een besluit. U kunt nu nog niet reageren.")
    a = velden_uit(aanvraag)
    check("kenmerk van de aanvraag", a["zaaknummer"], "Z2026-00005538")
    check("ontvangen", a["ontvangen"], "2026-09-22")
    check("verwacht besluit", a["verwacht_besluit"], "2026-11-17")
    # EEN AANVRAAG HEEFT GEEN UITKOMST, en die mag er ook niet bij verzonnen
    # worden. Een aanvraag die als verleend wordt geteld maakt onze
    # voorspelling beter dan zij is.
    check("aanvraag zonder uitkomst", a["uitkomst"], "")
    check("aanvraag zonder bezwaartermijn", a["bezwaar_tot"], "")

    # 3. WAT ONTBREEKT BLIJFT LEEG.
    leeg = velden_uit("een tekst zonder enig veld")
    check("leeg zaaknummer", leeg["zaaknummer"], "")
    check("lege uitkomst", leeg["uitkomst"], "")
    check("niets", velden_uit(""), velden_uit(None))

    # 4. EEN ANDERE AFLOOP WORDT NIET ALS VERLEEND GETELD.
    w = velden_uit("De gemeente heeft de aanvraag geweigerd. Dit besluit "
                   "namen wij op 1 maart 2026 voor de aanvraag met "
                   "zaaknummer Z2026-00000001.")
    check("weigering", w["uitkomst"], "anders")
    check("reden erbij", w["uitkomst_reden"], "geweigerd")
    check("zaaknummer bij een weigering", w["zaaknummer"], "Z2026-00000001")
    # Zegt een tekst allebei, dan kies ik niet. Liever onduidelijk dan een
    # verkeerd label, want een verkeerd label kan een lerend model niet zelf
    # herstellen.
    twee = velden_uit("verleende een omgevingsvergunning ... buiten "
                      "behandeling gelaten")
    check("twee uitkomsten", twee["uitkomst"], "onduidelijk")

    # 5. EEN DATUM IN WOORDEN WORDT EEN DATUM OM MEE TE REKENEN.
    check("datum", datum("13 november 2026"), "2026-11-13")
    check("datum met een cijfer", datum("1 maart 2026"), "2026-03-01")
    check("onbekende maand", datum("13 smurf 2026"), "")
    check("geen datum", datum("binnenkort"), "")

    # 6. ALLEEN WAT NU NOG OPEN STAAT.
    rijen = [{"gmb": "a", "bezwaar_tot": "2026-11-13"},
             {"gmb": "b", "bezwaar_tot": "2026-10-01"},
             {"gmb": "c", "bezwaar_tot": "2026-10-13"},
             {"gmb": "d", "bezwaar_tot": ""}]
    op = open_dossiers(rijen, "2026-10-13")
    check("open dossiers", [r["gmb"] for r in op], ["c", "a"])

    # 7. KOPPELEN OP ZAAKNUMMER EN NIET OP PAND.
    # Twee aanvragen voor hetzelfde pand horen bij hun eigen besluit. Dit is
    # het geval waar de koppeling op pand en datum de mist in gaat.
    aanvr = [{"zaaknummer": "Z1", "pand": "x", "datum": "2026-01-01"},
             {"zaaknummer": "Z2", "pand": "x", "datum": "2026-02-01"}]
    besl = [{"zaaknummer": "Z2", "pand": "x", "datum": "2026-03-01"}]
    paren, alleen_a, alleen_b = koppel(aanvr, besl)
    check("aantal paren", len(paren), 1)
    check("het juiste paar", paren[0][0], "Z2")
    check("aanvraag zonder besluit", [n for n, _ in alleen_a], ["Z1"])
    check("besluit zonder aanvraag", alleen_b, [])
    # Zonder zaaknummer doet een rij niet mee: raden is erger dan overslaan.
    paren2, a2, b2 = koppel([{"zaaknummer": ""}], [{"zaaknummer": ""}])
    check("zonder nummer geen koppeling", (len(paren2), len(a2), len(b2)),
          (0, 0, 0))

    print(f"Proef besluit: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--uit", default="", help="waar de velden worden bewaard")
    args = ap.parse_args()
    if args.proef:
        return proef()
    print("Deze module leest teksten die bijlagen.py ophaalt; draai hem via "
          "de workflow.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
