#!/usr/bin/env python3
"""
De modus van elke brief vastleggen, en bewaken dat er geen kopie meer naar pa
gaat.

GESCHIEDENIS. Van 20 oktober tot 4 november 2026 regelde dit bestand de kopie
van de brief naar pa: de briefrun mailde alleen Mark, de nakijkronde startte
daarna kopie_pa.yml (met of zonder correcties, die het verhaal lieten
herschrijven), en een geplande taak om 08:52 stuurde hem als vangnet alsnog.
pa_kopie.json hield bij of hij mocht (geen testrun, geen halve update) en of
hij al weg was.

4 NOVEMBER 2026, Mark: er gaat niets meer naar pa. kopie_pa.yml, het
herschrijven en het markeren als verstuurd zijn weggehaald. Wat overblijft:

  1. klaarzetten: de briefrun legt in pa_kopie.json de datum, de modus en een
     eventuele halve update vast. brief_invoer.py leest de modus daaruit en
     uit de geschiedenis van dat bestand terug, dus de naam blijft staan tot
     die lezer is omgezet; een nieuw bestand zou de geschiedenis kwijtraken.
     Het veld mag_naar_pa zegt sindsdien alleen nog "geen halve update".
  2. ontvangers_pa: geen workflow mag MAIL_TO_VERHAAL (het adres van pa) of
     CC_VERHAAL gebruiken. Zo komt de kopie niet stil terug.

  python3 kopie_pa.py --klaarzetten --datum D --modus M --testrun 0 --halve 0
  python3 kopie_pa.py --proef
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

PAD = "pa_kopie.json"


def lees(pad=PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def schrijf(stand, pad=PAD):
    with open(pad, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)


def klaarzetten(datum, modus, testrun, halve, reden="", pad=PAD):
    """Na de briefrun: de modus van deze brief, en of het een halve update was."""
    oud = lees(pad)
    if testrun:
        # Een testrun verandert de stand van de echte brief niet; anders zou
        # een handrun de modus van de echte brief van die dag overschrijven.
        return oud
    stand = {"datum": datum, "modus": modus, "mag_naar_pa": not halve,
             "reden": reden if halve else "",
             "verstuurd": None, "gecorrigeerd": None}
    schrijf(stand, pad)
    return stand


def ontvangers_pa(map_=".github/workflows"):
    """Regels in workflows die pa iets kunnen mailen. Leeg is goed.

    Elke regel buiten commentaar die MAIL_TO_VERHAAL of CC_VERHAAL noemt telt:
    het secret is het adres van pa, CC_VERHAAL was de cc naar hem in de
    ochtendrun. Ook een workflow met de naam kopie_pa.yml telt, want die mag
    niet terugkomen."""
    fout = []
    for naam in sorted(os.listdir(map_)):
        if not naam.endswith((".yml", ".yaml")):
            continue
        if naam.startswith("kopie_pa."):
            fout.append(f"{naam}: de workflow voor de kopie naar pa bestaat weer")
        with open(os.path.join(map_, naam), encoding="utf-8") as f:
            for i, r in enumerate(f, 1):
                t = r.strip()
                if t.startswith("#"):
                    continue
                if re.search(r"MAIL_TO_VERHAAL|CC_VERHAAL", t):
                    fout.append(f"{naam}:{i}: {t}")
    return fout


def proef():
    import tempfile
    afw = []
    for r in ontvangers_pa():
        afw.append(f"pa kan nog een mail krijgen: {r}")
    # De wacht moet vuren op wat hij moet zien: de cc van voor 20 oktober en
    # de mailstap van kopie_pa.yml, zoals ze er werkelijk stonden.
    with tempfile.TemporaryDirectory() as m:
        with open(os.path.join(m, "a.yml"), "w", encoding="utf-8") as f:
            f.write("          # MAIL_TO_VERHAAL in commentaar telt niet\n"
                    "          cc: ${{ env.CC_VERHAAL }}\n")
        with open(os.path.join(m, "kopie_pa.yml"), "w", encoding="utf-8") as f:
            f.write("          to: ${{ secrets.MAIL_TO_VERHAAL }}\n")
        gevonden = ontvangers_pa(m)
        if len(gevonden) != 3:
            afw.append(f"de wacht op mail naar pa ziet niet alles: {gevonden}")
    with tempfile.TemporaryDirectory() as m:
        p = os.path.join(m, "pa.json")
        klaarzetten("2026-10-21", "weekelijks", False, False, pad=p)
        if lees(p).get("modus") != "weekelijks":
            afw.append("de modus wordt niet vastgelegd")
        # Een testrun laat de stand van de echte brief staan.
        klaarzetten("2026-10-21", "dagelijks", True, True, pad=p)
        if lees(p).get("modus") != "weekelijks":
            afw.append("een testrun overschrijft de modus van de echte brief")
        klaarzetten("2026-10-22", "dagelijks", False, True,
                    "het verhaal ontbreekt", pad=p)
        s = lees(p)
        if s.get("mag_naar_pa") or s.get("reden") != "het verhaal ontbreekt":
            afw.append(f"een halve update wordt niet vastgelegd: {s}")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef kopie_pa: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--klaarzetten", action="store_true")
    ap.add_argument("--datum", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--modus", default="dagelijks")
    ap.add_argument("--testrun", default="0")
    ap.add_argument("--halve", default="0")
    ap.add_argument("--reden", default="")
    a = ap.parse_args()
    if a.proef:
        return proef()
    if a.klaarzetten:
        s = klaarzetten(a.datum, a.modus, a.testrun == "1", a.halve == "1",
                        a.reden)
        print(json.dumps(s, ensure_ascii=False))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
