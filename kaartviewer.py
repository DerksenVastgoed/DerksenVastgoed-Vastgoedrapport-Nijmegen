#!/usr/bin/env python3
"""
Welke kaartlagen de KaartViewer van de gemeente laadt (kaart.nijmegen.nl).

WAAROM. 18 oktober 2026, Mark gaf https://kaart.nijmegen.nl/menu/index.html.
De pagina is een JavaScript-app: zonder browser staat er alleen "KaartViewer
Menu werkt niet goed als JavaScript is uitgeschakeld", en de lagen komen pas
na het laden binnen. De browsers op Marks computer waren vanuit deze sessie
niet bereikbaar. Daarom laadt deze stap de pagina in een headless Chromium in
de workflow en schrijft hij op welke adressen de pagina opvraagt: de
configuratie, de werkruimtes op services.nijmegen.nl en de lagen. Eerst
robots.txt, zoals overal; staat die het niet toe, dan gebeurt er niets.

  python3 kaartviewer.py --verken
"""
import argparse
import re
import sys

import stadsbeeld  # mag(): robots.txt eerst, een implementatie

START = "https://kaart.nijmegen.nl/menu/index.html"
VERSLAG = "kaartviewer_verslag.md"
INTERESSANT = re.compile(r"geoservices|wms|wfs|ows|\.json|config|layer|laag|"
                         r"monument|erfgoed|cultuur", re.I)


def verken():
    r = ["# KaartViewer gemeente Nijmegen", "", f"Start: `{START}`", ""]
    ok, reden = stadsbeeld.mag(START)
    if not ok:
        r.append(f"NIET GELADEN: {reden}")
        _schrijf(r)
        return 0
    from playwright.sync_api import sync_playwright
    verzoeken, links = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=stadsbeeld.AGENT)
        pg.on("request", lambda q: verzoeken.append(q.url))
        pg.goto(START, wait_until="networkidle", timeout=60000)
        links = pg.eval_on_selector_all(
            "a", "els => els.map(e => [e.innerText.trim(), e.href])")
        # Elke kaart in het menu met monument, erfgoed of cultuur in de naam
        # ook openen, want pas daar laadt de kaart haar lagen.
        doelen = [h for t, h in links
                  if re.search(r"monument|erfgoed|cultuur|histor", t + h, re.I)]
        teksten = {}
        for h in doelen[:5]:
            ok2, reden2 = stadsbeeld.mag(h)
            if not ok2:
                r.append(f"- niet geopend {h}: {reden2}")
                continue
            try:
                pg.goto(h, wait_until="networkidle", timeout=60000)
                pg.wait_for_timeout(5000)
                # De lagenlijst van de kaart: pas aangevinkte lagen worden
                # opgevraagd, dus de namen staan alleen in de pagina zelf.
                teksten[h] = pg.inner_text("body")[:6000]
            except Exception as e:
                r.append(f"- fout bij {h}: {type(e).__name__}")
        b.close()
    r.append("## Menu")
    r += [f"- {t[:80]} -> {h}" for t, h in links[:80]]
    r.append("")
    # ALLES BEHALVE ACHTERGRONDTEGELS. De eerste ronde, 18 oktober, filterde
    # op woorden als json en config, en zag alleen de gemeentegrens: de
    # configuratie van de kaart Historie kwam blijkbaar via een adres zonder
    # die woorden. Nu staat elk verzoek erin, behalve de tegels van de
    # achtergrondkaart, met de kaartlagen bovenaan.
    uniek = sorted(set(u for u in verzoeken if "openbasiskaart" not in u
                       and not re.search(r"\.(png|jpg|svg|woff2?|ttf|css)"
                                         r"(\?|$)", u)))
    r.append("## Opgevraagde adressen die op kaartlagen wijzen")
    r += [f"- {u[:300]}" for u in uniek if INTERESSANT.search(u)][:150]
    r.append("")
    r.append("## Alle andere opgevraagde adressen")
    r += [f"- {u[:300]}" for u in uniek if not INTERESSANT.search(u)][:150]
    r.append("")
    for h, t in teksten.items():
        r.append(f"## Tekst op {h}")
        r.append("```")
        r.append(t)
        r.append("```")
    _schrijf(r)
    return 0


def _schrijf(r):
    with open(VERSLAG, "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    print("\n".join(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verken", action="store_true")
    a = ap.parse_args()
    if a.verken:
        return verken()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
