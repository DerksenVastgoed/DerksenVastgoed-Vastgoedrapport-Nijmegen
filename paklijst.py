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
  python paklijst.py --maak        de paklijst opnieuw opbouwen
  python paklijst.py --controleer  vergelijken en melden wat afwijkt

Het script heet paklijst.py en de lijst zelf versies.json. Dat is met opzet
verschillend: toen allebei "versies" heetten, is bij het uploaden de json als
py opgeslagen en stond er een bestand van 1500 bytes zonder functies in de
repo.
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
# Alleen code. Gegevensbestanden als verkopen.txt en woz.txt worden door de
# run zelf bijgewerkt en wijken dus altijd af; die meenemen levert elke dag een
# valse melding op. De handmatige lijsten zoals bouwkosten_eigen.txt vallen er
# ook buiten, want die vul jij aan en dan zou de paklijst gaan klagen over je
# eigen werk.
EXTENSIES = (".py", ".yml")
# Bestanden die ik niet zelf lever en waarvan mijn kopie dus kan afwijken van
# de repo. Die permanent als "andere versie" melden is ruis; wie ze beheert,
# beheert ze buiten deze sessies om.
NEGEER = ("paklijst.py", "versies.json", "requirements.txt",
          "ov_haltes.py", "rijksmonumenten.py", "bag_uitzoeken.py")
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


def _regels(bestand):
    """Het aantal regels, als handvat om twee versies te onderscheiden."""
    try:
        with open(bestand, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


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
            # Niet alleen DAT het afwijkt, maar ook iets waaraan te zien is WAT
            # er staat. Twee bestanden bleven afwijken na opnieuw uploaden, en
            # zonder dit detail was er alleen te raden: een oude versie, een
            # halve upload, of een echt verschil.
            afwijkend.append(f"{bestand} ({os.path.getsize(bestand)} bytes, "
                             f"{_regels(bestand)} regels)")
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
