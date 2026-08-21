#!/usr/bin/env python3
"""
Marktprijzen-blok voor de Nijmegen Vastgoedmonitor.

Leest handmatig verzamelde verkoop/aanbod-data uit verkopen.txt,
verrijkt elk adres met oppervlakte en buurtnaam uit de BAG API
Individuele Bevragingen (endpoint 'adressenuitgebreid'), en genereert
per focus-buurt een boxplot van EUR/m2 voor de dagelijkse brief.

Input:  verkopen.txt (Mark plakt hier periodiek adressen+prijzen in)
Cache:  marktprijzen_bag_cache.json (BAG-lookups worden gecached)
Output: digests/DATUM-marktprijzen.md
Vereist env: BAG_API_KEY (gratis via kadaster.nl)
"""

import argparse
import datetime as dt
import json
import os
import re
import statistics as st
import sys
import time
from collections import defaultdict

import requests

# --- CONFIG ---
INPUT_PAD = "verkopen.txt"
CACHE_PAD = "marktprijzen_bag_cache.json"

FOCUS_BUURTEN = [
    "Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
    "Altrade", "Biezen",
]

BUURT_ALIAS = {
    "Waterkwartier": "Biezen",
    "Nijmegen-Centrum": "Stadscentrum",
    "Nijmegen-Oud-West": "Biezen",
}

EIGEN_STRATEN = ["Graafsedwarsstraat", "Eerste Oude Heselaan"]
ACQUISITIE_STRATEN = ["Fransestraat", "Van Spaenstraat"]

BAG_API_KEY = os.environ.get("BAG_API_KEY", "")
BAG_BASE = "https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2"
BAG_HEADERS = {
    "X-Api-Key": BAG_API_KEY,
    "Accept": "application/hal+json",
    "Accept-Crs": "epsg:28992",
}
RATE_LIMIT_SEC = 1.1

PDOK_FREE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
PDOK_HEADERS = {"User-Agent": "DerksenVastgoedMonitor/1.0"}


