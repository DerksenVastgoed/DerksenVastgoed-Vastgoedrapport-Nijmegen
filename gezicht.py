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


# WGS84 NAAR RIJKSDRIEHOEK. De benadering van Schreutelkamp en Strang van
# Hees, nauwkeurig tot ongeveer een meter in Nederland. Nodig omdat de
# GIO's van het omgevingsplan in RD staan en de punten in de voorraad in
# WGS84. Proef op het nulpunt van RD, de Onze Lieve Vrouwetoren in
# Amersfoort.
_R = [(0, 1, 190094.945), (1, 1, -11832.228), (2, 1, -114.221),
      (0, 3, -32.391), (1, 0, -0.705), (3, 1, -2.340), (1, 3, -0.608),
      (0, 2, -0.008), (2, 3, 0.148)]
_S = [(1, 0, 309056.544), (0, 2, 3638.893), (2, 0, 73.077),
      (1, 2, -157.984), (3, 0, 59.788), (0, 1, 0.433), (2, 2, -6.439),
      (1, 1, -0.032), (0, 4, 0.092), (1, 4, -0.054)]


def wgs84_naar_rd(lat, lon):
    dp = 0.36 * (lat - 52.15517440)
    dl = 0.36 * (lon - 5.38720621)
    x = 155000 + sum(c * dp ** p * dl ** q for p, q, c in _R)
    y = 463000 + sum(c * dp ** p * dl ** q for p, q, c in _S)
    return x, y


STADSBEELD_SINDS = "4 september 2026"
STADSBEELD_BRON = ("Voorbeschermingsregels stadsbeeld Wederopbouwcentrum, "
                   "CVDR766239, GIO dc-2026-27212 en dc-2026-27213")
_cache = {}


def _laad():
    if "geladen" in _cache:
        return _cache
    import bestemming
    import stadsbeeld
    _cache["punten"] = bestemming.punten_per_pand()
    try:
        with open(UIT_PAD, encoding="utf-8") as f:
            _cache["gezichten"] = json.load(f).get("gezichten")
    except (OSError, ValueError):
        _cache["gezichten"] = None
    _cache["gebied"] = stadsbeeld.vlakken(stadsbeeld.WERKINGSGEBIED)
    _cache["objecten"] = stadsbeeld.vlakken(stadsbeeld.OBJECTEN)
    _cache["geladen"] = True
    return _cache


def bescherming(pand_id):
    """
    Wat er aan erfgoedbescherming op het punt van dit pand ligt.

    Geeft None als het pand niet in de ring ligt (dan is er niets gemeten),
    anders een dict met:
      rijks: lijst gezichtsnamen, of None als gezichten.json ontbreekt
      stadsbeeld: "object", "gebied", "" (gemeten, erbuiten) of None
                  (niet gemeten)
    """
    c = _laad()
    pt = c["punten"].get(str(pand_id or ""))
    if not pt:
        return None
    rijks = None
    if c["gezichten"] is not None:
        rijks = [g.get("naam") or g.get("id") for g in c["gezichten"]
                 if in_vlak(pt["lon"], pt["lat"], g.get("geometry"))]
    stadsbeeld = None
    if c["gebied"] is not None and c["objecten"] is not None:
        x, y = wgs84_naar_rd(pt["lat"], pt["lon"])
        if any(in_vlak(x, y, v) for v in c["objecten"]):
            stadsbeeld = "object"
        elif any(in_vlak(x, y, v) for v in c["gebied"]):
            stadsbeeld = "gebied"
        else:
            stadsbeeld = ""
    return {"rijks": rijks, "stadsbeeld": stadsbeeld}


# De dubbelbestemming die bij een rijksgezicht hoort. AFGELEID, niet uit de
# planregels: gemeten op 17 oktober per buurt, en de tellingen vielen op twee
# panden na samen (Benedenstad 634 tegen 634, Galgenveld 465 tegen 465,
# Altrade 438 tegen 438, Bottendaal 353 tegen 353, Hunnerberg 159 tegen 159).
# De planregels zelf waren niet automatisch op te halen.
BIJ_GEZICHT = {"Nijmegen": "Cultuurhistorie 1",
               "Nijmegen - De 19de-eeuwse Stadsuitleg": "Cultuurhistorie 2"}


