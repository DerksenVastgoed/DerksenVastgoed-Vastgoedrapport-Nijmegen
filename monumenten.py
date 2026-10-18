#!/usr/bin/env python3
"""
Gemeentelijke monumenten in Nijmegen, uit twee open bronnen naast elkaar.

WAAROM TWEE. 18 oktober 2026: het omgevingsplan heeft geen informatieobject
voor gemeentelijke monumenten, nijmegen.nl sluit op de monumentenlijst geen
bestand of kaart in, de GeoServer gaf 401 en de catalogus van data.overheid.nl
gaf nul datasets. Het register dat de Erfgoedverordening voorschrijft
(CVDR731607, art. 2) is dus niet als bestand te vinden. Twee bronnen die er
elk een deel van dekken:

1. AANWIJZINGSBESLUITEN in het Gemeenteblad, via de open SRU-zoekdienst van
   de officiele bekendmakingen. Officieel en met datum, maar elektronisch
   pas vanaf ongeveer 2014; oudere aanwijzingen ontbreken.
2. WIKIDATA, de door vrijwilligers bijgehouden lijst, open onder CC0, vaak
   met coordinaten. Niet officieel, dus nooit zonder die vermelding.

Waar ze het eens zijn, is het sterk; waar alleen Wikidata een monument kent,
is het waarschijnlijk een oude aanwijzing. Dit is een verkenning: eerst zien
wat er komt, voordat het dossier erop leunt.

  python3 monumenten.py --verken
  python3 monumenten.py --proef
"""
import argparse
import json
import re
import sys
import urllib.parse

import stadsbeeld  # mag() en haal(): robots.txt eerst, een implementatie

SRU = "https://repository.overheid.nl/sru"
# Een paar varianten, want de indexnamen van deze dienst zijn hier niet
# nagekeken. Het verslag zegt per variant hoeveel er terugkwam.
SRU_VRAGEN = [
    'dt.creator="Nijmegen" and cql.textAndIndexes="gemeentelijk monument"',
    'dt.creator="Nijmegen" and dt.title any "monument"',
    'cql.textAndIndexes="Nijmegen" and cql.textAndIndexes="aanwijzing '
    'gemeentelijk monument"',
]
WIKIDATA = "https://query.wikidata.org/sparql"
# Het label in de vraag zelf in plaats van een vast Q-nummer, zodat een
# verkeerd onthouden nummer niet stil nul oplevert.
SPARQL = """
SELECT ?item ?itemLabel ?adres ?coord ?aanduidingLabel WHERE {
  ?aanduiding rdfs:label "gemeentelijk monument"@nl .
  ?item wdt:P1435 ?aanduiding ;
        wdt:P131 ?plaats .
  ?plaats rdfs:label "Nijmegen"@nl .
  OPTIONAL { ?item wdt:P6375 ?adres . }
  OPTIONAL { ?item wdt:P625 ?coord . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "nl". }
}
"""
UIT_GMB = "monumenten_gemeenteblad.json"
UIT_WD = "monumenten_wikidata.json"
VERSLAG = "monumenten_bronnen_verslag.md"


def records_uit_sru(xml):
    """[(titel, url, datum)] uit een SRU-antwoord, of None als het geen
    SRU-antwoord is."""
    if not xml or "searchRetrieveResponse" not in xml:
        return None
    uit = []
    for rec in re.findall(r"<(?:\w+:)?record>(.*?)</(?:\w+:)?record>", xml,
                          re.S):
        titel = re.search(r"<dcterms:title>([^<]*)</dcterms:title>", rec)
        url = re.search(r"<(?:\w+:)?preferredUrl>([^<]*)<", rec)
        datum = re.search(r"<dcterms:available>([^<]*)<", rec)
        uit.append(((titel.group(1) if titel else "").strip(),
                    (url.group(1) if url else "").strip(),
                    (datum.group(1) if datum else "").strip()))
    return uit


def aantal_uit_sru(xml):
    m = re.search(r"<(?:\w+:)?numberOfRecords>(\d+)<", xml or "")
    return int(m.group(1)) if m else None


def rijen_uit_sparql(antwoord):
    """[{item, naam, adres, lon, lat}] uit een SPARQL-JSON-antwoord, of None."""
    try:
        d = json.loads(antwoord)
    except ValueError:
        return None
    uit = []
    for b in (d.get("results") or {}).get("bindings") or []:
        rij = {"item": (b.get("item") or {}).get("value"),
               "naam": (b.get("itemLabel") or {}).get("value"),
               "adres": (b.get("adres") or {}).get("value")}
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)",
                     (b.get("coord") or {}).get("value") or "")
        if m:
            rij["lon"], rij["lat"] = float(m.group(1)), float(m.group(2))
        uit.append(rij)
    return uit


