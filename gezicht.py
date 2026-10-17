#!/usr/bin/env python3
"""
Rijksbeschermde stads- en dorpsgezichten, per pand in de ring.

WAAROM DIT BESTAAT. Tot 17 oktober 2026 stond het beschermd gezicht in de
dossiers per BUURT, als vaste tekst in marktprijzen_bag.BESCHERMD_GEZICHT:
"rijksbeschermd stadsgezicht Benedenstad", "deels de negentiende-eeuwse
schil", en voor Hunnerberg en St. Anna "niet nagekeken". De grenzen van een
gezicht volgen de buurtgrenzen niet, dus "deels" zei bij een pand niets, en
het rustte op een aanname en niet op een meting. Voor een aankoop raakt het
gevelisolatie, kozijnen en zonnepanelen aan de voorzijde.

DE BRON. "Beschermde Gebieden - Cultuurhistorie (INSPIRE geharmoniseerd)"
van de Rijksdienst voor het Cultureel Erfgoed, via PDOK als OGC API
Features, collectie rce_inspire_polygons. Licentie CC BY 4.0. Die collectie
bevat rijksmonumenten en gezichten door elkaar; de gezichten herken je aan
namespace "nlps-stadsendorpsgezichten". Twee voorbehouden:
- Alleen RIJKSbeschermde gezichten. Een gemeentelijk beschermd gezicht staat
  er niet in, dus "niet in deze bron" is nooit "niet beschermd".
- De vlakken staan erin "mits beschikbaar", zegt de bron zelf.

HOE. Eén keer de vlakken in en rond de ring ophalen (geen aanroep per pand),
bewaren in gezichten.json, en dan per pand lokaal toetsen of het punt uit de
voorraad binnen een vlak valt. De verkenning schrijft per buurt hoeveel
panden binnen welk gezicht vallen, zodat te zien is of de Benedenstad er
inderdaad in ligt voordat het dossier hierop leunt.

  python3 gezicht.py --ophalen   # de vlakken en het verslag
  python3 gezicht.py --proef
"""
import argparse
import collections
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request

BASIS = ("https://api.pdok.nl/rce/beschermde-gebieden-cultuurhistorie/ogc/v1/"
         "collections/rce_inspire_polygons/items")
NAAMRUIMTE = "nlps-stadsendorpsgezichten"
UIT_PAD = "gezichten.json"
VERSLAG = "gezicht_verslag.md"
# De ring is 5,837 tot 5,897 oost en 51,817 tot 51,855 noord (voorraad, 17
# oktober). Een marge eromheen, want een gezicht dat de ring raakt kan zijn
# hoekpunten erbuiten hebben.
BBOX = (5.80, 51.80, 5.93, 51.87)
MAX_PAGINAS = 60
BRON = ("Beschermde Gebieden - Cultuurhistorie, RCE via PDOK, CC BY 4.0; "
        "alleen rijksbeschermde gezichten, vlakken mits beschikbaar")


