#!/usr/bin/env python3
"""
Geplakte Kamernet-tekst omzetten naar huurwaarnemingen.

Kamernet laat zich niet automatisch uitlezen, maar de tekst van de pagina is zo
geplakt. Zet de tekst in kamernet_plak.txt; dit script haalt er de advertenties
uit en zet ze in verkopen.txt, in hetzelfde formaat als de attenderingsmails.

Wat er gebeurt met wat erin staat:
- alleen Nijmegen; Arnhem, Lent, Groesbeek, Elst, Weurt en Zetten vallen af;
- een kamer met een oppervlakte van het hele huis (100 m2 voor 455 euro) valt
  af op de bestaande grenzen in marktprijzen_bag.py;
- "incl." wordt vastgelegd in de bron, want inclusief servicekosten is iets
  anders dan kale huur. Op de kamermarkt is inclusief eerder regel dan
  uitzondering, dus we gooien ze niet weg maar houden ze apart.

Gebruik:
  python kamernet_plak.py
"""

import datetime as dt
import os
import re
import sys

PLAK_PAD = "kamernet_plak.txt"
UIT_PAD = "verkopen.txt"
PLAATS = "Nijmegen"

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass

# "Kamer te huur 733 euro Polderstraat, Nijmegen"
KOP = re.compile(r"^(Kamer|Appartement|Studio|Woonhuis)\s+te huur\s+([\d.]+)\s*euro\s+(.+?),\s*(.+)$",
                 re.I)
OPP = re.compile(r"^(\d{1,4})\s*m²?$")
PRIJS = re.compile(r"^€\s*([\d.]+)")


def parse(tekst):
    """De advertenties uit de geplakte tekst, in volgorde van de pagina."""
    regels = [r.strip() for r in tekst.split("\n")]
    uit, huidig = [], None
    for regel in regels:
        kop = KOP.match(regel)
        if kop:
            if huidig:
                uit.append(huidig)
            soort, _prijs_kop, straat, plaats = kop.groups()
            huidig = {"soort": soort.lower(), "straat": straat.strip(),
                      "plaats": plaats.strip(), "opp": None, "prijs": None,
                      "incl": False, "staat": ""}
            continue
        if not huidig:
            continue
        m = OPP.match(regel)
        if m:
            huidig["opp"] = int(m.group(1))
            continue
        if regel.lower() in ("kaal", "gestoffeerd", "gemeubileerd"):
            huidig["staat"] = regel.lower()
            continue
        p = PRIJS.match(regel)
        if p and huidig["prijs"] is None:
            huidig["prijs"] = int(p.group(1).replace(".", ""))
            continue
        if "incl" in regel.lower() and "maand" in regel.lower():
            huidig["incl"] = True
    if huidig:
        uit.append(huidig)
    return uit


def naar_regels(advertenties, datum):
    """Van advertentie naar een regel voor verkopen.txt."""
    regels, overgeslagen = [], {"plaats": 0, "onvolledig": 0}
    for a in advertenties:
        if a["plaats"].lower() != PLAATS.lower():
            overgeslagen["plaats"] += 1
            continue
        if not a["prijs"] or not a["opp"] or not a["straat"]:
            overgeslagen["onvolledig"] += 1
            continue
        status = "te huur kamer" if a["soort"] == "kamer" else "te huur"
        # De staat van oplevering hoort in de bron: gemeubileerd is een andere
        # markt dan kaal, en inclusief servicekosten is geen kale huur.
        bron = "kamernet"
        if a["staat"]:
            bron += f"-{a['staat']}"
        if a["incl"]:
            bron += "-incl"
        regels.append(f"{a['straat']} | {PLAATS} | {a['prijs']} | {status} | "
                      f"{datum} | {bron} | {a['opp']} | ")
    return regels, overgeslagen


def bestaande(pad):
    if not os.path.exists(pad):
        return set()
    with open(pad, encoding="utf-8") as f:
        return {r.strip() for r in f if r.strip()}


def main():
    wis("kamernet")
    if not os.path.exists(PLAK_PAD):
        print(f"{PLAK_PAD} staat er niet; niets te doen", file=sys.stderr)
        return
    with open(PLAK_PAD, encoding="utf-8") as f:
        tekst = f.read()
    if not tekst.strip():
        print("Plakbestand is leeg", file=sys.stderr)
        return

    advertenties = parse(tekst)
    datum = dt.date.today().isoformat()
    regels, overgeslagen = naar_regels(advertenties, datum)
    if not regels:
        leg_vast("kamernet", f"Uit {PLAK_PAD} kwam geen enkele bruikbare "
                             f"advertentie ({len(advertenties)} gevonden). Is de "
                             f"opmaak van de pagina veranderd?")
        print("Geen bruikbare advertenties", file=sys.stderr)
        return

    al_bekend = bestaande(UIT_PAD)
    # Zelfde straat, prijs en oppervlakte op een andere dag is dezelfde
    # advertentie; alleen de datum verschilt. Daarop ontdubbelen we.
    kern = {"|".join(r.split("|")[:4] + [r.split("|")[6]]) for r in al_bekend
            if r.count("|") >= 6}
    nieuw = [r for r in regels
             if "|".join(r.split("|")[:4] + [r.split("|")[6]]) not in kern]
    if nieuw:
        with open(UIT_PAD, "a", encoding="utf-8") as f:
            f.write("\n".join(nieuw) + "\n")
    print(f"Kamernet: {len(advertenties)} advertenties gelezen, {len(regels)} in "
          f"{PLAATS}, {len(nieuw)} nieuw toegevoegd. Overgeslagen: "
          f"{overgeslagen['plaats']} buiten {PLAATS}, "
          f"{overgeslagen['onvolledig']} onvolledig.", file=sys.stderr)
    kaal = sum(1 for r in nieuw if "-incl" not in r)
    print(f"  waarvan {kaal} met een kale huur en {len(nieuw) - kaal} inclusief",
          file=sys.stderr)


if __name__ == "__main__":
    main()
