#!/usr/bin/env python3
"""
Koppelt de straten uit kamervergunningen.json aan een buurt, zodat de brief
per buurt kan tonen hoeveel kamerverhuurvergunningen er zijn verleend.

De vergunningenlijst van de gemeente noemt alleen straatnamen. Dit script zoekt
per straat eenmalig de buurt op bij PDOK en schrijft het resultaat weg. Dat
hoeft maar een keer: straten verhuizen niet.

Gebruik:
  python vergunningen_buurten.py

Resultaat: vergunningen_per_buurt.json
"""

import collections
import json
import os
import re
import sys
import time

import requests

BRON = "kamervergunningen.json"
UIT = "vergunningen_per_buurt.json"
STRAATCACHE = "straat_buurt_cache.json"
PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
HEADERS = {"User-Agent": "NijmegenVastgoedMonitor/1.0"}


def lees_cache():
    if os.path.exists(STRAATCACHE):
        try:
            with open(STRAATCACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def buurt_van_straat(straat, cache):
    """Zoekt de buurt van een straat op. Resultaten worden bewaard."""
    if straat in cache:
        return cache[straat]
    try:
        r = requests.get(PDOK, params={
            "q": f"{straat} Nijmegen", "fq": "type:weg", "rows": 1,
            "fl": "buurtnaam wijknaam weergavenaam",
        }, headers=HEADERS, timeout=20)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        buurt = docs[0].get("buurtnaam", "") if docs else ""
    except Exception as e:
        print(f"  fout bij {straat}: {e}", file=sys.stderr)
        buurt = ""
    cache[straat] = buurt
    time.sleep(0.2)
    return buurt


def main():
    if not os.path.exists(BRON):
        print(f"{BRON} niet gevonden", file=sys.stderr)
        return

    with open(BRON, encoding="utf-8") as f:
        vergunningen = json.load(f)

    # Straten tellen
    per_straat = collections.Counter()
    for lijst in vergunningen.values():
        for x in lijst:
            m = re.match(r"^(.+?)\s+\d", x.get("adres", ""))
            if m:
                per_straat[m.group(1).strip()] += 1

    print(f"{sum(per_straat.values())} vergunningen op "
          f"{len(per_straat)} straten", file=sys.stderr)

    cache = lees_cache()
    nieuw = sum(1 for s in per_straat if s not in cache)
    if nieuw:
        print(f"{nieuw} straten nog op te zoeken, ongeveer "
              f"{nieuw * 0.4 / 60:.0f} minuten", file=sys.stderr)

    per_buurt = collections.Counter()
    zonder_buurt = 0
    for i, (straat, aantal) in enumerate(per_straat.most_common(), 1):
        buurt = buurt_van_straat(straat, cache)
        if buurt:
            per_buurt[buurt] += aantal
        else:
            zonder_buurt += aantal
        if i % 25 == 0:
            print(f"  {i}/{len(per_straat)} straten", file=sys.stderr)
            with open(STRAATCACHE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)

    with open(STRAATCACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    with open(UIT, "w", encoding="utf-8") as f:
        json.dump(dict(per_buurt), f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"\nVergunningen per buurt, weggeschreven naar {UIT}:", file=sys.stderr)
    for buurt, n in per_buurt.most_common(15):
        print(f"  {n:>4}  {buurt}", file=sys.stderr)
    if zonder_buurt:
        print(f"  {zonder_buurt:>4}  buurt niet gevonden", file=sys.stderr)


if __name__ == "__main__":
    main()
