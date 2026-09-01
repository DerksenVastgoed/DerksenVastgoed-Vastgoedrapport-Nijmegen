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

BUURT_ALIAS = {
    "Waterkwartier": "Biezen",
    "Nijmegen-Centrum": "Stadscentrum",
    "Nijmegen-Oud-West": "Biezen",
}

BAG_API_KEY = os.environ.get("BAG_API_KEY", "")
DEBUG = False        # met --debug: toont welke velden de BAG teruggeeft
_DEBUG_TELLER = [0]  # beperkt de debug-uitvoer tot de eerste paar adressen
BAG_BASE = "https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2"
BAG_HEADERS = {
    "X-Api-Key": BAG_API_KEY,
    "Accept": "application/hal+json",
    "Accept-Crs": "epsg:28992",
}
RATE_LIMIT_SEC = 1.1

PDOK_FREE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
PDOK_HEADERS = {"User-Agent": "NijmegenVastgoedMonitor/1.0"}

ARCHIEF_PAD = "bekendmakingen_archief.json"
MONUMENTEN_PAD = "rijksmonumenten_nijmegen.json"


def lees_monumenten():
    """Rijksmonumenten per adres, opgehaald door rijksmonumenten.py."""
    if not os.path.exists(MONUMENTEN_PAD):
        return {}
    try:
        with open(MONUMENTEN_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def lees_archief():
    """Archief van bekendmakingen per adres, gebouwd door bekendmakingen_archief.py."""
    if not os.path.exists(ARCHIEF_PAD):
        return {}
    try:
        with open(ARCHIEF_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def archief_sleutel(straat, huisnr):
    """Zelfde normalisatie als in bekendmakingen_archief.py, anders matcht niets."""
    s = straat.lower()
    s = s.replace("sint ", "st ").replace("st. ", "st ")
    s = s.replace("professor ", "prof ").replace("prof. ", "prof ")
    s = s.replace("burgemeester ", "burg ").replace("burg. ", "burg ")
    s = re.sub(r"[^a-z0-9]", "", s)
    return f"{s}{huisnr}"


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
            # Vijfde veld is de datum waarop we dit object zagen. Oude regels
            # zonder datum blijven gewoon werken; die tellen als 'onbekend'.
            datum = delen[4] if len(delen) > 4 else ""
            bron = delen[5] if len(delen) > 5 else ""
            # Veld 7 en 8 komen uit de advertentie zelf. Bij huuraanbod zonder
            # huisnummer is dat de enige bron voor oppervlakte en buurt.
            opp_bron = delen[6] if len(delen) > 6 else ""
            postcode_bron = delen[7] if len(delen) > 7 else ""
            if datum and not re.match(r"^\d{4}-\d{2}-\d{2}$", datum):
                datum = ""
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
                "datum": datum,
                "bron": bron,
                "oppervlakte_bron": int(opp_bron) if opp_bron.isdigit() else None,
                "postcode_bron": postcode_bron,
                "regelnr": lineno,
            })
    return resultaat



AFKORTINGEN = [
    ("prof. ", "professor "), ("prof ", "professor "),
    ("st. ", "sint "), ("st ", "sint "),
    ("burg. ", "burgemeester "), ("burg ", "burgemeester "),
    ("dr. ", "doctor "), ("dr ", "doctor "),
    ("gen. ", "generaal "), ("mr. ", "meester "),
    ("v. ", "van "), ("v.d. ", "van de "),
]


def straatvarianten(straat):
    """Geeft schrijfwijzen van een straatnaam die de BAG kan hanteren."""
    varianten = [straat]
    laag = straat.lower()
    for kort, lang in AFKORTINGEN:
        if laag.startswith(kort):
            varianten.append(lang.capitalize() + straat[len(kort):])
            break
        if laag.startswith(lang):
            for k, l in AFKORTINGEN:
                if l == lang:
                    varianten.append(k.capitalize() + straat[len(lang):])
                    break
            break
    # Punt weglaten of juist toevoegen
    if "." in straat:
        varianten.append(straat.replace(".", ""))
    return list(dict.fromkeys(varianten))


def split_huisnummer(adres):
    """
    Splitst een adres in straat, huisnummer en achtervoegsel.
    Geeft een LIJST van interpretaties terug, want een achtervoegsel kan in de BAG
    een huisletter of een huisnummertoevoeging zijn. Beide worden geprobeerd.

    'Voorbeeldstraat 20'    -> [('Voorbeeldstraat','20',None,None)]
    'Voorbeeldstraat 20A'   -> [(...,'20','A',None), (...,'20',None,'A')]
    'Voorbeeldstraat 1-B'   -> [(...,'1','B',None), (...,'1',None,'B')]
    'Voorbeeldstraat 7A-12' -> [(...,'7','A','12')]
    """
    s = adres.strip()
    # Straten met een getal in de naam ('Plein 1944 168'): pak het laatste getal
    jaartal = re.match(r"^(.+?\s+\d{4})\s+(\d+)\s*([A-Za-z])?\s*$", s)
    if jaartal:
        return [(jaartal.group(1).strip(), jaartal.group(2),
                 (jaartal.group(3) or "").upper() or None, None)]
    m = re.match(r"^(.+?)\s+(\d+)\s*[-\s]?\s*([A-Za-z])?\s*[-\s]?\s*([A-Za-z0-9]{1,4})?\s*$", s)
    if not m:
        return []
    straat = m.group(1).strip()
    huisnr = m.group(2)
    letter = (m.group(3) or "").upper() or None
    toev = (m.group(4) or "").upper() or None

    if letter and toev:
        return [(straat, huisnr, letter, toev)]
    achter = letter or toev
    if not achter:
        return [(straat, huisnr, None, None)]
    varianten = []
    if len(achter) == 1 and achter.isalpha():
        varianten.append((straat, huisnr, achter, None))   # huisletter
        varianten.append((straat, huisnr, None, achter))   # toevoeging
    else:
        varianten.append((straat, huisnr, None, achter))
        varianten.append((straat, huisnr, None, None))
    return varianten



def pdok_buurt_postcode(postcode):
    """Buurt bepalen uit een postcode, voor adressen zonder huisnummer."""
    if not postcode:
        return {}
    try:
        r = requests.get(PDOK_FREE, params={
            "q": postcode, "fq": "type:postcode", "rows": 1,
            "fl": "buurtnaam wijknaam postcode",
        }, headers=PDOK_HEADERS, timeout=15)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return {}
        d = docs[0]
        return {"postcode": d.get("postcode", postcode),
                "buurtnaam": d.get("buurtnaam", ""),
                "wijknaam": d.get("wijknaam", "")}
    except Exception:
        return {}