def verken():
    r = ["# Gemeentelijke monumenten: twee open bronnen", ""]
    r.append("## Gemeenteblad (SRU)")
    beste = []
    for vraag in SRU_VRAGEN:
        url = SRU + "?" + urllib.parse.urlencode({
            "operation": "searchRetrieve", "version": "2.0",
            "query": vraag, "maximumRecords": "200"})
        _e, _s, inhoud = stadsbeeld.haal(url, r)
        tekst = inhoud.decode("utf-8", "replace") if inhoud else ""
        recs = records_uit_sru(tekst)
        r.append(f"- `{vraag}`: totaal {aantal_uit_sru(tekst)}, gelezen "
                 f"{'onleesbaar' if recs is None else len(recs)}")
        for t, u, d in (recs or [])[:8]:
            r.append(f"  - {d} {t[:140]} ({u})")
        if recs and len(recs) > len(beste):
            beste = recs
    with open(UIT_GMB, "w", encoding="utf-8") as f:
        json.dump([{"titel": t, "url": u, "datum": d} for t, u, d in beste],
                  f, ensure_ascii=False, indent=1)
    r.append("")
    r.append("## Wikidata")
    url = WIKIDATA + "?" + urllib.parse.urlencode({
        "query": SPARQL, "format": "json"})
    _e, _s, inhoud = stadsbeeld.haal(url, r)
    rijen = rijen_uit_sparql(inhoud.decode("utf-8", "replace")) \
        if inhoud else None
    if rijen is None:
        r.append("- geen leesbaar antwoord")
    else:
        met_coord = sum(1 for x in rijen if "lat" in x)
        met_adres = sum(1 for x in rijen if x.get("adres"))
        r.append(f"- {len(rijen)} rijen, {met_coord} met coordinaten, "
                 f"{met_adres} met adres")
        for x in rijen[:10]:
            r.append(f"  - {x.get('naam')} | {x.get('adres')} | "
                     f"{x.get('lat')}, {x.get('lon')}")
        with open(UIT_WD, "w", encoding="utf-8") as f:
            json.dump({"bron": "Wikidata, CC0, niet officieel",
                       "rijen": rijen}, f, ensure_ascii=False, indent=1)
    with open(VERSLAG, "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    print("\n".join(r))
    return 0


def proef():
    afw = []
    sru = ("<sru:searchRetrieveResponse><sru:numberOfRecords>2"
           "</sru:numberOfRecords><sru:record><dcterms:title>Aanwijzing "
           "gemeentelijk monument Hertogstraat 13</dcterms:title>"
           "<gzd:preferredUrl>https://x/gmb-1.html</gzd:preferredUrl>"
           "<dcterms:available>2023-01-02</dcterms:available></sru:record>"
           "</sru:searchRetrieveResponse>")
    if records_uit_sru(sru) != [("Aanwijzing gemeentelijk monument "
                                 "Hertogstraat 13", "https://x/gmb-1.html",
                                 "2023-01-02")]:
        afw.append(f"SRU-records worden niet gelezen: {records_uit_sru(sru)}")
    if aantal_uit_sru(sru) != 2:
        afw.append("het totaal uit SRU wordt niet gelezen")
    if records_uit_sru("<html>fout</html>") is not None:
        afw.append("een onleesbaar SRU-antwoord telt als nul besluiten")
    sp = json.dumps({"results": {"bindings": [{
        "item": {"value": "http://www.wikidata.org/entity/Q1"},
        "itemLabel": {"value": "Hertogstraat 13"},
        "coord": {"value": "Point(5.86 51.84)"}}]}})
    rij = (rijen_uit_sparql(sp) or [{}])[0]
    if (rij.get("lon"), rij.get("lat")) != (5.86, 51.84):
        afw.append(f"de coordinaten uit Wikidata worden niet gelezen: {rij}")
    if rijen_uit_sparql("<html>") is not None:
        afw.append("een onleesbaar Wikidata-antwoord telt als nul monumenten")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef monumenten: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verken", action="store_true")
    ap.add_argument("--proef", action="store_true")
    a = ap.parse_args()
    if a.proef:
        return proef()
    if a.verken:
        return verken()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
