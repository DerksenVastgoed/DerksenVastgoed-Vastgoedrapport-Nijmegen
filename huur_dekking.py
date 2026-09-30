#!/usr/bin/env python3
"""
Hoeveel van het huuraanbod zien we al?

Aanleiding: er blijken tien tot vijftien platforms te zijn die huurwoningen in
Nijmegen aanbieden. De vraag is niet of we ze allemaal kunnen koppelen, maar of
het loont. Als Pararius en Kamernet samen al negentig procent van die adressen
bevatten, is een derde koppeling weggegooid werk; is het de helft, dan ligt dat
anders.

Plak de adressen die je op zo'n site ziet in huur_elders.txt, een per regel,
en dit script zegt welke we al hadden en welke we misten. Daarna weten we of
een koppeling de moeite waard is, en welke.

Een regel mag van alles bevatten; het script haalt er straat en huisnummer uit:
  Kronenburgersingel 223-D, Nijmegen  €1.450
  Hatertseveldweg 12
  Thorbeckestraat 37 | huurflits
"""
import argparse
import re
import sys

ELDERS_PAD = "huur_elders.txt"
EIGEN_PAD = "verkopen.txt"

# Straat plus huisnummer, met een eventuele toevoeging.
RE_ADRES = re.compile(
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'\- ]{2,40}?)\s+(\d{1,4})\s*([A-Za-z]?(?:-\w+)?)")


def sleutel(straat, nummer=""):
    """Zelfde vorm voor twee schrijfwijzen van hetzelfde adres."""
    a = (straat or "").lower().strip()
    a = a.replace("straat", "str").replace("laan", "ln").replace("weg", "wg")
    a = a.replace("singel", "sgl").replace("plein", "pln")
    a = re.sub(r"[^a-z0-9]", "", a)
    return a + re.sub(r"[^a-z0-9]", "", str(nummer).lower())


def lees_elders(pad=ELDERS_PAD):
    """De geplakte adressen, met de regel erbij voor de rapportage."""
    uit = []
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if not regel or regel.startswith("#"):
                    continue
                m = RE_ADRES.search(regel)
                if not m:
                    continue
                straat, nummer, toev = m.groups()
                uit.append({"regel": regel, "straat": straat.strip(),
                            "nummer": nummer + (toev or ""),
                            "sleutel": sleutel(straat, nummer + (toev or ""))})
    except FileNotFoundError:
        return []
    return uit


def lees_eigen(pad=EIGEN_PAD):
    """
    Wat wij al aan huuraanbod hebben gezien, op sleutel.

    Alleen huurregels; koopaanbod telt hier niet mee. Advertenties zonder
    huisnummer, zoals bij Pararius en Kamernet, krijgen een sleutel zonder
    nummer; die matchen dus op straat.
    """
    per_sleutel, straten = {}, {}
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 6 or not v[3].lower().startswith("te huur"):
                    continue
                m = RE_ADRES.search(v[0])
                if m:
                    straat, nummer, toev = m.groups()
                    per_sleutel[sleutel(straat, nummer + (toev or ""))] = v
                    straten.setdefault(sleutel(straat), []).append(v)
                else:
                    straten.setdefault(sleutel(v[0]), []).append(v)
    except FileNotFoundError:
        return {}, {}
    return per_sleutel, straten


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elders", default=ELDERS_PAD)
    ap.add_argument("--eigen", default=EIGEN_PAD)
    args = ap.parse_args()

    elders = lees_elders(args.elders)
    if not elders:
        print(f"Geen adressen gevonden in {args.elders}; plak ze daar, "
              f"een per regel", file=sys.stderr)
        return 0
    per_sleutel, straten = lees_eigen(args.eigen)

    gevonden, op_straat, gemist = [], [], []
    for a in elders:
        if a["sleutel"] in per_sleutel:
            gevonden.append(a)
        elif sleutel(a["straat"]) in straten:
            op_straat.append(a)
        else:
            gemist.append(a)

    n = len(elders)
    print(f"Huurdekking: {n} adressen geplakt")
    print(f"  {len(gevonden)} exact bij ons bekend "
          f"({len(gevonden) / n * 100:.0f}%)")
    print(f"  {len(op_straat)} alleen op straatnaam herkend "
          f"({len(op_straat) / n * 100:.0f}%), want onze bron geeft geen "
          f"huisnummer")
    print(f"  {len(gemist)} missen we ({len(gemist) / n * 100:.0f}%)")
    if gemist:
        print("\nGemist:")
        for a in gemist[:40]:
            print(f"  {a['straat']} {a['nummer']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
