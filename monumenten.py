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


# DE BRON VAN DE GEMEENTE ZELF. Gevonden op 18 oktober via de KaartViewer
# (kaartviewer.py): de kaart Historie, map Monumenten, heeft de lagen
# "Beschermde objecten" (extern_Monumenten:HIS_MON_MONUMENT) en "Beschermde
# gebieden" (extern_Monumenten:HIS_MON_BESCHERMDE_GEB). Andere werkruimtes
# van dezelfde server geven WFS met outputFormat, dus hier ook proberen.
WFS = "https://services.nijmegen.nl/geoservices/extern_Monumenten/ows"
WFS_LAGEN = ("extern_Monumenten:HIS_MON_MONUMENT",
             "extern_Monumenten:HIS_MON_BESCHERMDE_GEB")


def verken_wfs():
    import collections
    r = ["# Monumenten uit de GeoServer van de gemeente", ""]
    for laag in WFS_LAGEN:
        url = WFS + "?" + urllib.parse.urlencode({
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": laag, "outputFormat": "application/json",
            "srsName": "EPSG:28992"})
        _e, soort, inhoud = stadsbeeld.haal(url, r)
        r.append(f"## {laag}")
        if inhoud is None:
            r.append("- niet opgehaald")
            continue
        try:
            d = json.loads(inhoud.decode("utf-8"))
        except ValueError:
            r.append(f"- geen JSON ({soort}): `{inhoud[:300]!r}`")
            continue
        fs = d.get("features") or []
        r.append(f"- {len(fs)} objecten")
        if fs:
            velden = sorted((fs[0].get("properties") or {}).keys())
            r.append(f"- velden: {velden}")
            for veld in velden:
                waarden = collections.Counter(
                    str((f.get("properties") or {}).get(veld)) for f in fs)
                if len(waarden) <= 12:
                    r.append(f"  - {veld}: {dict(waarden.most_common(12))}")
            for f in fs[:5]:
                r.append(f"  - voorbeeld: "
                         f"{json.dumps(f.get('properties'), ensure_ascii=False)[:400]}")
        naam = laag.split(":")[1].lower()
        with open(f"monumenten_{naam}.geojson", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        r.append("")
    with open("monumenten_wfs_verslag.md", "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    print("\n".join(r))
    return 0


# RCE-RIJKSMONUMENTEN ALS PUNTEN, VIA PDOK. 18 oktober 2026: het bestand van
# rijksmonumenten.py (RCE linked data, 45 minuten per run) bevat 76 unieke
# rijksmonumentnummers op 174 adressen, terwijl het erfgoedregister van de
# gemeente 206 objecten "Rijksmonument" kent. Dezelfde RCE publiceert de
# rijksmonumenten ook als punten in de PDOK-collectie die gezicht.py al
# gebruikt (rce_inspire_points, naamruimte nlps-rijksmonumenten). Dit haalt
# ze op voor de hele gemeente en vergelijkt de nummers met het register.
RCE_PUNTEN = ("https://api.pdok.nl/rce/beschermde-gebieden-cultuurhistorie/"
              "ogc/v1/collections/rce_inspire_points/items")
# De gemeente Nijmegen ruim, in WGS84 (lon, lat); de omhullende van de
# gemeentelijke lagen in RD is 170.170-200.457 bij 419.060-435.629.
GEMEENTE_BBOX = (5.72, 51.78, 5.97, 51.91)
UIT_RCE = "rijksmonumenten_rce_punten.json"


def nummer_uit_citatie(c):
    """Het rijksmonumentnummer uit ci_citation, zoals 'monumenten/341971'."""
    m = re.search(r"monumenten/(\d+)", c or "")
    return m.group(1) if m else None


def _gemeentegrens(r):
    url = ("https://services.nijmegen.nl/geoservices/extern_GEO_Gebiedsindelingen"
           "/ows?" + urllib.parse.urlencode({
               "service": "WFS", "version": "2.0.0", "request": "GetFeature",
               "typeNames": "extern_GEO_Gebiedsindelingen:GEO_IND_GEMEENTEGRENS",
               "outputFormat": "application/json", "srsName": "EPSG:28992"}))
    _e, _s, inhoud = stadsbeeld.haal(url, r)
    if inhoud is None:
        return None
    try:
        d = json.loads(inhoud.decode("utf-8"))
    except ValueError:
        return None
    uit = []
    for f in d.get("features") or []:
        g = f.get("geometry") or {}
        if g.get("type") == "Polygon":
            uit.append(g)
        elif g.get("type") == "MultiPolygon":
            uit += [{"type": "Polygon", "coordinates": c}
                    for c in g.get("coordinates") or []]
    return uit or None


def verken_rce():
    import time
    r = ["# Rijksmonumenten van de RCE als punten (PDOK)", ""]
    url = RCE_PUNTEN + "?" + urllib.parse.urlencode({
        "f": "json", "limit": "500",
        "bbox": ",".join(str(v) for v in GEMEENTE_BBOX)})
    punten, paginas = [], 0
    while url and paginas < 30:
        _e, _s, inhoud = stadsbeeld.haal(url, r)
        if inhoud is None:
            break
        d = json.loads(inhoud.decode("utf-8"))
        paginas += 1
        for f in d.get("features") or []:
            p = f.get("properties") or {}
            if p.get("namespace") != "nlps-rijksmonumenten":
                continue
            c = (f.get("geometry") or {}).get("coordinates") or [None, None]
            punten.append({"nummer": nummer_uit_citatie(p.get("ci_citation")),
                           "naam": p.get("text"), "lon": c[0], "lat": c[1],
                           "klasse": p.get("siteprotectionclassification"),
                           "aanduiding": p.get("designation")})
        url = next((l.get("href") for l in d.get("links") or []
                    if l.get("rel") == "next"), None)
        time.sleep(0.2)
    # BINNEN DE GEMEENTEGRENS. De eerste ronde gaf precies 500 punten op een
    # bbox die ook Ubbergen, Groesbeek en Beuningen raakt. De grens komt van
    # dezelfde GeoServer als het register (extern_GEO_Gebiedsindelingen).
    grens = _gemeentegrens(r)
    if grens:
        import gezicht
        binnen = []
        for x in punten:
            if x["lat"] is None:
                continue
            gx, gy = gezicht.wgs84_naar_rd(x["lat"], x["lon"])
            if any(gezicht.in_vlak(gx, gy, v) for v in grens):
                binnen.append(x)
        r.append(f"- binnen de gemeentegrens: {len(binnen)} van "
                 f"{len(punten)}")
        punten = binnen
    else:
        r.append("- gemeentegrens niet te lezen; punten niet gefilterd")
    nummers = {x["nummer"] for x in punten if x["nummer"]}
    r.append(f"- {len(punten)} punten, {len(nummers)} unieke nummers, "
             f"{paginas} pagina's, {'volledig' if url is None else 'NIET VOLLEDIG'}")
    try:
        with open("monumenten_his_mon_monument.geojson", encoding="utf-8") as f:
            reg = json.load(f).get("features") or []
        # Het register schrijft soms "31114 " of "31177 en 31178".
        regnr = {n for x in reg
                 for n in re.findall(r"\d{4,6}",
                                     str(x["properties"].get("RIJKSOBJECTCODE")
                                         or ""))}
        r.append(f"- register: {len(regnr)} objecten met een "
                 f"rijksmonumentnummer; in beide {len(nummers & regnr)}, "
                 f"alleen RCE {len(nummers - regnr)}, alleen register "
                 f"{len(regnr - nummers)}")
        r.append(f"  - alleen RCE, voorbeelden: {sorted(nummers - regnr)[:15]}")
        r.append(f"  - alleen register, voorbeelden: "
                 f"{sorted(regnr - nummers)[:15]}")
    except (OSError, ValueError):
        r.append("- register niet te lezen")
    try:
        with open("rijksmonumenten_nijmegen.json", encoding="utf-8") as f:
            oud = json.load(f)
        oudnr = {nummer_uit_citatie(x.get("nummer")) or
                 re.sub(r"\D", "", x.get("nummer") or "")
                 for v in oud.values() for x in v}
        oudnr.discard("")
        r.append(f"- rijksmonumenten_nijmegen.json: {len(oudnr)} nummers, "
                 f"waarvan {len(oudnr & nummers)} ook als RCE-punt")
    except (OSError, ValueError):
        pass
    with open(UIT_RCE, "w", encoding="utf-8") as f:
        json.dump({"bron": "RCE via PDOK, rce_inspire_points, CC BY 4.0",
                   "punten": punten}, f, ensure_ascii=False)
    with open("rijksmonumenten_rce_verslag.md", "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    print("\n".join(r))
    return 0


# RCE-PUNT NAAR PAND. 18 oktober 2026: van de 261 rijksmonumenten (RCE-punten)
# staan er 66 niet in het erfgoedregister, en voor die 66 wisten we niet in
# welk pand ze liggen: een RCE-punt is een punt, en wij kennen per pand ook
# alleen een punt. De BAG kent per pand de omtrek. Per RCE-punt vraagt dit de
# panden waarvan de omtrek een vierkant van een meter rond het punt raakt, bij
# de BAG-WFS van PDOK. Voor alle 261, niet alleen de 66, zodat de koppeling
# te toetsen is tegen het register: waar beide een pand noemen, horen ze
# hetzelfde pand te noemen.
BAG_WFS = "https://service.pdok.nl/lv/bag/wfs/v2_0"
UIT_RCE_PANDEN = "rijksmonumenten_rce_panden.json"


def panden_bij_punt(x, y, r, d=0.5):
    """De pand-identificaties waarvan de omtrek het vierkant rond (x, y) in
    RD raakt, of None als de BAG geen antwoord gaf."""
    url = BAG_WFS + "?" + urllib.parse.urlencode({
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeName": "bag:pand", "outputFormat": "application/json",
        "bbox": f"{x - d},{y - d},{x + d},{y + d},urn:ogc:def:crs:EPSG::28992"})
    _e, _s, inhoud = stadsbeeld.haal(url, r)
    if inhoud is None:
        return None
    try:
        d = json.loads(inhoud.decode("utf-8"))
    except ValueError:
        return None
    return [str((f.get("properties") or {}).get("identificatie"))
            for f in d.get("features") or []
            if (f.get("properties") or {}).get("identificatie")]


def koppel_rce_panden():
    import time
    import gezicht
    r = ["# RCE-rijksmonumenten gekoppeld aan BAG-panden", ""]
    try:
        with open(UIT_RCE, encoding="utf-8") as f:
            punten = json.load(f).get("punten") or []
    except (OSError, ValueError):
        r.append("- geen RCE-punten; eerst --rce")
        punten = []
    uit, fout, leeg = {}, 0, 0
    for x in punten:
        if x.get("lat") is None or not x.get("nummer"):
            continue
        gx, gy = gezicht.wgs84_naar_rd(x["lat"], x["lon"])
        p = panden_bij_punt(gx, gy, r if fout < 3 else [])
        time.sleep(0.2)
        if p is None:
            fout += 1
            continue
        if not p:
            leeg += 1
        uit[x["nummer"]] = {"naam": x.get("naam"), "panden": p,
                            "klasse": x.get("klasse"),
                            "aanduiding": x.get("aanduiding")}
    r.append(f"- {len(uit)} nummers gevraagd, {fout} zonder antwoord, "
             f"{leeg} met een punt buiten elk pand")
    # De toets: het register noemt per object een rijksmonumentnummer en ligt
    # als vlak; via de pandpunten van de voorraad weten we welk pand in welk
    # registervlak valt.
    reg = gezicht._laad().get("register") or []
    punt_pand = {pid: pt for pid, pt in gezicht._laad()["punten"].items()}
    nr_pand_reg = {}
    for pid, pt in punt_pand.items():
        gx, gy = gezicht.wgs84_naar_rd(pt["lat"], pt["lon"])
        for props in gezicht._raak(reg, gx, gy):
            for n in re.findall(r"\d{4,6}",
                                str(props.get("RIJKSOBJECTCODE") or "")):
                nr_pand_reg.setdefault(n, set()).add(pid)
    eens = oneens = te_toetsen = 0
    voorbeelden = []
    for n, v in uit.items():
        if n in nr_pand_reg and v["panden"]:
            te_toetsen += 1
            if set(v["panden"]) & nr_pand_reg[n]:
                eens += 1
            else:
                oneens += 1
                voorbeelden.append((n, v["naam"], v["panden"],
                                    sorted(nr_pand_reg[n])))
    r.append(f"- toets tegen het register (pand in de ring, nummer in "
             f"beide): {te_toetsen}, waarvan {eens} hetzelfde pand en "
             f"{oneens} een ander")
    r += [f"  - {v}" for v in voorbeelden[:10]]
    ring = set(punt_pand)
    in_ring = {n: [p for p in v["panden"] if p in ring] for n, v in uit.items()}
    r.append(f"- nummers met een pand in de ring: "
             f"{sum(1 for v in in_ring.values() if v)}, waarvan niet in het "
             f"register: {sum(1 for n, v in in_ring.items() if v and n not in nr_pand_reg)}")
    with open(UIT_RCE_PANDEN, "w", encoding="utf-8") as f:
        json.dump({"bron": "RCE-punten via PDOK, gekoppeld aan BAG-pandomtrek "
                           "(PDOK BAG WFS), vierkant van 1 m rond het punt",
                   "nummers": uit}, f, ensure_ascii=False, indent=1)
    with open("rijksmonumenten_rce_panden_verslag.md", "w",
              encoding="utf-8") as f:
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
    if nummer_uit_citatie("https://monumentenregister.cultureelerfgoed.nl/"
                          "monumenten/341971") != "341971" or \
            nummer_uit_citatie("kennis.cultureelerfgoed.nl/Gezicht/1439"):
        afw.append("het rijksmonumentnummer uit de citatie wordt verkeerd "
                   "gelezen")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef monumenten: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verken", action="store_true")
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--wfs", action="store_true")
    ap.add_argument("--rce", action="store_true")
    ap.add_argument("--rce-panden", action="store_true")
    a = ap.parse_args()
    if a.rce_panden:
        return koppel_rce_panden()
    if a.rce:
        return verken_rce()
    if a.wfs:
        return verken_wfs()
    if a.proef:
        return proef()
    if a.verken:
        return verken()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
