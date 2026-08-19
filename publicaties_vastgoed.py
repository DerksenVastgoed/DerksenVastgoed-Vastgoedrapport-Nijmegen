#!/usr/bin/env python3
"""
Publicaties-blok voor de Nijmegen Vastgoedmonitor.

Haalt recente artikelen op uit RSS-feeds van vastgoedbronnen, filtert op
relevantie voor Derksen Vastgoed, en genereert per bericht een samenvatting
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
    ("Woningmarkt NL", _gnews("Nederlandse woningmarkt")),
    ("Wet betaalbare huur", _gnews('"wet betaalbare huur" OR "WWS"')),
    ("Particuliere verhuur", _gnews("verhuurders OR particuliere huursector")),
    ("Vastgoed Gelderland", _gnews("vastgoed Nijmegen OR Arnhem OR Gelderland")),
    ("Verduurzaming huur", _gnews("verduurzaming huurwoning OR energielabel verhuur")),
    ("Rente vastgoed", _gnews("hypotheekrente OR verhuurhypotheek")),
    ("Box 3 vastgoed", _gnews('"box 3" vastgoed')),
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
    "dynamis", "capital value", "nvm", "brainbay", "pararius",
    "abn amro woningmarkt", "rabobank woningmarkt", "dnb",
]

MAX_LEEFTIJD_UREN = 30
MAX_ITEMS_LLM = 15
HISTORIE_PAD = "publicaties_gezien.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-5"
PROFIEL = """Je bent de analist van Derksen Vastgoed in Nijmegen. Context:
- Verhuurt woningen via BV. Eigen panden: Graafsedwarsstraat 58-60 en Eerste Oude Heselaan 86-88A, Waterkwartier (Oud-West).
- Acquisitietargets: Fransestraat en Van Spaenstraat, Galgenveld (Nijmegen-Oost).
- Focus: ring rond het Keizer Karelplein, oost en west. Vooroorlogs bezit met verduurzamingsopgave.
- Model: kopen, bij mutatie renoveren, label omhoog, waar mogelijk splitsen, beter verhuren. Vuistregel: bod = 17x jaarhuur. LTV standaard 70%.
Je krijgt titels + korte samenvattingen van vastgoedpublicaties. Voor elk:
1. Beoordeel of het echt relevant is voor Derksen. Zo nee, "gevolg" = "-".
2. Zo ja: geef in EEN zin de kern-samenvatting, in EEN zin het gevolg voor Derksen.
Wees streng. Institutioneel of retail buiten regio = niet relevant."""


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
    if not ANTHROPIC_API_KEY or not items:
        return
    lijst = "\n".join(
        f"{i}. [{it['bron']}] {it['titel']} - {it['beschrijving']}"
        for i, it in enumerate(items)
    )
    prompt = (f"Berichten:\n{lijst}\n\n"
              'Antwoord met ALLEEN een JSON-array. Per bericht: '
              '{"i": <index>, "samenvatting": "<1 zin, of leeg>", '
              '"gevolg": "<1 zin gevolg voor Derksen, of \'-\' als niet relevant>"}. '
              "Geen tekst eromheen.")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 2000, "system": PROFIEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        tekst = "".join(b.get("text", "") for b in resp.json().get("content", []))
        tekst = tekst.strip()
        if tekst.startswith("```"):
            tekst = tekst.split("```")[1]
            if tekst.startswith("json"):
                tekst = tekst[4:]
        data = json.loads(tekst)
        for rij in data:
            i = rij.get("i")
            if isinstance(i, int) and 0 <= i < len(items):
                items[i]["samenvatting"] = str(rij.get("samenvatting", "")).strip()
                items[i]["gevolg"] = str(rij.get("gevolg", "")).strip()
    except Exception as e:
        print(f"Duiding overgeslagen: {e}", file=sys.stderr)


def render(items):
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    r = ["", "## Publicaties", f"_Vastgoedartikelen laatste 24u, met vertaling naar Derksen. {vandaag}._", ""]
    if not items:
        r.append("_Geen relevante publicaties gevonden._")
        return "\n".join(r)
    for it in items:
        r.append(f"- **[{it['bron']}] {it['titel']}** ([bron]({it['link']}))")
        if it.get("samenvatting"):
            r.append(f"  {it['samenvatting']}")
        if it.get("gevolg") and it["gevolg"] not in ("-", ""):
            r.append(f"  -> _{it['gevolg']}_")
        r.append("")
    return "\n".join(r)


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

    gezien_batch, uniek = set(), []
    for it in kandidaten:
        if it["link"] in gezien_batch:
            continue
        gezien_batch.add(it["link"])
        uniek.append(it)

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