def pdok_buurt(straat, huisnr, plaats):
    q = f"{straat} {huisnr} {plaats}"
    try:
        r = requests.get(PDOK_FREE, params={
            "q": q, "fq": "type:adres", "rows": 1,
            "fl": "id buurtnaam wijknaam postcode weergavenaam",
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
            # Nummeraanduiding-id: hiermee kunnen we rechtstreeks naar het
            # Digitaal Gebouwen Archief van de gemeente linken.
            "nummeraanduiding": d.get("id", ""),
        }
    except Exception as e:
        print(f"  PDOK buurt-lookup '{q}': {e}", file=sys.stderr)
        return {}


EP_API_KEY = os.environ.get("EP_API_KEY", "")
EP_BASE = "https://public.ep-online.nl/api/v5/PandEnergielabel"
EP_HEADERS = {"Authorization": EP_API_KEY, "Accept": "application/json"}


def _ep_eerste(data):
    """De API geeft soms een lijst, soms een enkel object terug."""
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        for sleutelnaam in ("results", "data", "items"):
            binnen = data.get(sleutelnaam)
            if isinstance(binnen, list) and binnen:
                return binnen[0]
        return data
    return None


def _ep_veld(rec, namen):
    """Veldnamen verschillen per versie; probeer meerdere schrijfwijzen."""
    for naam in namen:
        for sleutel_ in (naam, naam.lower(), naam.replace("_", "")):
            for k, v in rec.items():
                if k.lower().replace("_", "") == sleutel_.lower().replace("_", ""):
                    if v not in (None, ""):
                        return v
    return None


def ep_energielabel(vbo_id, postcode, huisnr, letter, toev):
    """
    Haalt het energielabel op uit EP-Online.
    Bij voorkeur op VBO-id (exact), anders op postcode plus huisnummer.
    Geeft None terug als er geen key is of niets gevonden wordt.
    """
    if not EP_API_KEY:
        return None

    pogingen = []
    if vbo_id:
        pogingen.append((f"{EP_BASE}/AdresseerbaarObject/{vbo_id}", None))
    if postcode and huisnr:
        params = {"postcode": postcode.replace(" ", ""), "huisnummer": huisnr}
        if letter:
            params["huisletter"] = letter
        if toev:
            params["huisnummertoevoeging"] = toev
        pogingen.append((f"{EP_BASE}/Adres", params))

    for url, params in pogingen:
        try:
            r = requests.get(url, headers=EP_HEADERS, params=params, timeout=20)
            if r.status_code in (401, 403):
                print("  EP-Online: key geweigerd of nog niet actief", file=sys.stderr)
                return None
            if r.status_code == 404:
                continue
            r.raise_for_status()
            rec = _ep_eerste(r.json())
        except Exception as e:
            print(f"  EP-Online-fout: {e}", file=sys.stderr)
            continue
        if not isinstance(rec, dict) or not rec:
            continue

        prive = _ep_veld(rec, ["Pand_energielabel_is_prive", "isPrive", "prive"])
        if str(prive) in ("1", "True", "true"):
            return {"label": None, "prive": True}

        label = _ep_veld(rec, ["Pand_energieklasse", "energieklasse", "labelLetter",
                               "Pand_labelletter", "energielabel", "labelletter"])
        if not label:
            continue
        return {
            "label": str(label).strip(),
            "registratiedatum": str(_ep_veld(rec, ["Pand_registratiedatum",
                                                   "registratiedatum"]) or "")[:10],
            "geldig_tot": str(_ep_veld(rec, ["Meting_geldig_tot", "geldigTot",
                                             "metingGeldigTot"]) or "")[:10],
            "gebouwklasse": _ep_veld(rec, ["Pand_gebouwklasse", "gebouwklasse"]) or "",
            "prive": False,
        }
    return None


def bag_adres_uitgebreid(straat, huisnr, letter, toev, plaats):
    """
    Roept BAG /adressenuitgebreid aan. Retourneert oppervlakte, bouwjaar,
    gebruiksdoelen, postcode.

    Het bouwjaar (oorspronkelijkBouwjaar) hoort bij het PAND, niet bij het adres,
    dus vragen we het pand mee op met expand.
    """
    if not BAG_API_KEY:
        return None
    params = {
        "openbareRuimteNaam": straat,
        "huisnummer": huisnr,
        "woonplaatsNaam": plaats,
        "exacteMatch": "true",
        "expand": "panden",
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
            print("  BAG 401: API-key ongeldig?", file=sys.stderr)
            return None
        if r.status_code == 400 and "expand" in r.text.lower():
            # Sommige omgevingen accepteren expand=panden niet; opnieuw zonder.
            params.pop("expand", None)
            r = requests.get(f"{BAG_BASE}/adressenuitgebreid",
                             headers=BAG_HEADERS, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except requests.HTTPError:
        print(f"  BAG HTTP {r.status_code}: {straat} {huisnr}{letter or ''}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  BAG-fout {straat} {huisnr}: {e}", file=sys.stderr)
        return None

    embedded = data.get("_embedded", {}).get("adressen", [])
    if not embedded:
        return None
    a = embedded[0]

    if DEBUG and _DEBUG_TELLER[0] < 2:
        _DEBUG_TELLER[0] += 1
        print(f"  DEBUG {straat} {huisnr}: velden op adresniveau = "
              f"{sorted(a.keys())}", file=sys.stderr)
        inner = a.get("_embedded")
        if isinstance(inner, dict):
            for naam, waarde in inner.items():
                if isinstance(waarde, list) and waarde and isinstance(waarde[0], dict):
                    print(f"  DEBUG   _embedded.{naam}[0] = {sorted(waarde[0].keys())}",
                          file=sys.stderr)
                elif isinstance(waarde, dict):
                    print(f"  DEBUG   _embedded.{naam} = {sorted(waarde.keys())}",
                          file=sys.stderr)

    return {
        "oppervlakte": a.get("oppervlakte"),
        "bouwjaar": _bouwjaar_uit(a),
        "gebruiksdoelen": a.get("gebruiksdoelen", []),
        "postcode": a.get("postcode", ""),
        "adresseerbaarObjectIdentificatie": a.get("adresseerbaarObjectIdentificatie", ""),
    }


def _bouwjaar_uit(a):
    """
    Zoekt het bouwjaar in de adres-respons. Officieel heet het veld
    oorspronkelijkBouwjaar en hoort het bij het pand, maar afhankelijk van
    expand zit het op verschillende plekken. Daarom breed zoeken.
    """
    def eerste(waarde):
        if isinstance(waarde, list) and waarde:
            return waarde[0]
        return waarde

    for veld in ("oorspronkelijkBouwjaar", "adresseerbaarObjectBouwjaar", "bouwjaar"):
        waarde = eerste(a.get(veld))
        if waarde:
            return waarde

    # Via expand komt het pand mee onder _embedded
    inner = a.get("_embedded")
    if isinstance(inner, dict):
        for naam in ("panden", "pand"):
            panden = inner.get(naam)
            if isinstance(panden, dict):
                panden = [panden]
            if not isinstance(panden, list):
                continue
            for p in panden:
                if not isinstance(p, dict):
                    continue
                waarde = eerste(p.get("oorspronkelijkBouwjaar") or p.get("bouwjaar"))
                if waarde:
                    return waarde
    return None


def verrijk(woning, cache):
    sleutel = f"{woning['adres']}|{woning['plaats']}"
    if sleutel in cache and not cache[sleutel].get("gefaald"):
        gegevens = cache[sleutel]
        # Energielabel ontbreekt nog in oudere cache-regels: alleen die ophalen,
        # de BAG-gegevens zijn al bekend en hoeven niet opnieuw.
        if EP_API_KEY and "energielabel" not in gegevens:
            varianten = split_huisnummer(woning["adres"])
            letter = toev = None
            huisnr = ""
            if varianten:
                _, huisnr, letter, toev = varianten[0]
            ep = ep_energielabel(gegevens.get("adresseerbaarObjectIdentificatie"),
                                 gegevens.get("postcode"), huisnr, letter, toev)
            time.sleep(0.3)
            gegevens["energielabel"] = ep  # ook None bewaren, anders elke run opnieuw
            cache[sleutel] = gegevens
        woning.update(gegevens)
        return woning

    varianten = split_huisnummer(woning["adres"])

    # Adres zonder huisnummer, zoals Pararius bij huuraanbod toont. De advertentie
    # gaf dan zelf de oppervlakte, en de buurt halen we uit de postcode.
    if not varianten:
        if woning.get("oppervlakte_bron"):
            gegevens = {"oppervlakte": woning["oppervlakte_bron"],
                        "gebruiksdoelen": ["woonfunctie"]}
            gegevens.update(pdok_buurt_postcode(woning.get("postcode_bron", "")))
            time.sleep(0.2)
            cache[sleutel] = gegevens
            woning.update(gegevens)
            return woning
        print(f"  FAIL parse: {woning['adres']}", file=sys.stderr)
        cache[sleutel] = {"gefaald": True, "reden": "parse"}
        return woning

    bag = None
    for straat, huisnr, letter, toev in varianten:
        for straatnaam in straatvarianten(straat):
            bag = bag_adres_uitgebreid(straatnaam, huisnr, letter, toev, woning["plaats"])
            time.sleep(RATE_LIMIT_SEC)
            if bag and bag.get("oppervlakte"):
                break
            bag = None
        if bag:
            break

    # Laatste redmiddel: kaal huisnummer zonder achtervoegsel
    if not bag:
        straat, huisnr = varianten[0][0], varianten[0][1]
        bag = bag_adres_uitgebreid(straat, huisnr, None, None, woning["plaats"])
        time.sleep(RATE_LIMIT_SEC)

    if not bag or not bag.get("oppervlakte"):
        print(f"  FAIL BAG: {woning['adres']}", file=sys.stderr)
        cache[sleutel] = {"gefaald": True, "reden": "bag_geen_oppervlakte"}
        return woning

    pdok = pdok_buurt(varianten[0][0], varianten[0][1], woning["plaats"])
    time.sleep(0.2)

    verrijking = {**bag, **pdok}

    # Energielabel uit EP-Online, bij voorkeur op het VBO-id uit de BAG
    if EP_API_KEY:
        straat, huisnr, letter, toev = varianten[0]
        ep = ep_energielabel(
            verrijking.get("adresseerbaarObjectIdentificatie"),
            verrijking.get("postcode") or pdok.get("postcode"),
            huisnr, letter, toev)
        time.sleep(0.3)
        if ep:
            verrijking["energielabel"] = ep

    cache[sleutel] = verrijking
    woning.update(verrijking)
    return woning


def normaliseer_buurt(buurtnaam):
    if not buurtnaam:
        return ""
    if buurtnaam in FOCUS_BUURTEN:
        return buurtnaam
    return BUURT_ALIAS.get(buurtnaam, buurtnaam)




COMMERCIEEL = ["winkel", "kantoor", "horeca", "bijeenkomst", "industrie", "logies"]




CBS_PAD = "buurten_cbs.json"



BEKENDMAKINGEN_PAD = "bekendmakingen_vandaag.json"


def lees_bekendmakingen(cache):
    """
    Leest de bekendmakingen van vandaag en bepaalt per bericht in welke buurt
    het adres ligt, zodat nieuws en aanbod per gebied bij elkaar komen.
    De buurt-opzoeking gaat via de cache, dus meestal zonder extra verkeer.
    """
    if not os.path.exists(BEKENDMAKINGEN_PAD):
        return {}, []
    try:
        with open(BEKENDMAKINGEN_PAD, encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return {}, []

    per_buurt, zonder_buurt = defaultdict(list), []
    for it in items:
        straat, huisnr = it.get("straat", ""), it.get("huisnummer", "")
        if not straat or not huisnr:
            zonder_buurt.append(it)
            continue
        sleutel = f"bm:{straat} {huisnr}|Nijmegen"
        gegevens = cache.get(sleutel)
        if gegevens is None:
            gegevens = pdok_buurt(straat, huisnr, "Nijmegen")
            time.sleep(0.2)
            cache[sleutel] = gegevens or {}
        buurt = normaliseer_buurt((gegevens or {}).get("buurtnaam", ""))
        if buurt:
            it["buurt"] = buurt
            per_buurt[buurt].append(it)
        else:
            zonder_buurt.append(it)
    return per_buurt, zonder_buurt


KLEUREN = {
    "uitponden": "#B8860B", "buy-and-hold": "#4a7a72", "splitsen": "#7B5EA7",
    "kamerverhuur": "#C46A2F", "transformatie": "#2E6DA4", "verduurzaming": "#4E8C3A",
}


def _chip(label):
    """Klein gekleurd labeltje voor de strategie."""
    if not label or label == "geen":
        return ""
    kleur = KLEUREN.get(label, "#4a5b63")
    return (f'<span style="display:inline-block;background:{kleur};color:#fff;'
            f'font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;'
            f'margin-right:8px;vertical-align:middle">{label}</span>')


def bekendmakingregels(items):
    """
    Bekendmakingen als kaartjes onder een buurt. De stijl staat op de elementen
    zelf, want veel mailprogramma's negeren een stylesheet in de kop.
    """
    r = []
    for it in sorted(items, key=lambda x: (not x.get("kern"), x.get("datum", ""))):
        titel = it.get("titel", "")
        url = it.get("url", "")
        kop = (f'<a href="{url}" style="color:#12242c;text-decoration:none">{titel}</a>'
               if url else titel)

        feiten = it.get("feiten") or {}
        delen = []
        if feiten.get("oppervlakte_m2"):
            delen.append(f"{feiten['oppervlakte_m2']} m²")
        if feiten.get("bouwjaar"):
            delen.append(f"bouwjaar {feiten['bouwjaar']}")
        if feiten.get("m2_per_kamer"):
            delen.append(f"{feiten['m2_per_kamer']} m² per kamer")
        if feiten.get("energielabel"):
            delen.append(f"label {feiten['energielabel']}")
        if feiten.get("rijksmonument"):
            nr = feiten.get("monumentnr")
            delen.append(f"rijksmonument{f' {nr}' if nr else ''}")

        blok = ['<div style="border-left:3px solid #E0A458;background:#f7f9fa;'
                'border-radius:0 6px 6px 0;padding:12px 14px;margin:0 0 12px 0">',
                f'<div style="margin-bottom:6px">'
                f'{_chip((it.get("strategie") or "").strip())}'
                f'<span style="font-weight:700;font-size:14px;line-height:1.35">'
                f'{kop}</span></div>']
        if delen:
            blok.append('<div style="font-size:12px;color:#12242c;background:#eef2f4;'
                        'display:inline-block;padding:3px 8px;border-radius:4px;'
                        'margin-bottom:6px;font-family:ui-monospace,Menlo,Consolas,monospace">'
                        + " . ".join(delen) + "</div>")
        if it.get("duiding"):
            blok.append(f'<div style="font-size:13px;color:#4a5b63;font-style:italic">'
                        f'{it["duiding"]}</div>')
        voet = [v for v in [it.get("datum", ""),
                            (f'<a href="{url}" style="color:#4a7a72;'
                             f'text-decoration:none">bron</a>' if url else "")] if v]
        blok.append(f'<div style="font-size:11px;color:#7a8a92;margin-top:8px">'
                    f'{" . ".join(voet)}</div>')
        blok.append("</div>")
        r.append("\n".join(blok))
        r.append("")
    return r


def lees_cbs():
    """Buurtcijfers uit het CBS, weggeschreven door buurten_tabel.py."""
    if not os.path.exists(CBS_PAD):
        return {}
    try:
        with open(CBS_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def buurtregel(naam, cbs, opp_uit_bag=None, studenten_ring=None):
    """
    Een regel met de kenmerken van een buurt, alleen als we ze hebben.
    Toont ook de WOZ per m2, want dat is beter vergelijkbaar tussen buurten
    dan een gemiddelde WOZ: die hangt sterk af van de woninggrootte.
    Studentenaantallen krijgen twee noemers: het aandeel van de inwoners
    (hoe studentikoos is de buurt) en het aandeel van alle studenten in de
    ring (waar zit de vraag). Een absoluut aantal zegt op zichzelf te weinig.
    """
    g = cbs.get(naam)
    if not g:
        return ""
    delen = []
    if g.get("won"):
        delen.append(f"{g['won']:,}".replace(",", ".") + " woningen")
    if g.get("koop") is not None:
        delen.append(f"{g['koop']}% koop")
    if g.get("corp") is not None:
        delen.append(f"{g['corp']}% corporatie")
    if g.get("over") is not None:
        delen.append(f"{g['over']}% overige verhuurders")
    if g.get("woz"):
        delen.append("WOZ €" + f"{g['woz'] * 1000:,}".replace(",", "."))

        # WOZ per m2: eerst de CBS-oppervlakte, anders ons eigen BAG-gemiddelde
        opp, herkomst = g.get("opp"), "CBS"
        if not opp and opp_uit_bag:
            opp, herkomst = opp_uit_bag, "eigen aanbod"
        if opp:
            wozm2 = round(g["woz"] * 1000 / opp)
            delen.append(f"WOZ €{wozm2:,}".replace(",", ".")
                         + f"/m² bij {opp} m² gemiddeld ({herkomst})")

    # Kenmerken die raken aan splitsen, renoveren en kamerverhuur
    tweede = []
    if g.get("meergezins") is not None:
        tweede.append(f"{g['meergezins']}% appartementen")
    if g.get("voor2000") is not None:
        tweede.append(f"{g['voor2000']}% van voor 2000")
    if g.get("studenten"):
        stuk = f"{g['studenten']:,}".replace(",", ".") + " studenten"
        noemers = []
        if g.get("inwoners"):
            noemers.append(f"{round(g['studenten'] / g['inwoners'] * 100)}% van de inwoners")
        if studenten_ring:
            noemers.append(f"{round(g['studenten'] / studenten_ring * 100)}% van alle "
                           f"studenten in de ring")
        if noemers:
            stuk += " (" + ", ".join(noemers) + ")"
        tweede.append(stuk)
    if g.get("leegstand") is not None and g["leegstand"] > 0:
        tweede.append(f"{g['leegstand']}% leegstand")

    regel = " . ".join(delen)
    if tweede:
        regel += "<br>" + " . ".join(tweede)
    return regel


def gemiddelde_oppervlakte_per_buurt(woningen):
    """Gemiddelde BAG-oppervlakte per buurt uit de eigen lijst, als terugval."""
    per_buurt = defaultdict(list)
    for w in woningen:
        buurt = normaliseer_buurt(w.get("buurtnaam", ""))
        opp = w.get("oppervlakte")
        if buurt and opp and 15 <= opp <= 400:
            per_buurt[buurt].append(opp)
    return {b: round(st.mean(v)) for b, v in per_buurt.items() if len(v) >= 5}


def kaartlink(adres, plaats="Nijmegen", bron=""):
    """
    Adres als verwijzing naar Google Maps. Kennen we ook de oorspronkelijke
    advertentie, dan komt daar een tweede verwijzing achter.
    """
    zoek = urllib.parse.quote_plus(f"{adres}, {plaats}")
    tekst = f"[{adres}](https://www.google.com/maps/search/?api=1&query={zoek})"
    if bron and bron.startswith("http"):
        tekst += f" [↗]({bron})"
    return tekst



# Kamerverhuurregels Nijmegen. Onder de ondergrens is verkameren niet toegestaan,
# binnen de band is een omzettingsvergunning nodig bij drie kamers of meer.
# Bedragen uit de evaluatie kamerverhuurbeleid 2024; de gemeente indexeert deze,
# dus jaarlijks controleren op nijmegen.nl.
WOZ_ONDERGRENS = 278_000
WOZ_BOVENGRENS = 396_000



# ---------------------------------------------------------------------------
# KERNGETALLEN. Alles wat de brief rekent hangt hieraan. Pas ze hier aan; ze
# worden onder elke berekening in de brief vermeld, zodat een lezer kan zien
# waar een uitkomst op rust.
# ---------------------------------------------------------------------------
RENTE = 5.75              # verhuurhypotheek, aflossingsvrij
LTV = 66.7                # financieringsgraad op de koopsom
OPEX_PCT = 25             # onderhoud, leegstand, beheer, verzekering
AANKOOPKOSTEN_PCT = 12    # overdrachtsbelasting, notaris, makelaar, taxatie
DOEL_CASHFLOW = 0         # gewenste cashflow per jaar; 0 is precies rondlopen

# Aanname voor de huur per m2 per maand, per buurt. Vervalt zodra er gemeten
# huuraanbiedingen binnenkomen; in de brief staat per buurt welke bron geldt.
HUUR_M2_MND = {
    "Stadscentrum": 20, "Benedenstad": 20, "Bottendaal": 18,
    "Galgenveld": 18, "Altrade": 17, "Biezen": 18,
}



def richtprijs(opp, huur_m2):
    """
    De hoogste koopsom waarbij het pand nog de gewenste cashflow haalt.

    De nettohuur moet de rentelast dekken plus DOEL_CASHFLOW overhouden:
        huur * 12 * m2 * (1 - opex)  -  K * LTV% * rente%  >=  doel
    Oplossen naar K geeft het plafond. Dit is dus geen taxatie en geen bod,
    maar de bovengrens waarboven het pand jaarlijks geld kost.

    Wat er NIET in zit: renovatie om de huur te halen, en de vraag of het
    puntenstelsel die huur uberhaupt toestaat. Beide verlagen dit plafond.
    """
    if not opp or not huur_m2:
        return None
    netto = huur_m2 * 12 * opp * (1 - OPEX_PCT / 100)
    noemer = (LTV / 100) * (RENTE / 100)
    if noemer <= 0:
        return None
    plafond = (netto - DOEL_CASHFLOW) / noemer
    return plafond if plafond > 0 else None


def eigen_inleg(koopsom):
    """Eigen geld: het niet-gefinancierde deel plus de aankoopkosten."""
    return koopsom * (1 - LTV / 100) + koopsom * AANKOOPKOSTEN_PCT / 100


def huur_voor_buurt(buurt, huur_bk, huur_k, opp=None, klasse="woning"):
    """
    Gemeten huur per m2. Eerst de eigen grootteklasse, want die verklaart het
    meeste van de spreiding, dan de buurt, dan stadsbreed, dan de aanname.
    """
    band = groottebandje(opp)
    reeks = huur_k.get((klasse, band), [])
    if len(reeks) >= 3:
        return st.median(reeks), f"gemeten, {len(reeks)} panden {band}"

    reeks = huur_bk.get((klasse, buurt), [])
    if len(reeks) >= 3:
        return st.median(reeks), f"gemeten, {len(reeks)} in {buurt}"

    reeks = huur_k.get(klasse, [])
    if len(reeks) >= 3:
        return st.median(reeks), f"gemeten, {len(reeks)} stadsbreed"

    return HUUR_M2_MND.get(buurt, 18), "aanname"


def verkameren_signaal(prijs):
    """
    Richtinggevende zeef op basis van de vraagprijs. De WOZ zelf is niet vrij
    op te vragen, maar de vraagprijs ligt vrijwel altijd boven de WOZ. Een
    vraagprijs onder de ondergrens betekent dus vrijwel zeker een WOZ eronder.
    """
    if prijs < WOZ_ONDERGRENS:
        return "niet toegestaan"
    if prijs < WOZ_BOVENGRENS * 1.25:
        return "vermoedelijk vergunningplichtig"
    return "vermoedelijk boven de band"


def assetklasse(w):
    """
    Bepaalt de assetklasse uit het BAG-gebruiksdoel.
    Vergelijken doe je binnen een klasse: een winkelpand van 2.100 per m2 is
    niet goedkoop, het is gewoon een ander product dan een woning.
    """
    doelen = [str(d).lower() for d in (w.get("gebruiksdoelen") or [])]
    if not doelen:
        return "onbekend"
    heeft_woon = any("woon" in d for d in doelen)
    heeft_com = any(any(c in d for c in COMMERCIEEL) for d in doelen)
    if heeft_woon and heeft_com:
        return "gemengd"
    if heeft_woon:
        return "woning"
    if heeft_com:
        return "commercieel"
    return "onbekend"


def _labeltekst(ep):
    """Toont het label met het registratiejaar, zodat een oud label opvalt."""
    if not ep:
        return "onbekend"
    if ep.get("prive"):
        return "afgeschermd"
    label = ep.get("label") or "?"
    datum = ep.get("registratiedatum") or ""
    jaar = datum[:4]
    return f"{label} ({jaar})" if jaar else label


def _dagen_sinds(datum):
    """Aantal dagen tussen een datum als jjjj-mm-dd en vandaag."""
    if not datum:
        return None
    try:
        return (dt.date.today() - dt.date.fromisoformat(datum)).days
    except ValueError:
        return None


def render_prijswijzigingen(woningen):
    """Panden waarvan de vraagprijs is veranderd sinds we ze voor het eerst zagen."""
    r = []
    gewijzigd = []
    for w in woningen:
        eerst = w.get("prijs_eerst")
        if not eerst or eerst == w["prijs"]:
            continue
        verschil = w["prijs"] - eerst
        pct = verschil / eerst * 100
        gewijzigd.append((abs(pct), verschil, pct, w))

    if not gewijzigd:
        return r

    r.append("### Prijswijzigingen")
    r.append("")
    r.append("| Adres | Buurt | Eerst | Nu | Verschil | Dagen in aanbod |")
    r.append("|---|---|---:|---:|---:|---:|")
    for _, verschil, pct, w in sorted(gewijzigd, reverse=True):
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
        eerst_s = f"{w['prijs_eerst']:,}".replace(",", ".")
        nu_s = f"{w['prijs']:,}".replace(",", ".")
        teken = "▼" if verschil < 0 else "▲"
        versch_s = f"{abs(verschil):,}".replace(",", ".")
        dagen = _dagen_sinds(w.get("datum_eerst"))
        r.append(f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} | {buurt} | €{eerst_s} | €{nu_s} | "
                 f"{teken} €{versch_s} ({pct:+.1f}%) | {dagen if dagen is not None else '?'} |")
    r.append("")
    r.append("_Een verlaging na langere tijd in de markt is vaak het moment waarop "
             "onderhandelen zin heeft. Dagen in aanbod telt vanaf de eerste keer dat "
             "dit pand in de attendering verscheen, niet vanaf de plaatsing op Funda._")
    r.append("")
    return r


def render_looptijd(woningen):
    """Panden die het langst in de markt staan zonder prijsaanpassing."""
    r = []
    lang = []
    for w in woningen:
        if w.get("status", "").lower() not in ("te koop", "belegging"):
            continue
        dagen = _dagen_sinds(w.get("datum_eerst") or w.get("datum"))
        if dagen is None or dagen < 60:
            continue
        if w.get("prijs_eerst") and w["prijs_eerst"] != w["prijs"]:
            continue  # die staan al bij de prijswijzigingen
        lang.append((dagen, w))

    if not lang:
        return r

    r.append("### Langst in de markt zonder prijsaanpassing")
    r.append("")
    for dagen, w in sorted(lang, reverse=True)[:8]:
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
        prijs_s = f"{w['prijs']:,}".replace(",", ".")
        r.append(f"- **{kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))}** "
                 f"({buurt}) . €{prijs_s} . {dagen} dagen")
    r.append("")
    r.append("_Lang stilstaan zonder aanpassing wijst op een vraagprijs die de markt "
             "niet volgt. Dat is doorgaans het beste moment om te bieden._")
    r.append("")
    return r



def huur_per_m2_maand(w):
    """
    Rekent een huuraanbieding om naar euro per m2 per maand.
    Twee vormen komen binnen:
      'te huur'      prijs is de maandhuur van het hele object
      'te huur pm2'  prijs is de huur per m2 per JAAR, gedeeld door 12
    Beide zijn exacte omrekeningen, geen aannames.
    """
    status = (w.get("status") or "").lower()
    opp = w.get("oppervlakte")
    try:
        if status == "te huur pm2":
            return w["prijs"] / 12
        if status == "te huur kamer" and opp and opp >= 6:
            return w["prijs"] / opp
        if status == "te huur" and opp and opp >= 15:
            return w["prijs"] / opp
    except (TypeError, ZeroDivisionError):
        return None
    return None


def groottebandje(opp):
    """
    Huur per m2 daalt sterk met de omvang: een studio brengt per m2 ruim het
    dubbele op van een groot pand. Een enkele mediaan per buurt beoordeelt
    kleine units daardoor te laag en grote panden te hoog.
    """
    if not opp:
        return "onbekend"
    if opp < 50:
        return "klein"
    if opp <= 100:
        return "middel"
    return "groot"


def kamerhuur_binnen_wwso(w):
    """
    Geeft de vraaghuur terug, begrensd op het wettelijk maximum. Kamerhuur die
    boven het puntenstelsel uitkomt mag een huurder laten terugzetten, dus die
    telt niet mee als opbrengst waarop je een bod baseert.
    """
    if not wwso_bandbreedte or (w.get("status") or "").lower() != "te huur kamer":
        return w.get("prijs")
    opp = w.get("oppervlakte")
    if not opp or opp < 4:
        return w.get("prijs")
    ep = w.get("energielabel") or {}
    band = wwso_bandbreedte(opp, label=ep.get("label"), bouwjaar=w.get("bouwjaar"),
                            monument=bool(w.get("monument")))
    if not band:
        return w.get("prijs")
    return min(w["prijs"], band["hoog"])


def gemeten_huren(huur_aanbod):
    """
    Mediane huur per m2 per maand, per buurt en per klasse.
    Onzelfstandige eenheden (kamers) krijgen een eigen klasse: die liggen per m2
    hoger en zouden de huur voor gewone woningen anders scheeftrekken.
    """
    per_buurt_klasse = defaultdict(list)
    per_klasse = defaultdict(list)
    for w in huur_aanbod:
        # Kamerhuur aftoppen op het wettelijk maximum voordat we er een
        # mediaan van maken; anders rekenen we met huur die niet is toegestaan.
        begrensd = dict(w)
        begrensd["prijs"] = kamerhuur_binnen_wwso(w)
        hm2 = huur_per_m2_maand(begrensd)
        if not hm2:
            continue
        status = (w.get("status") or "").lower()
        bron = (w.get("bron") or "").lower()
        if status == "te huur kamer":
            klasse = "kamer"
            if hm2 < 8 or hm2 > 80:  # daarboven klopt de opgegeven oppervlakte niet
                continue
        else:
            # Zelfstandige eenheden op Kamernet zijn gemeubileerde shortstay met
            # korte contracten. Die brengen per m2 veel meer op dan gewone verhuur
            # en zouden de richtprijzen kunstmatig omhoog duwen.
            if bron.startswith("kamernet"):
                continue
            klasse = assetklasse(w)
            if hm2 < 4 or hm2 > 80:
                continue
        buurt = normaliseer_buurt(w.get("buurtnaam", ""))
        per_klasse[klasse].append(hm2)
        # Ook per grootteklasse, want dat verklaart het meeste van de spreiding
        per_klasse[(klasse, groottebandje(w.get("oppervlakte")))].append(hm2)
        if buurt:
            per_buurt_klasse[(klasse, buurt)].append(hm2)
    return per_buurt_klasse, per_klasse



# ---------------------------------------------------------------------------
# Zondagsbrief: geen lijst maar een handvol uitgewerkte investeringscases.
# ---------------------------------------------------------------------------

BELEID_UITGELICHT = [
    ("Aangewezen wijk",
     "In de aangewezen wijken, waaronder Benedenstad, Centrum, Bottendaal, "
     "Galgenveld, Altrade, Hunnerberg, Biezen en Wolfskuil, is omzetting van "
     "álle woonruimte vergunningplichtig, ongeacht de WOZ-waarde. De WOZ-band "
     "bepaalt dus niet óf je een vergunning nodig hebt, maar of je er een kunt "
     "krijgen."),
    ("Drempel van drie",
     "De vergunningplicht geldt bij omzetting naar drie of meer onzelfstandige "
     "woonruimten én bij bewoning door drie of meer personen. Twee kamers met "
     "drie bewoners valt er dus ook onder."),
    ("Fietsenstalling",
     "Een omzettingsvergunning wordt geweigerd als er geen stalling op eigen "
     "terrein is: anderhalve vierkante meter per bewoner, niet hoger dan de "
     "begane grond, in een afzonderlijke daartoe bestemde ruimte. Bij "
     "vooroorlogse panden zonder achterom is dit vaak de kritieke eis."),
    ("Maximaal twee naast elkaar",
     "Er mogen niet meer dan twee direct naast, onder of boven elkaar gelegen "
     "woningen kamergewijs bewoond zijn, en de omzetting mag geen zelfstandig "
     "bewoonde woning insluiten. In een straat waar de buren al verkamerd zijn "
     "kan het dus niet meer."),
    ("Leefbaarheidstoets",
     "Een ambtelijke adviesgroep beoordeelt of de vergunning leidt tot een "
     "onaanvaardbare inbreuk op het woon- en leefklimaat. Staat het woonmilieu "
     "van de straat al onder druk, dan is dat op zichzelf een weigeringsgrond."),
    ("Boetes bij een BV",
     "Omzetten zonder vergunning kost €5.000 als particulier en €10.000 bij "
     "bedrijfsmatige exploitatie, bij herhaling €7.500 respectievelijk €15.000. "
     "Verhuur je via een vennootschap, dan geldt de hogere staffel."),
    ("Hospita-uitzondering",
     "Vergunningvrij blijft de hospita-constructie: je woont zelf in het pand, "
     "bent volledig eigenaar, gebruikt meer dan de helft zelf en verhuurt "
     "maximaal twee kamers aan maximaal twee personen."),
    ("Bouwbesluit bij verkamering",
     "Na omzetting moeten de kamers voldoen aan de nieuwbouwnormen voor "
     "luchtgeluidsisolatie en aan de eisen voor brandveilig gebruik. Dat is "
     "bij een vooroorlogs pand zelden een kleine ingreep."),
]


def _beleid_van_de_week():
    """Rouleert door de beleidsonderdelen op weeknummer, zodat elke week iets anders."""
    week = dt.date.today().isocalendar()[1]
    return BELEID_UITGELICHT[week % len(BELEID_UITGELICHT)]



def coordinaten(straat, huisnr, plaats="Nijmegen"):
    """Haalt de coordinaten van een adres op via PDOK, voor de kaart."""
    try:
        r = requests.get(PDOK_FREE, params={
            "q": f"{straat} {huisnr} {plaats}", "fq": "type:adres", "rows": 1,
            "fl": "centroide_ll weergavenaam",
        }, headers=PDOK_HEADERS, timeout=15)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        punt = docs[0].get("centroide_ll", "")
        m = re.match(r"POINT\(([-\d.]+) ([-\d.]+)\)", punt)
        if not m:
            return None
        return float(m.group(2)), float(m.group(1))  # lat, lon
    except Exception:
        return None



DGA_BASIS = "https://app4.nijmegen.nl/DGD2/Bouwarchief/Index/"


def bouwarchief_link(w):
    """
    Rechtstreekse link naar het Digitaal Gebouwen Archief van Nijmegen.
    De pagina werkt op de BAG-nummeraanduiding, die we bij de adres-lookup
    al ophalen. Daar staan de bouwtekeningen en constructiegegevens; je
    selecteert de stukken en krijgt een downloadlink per mail.
    """
    nr = (w.get("nummeraanduiding") or "").strip()
    if not nr or not nr.isdigit():
        return ""
    return DGA_BASIS + nr


def streetview_link(adres, plaats="Nijmegen"):
    """Link naar Street View. Een ingesloten foto vraagt een betaalde sleutel."""
    zoek = urllib.parse.quote_plus(f"{adres}, {plaats}")
    return f"https://www.google.com/maps/search/?api=1&query={zoek}&layer=c"


def schrijf_top3_kaart(panden, pad="top3-kaart.html"):
    """
    Schrijft een kaartpagina met de uitgelichte panden. Die komt op GitHub Pages
    te staan, zodat de brief er met een link naar kan verwijzen. Bij een nieuwe
    top drie wordt de pagina overschreven.
    """
    punten = []
    for rang, w in enumerate(panden, 1):
        varianten = split_huisnummer(w["adres"])
        if not varianten:
            continue
        coord = coordinaten(varianten[0][0], varianten[0][1], w.get("plaats", "Nijmegen"))
        time.sleep(0.2)
        if not coord:
            continue
        prijs = f"{w['prijs']:,}".replace(",", ".")
        ppm2 = f"{int(w['prijs'] / w['oppervlakte']):,}".replace(",", ".")
        punten.append({
            "rang": rang, "lat": coord[0], "lon": coord[1],
            "adres": w["adres"],
            "buurt": normaliseer_buurt(w.get("buurtnaam", "")) or "",
            "tekst": f"€{prijs} . {w['oppervlakte']} m² . €{ppm2}/m²",
        })
    if not punten:
        return False

    vandaag = dt.date.today().strftime("%d-%m-%Y")
    html = """<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uitgelichte panden</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
 body{margin:0;font:14px -apple-system,Segoe UI,Roboto,sans-serif;color:#1a2830}
 header{padding:14px 18px;border-bottom:2px solid #E0A458}
 h1{margin:0;font-size:18px}
 p{margin:4px 0 0;color:#4a5b63;font-size:13px}
 #kaart{height:calc(100vh - 74px)}
 .nr{background:#12242c;color:#fff;border-radius:50%;width:26px;height:26px;
     line-height:26px;text-align:center;font-weight:700}
</style></head><body>
<header><h1>Uitgelichte panden</h1><p>Bijgewerkt __DATUM__</p></header>
<div id="kaart"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var punten = __PUNTEN__;
var kaart = L.map('kaart');
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom:19, attribution:'&copy; OpenStreetMap'}).addTo(kaart);
var groep = [];
punten.forEach(function(p){
  var icoon = L.divIcon({html:'<div class="nr">'+p.rang+'</div>', className:'', iconSize:[26,26]});
  var m = L.marker([p.lat,p.lon],{icon:icoon}).addTo(kaart)
    .bindPopup('<b>'+p.adres+'</b><br>'+p.buurt+'<br>'+p.tekst);
  groep.push([p.lat,p.lon]);
});
kaart.fitBounds(groep,{padding:[60,60]});
if(punten.length===1){kaart.setView(groep[0],16);}
</script></body></html>"""
    html = html.replace("__DATUM__", vandaag)
    html = html.replace("__PUNTEN__", json.dumps(punten, ensure_ascii=False))
    with open(pad, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Kaart met {len(punten)} panden weggeschreven naar {pad}", file=sys.stderr)
    return True



ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MEMO_MODEL = "claude-sonnet-5"

MEMO_PROFIEL = """Je schrijft de zondagseditie van een vastgoedbrief over de binnenring van Nijmegen. Lezers zijn particuliere investeerders en kleine ontwikkelaars.

Je krijgt per pand een blok met FEITEN: alles is al berekend. Schrijf daarover een kort investeringsmemo in doorlopend Nederlands, twee tot drie alinea's per pand, dat toewerkt naar een oordeel.

UITGANGSPUNT: het gewone geval is kopen en verhuren. Beoordeel een pand dus eerst als exploitatieobject: wat kost het, wat brengt het op, houdt het zichzelf rond bij deze rente. Een bescheiden ingreep die het energielabel verbetert telt mee in de WWS-punten en daarmee in de maximaal toegestane huur; dat is bij een matig label vaak de meest realistische route naar meer rendement.

Uitponden, splitsen of verkameren zijn UITZONDERINGEN. Noem die alleen als de feiten er aanleiding toe geven, bijvoorbeeld een grote oppervlakte, een hoog aandeel appartementen in de buurt of een aanzienlijke uitpondruimte. Presenteer ze nooit als vanzelfsprekend, en benoem dan ook meteen de beperking: in een aangewezen wijk is omzetting vergunningplichtig, en onder de WOZ-grens is verkameren simpelweg niet toegestaan.

Bouw het memo zo op: waarom valt dit pand op, wat zeggen de cijfers over de positie in de markt, wat doet het rendement bij de huidige rente, wat is de meest voor de hand liggende route naar meer huur of waarde, en welk risico of welke beperking staat daartegenover. Sluit af met een oordeel in een zin.

Staat er een "bod voor cashflow nul" bij de feiten, verwerk dat dan in je oordeel. Ligt dat bedrag onder de vraagprijs, benoem dan hoeveel eraf zou moeten voordat het pand zichzelf rondhoudt. Dat is geen taxatie maar een vertrekpunt voor onderhandeling; schrijf het ook zo op.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS.
- Gebruik UITSLUITEND getallen die letterlijk in de FEITEN staan.
- Verzin nooit huurprijzen, rendementen, kosten, WOZ-waarden, WWS-punten of percentages die er niet staan.
- Staat een gegeven er niet, benoem dan dat het onbekend is of laat het weg.
- Noem bij een aanname dat het een aanname is; dat staat bij de feiten vermeld.

STIJL:
- Doorlopende zinnen, geen opsommingen, geen kopjes als "Het pand" of "Rendement".
- Zakelijk en direct, zoals een analist die zijn eigen geld erin zou steken.
- Geen aanprijzende taal, geen superlatieven. Een pand mag ook gewoon tegenvallen.
- Geen gedachtestreepjes.
- Maximaal 180 woorden per pand."""


def schrijf_memos(feitenblokken):
    """
    Laat het model per pand een kort memo schrijven op basis van de berekende
    feiten. Zonder sleutel of bij een fout geven we niets terug, en valt de
    brief terug op de feitelijke weergave.
    """
    if not ANTHROPIC_API_KEY or not feitenblokken:
        return {}
    lijst = "\n\n".join(
        f"PAND {i}\nFEITEN:\n" + "\n".join(f"- {r}" for r in blok)
        for i, blok in enumerate(feitenblokken))
    prompt = (f"{lijst}\n\nAntwoord met ALLEEN een JSON-array, per pand een object "
              '{"i": <index>, "memo": "<twee tot drie alinea\'s, alinea\'s gescheiden '
              'door \\n\\n>"}. Geen tekst eromheen.')
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MEMO_MODEL, "max_tokens": 4000, "system": MEMO_PROFIEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=120)
        resp.raise_for_status()
        body = resp.json()
        tekst = "".join(b.get("text", "") for b in body.get("content", [])).strip()
        if tekst.startswith("```"):
            tekst = tekst.split("```")[1]
            if tekst.startswith("json"):
                tekst = tekst[4:]
        data = json.loads(tekst.strip())
        uit = {}
        for rij in data:
            if isinstance(rij, dict) and isinstance(rij.get("i"), int):
                uit[rij["i"]] = str(rij.get("memo", "")).strip()
        print(f"Memo's geschreven voor {len(uit)} panden", file=sys.stderr)
        return uit
    except Exception as e:
        print(f"Memo's overgeslagen: {e}", file=sys.stderr)
        return {}


TOP3_KAART_URL = ("https://derksenvastgoed.github.io/"
                  "DerksenVastgoed-Vastgoedrapport-Nijmegen/top3-kaart.html")



# WWSO-teller. Ontbreekt het bestand, dan slaan we de toets gewoon over.
try:
    from wwso import wwso_bandbreedte
except Exception:  # noqa
    wwso_bandbreedte = None


def wwso_toets(huur_aanbod):
    """
    Toetst de vraaghuren van kamers aan het wettelijk maximum uit het WWSO.
    Dat maximum hangt af van gegevens die niet in een advertentie staan, zoals
    gemeenschappelijke ruimte en sanitair, dus we rekenen met een bandbreedte.
    Boven de ruime variant haalt zelfs een gunstige telling het niet meer.
    """
    if not wwso_bandbreedte:
        return []
    treffers = []
    for w in huur_aanbod:
        if (w.get("status") or "").lower() != "te huur kamer":
            continue
        opp = w.get("oppervlakte")
        if not opp or opp < 4:
            continue
        ep = w.get("energielabel") or {}
        band = wwso_bandbreedte(opp, label=ep.get("label"),
                                bouwjaar=w.get("bouwjaar"),
                                monument=bool(w.get("monument")))
        if not band:
            continue
        inclusief = (w.get("bron") or "").endswith("incl")
        treffers.append({"w": w, "band": band, "inclusief": inclusief,
                         "boven": w["prijs"] > band["hoog"]})
    return treffers


def render_wwso(huur_aanbod):
    """Blok met de toets van kamerhuren aan het puntenstelsel."""
    treffers = wwso_toets(huur_aanbod)
    if not treffers:
        return []
    boven = [t for t in treffers if t["boven"]]
    r = ["### Kamerhuren getoetst aan het puntenstelsel", ""]
    r.append(f"_Van {len(treffers)} kamers in het aanbod vragen er {len(boven)} meer dan "
             f"het WWSO toestaat, ook bij een gunstige telling._")
    r.append("")
    if boven:
        r.append("| Adres | m² | Vraaghuur | Wettelijk maximum |")
        r.append("|---|---:|---:|---:|")
        for t in sorted(boven, key=lambda x: -(x["w"]["prijs"] - x["band"]["hoog"])):
            w, b = t["w"], t["band"]
            merk = " (incl. servicekosten)" if t["inclusief"] else ""
            r.append(f"| {w['adres']} | {w.get('oppervlakte')} | "
                     f"€{w['prijs']:,}{merk} | €{b['laag']:,.0f} tot €{b['hoog']:,.0f} |"
                     .replace(",", "."))
        r.append("")
    r.append("_Onzelfstandige woonruimte valt altijd in de sociale sector en heeft dus "
             "altijd huurprijsbescherming, ongeacht de afgesproken prijs. Een huurder kan "
             "de aanvangshuurprijs binnen zes maanden laten toetsen, en de Huurcommissie "
             "stelt een te hoge huur met terugwerkende kracht bij. Bedragen inclusief "
             "servicekosten zijn niet zuiver vergelijkbaar met de kale huur waarop het "
             "stelsel toetst. Bron: Beleidsboek waarderingsstelsel onzelfstandige "
             "woonruimte, Huurcommissie, januari 2026._")
    r.append("")
    return r


def render_investeringscases(kandidaten, cbs, per_buurt, huur_bk, huur_k,
                             bm_per_buurt=None, beleggingen=None, aantal=3):
    """
    De zondagsbrief licht een paar panden uit en rekent ze door: positie in de
    markt, rendement bij de huidige rente, uitpondpotentie en het gemeentelijk
    beleid dat op dat pand van toepassing is.
    """
    r = []
    bm = bm_per_buurt or {}

    # Alleen woningen in de eigen ring, met een oordeel, scherpst eerst
    geschikt = [k for k in kandidaten
                if k[2] == "woning" and k[3] is not None
                and normaliseer_buurt(k[-1].get("buurtnaam", "")) in FOCUS_BUURTEN]
    if not geschikt:
        return r
    top = sorted(geschikt, key=lambda x: x[0])[:aantal]

    r.append("## Uitgelicht: investeringscases")
    r.append("")
    r.append(f"_De {len(top)} scherpst geprijsde woningen in de ring, beoordeeld als "
             f"exploitatieobject: wat kost het, wat brengt het op, en wat is de meest "
             f"realistische route naar meer huur of waarde. Blijft een pand staan, dan "
             f"blijft het hier staan tot het verkocht is of iets beters langskomt._")
    r.append("")

    # Eerst alle feiten per pand berekenen; het verhaal komt daarna
    feitenblokken, panden = [], []
    for rang, (afwijking, ppm2, klasse, _a, basis, w) in enumerate(top, 1):
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
        g = cbs.get(buurt) or {}
        opp, prijs = w["oppervlakte"], w["prijs"]

        def n(x):
            return f"{int(x):,}".replace(",", ".")

        f = [f"adres: {w['adres']} in {buurt}",
             f"vraagprijs: €{n(prijs)}",
             f"oppervlakte: {opp} m2",
             f"prijs per m2: €{n(ppm2)}"]
        if w.get("bouwjaar"):
            f.append(f"bouwjaar: {w['bouwjaar']}")
        lab = _labeltekst(w.get("energielabel"))
        if lab != "onbekend":
            f.append(f"energielabel: {lab}")
            letter = (w.get("energielabel") or {}).get("label") or ""
            if letter and letter[0].upper() in ("D", "E", "F", "G"):
                f.append("labelstap: het label is matig; verbetering telt mee in de "
                         "WWS-punten en verhoogt daarmee de maximaal toegestane huur")
        if w.get("monument"):
            f.append("rijksmonument: ja")

        f.append(f"positie: {afwijking:+.0f}% ten opzichte van de mediaan"
                 + ("" if basis == buurt else f" van {basis}"))
        rijen = per_buurt.get(buurt, [])
        if len(rijen) >= 10:
            prijzen = sorted(p for p, _ in rijen)
            p25 = prijzen[len(prijzen) // 4]
            p75 = prijzen[3 * len(prijzen) // 4]
            f.append(f"spreiding in {buurt}: p25 €{n(p25)}/m2, mediaan "
                     f"€{n(st.median(prijzen))}/m2, p75 €{n(p75)}/m2")
        if g.get("woz") and g.get("opp"):
            wozm2 = g["woz"] * 1000 / g["opp"]
            f.append(f"WOZ per m2 in de buurt: €{n(wozm2)}, dit pand ligt daar "
                     f"{(ppm2 - wozm2) / wozm2 * 100:+.0f}% boven of onder")

        lening = prijs * LTV / 100
        rentelast = lening * RENTE / 100
        eigen = prijs - lening
        reeks = huur_bk.get(("woning", buurt), [])
        bron_huur = f"gemeten op {len(reeks)} huuraanbiedingen in {buurt}"
        if len(reeks) < 3:
            reeks = huur_k.get("woning", [])
            bron_huur = f"gemeten op {len(reeks)} huuraanbiedingen stadsbreed"
        if len(reeks) < 3:
            huur_m2 = HUUR_M2_MND.get(buurt, 18)
            bron_huur = "AANNAME, er is nog geen huurdata verzameld"
        else:
            huur_m2 = st.median(reeks)
        jaarhuur = huur_m2 * 12 * opp
        netto = jaarhuur * (1 - OPEX_PCT / 100)
        cashflow = netto - rentelast
        f += [f"financiering: {LTV:.0f}% loan-to-value, lening €{n(lening)}, "
              f"eigen inleg €{n(eigen)}",
              f"rente: {RENTE}% aflossingsvrij, rentelast €{n(rentelast)} per jaar",
              f"huur per m2 per maand: €{huur_m2:.0f} ({bron_huur})",
              f"kale huur: €{n(jaarhuur)} per jaar, na {OPEX_PCT}% opex €{n(netto)}",
              f"cashflow: €{n(cashflow) if cashflow >= 0 else '-' + n(abs(cashflow))} per jaar",
              f"bruto aanvangsrendement: {jaarhuur / prijs * 100:.1f}%"]
        bod = richtprijs(opp, huur_m2)
        if bod:
            f.append(f"bod voor cashflow nul: €{n(bod)}, dat is "
                     f"{(bod - prijs) / prijs * 100:+.0f}% ten opzichte van de vraagprijs")

        if len(rijen) >= 10:
            voh = st.median([p for p, _ in rijen])
            marge = (voh - ppm2) * opp
            if marge > 0:
                f.append(f"uitpondruimte: €{n(marge)} tot de buurtmediaan, voor renovatie, "
                         f"overdrachtsbelasting en verkoopkosten")
            else:
                f.append("uitpondruimte: geen, de vraagprijs ligt al boven de buurtmediaan")

        signaal = verkameren_signaal(prijs)
        if signaal == "niet toegestaan":
            f.append(f"verkameren: uitgesloten, vraagprijs onder €{n(WOZ_ONDERGRENS)} en "
                     f"Nijmegen staat kamerverhuur onder die WOZ-grens niet toe")
        elif signaal == "vermoedelijk vergunningplichtig":
            f.append("verkameren: vermoedelijk vergunningplichtig, WOZ zelf niet bekend")
        else:
            f.append("verkameren: WOZ ligt vermoedelijk boven de band")
        if buurt in FOCUS_BUURTEN:
            f.append(f"{buurt} is een aangewezen wijk, omzetting is er hoe dan ook "
                     f"vergunningplichtig")
        if g.get("meergezins") is not None:
            f.append(f"aandeel appartementen in {buurt}: {g['meergezins']}%")
        if g.get("studenten") and g.get("inwoners"):
            f.append(f"studenten in {buurt}: {g['studenten']}, "
                     f"{round(g['studenten'] / g['inwoners'] * 100)}% van de inwoners")

        eigen_bm = [b for b in bm.get(buurt, [])
                    if b.get("straat", "").lower() in w["adres"].lower()
                    and b.get("huisnummer", "") in w["adres"]]
        for b in eigen_bm:
            f.append(f"bekendmaking op dit adres: {b.get('datum','')} {b.get('titel','')}")

        feitenblokken.append(f)
        panden.append((rang, w, buurt, f))

    memos = schrijf_memos(feitenblokken)

    for i, (rang, w, buurt, f) in enumerate(panden):
        r.append(f"### {rang}. {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))}"
                 f", {buurt}")
        r.append("")
        if memos.get(i):
            for alinea in memos[i].split("\n\n"):
                if alinea.strip():
                    r.append(alinea.strip())
                    r.append("")
        else:
            # Zonder memo terugvallen op de kale feiten
            for regel in f:
                r.append(f"- {regel}")
            r.append("")
        kern = [x for x in f if x.startswith(("vraagprijs", "oppervlakte", "prijs per m2",
                                              "energielabel", "bouwjaar"))]
        voet = ("_" + " . ".join(x.split(": ", 1)[1] for x in kern)
                + f". [Bekijk op straatniveau]"
                  f"({streetview_link(w['adres'], w.get('plaats', 'Nijmegen'))})")
        dga = bouwarchief_link(w)
        if dga:
            voet += f" . [Bouwtekeningen opvragen]({dga})"
        r.append(voet + "_")
        r.append("")

    # Kaart met de drie panden, en de uitpondmarge als context
    if schrijf_top3_kaart([k[-1] for k in top]):
        r.append(f"[Bekijk de drie panden op de kaart]({TOP3_KAART_URL})")
        r.append("")

    if beleggingen and len(beleggingen) >= 3:
        bel = sorted(p for p, _ in beleggingen)
        voh = []
        for buurt in {normaliseer_buurt(w.get("buurtnaam", "")) for _, w in beleggingen}:
            voh.extend(p for p, _ in per_buurt.get(buurt, []))
        if len(voh) >= 5:
            bel_med, voh_med = st.median(bel), st.median(voh)
            marge = voh_med - bel_med
            if marge > 0:
                r.append(f"_Ter vergelijking: beleggingspanden in verhuurde staat gaan in "
                         f"dezelfde buurten voor mediaan €{int(bel_med):,}/m², tegen "
                         f"€{int(voh_med):,}/m² vrij van huurder. Dat verschil van "
                         f"€{int(marge):,}/m² is de ruimte die uitponden oplevert, "
                         f"gerekend op {len(beleggingen)} beleggingen en {len(voh)} "
                         f"verkopen._".replace(",", "."))
                r.append("")

    # Beleidsonderdeel van de week
    titel, tekst = _beleid_van_de_week()
    r.append(f"### Beleid uitgelicht: {titel.lower()}")
    r.append("")
    r.append(tekst)
    r.append("")
    r.append("_Uit de Huisvestingsverordening Nijmegen. Controleer de actuele versie "
             "voordat je erop handelt; de verordening wordt periodiek herzien en "
             "bedragen worden geïndexeerd._")
    r.append("")
    return r


def render_nieuw_aanbod(woningen, per_buurt, stad_breed, bm_per_buurt=None,
                        bm_overig=None, kort=False):
    """
    Al het aanbod in een overzicht, elk pand afgezet tegen de mediaan van zijn
    EIGEN assetklasse. Een winkelpand vergelijken met woningen levert een
    percentage op dat er scherp uitziet maar niets betekent.
    """
    r = []
    MINIMUM = 8  # onder dit aantal is een mediaan te wankel om tegen af te zetten

    # Medianen per klasse, en binnen een klasse per buurt
    per_klasse, per_klasse_buurt = defaultdict(list), defaultdict(list)
    for w in woningen:
        opp = w.get("oppervlakte")
        if not opp or opp < 15:
            continue
        try:
            ppm2 = w["prijs"] / opp
        except (TypeError, ZeroDivisionError):
            continue
        klasse = assetklasse(w)
        if klasse == "onbekend":
            continue
        per_klasse[klasse].append(ppm2)
        buurt = normaliseer_buurt(w.get("buurtnaam", ""))
        if buurt:
            per_klasse_buurt[(klasse, buurt)].append(ppm2)

    kandidaten = []
    for w in woningen:
        if w.get("status", "").lower() not in ("te koop", "nieuw", "onder bod", "belegging"):
            continue
        opp = w.get("oppervlakte")
        if not opp or opp < 15:
            continue
        ppm2 = w["prijs"] / opp
        klasse = assetklasse(w)
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"

        # Eerst de eigen klasse in de eigen buurt, dan de eigen klasse stadsbreed
        reeks = per_klasse_buurt.get((klasse, buurt), [])
        basis = buurt
        if len(reeks) < MINIMUM:
            reeks = per_klasse.get(klasse, [])
            basis = "heel Nijmegen"
        if len(reeks) < MINIMUM:
            kandidaten.append((999, ppm2, klasse, None, None, w))
            continue

        mediaan = st.median(reeks)
        afwijking = (ppm2 - mediaan) / mediaan * 100
        kandidaten.append((afwijking, ppm2, klasse, afwijking, basis, w))

    if not kandidaten:
        return r, []

    cbs = lees_cbs()
    opp_bag = gemiddelde_oppervlakte_per_buurt(woningen)
    huur_bk, huur_k = gemeten_huren(
        [w for w in woningen if (w.get("status") or "").lower().startswith("te huur")])
    # Noemer voor het studentenaandeel: alle studenten in de focus-buurten samen
    studenten_ring = sum((cbs.get(b) or {}).get("studenten") or 0 for b in FOCUS_BUURTEN)

    # Per buurt groeperen. Buurten zonder aanbod komen niet voor.
    per_buurt_aanbod = defaultdict(list)
    for kandidaat in kandidaten:
        w = kandidaat[-1]
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "Overig"
        per_buurt_aanbod[buurt].append(kandidaat)

    bm = bm_per_buurt or {}

    # Alle buurten waar iets speelt: aanbod, een bekendmaking, of allebei
    alle_buurten = set(per_buurt_aanbod) | set(bm)

    # Doordeweeks alleen de eigen ring. Buurten daarbuiten zijn nuttig als
    # referentie, maar niet als dagelijkse leesstof.
    buiten_ring = 0
    if kort:
        buiten = [b for b in alle_buurten if b not in FOCUS_BUURTEN]
        buiten_ring = sum(len(per_buurt_aanbod.get(b, [])) for b in buiten)
        alle_buurten = {b for b in alle_buurten if b in FOCUS_BUURTEN}
        if not alle_buurten:
            return [], kandidaten

    def sorteer(buurt):
        rijen_buurt = per_buurt_aanbod.get(buurt, [])
        return min((k[0] for k in rijen_buurt), default=500)

    volgorde = [(b, per_buurt_aanbod.get(b, [])) for b in sorted(alle_buurten, key=sorteer)]

    r.append("### Per gebied: aanbod en gemeentelijke berichten")
    r.append("")

    # De dagenkolom alleen tonen als er ergens een datum bekend is
    toon_dagen = any(_dagen_sinds(k[-1].get("datum_eerst") or k[-1].get("datum")) is not None
                     for rijen_buurt in per_buurt_aanbod.values() for k in rijen_buurt)

    for buurt, rijen_buurt in volgorde:
        r.append(f"**{buurt}**")
        kenmerken = buurtregel(buurt, cbs, opp_bag.get(buurt), studenten_ring)
        if kenmerken:
            r.append(f"_{kenmerken}_")
        r.append("")

        # Panden zonder vergelijkingsmateriaal apart houden: vijf keer dezelfde
        # mededeling in een tabel leest slecht.
        beoordeeld = [k for k in rijen_buurt if k[3] is not None]
        onbeoordeeld = [k for k in rijen_buurt if k[3] is None]

        if beoordeeld:
            kop = ("| Adres | Klasse | Prijs | m² | €/m² | Tegen mediaan | "
                   "Richtprijs | Ruimte | Label |")
            streep = "|---|---|---:|---:|---:|---:|---:|---:|---|"
            if toon_dagen:
                kop += " Dagen |"
                streep += "---:|"
            r.append(kop)
            r.append(streep)
            for _, ppm2, klasse, afwijking, basis, w in sorted(beoordeeld, key=lambda x: x[0]):
                prijs_s = f"{w['prijs']:,}".replace(",", ".")
                ppm2_s = f"{int(ppm2):,}".replace(",", ".")
                merk = "🟢" if afwijking <= -10 else ("🟡" if afwijking < 10 else "🔴")
                staart = "" if basis == buurt else f" ({basis})"
                huur_m2, _ = huur_voor_buurt(buurt, huur_bk, huur_k, w['oppervlakte'])
                plafond = richtprijs(w["oppervlakte"], huur_m2)
                if plafond:
                    verschil = (plafond - w["prijs"]) / w["prijs"] * 100
                    plafond_s = "€" + f"{int(plafond):,}".replace(",", ".")
                    ruimte_s = f"{verschil:+.0f}%"
                else:
                    plafond_s = ruimte_s = "—"
                regel = (f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} | "
                         f"{klasse} | €{prijs_s} | {w['oppervlakte']} | €{ppm2_s} | "
                         f"{merk} {afwijking:+.0f}%{staart} | {plafond_s} | {ruimte_s} | "
                         f"{_labeltekst(w.get('energielabel'))} |")
                if toon_dagen:
                    dagen = _dagen_sinds(w.get("datum_eerst") or w.get("datum"))
                    regel += f" {dagen if dagen is not None else '—'} |"
                r.append(regel)
            r.append("")

        if onbeoordeeld:
            stukken = []
            for _, ppm2, klasse, _a, _b, w in sorted(onbeoordeeld, key=lambda x: x[1]):
                prijs_s = f"{w['prijs']:,}".replace(",", ".")
                ppm2_s = f"{int(ppm2):,}".replace(",", ".")
                stukken.append(f"{kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} "
                               f"€{prijs_s} ({w['oppervlakte']} m², €{ppm2_s}/m²)")
            r.append(f"_Zonder vergelijking, te weinig {onbeoordeeld[0][2]} objecten in de "
                     f"dataset: " + " . ".join(stukken) + "._")
            r.append("")

        # Verkameren: welke panden vallen buiten de Nijmeegse WOZ-band
        woningen_hier = [k[-1] for k in rijen_buurt if k[2] == "woning"]
        if woningen_hier:
            uitgesloten = [w for w in woningen_hier
                           if verkameren_signaal(w["prijs"]) == "niet toegestaan"]
            if uitgesloten:
                namen = ", ".join(w["adres"] for w in uitgesloten)
                r.append(f"_Verkameren valt af bij {namen}: de vraagprijs ligt onder "
                         f"€{WOZ_ONDERGRENS:,}".replace(",", ".")
                         + ", en onder die WOZ-grens staat Nijmegen kamerverhuur niet toe. "
                           "Als gewone verhuur kunnen deze panden wel uitkomen; kijk "
                           "daarvoor naar de kolom Richtprijs._")
                r.append("")

        if bm.get(buurt):
            r.extend(bekendmakingregels(bm[buurt]))
            r.append("")

    if kort and buiten_ring:
        r.append(f"_{buiten_ring} panden staan in buurten buiten de ring. Die staan in de "
                 f"uitgebreide brief van zondag._")
        r.append(f"_**Richtprijs** is de hoogste koopsom waarbij de nettohuur de rentelast "
                 f"nog dekt. **Ruimte** is het verschil met de vraagprijs: positief betekent "
                 f"dat er speling zit, negatief dat er zoveel af zou moeten voordat het pand "
                 f"zichzelf rondhoudt. Gerekend met {LTV:.0f}% financiering, {RENTE}% rente "
                 f"aflossingsvrij, {OPEX_PCT}% opex en een gewenste cashflow van "
                 f"€{DOEL_CASHFLOW:,}".replace(",", ".")
                 + ". Aankoopkosten van "
                 f"{AANKOOPKOSTEN_PCT}% zitten niet in de richtprijs maar wel in je eigen "
                 f"inleg. Renovatie om die huur te halen en de vraag of het puntenstelsel "
                 f"die huur toestaat zitten er evenmin in; beide verlagen dit plafond._")
        r.append("")
    if not kort:
        # De spelregels horen in de weekbrief, niet elke ochtend opnieuw
        r.append("_Elk pand is afgezet tegen de mediaan van zijn eigen assetklasse, want een "
                 "winkelpand en een woning zijn verschillende producten. Lukt dat niet in de "
                 "eigen buurt, dan tegen heel Nijmegen; staan er ook stadsbreed te weinig "
                 f"vergelijkbare objecten (minder dan {MINIMUM}), dan volgt er geen oordeel. "
                 "Groen is meer dan 10% onder de mediaan van de eigen klasse, rood meer dan "
                 "10% erboven. Buurtkenmerken komen uit de CBS Wijk- en Buurtkaart._")
        tellen = ", ".join(f"{k}: {len(v)}" for k, v in sorted(per_klasse.items()))
        r.append(f"_Omvang per klasse in de dataset: {tellen}._")
        r.append(f"_Kamerverhuur in Nijmegen: onder een WOZ van "
                 f"€{WOZ_ONDERGRENS:,} niet toegestaan, tussen €{WOZ_ONDERGRENS:,} en "
                 f"€{WOZ_BOVENGRENS:,} een omzettingsvergunning nodig bij drie kamers of "
                 f"meer, en vanaf vijf kamers ook een melding brandveilig gebruik. "
                 f"Corporatiebezit is vrijgesteld. Wij toetsen op de vraagprijs, want de "
                 f"WOZ per pand is niet vrij op te vragen; controleer die zelf op "
                 f"wozwaardeloket.nl. Bedragen worden jaarlijks geïndexeerd._".replace(",", "."))
        r.append("")
    return r, kandidaten


KAART_URL = ("https://derksenvastgoed.github.io/"
             "DerksenVastgoed-Vastgoedrapport-Nijmegen/kaart-eigendom-ring.html")


def render_intro(cbs, woningen, kort=False):
    """
    De opening als lopende tekst in plaats van een tabel: eerst de stad,
    dan de ring, dan wat er vandaag speelt. Cijfers horen in een zin,
    niet in een raster dat je moet ontcijferen.
    """
    def n(x):
        return f"{x:,}".replace(",", ".")

    stad = cbs.get("_nijmegen") or {}
    ring = {"won": 0, "niet": 0, "inw": 0, "stud": 0}
    for buurt in FOCUS_BUURTEN:
        g = cbs.get(buurt) or {}
        ring["won"] += g.get("won") or 0
        ring["niet"] += g.get("nietwoningen") or 0
        ring["inw"] += g.get("inwoners") or 0
        ring["stud"] += g.get("studenten") or 0

    in_aanbod = sum(1 for w in woningen
                    if (w.get("status") or "").lower() in
                    ("te koop", "nieuw", "onder bod", "belegging"))
    vandaag = dt.date.today().strftime("%d %B %Y")
    maanden = {"January": "januari", "February": "februari", "March": "maart",
               "April": "april", "May": "mei", "June": "juni", "July": "juli",
               "August": "augustus", "September": "september", "October": "oktober",
               "November": "november", "December": "december"}
    for en, nl in maanden.items():
        vandaag = vandaag.replace(en, nl)

    zinnen = []
    if stad.get("woningen") and ring["won"]:
        aandeel = round(ring["won"] / stad["woningen"] * 100)
        zin = (f"Nijmegen telt {n(stad['woningen'])} woningen")
        if stad.get("inwoners"):
            zin += f" en {n(stad['inwoners'])} inwoners"
        zin += (f". De ring rond het Keizer Karelplein is daarvan {aandeel}%: "
                f"{n(ring['won'])} woningen")
        if ring["niet"]:
            zin += f", {n(ring['niet'])} winkels en kantoren"
        if ring["inw"]:
            zin += f" en {n(ring['inw'])} inwoners"
        zin += "."
        zinnen.append(zin)

    if stad.get("studenten") and ring["stud"] and ring["inw"] and stad.get("inwoners"):
        aandeel_stud = round(ring["stud"] / stad["studenten"] * 100)
        ring_pct = round(ring["stud"] / ring["inw"] * 100)
        stad_pct = round(stad["studenten"] / stad["inwoners"] * 100)
        zinnen.append(
            f"Studenten wegen er zwaarder dan in de rest van de stad: {aandeel_stud}% "
            f"van de {n(stad['studenten'])} Nijmeegse studenten woont in de ring, waar "
            f"{ring_pct}% van de inwoners student is tegen {stad_pct}% stadsbreed "
            f"(CBS telt studenten op hun woonadres).")

    slot = f"Vandaag staan er **{in_aanbod} panden in aanbod**"
    if len(woningen) > in_aanbod:
        slot += f", afgezet tegen {n(len(woningen))} gevolgde panden"
    slot += f". Bijgewerkt {vandaag}. [Bekijk de eigendomskaart]({KAART_URL})."
    zinnen.append(slot)

    return ["", " ".join(zinnen), ""]


def render(woningen, modus="weekelijks", bm_per_buurt=None, bm_overig=None):
    """
    In de dagelijkse brief tonen we alleen wat beweegt: prijswijzigingen,
    looptijd en het actuele aanbod met zijn positie ten opzichte van de markt.
    De referentietabellen horen in de weekbrief, want die veranderen nauwelijks.
    """
    kort = (modus == "dagelijks")
    vandaag = dt.date.today().strftime("%d-%m-%Y")

    # Bekendmakingen-signalen en monumentenstatus per pand opzoeken
    archief = lees_archief()
    monumenten = lees_monumenten()
    if archief or monumenten:
        for w in woningen:
            varianten = split_huisnummer(w["adres"])
            if not varianten:
                continue
            straat, huisnr = varianten[0][0], varianten[0][1]
            k = archief_sleutel(straat, huisnr)
            if archief:
                treffers = archief.get(k, [])
                if treffers:
                    w["signalen"] = treffers
            if monumenten:
                mon = monumenten.get(k, [])
                if mon:
                    w["monument"] = mon[0]

    r = render_intro(lees_cbs(), woningen, kort=kort)

    # Bewegingen: het enige dat sinds gisteren veranderd kan zijn
    r.extend(render_prijswijzigingen(woningen))
    r.extend(render_looptijd(woningen))

    per_buurt = defaultdict(list)
    beleggingen = []
    huur_aanbod = []
    stad_breed = []      # alle woningen met bruikbare data, ook buiten de focus-buurten
    buiten_focus = 0
    geen_woonfunctie = 0
    belegging_buiten_ring = 0

    # Gebruiksdoelen die nooit een woonbelegging zijn: garageboxen, opslag, bedrijfshallen.
    NOOIT_BELEGGING = ["industrie", "overige gebruiksfunctie", "sport",
                       "onderwijs", "gezondheidszorg", "cel"]

    for w in woningen:
        buurt = normaliseer_buurt(w.get("buurtnaam", ""))
        opp = w.get("oppervlakte")
        if not opp or opp < 15:
            continue

        doelen = [str(d).lower() for d in (w.get("gebruiksdoelen") or [])]
        heeft_woonfunctie = any("woon" in d for d in doelen)

        try:
            ppm2 = w["prijs"] / opp
        except (TypeError, ZeroDivisionError):
            continue

        # Huuraanbod telt niet mee in de koopprijs-statistiek
        if w.get("status", "").lower().startswith("te huur"):
            huur_aanbod.append(w)
            continue

        if w.get("status", "").lower() == "belegging":
            # Ruimer filter: gemengde panden (winkel of kantoor met woningen erboven)
            # zijn juist interessant, dus die blijven staan. Alleen duidelijk
            # niet-woongerelateerde objecten vallen af.
            if doelen and not heeft_woonfunctie and any(
                    any(n in d for n in NOOIT_BELEGGING) for d in doelen):
                geen_woonfunctie += 1
                continue
            if buurt in FOCUS_BUURTEN:
                beleggingen.append((ppm2, w))
            else:
                belegging_buiten_ring += 1
            continue

        # Voor de prijsindex wel streng: alleen woningen, anders vervuilt de €/m².
        if doelen and not heeft_woonfunctie:
            geen_woonfunctie += 1
            continue

        stad_breed.append(ppm2)
        if not buurt or buurt not in FOCUS_BUURTEN:
            buiten_focus += 1
            continue
        per_buurt[buurt].append((ppm2, w))

    if not per_buurt and not beleggingen:
        r.append("_Geen woningen met bruikbare data._")
        return "\n".join(r)

    # Doordeweeks de volledige lijst per buurt, zondag uitgewerkte cases
    aanbod_regels, kandidaten = render_nieuw_aanbod(
        woningen, per_buurt, stad_breed, bm_per_buurt, bm_overig, kort=kort)
    if kort:
        r.extend(aanbod_regels)

    if kort:
        # Dagelijks houdt het hier op. De referentietabellen, yield, uitpond-marge
        # en beleggingstabel staan in de zondagsbrief.
        if len(r) <= 4:
            return ""  # niets bewogen en geen aanbod: blok helemaal weglaten
        r.append("_Referentietabellen, rendement en de beleggingslijst staan in de "
                 "uitgebreide brief van zondag._")
        r.append("")
        return "\n".join(r)

    # Zondag: uitgewerkte investeringscases, en verder niets. De referentie-
    # tabellen zaten hier eerder onder, maar die informatie zit nu in de cases.
    huur_bk, huur_k = gemeten_huren(huur_aanbod)
    r.extend(render_investeringscases(kandidaten, lees_cbs(), per_buurt,
                                      huur_bk, huur_k, bm_per_buurt, beleggingen=beleggingen))
    r.extend(render_wwso(huur_aanbod))
    return "\n".join(r)

    r.append("### Referentie: prijspeil per buurt")
    r.append("")
    r.append("| Buurt | N | p10 €/m² | p25 | mediaan | p75 | p90 |")
    r.append("|---|---:|---:|---:|---:|---:|---:|")
    for buurt in FOCUS_BUURTEN:
        rijen = per_buurt.get(buurt, [])
        if not rijen:
            r.append(f"| {buurt} | 0 | — | — | — | — | — |")
            continue
        prijzen = sorted(p for p, _ in rijen)
        n = len(prijzen)
        if n < 10:
            # Te weinig waarnemingen voor percentielen; alleen de mediaan zegt nog iets.
            r.append(f"| {buurt} | {n} | — | — | €{int(st.median(prijzen)):,} | — | — |".replace(",", "."))
            continue
        p10 = prijzen[int(n * 0.10)]
        p25 = prijzen[n // 4]
        p75 = prijzen[3 * n // 4]
        p90 = prijzen[min(n - 1, int(n * 0.90))]
        r.append(f"| {buurt} | {n} | "
                 f"€{int(p10):,} | €{int(p25):,} | "
                 f"€{int(st.median(prijzen)):,} | €{int(p75):,} | €{int(p90):,} |".replace(",", "."))

    # Referentieregel: heel Nijmegen, zodat je ziet of de ring boven of onder de stad zit
    if len(stad_breed) >= 10:
        sb = sorted(stad_breed)
        n = len(sb)
        r.append(f"| _Nijmegen totaal_ | {n} | "
                 f"€{int(sb[int(n*0.10)]):,} | €{int(sb[n//4]):,} | "
                 f"€{int(st.median(sb)):,} | €{int(sb[3*n//4]):,} | "
                 f"€{int(sb[min(n-1,int(n*0.90))]):,} |".replace(",", "."))
    r.append("")
    toelichting = ["p10 en p90 in plaats van uitersten, want één verkeerd gekoppeld "
                   "adres verpest een minimum. Onder tien waarnemingen alleen de mediaan"]
    if buiten_focus:
        toelichting.append(f"{buiten_focus} panden buiten de focus-buurten, alleen in de totaalregel")
    if geen_woonfunctie:
        toelichting.append(f"{geen_woonfunctie} objecten zonder woonfunctie weggelaten")
    toelichting.append("prijzen zijn vrij van huurder; verhuurde staat ligt lager")
    r.append("_" + ". ".join(toelichting) + "._")
    r.append("")

    # Yield-analyse: wat betekent deze €/m² voor een investeerder tegen huidige rente
    # Referentie-huren op basis van Krayenhofflaan-cluster (Biezen €19-22/m²) en Pararius Q2 2026

    r.append("### Yield en cashflow bij aankoop vrij van huurder")
    aantal_gemeten = sum(len(v) for v in huur_k.values())
    if aantal_gemeten:
        r.append(f"_Huur per m² is waar mogelijk **gemeten** uit {aantal_gemeten} "
                 f"huuraanbiedingen; waar die ontbreken staat een aanname. "
                 f"Gerekend met rente {RENTE}% aflossingsvrij, LTV {LTV:.0f}% en {OPEX_PCT}% opex._")
    else:
        r.append(f"_De mediaan €/m² is gemeten. De huur per m² is nog een **aanname**, "
                 f"want er zijn nog geen huuraanbiedingen verzameld. "
                 f"Gerekend met rente {RENTE}% aflossingsvrij, LTV {LTV:.0f}% en {OPEX_PCT}% opex._")
    r.append("")
    r.append("| Buurt | mediaan €/m² | huur/m²/mnd | bron huur | bruto yield | netto cashflow op €1M lening |")
    r.append("|---|---:|---:|---|---:|---:|")
    for buurt in FOCUS_BUURTEN:
        rijen = per_buurt.get(buurt, [])
        if not rijen or buurt not in HUUR_M2_MND:
            r.append(f"| {buurt} | — | — | — | — | — |")
            continue
        if len(rijen) < 10:
            r.append(f"| {buurt} | te weinig data (N={len(rijen)}) | — | — | — | — |")
            continue
        prijzen = sorted(p for p, _ in rijen)
        med_m2 = st.median(prijzen)

        # Eerst de eigen buurt, dan stadsbreed, dan pas de aanname
        reeks = huur_bk.get(("woning", buurt), [])
        bron = f"gemeten (N={len(reeks)})"
        if len(reeks) < 3:
            reeks = huur_k.get("woning", [])
            bron = f"stad (N={len(reeks)})"
        if len(reeks) < 3:
            huur_m2 = HUUR_M2_MND[buurt]
            bron = "aanname"
        else:
            huur_m2 = st.median(reeks)

        huur_m2_jaar = huur_m2 * 12
        bruto_yield = huur_m2_jaar / med_m2 * 100
        waarde = 1_000_000 / (LTV / 100)
        m2_pand = waarde / med_m2
        kale_huur = m2_pand * huur_m2_jaar
        netto_huur = kale_huur * (1 - OPEX_PCT / 100)
        rentelast = 1_000_000 * RENTE / 100
        cashflow = netto_huur - rentelast
        teken = "🔴" if cashflow < 0 else "🟢"
        r.append(f"| {buurt} | €{int(med_m2):,} | €{huur_m2:.0f} | {bron} | "
                 f"{bruto_yield:.1f}% | {teken} €{int(cashflow):,}/jaar |".replace(",", "."))
    r.append("")

    # Huurniveaus per assetklasse, zodra er iets gemeten is
    if huur_k:
        regels_klasse = []
        for klasse, waarden in sorted(huur_k.items()):
            if len(waarden) < 3:
                continue
            regels_klasse.append(f"{klasse}: €{st.median(waarden):.0f}/m²/mnd (N={len(waarden)})")
        if regels_klasse:
            r.append("**Gemeten huurniveaus per klasse:** " + " . ".join(regels_klasse))
            r.append("_Commerciële huur wordt vaak per m² per jaar geadverteerd; die is "
                     "hier door twaalf gedeeld. Kamers staan apart, want onzelfstandige "
                     "eenheden brengen per m² meer op en zouden de huur voor gewone "
                     "woningen anders scheeftrekken._")
            r.append("")

    # Waardecreatie: uitpond-marge concreet maken
    r.append("### Waardecreatie via uitponden")
    r.append("")
    if len(beleggingen) >= 3 and per_buurt:
        bel_prijzen = sorted(p for p, _ in beleggingen)
        bel_med = st.median(bel_prijzen)
        # Vrij van huurder: mediaan over dezelfde buurten waar beleggingen in staan
        bel_buurten = {normaliseer_buurt(w.get("buurtnaam", "")) for _, w in beleggingen}
        voh = [p for b in bel_buurten for p, _ in per_buurt.get(b, [])]
        if len(voh) >= 5:
            voh_med = st.median(voh)
            marge = voh_med - bel_med
            pct = marge / voh_med * 100 if voh_med else 0
            r.append(f"Berekend op de {len(beleggingen)} beleggingsobjecten en {len(voh)} "
                     f"verkopen vrij van huurder in dezelfde buurten:")
            r.append("")
            r.append("- Mediaan in **verhuurde staat**: €"
                     + f"{int(bel_med):,}".replace(",", ".") + "/m²")
            r.append("- Mediaan **vrij van huurder**: €"
                     + f"{int(voh_med):,}".replace(",", ".") + "/m²")
            if marge > 0:
                marge_s = f"{int(marge):,}".replace(",", ".")
                totaal_s = f"{int(marge*100):,}".replace(",", ".")
                r.append(f"- **Verschil: €{marge_s}/m², oftewel {pct:.0f}%**. "
                         f"Op 100 m² is dat €{totaal_s} bruto.")
            else:
                marge_s = f"{int(abs(marge)):,}".replace(",", ".")
                r.append(f"- **Verschil: geen korting zichtbaar.** De beleggingen liggen "
                         f"€{marge_s}/m² hóger dan de verkopen vrij van huurder. "
                         f"Dat komt bij zo'n kleine steekproef voor, bijvoorbeeld door "
                         f"gemengde panden met een commerciële plint.")
            r.append("")
            r.append(f"_Let op de steekproefgrootte: {len(beleggingen)} beleggingen is weinig. "
                     f"Dit cijfer beweegt sterk zolang die lijst kort is. "
                     f"Het is een richting, geen taxatie._")
        else:
            r.append("_Te weinig verkopen vrij van huurder in dezelfde buurten om een "
                     "betrouwbaar verschil te berekenen._")
    else:
        r.append(f"_Nog te weinig beleggingsobjecten in de lijst ({len(beleggingen)}) om het "
                 f"verschil tussen verhuurde staat en vrij van huurder te berekenen. "
                 f"Vanaf drie objecten verschijnt hier een cijfer op basis van de eigen data._")
    r.append("")
    r.append("De kern blijft: bij de huidige rente komt het rendement in dit segment niet uit "
             "de lopende cashflow, maar uit het verschil tussen aankoop in verhuurde staat en "
             "verkoop vrij van huurder na mutatie, renovatie of splitsing.")
    r.append("")

    # Beleggings-tabel (in verhuurde staat)
    if beleggingen:
        r.append("### Beleggingsobjecten in de ring (in verhuurde staat)")
        r.append("_Bron: Funda Business. Garageboxen en bedrijfsunits zijn eruit gefilterd. "
                 "Gemengde panden (winkel of kantoor met woningen erboven) staan er bewust wel in; "
                 "de kolom Functie toont wat de BAG registreert._")
        r.append("")
        # Kolommen alleen tonen als er daadwerkelijk data is
        toon_bouwjaar = any(w.get("bouwjaar") for _, w in beleggingen)
        toon_monument = any(w.get("monument") for _, w in beleggingen)
        toon_label = any(w.get("energielabel") for _, w in beleggingen)
        kop = "| Adres | Buurt | Prijs | m² | €/m² |"
        streep = "|---|---|---:|---:|---:|"
        if toon_bouwjaar:
            kop += " Bouwjaar |"
            streep += "---:|"
        if toon_label:
            kop += " Label |"
            streep += "---|"
        if toon_monument:
            kop += " Monument |"
            streep += "---|"
        kop += " Functie | Bekendmakingen |"
        streep += "---|---|"
        r.append(kop)
        r.append(streep)
        for ppm2, w in sorted(beleggingen, key=lambda x: x[1]["prijs"]):
            buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
            doelen = [str(d).replace("functie", "") for d in (w.get("gebruiksdoelen") or [])]
            functie = ", ".join(doelen) if doelen else "?"
            sig = w.get("signalen") or []
            soorten = sorted({s for t in sig for s in t.get("soorten", [])})
            sigtekst = ", ".join(soorten) if soorten else "geen treffer"
            prijs_s = f"{w['prijs']:,}".replace(",", ".")
            ppm2_s = f"{int(ppm2):,}".replace(",", ".")
            regel = (f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} | {buurt} | "
                     f"€{prijs_s} | {w.get('oppervlakte','?')} | €{ppm2_s} |")
            if toon_bouwjaar:
                regel += f" {w.get('bouwjaar') or '?'} |"
            if toon_label:
                regel += f" {_labeltekst(w.get('energielabel'))} |"
            if toon_monument:
                mon = w.get("monument")
                regel += f" {'rijksmonument' if mon else 'nee'} |"
            regel += f" {functie} | {sigtekst} |"
            r.append(regel)
        r.append("")
        if belegging_buiten_ring:
            r.append(f"_{belegging_buiten_ring} beleggingsobjecten lagen buiten de ring en zijn niet getoond._")
        r.append("_Deze panden worden in verhuurde staat aangeboden. Het verschil met de "
                 "mediaan vrij van huurder staat hierboven, berekend op deze lijst._")
        if toon_label:
            r.append("_Label met registratiejaar tussen haakjes. Een label is tien jaar "
                     "geldig vanaf de opnamedatum, dus bij een oud jaartal loopt het af. "
                     "'Afgeschermd' betekent dat de eigenaar het label niet openbaar heeft "
                     "staan, niet dat het ontbreekt. Bron: EP-Online, RVO._")
        r.append("")

    # Panden waar ooit iets over gepubliceerd is
    met_signaal = [w for w in woningen if w.get("signalen")]
    if met_signaal:
        r.append("### Panden met een bekendmaking in het archief")
        r.append("")
        for w in sorted(met_signaal, key=lambda x: x["adres"]):
            buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
            r.append(f"- **{w['adres']}** ({buurt}) . {w['status']}")
            for t in w["signalen"][:3]:
                soorten = ", ".join(t.get("soorten", []))
                link = f" ([bron]({t['url']}))" if t.get("url") else ""
                r.append(f"  `{t.get('datum','?')}` {soorten}: {t.get('titel','')}{link}")
            if len(w["signalen"]) > 3:
                r.append(f"  _en nog {len(w['signalen']) - 3} eerdere publicaties_")
            r.append("")
        r.append("_**Wat dit wel en niet zegt.** Een treffer betekent dat de gemeente ooit "
                 "iets over dit adres publiceerde, niet dat er een geldige vergunning ligt: "
                 "een aanvraag kan geweigerd of ingetrokken zijn. Geen treffer betekent "
                 "evenmin dat er niets is, want het archief gaat maar enkele jaren terug. "
                 "Gebruik dit als aanleiding om na te vragen, niet als bewijs._")
        r.append("")

    # Rijksmonumenten in de lijst
    monument_hits = [w for w in woningen if w.get("monument")]
    if monument_hits:
        r.append("### Rijksmonumenten in de lijst")
        r.append("")
        for w in sorted(monument_hits, key=lambda x: x["adres"]):
            buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
            mon = w["monument"]
            extra = []
            if mon.get("nummer"):
                extra.append(f"monumentnr {mon['nummer']}")
            if mon.get("functie"):
                extra.append(f"oorspronkelijk {mon['functie'].lower()}")
            staart = f" ({', '.join(extra)})" if extra else ""
            r.append(f"- **{w['adres']}** ({buurt}) . {w['status']}{staart}")
        r.append("")
        r.append("_Wat dit betekent voor de rekensom: een rijksmonument kent geen "
                 "energielabelplicht en dus geen label-eis bij verhuur, maar wel "
                 "vergunningplicht voor ingrepen aan het monument, wat verbouwen en "
                 "splitsen trager en duurder maakt. Daartegenover staan eigen subsidie- "
                 "en financieringsroutes voor onderhoud en restauratie. "
                 "Bron: Rijksdienst voor het Cultureel Erfgoed._")
        r.append("")
    elif monumenten:
        r.append("_Geen rijksmonumenten in deze lijst. Let op: gemeentelijke monumenten en "
                 "panden binnen een beschermd stadsgezicht staan hier niet bij, want die "
                 "zitten niet in het landelijke register. "
                 "Bron: Rijksdienst voor het Cultureel Erfgoed._")
        r.append("")

    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="marktprijzen_digest.md")
    ap.add_argument("--input", default=INPUT_PAD)
    ap.add_argument("--modus", choices=["dagelijks", "weekelijks"], default="weekelijks",
                    help="dagelijks toont alleen wat beweegt, weekelijks het volledige beeld")
    ap.add_argument("--debug", action="store_true",
                    help="toon de velden die de BAG teruggeeft, voor het eerste adres")
    args = ap.parse_args()

    global DEBUG
    DEBUG = args.debug

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

    # Waarnemingen groeperen per BAG-object. Hetzelfde pand kan meerdere keren
    # in verkopen.txt staan: nieuwe attendering, prijsverlaging, status gewijzigd.
    # We houden de volledige reeks bij, want daaruit volgt de prijshistorie.
    per_object, volgorde = {}, []
    for w in woningen:
        obj = w.get("adresseerbaarObjectIdentificatie")
        sleutel = obj if obj else re.sub(r"[^a-z0-9]", "", w["adres"].lower())
        if sleutel not in per_object:
            volgorde.append(sleutel)
            per_object[sleutel] = []
        per_object[sleutel].append(w)

    ontdubbeld = []
    for sleutel in volgorde:
        reeks = per_object[sleutel]
        # Op datum sorteren waar die bekend is, anders op volgorde in het bestand
        reeks.sort(key=lambda x: (x.get("datum") or "", x.get("regelnr", 0)))
        laatste = reeks[-1]
        if len(reeks) > 1:
            eerste = reeks[0]
            laatste["historie"] = [
                {"datum": r.get("datum", ""), "prijs": r["prijs"], "status": r["status"]}
                for r in reeks
            ]
            laatste["prijs_eerst"] = eerste["prijs"]
            laatste["datum_eerst"] = eerste.get("datum", "")
            laatste["waarnemingen"] = len(reeks)
        ontdubbeld.append(laatste)

    weg = len(woningen) - len(ontdubbeld)
    if weg:
        print(f"Samengevoegd: {weg} herhaalde waarnemingen, {len(ontdubbeld)} panden over",
              file=sys.stderr)
    woningen = ontdubbeld

    bm_per_buurt, bm_overig = lees_bekendmakingen(cache)
    schrijf_cache(cache)
    md = render(woningen, modus=args.modus,
                bm_per_buurt=bm_per_buurt, bm_overig=bm_overig)

    # Berichten zonder herkenbare buurt horen bij het algemene nieuws
    if bm_overig:
        with open("overige_berichten.md", "w", encoding="utf-8") as f:
            f.write("\n".join(bekendmakingregels(bm_overig)) + "\n")
        print(f"{len(bm_overig)} berichten zonder buurt naar overige_berichten.md",
              file=sys.stderr)
    elif os.path.exists("overige_berichten.md"):
        os.remove("overige_berichten.md")
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
