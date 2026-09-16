#!/usr/bin/env python3
"""
Houdt de regels bij die deze portefeuille raken, en meldt wanneer er een
wijzigt.

Twee bronnen, allebei van KOOP en allebei zonder sleutel:

  CVDR, de Centrale Voorziening Decentrale Regelgeving. Hierin staan de
  gemeentelijke verordeningen, waaronder de Huisvestingsverordening Nijmegen.
  Dit is de bron die ertoe doet: de opkoopbescherming, de WOZ-grenzen voor
  kamerverhuur en de weigeringsgronden staan daar, en ze veranderen.

  BWB, het Basiswettenbestand. De landelijke wetten: Huisvestingswet,
  Wet op belastingen van rechtsverkeer, Wet betaalbare huur.

Het script onthoudt per regeling de laatste wijzigingsdatum. Verandert die,
dan is dat een signaal: de regel waarop de brief rekent is aangepast.

Gebruik:
  python regelgeving_monitor.py            # controleer op wijzigingen
  python regelgeving_monitor.py --toon     # laat zien wat er wordt gevolgd
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import requests

SRU = "https://zoekservice.overheid.nl/sru/Search"
STATUS_PAD = "regelgeving_status.json"
GEMEENTE = "Nijmegen"

# Gemeentelijke verordeningen die deze portefeuille raken. De zoekterm moet
# breed genoeg zijn om een hernoemde verordening te blijven vinden.
GEMEENTELIJK = [
    ("huisvesting", "Huisvestingsverordening: opkoopbescherming, omzetting, "
                    "onttrekking en de WOZ-grenzen voor kamerverhuur"),
    ("erfgoed", "Erfgoedverordening: monumenten en beschermde stadsbeelden"),
    ("parkeer", "Parkeerverordening: parkeereis en vergunningen bij splitsing"),
    ("leegstand", "Leegstandverordening"),
    ("bouw", "Bouwverordening"),
]

# Landelijke wetten. De nummers zijn de vaste BWB-identificatie.
LANDELIJK = [
    ("BWBR0035303", "Huisvestingswet 2014"),
    ("BWBR0002740", "Wet op belastingen van rechtsverkeer, de overdrachtsbelasting"),
    ("BWBR0002672", "Uitvoeringsbesluit belastingen van rechtsverkeer"),
]

HEADERS = {"Accept": "application/xml",
           "User-Agent": "NijmegenVastgoedMonitor/1.0"}


def _tekst(element, naam):
    """Haalt de tekst uit het eerste element met deze naam, ongeacht namespace."""
    for el in element.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == naam and el.text:
            return el.text.strip()
    return ""


def bevraag(connection, query, aantal=50):
    """Eén SRU-bevraging, met herhaalpogingen want de dienst is weleens traag."""
    params = {
        "x-connection": connection,
        "version": "2.0",
        "operation": "searchRetrieve",
        "query": query,
        "maximumRecords": aantal,
    }
    url = SRU + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    for poging in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=(15, 60))
            if r.status_code == 503:
                raise RuntimeError("503 Service Unavailable")
            r.raise_for_status()
            return ET.fromstring(r.content)
        except Exception as e:
            if poging == 3:
                print(f"  bevraging mislukt ({connection}): {e}", file=sys.stderr)
                return None
            time.sleep(poging * 10)
    return None


def records(root):
    """De losse records uit een SRU-antwoord."""
    if root is None:
        return []
    uit = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] == "record":
            uit.append(el)
    return uit


def haal_gemeentelijk():
    """De Nijmeegse verordeningen die we volgen."""
    gevonden = {}
    for term, waarom in GEMEENTELIJK:
        query = (f'(creator=="{GEMEENTE}") and (title any "{term}")')
        root = bevraag("cvdr", query)
        for rec in records(root):
            titel = _tekst(rec, "title")
            if not titel or term.lower() not in titel.lower():
                continue
            sleutel = _tekst(rec, "identifier") or titel
            gevonden[sleutel] = {
                "titel": titel,
                "gewijzigd": (_tekst(rec, "modified")
                              or _tekst(rec, "issued")
                              or _tekst(rec, "date")),
                "geldig_vanaf": _tekst(rec, "inwerkingtredingDatum"),
                "geldig_tot": _tekst(rec, "uitwerkingtredingDatum"),
                "waarom": waarom,
                "bron": "gemeente",
                "url": _tekst(rec, "preferredUrl") or _tekst(rec, "publicatieurl"),
            }
        time.sleep(1)
    return gevonden


def haal_landelijk():
    """De landelijke wetten die we volgen."""
    gevonden = {}
    for bwb, naam in LANDELIJK:
        root = bevraag("BWB", f'(dcterms.identifier=="{bwb}")', aantal=5)
        recs = records(root)
        if not recs:
            continue
        rec = recs[0]
        gevonden[bwb] = {
            "titel": _tekst(rec, "title") or naam,
            "gewijzigd": (_tekst(rec, "modified") or _tekst(rec, "date")),
            "geldig_vanaf": _tekst(rec, "inwerkingtredingDatum"),
            "waarom": naam,
            "bron": "landelijk",
            "url": f"https://wetten.overheid.nl/{bwb}",
        }
        time.sleep(1)
    return gevonden


def lees_status():
    if not os.path.exists(STATUS_PAD):
        return {}
    try:
        with open(STATUS_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def schrijf_status(status):
    try:
        with open(STATUS_PAD, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Kon {STATUS_PAD} niet schrijven: {e}", file=sys.stderr)


def render(wijzigingen, nieuw):
    """Alleen iets tonen als er werkelijk iets is veranderd."""
    if not wijzigingen and not nieuw:
        return []
    r = ["", "## Regelgeving gewijzigd", ""]
    for sleutel, was, wordt in wijzigingen:
        r.append(f"- **{wordt['titel']}** is gewijzigd: laatste wijziging staat nu "
                 f"op {wordt.get('gewijzigd') or 'onbekend'}, was "
                 f"{was.get('gewijzigd') or 'onbekend'}."
                 + (f" [bekijken]({wordt['url']})" if wordt.get("url") else ""))
        r.append(f"  _Waarom dit telt: {wordt['waarom']}._")
    for sleutel, wordt in nieuw:
        r.append(f"- **{wordt['titel']}** is nieuw in beeld."
                 + (f" [bekijken]({wordt['url']})" if wordt.get("url") else ""))
        r.append(f"  _Waarom dit telt: {wordt['waarom']}._")
    r.append("")
    r.append("_De brief rekent met deze regels. Verandert er een, controleer dan "
             "of de grenzen in het script nog kloppen: de WOZ-grenzen voor "
             "kamerverhuur en opkoopbescherming, de weigeringsgronden en de "
             "overdrachtsbelasting._")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toon", action="store_true",
                    help="laat zien wat er wordt gevolgd, zonder te vergelijken")
    ap.add_argument("--uit", default="")
    args = ap.parse_args()

    print("Regelgeving ophalen", file=sys.stderr)
    huidig = {}
    huidig.update(haal_gemeentelijk())
    huidig.update(haal_landelijk())

    if not huidig:
        print("Niets gevonden. De opzet van de SRU is mogelijk gewijzigd; "
              "controleer zoekservice.overheid.nl", file=sys.stderr)
        return

    print(f"  {len(huidig)} regelingen gevonden", file=sys.stderr)
    if args.toon:
        for sleutel, g in sorted(huidig.items(), key=lambda x: x[1]["titel"]):
            print(f"  {g['titel'][:70]:72} {g.get('gewijzigd', '')[:10]}",
                  file=sys.stderr)
        return

    vorig = lees_status()
    wijzigingen, nieuw = [], []
    for sleutel, g in huidig.items():
        was = vorig.get(sleutel)
        if not was:
            if vorig:          # bij de eerste run is alles nieuw, dat is geen signaal
                nieuw.append((sleutel, g))
        elif (was.get("gewijzigd") or "") != (g.get("gewijzigd") or ""):
            wijzigingen.append((sleutel, was, g))

    schrijf_status(huidig)

    regels = render(wijzigingen, nieuw)
    if regels:
        for r in regels:
            print(r)
        if args.uit:
            with open(args.uit, "w", encoding="utf-8") as f:
                f.write("\n".join(regels) + "\n")
        print(f"\n{len(wijzigingen)} gewijzigd, {len(nieuw)} nieuw", file=sys.stderr)
    else:
        print("Geen wijzigingen in de gevolgde regelgeving", file=sys.stderr)


if __name__ == "__main__":
    main()
