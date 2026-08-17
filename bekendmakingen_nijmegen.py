#!/usr/bin/env python3
"""
Bekendmakingen-blok voor de Nijmegen Vastgoedmonitor.

Haalt officiele bekendmakingen (gemeenteblad e.d.) van gemeente Nijmegen op via
de KOOP SRU-API, filtert op de ring rond het Keizer Karelplein, gooit ruis weg,
en splitst de rest in KERNSIGNALEN (splitsen, samenvoegen, transformatie e.d.)
en OVERIGE relevante bekendmakingen. Schrijft het geheel weg als markdown.

Bron:  https://repository.overheid.nl/sru   (collectie: officielepublicaties)
Open data, geen sleutel nodig. Draai dit op een machine met internettoegang.

Gebruik:
    python bekendmakingen_nijmegen.py
    python bekendmakingen_nijmegen.py --dagen 7
    python bekendmakingen_nijmegen.py --alles      # geen ringfilter
"""

import argparse
import datetime as dt
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import requests

# --------------------------------------------------------------------------
# CONFIG - dit is het enige wat je aanpast
# --------------------------------------------------------------------------
SRU_URL = "https://repository.overheid.nl/sru"
GEMEENTE = "Nijmegen"

RING_POSTCODES = ["6511", "6512", "6521", "6522", "6524", "6525", "6541", "6542"]

RING_STRATEN = [
    "Graafsedwarsstraat", "Eerste Oude Heselaan",
    "Fransestraat", "Van Spaenstraat",
    "Bottendaalseweg", "Groesbeekseweg", "Berg en Dalseweg", "Sint Annastraat",
    "Graafseweg", "Voorstadslaan", "Waterstraat", "Biezenstraat",
]

# 1. RUIS: bevat de titel een van deze woorden, dan valt het bericht weg.
UITSLUITEN = [
    "reclame", "uithangbord", "gevelbelettering", "naambord", "sticker",
    "spandoek", "vlaggenmast", "dakkapel", "dakterras", "dakraam", "veranda",
    "overkapping", "carport", "airco", "oprit", "inrit", "puinbak", "container",
    "hekwerk", "erfafscheiding", "schutting", "schuur", "tuinhuis", "zwembad",
    "alcohol", "leidinggevende", "exploitatievergunning", "terras", "evenement",
    "standplaats", "kappen", "kapvergunning", "boom", "bomen",
    "termijnverlenging", "buiten behandeling", "intrekking", "rectificatie",
]

# 2. KERNSIGNALEN: de waardecreatie-bewegingen. Deze komen bovenaan.
#    Kern wint altijd van de uitsluitlijst.
KERN = [
    "splits", "samenvoeg", "omzetten", "omgezet", "omzetting",
    "zelfstandige woon", "zelfstandige wooneenhe", "zelfstandige woning",
    "wooneenhe", "appartement", "transformatie", "herbestemm",
    "kamerverhuur", "logiesfunctie", "logies", "bopa",
    "nieuwbouw", "starters", "optoppen", "woningen",
]

# 3. OVERIG RELEVANT: vastgoed-ingrepen die er wel toe doen maar geen kern zijn.
REL_BASIS = [
    "verbouw", "renove", "verduurz", "sloop", "woning", "woon", "warmtepomp",
    "monument", "pand", "klooster", "nokverhoging", "dakopbouw", "uitbouw",
    "aanbouw", "kozijn", "pui", "gevel",
]

MAX_PER_PAGINA = 100
# --------------------------------------------------------------------------


def bouw_cql(vanaf_datum: str) -> str:
    delen = [
        "c.product-area==officielepublicaties",
        "w.organisatietype==gemeente",
        f'dt.creator=="{GEMEENTE}"',
        f'dt.date>="{vanaf_datum}"',
    ]
    return " and ".join(delen)


