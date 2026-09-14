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
import time

import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-5"
# Let op: een secret dat bestaat maar leeg is, geeft een lege tekst terug en
# niet de standaardwaarde. Vandaar de or in plaats van een default.
AANHEF = (os.environ.get("BRIEF_AANHEF") or "").strip() or "Beste pa"

PROFIEL = """Je schrijft een lange brief van Mark aan zijn vader over de vastgoedmarkt in Nijmegen. Zij kennen elkaar goed en werken allebei in vastgoed; Mark en zijn broer runnen samen Derksen Vastgoed. Zijn vader volgt de Nijmeegse markt al zijn hele leven.

Hij heeft ruim de tijd om te lezen. Schrijf dus uitgebreid: liever te veel dan te weinig. Maar het moet wel prettig blijven lezen, dus doorlopende tekst en geen opsommingen van kale cijfers.

Schrijf in de ik-vorm. Spreek hem aan met 'je' en 'jij', nooit met 'u'.

OPBOUW:

1. Een korte opening over wat er deze week het meest opvalt.

2. Dan de buurten. LET OP: deze brief komt elke dag, dus herhaal niet elke dag dezelfde beschrijving van alle buurten. Werk zo:

   - Buurten WAAR IETS GEBEURT (een pand dat opvalt, een prijswijziging, een gemeentelijk besluit) krijgen een eigen kopje en een paar alinea's. Noem de panden bij naam met vraagprijs en oppervlakte, schrijf of dat duur of goedkoop is voor die buurt, en behoud de links precies zoals ze in de gegevens staan, in de vorm [naam](adres).

   - Voor de overige buurten schrijf je GEEN apart kopje en GEEN beschrijving. Vat ze samen in één of twee zinnen, bijvoorbeeld: in de andere buurten gebeurde deze week niets, met de prijs per meter tussen X en Y.

   - Je krijgt de aanwijzing BUURT VAN DE DAG mee. Geef ALLEEN die ene buurt een achtergrondportret van een paar zinnen: wat voor buurt het is, wie er woont, wat men er verdient en bezit, hoe het staat met inbraak, vernieling en overlast. Kies de drie of vier cijfers die het meest zeggen. De andere buurten krijgen dat portret vandaag niet; die komen een andere dag aan de beurt.

   - Ligt het aanbod stil en is er geen nieuws, houd de brief dan kort. Een korte brief is beter dan een lange die niets nieuws zegt.

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

    # Niet op de datum vertrouwen maar bijhouden wat er al geweest is. Een
    # rekentruc met het dagnummer gaat mis zodra de lijst van lengte verandert,
    # en dan zie je hetzelfde weetje dagen achter elkaar.
    pad = "weetjes_gezien.json"
    try:
        with open(pad, encoding="utf-8") as fh:
            gezien = json.load(fh)
    except Exception:
        gezien = []

    nieuw = [w for w in weetjes if w not in gezien]
    if not nieuw:          # alles geweest: de ronde begint opnieuw
        gezien, nieuw = [], weetjes
    keuze = nieuw[0]

    gezien.append(keuze)
    # Alleen de laatste ronde onthouden, anders groeit het bestand eindeloos
    gezien = gezien[-max(len(weetjes), 1):]
    try:
        with open(pad, "w", encoding="utf-8") as fh:
            json.dump(gezien, fh, ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"Kon {pad} niet schrijven: {e}", file=sys.stderr)
    print(f"Weetje {len(gezien)} van {len(weetjes)}: {keuze[:60]}", file=sys.stderr)
    return keuze



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
    try:
        with open("misdrijven_per_buurt.json", encoding="utf-8") as f:
            misdrijven = json.load(f)
    except Exception:
        misdrijven = {}

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

        # Wie er woont, wat ze verdienen en bezitten
        if g.get("eenpersoons") is not None:
            d.append(f"{g['eenpersoons']}% woont alleen")
        if g.get("met_kinderen") is not None:
            d.append(f"{g['met_kinderen']}% van de huishoudens heeft kinderen")
        if g.get("huishoudgrootte"):
            d.append(f"gemiddeld {g['huishoudgrootte']} personen per huishouden")
        if g.get("inkomen"):
            d.append(f"gemiddeld inkomen {g['inkomen'] * 1000} euro per inwoner")
        if g.get("vermogen") is not None:
            d.append(f"mediaan vermogen {g['vermogen'] * 1000} euro per huishouden")
        if g.get("laag_inkomen") is not None:
            d.append(f"{g['laag_inkomen']}% met een laag inkomen")

        # Misdrijven, afgezet tegen het aantal inwoners
        mis = misdrijven.get(buurt)
        if mis:
            jaren = sorted(mis)
            laatst = mis[jaren[-1]]
            per = []
            for soort in ("woninginbraak", "vernieling", "drugs- en drankoverlast",
                          "fietsendiefstal"):
                n = laatst.get(soort)
                if n is None:
                    continue
                tekst = f"{n} {soort}"
                if g.get("inwoners"):
                    tekst += f" ({n / g['inwoners'] * 1000:.1f} per 1000 inwoners)"
                per.append(tekst)
            if per:
                d.append(f"misdrijven in {jaren[-1][:4]}: " + ", ".join(per))
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



AANHEF_WOORDEN = ("beste", "hoi", "hallo", "dag", "lieve", "pa", "pap", "papa",
                  "vader", "hey", "hé")


# De afsluiting kan op een of twee regels staan: "Groet, Mark" maar ook
# "Met vriendelijke groet," met de naam eronder.
ONDERTEKENING = re.compile(
    r"\n+\s*(?:met vriendelijke groet(?:en)?|met hartelijke groet(?:en)?|"
    r"groet(?:en)?|hartelijke groet(?:en)?|tot (?:morgen|volgende week|zondag|snel)|"
    r"liefs|hoogachtend|vriendelijke groet(?:en)?)\b[^\n]*"
    r"(?:\n[^\n]{0,40})?\s*$",
    re.IGNORECASE)


def haal_ondertekening_weg(brief):
    """
    Het model zet er soms toch een ondertekening onder. Die hoort er niet:
    de mail komt van Mark, dus zijn naam eronder is dubbelop.
    """
    vorige = None
    while brief != vorige:
        vorige = brief
        brief = ONDERTEKENING.sub("", brief).rstrip()
    return brief


def zet_aanhef(brief, aanhef):
    """
    Vervangt de aanhef door de ingestelde. Het model neemt de opgegeven aanhef
    niet altijd letterlijk over en maakt er soms Pap of Beste vader van; dat is
    niet aan het model om te bepalen.
    """
    if not brief:
        return brief
    regels = brief.split("\n")
    # Zoek de eerste niet-lege regel; is dat een aanhef, dan vervangen we hem
    for i, regel in enumerate(regels):
        if not regel.strip():
            continue
        kaal = regel.strip()
        eerste = kaal.rstrip(",.!").lower()
        # Een lege of bijna lege eerste regel is een mislukte aanhef: het model
        # kreeg een lege aanhef aangeleverd en zette alleen de komma neer.
        if len(eerste) <= 1:
            regels[i] = f"{aanhef},"
            return "\n".join(regels)
        kort = len(eerste.split()) <= 4
        if kort and any(eerste.startswith(w) for w in AANHEF_WOORDEN):
            regels[i] = f"{aanhef},"
            return "\n".join(regels)
        # Geen aanhef gevonden: we zetten hem er alsnog voor
        return f"{aanhef},\n\n" + brief
    return brief


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
    # Elke dag krijgt een andere buurt het achtergrondportret, zodat de brief
    # niet elke ochtend dezelfde zes beschrijvingen herhaalt.
    ronde = ["Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
             "Altrade", "Biezen"]
    buurt_vandaag = ronde[dt.date.today().toordinal() % len(ronde)]
    prompt = (f"AANHEF: {AANHEF}\n"
              f"BUURT VAN DE DAG: {buurt_vandaag}\n\n"
              f"GEGEVENS VAN VANDAAG:\n\n{inhoud}\n\n"
              f"Schrijf de brief. Alleen de brieftekst, niets eromheen.")
    # Een lange brief schrijven duurt; twee minuten was te krap. Drie pogingen
    # met ruime wachttijd, want dit is de enige stap die de brief oplevert.
    resp = None
    for poging in range(1, 4):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 16000, "system": PROFIEL,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=(30, 600))
            resp.raise_for_status()
            break
        except Exception as e:
            if poging == 3:
                print(f"Brief schrijven mislukt na 3 pogingen: {e}", file=sys.stderr)
                return ""
            print(f"  poging {poging} mislukt ({e}), opnieuw", file=sys.stderr)
            time.sleep(poging * 10)
    try:
        body = resp.json()
        tekst = "".join(b.get("text", "")
                        for b in body.get("content", [])).strip()
        reden = body.get("stop_reason")
        if reden == "max_tokens":
            print("LET OP: de brief is afgekapt omdat de limiet is bereikt. "
                  "Verhoog max_tokens in dit bestand.", file=sys.stderr)
        gebruikt = (body.get("usage") or {}).get("output_tokens")
        if gebruikt:
            print(f"Brief geschreven: {gebruikt} tokens, "
                  f"{len(tekst.split())} woorden", file=sys.stderr)
        return tekst
    except Exception as e:
        print(f"Antwoord verwerken mislukt: {e}", file=sys.stderr)
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
    brief = zet_aanhef(haal_ondertekening_weg(schrijf_brief(bronnen) or ""), AANHEF)
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
