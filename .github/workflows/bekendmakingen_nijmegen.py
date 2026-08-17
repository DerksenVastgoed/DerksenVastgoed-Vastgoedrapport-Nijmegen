#!/usr/bin/env python3
"""
Bekendmakingen-blok voor de Nijmegen Vastgoedmonitor.

Haalt officiele bekendmakingen (gemeenteblad e.d.) van gemeente Nijmegen op via
de KOOP SRU-API, filtert op de ring rond het Keizer Karelplein en op
vastgoed-relevante types, en schrijft een dagelijkse digest weg als markdown.

Bron:  https://repository.overheid.nl/sru   (collectie: officielepublicaties)
Open data, geen sleutel nodig. Draai dit op een machine met internettoegang.

Gebruik:
    python bekendmakingen_nijmegen.py                 # laatste 2 dagen, print + schrijft digest
    python bekendmakingen_nijmegen.py --dagen 7       # ruimere terugblik
    python bekendmakingen_nijmegen.py --alles         # geen ringfilter, hele gemeente

Let op: dit is v1, geschreven tegen de SRU-documentatie maar nog niet live
getest. Draai het, en als er iets misgaat: plak de foutmelding of een stuk
van de ruwe XML terug, dan scherpen we de parsing en de query samen aan.
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

# Ringfilter. Een bekendmaking wordt getoond als de titel een van deze
# postcode-prefixes OF een van deze straatnamen bevat. Begin ruim, snoei later.
RING_POSTCODES = ["6511", "6512", "6521", "6522", "6524", "6525", "6541", "6542"]

RING_STRATEN = [
    # eigen panden
    "Graafsedwarsstraat", "Eerste Oude Heselaan",
    # acquisitietargets
    "Fransestraat", "Van Spaenstraat",
    # kernstraten van de ring (uitbreidbaar na eerste echte output)
    "Bottendaalseweg", "Groesbeekseweg", "Berg en Dalseweg", "Sint Annastraat",
    "Graafseweg", "Voorstadslaan", "Waterstraat", "Biezenstraat",
]

# Alleen deze publicatie-types tonen (vastgoed-relevant). Match op woorden in
# titel of type. Leeg maken = alle types tonen.
RELEVANTE_TREFWOORDEN = [
    "omgevingsvergunning", "bouw", "sloop", "splits", "onttrekking",
    "transformatie", "ruimtelijk plan", "omgevingsplan", "omgevingsdocument",
    "bestemmingsplan", "kadastr", "aanvraag", "verleend", "monument",
]

MAX_PER_PAGINA = 100  # SRU maximumRecords per call
# --------------------------------------------------------------------------


def bouw_cql(vanaf_datum: str) -> str:
    """CQL-query: gemeente Nijmegen, publicatiedatum vanaf, collectie officiele publicaties."""
    delen = [
        'c.product-area==officielepublicaties',
        'w.organisatietype==gemeente',
        f'dt.creator=="{GEMEENTE}"',
        f'dt.date>="{vanaf_datum}"',
    ]
    return " and ".join(delen)


def haal_records(cql: str):
    """Loop over alle SRU-pagina's en geef de ruwe <record>-elementen terug."""
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

        # namespace-agnostisch: pak alle elementen met local-name 'record'
        pagina = [el for el in root.iter() if _lokaal(el.tag) == "record"]
        if not pagina:
            break
        records.extend(pagina)

        totaal = _eerste_tekst(root, "numberOfRecords")
        totaal = int(totaal) if totaal and totaal.isdigit() else len(records)
        start += MAX_PER_PAGINA
        if start > totaal or start > 4200:  # SRU-plafond
            break
    return records


def _lokaal(tag: str) -> str:
    """Strip de namespace van een XML-tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _eerste_tekst(element, local_name: str):
    for el in element.iter():
        if _lokaal(el.tag) == local_name and el.text:
            return el.text.strip()
    return None


def _url_uit_record(record):
    """Zoek de voorkeurs-URL of eerste http-link in het record."""
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
        "creator": _eerste_tekst(record, "creator") or "",
        "url": _url_uit_record(record) or "",
    }


def in_ring(item: dict) -> bool:
    hooi = (item["titel"] + " " + item["type"]).lower()
    if any(pc in hooi for pc in RING_POSTCODES):
        return True
    if any(straat.lower() in hooi for straat in RING_STRATEN):
        return True
    return False


def is_relevant(item: dict) -> bool:
    if not RELEVANTE_TREFWOORDEN:
        return True
    hooi = (item["titel"] + " " + item["type"]).lower()
    return any(tw in hooi for tw in RELEVANTE_TREFWOORDEN)


def render_digest(items: list, vanaf: str) -> str:
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    regels = [f"# Bekendmakingen ring Keizer Karelplein - {vandaag}",
              f"_Gemeente {GEMEENTE}, publicaties vanaf {vanaf}. {len(items)} relevante berichten._", ""]
    if not items:
        regels.append("Geen nieuwe relevante bekendmakingen in de ring. Rustige dag.")
        return "\n".join(regels)
    for it in sorted(items, key=lambda x: x["datum"], reverse=True):
        titel = it["titel"]
        link = f"([bron]({it['url']}))" if it["url"] else ""
        regels.append(f"- **{it['datum']}** . {titel} {link}")
    return "\n".join(regels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dagen", type=int, default=2, help="terugblik in dagen")
    ap.add_argument("--alles", action="store_true", help="geen ringfilter")
    ap.add_argument("--uit", default="bekendmakingen_digest.md", help="uitvoerbestand")
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
    items = [it for it in items if is_relevant(it)]
    if not args.alles:
        items = [it for it in items if in_ring(it)]

    # dedup op titel+datum
    gezien, uniek = set(), []
    for it in items:
        sleutel = (it["titel"], it["datum"])
        if sleutel not in gezien:
            gezien.add(sleutel)
            uniek.append(it)

    digest = render_digest(uniek, vanaf)
    print(digest)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"\nDigest opgeslagen in {args.uit}", file=sys.stderr)


if __name__ == "__main__":
    main()
