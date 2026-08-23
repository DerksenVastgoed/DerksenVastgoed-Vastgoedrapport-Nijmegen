#!/usr/bin/env python3
"""
Publicaties-blok voor de Nijmegen Vastgoedmonitor.

Haalt recente artikelen op uit RSS-feeds van vastgoedbronnen, filtert op
relevantie voor de Nijmeegse beleggingsmarkt, en genereert per bericht een samenvatting
met vertaling naar de portefeuille.

Zonder ANTHROPIC_API_KEY werkt alles gewoon, alleen zonder de duiding-zin.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

# --- CONFIG ---
# Google News RSS-feeds. Elke zoekopdracht = 1 feed. Robuust en actueel.
# Format: news.google.com/rss/search?q=<query>&hl=nl&gl=NL&ceid=NL:nl
def _gnews(q):
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(q)}&hl=nl&gl=NL&ceid=NL:nl"

FEEDS = [
    # Markt en beleid
    ("Woningmarkt NL", _gnews("Nederlandse woningmarkt")),
    ("Wet betaalbare huur", _gnews('"wet betaalbare huur" OR "WWS"')),
    ("Particuliere verhuur", _gnews("verhuurders OR particuliere huursector")),
    ("Box 3 vastgoed", _gnews('"box 3" vastgoed')),
    ("Uitponden", _gnews("uitponden OR uitpondstrategie OR leegwaarde")),
    # Regio
    ("Vastgoed Gelderland", _gnews("vastgoed Nijmegen OR Arnhem OR Gelderland")),
    # Verduurzaming
    ("Verduurzaming huur", _gnews("verduurzaming huurwoning OR energielabel verhuur")),
    # Financiering
    ("Rente vastgoed", _gnews("hypotheekrente OR verhuurhypotheek")),
    # Kwartaal-updates van grote spelers (vangen automatisch nieuwe rapporten)
    ("Brainbay Woningwaarde-index", _gnews("Brainbay OR NVM woningmarktcijfers")),
    ("Pararius huurmarkt", _gnews("Pararius huurprijs OR huurmarkt")),
    ("Rabobank Woningmarkt", _gnews("Rabobank woningmarkt kwartaalbericht")),
    ("ABN AMRO Woningmarkt", _gnews("ABN AMRO woningmarkt sector update")),
    # Directe RSS van Vastgoed Insider (schrijft vaak relevant over uitponden/beleggers)
    ("Vastgoed Insider", "https://vastgoedinsider.nl/feed/"),
    ("Vastgoed Insider (Google News)", _gnews("site:vastgoedinsider.nl")),
]

TREFWOORDEN = [
    "woningmarkt", "verhuur", "verhuurders", "huurwoning", "koopwoning",
    "particuliere verhuur", "belegger", "beleggers", "uitpond", "uitponding",
    "corporatie", "corporaties", "woningcorporatie",
    "prijsontwikkeling", "huizenprijzen", "huurprijs", "huurprijzen",
    "wws", "woningwaardering", "wet betaalbare huur",
    "box 3", "box3", "overdrachtsbelasting",
    "opkoopbescherming", "huurbescherming",
    "energielabel", "verduurzaming", "isolatie", "warmtepomp", "warmtenet",
    "nijmegen", "arnhem-nijmegen", "arnhem", "gelderland",
    "dynamis", "capital value", "nvm", "brainbay", "pararius", "rabobank", "abn amro", "woningmarktcijfers", "woningwaarde", "kwartaalbericht", "sector update",
    "abn amro woningmarkt", "rabobank woningmarkt", "dnb",
]

MAX_LEEFTIJD_UREN = 30
MAX_ITEMS_LLM = 15
HISTORIE_PAD = "publicaties_gezien.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-5"
PROFIEL = """Je bent vastgoedanalist voor een marktbrief over de binnenring van Nijmegen. Lezers zijn particuliere vastgoedinvesteerders en kleine ontwikkelaars. Denk als MSRE-professional, schrijf toegankelijk.

Marktcontext (referentiepand in dit segment): waarde circa €1,5M, hypotheek €1M rond 5,75%, kale huur circa €67.500/jaar. Na 25% opex is de cashflow ongeveer nul. Rendement komt niet uit huur maar uit waardecreatie: uitponden, splitsen, renoveren bij mutatie, functie omzetten.

Je krijgt titels en samenvattingen van vastgoedpublicaties. Voor elk:
1. "relevant": true of false. Institutioneel of retail buiten de regio is niet relevant.
2. "strategie": voor welk type investeerder dit nieuws telt. Kies EEN uit:
   uitponden | buy-and-hold | splitsen | kamerverhuur | transformatie | verduurzaming | financiering | fiscaal | algemeen
