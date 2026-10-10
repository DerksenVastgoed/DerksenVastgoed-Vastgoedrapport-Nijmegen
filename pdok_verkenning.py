#!/usr/bin/env python3
"""
Eenmalige verkenning van de BAG bij PDOK. Hoort niet in main thuis en wordt na
gebruik weggegooid.

WAAROM DIT BESTAAT. Op 10 oktober mislukte het ophalen van de voorraad vier
keer op rij, elke keer omdat ik een eigenschap van de dienst aannam in plaats
van hem te vragen. Eerst dat de BAG een postcode alleen accepteert (nee, er
moet een huisnummer bij). Toen dat PDOK op postcode kan filteren (nee, alleen
geometry en identificatie zijn filterbaar). Deze omgeving mag api.pdok.nl niet
benaderen, dus elk antwoord kost een workflowrun. Dan is één run die alle
vragen tegelijk stelt goedkoper dan vier runs die er één stellen.

DE VRAGEN.
  1. Welke collecties biedt deze dienst, en wat is per collectie filterbaar?
     Als er een adres- of nummeraanduidingcollectie is waar postcode wél
     filterbaar is, is de hele ruimtelijke route onnodig.
  2. Hoe ziet één echt verblijfsobject eruit? Tot nu toe is er geen enkel
     antwoord van deze dienst gelukt, dus de veldnamen waar voorraad_bag.py op
     rekent zijn nog nooit gezien. In de echte BAG hangt de postcode aan de
     nummeraanduiding en niet aan het verblijfsobject. Staat postcode hier niet
     in het antwoord, dan kan ik lokaal niet op postcode filteren en moet het
     ophalen langs een andere collectie.
  3. Werkt de bbox-parameter, en vertelt de dienst hoeveel objecten er in een
     gebied zitten (numberMatched)? Dat getal bepaalt hoeveel pagina's een
     volledige ronde kost, en dus of het binnen het tijdbudget past.
  4. Is er een collectie met de begrenzing van Nijmegen erin? De zes buurten
     staan nergens in deze repo als geometrie. Komt de begrenzing uit de BAG
     zelf, dan hoef ik geen doos te gokken.

OVER DE GEGOKTE DOOS. Vraag 3 en 4 gebruiken een ruime doos om Nijmegen die ik
uit mijn hoofd opschrijf. Dat mag hier, want deze doos wordt alleen gebruikt om
de echte begrenzing te vínden, en als de gok te klein is meldt dit script dat
Nijmegen niet gevonden is. Een gok in de vindstap faalt hard. Diezelfde gok in
de ophaalstap zou stil adressen missen, en dat is precies het soort fout dat
dit project steeds inhaalt.
"""

import json
import sys

import requests

BASIS = "https://api.pdok.nl/kadaster/bag/ogc/v2"

# Ruim om Nijmegen heen, in CRS84 (lengte, breedte). Alleen om te zoeken.
ZOEKDOOS = "5.75,51.76,5.98,51.90"

TIJD = 30


def haal(pad, params=None):
    """Een GET met de fout als tekst in plaats van als uitzondering."""
    url = pad if pad.startswith("http") else f"{BASIS}{pad}"
    try:
        r = requests.get(url, params=params or {}, timeout=TIJD,
                         headers={"Accept": "application/json"})
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:600]}"
    try:
        return r.json(), ""
    except Exception as e:
        return None, f"geen json: {e}; begin van het antwoord: {r.text[:300]}"


def kop(n, tekst):
    print(f"\n{'=' * 70}\nVRAAG {n}. {tekst}\n{'=' * 70}")


def vraag1_collecties():
    kop(1, "Welke collecties zijn er, en wat is filterbaar?")
    d, fout = haal("/collections")
    if fout:
        print(f"MISLUKT: {fout}")
        return []
    namen = []
    for c in d.get("collections") or []:
        cid = c.get("id") or ""
        namen.append(cid)
        print(f"\n  collectie: {cid}   ({c.get('title') or ''})")
        q, qfout = haal(f"/collections/{cid}/queryables")
        if qfout:
            print(f"    queryables MISLUKT: {qfout}")
            continue
        velden = sorted((q.get("properties") or {}).keys())
        print(f"    filterbaar: {', '.join(velden) or 'niets'}")
        if "postcode" in velden:
            print("    >>> POSTCODE IS HIER FILTERBAAR <<<")
    print(f"\n  alle collecties: {', '.join(namen)}")
    return namen


