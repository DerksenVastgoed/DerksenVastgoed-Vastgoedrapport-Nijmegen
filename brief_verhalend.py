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

PROFIEL = """Je schrijft een brief van Mark aan zijn vader over de vastgoedmarkt in Nijmegen. Zij kennen elkaar goed en werken allebei in vastgoed; Mark en zijn broer runnen samen Derksen Vastgoed. Zijn vader volgt de Nijmeegse markt al zijn hele leven en is oprecht nieuwsgierig naar wat er speelt.

Schrijf in de ik-vorm, alsof Mark het zelf schrijft. Spreek zijn vader aan met 'je' en 'jij', nooit met 'u'. Dat past niet bij hun manier van doen.

VORM:
- Begin met de aanhef die je krijgt aangeleverd, gevolgd door een komma.
- Doorlopende alinea's, vier tot zes stuks. Geen tabellen, geen opsommingen.
- Schrijf zoals je praat: gewone zinnen, niet te lang.
- Noem straten en buurten bij naam. Die kent hij, en dat maakt het levendig.
- Geen gedachtestreepjes.
- Sluit af met een gewone zin over iets waar je benieuwd naar bent of wat je volgende week verwacht. Geen ondertekening, geen vraag om een reactie.

GEEN VAKJARGON. Deze woorden gebruik je niet: LTV, basispunten, cashflow, mediaan, yield, box 3, WWS, WOZ, forfait, rendement op eigen vermogen. Schrijf in plaats daarvan:
- LTV of loan-to-value: 'als je twee derde leent'
- basispunten: gewoon procenten
- cashflow: 'wat er onder de streep overblijft'
- mediaan: 'het gemiddelde' of 'wat vergelijkbare panden doen'
- WOZ: 'de waarde die de gemeente aan het huis toekent'
- box 3: 'de belasting op vermogen'
- puntenstelsel of WWS: 'het puntenstelsel dat bepaalt wat je maximaal aan huur mag vragen'

INHOUD, in deze volgorde:
1. Wat er deze week te koop staat dat de moeite waard is om te volgen voor Derksen Vastgoed. Niet als koopadvies, maar als iets om in de gaten te houden.
2. Wat de gemeente heeft besloten over concrete panden in de stad, en wat dat zegt over waar het heen gaat.
3. De rente, en in gewone taal wat dat betekent voor iemand die verhuurt.
4. Eventueel iets breders uit het nieuws, als het echt iets toevoegt.

TOON:
- Rustig, feitelijk en persoonlijk. Zoals je iemand bijpraat die het vak kent maar er even niet middenin zit.
- Geen opgewektheid die er niet is. Vallen de cijfers tegen, schrijf dat gewoon.
- Verwijs nergens naar ziekte, behandeling of gezondheid. Dit is een brief over vastgoed.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS. Alleen getallen die in de aangeleverde gegevens staan. Staat iets er niet, laat het weg."""


def render_bijlage():
    """
    Cijfers per buurt en het actuele aanbod, als bijlage onder de brief.
    Dit is materiaal om rustig doorheen te bladeren, niet om te beslissen.
    """
    def lees_json(pad):
        try:
            with open(pad, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    cbs = lees_json("buurten_cbs.json")
    verg = lees_json("vergunningen_per_buurt.json")
    if not cbs:
        return ""

    volgorde = ["Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
                "Altrade", "Biezen"]

    def n(x):
        return f"{int(x):,}".replace(",", ".")

    regels = ["", "## De buurten in cijfers", "",
              "_Ter aanvulling, om eens rustig door te kijken._", ""]
    for buurt in volgorde:
        g = cbs.get(buurt)
        if not g:
            continue
        zinnen = []
        eerste = f"**{buurt}** telt {n(g['won'])} woningen"
        if g.get("koop") is not None:
            eerste += (f", waarvan {g['koop']} procent koopwoning is en "
                       f"{g.get('corp', 0)} procent van een woningcorporatie")
        zinnen.append(eerste + ".")

        if g.get("meergezins") is not None:
            zin = f"{g['meergezins']} procent van de voorraad is appartement"
            if g.get("woz"):
                zin += (f", en een huis is er volgens de gemeente gemiddeld "
                        f"{n(g['woz'] * 1000)} euro waard")
            zinnen.append(zin + ".")
        elif g.get("woz"):
            zinnen.append(f"Een huis is er volgens de gemeente gemiddeld "
                          f"{n(g['woz'] * 1000)} euro waard.")

        if g.get("studenten") and g.get("inwoners"):
            aandeel = round(g["studenten"] / g["inwoners"] * 100)
            zinnen.append(f"Er wonen {n(g['studenten'])} studenten, ongeveer "
                          f"{aandeel} van elke honderd inwoners.")

        v = verg.get(buurt)
        if v and g.get("won"):
            zinnen.append(f"Sinds 2013 zijn er {v} vergunningen voor kamerverhuur "
                          f"verleend, dat is "
                          + f"{v / g['won'] * 100:.1f}".replace(".", ",")
                          + " procent van "
                          f"alle woningen daar.")
        regels.append(" ".join(zinnen))
        regels.append("")
    return "\n".join(regels)


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
    bijlage = render_bijlage()
    if bijlage:
        tekst += "\n" + bijlage
    uit = args.uit or f"digests/{d}-verhaal.md"
    os.makedirs(os.path.dirname(uit) or ".", exist_ok=True)
    with open(uit, "w", encoding="utf-8") as f:
        f.write(tekst)
    print(f"Brief weggeschreven naar {uit}", file=sys.stderr)
    print(tekst)


if __name__ == "__main__":
    main()
