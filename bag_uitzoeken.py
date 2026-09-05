#!/usr/bin/env python3
"""
Toont de volledige BAG-respons voor een paar adressen.

Doel: uitzoeken welk veld de oppervlakte van het verblijfsobject bevat en welk
veld die van het pand. Bij van Slichtenhorststraat 42 geeft onze huidige code
233 m2 terug, terwijl de advertentie 144 m2 noemt voor het bovenhuis.

Zet dit bestand in de repo-root en voeg deze stap toe aan de workflow, boven de
marktprijzen-stap:

      - name: BAG uitzoeken
        env:
          BAG_API_KEY: ${{ secrets.BAG_API_KEY }}
        run: python bag_uitzoeken.py

Draai de workflow, kopieer de uitvoer van deze stap, en haal de stap daarna
weer weg.
"""

import json
import os
import re
import sys
import time

import requests

BAG_API_KEY = os.environ.get("BAG_API_KEY", "")
BAG_BASE = "https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2"
HEADERS = {"X-Api-Key": BAG_API_KEY, "Accept": "application/hal+json"}

# Panden waarvan we weten dat de oppervlakte niet klopt, plus een gewoon pand
# als vergelijking.
ADRESSEN = [
    "van Slichtenhorststraat 42",   # bovenhuis, advertentie zegt 144 m2
    "Bronsgeeststraat 11",          # gaf 52 m2 bij een splitsingsaanvraag
    "Plein 1944 142",               # gaf 53 m2 voor een bovenwoning van 132 m2
    "Zwaluwstraat 7",               # gewoon pand, ter vergelijking
]

# Velden die we willen zien; de rest laten we weg om de uitvoer leesbaar te houden
INTERESSANT = (
    "oppervlakte", "gebruiksdoelen", "postcode", "huisnummer", "huisletter",
    "huisnummertoevoeging", "openbareRuimteNaam", "adresseerbaarObjectIdentificatie",
    "nummeraanduidingIdentificatie", "pandIdentificaties", "oorspronkelijkBouwjaar",
    "adresseerbaarObjectStatus", "typeAdresseerbaarObject",
)


def splits(adres):
    m = re.match(r"^(.+?)\s+(\d+)\s*([A-Za-z])?\s*$", adres.strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2), (m.group(3) or "").upper() or None


def toon(kop, data):
    print(f"\n  {kop}")
    if isinstance(data, dict):
        for k in sorted(data):
            if k in INTERESSANT:
                print(f"    {k}: {data[k]}")
        # Wat er nog meer in zit, alleen de namen
        rest = [k for k in sorted(data) if k not in INTERESSANT
                and not k.startswith("_")]
        if rest:
            print(f"    (overige velden: {', '.join(rest)})")
        binnen = data.get("_embedded")
        if isinstance(binnen, dict):
            for naam, waarde in binnen.items():
                lijst = waarde if isinstance(waarde, list) else [waarde]
                for i, item in enumerate(lijst):
                    if isinstance(item, dict):
                        print(f"    _embedded.{naam}[{i}]:")
                        for k in sorted(item):
                            if k in INTERESSANT or "oppervlak" in k.lower():
                                print(f"      {k}: {item[k]}")
                        overig = [k for k in sorted(item)
                                  if k not in INTERESSANT and not k.startswith("_")]
                        if overig:
                            print(f"      (overige: {', '.join(overig)})")


def bevraag(adres):
    gesplitst = splits(adres)
    if not gesplitst:
        print(f"  kan {adres} niet splitsen")
        return
    straat, nr, letter = gesplitst
    basis = {"openbareRuimteNaam": straat, "huisnummer": nr,
             "woonplaatsNaam": "Nijmegen", "exacteMatch": "true"}
    if letter:
        basis["huisletter"] = letter

    varianten = [
        ("met expand=panden", {**basis, "expand": "panden"}),
        ("zonder expand", dict(basis)),
        ("zonder exacteMatch", {k: v for k, v in basis.items()
                                if k != "exacteMatch"}),
    ]
    vbo = None
    for naam, params in varianten:
        try:
            r = requests.get(f"{BAG_BASE}/adressenuitgebreid",
                             headers=HEADERS, params=params, timeout=25)
        except Exception as e:
            print(f"  {naam}: fout {e}")
            continue
        if r.status_code != 200:
            print(f"  {naam}: status {r.status_code} {r.text[:200]}")
            continue
        rijen = r.json().get("_embedded", {}).get("adressen", [])
        print(f"  {naam}: {len(rijen)} adres(sen)")
        for a in rijen:
            toon(f"{a.get('openbareRuimteNaam','')} {a.get('huisnummer','')}"
                 f"{a.get('huisletter','') or ''}", a)
            vbo = vbo or a.get("adresseerbaarObjectIdentificatie")
        time.sleep(0.4)

    # Alle adressen die aan hetzelfde verblijfsobject hangen
    if vbo:
        print(f"\n  alle adressen op verblijfsobject {vbo}:")
        try:
            r = requests.get(f"{BAG_BASE}/adressenuitgebreid", headers=HEADERS,
                             params={"adresseerbaarObjectIdentificatie": vbo},
                             timeout=25)
            if r.status_code == 200:
                for a in r.json().get("_embedded", {}).get("adressen", []):
                    print(f"    {a.get('openbareRuimteNaam','')} "
                          f"{a.get('huisnummer','')}{a.get('huisletter','') or ''} "
                          f"-> oppervlakte {a.get('oppervlakte')}")
            else:
                print(f"    status {r.status_code}")
        except Exception as e:
            print(f"    fout {e}")
        time.sleep(0.4)

        # Het verblijfsobject zelf opvragen
        print(f"\n  verblijfsobject {vbo} rechtstreeks:")
        try:
            r = requests.get(f"{BAG_BASE}/verblijfsobjecten/{vbo}",
                             headers=HEADERS, timeout=25)
            if r.status_code == 200:
                body = r.json()
                vb = body.get("verblijfsobject", body)
                if isinstance(vb, dict) and "verblijfsobject" in vb:
                    vb = vb["verblijfsobject"]
                print(f"    velden: {sorted(vb.keys()) if isinstance(vb, dict) else vb}")
                if isinstance(vb, dict):
                    for k in sorted(vb):
                        if "oppervlak" in k.lower() or k in INTERESSANT:
                            print(f"    {k}: {vb[k]}")
            else:
                print(f"    status {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"    fout {e}")
        time.sleep(0.4)


def main():
    if not BAG_API_KEY:
        print("BAG_API_KEY ontbreekt", file=sys.stderr)
        return
    for adres in ADRESSEN:
        print(f"\n{'=' * 70}\n{adres}\n{'=' * 70}")
        bevraag(adres)


if __name__ == "__main__":
    main()
