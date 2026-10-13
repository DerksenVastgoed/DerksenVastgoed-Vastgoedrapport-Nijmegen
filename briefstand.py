#!/usr/bin/env python3
"""
Vastleggen of de brief van vandaag werkelijk opnieuw is geschreven.

WAAROM DIT EEN EIGEN BESTAND IS. Dit stond als drie python -c regels in de
workflow, en de reden van een mislukking kwam daarin niet terug. Op 13 oktober
mislukte het schrijven in de run van 08:46: de stand zei "het schrijven
mislukte" en verder niets. Waarom het mislukte stond alleen in het joblogboek
van GitHub, en dat zit achter results-receiver.actions.githubusercontent.com,
die van buiten de runner wordt geweigerd. Er was dus niets te onderzoeken.

Daarom gaat de staart van het logboek van die stap mee in briefstand.json, en
komt die via het gezondheidsrapport in de bijlage die elke ochtend meegaat.
Diagnose en bezorging mogen niet hetzelfde kanaal delen, en een logboek dat
alleen op de runner bestaat is geen kanaal.

Gebruik:
  python briefstand.py --reden "..." --log /tmp/verhaal.log
  python briefstand.py --geschreven
  python briefstand.py --proef
"""
import argparse
import datetime as dt
import json
import sys

PAD = "briefstand.json"
REGELS_UIT_LOG = 8
MAX_TEKENS = 1500


def staart_van(pad, regels=REGELS_UIT_LOG, tekens=MAX_TEKENS):
    """
    De laatste betekenisvolle regels van een logboek, als een regel tekst.

    Lege regels vallen weg, want een stap die afbreekt laat er vaak tien
    achter en dan bestaat de staart daaruit. Bij een onleesbaar bestand staat
    er wat er mis was en niet een leeg veld: "niet gekeken" en "gekeken en
    niets gevonden" mogen niet hetzelfde opleveren.
    """
    try:
        with open(pad, encoding="utf-8", errors="replace") as f:
            gevuld = [r.rstrip() for r in f if r.strip()]
    except FileNotFoundError:
        return f"geen logboek op {pad}"
    except Exception as e:
        return f"logboek niet te lezen: {type(e).__name__}"
    if not gevuld:
        return f"logboek {pad} is leeg"
    return " | ".join(gevuld[-regels:])[:tekens]


def stand(geschreven, reden="", log=None, vandaag=None):
    """De stand als dict, met de logstaart alleen als het misging."""
    uit = {"datum": (vandaag or dt.date.today()).isoformat(),
           "opnieuw_geschreven": bool(geschreven),
           "reden": reden or ""}
    if not geschreven:
        uit["logstaart"] = staart_van(log) if log else "geen logboek opgegeven"
    return uit


def proef():
    """Nameten wat deze module belooft, zonder iets weg te schrijven."""
    import os
    import tempfile
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # Een geslaagde brief draagt geen logstaart: er is niets te onderzoeken.
    goed = stand(True, vandaag=dt.date(2026, 10, 13))
    check("geslaagd, datum", goed["datum"], "2026-10-13")
    check("geslaagd, geschreven", goed["opnieuw_geschreven"], True)
    if "logstaart" in goed:
        fouten.append("een geslaagde brief krijgt toch een logstaart")

    # Een mislukte brief draagt de staart van het logboek.
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                     encoding="utf-8") as f:
        pad = f.name
        f.write("eerste regel\n\n\n")
        for n in range(1, 13):
            f.write(f"regel {n}\n")
        f.write("\n")
    mis = stand(False, "het schrijven mislukte", log=pad,
                vandaag=dt.date(2026, 10, 13))
    check("mislukt, geschreven", mis["opnieuw_geschreven"], False)
    if "regel 12" not in mis["logstaart"]:
        fouten.append(f"de laatste regel staat niet in de staart: "
                      f"{mis['logstaart']!r}")
    if "regel 4" in mis["logstaart"]:
        fouten.append(f"de staart is langer dan {REGELS_UIT_LOG} regels: "
                      f"{mis['logstaart']!r}")
    if "" in mis["logstaart"].split(" | "):
        fouten.append("lege regels staan in de staart")
    os.remove(pad)

    # DRIE KEER NIETS IS NIET HETZELFDE. Een ontbrekend bestand, een leeg
    # bestand en geen opgave moeten elk hun eigen tekst geven, anders is niet
    # te zien of er niet gekeken is of niets gevonden.
    zonder = stand(False, "x")["logstaart"]
    weg = stand(False, "x", log="/tmp/bestaat-niet-12345.log")["logstaart"]
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        leeg_pad = f.name
    leeg = stand(False, "x", log=leeg_pad)["logstaart"]
    os.remove(leeg_pad)
    if len({zonder, weg, leeg}) != 3:
        fouten.append(f"niet-gekeken, niet-gevonden en leeg geven niet drie "
                      f"verschillende teksten: {zonder!r} {weg!r} {leeg!r}")

    # Een heel lang logboek mag het bestand niet laten groeien.
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                     encoding="utf-8") as f:
        lang_pad = f.name
        for n in range(50):
            f.write("x" * 400 + "\n")
    lang = stand(False, "x", log=lang_pad)["logstaart"]
    if len(lang) > MAX_TEKENS:
        fouten.append(f"de staart is {len(lang)} tekens, hoogstens "
                      f"{MAX_TEKENS}")
    os.remove(lang_pad)

    print(f"Proef briefstand: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geschreven", action="store_true",
                    help="de brief is door deze run opnieuw geschreven")
    ap.add_argument("--reden", default="",
                    help="waarom hij niet opnieuw is geschreven")
    ap.add_argument("--log", default="",
                    help="logboek van de stap; de staart gaat mee in de stand")
    ap.add_argument("--uit", default=PAD)
    ap.add_argument("--proef", action="store_true")
    args = ap.parse_args()
    if args.proef:
        return proef()
    uit = stand(args.geschreven, args.reden, args.log or None)
    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False, indent=1)
    print(f"Briefstand: opnieuw geschreven = {uit['opnieuw_geschreven']}"
          + (f"; {uit['reden']}" if uit["reden"] else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): zonder dit geeft het proces altijd 0 terug, ook
    # als de proef rood staat, en is de poort in de workflow een formaliteit.
    sys.exit(main())
