#!/usr/bin/env python3
"""
Wat er van het beleidsblok nog in de bijlage hoort, nadat de brief is geschreven.

WAAROM DIT BESTAAT. Mark wil beleid in de brief zelf en niet als los blok in de
bijlage, zodat de brief als geheel leest. Daarom staat beleid_vandaag.md nu in
de bronnen die brief_verhalend.py krijgt, en schrijft de brief er zelf over
onder een eigen tussenkopje.

Maar het model kiest zelf waarover het schrijft. Slaat het een stuk over, dan
zou dat stuk nergens meer staan, en afwezigheid is in dit project steeds de
fout geweest die niemand zag: de Huislijn-afzender, de 123Wonen-link, de
identieke brief, het splitsblok, de prijsindex, de weggegooide
samenstellingswaarschuwing en de stappen met || echo. Daarom kijkt dit script
na het schrijven welke stukken de brief werkelijk heeft behandeld, en zet
alleen de overgeslagen stukken in de bijlage.

Dus: een stuk staat precies één keer in de mail. In de brief als de brief het
heeft opgepakt, en anders in de bijlage.

De staartregel met de titels van stukken buiten ons onderwerp gaat altijd naar
de bijlage. Die hoort niet in de brief, want de brief gaat niet over
kinderopvang; hij staat er zodat een verkeerd woord in de relevantielijsten
zichtbaar is.

Gebruik:
  python beleid_plaatsen.py --brief digests/2026-10-10-verhaal.md
  python beleid_plaatsen.py --zelftest
"""

import argparse
import json
import os
import sys

import beleidsrelevantie

BLOKRAND = 'border-left:3px solid #E0A458'