def _vraag(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "NijmegenVastgoedMonitor/1.0",
        "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _in_bbox(geom, bbox=BBOX):
    """Raakt de omhullende van deze geometrie de bbox? Om te zien of de bron
    de bbox-parameter respecteert, want een proefvraag op 17 oktober gaf
    monumenten uit heel Nederland terug."""
    xs, ys = [], []
    for ring in _ringen(geom):
        for x, y in ring:
            xs.append(x)
            ys.append(y)
    if not xs:
        return False
    return not (max(xs) < bbox[0] or min(xs) > bbox[2]
                or max(ys) < bbox[1] or min(ys) > bbox[3])


def _ringen(geom):
    if not geom:
        return
    soort, c = geom.get("type"), geom.get("coordinates") or []
    if soort == "Polygon":
        yield from c
    elif soort == "MultiPolygon":
        for poly in c:
            yield from poly


def _in_ring(x, y, ring):
    """Ray casting: ligt (x, y) binnen deze ring?"""
    binnen = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xs = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xs:
                binnen = not binnen
    return binnen


def in_vlak(lon, lat, geom):
    """Ligt het punt in het vlak, met gaten als gaten?"""
    if not geom:
        return False
    if geom.get("type") == "Polygon":
        polys = [geom.get("coordinates") or []]
    elif geom.get("type") == "MultiPolygon":
        polys = geom.get("coordinates") or []
    else:
        return False
    for poly in polys:
        if poly and _in_ring(lon, lat, poly[0]) and not any(
                _in_ring(lon, lat, gat) for gat in poly[1:]):
            return True
    return False


def ophalen():
    params = {"f": "json", "limit": "1000",
              "bbox": ",".join(str(v) for v in BBOX)}
    url = BASIS + "?" + urllib.parse.urlencode(params)
    gezichten, totaal, buiten, paginas = [], 0, 0, 0
    namen = collections.Counter()
    while url and paginas < MAX_PAGINAS:
        d = _vraag(url)
        paginas += 1
        for f in d.get("features") or []:
            totaal += 1
            p = f.get("properties") or {}
            namen[p.get("namespace")] += 1
            if not _in_bbox(f.get("geometry")):
                buiten += 1
                continue
            if p.get("namespace") != NAAMRUIMTE:
                continue
            gezichten.append({
                "id": f.get("id"), "naam": p.get("text"),
                "aangewezen": p.get("legalfoundationdate"),
                "bron": p.get("ci_citation"),
                "geometry": f.get("geometry")})
        url = next((l.get("href") for l in d.get("links") or []
                    if l.get("rel") == "next"), None)
        time.sleep(0.2)
    uit = {"bron": BRON, "bijgewerkt": dt.date.today().isoformat(),
           "volledig": url is None, "gezichten": gezichten,
           "meting": {"objecten": totaal, "buiten_bbox": buiten,
                      "paginas": paginas,
                      "naamruimtes": dict(namen)}}
    with open(UIT_PAD, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False)
    print(f"Gezichten: {len(gezichten)} in de bbox, van {totaal} objecten op "
          f"{paginas} pagina's; {buiten} buiten de bbox; "
          f"{'volledig' if url is None else 'NIET VOLLEDIG, paginaplafond'}",
          file=sys.stderr)
    return uit


def per_pand(gezichten, punten):
    """pand-id -> lijst van gezichtsnamen waarin het punt ligt."""
    uit = {}
    for pid, pt in punten.items():
        uit[pid] = [g.get("naam") or g.get("id") for g in gezichten
                    if in_vlak(pt["lon"], pt["lat"], g.get("geometry"))]
    return uit


def verslag(uit):
    import bestemming
    with open("voorraad.json", encoding="utf-8") as f:
        v = json.load(f)
    buurt = {}
    for r in (v.get("adressen") or {}).values():
        if r.get("herkomst") == "focusbuurt" and r.get("pand"):
            bb = r.get("buurten")
            buurt.setdefault(r["pand"], bb[0] if isinstance(bb, list) and bb
                             else bb)
    punten = bestemming.punten_per_pand()
    pp = per_pand(uit["gezichten"], punten)
    tel = collections.defaultdict(collections.Counter)
    for pid, namen in pp.items():
        b = buurt.get(pid) or "?"
        tel[b]["panden"] += 1
        for n in namen:
            tel[b][n] += 1
    r = ["# Verkenning rijksbeschermde gezichten", "",
         f"Op {uit['bijgewerkt']}, bron: {BRON}.", "",
         f"Meting: {json.dumps(uit['meting'], ensure_ascii=False)}", "",
         "## Gezichten in de bbox", ""]
    for g in uit["gezichten"]:
        r.append(f"- {g.get('naam')} (aangewezen {g.get('aangewezen')}, "
                 f"{g.get('bron')})")
    if not uit["gezichten"]:
        r.append("- geen")
    r += ["", "## Panden per buurt binnen een gezicht", ""]
    for b in sorted(tel):
        rest = {k: n for k, n in tel[b].items() if k != "panden"}
        r.append(f"- {b}: {tel[b]['panden']} panden; "
                 + (", ".join(f"{k} {n}" for k, n in sorted(rest.items()))
                    or "in geen enkel gezicht"))
    with open(VERSLAG, "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    print("\n".join(r))


def proef():
    afw = []
    vierkant = {"type": "Polygon", "coordinates": [
        [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
        [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]}
    if not in_vlak(2, 2, vierkant):
        afw.append("een punt binnen het vlak valt erbuiten")
    if in_vlak(5, 5, vierkant):
        afw.append("een punt in het gat telt als binnen")
    if in_vlak(12, 5, vierkant):
        afw.append("een punt buiten het vlak telt als binnen")
    multi = {"type": "MultiPolygon", "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        [[[20, 20], [21, 20], [21, 21], [20, 21], [20, 20]]]]}
    if not in_vlak(20.5, 20.5, multi):
        afw.append("het tweede deel van een multipolygoon wordt niet gezien")
    if _in_bbox({"type": "Polygon", "coordinates": [
            [[4.0, 52.0], [4.1, 52.0], [4.1, 52.1], [4.0, 52.0]]]}):
        afw.append("een vlak bij Den Haag valt binnen de bbox van Nijmegen")
    if not _in_bbox({"type": "Polygon", "coordinates": [
            [[5.85, 51.84], [5.86, 51.84], [5.86, 51.85], [5.85, 51.84]]]}):
        afw.append("een vlak in de Benedenstad valt buiten de bbox")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef gezicht: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--ophalen", action="store_true")
    a = ap.parse_args()
    if a.proef:
        return proef()
    if a.ophalen:
        verslag(ophalen())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
