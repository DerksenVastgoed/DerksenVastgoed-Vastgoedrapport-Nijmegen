#!/usr/bin/env python3
"""
Eenmalige verkenning van de BAG bij PDOK. Hoort niet in main thuis en wordt na
gebruik weggegooid.

WAAROM DIT BESTAAT. Op 10 oktober mislukte het ophalen van de voorraad vier
keer op rij, elke keer omdat ik een eigenschap van de dienst aannam in plaats
van hem te vragen. Deze omgeving mag api.pdok.nl niet benaderen en het logboek
van een run is hier niet te lezen, dus elk antwoord kost een workflowrun die
zijn uitkomst terugcommit. Dan is één run die alle vragen tegelijk stelt
goedkoper dan vier runs die er één stellen.

RONDE 1 (beantwoord op 10 oktober, zie pdok_antwoord.md):
  1. Filterbaar is op alle zes collecties alleen geometry en identificatie.
     Postcode kan dus nergens als filter.
  2. Postcode komt wél terug in het antwoord, met oppervlakte, gebruiksdoel
     (enkelvoud, string), huisnummer, huisletter, toevoeging,
     openbare_ruimte_naam, status en woonplaats_naam. Het pand staat er als
     pand.href, een lijst met URL's naar PDOK's eigen kenmerk-id, niet als de
     16-cijferige BAG-pandidentificatie.
  3. bbox werkt. numberMatched is leeg, dus de dienst zegt niet hoeveel
     objecten er in een gebied zitten. Doorbladeren gaat met een cursor in de
     volgende-link.

RONDE 2 (dit bestand nu): hoe duur is een ronde werkelijk? Daar hangt het hele
ontwerp aan. Past de hele doos om Nijmegen in één run, dan is er geen cursor
om te bewaren, geen raster en geen gegokte geometrie nodig, en is het ophalen
per gebied simpeler dan het ooit per postcode was.
"""

import json
import sys
import time

import requests

BASIS = "https://api.pdok.nl/kadaster/bag/ogc/v2"
ITEMS = f"{BASIS}/collections/verblijfsobject/items"

# Ruim om Nijmegen heen, in CRS84 (lengte, breedte). Dit is met opzet te groot:
# het is een bovengrens, geen schatting van het gebied. De vraag is juist of
# die bovengrens betaalbaar is.
ZOEKDOOS = "5.75,51.76,5.98,51.90"

INVENTARIS = "buurtinventaris.json"
BUDGET = 300  # seconden voor de proefronde
TIJD = 60


def haal(url, params=None):
    try:
        r = requests.get(url, params=params or {}, timeout=TIJD,
                         headers={"Accept": "application/json"})
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:500]}"
    try:
        return r.json(), ""
    except Exception as e:
        return None, f"geen json: {e}; {r.text[:200]}"


def kop(n, tekst):
    print(f"\n{'=' * 70}\nVRAAG {n}. {tekst}\n{'=' * 70}")


