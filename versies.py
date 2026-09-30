#!/usr/bin/env python3
"""
Welke versie van welk bestand draait er?

Het probleem dat dit oplost: bij een handmatige upload is niet te zien of alle
bestanden zijn meegekomen en of ze de laatste versie zijn. De vorige controle
zocht naar een stukje tekst dat ook in oudere versies stond en meldde daarom
"nieuwste versie" terwijl dat niet zo was.

Hier staat per bestand een vingerafdruk. Wijkt die af, dan is het bestand
ouder of nieuwer dan de paklijst; ontbreekt het, dan is het niet geuploud.
Dat is niet te verwarren met iets anders.

Gebruik:
  python versies.py --maak        de paklijst opnieuw opbouwen
  python versies.py --controleer  vergelijken en melden wat afwijkt
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys

PAD = "versies.json"
# Wat er meetelt. De digests en gegevensbestanden veranderen elke run en horen
# er dus niet in; alleen code en handmatig beheerde lijsten.
MAPPEN = (".", ".github/workflows")
EXTENSIES = (".py", ".yml", ".txt", ".md")
NEGEER = ("versies.py", "versies.json", "requirements.txt")
NEGEER_MAPPEN = ("digests", ".git", "__pycache__", "node_modules")


def vingerafdruk(pad):
    """De sha256 van een bestand, de eerste twaalf tekens."""
    h = hashlib.sha256()
    with open(pad, "rb") as f:
        for blok in iter(lambda: f.read(65536), b""):
            h.update(blok)
    return h.hexdigest()[:12]


def bestanden():
    """Alle bestanden die meetellen, op volgorde."""
    uit = []
    for map_ in MAPPEN:
        if not os.path.isdir(map_):
            continue
        for naam in sorted(os.listdir(map_)):
            pad = os.path.join(map_, naam) if map_ != "." else naam
            if os.path.isdir(pad) or naam in NEGEER:
                continue
            # Op mapnaam vergelijken en niet op tekst: ".github" bevat ".git",
            # waardoor de workflow er anders uit valt. Dezelfde insluitingsfout
            # als "studentenhuis" dat op "huis" matchte.
            delen = set(pad.replace("\\", "/").split("/"))
            if delen & set(NEGEER_MAPPEN):
                continue
            if naam.endswith(EXTENSIES):
                uit.append(pad)
    return uit


def maak(pad=PAD):
    """De paklijst opbouwen uit wat er nu staat."""
    lijst = {p: vingerafdruk(p) for p in bestanden()}
    with open(pad, "w", encoding="utf-8") as f:
        json.dump({"gemaakt": dt.date.today().isoformat(),
                   "bestanden": lijst}, f, ensure_ascii=False,
                  indent=1, sort_keys=True)
    print(f"Paklijst met {len(lijst)} bestanden weggeschreven naar {pad}",
          file=sys.stderr)
    return lijst


def controleer(pad=PAD):
    """
    Vergelijken met de paklijst.

    Geeft drie groepen terug: gelijk, afwijkend en ontbrekend. Bestanden die er
    wel zijn maar niet in de lijst staan, worden apart gemeld; dat is geen
    fout, maar het zegt wel dat de paklijst ouder is dan de repo.
    """
    try:
        with open(pad, encoding="utf-8") as f:
            lijst = (json.load(f) or {}).get("bestanden") or {}
    except Exception:
        return None
    gelijk, afwijkend, ontbrekend = [], [], []
    for bestand, verwacht in sorted(lijst.items()):
        if not os.path.exists(bestand):
            ontbrekend.append(bestand)
        elif vingerafdruk(bestand) == verwacht:
            gelijk.append(bestand)
        else:
            afwijkend.append(bestand)
    onbekend = [p for p in bestanden() if p not in lijst]
    return {"gelijk": gelijk, "afwijkend": afwijkend,
            "ontbrekend": ontbrekend, "onbekend": onbekend}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maak", action="store_true")
    ap.add_argument("--controleer", action="store_true")
    args = ap.parse_args()

    if args.maak:
        maak()
        return 0

    uit = controleer()
    if uit is None:
        print("Geen paklijst gevonden; draai eerst versies.py --maak",
              file=sys.stderr)
        return 0
    print(f"Versiecontrole: {len(uit['gelijk'])} gelijk aan de paklijst, "
          f"{len(uit['afwijkend'])} afwijkend, {len(uit['ontbrekend'])} ontbreekt")
    for bestand in uit["afwijkend"]:
        print(f"  ANDERE VERSIE: {bestand}")
    for bestand in uit["ontbrekend"]:
        print(f"  ONTBREEKT:     {bestand}")
    for bestand in uit["onbekend"][:10]:
        print(f"  niet in de paklijst: {bestand}")
    if uit["afwijkend"] or uit["ontbrekend"]:
        print("Let op: de code die draait is niet de code uit de paklijst.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
