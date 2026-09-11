#!/usr/bin/env python3
"""
Bouwt een archief van Nijmeegse bekendmakingen die iets zeggen over
kamerverhuur, omzetting, splitsing, transformatie of brandveilig gebruik.

Het archief wordt per adres doorzoekbaar gemaakt, zodat marktprijzen_bag.py
bij een pand kan tonen of daar ooit iets over gepubliceerd is.

BELANGRIJK: een treffer is een SIGNAAL, geen bewijs van een geldige vergunning.
Het archief van officiele bekendmakingen gaat maar enkele jaren terug, en een
gepubliceerde aanvraag zegt niets over de uitkomst. Geen treffer betekent dus
uitdrukkelijk NIET dat er geen vergunning is.

Gebruik:
  python bekendmakingen_archief.py --vanaf 2026-05-01              # test, korte periode
  python bekendmakingen_archief.py --vanaf 2012-01-01              # volledige backfill

Voor de leefbaarheidstoets is een korte terugblik te weinig. De verordening
noemt geen termijn; de ambtelijke adviesgroep beoordeelt of het woonmilieu al
onder druk staat, en daar telt de opbouw over jaren in mee. Ga daarom zo ver
terug als de bron toelaat. De officiele bekendmakingen van gemeenten lopen
ongeveer terug tot 2012; eerder is er niets digitaal. Loopt de backfill
vast, dan kun je hem in stukken draaien: eerst 2012 tot 2016, dan verder.
Het archief wordt samengevoegd, dus meerdere keren draaien is veilig.
  python bekendmakingen_archief.py --vanaf 2026-08-01 --stil       # dagelijks bijwerken

Het archief wordt samengevoegd, niet overschreven. Meerdere keren draaien is veilig.
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

SRU_URL = "https://repository.overheid.nl/sru"
GEMEENTE = "Nijmegen"
ARCHIEF_PAD = "bekendmakingen_archief.json"
MAX_PER_PAGINA = 100

# Pauze tussen twee bevragingen. Bij een volledige backfill loopt dit op tot
# honderden verzoeken; te snel achter elkaar levert 503-fouten op.
PAUZE = float(os.environ.get("SRU_PAUZE", "1.0"))

# Alleen bekendmakingen die iets zeggen over het gebruik van een pand.
SIGNAALWOORDEN = {
    "kamerverhuur": ["kamerverhuur", "kamerbewoning", "onzelfstandige woonruimte",
                     "onzelfstandige wooneenhe", "verkamer"],
    "brandveilig gebruik": ["brandveilig gebruik"],
    "omzetting": ["omzetten", "omzetting", "omgezet"],
    "splitsing": ["splits", "woningvorming", "wooneenhe", "appartementsrecht"],
    "samenvoeging": ["samenvoeg"],
    "transformatie": ["transformatie", "herbestemm", "logiesfunctie",
                      "kantoorfunctie naar", "winkelfunctie naar"],
    "onttrekking": ["onttrekking", "onttrekken"],
    "tijdelijke verhuur": ["tijdelijk verhuren", "tijdelijke verhuur"],

    # Handhaving per adres. De politiecijfers gaan niet dieper dan de buurt,
    # maar handhavingsbesluiten worden wel per pand gepubliceerd. Voor de
    # leefbaarheidstoets en voor het risico bij aankoop is dat het enige
    # openbare signaal op objectniveau.
    "sluiting": ["sluiting van de woning", "sluiting van het pand", "woningsluiting",
                 "artikel 13b", "13b opiumwet", "sluitingsbevel", "gesloten verklaard"],
    "handhaving": ["last onder dwangsom", "last onder bestuursdwang", "bestuursdwang",
                   "bestuurlijke boete", "invordering dwangsom", "handhavingsbesluit",
                   "voornemen tot handhaving"],
    "onrechtmatig gebruik": ["onrechtmatige bewoning", "illegale bewoning",
                             "zonder vergunning verhuurd", "strijdig gebruik",
                             "in strijd met het bestemmingsplan"],
    "geluidsoverlast": ["geluidsoverlast", "geluidhinder", "geluidsklacht",
                        "akoestisch onderzoek", "hogere waarde", "geluidsnorm",
                        "wet geluidhinder", "geluidwerende", "geluidsisolatie",
                        "horecaoverlast", "overlastmelding", "sluitingstijd"],
}


def _lokaal(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _eerste_tekst(element, local_name):
    for el in element.iter():
        if _lokaal(el.tag) == local_name and el.text:
            return el.text.strip()
    return None


def _url_uit_record(record):
    for el in record.iter():
        if _lokaal(el.tag) == "itemUrl" and el.text:
            return el.text.strip()
    for el in record.iter():
        if _lokaal(el.tag) == "identifier" and el.text and el.text.startswith("http"):
            return el.text.strip()
    return ""


def haal_periode(vanaf, tot, stil=False):
    """Haalt records op voor een periode. Geeft een lijst XML-records terug."""
    cql = " and ".join([
        "c.product-area==officielepublicaties",
        "w.organisatietype==gemeente",
        f'dt.creator=="{GEMEENTE}"',
        f'dt.date>="{vanaf}"',
        f'dt.date<="{tot}"',
    ])
    records, start = [], 1
    while True:
        params = {"version": "2.0", "operation": "searchRetrieve", "query": cql,
                  "maximumRecords": MAX_PER_PAGINA, "startRecord": start}
        url = SRU_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        # De SRU gaat 503 geven als je te snel achter elkaar bevraagt. Bij een
        # fout dus wachten en opnieuw, met oplopende pauze. Dat is de enige
        # manier om de drukke maanden binnen te krijgen.
        root = None
        for poging in range(1, 5):
            try:
                resp = requests.get(url, timeout=(20, 90))
                if resp.status_code == 503:
                    raise RuntimeError("503 Service Unavailable")
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                break
            except Exception as e:
                if poging == 4:
                    print(f"  fout bij {vanaf}..{tot} vanaf record {start}: {e}",
                          file=sys.stderr)
                    break
                wacht = poging * 20
                if not stil:
                    print(f"    {vanaf} record {start}: poging {poging} mislukt, "
                          f"opnieuw over {wacht}s", file=sys.stderr)
                time.sleep(wacht)
        if root is None:
            break
        pagina = [el for el in root.iter() if _lokaal(el.tag) == "record"]
        if not pagina:
            break
        records.extend(pagina)
        totaal = _eerste_tekst(root, "numberOfRecords")
        totaal = int(totaal) if totaal and totaal.isdigit() else len(records)
        start += MAX_PER_PAGINA
        if start > totaal or start > 4000:
            break
        time.sleep(PAUZE)
    if not stil:
        print(f"  {vanaf}..{tot}: {len(records)} records", file=sys.stderr)
    time.sleep(PAUZE * 2)   # adempauze voordat het volgende blok begint
    return records


def adres_uit_titel(titel):
    """Haalt (straat, huisnummer) uit een bekendmakingstitel. Neemt de laatste 'aan'."""
    pc = re.search(r",?\s+\d{4}\s?[A-Z]{2}\s+Nijmegen", titel)
    if not pc:
        return None
    kop = titel[:pc.start()]
    delen = re.split(r"\baan\s+", kop, flags=re.IGNORECASE)
    if len(delen) < 2:
        return None
    straatdeel = delen[-1].strip().rstrip(",").strip()
    straatdeel = re.split(r"\s+en\s+\d", straatdeel)[0].strip()
    a = re.match(r"^(.+?)\s+(\d+)\s*([A-Za-z])?\s*$", straatdeel)
    if not a:
        return None
    return a.group(1).strip(), a.group(2)


def sleutel(straat, huisnr):
    """Normaliseert straat+nummer tot een matchbare sleutel."""
    s = straat.lower()
    s = s.replace("sint ", "st ").replace("st. ", "st ")
    s = s.replace("professor ", "prof ").replace("prof. ", "prof ")
    s = s.replace("burgemeester ", "burg ").replace("burg. ", "burg ")
    s = re.sub(r"[^a-z0-9]", "", s)
    return f"{s}{huisnr}"


def signalen_in(titel):
    """Welke soorten signalen zitten in deze titel?"""
    laag = titel.lower()
    gevonden = []
    for soort, woorden in SIGNAALWOORDEN.items():
        if any(w in laag for w in woorden):
            gevonden.append(soort)
    return gevonden


def lees_archief():
    if not os.path.exists(ARCHIEF_PAD):
        return {}
    try:
        with open(ARCHIEF_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def schrijf_archief(archief):
    with open(ARCHIEF_PAD, "w", encoding="utf-8") as f:
        json.dump(archief, f, ensure_ascii=False, indent=1, sort_keys=True)


def maanden(vanaf, tot):
    """Splitst een periode in maandblokken, zodat we onder de recordlimiet blijven."""
    d = dt.date.fromisoformat(vanaf)
    eind = dt.date.fromisoformat(tot)
    while d <= eind:
        if d.month == 12:
            volgende = dt.date(d.year + 1, 1, 1)
        else:
            volgende = dt.date(d.year, d.month + 1, 1)
        blok_eind = min(volgende - dt.timedelta(days=1), eind)
        yield d.isoformat(), blok_eind.isoformat()
        d = volgende


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanaf", required=True, help="startdatum, bv 2023-01-01")
    ap.add_argument("--tot", default=dt.date.today().isoformat())
    ap.add_argument("--stil", action="store_true", help="minder logregels")
    args = ap.parse_args()

    archief = lees_archief()
    voor = sum(len(v) for v in archief.values())
    print(f"Archief bij start: {len(archief)} adressen, {voor} publicaties", file=sys.stderr)

    totaal_records = 0
    nieuw = 0
    for blok_van, blok_tot in maanden(args.vanaf, args.tot):
        records = haal_periode(blok_van, blok_tot, args.stil)
        totaal_records += len(records)
        for rec in records:
            titel = _eerste_tekst(rec, "title") or ""
            if not titel:
                continue
            soorten = signalen_in(titel)
            if not soorten:
                continue
            adres = adres_uit_titel(titel)
            if not adres:
                continue
            k = sleutel(*adres)
            datum = _eerste_tekst(rec, "date") or _eerste_tekst(rec, "available") or ""
            item = {
                "datum": datum,
                "titel": titel,
                "soorten": soorten,
                "url": _url_uit_record(rec),
            }
            bestaand = archief.setdefault(k, [])
            if not any(b.get("titel") == titel and b.get("datum") == datum for b in bestaand):
                bestaand.append(item)
                nieuw += 1

    for k in archief:
        archief[k].sort(key=lambda x: x.get("datum", ""), reverse=True)

    schrijf_archief(archief)
    na = sum(len(v) for v in archief.values())
    print(f"Doorzocht: {totaal_records} records", file=sys.stderr)
    print(f"Nieuw toegevoegd: {nieuw} publicaties", file=sys.stderr)
    print(f"Archief nu: {len(archief)} adressen, {na} publicaties", file=sys.stderr)


if __name__ == "__main__":
    main()
