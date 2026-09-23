#!/usr/bin/env python3
"""
De Stadsbegroting van Nijmegen als bron.

De begroting is een raadsstuk en geen bekendmaking, dus de bekendmakingen-
monitor ziet hem niet. Toch staat er wat ons raakt: de tarieven voor OZB,
riool- en afvalstoffenheffing, het grondbeleid, de investeringen en het
programma Wonen en stedelijke ontwikkeling.

De site is per jaar een eigen adres, bijvoorbeeld nijmegen.begroting-2027.nl,
en meldt onderaan wanneer de pagina is gebouwd. Dat gebruiken we om te zien of
er iets is veranderd.

Dit is geen vervanging van de verordening: de tarieven worden pas vastgesteld
in de belastingverordeningen, en die volgt regelgeving_monitor.py. De begroting
laat ze eerder zien, als voornemen.

Gebruik:
  python begroting_monitor.py            # hooguit een keer per week
  python begroting_monitor.py --forceer  # altijd ophalen
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

import requests

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass

UIT_PAD = "begroting_nijmegen.json"
DAGEN_TUSSEN = 7

# Welke pagina's we lezen, op een woord in de linktekst
PAGINAS = ("lokale heffingen", "grondbeleid", "investeringen",
           "wonen en stedelijke ontwikkeling", "financieel beeld")

# Waar we op letten binnen die pagina's
TREFWOORDEN = ("ozb", "onroerendezaakbelasting", "rioolheffing",
               "afvalstoffenheffing", "leges", "woonfonds", "grondprijs",
               "woningbouw", "verkamer", "splitsing", "middenhuur",
               "sociale huur", "tarief", "woonlasten")


def _tekst(html):
    """Platte tekst uit HTML, zonder script, style en tags."""
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = (html.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&euro;", "€").replace("&#8364;", "€"))
    return re.sub(r"[ \t\r\f\v]+", " ", html)


def _links(html, basis):
    """De links op de pagina, als (tekst, url)."""
    uit = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html):
        url, tekst = m.group(1), _tekst(m.group(2)).strip()
        if not tekst:
            continue
        if url.startswith("/"):
            url = basis.rstrip("/") + url
        uit.append((tekst, url))
    return uit


def _regels_met_trefwoord(tekst):
    """Zinnen waarin een van onze trefwoorden voorkomt, ontdubbeld."""
    zinnen = re.split(r"(?<=[.!?])\s+|\n+", tekst)
    uit, gezien = [], set()
    for z in zinnen:
        z = z.strip()
        if not (25 < len(z) < 400):
            continue
        laag = z.lower()
        if any(t in laag for t in TREFWOORDEN) and z not in gezien:
            gezien.add(z)
            uit.append(z)
    return uit[:12]


def haal(jaar, sessie=None):
    """De begrotingssite van een jaar, als die bestaat."""
    basis = f"https://nijmegen.begroting-{jaar}.nl"
    s = sessie or requests.Session()
    try:
        r = s.get(basis + "/", timeout=(15, 60))
        r.raise_for_status()
    except Exception:
        return None
    html = r.text
    gebouwd = ""
    m = re.search(r"gebouwd op ([\d/: ]+)", _tekst(html))
    if m:
        gebouwd = m.group(1).strip()

    paginas = {}
    for tekst, url in _links(html, basis):
        naam = tekst.lower().strip()
        if not any(p in naam for p in PAGINAS):
            continue
        if naam in paginas or not url.startswith(basis):
            continue
        try:
            rp = s.get(url, timeout=(15, 60))
            rp.raise_for_status()
        except Exception:
            continue
        regels = _regels_met_trefwoord(_tekst(rp.text))
        if regels:
            paginas[tekst.strip()] = {"url": url, "regels": regels}
    if not paginas:
        return None
    return {"jaar": jaar, "basis": basis, "gebouwd": gebouwd,
            "opgehaald": dt.date.today().isoformat(), "paginas": paginas}


def nieuw_ten_opzichte_van(nu, eerder):
    """Welke regels zijn er sinds de vorige keer bij gekomen?"""
    oud = set()
    for p in (eerder or {}).get("paginas", {}).values():
        oud.update(p.get("regels", []))
    uit = {}
    for titel, p in nu.get("paginas", {}).items():
        verschil = [r for r in p["regels"] if r not in oud]
        if verschil:
            uit[titel] = verschil
    return uit


def omschrijf(data, nieuw=None):
    """Tekst voor de brief."""
    if not data:
        return ""
    kop = (f"Stadsbegroting {data['jaar']} van de gemeente Nijmegen"
           + (f", pagina gebouwd op {data['gebouwd']}" if data.get("gebouwd") else "")
           + f" (bron: {data['basis']}). De tarieven hierin zijn een voornemen; "
             f"vastgesteld worden ze in de belastingverordeningen.")
    delen = [kop]
    bron = nieuw if nieuw else {t: p["regels"] for t, p in data["paginas"].items()}
    for titel, regels in bron.items():
        delen.append(f"{titel}: " + " ".join(regels[:6]))
    return "\n".join(delen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forceer", action="store_true")
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    wis("begroting")

    eerder = {}
    if os.path.exists(UIT_PAD):
        try:
            with open(UIT_PAD, encoding="utf-8") as f:
                eerder = json.load(f)
        except Exception:
            eerder = {}
    if eerder and not args.forceer:
        try:
            oud = dt.date.fromisoformat(eerder.get("opgehaald", "1900-01-01"))
            if (dt.date.today() - oud).days < DAGEN_TUSSEN:
                print(f"Begroting: {(dt.date.today() - oud).days} dagen geleden "
                      f"opgehaald, overgeslagen", file=sys.stderr)
                return
        except Exception:
            pass

    # De begroting van volgend jaar verschijnt in het najaar; daarvoor is de
    # lopende de meest actuele.
    data = None
    for jaar in (dt.date.today().year + 1, dt.date.today().year):
        data = haal(jaar)
        if data:
            break
    if not data:
        leg_vast("begroting", "Geen begrotingssite gevonden voor "
                              f"{dt.date.today().year + 1} of "
                              f"{dt.date.today().year}. Adres veranderd?")
        print("Geen begroting opgehaald", file=sys.stderr)
        return

    nieuw = nieuw_ten_opzichte_van(data, eerder)
    with open(UIT_PAD, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    if args.uit and nieuw:
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(omschrijf(data, nieuw) + "\n")
    print(f"Begroting {data['jaar']}: {len(data['paginas'])} pagina's, "
          f"{sum(len(v) for v in nieuw.values())} nieuwe regels", file=sys.stderr)


if __name__ == "__main__":
    main()