def lees_cache():
    if not os.path.exists(CACHE_PAD):
        return {}
    try:
        with open(CACHE_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def schrijf_cache(cache):
    with open(CACHE_PAD, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def lees_verkopen(pad):
    if not os.path.exists(pad):
        print(f"Bestand niet gevonden: {pad}", file=sys.stderr)
        return []
    resultaat = []
    with open(pad, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            regel = raw.strip()
            if not regel or regel.startswith("#"):
                continue
            delen = [d.strip() for d in regel.split("|")]
            if len(delen) < 3:
                print(f"Regel {lineno} onvolledig: {regel}", file=sys.stderr)
                continue
            adres, plaats, prijs_str = delen[0], delen[1], delen[2]
            status = delen[3] if len(delen) > 3 else "onbekend"
            try:
                prijs = int(re.sub(r"[^\d]", "", prijs_str))
            except ValueError:
                print(f"Regel {lineno} prijsfout: {prijs_str}", file=sys.stderr)
                continue
            resultaat.append({
                "adres": adres,
                "plaats": plaats,
                "prijs": prijs,
                "status": status,
            })
    return resultaat


def split_huisnummer(adres):
    """
    Splits 'Van Spaenstraat 20A' -> ('Van Spaenstraat', '20', 'A', None)
    'Molenstraat 41K' -> ('Molenstraat', '41', 'K', None)
    'Dommer van Poldersveldtweg 42' -> ('Dommer van Poldersveldtweg', '42', None, None)
    'Bijleveldsingel 20 Bb' -> ('Bijleveldsingel', '20', 'B', 'B')
    """
    m = re.match(r"^(.+?)\s+(\d+)\s*([A-Za-z])?\s*[\-]?\s*([A-Za-z0-9]{1,4})?\s*$", adres.strip())
    if not m:
        return adres, None, None, None
    straat = m.group(1).strip()
    huisnr = m.group(2)
    letter = (m.group(3) or "").upper() or None
    toev = (m.group(4) or "").upper() or None
    return straat, huisnr, letter, toev


def pdok_buurt(straat, huisnr, plaats):
    q = f"{straat} {huisnr} {plaats}"
    try:
        r = requests.get(PDOK_FREE, params={
            "q": q, "fq": "type:adres", "rows": 1,
            "fl": "buurtnaam wijknaam postcode weergavenaam",
        }, headers=PDOK_HEADERS, timeout=15)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return {}
        d = docs[0]
        return {
            "postcode": d.get("postcode", ""),
            "buurtnaam": d.get("buurtnaam", ""),
            "wijknaam": d.get("wijknaam", ""),
        }
    except Exception as e:
        print(f"  PDOK buurt-lookup '{q}': {e}", file=sys.stderr)
        return {}


def bag_adres_uitgebreid(straat, huisnr, letter, toev, plaats):
    """
    Roept BAG /adressenuitgebreid aan. Retourneert oppervlakte, bouwjaar,
    gebruiksdoelen, postcode.
    """
    if not BAG_API_KEY:
        return None
    params = {
        "openbareRuimteNaam": straat,
        "huisnummer": huisnr,
        "woonplaatsNaam": plaats,
        "exacteMatch": "true",
    }
    if letter:
        params["huisletter"] = letter
    if toev:
        params["huisnummertoevoeging"] = toev
    try:
        r = requests.get(f"{BAG_BASE}/adressenuitgebreid",
                         headers=BAG_HEADERS, params=params, timeout=20)
        if r.status_code == 404:
            return None
        if r.status_code == 401:
            print(f"  BAG 401: API-key ongeldig?", file=sys.stderr)
            return None
        r.raise_for_status()
        data = r.json()
    except requests.HTTPError as e:
        print(f"  BAG HTTP {r.status_code}: {straat} {huisnr}{letter or ''}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  BAG-fout {straat} {huisnr}: {e}", file=sys.stderr)
        return None

    embedded = data.get("_embedded", {}).get("adressen", [])
    if not embedded:
        return None
    a = embedded[0]
    bouwjaar = a.get("adresseerbaarObjectBouwjaar")
    if isinstance(bouwjaar, list) and bouwjaar:
        bouwjaar = bouwjaar[0]
    return {
        "oppervlakte": a.get("oppervlakte"),
        "bouwjaar": bouwjaar,
        "gebruiksdoelen": a.get("gebruiksdoelen", []),
        "postcode": a.get("postcode", ""),
        "adresseerbaarObjectIdentificatie": a.get("adresseerbaarObjectIdentificatie", ""),
    }


def verrijk(woning, cache):
    sleutel = f"{woning['adres']}|{woning['plaats']}"
    if sleutel in cache and not cache[sleutel].get("gefaald"):
        woning.update(cache[sleutel])
        return woning

    straat, huisnr, letter, toev = split_huisnummer(woning["adres"])
    if not huisnr:
        print(f"  FAIL parse: {woning['adres']}", file=sys.stderr)
        cache[sleutel] = {"gefaald": True, "reden": "parse"}
        return woning

    bag = bag_adres_uitgebreid(straat, huisnr, letter, toev, woning["plaats"])
    time.sleep(RATE_LIMIT_SEC)

    # Retry zonder toevoeging als exact niet lukt
    if not bag and (toev or letter):
        bag = bag_adres_uitgebreid(straat, huisnr, None, None, woning["plaats"])
        time.sleep(RATE_LIMIT_SEC)

    if not bag or not bag.get("oppervlakte"):
        print(f"  FAIL BAG: {woning['adres']}", file=sys.stderr)
        cache[sleutel] = {"gefaald": True, "reden": "bag_geen_oppervlakte"}
        return woning

    pdok = pdok_buurt(straat, huisnr, woning["plaats"])
    time.sleep(0.2)

    verrijking = {**bag, **pdok}
    cache[sleutel] = verrijking
    woning.update(verrijking)
    return woning


def normaliseer_buurt(buurtnaam):
    if not buurtnaam:
        return ""
    if buurtnaam in FOCUS_BUURTEN:
        return buurtnaam
    return BUURT_ALIAS.get(buurtnaam, buurtnaam)


def render(woningen):
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    r = ["", "## Marktprijzen koop per buurt",
         f"_Op basis van {len(woningen)} recente transacties/aanbiedingen. Oppervlakte uit BAG. Bijgewerkt {vandaag}._",
         ""]

    per_buurt = defaultdict(list)
    for w in woningen:
        buurt = normaliseer_buurt(w.get("buurtnaam", ""))
        opp = w.get("oppervlakte")
        if not buurt or buurt not in FOCUS_BUURTEN or not opp or opp < 15:
            continue
        try:
            ppm2 = w["prijs"] / opp
            per_buurt[buurt].append((ppm2, w))
        except (TypeError, ZeroDivisionError):
            continue

    if not per_buurt:
        r.append("_Geen woningen met bruikbare data in de focus-buurten._")
        return "\n".join(r)

    r.append("| Buurt | N | min €/m² | p25 | mediaan | p75 | max |")
    r.append("|---|---:|---:|---:|---:|---:|---:|")
    for buurt in FOCUS_BUURTEN:
        rijen = per_buurt.get(buurt, [])
        if not rijen:
            r.append(f"| {buurt} | 0 | — | — | — | — | — |")
            continue
        prijzen = sorted(p for p, _ in rijen)
        n = len(prijzen)
        p25 = prijzen[n // 4]
        p75 = prijzen[3 * n // 4]
        med = st.median(prijzen)
        r.append(f"| {buurt} | {n} | "
                 f"€{int(min(prijzen)):,} | €{int(p25):,} | "
                 f"€{int(med):,} | €{int(p75):,} | €{int(max(prijzen)):,} |".replace(",", "."))
    r.append("")

    eigen_hits, acq_hits = [], []
    for w in woningen:
        for straat in EIGEN_STRATEN:
            if straat.lower() in w["adres"].lower():
                eigen_hits.append(w)
        for straat in ACQUISITIE_STRATEN:
            if straat.lower() in w["adres"].lower():
                acq_hits.append(w)

    if eigen_hits or acq_hits:
        r.append("### Transacties in eigen bezit-straten of acquisitietargets")
        r.append("")
        if eigen_hits:
            r.append("**Naast eigen bezit:**")
            for w in eigen_hits:
                opp = w.get("oppervlakte")
                ppm2 = f"€{int(w['prijs']/opp):,}/m²".replace(",", ".") if opp else "?"
                r.append(f"- {w['adres']} ({w.get('postcode','?')}): "
                         f"€{w['prijs']:,} ({opp}m² → {ppm2}) . _{w['status']}_".replace(",", "."))
            r.append("")
        if acq_hits:
            r.append("**Acquisitietargets:**")
            for w in acq_hits:
                opp = w.get("oppervlakte")
                ppm2 = f"€{int(w['prijs']/opp):,}/m²".replace(",", ".") if opp else "?"
                r.append(f"- {w['adres']} ({w.get('postcode','?')}): "
                         f"€{w['prijs']:,} ({opp}m² → {ppm2}) . _{w['status']}_".replace(",", "."))
            r.append("")

    r.append("_Vuistregel Derksen: bod = 17× jaarhuur. Bij €12/m²/maand huur = €2.448/m² bod-referentie; bij €15/m²/maand = €3.060/m²._")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="marktprijzen_digest.md")
    ap.add_argument("--input", default=INPUT_PAD)
    args = ap.parse_args()

    if not BAG_API_KEY:
        print("WAARSCHUWING: BAG_API_KEY ontbreekt", file=sys.stderr)

    woningen = lees_verkopen(args.input)
    print(f"Ingelezen: {len(woningen)} regels", file=sys.stderr)
    if not woningen:
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write("\n## Marktprijzen koop per buurt\n\n_Nog geen data in verkopen.txt._\n")
        return

    cache = lees_cache()
    print(f"Cache-entries: {len(cache)}", file=sys.stderr)

    ok, nieuw = 0, 0
    for w in woningen:
        sleutel = f"{w['adres']}|{w['plaats']}"
        was_nieuw = sleutel not in cache or cache.get(sleutel, {}).get("gefaald")
        verrijk(w, cache)
        if w.get("oppervlakte"):
            ok += 1
        if was_nieuw:
            nieuw += 1
            if nieuw % 20 == 0:
                schrijf_cache(cache)  # tussentijds opslaan bij crash

    schrijf_cache(cache)
    print(f"Verrijkt met oppervlakte: {ok}/{len(woningen)} (nieuw opgehaald: {nieuw})", file=sys.stderr)

    md = render(woningen)
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