3. "samenvatting": EEN zin met de kern van het artikel.
4. "duiding": EEN zin met concrete betekenis voor investeerders in dit segment.

De duiding moet concreet zijn. Denk aan effect op kosten van kapitaal, huurniveau en dus yield, exit-waarde bij verkoop, netto rendement na belasting, of vergunbaarheid van splitsen.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS. Dit is de belangrijkste regel.
- Je mag ALLEEN getallen noemen die letterlijk in de aangeleverde titel of samenvatting staan.
- Verzin NOOIT bedragen, percentages, rendementen, kostenramingen of huurprijzen die er niet staan. Ook niet als ze plausibel lijken of als je meent ze uit algemene kennis te weten.
- Geen schattingen met "circa", "ruwweg", "kan oplopen tot" of een bandbreedte bij een bedrag dat je niet hebt gekregen.
- Staat er geen cijfer in de bron? Dan is je duiding puur kwalitatief. Dat is prima en beter dan een gok.
- Noem het mechanisme, niet het bedrag. "Onvoorzien funderingsherstel drukt de exit-waarde" mag altijd. Een bedrag noemen mag alleen als dat bedrag in de bron staat.

OVERIGE REGELS:
- Geen algemeenheden.
- Nooit specifieke beleggers of portefeuilles benoemen. Schrijf onpersoonlijk over de markt.
- Maximaal 30 woorden per zin. Nederlands."""


def haal_feed(bron):
    naam, url = bron
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception as e:
        print(f"Feed {naam} mislukt: {e}", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        print(f"Feed {naam} XML-fout: {e}", file=sys.stderr)
        return []

    items = []
    for it in root.iter():
        tag = it.tag.rsplit("}", 1)[-1].lower()
        if tag != "item":
            continue
        d = {"bron": naam, "titel": "", "link": "", "beschrijving": "", "datum": None}
        for child in it:
            ctag = child.tag.rsplit("}", 1)[-1].lower()
            if ctag == "title" and child.text:
                d["titel"] = child.text.strip()
            elif ctag == "link" and child.text:
                d["link"] = child.text.strip()
            elif ctag == "description" and child.text:
                d["beschrijving"] = re.sub(r"<[^>]+>", "", child.text).strip()[:500]
            elif ctag in ("pubdate", "date", "published") and child.text:
                try:
                    d["datum"] = parsedate_to_datetime(child.text)
                except Exception:
                    pass
        if d["titel"] and d["link"]:
            items.append(d)

    if not items:
        for it in root.iter():
            tag = it.tag.rsplit("}", 1)[-1].lower()
            if tag != "entry":
                continue
            d = {"bron": naam, "titel": "", "link": "", "beschrijving": "", "datum": None}
            for child in it:
                ctag = child.tag.rsplit("}", 1)[-1].lower()
                if ctag == "title" and child.text:
                    d["titel"] = child.text.strip()
                elif ctag == "link":
                    d["link"] = (child.get("href") or (child.text or "")).strip()
                elif ctag in ("summary", "content") and child.text:
                    d["beschrijving"] = re.sub(r"<[^>]+>", "", child.text).strip()[:500]
                elif ctag == "updated" and child.text:
                    try:
                        d["datum"] = dt.datetime.fromisoformat(child.text.replace("Z", "+00:00"))
                    except Exception:
                        pass
            if d["titel"] and d["link"]:
                items.append(d)
    return items


def recent(item):
    if not item["datum"]:
        return True
    leeftijd = dt.datetime.now(item["datum"].tzinfo) - item["datum"]
    return leeftijd <= dt.timedelta(hours=MAX_LEEFTIJD_UREN)


def relevant_trefwoord(item):
    hooi = (item["titel"] + " " + item["beschrijving"]).lower()
    return any(tw in hooi for tw in TREFWOORDEN)


def lees_gezien():
    if not os.path.exists(HISTORIE_PAD):
        return set()
    try:
        with open(HISTORIE_PAD, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("links", []))
    except Exception:
        return set()


def schrijf_gezien(links):
    with open(HISTORIE_PAD, "w", encoding="utf-8") as f:
        json.dump({"links": list(links)[-500:]}, f, ensure_ascii=False)


def verrijk(items):
    for it in items:
        it["samenvatting"] = ""
        it["gevolg"] = ""
        it["strategie"] = ""
    if not ANTHROPIC_API_KEY or not items:
        return
    lijst = "\n".join(
        f"{i}. [{it['bron']}] {it['titel']} - {it['beschrijving']}"
        for i, it in enumerate(items)
    )
    prompt = (f"Berichten:\n{lijst}\n\n"
              'Antwoord met ALLEEN een JSON-array. Per bericht: '
              '{"i": <index>, "relevant": true/false, "strategie": "<label>", '
              '"samenvatting": "<1 zin>", "duiding": "<1 zin>"}. '
              "Geen tekst eromheen.")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 4000, "system": PROFIEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=90,
        )
        resp.raise_for_status()
        body = resp.json()
        tekst = "".join(b.get("text", "") for b in body.get("content", []))
        if body.get("stop_reason") == "max_tokens":
            print("LET OP: antwoord afgekapt op max_tokens", file=sys.stderr)
        tekst = tekst.strip()
        if tekst.startswith("```"):
            tekst = tekst.split("```")[1]
            if tekst.startswith("json"):
                tekst = tekst[4:]
        tekst = tekst.strip()

        try:
            data = json.loads(tekst)
        except json.JSONDecodeError:
            data = []
            for m in re.finditer(r"\{[^{}]*\}", tekst):
                try:
                    data.append(json.loads(m.group(0)))
                except json.JSONDecodeError:
                    continue
            if not data:
                raise

        for rij in data:
            if not isinstance(rij, dict):
                continue
            i = rij.get("i")
            if not (isinstance(i, int) and 0 <= i < len(items)):
                continue
            if rij.get("relevant") is False:
                items[i]["gevolg"] = "-"
                continue
            items[i]["strategie"] = str(rij.get("strategie", "")).strip().lower()
            items[i]["samenvatting"] = str(rij.get("samenvatting", "")).strip()
            items[i]["gevolg"] = str(rij.get("duiding", rij.get("gevolg", ""))).strip()
    except Exception as e:
        print(f"Duiding overgeslagen: {e}", file=sys.stderr)


def render(items):
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    r = ["", "## Publicaties", f"_Vastgoedartikelen laatste 24u, met marktduiding. {vandaag}._", ""]
    if not items:
        r.append("_Geen relevante publicaties gevonden._")
        return "\n".join(r)
    for it in items:
        strat = (it.get("strategie") or "").strip()
        kop = f"**[{strat}]** " if strat and strat != "algemeen" else ""
        r.append(f"- {kop}**{it['titel']}** ([bron]({it['link']}))")
        if it.get("samenvatting"):
            r.append(f"  {it['samenvatting']}")
        if it.get("gevolg") and it["gevolg"] not in ("-", ""):
            r.append(f"  _{it['gevolg']}_")
        r.append("")
    return "\n".join(r)


def _titel_sleutel(titel):
    """Normaliseert een titel voor dedup: zelfde artikel via verschillende feeds."""
    t = titel.lower()
    t = re.sub(r"\s+-\s+[^-]+$", "", t)   # trailing " - Bronnaam" weghalen
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="publicaties_digest.md")
    args = ap.parse_args()

    alle = []
    for bron in FEEDS:
        alle.extend(haal_feed(bron))
    print(f"Opgehaald: {len(alle)} items uit {len(FEEDS)} feeds", file=sys.stderr)

    gezien = lees_gezien()
    kandidaten = [it for it in alle if recent(it) and it["link"] not in gezien]
    print(f"Nieuw (laatste {MAX_LEEFTIJD_UREN}u): {len(kandidaten)}", file=sys.stderr)

    kandidaten = [it for it in kandidaten if relevant_trefwoord(it)]
    print(f"Na trefwoordfilter: {len(kandidaten)}", file=sys.stderr)

    gezien_batch, titels_batch, uniek = set(), set(), []
    for it in kandidaten:
        if it["link"] in gezien_batch:
            continue
        tsleutel = _titel_sleutel(it["titel"])
        if tsleutel in titels_batch:
            continue
        gezien_batch.add(it["link"])
        titels_batch.add(tsleutel)
        uniek.append(it)
    print(f"Na dedup (url + titel): {len(uniek)}", file=sys.stderr)

    kandidaten = uniek[:MAX_ITEMS_LLM]
    verrijk(kandidaten)

    tonen = [it for it in kandidaten
             if it.get("gevolg") and it["gevolg"] not in ("-", "")]
    print(f"Na LLM-filter: {len(tonen)}", file=sys.stderr)

    md = render(tonen)
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)

    for it in uniek:
        gezien.add(it["link"])
    schrijf_gezien(gezien)


if __name__ == "__main__":
    main()
