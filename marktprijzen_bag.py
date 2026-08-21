#!/usr/bin/env python3
"""
Marktprijzen-blok voor de Nijmegen Vastgoedmonitor.

Leest handmatig verzamelde verkoop/aanbod-data uit verkopen.txt,
verrijkt elk adres met oppervlakte en buurtnaam uit PDOK BAG,
en genereert per focus-buurt een boxplot van €/m² voor de dagelijkse brief.

Input:  verkopen.txt (Mark plakt hier periodiek adressen+prijzen in)
Cache:  marktprijzen_bag_cache.json (BAG-lookups worden gecached)
Output: digests/DATUM-marktprijzen.md
"""

import argparse
import datetime as dt
import json
import os
import re
import statistics as st
import sys
import time
import urllib.parse
from collections import defaultdict

import requests

# --- CONFIG ---
INPUT_PAD = "verkopen.txt"
CACHE_PAD = "marktprijzen_bag_cache.json"

FOCUS_BUURTEN = [
    "Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
    "Altrade", "Biezen",
]

# Alternatieve buurtnamen die PDOK soms hanteert -> onze focus-naam
BUURT_ALIAS = {
    "Waterkwartier": "Biezen",       # PDOK noemt soms Waterkwartier voor 6541
    "Nijmegen-Centrum": "Stadscentrum",
    "Nijmegen-Oud-West": "Biezen",
}

# Marks eigen straten (voor highlight in de tabel)
EIGEN_STRATEN = ["Graafsedwarsstraat", "Eerste Oude Heselaan"]
ACQUISITIE_STRATEN = ["Fransestraat", "Van Spaenstraat"]

PDOK_FREE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
PDOK_LOOKUP = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/lookup"

HEADERS = {"User-Agent": "DerksenVastgoedMonitor/1.0"}
RATE_LIMIT_SEC = 0.2  # PDOK fair use policy


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
    """
    Format per regel: adres | plaats | prijs | status
    Regels met # zijn commentaar. Lege regels worden overgeslagen.
    """
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
                print(f"Regel {lineno} overgeslagen (onvolledig): {regel}", file=sys.stderr)
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


def pdok_free(adres, plaats):
    """Zoek een adres. Geef nummeraanduiding_id + postcode + buurtnaam terug."""
    q = f"{adres} {plaats}"
    try:
        r = requests.get(PDOK_FREE, params={
            "q": q, "fq": "type:adres", "rows": 1,
        }, headers=HEADERS, timeout=15)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        d = docs[0]
        return {
            "id": d.get("id"),
            "postcode": d.get("postcode", ""),
            "buurtnaam": d.get("buurtnaam", ""),
            "wijknaam": d.get("wijknaam", ""),
            "weergavenaam": d.get("weergavenaam", ""),
        }
    except Exception as e:
        print(f"PDOK free '{q}': {e}", file=sys.stderr)
        return None


def pdok_lookup(id_):
    """Haal per id oppervlakte + gebruiksdoel op."""
    try:
        r = requests.get(PDOK_LOOKUP, params={"id": id_}, headers=HEADERS, timeout=15)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        d = docs[0]
        return {
            "oppervlakte": d.get("oppervlakte"),
            "gebruiksdoel": d.get("gebruiksdoel"),
            "bouwjaar": d.get("bouwjaar"),
        }
    except Exception as e:
        print(f"PDOK lookup {id_}: {e}", file=sys.stderr)
        return None


def verrijk(woning, cache):
    """Voeg oppervlakte, postcode, buurt toe uit BAG. Cache uses adres+plaats key."""
    sleutel = f"{woning['adres']}|{woning['plaats']}"
    if sleutel in cache:
        c = cache[sleutel]
        woning.update(c)
        return woning
    # Nieuwe lookup
    vrij = pdok_free(woning["adres"], woning["plaats"])
    if not vrij or not vrij.get("id"):
        cache[sleutel] = {"gefaald": True}
        return woning
    time.sleep(RATE_LIMIT_SEC)
    detail = pdok_lookup(vrij["id"])
    time.sleep(RATE_LIMIT_SEC)
    if not detail:
        cache[sleutel] = {"gefaald": True, **vrij}
        return woning
    verrijking = {**vrij, **detail}
    cache[sleutel] = verrijking
    woning.update(verrijking)
    return woning


def normaliseer_buurt(buurtnaam):
    """Map PDOK-buurtnamen naar onze focus-buurten waar nodig."""
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

    # Groepeer per genormaliseerde buurt
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

    # Boxplot-tabel
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

    # Highlight: transacties in Marks straten
    eigen_hits = []
    acq_hits = []
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

    # Bod-referentie
    r.append("_Vuistregel Derksen: bod = 17× jaarhuur. Bij €12/m²/maand huur = €2.448/m² bod-referentie; bij €15/m²/maand = €3.060/m²._")

    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="marktprijzen_digest.md")
    ap.add_argument("--input", default=INPUT_PAD)
    args = ap.parse_args()

    woningen = lees_verkopen(args.input)
    print(f"Ingelezen: {len(woningen)} regels uit {args.input}", file=sys.stderr)
    if not woningen:
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write("\n## Marktprijzen koop per buurt\n\n_Nog geen data. Voeg regels toe aan verkopen.txt._\n")
        return

    cache = lees_cache()
    print(f"Cache-entries: {len(cache)}", file=sys.stderr)

    verrijkt = 0
    nieuw = 0
    for w in woningen:
        was_nieuw = f"{w['adres']}|{w['plaats']}" not in cache
        verrijk(w, cache)
        if w.get("oppervlakte"):
            verrijkt += 1
        if was_nieuw:
            nieuw += 1

    schrijf_cache(cache)
    print(f"Verrijkt met BAG: {verrijkt}/{len(woningen)} (nieuw opgehaald: {nieuw})", file=sys.stderr)

    md = render(woningen)
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