def haal_records(cql: str):
    records = []
    start = 1
    while True:
        params = {
            "version": "2.0",
            "operation": "searchRetrieve",
            "query": cql,
            "maximumRecords": MAX_PER_PAGINA,
            "startRecord": start,
        }
        url = SRU_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        pagina = [el for el in root.iter() if _lokaal(el.tag) == "record"]
        if not pagina:
            break
        records.extend(pagina)
        totaal = _eerste_tekst(root, "numberOfRecords")
        totaal = int(totaal) if totaal and totaal.isdigit() else len(records)
        start += MAX_PER_PAGINA
        if start > totaal or start > 4200:
            break
    return records


def _lokaal(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _eerste_tekst(element, local_name: str):
    for el in element.iter():
        if _lokaal(el.tag) == local_name and el.text:
            return el.text.strip()
    return None


def _url_uit_record(record):
    for el in record.iter():
        naam = _lokaal(el.tag)
        if naam in ("preferredUrl", "itemUrl") and el.text and el.text.startswith("http"):
            return el.text.strip()
    for el in record.iter():
        for waarde in el.attrib.values():
            if isinstance(waarde, str) and waarde.startswith("http"):
                return waarde
    return None


def parse_record(record) -> dict:
    return {
        "titel": _eerste_tekst(record, "title") or "(geen titel)",
        "datum": _eerste_tekst(record, "date") or _eerste_tekst(record, "available") or "",
        "type": _eerste_tekst(record, "type") or "",
        "url": _url_uit_record(record) or "",
    }


def in_ring(item: dict) -> bool:
    hooi = (item["titel"] + " " + item["type"]).lower()
    if any(pc in hooi for pc in RING_POSTCODES):
        return True
    return any(s.lower() in hooi for s in RING_STRATEN)


def classificeer(item: dict):
    """Geeft 'kern', 'overige' of None terug."""
    hooi = (item["titel"] + " " + item["type"]).lower()
    if any(w in hooi for w in KERN):
        return "kern"
    if any(w in hooi for w in UITSLUITEN):
        return None
    if any(w in hooi for w in REL_BASIS):
        return "overige"
    return None


def _regel(it: dict) -> str:
    link = f"([bron]({it['url']}))" if it["url"] else ""
    return f"- **{it['datum']}** . {it['titel']} {link}"


def render_digest(kern: list, overige: list, vanaf: str) -> str:
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    r = [f"# Bekendmakingen ring Keizer Karelplein - {vandaag}",
         f"_Gemeente {GEMEENTE}, publicaties vanaf {vanaf}. "
         f"{len(kern)} kernsignalen, {len(overige)} overige._", ""]

    r.append(f"## Kernsignalen ({len(kern)})")
    r.append("_Splitsen, samenvoegen, omzetten, transformatie, kamerverhuur, nieuwbouw._")
    r.append("")
    if kern:
        for it in sorted(kern, key=lambda x: x["datum"], reverse=True):
            r.append(_regel(it))
    else:
        r.append("Geen kernsignalen in deze periode.")
    r.append("")

    if overige:
        r.append(f"## Overige relevante bekendmakingen ({len(overige)})")
        r.append("_Verbouw, renovatie, sloop, verduurzaming e.d._")
        r.append("")
        for it in sorted(overige, key=lambda x: x["datum"], reverse=True):
            r.append(_regel(it))
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dagen", type=int, default=2)
    ap.add_argument("--alles", action="store_true")
    ap.add_argument("--uit", default="bekendmakingen_digest.md")
    args = ap.parse_args()

    vanaf = (dt.date.today() - dt.timedelta(days=args.dagen)).isoformat()
    cql = bouw_cql(vanaf)
    print(f"Query: {cql}", file=sys.stderr)

    try:
        records = haal_records(cql)
    except Exception as e:  # noqa
        print(f"Ophalen mislukt: {e}", file=sys.stderr)
        sys.exit(1)

    items = [parse_record(r) for r in records]
    if not args.alles:
        items = [it for it in items if in_ring(it)]

    gezien, kern, overige = set(), [], []
    for it in items:
        sleutel = (it["titel"], it["datum"])
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        soort = classificeer(it)
        if soort == "kern":
            kern.append(it)
        elif soort == "overige":
            overige.append(it)

    digest = render_digest(kern, overige, vanaf)
    print(digest)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"\nDigest opgeslagen in {args.uit}", file=sys.stderr)


if __name__ == "__main__":
    main()
