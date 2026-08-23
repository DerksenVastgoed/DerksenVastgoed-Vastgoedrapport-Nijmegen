#!/usr/bin/env python3
"""
Haalt de rijksmonumenten van Nijmegen op uit het Rijksmonumentenregister
en bewaart ze per adres, zodat marktprijzen_bag.py bij een pand kan tonen
of het een rijksmonument is.

Bron: Rijksdienst voor het Cultureel Erfgoed (RCE), Linked Open Data API.
Geen registratie of key nodig. De RCE vraagt wel om bronvermelding.

Gebruik:
  python rijksmonumenten.py                 # haalt Nijmegen op en schrijft het bestand
  python rijksmonumenten.py --debug         # toont ook welke velden de API teruggeeft
  python rijksmonumenten.py --plaats Lent   # andere woonplaats

Het bestand hoeft niet dagelijks ververst te worden; het register verandert
zelden. Eens per kwartaal meedraaien is ruim voldoende.
"""

import argparse
import json
import os
import re
import sys
import time

import requests

API = "https://api.linkeddata.cultureelerfgoed.nl/queries/rce/rest-api-rijksmonumenten/run"
UIT_PAD = "rijksmonumenten_nijmegen.json"
PAGINA_GROOTTE = 200
HEADERS = {"Accept": "application/json",
           "User-Agent": "NijmegenVastgoedMonitor/1.0"}

# Mogelijke veldnamen in de respons. De API is JSON-LD, dus de sleutels kunnen
# per query verschillen. We proberen ze op volgorde.
VELD_ADRES = ["volledigAdres", "adres", "volledigadres"]
VELD_STRAAT = ["straat", "straatnaam", "openbareRuimteNaam"]
VELD_POSTCODE = ["postcode"]
VELD_NUMMER = ["rijksmonumentnummer", "monumentnummer"]
VELD_FUNCTIE = ["oorspronkelijkeFunctie", "functie"]
VELD_AARD = ["monumentaard", "aard"]


def _pak(rij, namen):
    for naam in namen:
        waarde = rij.get(naam)
        if isinstance(waarde, list) and waarde:
            waarde = waarde[0]
        if waarde not in (None, ""):
            return str(waarde).strip()
    return ""


def sleutel(straat, huisnr):
    """Zelfde normalisatie als in de andere scripts, anders matcht niets."""
    s = straat.lower()
    s = s.replace("sint ", "st ").replace("st. ", "st ")
    s = s.replace("professor ", "prof ").replace("prof. ", "prof ")
    s = s.replace("burgemeester ", "burg ").replace("burg. ", "burg ")
    s = re.sub(r"[^a-z0-9]", "", s)
    return f"{s}{huisnr}"


def split_adres(volledig, straat_veld):
    """
    Haalt (straat, huisnummer) uit het adresveld.
    'Vondelstraat 77' -> ('Vondelstraat', '77')
    Valt terug op het losse straatveld als het nummer ontbreekt.
    """
    bron = (volledig or straat_veld or "").strip()
    if not bron:
        return None
    m = re.match(r"^(.+?)\s+(\d+)\s*[A-Za-z]?\s*$", bron)
    if not m:
        return None
    return m.group(1).strip(), m.group(2)


def haal_pagina(plaats, pagina, debug=False):
    params = {
        "woonplaatsnaam": plaats,
        "status": "rijksmonument",
        "page": pagina,
        "pageSize": PAGINA_GROOTTE,
    }
    laatste_fout = None
    for poging in range(1, 4):
        try:
            r = requests.get(API, params=params, headers=HEADERS, timeout=(20, 90))
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            laatste_fout = e
            if poging < 3:
                wacht = poging * 5
                print(f"  poging {poging} mislukt, opnieuw over {wacht}s", file=sys.stderr)
                time.sleep(wacht)
    else:
        print(f"  pagina {pagina} definitief mislukt: {laatste_fout}", file=sys.stderr)
        return None  # None = netwerkprobleem, [] = geen resultaten

    # De respons kan een lijst zijn, of een object met de lijst erin
    if isinstance(data, dict):
        for sleutelnaam in ("results", "data", "items", "@graph"):
            if isinstance(data.get(sleutelnaam), list):
                data = data[sleutelnaam]
                break
    if not isinstance(data, list):
        print(f"  onverwacht antwoord op pagina {pagina}: {type(data).__name__}", file=sys.stderr)
        return []

    if debug and data:
        print(f"  DEBUG velden in eerste record: {sorted(data[0].keys())}", file=sys.stderr)
        print(f"  DEBUG eerste record: "
              f"{json.dumps(data[0], ensure_ascii=False)[:600]}", file=sys.stderr)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plaats", default="Nijmegen")
    ap.add_argument("--uit", default=UIT_PAD)
    ap.add_argument("--debug", action="store_true",
                    help="toon de velden die de RCE-API teruggeeft")
    args = ap.parse_args()

    alles = {}
    zonder_adres = 0
    totaal = 0

    netwerkfout = False
    for pagina in range(1, 60):
        rijen = haal_pagina(args.plaats, pagina, args.debug and pagina == 1)
        if rijen is None:
            netwerkfout = True
            break
        if not rijen:
            break
        totaal += len(rijen)
        for rij in rijen:
            if not isinstance(rij, dict):
                continue
            volledig = _pak(rij, VELD_ADRES)
            straat_veld = _pak(rij, VELD_STRAAT)
            gesplitst = split_adres(volledig, straat_veld)
            if not gesplitst:
                zonder_adres += 1
                continue
            k = sleutel(*gesplitst)
            item = {
                "adres": volledig or f"{gesplitst[0]} {gesplitst[1]}",
                "nummer": _pak(rij, VELD_NUMMER),
                "postcode": _pak(rij, VELD_POSTCODE),
                "functie": _pak(rij, VELD_FUNCTIE),
                "aard": _pak(rij, VELD_AARD),
            }
            alles.setdefault(k, [])
            if not any(b.get("nummer") == item["nummer"] for b in alles[k]):
                alles[k].append(item)
        print(f"  pagina {pagina}: {len(rijen)} records", file=sys.stderr)
        if len(rijen) < PAGINA_GROOTTE:
            break
        time.sleep(0.5)

    if netwerkfout and not alles:
        print("De RCE-API was niet bereikbaar. Bestaand bestand blijft ongewijzigd.",
              file=sys.stderr)
        print("Tip: draai dit script een keer op je eigen computer en commit het "
              "resultaat. Het monumentenregister verandert nauwelijks.", file=sys.stderr)
        sys.exit(0)

    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(alles, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"Opgehaald: {totaal} records voor {args.plaats}", file=sys.stderr)
    print(f"Zonder bruikbaar huisnummer: {zonder_adres}", file=sys.stderr)
    print(f"Weggeschreven: {len(alles)} adressen naar {args.uit}", file=sys.stderr)
    if totaal and not alles:
        print("LET OP: records opgehaald maar geen adressen herkend. "
              "Draai met --debug om de veldnamen te zien.", file=sys.stderr)


if __name__ == "__main__":
    main()
