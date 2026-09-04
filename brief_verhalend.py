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

PROFIEL = """Je schrijft een lange brief van Mark aan zijn vader over de vastgoedmarkt in Nijmegen. Zij kennen elkaar goed en werken allebei in vastgoed; Mark en zijn broer runnen samen Derksen Vastgoed. Zijn vader volgt de Nijmeegse markt al zijn hele leven.

Hij heeft ruim de tijd om te lezen. Schrijf dus uitgebreid: liever te veel dan te weinig. Maar het moet wel prettig blijven lezen, dus doorlopende tekst en geen opsommingen van kale cijfers.

Schrijf in de ik-vorm. Spreek hem aan met 'je' en 'jij', nooit met 'u'.

OPBOUW:

1. Een korte opening over wat er deze week het meest opvalt.

2. Dan **per buurt een eigen kopje** met de buurtnaam. Neem alle buurten waarover gegevens zijn. Behandel per buurt:
   - Een paar zinnen over wat voor buurt het is, met de cijfers erin verweven: hoeveel woningen, de verhouding koop en corporatiebezit, het aandeel appartementen, wat een huis er waard is volgens de gemeente, hoeveel studenten er wonen. Niet als lijstje maar als verhaal.
   - Welke panden er te koop staan. Noem ze bij naam met de vraagprijs en de oppervlakte, en schrijf erbij of dat duur of goedkoop is voor die buurt en waarom. Behoud de links precies zoals ze in de gegevens staan, in de vorm [naam](adres), zodat hij kan doorklikken.
   - Wat de gemeente over panden in die buurt heeft besloten, en wat dat zegt.
   Sla een buurt over als er niets over te melden is.

3. Een stuk over de rente en wat die betekent voor iemand die verhuurt.

4. Een stuk over het nieuws, met de artikelen bij naam genoemd en de links behouden zoals ze zijn.

5. Een slotalinea over wat je volgende week verwacht of waar je benieuwd naar bent.

LINKS: laat elke link staan in de vorm [tekst](https://...). Verzin nooit een link en verander geen adres.

GEEN VAKJARGON. Deze woorden gebruik je niet: LTV, basispunten, cashflow, mediaan, yield, box 3, WWS, WOZ, forfait, richtprijs. Schrijf in plaats daarvan:
- LTV: 'als je twee derde leent'
- basispunten: gewoon procenten
- cashflow: 'wat er onder de streep overblijft'
- mediaan: 'wat vergelijkbare panden doen'
- WOZ: 'de waarde die de gemeente aan het huis toekent'
- box 3: 'de belasting op vermogen'
- richtprijs: 'de prijs waarbij het zichzelf nog net rondbetaalt'
- puntenstelsel of WWS: 'het puntenstelsel dat bepaalt wat je maximaal aan huur mag vragen'

TOON:
- Rustig, feitelijk en persoonlijk. Zoals je iemand bijpraat die het vak kent.
- Geen opgewektheid die er niet is. Vallen de cijfers tegen, schrijf dat gewoon.
- Verwijs nergens naar ziekte, behandeling of gezondheid. Dit is een brief over vastgoed.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS. Alleen getallen die in de aangeleverde gegevens staan."""


def wist_je_dat(cbs, verg):
    """
    Elke dag een ander weetje uit de eigen cijfers. Rouleert op dagnummer,
    zodat het niet elke ochtend hetzelfde is.
    """
    def n(x):
        return f"{int(x):,}".replace(",", ".")

    def pct(x, cijfers=1):
        return f"{x:.{cijfers}f}".replace(".", ",")

    weetjes = []
    buurten = [b for b in cbs if not b.startswith("_")]

    # Verkameringsgraad
    met_verg = [(b, verg[b], cbs[b]["won"]) for b in buurten
                if verg.get(b) and cbs[b].get("won")]
    for b, v, won in sorted(met_verg, key=lambda x: -x[1] / x[2])[:3]:
        weetjes.append(f"in {b} {pct(v / won * 100)} procent van alle woningen een "
                       f"vergunning voor kamerverhuur heeft, {v} stuks op {n(won)} "
                       f"woningen")

    # Studentendichtheid
    met_stud = [(b, cbs[b]["studenten"], cbs[b]["inwoners"]) for b in buurten
                if cbs[b].get("studenten") and cbs[b].get("inwoners")]
    for b, st_, inw in sorted(met_stud, key=lambda x: -x[1] / x[2])[:2]:
        weetjes.append(f"in {b} bijna {round(st_ / inw * 100)} van elke honderd "
                       f"inwoners student is")
    totaal_stud = sum(x[1] for x in met_stud)
    if met_stud and totaal_stud:
        b, st_, _ = max(met_stud, key=lambda x: x[1])
        weetjes.append(f"{round(st_ / totaal_stud * 100)} procent van alle studenten "
                       f"in de ring in {b} woont")

    # Eigendomsverhouding
    for b in buurten:
        g = cbs[b]
        if g.get("corp", 0) >= 40:
            weetjes.append(f"in {b} {g['corp']} procent van de woningen van een "
                           f"woningcorporatie is, meer dan waar ook in de ring")
        if g.get("meergezins", 0) >= 90:
            weetjes.append(f"{g['meergezins']} procent van alle woningen in {b} een "
                           f"appartement is")
        if g.get("koop", 100) <= 15:
            weetjes.append(f"in {b} maar {g['koop']} procent van de woningen een "
                           f"koopwoning is")

    if not weetjes:
        return ""
    return weetjes[dt.date.today().toordinal() % len(weetjes)]