def onze_postcodes():
    try:
        with open(INVENTARIS, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        print(f"  {INVENTARIS} niet leesbaar: {e}")
        return {}
    uit = {}
    for buurt, lijst in (d.get("postcodes_per_buurt") or {}).items():
        for pc in lijst:
            uit[pc.replace(" ", "").upper()] = buurt
    return uit


def vraag5_limiet():
    """Hoe veel objecten mag één pagina bevatten?"""
    kop(5, "Hoe groot mag limit zijn?")
    beste = 0
    for n in (200, 500, 1000, 2000, 5000):
        d, fout = haal(ITEMS, {"bbox": ZOEKDOOS, "limit": n})
        if fout:
            print(f"  limit={n}: MISLUKT: {fout[:200]}")
            continue
        terug = d.get("numberReturned")
        print(f"  limit={n}: numberReturned={terug}")
        if terug and terug >= n:
            beste = n
        elif terug:
            print(f"    >>> afgekapt op {terug}, dat is het echte maximum")
            beste = max(beste, terug)
            break
    print(f"\n  grootste werkende pagina: {beste}")
    return beste or 200


def vraag6_ronde(limiet, pcs):
    """Een echte ronde over de hele doos, tot het budget om is."""
    kop(6, f"Wat kost een ronde over de hele doos? (limit={limiet}, "
           f"budget={BUDGET}s)")
    start = time.time()
    url, params = ITEMS, {"bbox": ZOEKDOOS, "limit": limiet}
    paginas = objecten = raak = 0
    gezien = {}
    lo, la = [], []
    doelen = {}
    klaar = False
    while time.time() - start < BUDGET:
        d, fout = haal(url, params)
        if fout:
            print(f"  pagina {paginas + 1} MISLUKT: {fout[:300]}")
            break
        paginas += 1
        kenmerken = d.get("features") or []
        objecten += len(kenmerken)
        for k in kenmerken:
            eig = k.get("properties") or {}
            pc = (eig.get("postcode") or "").replace(" ", "").upper()
            if pc in pcs:
                raak += 1
                gezien[pc] = gezien.get(pc, 0) + 1
                doelen[eig.get("gebruiksdoel") or "?"] = doelen.get(
                    eig.get("gebruiksdoel") or "?", 0) + 1
                co = (k.get("geometry") or {}).get("coordinates") or []
                if len(co) >= 2:
                    lo.append(co[0])
                    la.append(co[1])
        volgende = [l.get("href") for l in (d.get("links") or [])
                    if l.get("rel") == "next"]
        if not volgende:
            klaar = True
            break
        url, params = volgende[0], None
    duur = time.time() - start
    print(f"  pagina's: {paginas}")
    print(f"  objecten gezien: {objecten}")
    print(f"  duur: {duur:.1f}s")
    if duur > 0:
        print(f"  tempo: {objecten / duur:.0f} objecten per seconde, "
              f"{duur / max(paginas, 1):.2f}s per pagina")
    print(f"  hele doos uitgelezen binnen het budget: "
          f"{'JA' if klaar else 'NEE'}")
    if not klaar and objecten:
        print("  (dus de doos is groter dan dit budget; het tempo hierboven "
              "zegt wat een volledige ronde kost zodra het totaal bekend is)")
    print(f"\n  objecten in onze {len(pcs)} postcodes: {raak}")
    print(f"  postcodes geraakt: {len(gezien)} van {len(pcs)}")
    if lo:
        print(f"  gemeten doos om onze treffers: "
              f"{min(lo):.5f},{min(la):.5f},{max(lo):.5f},{max(la):.5f}")
    if doelen:
        print("  gebruiksdoelen van de treffers: "
              + ", ".join(f"{k}={v}" for k, v in
                          sorted(doelen.items(), key=lambda x: -x[1])[:10]))
    return klaar


def vraag7_kleine_doos(limiet, pcs):
    """Hetzelfde, maar dan over een doos die alleen de ring omvat.

    Deze doos komt uit de treffers van vraag 6 en is dus gemeten, geen gok.
    Hij is alleen te klein als vraag 6 niet klaar kwam, en dan staat dat er
    ook bij.
    """
    kop(7, "En hoe duur is een kleine doos om alleen de ring?")
    # Eerst de doos opnieuw bepalen uit een snelle ronde over de eigen
    # postcodes is niet mogelijk zonder filter. Daarom hier handmatig: de doos
    # die vraag 6 meldde. Bij de eerste run is die er nog niet, dus dan slaat
    # deze vraag over en lees ik het antwoord van vraag 6.
    print("  overgeslagen: deze vraag heeft de gemeten doos van vraag 6 "
          "nodig en die komt uit deze run.")


def main():
    print("Verkenning van de BAG bij PDOK, ronde 2")
    pcs = onze_postcodes()
    print(f"onze postcodes: {len(pcs)} uit {INVENTARIS}")
    limiet = vraag5_limiet()
    vraag6_ronde(limiet, pcs)
    vraag7_kleine_doos(limiet, pcs)
    print("\nKlaar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