def dossierregels(pand_id):
    """[(onderwerp, tekst, bron)] voor het dossier van een pand."""
    b = bescherming(pand_id)
    if b is None:
        return [("beschermd gezicht", "niet nagekeken: dit pand ligt niet in "
                 "de ring, of de voorraad kent er geen punt van", "eigen meting")]
    uit = []
    if b["rijks"] is None:
        uit.append(("rijksbeschermd gezicht", "niet nagekeken", BRON))
    elif b["rijks"]:
        namen = ", ".join(b["rijks"])
        dub = [BIJ_GEZICHT[n] for n in b["rijks"] if n in BIJ_GEZICHT]
        uit.append(("rijksbeschermd gezicht",
                    f"{namen}: wijzigingen aan het uiterlijk zijn "
                    f"vergunningplichtig, wat gevelisolatie, kozijnen en "
                    f"zonnepanelen aan de voorzijde raakt"
                    + (f". In het bestemmingsplan hoort hier vermoedelijk de "
                       f"dubbelbestemming {', '.join(dub)} bij (afgeleid uit "
                       f"de overlap per buurt, niet uit de planregels)"
                       if dub else ""), BRON))
    else:
        uit.append(("rijksbeschermd gezicht", "geen op dit punt. "
                    "Gemeentelijke monumenten zijn niet nagekeken", BRON))
    if b["stadsbeeld"] == "object":
        uit.append(("gemeentelijk voorbeschermd stadsbeeld",
                    f"dit is een voorbeschermd stadsbeeldobject in het "
                    f"Wederopbouwcentrum, sinds {STADSBEELD_SINDS}: sloop van "
                    f"delen aan de openbare ruimte en het wijzigen van gevels "
                    f"en dakvlakken naar openbaar gebied zijn "
                    f"vergunningplichtig; normaal onderhoud zonder wijziging "
                    f"van detaillering, materiaal en kleur niet",
                    STADSBEELD_BRON))
    elif b["stadsbeeld"] == "gebied":
        uit.append(("gemeentelijk voorbeschermd stadsbeeld",
                    f"ligt in het voorbeschermd stadsbeeld Wederopbouwcentrum, "
                    f"sinds {STADSBEELD_SINDS}, maar het gebouw is zelf geen "
                    f"stadsbeeldobject: wijzigingen aan gevels en dakvlakken "
                    f"naar openbaar gebied kunnen vergunningplichtig zijn, "
                    f"nakijken in het omgevingsplan", STADSBEELD_BRON))
    elif b["stadsbeeld"] is None:
        uit.append(("gemeentelijk voorbeschermd stadsbeeld", "niet nagekeken",
                    STADSBEELD_BRON))
    return uit


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
    x, y = wgs84_naar_rd(52.15517440, 5.38720621)
    if abs(x - 155000) > 0.01 or abs(y - 463000) > 0.01:
        afw.append(f"het nulpunt van RD komt uit op {x:.2f}, {y:.2f}")
    # Een bekend punt verder weg: de omrekening mag niet alleen in het
    # nulpunt kloppen. Plein 1944 in Nijmegen ligt in het werkingsgebied van
    # het voorbeschermd stadsbeeld (gemeten 18 oktober), dus de omrekening
    # moet daar binnen het vlak uitkomen.
    try:
        import stadsbeeld
        gebied = stadsbeeld.vlakken(stadsbeeld.WERKINGSGEBIED)
    except Exception:
        gebied = None
    if gebied:
        import bestemming
        plein = [pt for pt in bestemming.punten_per_pand().values()
                 if (pt.get("adres") or "").startswith("Plein 1944")]
        binnen = sum(1 for pt in plein if any(
            in_vlak(*wgs84_naar_rd(pt["lat"], pt["lon"]), v) for v in gebied))
        if plein and not binnen:
            afw.append("geen enkel pand aan Plein 1944 valt in het "
                       "voorbeschermd stadsbeeld; de omrekening naar RD klopt "
                       "niet")
        # En via bescherming(), zodat ook de aansluiting wordt beproefd.
        _cache.clear()
        b = None
        for pid, pt in bestemming.punten_per_pand().items():
            if (pt.get("adres") or "").startswith("Plein 1944"):
                b = bescherming(pid)
                break
        if b is not None and b["stadsbeeld"] not in ("object", "gebied"):
            afw.append(f"bescherming() ziet Plein 1944 niet in het "
                       f"stadsbeeld: {b}")
    # De drie toestanden van het rijksgezicht krijgen elk een eigen tekst.
    _oud = dict(_cache)
    try:
        _cache.clear()
        _cache.update({"geladen": True, "punten": {"P": {"lat": 5, "lon": 5}},
                       "gezichten": None, "gebied": None, "objecten": None})
        t_niet = dossierregels("P")[0][1]
        _cache["gezichten"] = []
        t_geen = dossierregels("P")[0][1]
        _cache["gezichten"] = [{"naam": "Nijmegen", "geometry": {
            "type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10],
                                                [0, 10], [0, 0]]]}}]
        t_wel = dossierregels("P")[0][1]
        if len({t_niet, t_geen, t_wel}) != 3 or t_niet != "niet nagekeken":
            afw.append("niet nagekeken, geen en wel krijgen geen eigen tekst")
        if "Cultuurhistorie 1" not in t_wel or "afgeleid" not in t_wel:
            afw.append("de afgeleide dubbelbestemming staat er niet, of niet "
                       "als afgeleid")
        if dossierregels("ONBEKEND")[0][1].startswith("geen"):
            afw.append("een pand buiten de ring leest als geen gezicht")
    finally:
        _cache.clear()
        _cache.update(_oud)
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