def _lees(pad):
    try:
        with open(pad, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def blokken_van(tekst):
    """De losse beleidsblokken uit beleid_vandaag.md, met hun rand ervoor."""
    delen = tekst.split(BLOKRAND)
    if len(delen) < 2:
        return []
    # delen[0] is de kop; elk volgend deel is een blok zonder zijn rand.
    return [BLOKRAND + d for d in delen[1:]]


def verdeel(brief, blokkentekst, titels):
    """
    Geeft (overgeslagen_blokken, behandelde_titels) terug.

    Een blok hoort bij een titel als die titel er letterlijk in staat; zo
    schrijft beleidsblok() hem immers weg. Hoort een blok bij geen enkele
    titel, dan gaat het naar de bijlage: niet kunnen vaststellen dat de brief
    het heeft behandeld is geen reden om het te laten verdwijnen.
    """
    overgeslagen, behandeld = [], []
    for blok in blokken_van(blokkentekst):
        bij = next((t for t in titels if t and t in blok), "")
        if bij and beleidsrelevantie.genoemd(brief, bij):
            behandeld.append(bij)
            continue
        overgeslagen.append(blok)
    return overgeslagen, behandeld


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brief", default="", help="pad naar het verhaalbestand")
    p.add_argument("--blok", default="beleid_vandaag.md")
    p.add_argument("--staart", default="beleid_staart.md")
    p.add_argument("--stand", default="beleid_stand.json")
    p.add_argument("--uit", default="beleid_rest.md")
    p.add_argument("--zelftest", action="store_true")
    a = p.parse_args()
    if a.zelftest:
        return 1 if zelftest() else 0

    blokkentekst = _lees(a.blok)
    staart = _lees(a.staart)
    if not blokkentekst and not staart:
        if os.path.exists(a.uit):
            os.remove(a.uit)
        print("Geen beleid vandaag, niets voor de bijlage")
        return 0

    titels = []
    try:
        titels = (json.loads(_lees(a.stand)) or {}).get("titels") or []
    except Exception as e:
        print(f"Kon {a.stand} niet lezen: {e}", file=sys.stderr)

    brief = _lees(a.brief) if a.brief else ""
    if not brief:
        # Geen brief betekent niet dat de brief alles heeft behandeld. Zonder
        # brief gaat alles naar de bijlage, want dat is de kant waarop een
        # fout niets kost.
        print("Geen brief gelezen; alles gaat naar de bijlage", file=sys.stderr)

    overgeslagen, behandeld = verdeel(brief, blokkentekst, titels)
    for t in behandeld:
        print(f"In de brief behandeld: {t[:70]}")
    for b in overgeslagen:
        print(f"Niet in de brief, dus naar de bijlage: "
              f"{_titel_uit(b, titels)[:70]}")

    if not overgeslagen and not staart:
        if os.path.exists(a.uit):
            os.remove(a.uit)
        print("Alles staat in de brief; niets voor de bijlage")
        return 0

    deel = ["\n## Beleid gemeente Nijmegen\n\n"]
    if overgeslagen:
        deel.extend(overgeslagen)
    if staart:
        deel.append(staart)
    try:
        with open(a.uit, "w", encoding="utf-8") as f:
            f.write("".join(deel))
    except Exception as e:
        print(f"Kon {a.uit} niet schrijven: {e}", file=sys.stderr)
        return 1
    print(f"{len(overgeslagen)} blokken en "
          f"{'een' if staart else 'geen'} staartregel in {a.uit}")
    return 0


def _titel_uit(blok, titels):
    return next((t for t in titels if t and t in blok), "(titel onbekend)")


def zelftest():
    fout = 0
    t1 = "Beleidsregels Woonruimte op de eerste bouwlaag toevoegen binnenstad"
    t2 = "Wijzigingsverordening opkoopbescherming Nijmegen 2026"
    blok = (f'\n## Beleid gemeente Nijmegen\n\n'
            f'<div style="{BLOKRAND};padding:12px">\n<span>{t1}</span>\n</div>\n\n'
            f'<div style="{BLOKRAND};padding:12px">\n<span>{t2}</span>\n</div>\n\n')

    if len(blokken_van(blok)) != 2:
        print(f"AFWIJKING: {len(blokken_van(blok))} blokken gevonden, verwacht 2")
        fout += 1
    if blokken_van("") or blokken_van("## Beleid\n\nniets"):
        print("AFWIJKING: zonder rand horen er geen blokken uit te komen")
        fout += 1

    # De brief behandelt het eerste stuk en niet het tweede.
    brief = ("De gemeente voert een vergunningplicht in voor woonruimte op de "
             "eerste bouwlaag in de binnenstad.")
    over, behandeld = verdeel(brief, blok, [t1, t2])
    if behandeld != [t1]:
        print(f"AFWIJKING: behandeld gaf {behandeld}, verwacht alleen het eerste")
        fout += 1
    if len(over) != 1 or t2 not in over[0]:
        print(f"AFWIJKING: overgeslagen hoort alleen het tweede stuk te zijn")
        fout += 1

    # Geen brief: alles naar de bijlage.
    over, behandeld = verdeel("", blok, [t1, t2])
    if len(over) != 2 or behandeld:
        print(f"AFWIJKING: zonder brief horen alle blokken naar de bijlage, "
              f"gaf {len(over)} over en {len(behandeld)} behandeld")
        fout += 1

    # Een blok waarvan de titel niet in de stand staat, gaat naar de bijlage.
    over, behandeld = verdeel(brief, blok, [])
    if len(over) != 2:
        print("AFWIJKING: zonder titels horen alle blokken naar de bijlage")
        fout += 1

    # De echte brief van 10 oktober noemde het stuk niet.
    echt = _lees("digests/2026-10-10-verhaal.md")
    if echt:
        over, behandeld = verdeel(echt, blok, [t1, t2])
        if len(over) != 2:
            print(f"AFWIJKING: de brief van 10 oktober noemde geen van beide "
                  f"stukken, maar {2 - len(over)} gold als behandeld")
            fout += 1

    print(f"zelftest: {fout} afwijkend")
    return fout


if __name__ == "__main__":
    sys.exit(main())