def buurtcijfers_tekst():
    """De buurtcijfers als platte regels, zodat het model ze kan verwerken."""
    try:
        with open("buurten_cbs.json", encoding="utf-8") as f:
            cbs = json.load(f)
    except Exception:
        return ""
    try:
        with open("vergunningen_per_buurt.json", encoding="utf-8") as f:
            verg = json.load(f)
    except Exception:
        verg = {}

    regels = []
    for buurt in ("Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
                  "Altrade", "Biezen"):
        g = cbs.get(buurt)
        if not g:
            continue
        d = [f"{buurt}: {g.get('won')} woningen"]
        if g.get("koop") is not None:
            d.append(f"{g['koop']}% koop")
        if g.get("corp") is not None:
            d.append(f"{g['corp']}% woningcorporatie")
        if g.get("meergezins") is not None:
            d.append(f"{g['meergezins']}% appartement")
        if g.get("woz"):
            d.append(f"gemiddelde waarde volgens de gemeente "
                     f"{g['woz'] * 1000} euro")
        if g.get("studenten"):
            d.append(f"{g['studenten']} studenten")
        if g.get("inwoners"):
            d.append(f"{g['inwoners']} inwoners")
        if verg.get(buurt):
            d.append(f"{verg[buurt]} vergunningen voor kamerverhuur sinds 2013")
        regels.append(", ".join(d))
    return "\n".join(regels)


def weetje_van_de_dag():
    """Een weetje onder de brief, dat elke dag rouleert."""
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
    return wist_je_dat(cbs, verg)


def lees(pad):
    """Leest een digest-bestand, of een lege string."""
    try:
        with open(pad, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def strip_opmaak(tekst, maxlen=14000):
    """Haalt tabellen en HTML eruit; het model krijgt de inhoud, niet de vorm."""
    tekst = re.sub(r"<[^>]+>", " ", tekst)
    regels = []
    for regel in tekst.split("\n"):
        r = regel.strip()
        if not r or r.startswith("|---") or set(r) <= set("|-: "):
            continue
        if r.startswith("|"):
            r = " . ".join(x.strip() for x in r.strip("|").split("|") if x.strip())
        # Links laten staan: de lezer moet kunnen doorklikken naar het artikel
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
            json={"model": MODEL, "max_tokens": 8000, "system": PROFIEL,
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
        ("Cijfers per buurt", buurtcijfers_tekst()),
        ("Aanbod en buurten", strip_opmaak(lees(f"digests/{d}-marktprijzen.md"))),
        ("Gemeentelijke besluiten", strip_opmaak(lees(f"digests/{d}-bekendmakingen.md"))),
        ("Nieuws", strip_opmaak(lees(f"digests/{d}-publicaties.md"), 6000)),
        ("Rente", strip_opmaak(lees(f"digests/{d}-rente.md"), 3000)),
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
    weetje = weetje_van_de_dag()
    if weetje:
        tekst += f"\n---\n\n**Wist je dat** {weetje}?\n"
    uit = args.uit or f"digests/{d}-verhaal.md"
    os.makedirs(os.path.dirname(uit) or ".", exist_ok=True)
    with open(uit, "w", encoding="utf-8") as f:
        f.write(tekst)
    print(f"Brief weggeschreven naar {uit}", file=sys.stderr)
    print(tekst)


if __name__ == "__main__":
    main()
