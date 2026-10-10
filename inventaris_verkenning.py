#!/usr/bin/env python3
"""
Eenmalige verkenning van de PDOK-locatieserver. Wordt na gebruik weggegooid.

WAAROM. buurtinventaris.py filtert op buurtnaam zonder gemeente erbij:
fq=["type:adres", 'buurtnaam:"Biezen"']. Die buurtnamen bestaan elders ook, en
daardoor staan er in buurtinventaris.json 491 postcodes van de 1.733 die niet
in Nijmegen liggen: 2771 Boskoop, 3431 Nieuwegein, 3828 Amersfoort, 4131
Vianen, 4201 Gorinchem, 5103 Dongen, 7001 Doetinchem en 9401 Assen. Altrade en
Bottendaal zijn als buurtnaam uniek voor Nijmegen en hebben nul vervuiling; de
andere vier hebben het wel.

Dat raakt meer dan de postcodes. Het aantal adressen per buurt komt uit
numFound van dezelfde vraag, dus die 34.946 adressen zijn op dezelfde manier te
hoog, en de straatnamen die de tweede ronde per straat gebruikt ook.

DE VRAGEN. Deze omgeving mag api.pdok.nl niet benaderen en het logboek van een
run is hier niet te lezen, dus het antwoord moet via git terug en één run moet
alle vragen tegelijk stellen.

  1. Welke velden heeft een adresrecord werkelijk? Daaruit blijkt op welk veld
     de gemeente te filteren is. Gokken op een veldnaam is wat deze hele reeks
     fouten heeft veroorzaakt.
  2. Accepteert de dienst gemeentenaam als filter, en wat doet dat met
     numFound per buurt? Een filter dat niet werkt geeft geen fout maar
     dezelfde telling, en dat is stil.
  3. Hetzelfde voor woonplaatsnaam. Let op het verschil: gemeente Nijmegen
     bevat ook de woonplaatsen Lent, Oosterhout en Ressen. Filteren op
     woonplaats zou die eruit gooien, en of dat goed is hangt ervan af of
     onze zes buurten daar liggen. De zes liggen om het centrum, dus
     gemeentenaam is wat we willen, maar dat moet uit de cijfers blijken en
     niet uit mijn aanname.
  4. Welke gemeenten leveren de vervuiling precies? Dat is de controle dat de
     diagnose klopt: de gemeenten die hieruit komen moeten overeenkomen met de
     postcodes die we al in de inventaris vonden.
"""

import json
import sys

import requests

PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
KOP = {"User-Agent": "NijmegenVastgoedMonitor/1.0"}
BUURTEN = ["Altrade", "Benedenstad", "Biezen", "Bottendaal", "Galgenveld",
           "Stadscentrum"]
TIJD = 30


def vraag(params):
    try:
        r = requests.get(PDOK, params=params, headers=KOP, timeout=TIJD)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:400]}"
    try:
        return r.json().get("response", {}), ""
    except Exception as e:
        return None, f"geen json: {e}"


def tel(fq):
    antwoord, fout = vraag({"q": "*", "fq": fq, "rows": 0, "wt": "json"})
    if fout:
        return None, fout
    return antwoord.get("numFound"), ""


def kop(n, tekst):
    print(f"\n{'=' * 70}\nVRAAG {n}. {tekst}\n{'=' * 70}")


def vraag1_velden():
    kop(1, "Welke velden heeft een adresrecord?")
    antwoord, fout = vraag({"q": "*", "fq": ["type:adres",
                                             'buurtnaam:"Bottendaal"'],
                            "rows": 1, "wt": "json"})
    if fout:
        print(f"MISLUKT: {fout}")
        return
    docs = antwoord.get("docs") or []
    if not docs:
        print("geen records")
        return
    print("  het hele eerste record:")
    print(json.dumps(docs[0], ensure_ascii=False, indent=2)[:2000])
    print(f"\n  velden: {', '.join(sorted(docs[0].keys()))}")
    for veld in ("gemeentenaam", "gemeentecode", "woonplaatsnaam",
                 "provincienaam", "buurtnaam", "wijknaam", "postcode"):
        aan = "JA" if veld in docs[0] else "NEE"
        print(f"    {veld}: {aan}"
              + (f"  waarde={docs[0][veld]!r}" if veld in docs[0] else ""))


