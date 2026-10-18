#!/usr/bin/env python3
"""
De begrenzing van het voorbeschermd stadsbeeld Wederopbouwcentrum ophalen.

WAAROM. Sinds 4 september 2026 heeft Nijmegen het naoorlogse centrum in het
omgevingsplan voorbeschermd als stadsbeeld (CVDR766239): sloop van
gebouwdelen aan de openbare ruimte en het wijzigen van gevels en dakvlakken
die naar openbaar gebied gekeerd zijn, zijn dan vergunningplichtig. Dat staat
in geen van onze twee bronnen: ruimtelijkeplannen.nl mist het omgevingsplan
in de nieuwe standaard, en de RCE kent alleen rijksgezichten. Gemeten op 17
oktober: 466 panden in het Stadscentrum liggen in geen rijksgezicht, en een
deel daarvan valt hier waarschijnlijk onder.

DE BRON. De regeling verwijst in Bijlage I naar twee geografische
informatieobjecten (GIO's), met een JOIN-identificatie bij de officiele
bekendmakingen. Een GIO is een openbare publicatie van de overheid. Deze stap
volgt de JOIN-identificatie, bewaart wat hij vindt en zoekt naar de
geometrie, zonder sleutel. Eerst kijkt hij in robots.txt van elke host; staat
daar dat automatisch ophalen niet mag, dan stopt hij voor die host en zegt
dat. Dat is dezelfde regel als bij jeleefomgeving.nl.

  python3 stadsbeeld.py --verken
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.robotparser

GIO = {
    "werkingsgebied": "https://identifier.officielebekendmakingen.nl/join/id/"
                      "regdata/gm0268/2026/e2b2210e98944ca387229c231879c6d4/"
                      "nld@2026-09-03;09225018",
    "stadsbeeldobject": "https://identifier.officielebekendmakingen.nl/join/"
                        "id/regdata/gm0268/2026/7b82e3db52154524910d9bf933a"
                        "7213f/nld@2026-09-03;09225018",
}
AGENT = "NijmegenVastgoedMonitor/1.0"
VERSLAG = "stadsbeeld_verslag.md"
_robots = {}


def mag(url):
    """Mag dit volgens robots.txt van de host? Onbereikbare robots.txt telt
    als niet nagekeken, en dan halen we niets op."""
    deel = urllib.parse.urlsplit(url)
    host = f"{deel.scheme}://{deel.netloc}"
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser(host + "/robots.txt")
        try:
            rp.read()
            _robots[host] = rp
        except Exception as e:
            _robots[host] = e
    rp = _robots[host]
    if isinstance(rp, Exception):
        return None, f"robots.txt van {host} niet te lezen: {rp}"
    if not rp.can_fetch(AGENT, url):
        return False, f"robots.txt van {host} staat dit niet toe"
    return True, ""


def haal(url, r):
    ok, reden = mag(url)
    if not ok:
        r.append(f"- NIET OPGEHAALD {url}: {reden}")
        return None, None, None
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            inhoud = resp.read()
            return resp.geturl(), resp.headers.get("Content-Type", ""), inhoud
    except Exception as e:
        r.append(f"- FOUT {url}: {type(e).__name__} {str(e)[:200]}")
        return None, None, None


def verken():
    r = ["# Verkenning stadsbeeld Wederopbouwcentrum", ""]
    gevonden = {}
    for naam, url in GIO.items():
        r.append(f"## {naam}")
        r.append(f"JOIN: `{url}`")
        eind, soort, inhoud = haal(url, r)
        if inhoud is None:
            r.append("")
            continue
        tekst = inhoud.decode("utf-8", errors="replace")
        r.append(f"- eindadres na doorverwijzing: `{eind}`")
        r.append(f"- type: {soort}, {len(inhoud)} bytes")
        links = sorted(set(re.findall(r'href="([^"]+)"', tekst)))
        geo = [l for l in links if re.search(r"\.(gml|xml|json|zip)(\?|$)", l,
                                             re.I)]
        r.append(f"- links naar mogelijke geometrie: {geo[:20]}")
        r.append(f"- begin van het antwoord: `{tekst[:800]}`")
        for l in geo[:5]:
            volledig = urllib.parse.urljoin(eind, l)
            e2, s2, i2 = haal(volledig, r)
            if i2 is None:
                continue
            t2 = i2.decode("utf-8", errors="replace")
            heeft = bool(re.search(r"posList|coordinates|Polygon", t2))
            r.append(f"  - `{e2}`: {s2}, {len(i2)} bytes, geometrie "
                     f"{'ja' if heeft else 'nee'}")
            if heeft:
                pad = f"stadsbeeld_{naam}{'.gml' if 'gml' in (s2 or '') or '<' in t2[:5] else '.json'}"
                with open(pad, "wb") as f:
                    f.write(i2)
                gevonden[naam] = {"bron": e2, "bestand": pad,
                                  "bytes": len(i2)}
                r.append(f"  - bewaard als {pad}")
                break
        r.append("")
    r.append(f"Gevonden: {json.dumps(gevonden, ensure_ascii=False)}")
    with open(VERSLAG, "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    print("\n".join(r))
    return 0


WERKINGSGEBIED = "stadsbeeld_werkingsgebied.gml"
OBJECTEN = "stadsbeeld_stadsbeeldobject.gml"
_GML = "{http://www.opengis.net/gml/3.2}"


def vlakken(pad):
    """De vlakken uit een GIO als GeoJSON-achtige Polygon-dicts, in RD
    (EPSG:28992, zoals het GIO zelf zegt). None als het bestand er niet is:
    dat is niet nagekeken, en geen leeg gebied."""
    import xml.etree.ElementTree as ET
    try:
        boom = ET.parse(pad)
    except (OSError, ET.ParseError):
        return None
    uit = []
    for poly in boom.iter(_GML + "Polygon"):
        ringen = []
        for pl in poly.iter(_GML + "posList"):
            w = [float(x) for x in (pl.text or "").split()]
            ringen.append([[w[i], w[i + 1]] for i in range(0, len(w) - 1, 2)])
        if ringen:
            uit.append({"type": "Polygon", "coordinates": ringen})
    return uit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verken", action="store_true")
    a = ap.parse_args()
    if a.verken:
        return verken()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
