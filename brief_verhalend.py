#!/usr/bin/env python3
"""
Maakt een verhalende versie van de vastgoedbrief.

Zelfde bronnen als de werkbrief, maar geschreven als een brief: doorlopende
tekst, geen tabellen, cijfers in zinnen in plaats van in kolommen. Bedoeld om
rustig te lezen, niet om beslissingen mee te nemen.

Gebruik:
  python brief_verhalend.py --datum 2026-09-04 --uit digests/2026-09-04-verhaal.md
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-5"
AANHEF = os.environ.get("BRIEF_AANHEF", "Beste pa")

PROFIEL = """Je schrijft een brief over de vastgoedmarkt in Nijmegen aan een lezer van 69 jaar die de stad goed kent en zijn leven lang met vastgoed te maken heeft gehad. Hij leest de brief rustig, met tijd, en wil weten wat er speelt.

Schrijf als een brief, niet als een rapport.

VORM:
- Begin met de aanhef die je krijgt aangeleverd, gevolgd door een komma.
- Doorlopende alinea's. Geen tabellen, geen opsommingen, geen kopjes met streepjes.
- Hooguit vier of vijf alinea's, elk over één onderwerp.
- Korte zinnen. Geen vakjargon zonder uitleg. Schrijf 'de waarde die de gemeente aan een huis toekent' in plaats van alleen 'WOZ'.
- Noem straten en buurten bij naam; die kent hij.
- Geen gedachtestreepjes.
- Sluit af met een gewone zin, geen ondertekening.

INHOUD, in deze volgorde:
1. Wat er deze week opvalt aan het aanbod: welk pand, in welke straat, wat het kost en waarom het opvalt.
2. Wat de gemeente heeft besloten over concrete panden, en wat dat betekent.
3. De rente en wat die doet met de rekensom van een verhuurder.
4. Eventueel een breder marktbericht.

TOON:
- Rustig en feitelijk, zoals je een geïnteresseerde vakgenoot bijpraat.
- Geen opgewektheid die er niet is, maar ook geen somberheid. Als de cijfers tegenvallen, schrijf dat gewoon.
- Verwijs nergens naar ziekte, behandeling of gezondheid. Dit is een brief over vastgoed.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS. Gebruik alleen getallen die in de aangeleverde gegevens staan. Staat iets er niet, laat het weg."""


def lees(pad):
    """Leest een digest-bestand, of een lege string."""
    try:
        with open(pad, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def strip_opmaak(tekst, maxlen=7000):
    """Haalt tabellen en HTML eruit; het model krijgt de inhoud, niet de vorm."""
    tekst = re.sub(r"<[^>]+>", " ", tekst)
    regels = []
    for regel in tekst.split("\n"):
        r = regel.strip()
        if not r or r.startswith("|---") or set(r) <= set("|-: "):
            continue
        if r.startswith("|"):
            r = " . ".join(x.strip() for x in r.strip("|").split("|") if x.strip())
        r = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", r)   # links naar tekst
        r = r.replace("**", "").replace("_", "")
        if r:
            regels.append(r)
    return "\n".join(regels)[:maxlen]


def schrijf_brief(bronnen):
    if not ANTHROPIC_API_KEY:
        print("Geen ANTHROPIC_API_KEY", file=sys.stderr)
        return ""
    inhoud = "\n\n".join(f"=== {naam} ===\n{tekst}"
                         for naam, tekst in bronnen if tekst)
    if not inhoud.strip():
        return ""
    prompt = (f"AANHEF: {AANHEF}\n\nGEGEVENS VAN VANDAAG:\n\n{inhoud}\n\n"
              f"Schrijf de brief. Alleen de brieftekst, niets eromheen.")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 2000, "system": PROFIEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=120)
        resp.raise_for_status()
        return "".join(b.get("text", "")
                       for b in resp.json().get("content", [])).strip()
    except Exception as e:
        print(f"Brief schrijven mislukt: {e}", file=sys.stderr)
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datum", default=dt.date.today().isoformat())
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    d = args.datum

    bronnen = [
        ("Aanbod en buurten", strip_opmaak(lees(f"digests/{d}-marktprijzen.md"))),
        ("Gemeentelijke besluiten", strip_opmaak(lees(f"digests/{d}-bekendmakingen.md"))),
        ("Nieuws", strip_opmaak(lees(f"digests/{d}-publicaties.md"), 3000)),
        ("Rente", strip_opmaak(lees(f"digests/{d}-rente.md"), 2000)),
    ]
    brief = schrijf_brief(bronnen)
    if not brief:
        print("Geen brief gemaakt", file=sys.stderr)
        return

    datum_nl = dt.date.fromisoformat(d).strftime("%d %B %Y")
    for en, nl in {"January": "januari", "February": "februari", "March": "maart",
                   "April": "april", "May": "mei", "June": "juni", "July": "juli",
                   "August": "augustus", "September": "september",
                   "October": "oktober", "November": "november",
                   "December": "december"}.items():
        datum_nl = datum_nl.replace(en, nl)

    tekst = f"# Vastgoed in Nijmegen, {datum_nl}\n\n{brief}\n"
    uit = args.uit or f"digests/{d}-verhaal.md"
    os.makedirs(os.path.dirname(uit) or ".", exist_ok=True)
    with open(uit, "w", encoding="utf-8") as f:
        f.write(tekst)
    print(f"Brief weggeschreven naar {uit}", file=sys.stderr)
    print(tekst)


if __name__ == "__main__":
    main()