def vraag2_een_object():
    kop(2, "Hoe ziet een echt verblijfsobject eruit?")
    d, fout = haal("/collections/verblijfsobject/items", {"limit": 1})
    if fout:
        print(f"MISLUKT: {fout}")
        return
    kenmerken = d.get("features") or []
    print(f"  numberMatched: {d.get('numberMatched')}")
    print(f"  numberReturned: {d.get('numberReturned')}")
    if not kenmerken:
        print("  geen enkel kenmerk teruggekregen")
        return
    print("  het hele eerste kenmerk, onbewerkt:")
    print(json.dumps(kenmerken[0], ensure_ascii=False, indent=2)[:2500])
    eig = kenmerken[0].get("properties") or {}
    print(f"\n  eigenschappen: {', '.join(sorted(eig.keys()))}")
    for veld in ("postcode", "oppervlakte", "gebruiksdoel", "huisnummer",
                 "openbare_ruimte_naam", "pand", "identificatie", "status"):
        aanwezig = "JA" if veld in eig else "NEE"
        print(f"    {veld}: {aanwezig}"
              + (f"  waarde={eig[veld]!r}" if veld in eig else ""))


def vraag3_bbox():
    kop(3, "Werkt bbox, en hoeveel objecten zitten er in de doos?")
    d, fout = haal("/collections/verblijfsobject/items",
                   {"bbox": ZOEKDOOS, "limit": 2})
    if fout:
        print(f"MISLUKT: {fout}")
        return
    print(f"  bbox {ZOEKDOOS} werkt.")
    print(f"  numberMatched: {d.get('numberMatched')}")
    print(f"  numberReturned: {d.get('numberReturned')}")
    for k in (d.get("features") or [])[:2]:
        eig = k.get("properties") or {}
        kort = {v: eig.get(v) for v in
                ("postcode", "openbare_ruimte_naam", "huisnummer",
                 "oppervlakte", "gebruiksdoel")}
        print(f"    {json.dumps(kort, ensure_ascii=False)}")
    links = [l.get("href") for l in (d.get("links") or [])
             if l.get("rel") == "next"]
    print(f"  volgende-link aanwezig: {'JA' if links else 'NEE'}")
    if links:
        print(f"    {links[0][:300]}")


def vraag4_begrenzing(namen):
    kop(4, "Is de begrenzing van Nijmegen uit de BAG zelf te halen?")
    kandidaten = [n for n in namen
                  if n in ("woonplaats", "woonplaatsen", "gemeente",
                           "buurt", "wijk")]
    if not kandidaten:
        print(f"  geen gebiedscollectie gevonden tussen: {', '.join(namen)}")
        return
    for cid in kandidaten:
        print(f"\n  collectie {cid} binnen de zoekdoos:")
        d, fout = haal(f"/collections/{cid}/items",
                       {"bbox": ZOEKDOOS, "limit": 20})
        if fout:
            print(f"    MISLUKT: {fout}")
            continue
        for k in d.get("features") or []:
            eig = k.get("properties") or {}
            naam = (eig.get("naam") or eig.get("woonplaats_naam")
                    or eig.get("identificatie") or "?")
            doos = _doos_van(k.get("geometry"))
            print(f"    {naam}: bbox={doos}")


def _doos_van(geo):
    """De omhullende doos van een geometrie, zonder bibliotheek."""
    if not geo:
        return "geen geometrie"
    lo, la = [], []

    def loop(x):
        if isinstance(x, (int, float)):
            return
        if (len(x) >= 2 and isinstance(x[0], (int, float))
                and isinstance(x[1], (int, float))):
            lo.append(x[0])
            la.append(x[1])
            return
        for d in x:
            loop(d)

    try:
        loop(geo.get("coordinates") or [])
    except Exception as e:
        return f"onleesbaar: {e}"
    if not lo:
        return "geen punten"
    return (f"{min(lo):.5f},{min(la):.5f},{max(lo):.5f},{max(la):.5f} "
            f"({len(lo)} punten)")


def main():
    print("Verkenning van de BAG bij PDOK")
    namen = vraag1_collecties()
    vraag2_een_object()
    vraag3_bbox()
    vraag4_begrenzing(namen)
    print("\nKlaar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