def vraag23_filters():
    kop(2, "Wat doet een filter op gemeente en op woonplaats per buurt?")
    print(f"  {'buurt':14s} {'zonder':>8s} {'gemeente':>9s} "
          f"{'woonplaats':>11s}  {'vervuiling':>10s}")
    totalen = [0, 0, 0]
    for buurt in BUURTEN:
        basis = ["type:adres", f'buurtnaam:"{buurt}"']
        zonder, f1 = tel(basis)
        gem, f2 = tel(basis + ['gemeentenaam:"Nijmegen"'])
        wpl, f3 = tel(basis + ['woonplaatsnaam:"Nijmegen"'])
        if f1 or f2 or f3:
            print(f"  {buurt:14s} MISLUKT: {f1 or f2 or f3}")
            continue
        vervuild = (zonder or 0) - (gem or 0)
        print(f"  {buurt:14s} {zonder:>8} {gem:>9} {wpl:>11}  "
              f"{vervuild:>10}")
        totalen[0] += zonder or 0
        totalen[1] += gem or 0
        totalen[2] += wpl or 0
    print(f"  {'TOTAAL':14s} {totalen[0]:>8} {totalen[1]:>9} "
          f"{totalen[2]:>11}  {totalen[0] - totalen[1]:>10}")
    print()
    if totalen[1] == totalen[0]:
        print("  >>> LET OP: het gemeentefilter verandert niets. Dan wordt het")
        print("      veld niet als filter geaccepteerd en wordt het stil")
        print("      genegeerd, want er komt geen fout.")
    if totalen[2] and totalen[2] != totalen[1]:
        print(f"  >>> woonplaats geeft {totalen[1] - totalen[2]} minder dan")
        print(f"      gemeente. Gemeente Nijmegen bevat ook Lent, Oosterhout")
        print(f"      en Ressen, dus dat verschil hoort bij die woonplaatsen.")
        print(f"      Voor onze zes centrumbuurten hoort het 0 te zijn.")


def vraag4_welke_gemeenten():
    kop(4, "Welke gemeenten leveren de vervuiling?")
    for buurt in BUURTEN:
        antwoord, fout = vraag({
            "q": "*", "fq": ["type:adres", f'buurtnaam:"{buurt}"'],
            "rows": 0, "wt": "json", "facet": "true",
            "facet.field": "gemeentenaam", "facet.limit": 12})
        if fout:
            print(f"  {buurt}: MISLUKT: {fout}")
            continue
        print(f"\n  {buurt}:")
        velden = (((antwoord.get("facet_counts") or {})
                   .get("facet_fields") or {}).get("gemeentenaam") or [])
        if not velden:
            # Geen facetten? Dan met de hand een steekproef.
            steek, f2 = vraag({"q": "*",
                               "fq": ["type:adres", f'buurtnaam:"{buurt}"'],
                               "rows": 200, "wt": "json",
                               "fl": "gemeentenaam postcode"})
            if f2:
                print(f"    facetten noch steekproef: {f2}")
                continue
            per = {}
            for doc in (steek.get("docs") or []):
                per[doc.get("gemeentenaam") or "?"] = per.get(
                    doc.get("gemeentenaam") or "?", 0) + 1
            print("    (uit een steekproef van 200, geen facetten)")
            for naam, n in sorted(per.items(), key=lambda x: -x[1]):
                print(f"      {naam}: {n}")
            continue
        for i in range(0, len(velden) - 1, 2):
            print(f"      {velden[i]}: {velden[i + 1]}")


def main():
    print("Verkenning van de PDOK-locatieserver")
    vraag1_velden()
    vraag23_filters()
    vraag4_welke_gemeenten()
    print("\nKlaar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
