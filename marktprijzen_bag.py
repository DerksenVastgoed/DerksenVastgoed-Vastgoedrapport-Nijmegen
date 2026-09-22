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




def bag_dump(adres, plaats="Nijmegen"):
    """
    Toont de volledige BAG-respons voor een adres. Bedoeld om uit te zoeken
    welk veld welke oppervlakte bevat: die van het verblijfsobject of die van
    het pand. Gebruik: python marktprijzen_bag.py --bag "van Slichtenhorststraat 42"
    """
    varianten = split_huisnummer(adres)
    if not varianten:
        print(f"Kan {adres} niet splitsen in straat en huisnummer", file=sys.stderr)
        return
    straat, huisnr, letter, toev = varianten[0]
    params = {"openbareRuimteNaam": straat, "huisnummer": huisnr,
              "woonplaatsNaam": plaats, "exacteMatch": "true", "expand": "panden"}
    if letter:
        params["huisletter"] = letter
    if toev:
        params["huisnummertoevoeging"] = toev

    for naam, extra in (("met expand=panden", params),
                        ("zonder expand", {k: v for k, v in params.items()
                                           if k != "expand"})):
        print(f"\n=== {naam} ===")
        try:
            r = requests.get(f"{BAG_BASE}/adressenuitgebreid",
                             headers=BAG_HEADERS, params=extra, timeout=20)
            print(f"status {r.status_code}")
            if r.status_code != 200:
                print(r.text[:400])
                continue
            data = r.json().get("_embedded", {}).get("adressen", [])
            print(f"adressen in respons: {len(data)}")
            for i, a in enumerate(data):
                print(f"\n--- adres {i} ---")
                print(json.dumps(a, ensure_ascii=False, indent=1)[:3000])
        except Exception as e:
            print(f"fout: {e}")
        time.sleep(0.5)



def bag_eenheden_in_pand(pand_id):
    """
    Hoeveel zelfstandige eenheden kent de BAG in dit pand, en op welke adressen?

    Dit onderscheidt een pand dat feitelijk is opgedeeld van een pand dat ook
    juridisch is gesplitst. Twee keukens en twee voordeuren zeggen niets over
    de registratie; twee nummeraanduidingen wel. Staat er maar een, dan is de
    splitsing nog niet geregistreerd en heb je een omgevingsvergunning nodig.
    """
    if not BAG_API_KEY or not pand_id:
        return []
    try:
        r = requests.get(f"{BAG_BASE}/adressenuitgebreid", headers=BAG_HEADERS,
                         params={"pandIdentificatie": pand_id, "pageSize": 50},
                         timeout=(15, 60))
        if r.status_code != 200:
            return []
        rijen = r.json().get("_embedded", {}).get("adressen", [])
    except Exception:
        return []

    uit = []
    for a in rijen:
        straat = a.get("openbareRuimteNaam", "")
        nr = a.get("huisnummer", "")
        letter = a.get("huisletter") or ""
        toev = a.get("huisnummertoevoeging") or ""
        if not straat or not nr:
            continue
        uit.append({
            "adres": f"{straat} {nr}{letter}{('-' + toev) if toev else ''}",
            "oppervlakte": a.get("oppervlakte"),
            "gebruiksdoelen": a.get("gebruiksdoelen", []),
            "status": a.get("adresseerbaarObjectStatus", ""),
        })
    return uit


def bag_adressen_op_object(vbo_id):
    """
    Hoeveel adressen hangen er aan dit verblijfsobject?

    In de BAG kan een verblijfsobject meerdere nummeraanduidingen hebben, een
    hoofdadres met nevenadressen. De oppervlakte die de API teruggeeft is dan
    die van het hele object, niet van wat achter een enkel huisnummer zit. Bij
    een pand dat is opgedeeld in een boven- en benedenhuis loopt dat ver uiteen.
    """
    if not BAG_API_KEY or not vbo_id:
        return []
    try:
        r = requests.get(f"{BAG_BASE}/adressenuitgebreid", headers=BAG_HEADERS,
                         params={"adresseerbaarObjectIdentificatie": vbo_id},
                         timeout=20)
        if r.status_code != 200:
            return []
        rijen = r.json().get("_embedded", {}).get("adressen", [])
    except Exception:
        return []
    adressen = []
    for a in rijen:
        straat = a.get("openbareRuimteNaam", "")
        nr = a.get("huisnummer", "")
        letter = a.get("huisletter", "") or ""
        toev = a.get("huisnummertoevoeging", "") or ""
        if straat and nr:
            adressen.append(f"{straat} {nr}{letter}{('-' + toev) if toev else ''}")
    return adressen


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

    # Op hetzelfde adres kunnen meerdere verblijfsobjecten staan: de bestaande
    # situatie met status "in gebruik", en een al geregistreerde splitsing met
    # status "gevormd". Die laatste is nog niet gerealiseerd, dus we rekenen met
    # het object dat in gebruik is. Bij Plein 1944 142 scheelde dat 163 om 53 m2.
    in_gebruik = [x for x in embedded
                  if "in gebruik" in str(x.get("adresseerbaarObjectStatus", "")).lower()]
    gevormd = [x for x in embedded
               if "gevormd" in str(x.get("adresseerbaarObjectStatus", "")).lower()]
    a = (in_gebruik or embedded)[0]

    if gevormd and in_gebruik:
        print(f"  {straat} {huisnr}: splitsing geregistreerd maar nog niet in "
              f"gebruik ({len(gevormd)} nieuwe objecten). We rekenen met de "
              f"bestaande {a.get('oppervlakte')} m².", file=sys.stderr)

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
        "pand": (a.get("pandIdentificaties") or [""])[0],
        # Een geregistreerde maar nog niet gerealiseerde splitsing is een signaal:
        # de eigenaar is er al mee bezig.
        "splitsing_geregistreerd": [
            {"adres": f"{x.get('openbareRuimteNaam','')} {x.get('huisnummer','')}"
                      f"{x.get('huisletter','') or ''}",
             "oppervlakte": x.get("oppervlakte")}
            for x in gevormd] if gevormd else None,
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
        if woning.get("oppervlakte_bron"):
            woning["oppervlakte"] = woning["oppervlakte_bron"]
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

    # Hoeveel zelfstandige woningen kent de BAG in dit pand? Meer dan een
    # betekent dat de splitsing al geregistreerd is; precies een betekent dat
    # een feitelijke opdeling nog juridisch moet worden gemaakt.
    pand_id = bag.get("pand")
    if pand_id:
        eenheden = bag_eenheden_in_pand(pand_id)
        time.sleep(0.2)
        woon = [e for e in eenheden
                if "woonfunctie" in (e.get("gebruiksdoelen") or [])]
        if len(woon) > 1:
            verrijking["eenheden_in_pand"] = woon
            print(f"  {woning['adres']}: het pand bevat {len(woon)} zelfstandige "
                  f"woningen volgens de BAG "
                  f"({', '.join(e['adres'] for e in woon[:4])})", file=sys.stderr)

    # De oppervlakte uit de advertentie gaat voor op die uit de BAG. De
    # advertentie beschrijft wat je koopt of huurt; de BAG geeft soms het hele
    # pand of juist een enkel verblijfsobject. Bij gesplitste panden liep dat
    # ver uiteen: een bovenhuis van 144 m2 stond in de BAG als 233 m2, waardoor
    # het pand veel goedkoper per m2 leek dan het is.
    if woning.get("oppervlakte_bron"):
        bag_opp = bag.get("oppervlakte")
        verrijking["oppervlakte"] = woning["oppervlakte_bron"]
        verrijking["oppervlakte_bag"] = bag_opp
        if bag_opp and abs(bag_opp - woning["oppervlakte_bron"]) / bag_opp > 0.20:
            verrijking["opp_verschil"] = True
            print(f"  Oppervlakte wijkt af bij {woning['adres']}: "
                  f"advertentie {woning['oppervlakte_bron']} m², "
                  f"BAG {bag_opp} m². We rekenen met de advertentie.",
                  file=sys.stderr)

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
            f'margin-right:8px;vertical-align:middle">{label}</span> ')


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


def lees_actuele_rente():
    """
    De rente die het rente-script vandaag heeft gemeten. Zo rekenen de
    richtprijzen met de werkelijke stand in plaats van met een vast getal.
    """
    if not os.path.exists("rente_actueel.json"):
        return None
    try:
        with open("rente_actueel.json", encoding="utf-8") as f:
            waarde = json.load(f).get("ltv70")
        return float(waarde) if waarde and 1 < float(waarde) < 15 else None
    except Exception:
        return None


def lees_cbs():
    """Buurtcijfers uit het CBS, weggeschreven door buurten_tabel.py."""
    if not os.path.exists(CBS_PAD):
        return {}
    try:
        with open(CBS_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}



TREND_PAD = "prijstrend.json"


def lees_trend():
    """De opgeslagen prijshistorie per buurt."""
    try:
        with open(TREND_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def bewaar_prijspeil(per_buurt, stad_breed):
    """
    Legt de mediaan per buurt vast, zodat we later kunnen zien welke kant het
    op gaat. Eens per week is genoeg: dagelijks opslaan levert alleen ruis op
    bij zo'n kleine dataset.
    """
    try:
        with open(TREND_PAD, encoding="utf-8") as f:
            historie = json.load(f)
    except Exception:
        historie = {}

    vandaag = dt.date.today()
    week = f"{vandaag.isocalendar()[0]}-W{vandaag.isocalendar()[1]:02d}"
    meting = {}
    for buurt, rijen in per_buurt.items():
        if len(rijen) >= 8:
            meting[buurt] = round(st.median([p for p, _ in rijen]))
    if len(stad_breed) >= 20:
        meting["_nijmegen"] = round(st.median(stad_breed))
    if not meting:
        return historie

    meting["_datum"] = vandaag.isoformat()
    meting["_n"] = {b: len(r) for b, r in per_buurt.items() if len(r) >= 8}
    historie[week] = meting
    try:
        with open(TREND_PAD, "w", encoding="utf-8") as f:
            json.dump(historie, f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Kon {TREND_PAD} niet schrijven: {e}", file=sys.stderr)
    return historie


def trendregel(buurt, historie):
    """Hoe staat deze buurt er nu voor ten opzichte van eerder?"""
    weken = sorted(w for w in historie if not w.startswith("_"))
    if len(weken) < 2:
        return ""
    nu = historie[weken[-1]].get(buurt)
    if not nu:
        return ""
    # Vergelijk met de oudste meting die we hebben, en met vier weken terug
    stukken = []
    for terug, label in ((4, "vier weken"), (13, "een kwartaal")):
        if len(weken) > terug and historie[weken[-1 - terug]].get(buurt):
            toen = historie[weken[-1 - terug]][buurt]
            pct = (nu - toen) / toen * 100
            stukken.append(f"{pct:+.1f}".replace(".", ",") + f"% in {label}")
    oudste = historie[weken[0]].get(buurt)
    if oudste and not stukken:
        pct = (nu - oudste) / oudste * 100
        stukken.append(f"{pct:+.1f}".replace(".", ",")
                       + f"% sinds {historie[weken[0]].get('_datum', weken[0])}")
    return ". ".join(stukken)


def buurtregel(naam, cbs, opp_uit_bag=None, studenten_ring=None,
               _trend_historie=None):
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
    trend = trendregel(naam, _trend_historie or {})
    if trend:
        tweede.append(f"prijspeil {trend}")

    vpb = lees_vergunningen_per_buurt().get(naam)
    if vpb and g.get("won"):
        tweede.append(f"{vpb} kamerverhuurvergunningen sinds 2013 "
                      f"({vpb / g['won'] * 100:.1f}% van de voorraad)")

    # Wie woont er, en met hoeveel. Het aandeel alleenwonenden voorspelt de
    # vraag naar kleine eenheden.
    if g.get("eenpersoons") is not None:
        stuk = f"{g['eenpersoons']}% woont alleen"
        if g.get("met_kinderen") is not None:
            stuk += f", {g['met_kinderen']}% is een huishouden met kinderen"
        if g.get("huishoudgrootte"):
            stuk += (f", gemiddeld "
                     + f"{g['huishoudgrootte']:.1f}".replace(".", ",")
                     + " personen per huishouden")
        tweede.append(stuk)

    if g.get("leeftijd"):
        tweede.append(f"gemiddelde leeftijd "
                      + f"{g['leeftijd']:.0f}".replace(".", ",") + " jaar")

    # Bereikbaarheid: wat een huurder zonder auto aan het pand heeft
    bereik = []
    for soort, naam in (("trein", "station"), ("supermarkt", "supermarkt"),
                        ("huisarts", "huisarts")):
        km = g.get(f"afstand_{soort}")
        if km:
            bereik.append(f"{naam} op " + f"{km:.1f}".replace(".", ",") + " km")
    if bereik:
        tweede.append(", ".join(bereik))

    # Inkomen zegt wat een buurt aan huur kan dragen. Ligt de gevraagde huur
    # boven wat er verdiend wordt, dan is de doelgroep smaller dan hij lijkt.
    if g.get("inkomen") or g.get("vermogen") is not None:
        stukken_i = []
        if g.get("inkomen"):
            stukken_i.append(f"gemiddeld inkomen €{eu(g['inkomen'] * 1000)} per inwoner")
        if g.get("vermogen") is not None:
            stukken_i.append(f"mediaan vermogen €{eu(g['vermogen'] * 1000)} "
                             f"per huishouden")
        if g.get("laag_inkomen") is not None:
            stukken_i.append(f"{g['laag_inkomen']}% met een laag inkomen")
        tweede.append(", ".join(stukken_i))

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
        # Bij meer dan drie onderdelen wordt de regel te lang om te scannen
        if len(tweede) > 3:
            helft = (len(tweede) + 1) // 2
            regel += ("<br>" + " . ".join(tweede[:helft])
                      + "<br>" + " . ".join(tweede[helft:]))
        else:
            regel += "<br>" + " . ".join(tweede)

    mis = misdrijfregel(naam, lees_misdrijven(), g.get("inwoners"))
    if mis:
        regel += "<br>Misdrijven " + mis

    bron = verwijs("Kerncijfers wijken en buurten", "Kamerverhuurvergunningen",
                   "Politiedata")
    if bron:
        regel += f" {bron}"
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

# Opkoopbescherming Nijmegen, Huisvestingsverordening 2024 artikel 19.
# Het verbod geldt vier jaar na inschrijving van de leveringsakte, en alleen
# voor woonruimte die op dat moment vrij van huur was, korter dan zes maanden
# verhuurd, of verhuurd met een verhuurvergunning opkoopbescherming. Een pand
# dat langer dan zes maanden verhuurd was en in verhuurde staat wordt geleverd
# is dus geen beschermde woonruimte.
OPKOOPBESCHERMING_WOZ = 396_000
OPKOOPBESCHERMING_JAAR = 4

# Nijmegen kent geen splitsings- of woningvormingsvergunning: die begrippen
# komen in de verordening niet voor. Voor bouwkundig splitsen is wel een
# omgevingsvergunning nodig, maar er gelden geen minimumoppervlaktes vanuit
# de huisvestingsverordening.
SPLITSINGSVERGUNNING_NODIG = False



# ---------------------------------------------------------------------------
# KERNGETALLEN. Alles wat de brief rekent hangt hieraan. Pas ze hier aan; ze
# worden onder elke berekening in de brief vermeld, zodat een lezer kan zien
# waar een uitkomst op rust.
# ---------------------------------------------------------------------------
RENTE = 5.75              # verhuurhypotheek; wordt overschreven door de
                          # actuele stand uit rente_actueel.json als die er is
# Financieringsgraad. Let op twee dingen die de brief niet kan weten:
#   1. Banken lenen op de LAAGSTE van koopsom en taxatiewaarde. Koop je onder
#      de marktwaarde, dan telt de koopsom; koop je erboven, dan de taxatie.
#   2. Bij verhuurd vastgoed taxeren ze op waarde in verhuurde staat, en die
#      ligt lager dan vrij van huurder. Bij een pand met zittende huurders valt
#      de lening dus lager uit dan dit percentage suggereert.
# In de praktijk knelt bovendien vaak de rentedekking eerder dan de LTV: bij de
# huidige rente haal je de eis van 1,25 keer al niet bij een lagere lening.
LTV = 66.7                # financieringsgraad op de koopsom
# Exploitatiekosten als percentage van de kale huur, per scenario. Eén vast
# percentage voor alles was te grof: kamerverhuur kent veel meer mutaties,
# slijtage en beheer dan verhuur aan één huishouden.
#
# Dit zijn AANNAMES. Vervang ze door je eigen cijfers zodra je die hebt; dat
# is het enige getal in deze brief waar je eigen administratie beter is dan
# welke vuistregel ook.
# WAT ER WEL IN ZIT: groot onderhoud, verzekering, gemeentelijke lasten,
# beheer, leegstand en mutatiekosten.
#
# WAT ER NIET IN ZIT, omdat het via de servicekosten aan de huurder wordt
# doorbelast: gas, water, licht, internet, schoonmaak van gemeenschappelijke
# ruimten, tuinonderhoud en kleine reparaties daarin. Die kosten drukken dus
# niet op jouw rendement. Dat is ook consistent met de rest van de brief: het
# puntenstelsel begrenst de KALE huur, en daar horen servicekosten niet bij.
OPEX_PER_SCENARIO = {
    "woning": 20,
    # Hoger dan bij een huishouden door meer slijtage, vaker mutatie en
    # intensiever beheer, maar niet door de doorbelaste posten.
    "kamers": 25,
    # Iets hoger dan een gewone woning door gedeelde entree en installaties.
    "splitsen": 22,
}
OPEX_PCT = OPEX_PER_SCENARIO["woning"]   # standaard, wordt per scenario gezet


def opex_voor(scenario_naam):
    """Het exploitatiepercentage dat bij dit scenario hoort."""
    naam = (scenario_naam or "").lower()
    if "kamer" in naam:
        return OPEX_PER_SCENARIO["kamers"]
    if "splitsen" in naam:
        return OPEX_PER_SCENARIO["splitsen"]
    return OPEX_PER_SCENARIO["woning"]
DOEL_CASHFLOW = 0         # gewenst operationeel resultaat per jaar

# Beschikbaar eigen vermogen. Staat in een omgevingsvariabele en niet in dit
# bestand, want de repo is openbaar. Zonder waarde rekent de brief zonder
# budgetgrens. Zet het secret EIGEN_VERMOGEN in GitHub.
try:
    EIGEN_VERMOGEN = float(os.environ.get("EIGEN_VERMOGEN", "") or 0)
except ValueError:
    EIGEN_VERMOGEN = 0

# Rentedekking die banken eisen: nettohuur gedeeld door rentelast
DEKKINGSEIS = 1.25

# ---------------------------------------------------------------------------
# AANLOOP EN RENOVATIE
#
# Een pand levert de eerste maanden niets op: je klust, je zoekt huurders, en
# de rente loopt door. Daarna moet er geld in voordat je de huur haalt waarmee
# de brief rekent.
#
# Banken financieren verbouwing bij verhuurd vastgoed doorgaans niet mee, dus
# dit komt uit eigen vermogen. Het verhoogt je inleg en verlaagt daarmee zowel
# je rendement als de prijs die je kunt betalen.
#
# DEZE BEDRAGEN ZIJN AANNAMES. Vervang ze door je eigen ervaringscijfers; jij
# hebt gebouwd in Nijmegen en weet wat een vierkante meter kost.
# ---------------------------------------------------------------------------
AANLOOPMAANDEN = 3        # klussen, verhuurklaar maken en verhuren

# De verbouwing bestaat uit twee posten die je niet moet mengen.
#
# 1. VERDUURZAMING naar een beter label. LET OP: de bedragen hieronder zijn
#    NIET uit de RVO-kentallen overgenomen. Ze zijn door Claude gekozen als
#    werkbare eerste schatting. De echte kentallen bestaan wel en zijn de
#    juiste bron: marktonderzoek, peildatum mei 2025, te vinden op
#    regelhulpenvoorbedrijven.nl/kostenkentallen. Zolang die niet zijn
#    ingelezen, staat hier een aanname en geen meting.
#    Let op bij het overnemen van die cijfers:
#      - ze zijn exclusief btw; PBL rekent met gemiddeld 15% (9% arbeid,
#        21% materiaal)
#      - de werkelijke kosten wijken 20 tot 30% af door locatie, bouwkundige
#        staat en complexiteit
#      - asbest, funderingsherstel en slechte bouwkundige staat vallen er
#        buiten, en dat is bij vooroorlogse panden geen detail
#    Als particuliere verhuurder vraag je subsidie aan via SVOH, niet via ISDE.
#
# 2. VERHUURKLAAR MAKEN: keuken, badkamer, schilderwerk, vloeren, elektra.
#    Hiervoor bestaat geen landelijk kental; dit is je eigen ervaringscijfer.
#
# De bedragen hieronder zijn nog aannames. Vul ze aan met de RVO-tabel voor de
# eerste post en met je eigen cijfers voor de tweede.
VERDUURZAMING_PER_M2 = {
    # naar label B of beter; hoe slechter het startpunt, hoe meer er moet.
    # A0 is de klasse voor bijna emissievrije gebouwen uit de NTA 8800:2025,
    # geldig voor labels die vanaf 29 mei 2026 zijn geregistreerd.
    "A0": 0, "A": 0, "B": 0, "C": 150, "D": 275, "E": 400, "F": 475, "G": 550,
}

# Een energielabel opstellen kost geld, en sinds 29 mei 2026 is het ook bij
# monumenten verplicht bij verkoop, verhuur of oplevering. De uitzondering die
# daar decennialang gold, is vervallen door de Europese richtlijn EPBD IV.
LABEL_PLICHT_VANAF = "2026-05-29"
VERDUURZAMING_ONBEKEND = 275
VERHUURKLAAR_PER_M2 = 275     # keuken, badkamer, schilderwerk, vloeren
BTW_OP_VERBOUWING = 15        # gemiddeld, want arbeid 9% en materiaal 21%


def _bouwkostenfactor():
    """
    Met welke factor de kentallen worden geindexeerd.

    De RVO-cijfers hebben peildatum mei 2025. Zonder indexering loopt de
    raming steeds verder achter, en dan schat de brief elke verbouwing te
    laag in. Lukt het ophalen niet, dan rekenen we ongeindexeerd en zegt de
    brief dat erbij.
    """
    if not indexfactor:
        return {"factor": 1.0, "geindexeerd": False}
    try:
        return indexfactor()
    except Exception:
        return {"factor": 1.0, "geindexeerd": False}



BOUWKOSTEN_EIGEN_PAD = "bouwkosten_eigen.txt"


def lees_eigen_bouwkosten():
    """
    Eigen ervaringscijfers per m2, als die er zijn.

    Formaat per regel: soort | euro per m2 | peildatum | toelichting
    Soorten: verduurzaming-<label> of verhuurklaar.

    Deze gaan voor op de aannames in dit script, zoals de advertentie-
    oppervlakte voorgaat op de BAG. Een getal uit de eigen administratie is
    altijd beter dan een geschat kental, ook als het uit het hoofd komt.
    """
    if not os.path.exists(BOUWKOSTEN_EIGEN_PAD):
        return {}
    uit = {}
    try:
        with open(BOUWKOSTEN_EIGEN_PAD, encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if not regel or regel.startswith("#") or "|" not in regel:
                    continue
                d = [x.strip() for x in regel.split("|")]
                bedrag = re.sub(r"[^\d]", "", d[1]) if len(d) > 1 else ""
                if not d[0] or not bedrag:
                    continue
                uit[d[0].lower()] = {
                    "per_m2": int(bedrag),
                    "peildatum": d[2] if len(d) > 2 else "",
                    "toelichting": d[3] if len(d) > 3 else "",
                }
    except Exception:
        return {}
    return uit


def _herkomst_verbouwing(uit):
    """Waar komen deze bedragen vandaan? Eerlijk benoemen in de brief."""
    eigen = uit.get("eigen") or {}
    delen = []
    if eigen.get("verduurzaming"):
        delen.append("verduurzaming uit de eigen administratie")
    else:
        delen.append("verduurzaming is een aanname van het script, nog niet "
                     "getoetst aan de kostenkentallen van RVO")
    if eigen.get("verhuurklaar"):
        delen.append("verhuurklaar maken uit de eigen administratie")
    else:
        delen.append("verhuurklaar maken is eveneens een aanname")

    idx = uit.get("index") or {}
    staart = (f"Inclusief {BTW_OP_VERBOUWING}% btw"
              + (f" en geindexeerd "
                 + f"{idx['pct']:+.1f}".replace(".", ",")
                 + f"% van {idx['vanaf']} naar {idx['tot']} met de CBS "
                   f"bouwkostenindex" if idx.get("geindexeerd") else "")
              + ".")
    return "Herkomst: " + "; ".join(delen) + ". " + staart


def renovatiekosten(opp, energielabel=None, uitsplitsen=False):
    """
    Geschatte verbouwkosten: verduurzaming plus verhuurklaar maken, inclusief
    btw. Uitsplitsen geeft de twee posten apart terug.
    """
    if not opp:
        return {"totaal": 0, "verduurzaming": 0, "verhuurklaar": 0} if uitsplitsen else 0
    letter = ""
    if isinstance(energielabel, dict):
        letter = (energielabel.get("label") or "")[:1].upper()
    eigen = lees_eigen_bouwkosten()
    gebruikt_eigen = {}

    # Eigen cijfers gaan voor, per label en anders algemeen
    tarief_d = None
    for sleutel in (f"verduurzaming-{letter.lower()}", "verduurzaming"):
        if sleutel in eigen:
            tarief_d = eigen[sleutel]["per_m2"]
            gebruikt_eigen["verduurzaming"] = eigen[sleutel]
            break
    if tarief_d is None:
        tarief_d = VERDUURZAMING_PER_M2.get(letter, VERDUURZAMING_ONBEKEND)

    tarief_k = None
    if "verhuurklaar" in eigen:
        tarief_k = eigen["verhuurklaar"]["per_m2"]
        gebruikt_eigen["verhuurklaar"] = eigen["verhuurklaar"]
    if tarief_k is None:
        tarief_k = VERHUURKLAAR_PER_M2

    duurzaam = opp * tarief_d
    klaar = opp * tarief_k
    btw = 1 + BTW_OP_VERBOUWING / 100

    # Indexeren naar nu, want de kentallen hebben peildatum mei 2025
    idx = _bouwkostenfactor()
    f = idx.get("factor", 1.0) * btw

    if uitsplitsen:
        return {"totaal": (duurzaam + klaar) * f,
                "verduurzaming": duurzaam * f,
                "verhuurklaar": klaar * f,
                "per_m2_verduurzaming": tarief_d,
                "per_m2_verhuurklaar": tarief_k,
                "index": idx,
                "eigen": gebruikt_eigen}
    return (duurzaam + klaar) * f


def aanloopverlies(lening, netto_huur):
    """
    Wat de aanloopperiode kost: de rente loopt door terwijl er geen huur is.
    De gemiste huur zelf is geen uitgave maar wel rendement dat je misloopt,
    dus die tellen we apart.
    """
    maanden = AANLOOPMAANDEN / 12
    return {
        "rente": lening * RENTE / 100 * maanden,
        "gemiste_huur": netto_huur * maanden,
    }
LOOPTIJD_JAAR = 30        # looptijd voor de annuiteit; 0 = alleen rente betalen

# Aankoopkosten, apart zodat je ziet waar ze vandaan komen.
# Overdrachtsbelasting voor woningen die niet als hoofdverblijf dienen.
# Per 1 januari 2026 verlaagd van 10,4% naar 8%. Controleer dit jaarlijks:
# het tarief is de afgelopen jaren meermaals gewijzigd en het is de grootste
# post in de aankoopkosten.
OVERDRACHTSBELASTING_PCT = 8.0   # tarief beleggingsvastgoed; controleer jaarlijks
BIJKOMENDE_KOSTEN_PCT = 2.0       # notaris, makelaar, taxatie, advies
AANKOOPKOSTEN_PCT = OVERDRACHTSBELASTING_PCT + BIJKOMENDE_KOSTEN_PCT

# Aanname voor de huur per m2 per maand, per buurt. Vervalt zodra er gemeten
# huuraanbiedingen binnenkomen; in de brief staat per buurt welke bron geldt.
HUUR_M2_MND = {
    "Stadscentrum": 20, "Benedenstad": 20, "Bottendaal": 18,
    "Galgenveld": 18, "Altrade": 17, "Biezen": 18,
}



def jaarlast_factor():
    """
    Wat kost een euro lening per jaar? Bij LOOPTIJD_JAAR = 0 alleen rente,
    anders een annuiteit waarin rente en aflossing samen zitten. Dat laatste is
    de strengere lat: de huur moet dan ook de aflossing dragen.
    """
    r = RENTE / 100
    if not LOOPTIJD_JAAR:
        return r
    return r / (1 - (1 + r) ** -LOOPTIJD_JAAR)



# Boven deze oppervlakte is verhuur aan een enkel huishouden niet realistisch:
# de maandhuur loopt dan op tot bedragen die de markt niet betaalt.
MAX_M2_EEN_HUISHOUDEN = 150
MAX_HUUR_EEN_HUISHOUDEN = 3500     # euro per maand
# Aandeel van het vloeroppervlak dat bij verkamering verhuurbaar is; de rest is
# gang, trappenhuis en gedeelde ruimte. Ontleend aan een pand van 439 m2 bvo
# met 346 m2 verhuurbaar.
VERHUURBAAR_AANDEEL = 0.79

# Splitsen: aannames, want hier is geen openbare norm voor. Nijmegen kent geen
# splitsingsvergunning, dus de rem zit in het Bouwbesluit en het omgevingsplan.
# Ondergrens per zelfstandige eenheid. Er is geen wettelijke norm; Nijmegen
# verleende in september 2026 een vergunning voor eenheden van 53, 43 en 32 m2
# (Plein 1944 142), dus 30 is realistischer dan de 40 die we eerst aanhielden.
MIN_UNIT_M2 = 30
VERHUURBAAR_SPLITSING = 0.90  # verlies aan gedeelde entree en trappenhuis
MAX_UNITS = 6               # boven dit aantal is het geen splitsing meer



def splitsscenario(w, huur_bk, huur_k, buurt, per_buurt_prijzen=None):
    """
    Wat levert het op om dit pand bouwkundig te splitsen in zelfstandige
    woningen? Nijmegen kent geen splitsingsvergunning, dus de rem zit in het
    Bouwbesluit, het omgevingsplan en de verbouwing zelf.

    De winst zit erin dat kleine zelfstandige eenheden per m2 fors meer huur
    opbrengen dan een grote woning. De rem zit in de opkoopbescherming: komt
    een nieuwe eenheid onder de WOZ-grens uit, dan mag je die vier jaar lang
    niet verhuren zonder vergunning.
    """
    opp = w.get("oppervlakte")
    if not opp:
        return None
    bruikbaar = opp * VERHUURBAAR_SPLITSING
    aantal = int(bruikbaar // MIN_UNIT_M2)
    if aantal < 2:
        return None
    aantal = min(aantal, MAX_UNITS)

    # Het maximale aantal eenheden is zelden het realistische aantal. Bij een
    # bovenwoning over twee etages is de natuurlijke splitsing er een per
    # verdieping. Kent de BAG al meer eenheden in dit pand, dan is dat aantal
    # het uitgangspunt: die opdeling is al geregistreerd.
    al_bekend = len(w.get("eenheden_in_pand") or [])
    if al_bekend > 1:
        aantal = al_bekend
    elif bruikbaar / aantal < 45 and bruikbaar >= 2 * 45:
        # Eenheden onder 45 m2 zijn krap; twee ruimere etages is vaak
        # realistischer dan vier kleine.
        aantal = max(2, int(bruikbaar // 60))

    unit_m2 = bruikbaar / aantal
    huur_m2, bron = huur_voor_buurt(buurt, huur_bk, huur_k, unit_m2, "woning")
    maand = huur_m2 * bruikbaar

    # Splitsen is in Nijmegen vooral een verkoopinstrument: de eenheden vallen
    # onder de opkoopbescherming en het puntenstelsel begrenst de huur op
    # sociaal niveau. De winst zit in het verschil tussen de prijs per m2 van
    # een groot pand en die van kleine eenheden.
    verkoop_per_m2 = None
    if per_buurt_prijzen:
        klein = [p for p, x in per_buurt_prijzen
                 if groottebandje(x.get("oppervlakte")) == "klein"]
        if len(klein) >= 4:
            verkoop_per_m2 = st.median(klein)

    # Waarde per eenheid, om te toetsen aan de opkoopbescherming
    unit_waarde = w["prijs"] / aantal
    beschermd = unit_waarde < OPKOOPBESCHERMING_WOZ

    # Puntentelling per nieuwe eenheid. Onder 187 punten is de huur wettelijk
    # begrensd en is de marktprijs per m2 niet wat je mag vragen.
    punten = segment = None
    if wws_punten:
        ep = w.get("energielabel") or {}
        try:
            r = wws_punten(unit_m2, unit_waarde, label=ep.get("label"),
                           monument=bool(w.get("monument")), heeft_buiten=False)
            punten, segment = r["punten"], r["segment"]
            if r["gereguleerd"] and wws_max_huur:
                # Onder 187 punten geldt een wettelijk maximum per eenheid. De
                # markthuur mag dan niet gevraagd worden, dus we rekenen met
                # het maximum. Dat is het bedrag waarop je een bod baseert.
                maximum = wws_max_huur(punten)
                if maximum:
                    maand_wettelijk = maximum * aantal
                    if maand_wettelijk < maand:
                        maand = maand_wettelijk
                        huur_m2 = maand / bruikbaar
                        bron = f"wettelijk maximum, {punten} punten per eenheid"
        except Exception:
            pass

    opbrengst = verkoop_per_m2 * bruikbaar if verkoop_per_m2 else None
    return {"naam": f"splitsen in {aantal}", "huur_m2": huur_m2, "maand": maand,
            "verkoopwaarde": opbrengst,
            "verkoopmarge": (opbrengst - w["prijs"]) if opbrengst else None,
            "opp": round(bruikbaar), "bron": bron, "aantal": aantal,
            "unit_m2": round(unit_m2), "unit_waarde": unit_waarde,
            "beschermd": beschermd, "punten": punten, "segment": segment,
            "gereguleerd": bool(segment and segment != "vrije sector")}



KAMERSIGNALEN = ("kamerverhuur", "omzetting", "onttrekking", "brandveilig gebruik")

# Handhaving weegt zwaarder dan een vergunningaanvraag: dit is het enige
# openbare signaal op pandniveau, en het telt mee in de leefbaarheidstoets.
HANDHAVINGSIGNALEN = ("sluiting", "handhaving", "onrechtmatig gebruik",
                      "geluidsoverlast")


def handhaving_op_adres(adres, archief, straal=0):
    """Handhavingsbesluiten op dit adres, of in de directe omgeving."""
    if not archief:
        return []
    m = re.match(r"^(.+?)\s+(\d+)", adres.strip())
    if not m:
        return []
    straat, nummer = m.group(1), int(m.group(2))
    treffers = []
    for offset in range(-straal, straal + 1):
        buur = nummer + offset
        if buur < 1:
            continue
        for t in archief.get(archief_sleutel(straat, str(buur)), []):
            soorten = [x.lower() for x in (t.get("soorten") or [])]
            raak = [s for s in HANDHAVINGSIGNALEN
                    if any(s in x for x in soorten)]
            if raak:
                treffers.append({"adres": f"{straat} {buur}",
                                 "datum": t.get("datum", ""),
                                 "soort": ", ".join(t.get("soorten") or []),
                                 "titel": t.get("titel", ""),
                                 "url": t.get("url", ""),
                                 "eigen": offset == 0})
    return treffers
VERGUNNINGEN_PAD = "kamervergunningen.json"



MISDRIJVEN_PAD = "misdrijven_per_buurt.json"

# Wat er in de buurtregel komt te staan, en in welke volgorde. De rest staat
# wel in het bestand maar zou de regel te lang maken.
MISDRIJVEN_TONEN = ("woninginbraak", "vernieling", "drugs- en drankoverlast")


def lees_misdrijven():
    if not os.path.exists(MISDRIJVEN_PAD):
        return {}
    try:
        with open(MISDRIJVEN_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _bruikbare_soorten(misdrijven):
    """
    Welke misdrijfsoorten leveren werkelijk cijfers op?

    Staat een soort in elke buurt op nul, dan krijgen we hem niet binnen en is
    het geen bevinding maar een gat in de data. Die tonen we niet, want nul
    suggereert dat het er niet gebeurt.
    """
    totalen = {}
    for per_jaar in misdrijven.values():
        if not per_jaar:
            continue
        laatst = per_jaar[sorted(per_jaar)[-1]]
        for soort, aantal in laatst.items():
            totalen[soort] = totalen.get(soort, 0) + (aantal or 0)
    return {s for s, t in totalen.items() if t > 0}


def misdrijfregel(buurt, misdrijven, inwoners=None):
    """
    Misdrijven per buurt, afgezet tegen het aantal inwoners. Absolute aantallen
    zeggen weinig: een grote buurt heeft er vanzelf meer.
    """
    per_buurt = misdrijven.get(buurt)
    if not per_buurt:
        return ""
    jaren = sorted(per_buurt)
    if not jaren:
        return ""
    laatst = per_buurt[jaren[-1]]
    jaar = jaren[-1][:4]

    bruikbaar = _bruikbare_soorten(misdrijven)
    stukken = []
    for soort in MISDRIJVEN_TONEN:
        n = laatst.get(soort)
        if n is None or soort not in bruikbaar:
            continue
        tekst = f"{n} {soort}"
        if inwoners:
            tekst += f" ({n / inwoners * 1000:.1f}".replace(".", ",") + " per 1.000)"
        stukken.append(tekst)
    if not stukken:
        return ""

    regel = f"in {jaar}: " + ", ".join(stukken)

    # Beweging ten opzichte van het jaar ervoor, alleen bij genoeg gevallen
    if len(jaren) > 1:
        vorig = per_buurt[jaren[-2]]
        nu, toen = laatst.get("totaal"), vorig.get("totaal")
        if nu and toen and toen >= 50:
            pct = (nu - toen) / toen * 100
            regel += (f". totaal {f'{pct:+.0f}'}% ten opzichte van {jaren[-2][:4]}")
    return regel



def eigen_kamervergunning(w, vergunningen=None):
    """
    De vergunningen voor kamerverhuur op dit pand zelf, uit de gemeentelijke lijst.

    Samenvoeging telt niet mee, want dat is geen kamerverhuur. Geen treffer
    betekent niet dat er niets ligt: oudere vergunningen staan niet in de lijst.
    """
    vergunningen = (vergunningen if vergunningen is not None
                    else lees_kamervergunningen())
    m = re.match(r"^(.+?)\s+(\d+)", (w.get("adres") or "").strip())
    if not m or not vergunningen:
        return []
    basis = archief_sleutel(m.group(1), m.group(2))
    lijst = list(vergunningen.get(basis, []))

    # Staat het nummer in de lijst met een lettertoevoeging, zoals 28A, dan
    # matcht de exacte sleutel niet. Alleen een letter is veilig: na het
    # normaliseren valt een streepje weg, en dan is 28-1 niet te onderscheiden
    # van nummer 281.
    if not lijst:
        for sleutel, items in vergunningen.items():
            if (sleutel.startswith(basis)
                    and re.fullmatch(r"[a-z]{1,2}", sleutel[len(basis):])):
                lijst.extend(items)

    # En als laatste: op het adres zoals het in de vergunning zelf staat
    if not lijst:
        doel = basis
        for items in vergunningen.values():
            for v in items:
                ma = re.match(r"^(.+?)\s+(\d+)", (v.get("adres") or "").strip())
                if ma and archief_sleutel(ma.group(1), ma.group(2)) == doel:
                    lijst.append(v)

    return [v for v in lijst
            if "samenvoeg" not in (v.get("soort") or "").lower()]


def kamerverhuur_bekend(w, vergunningen=None, archief=None):
    """
    Aanwijzingen dat dit pand per kamer wordt verhuurd, elk met de bron.

    De vergunningenlijst alleen is niet genoeg. Boven de WOZ-grens van
    €396.000 is geen omzettingsvergunning nodig, dus kamerpanden in die klasse
    staan er per definitie niet in; de St. Annastraat 28 is daar een voorbeeld
    van. Een melding brandveilig gebruik hangt niet aan de WOZ maar aan het
    gebruik: verplicht vanaf vijf verhuurde kamers (Besluit bouwwerken
    leefomgeving, artikel 6.6). Die meldingen staan in het bekendmakingen-
    archief.

    Wat ook dit mist: panden met drie of vier kamers boven de WOZ-grens, en
    meldingen van voor het archief. Geen aanwijzing betekent dus niet dat er
    geen kamerverhuur is.
    """
    uit = []
    for v in eigen_kamervergunning(w, vergunningen):
        uit.append({"bron": "vergunningenlijst van de gemeente",
                    "soort": v.get("soort") or "kamerverhuur",
                    "jaar": (v.get("datum") or "")[:4]})

    archief = archief if archief is not None else lees_archief()
    m = re.match(r"^(.+?)\s+(\d+)", (w.get("adres") or "").strip())
    if m and archief:
        for t in archief.get(archief_sleutel(m.group(1), m.group(2)), []):
            soorten = " ".join(x.lower() for x in (t.get("soorten") or []))
            titel = (t.get("titel") or "").lower()
            jaar = (t.get("datum") or "")[:4]
            if "brandveilig" in soorten or "brandveilig" in titel:
                uit.append({"bron": "melding brandveilig gebruik",
                            "soort": "melding brandveilig gebruik", "jaar": jaar})
            elif (any(k in soorten for k in ("kamerverhuur", "omzetting"))
                    and not titel.startswith("aanvraag")):
                # Een aanvraag is nog geen toestemming; alleen een besluit telt
                uit.append({"bron": "officiele bekendmaking",
                            "soort": "besluit kamerverhuur", "jaar": jaar})
    return uit


def wws_indicatie(w):
    """
    Het puntenaantal van een pand, voor zover het uit bekende gegevens volgt.

    Het woningwaarderingsstelsel telt onder meer de oppervlakte, het
    energielabel en de WOZ-waarde, plus keuken, sanitair, buitenruimte en
    verwarming. De eerste drie zijn per pand bekend: oppervlakte uit de BAG of
    de advertentie, het label uit EP-Online, de WOZ als die is ingevoerd. Voor
    keuken, sanitair en buitenruimte neemt wwso.py een gewone woning aan, en
    verwarming zit er niet in. De uitkomst is daarom een ondergrens.

    Zonder bekende WOZ rekenen we niet: de vraagprijs is geen WOZ, en de WOZ
    is juist een van de zwaarste onderdelen van de telling.
    """
    # Heeft het pand een vergunning voor kamerverhuur, dan wordt het per kamer
    # verhuurd. Dan geldt het puntenstelsel voor onzelfstandige woonruimte, en
    # daarbij geldt altijd een maximale huur. De telling voor een zelfstandige
    # woning geeft dan een getal dat nergens over gaat: bij de St. Annastraat 28
    # kwam er 476 punten en "vrije sector" uit, terwijl het een kamerpand is.
    bekend = kamerverhuur_bekend(w)
    if bekend:
        v = bekend[0]
        return {"punten": None, "kamerpand": True,
                "basis": f"{v['soort']}{' uit ' + v['jaar'] if v['jaar'] else ''}, "
                         f"bron: {v['bron']}",
                "oordeel": ("er is een aanwijzing voor kamerverhuur. Per kamer "
                            "verhuurd geldt het puntenstelsel voor onzelfstandige "
                            "woonruimte, en daarbij geldt altijd een maximale "
                            "huur, ongeacht het aantal punten")}

    try:
        from wwso import wws_punten
    except Exception:
        return None
    woz = w.get("woz")
    opp = w.get("oppervlakte")
    if not woz or not opp:
        return None
    # Zo groot dat het script het niet als een huishouden doorrekent: dan zegt
    # de telling voor een zelfstandige woning weinig over de verhuur.
    if opp > MAX_M2_EEN_HUISHOUDEN:
        return {"punten": None, "kamerpand": False,
                "basis": f"{opp} m2",
                "oordeel": (f"groter dan {MAX_M2_EEN_HUISHOUDEN} m2, dus niet als "
                            f"een huishouden doorgerekend; een telling voor een "
                            f"zelfstandige woning zegt hier weinig")}
    label = (w.get("energielabel") or {}).get("label")
    uit = wws_punten(opp, woz, label=label, monument=bool(w.get("monument")))
    punten = uit.get("punten")
    if punten is None:
        return None
    if punten >= 187:
        oordeel = ("vrije sector: de ondergrens ligt al op of boven 187 punten, "
                   "en verwarming telt nog mee")
    else:
        oordeel = ("onder de 187 op basis van wat bekend is; keuken, sanitair en "
                   "verwarming bepalen of het middenhuur blijft of vrije sector "
                   "wordt")
    basis = [f"{opp} m2", f"WOZ €{eu(woz)}",
             f"label {label}" if label else "label onbekend, niet meegeteld"]
    return {"punten": punten, "oordeel": oordeel, "basis": ", ".join(basis)}


def _uitleg_blokkade(route, reden):
    """
    Waarom valt een route af, met het mechanisme erbij.

    Alleen het woord "opkoopbescherming" liet de brief zelf invullen hoe dat
    werkt, en dan ging het mis: de brief concludeerde dat je "net boven de
    grens" moest zoeken, terwijl je bij splitsen in twee ruwweg het dubbele
    nodig hebt. Het mechanisme en de rekensom staan er daarom nu bij.
    """
    grens = OPKOOPBESCHERMING_WOZ
    # De opkoopbescherming toetst de WOZ van het pand bij aankoop, niet die van
    # eenheden die je daarna zelf maakt (artikel 19 Huisvestingsverordening
    # Nijmegen 2024). Een eerdere versie van deze tekst rekende per eenheid en
    # noemde een ondergrens van twee keer de grens; dat was fout.
    if reden == "opkoopbescherming":
        wat = "splitsen om te verhuren" if route == "splitsen" else "kamerverhuur"
        return (f"{wat} valt af op de opkoopbescherming: het pand heeft een WOZ "
                f"van €{eu(grens)} of minder, en dan mag je het na aankoop vrij "
                f"van huur vier jaar niet verhuren zonder vergunning, gesplitst "
                f"of niet.")
    return f"{route} valt af op {reden}."


def lees_vergunningen_per_buurt():
    """
    Aantal verleende kamerverhuurvergunningen per buurt.

    De buurtnamen uit PDOK wijken soms af van die in onze eigen lijst, met een
    hoofdletter of een streepje verschil. Daarom matchen we op een genormali-
    seerde naam en niet op de letterlijke tekst.
    """
    if not os.path.exists("vergunningen_per_buurt.json"):
        return {}
    try:
        with open("vergunningen_per_buurt.json", encoding="utf-8") as f:
            ruw = json.load(f)
    except Exception:
        return {}

    def norm(naam):
        return re.sub(r"[^a-z0-9]", "", str(naam).lower())

    uit = dict(ruw)
    for naam, aantal in ruw.items():
        uit[norm(naam)] = aantal
    for buurt in FOCUS_BUURTEN:
        if buurt not in uit and norm(buurt) in uit:
            uit[buurt] = uit[norm(buurt)]

    # Levert het bestand niets op voor onze buurten, dan tellen we zelf: de
    # vergunningenlijst plus de straat-naar-buurtcache hebben we toch al. Zo
    # hangt de kolom niet af van een apart bestand dat verouderd kan zijn.
    if not any(uit.get(b) for b in FOCUS_BUURTEN):
        zelf = _tel_vergunningen_per_buurt()
        if zelf:
            print(f"Vergunningen per buurt zelf geteld: "
                  + ", ".join(f"{b} {n}" for b, n in sorted(zelf.items())),
                  file=sys.stderr)
            uit.update(zelf)
        else:
            print("Geen vergunningen per buurt beschikbaar; kolom blijft leeg. "
                  "Draai vergunningen_buurten.py om de koppeling te maken.",
                  file=sys.stderr)
    return uit


def _tel_vergunningen_per_buurt():
    """
    Tel de vergunningen per buurt uit de eigen bestanden.

    Gebruikt de vergunningenlijst en de straat-naar-buurtcache die het
    koppelscript eerder heeft opgebouwd. Ontbreekt die cache, dan kunnen we
    niets tellen en blijft de kolom leeg.
    """
    try:
        with open("straat_buurt_cache.json", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        return {}
    if not cache:
        return {}

    def norm_s(naam):
        return re.sub(r"[^a-z0-9]", "", str(naam).lower())

    straat_naar_buurt = {norm_s(k): v for k, v in cache.items() if v}

    telling = {}
    for lijst in lees_kamervergunningen().values():
        for v in lijst:
            m = re.match(r"^(.+?)\s+\d", v.get("adres", ""))
            if not m:
                continue
            buurt = straat_naar_buurt.get(norm_s(m.group(1)))
            if buurt in FOCUS_BUURTEN:
                telling[buurt] = telling.get(buurt, 0) + 1
            break
    return telling


def lees_kamervergunningen():
    """
    Verleende vergunningen uit de overzichten van de gemeente: onttrekking,
    omzetting en samenvoeging vanaf 2016, plus omgevingsvergunningen voor
    verbouwing ten behoeve van kamerverhuur vanaf 2013.

    Let op: oudere vergunningen staan er niet in, en veel bestaande kamerpanden
    zijn ouder dan dat. Geen treffer is dus geen bewijs dat er niets ligt.
    """
    if not os.path.exists(VERGUNNINGEN_PAD):
        return {}
    try:
        with open(VERGUNNINGEN_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def buren_met_kamerverhuur(adres, archief, vergunningen=None, straal=2):
    """
    Nijmegen staat niet meer dan twee direct naast, onder of boven elkaar
    gelegen kamergewijs bewoonde woningen toe. Deze functie kijkt in het
    bekendmakingen-archief of de buurpanden zo'n signaal hebben.

    Beperking: het archief gaat maar enkele jaren terug. Een vergunning van
    voor die tijd zien we niet. Geen treffer is dus geen vrijbrief.
    """
    if not archief and not vergunningen:
        return []
    m = re.match(r"^(.+?)\s+(\d+)", adres.strip())
    if not m:
        return []
    straat, nummer = m.group(1), int(m.group(2))

    treffers = []
    for offset in range(-straal, straal + 1):
        if offset == 0:
            continue
        buur = nummer + offset
        if buur < 1:
            continue
        sleutel = archief_sleutel(straat, str(buur))

        # De vergunningenlijst van de gemeente is hard bewijs en gaat voor
        vlijst = (vergunningen or {}).get(sleutel, [])
        if vlijst:
            treffers.append({"adres": vlijst[0].get("adres", f"{straat} {buur}"),
                             "datum": vlijst[0].get("datum", ""),
                             "soort": vlijst[0].get("soort", "vergunning"),
                             "hard": True})
            continue

        for t in (archief or {}).get(sleutel, []):
            soorten = [x.lower() for x in (t.get("soorten") or [])]
            if any(k in " ".join(soorten) for k in KAMERSIGNALEN):
                treffers.append({"adres": f"{straat} {buur}",
                                 "datum": t.get("datum", ""),
                                 "soort": ", ".join(t.get("soorten") or []),
                                 "url": t.get("url", ""), "hard": False})
                break
    return treffers


def kies_scenario(w, huur_bk, huur_k, buurt, mediaan_m2=None,
                  _per_buurt_prijzen=None):
    """
    Bepaalt hoe een pand realistisch verhuurd wordt en tegen welke huur.

    Een groot pand verhuur je niet aan een huishouden maar per kamer, en een
    klein appartement kun je niet verkameren. De keuze volgt dus uit de omvang,
    en uit signalen dat er al kamerverhuur plaatsvindt.
    """
    opp = w.get("oppervlakte")
    if not opp:
        return None

    # Aanwijzingen dat het pand al als kamerverhuur draait
    tekst = " ".join(str(w.get(k, "")) for k in ("adres", "status", "bron")).lower()
    signalen = w.get("signalen") or []
    kamerpand = (bool(kamerverhuur_bekend(w))
                 or any("kamerverhuur" in (s.get("soorten") or []) for s in signalen)
                 or "kamer" in tekst)

    huur_w, bron_w = huur_voor_buurt(buurt, huur_bk, huur_k, opp, "woning")
    maand_w = huur_w * opp

    geschikt_woning = (opp <= MAX_M2_EEN_HUISHOUDEN
                       and maand_w <= MAX_HUUR_EEN_HUISHOUDEN)

    # Verkameren verzilvert vierkante meters, geen kwaliteit. Een kamerhuurder
    # betaalt niet extra voor een tuin, de ligging of de afwerking, terwijl je
    # die wel meebetaalt. Ligt de prijs per m2 boven de buurtmediaan, dan koop
    # je die meters duur in en is verkameren zelden de juiste route. Ook de
    # leefbaarheidstoets loopt in zulke straten vrijwel altijd stuk.
    # Vergelijken binnen dezelfde grootteklasse: grote panden hebben altijd een
    # lagere prijs per m2, dus toetsen aan de buurtmediaan zou hen ten onrechte
    # goedkoop laten lijken.
    duur_ingekocht = False
    if mediaan_m2 and opp:
        duur_ingekocht = (w["prijs"] / opp) > mediaan_m2

    sp = splitsscenario(w, huur_bk, huur_k, buurt, _per_buurt_prijzen)

    # Het puntenstelsel geldt ook voor een pand dat je als een woning verhuurt.
    # Tot 21 september 2026 werd dat alleen bij splitsen getoetst, waardoor een
    # pand in de middenhuur met markthuur werd doorgerekend en de richtprijs te
    # hoog uitviel. Nu toetsen we het hier ook, als de WOZ bekend is. De
    # telling is een ondergrens (verwarming ontbreekt), dus het maximum is
    # voorzichtig; voor een bod is dat de goede kant.
    punten_w = None
    if wws_punten and wws_max_huur and w.get("woz") and opp:
        try:
            ep = w.get("energielabel") or {}
            r = wws_punten(opp, w["woz"], label=ep.get("label"),
                           monument=bool(w.get("monument")))
            punten_w = r["punten"]
            if r["gereguleerd"]:
                maximum = wws_max_huur(punten_w)
                if maximum and maximum < maand_w:
                    maand_w = maximum
                    huur_w = maximum / opp
                    bron_w = (f"wettelijk maximum bij {punten_w} punten "
                              f"(ondergrens), niet de markthuur")
        except Exception:
            pass
    if punten_w is None:
        # Zonder WOZ kunnen we niet toetsen. Dat zeggen we erbij, want dan kan
        # de huur boven het wettelijk maximum liggen zonder dat we het zien.
        bron_w = f"{bron_w}; niet getoetst aan het puntenstelsel, WOZ onbekend"

    if geschikt_woning and not kamerpand:
        # Levert splitsen aantoonbaar meer op, dan tonen we dat
        if sp and sp["maand"] > maand_w * 1.1:
            return sp
        return {"naam": "één woning", "huur_m2": huur_w, "maand": maand_w,
                "opp": opp, "bron": bron_w, "wws_punten": punten_w}

    # Kamerverhuur: alleen het verhuurbare deel telt, tegen de kamerhuur
    huur_k_m2, bron_k = huur_voor_buurt(buurt, huur_bk, huur_k, 20, "kamer")
    verhuurbaar = round(opp * VERHUURBAAR_AANDEEL)
    maand_k = huur_k_m2 * verhuurbaar
    naam = "kamers" if kamerpand else "kamers, mits vergunning"
    if not kamerpand:
        # Omzetten van een eengezinswoning is geen formaliteit: de
        # leefbaarheidstoets en de regel van maximaal twee kamergewijs bewoonde
        # woningen naast elkaar sneuvelen juist in rustige straten.
        naam = "kamers, mits vergunning"

    # Duur ingekochte meters: verkameren afraden tenzij het pand het al is
    if duur_ingekocht and not kamerpand:
        # Splitsen als dat meer oplevert
        if sp and sp["maand"] > max(maand_w, maand_k):
            return sp
        # Alleen terugvallen op één huishouden als dat ook realistisch is.
        # Een pand van 367 m2 verhuur je niet aan een gezin voor €6.500.
        if geschikt_woning:
            return {"naam": "één woning", "huur_m2": huur_w, "maand": maand_w,
                    "opp": opp, "bron": bron_w,
                    "let_op": "prijs per m² ligt boven het gemiddelde van "
                              "vergelijkbaar grote panden"}
        # Te groot voor één huishouden: dan blijft kamers het scenario, met de
        # waarschuwing dat de meters duur zijn ingekocht.
        return {"naam": naam, "huur_m2": huur_k_m2, "maand": maand_k,
                "opp": verhuurbaar, "bron": bron_k,
                "let_op": "prijs per m² ligt boven het gemiddelde van "
                          "vergelijkbaar grote panden"}

    # Is verhuur aan een huishouden toch gunstiger, dan tonen we dat
    if geschikt_woning and maand_w >= maand_k:
        return {"naam": "één woning", "huur_m2": huur_w, "maand": maand_w,
                "opp": opp, "bron": bron_w}

    # Bij grote panden is splitsen vaak het alternatief voor verkameren
    if sp and sp["maand"] > maand_k:
        return sp
    return {"naam": naam, "huur_m2": huur_k_m2, "maand": maand_k,
            "opp": verhuurbaar, "bron": bron_k}



def financiering(prijs, netto_huur, renovatie=0):
    """
    Rekent een aankoop door zoals een financier dat zou doen.

    Gescheiden waar het gescheiden hoort: aflossing is geen kostenpost maar
    vermogensopbouw, dus het operationeel resultaat is de nettohuur min de
    rente. De aflossing komt daarna apart, want die verlaat je rekening wel
    maar verdwijnt niet uit je vermogen.

    De lening is het laagste van twee grenzen: de financieringsgraad en wat de
    rentedekking toelaat. Bij de huidige rente knelt die tweede meestal eerder.
    """
    op_ltv = prijs * LTV / 100
    op_dekking = (netto_huur / DEKKINGSEIS / (RENTE / 100)) if netto_huur else 0
    lening = min(op_ltv, op_dekking) if op_dekking else op_ltv
    knelpunt = "rentedekking" if op_dekking and op_dekking < op_ltv else "financieringsgraad"

    ovb = prijs * OVERDRACHTSBELASTING_PCT / 100
    bijkomend = prijs * BIJKOMENDE_KOSTEN_PCT / 100

    # Verbouwing en aanloop komen uit eigen vermogen: de bank financiert ze
    # bij verhuurd vastgoed doorgaans niet mee.
    aanloop = aanloopverlies(lening, netto_huur)
    investering = prijs + ovb + bijkomend + renovatie + aanloop["rente"]
    eigen = investering - lening

    rente = lening * RENTE / 100
    jaarlast = lening * jaarlast_factor()
    aflossing = jaarlast - rente

    operationeel = netto_huur - rente          # wat het pand echt oplevert
    na_aflossing = operationeel - aflossing    # wat er van je rekening af gaat

    return {
        "lening": lening, "knelpunt": knelpunt,
        "ovb": ovb, "bijkomend": bijkomend,
        "renovatie": renovatie,
        "aanloop_rente": aanloop["rente"],
        "gemiste_huur": aanloop["gemiste_huur"],
        "investering": investering, "eigen": eigen,
        "rente": rente, "aflossing": aflossing, "jaarlast": jaarlast,
        "operationeel": operationeel, "na_aflossing": na_aflossing,
        "bar": netto_huur / (1 - 0) / prijs * 100 if prijs else 0,
        # Netto aanvangsrendement: nettohuur over de totale investering. Dit is
        # waar taxateurs en beleggers op vergelijken, niet op de koopsom alleen.
        "nar": netto_huur / investering * 100 if investering else 0,
        "op_eigen": operationeel / eigen * 100 if eigen > 0 else 0,
        "dekking": netto_huur / rente if rente else 0,
    }


def max_koopsom_bij_budget(netto_huur, budget=None, renovatie=0):
    """
    Hoeveel kun je maximaal kopen met het eigen vermogen dat je hebt?

    Twee grenzen: het budget zelf, en wat de bank op deze huur wil lenen.
    De strengste wint. Zonder budget geven we niets terug.
    """
    budget = EIGEN_VERMOGEN if budget is None else budget
    if not budget:
        return None
    # Verbouwing gaat er als eerste af: dat geld is weg voordat je koopt
    budget = budget - renovatie
    if budget <= 0:
        return {"max": 0, "knelpunt": "verbouwing die het budget al opslokt"}
    kosten = (OVERDRACHTSBELASTING_PCT + BIJKOMENDE_KOSTEN_PCT) / 100

    # Grens 1: de financieringsgraad. eigen = K(1 + kosten - LTV)
    noemer = 1 + kosten - LTV / 100
    via_ltv = budget / noemer if noemer > 0 else 0

    # Grens 2: de rentedekking. De lening staat dan vast op de huur.
    via_dekking = None
    if netto_huur:
        lening = netto_huur / DEKKINGSEIS / (RENTE / 100)
        via_dekking = (budget + lening) / (1 + kosten)

    if via_dekking is None:
        return {"max": via_ltv, "knelpunt": "financieringsgraad"}
    if via_dekking < via_ltv:
        return {"max": via_dekking, "knelpunt": "rentedekking"}
    return {"max": via_ltv, "knelpunt": "financieringsgraad"}


def richtprijs(opp, huur_m2, opex=None):
    """
    De hoogste koopsom waarbij het pand nog de gewenste cashflow haalt.

    De nettohuur moet de jaarlast op de lening dekken plus DOEL_CASHFLOW:
        huur * 12 * m2 * (1 - opex)  -  K * LTV% * jaarlastfactor  >=  doel

    Wat er NIET in zit: renovatie om de huur te halen, en de vraag of het
    puntenstelsel die huur toestaat. Beide verlagen dit plafond.
    """
    if not opp or not huur_m2:
        return None
    netto = huur_m2 * 12 * opp * (1 - (OPEX_PCT if opex is None else opex) / 100)
    noemer = (LTV / 100) * jaarlast_factor()
    if noemer <= 0:
        return None
    plafond = (netto - DOEL_CASHFLOW) / noemer
    return plafond if plafond > 0 else None


def eigen_inleg(koopsom):
    """Eigen geld: het niet-gefinancierde deel plus de aankoopkosten."""
    return koopsom * (1 - LTV / 100) + koopsom * AANKOOPKOSTEN_PCT / 100


def huur_voor_buurt(buurt, huur_bk, huur_k, opp=None, klasse="woning"):
    """
    Gemeten huur per m2.

    Grootte en buurt verklaren allebei een deel van de spreiding, en ze los van
    elkaar gebruiken gaat mis: de grootteklasse wordt gevuld met panden uit
    duurdere buurten, en de buurt zelf heeft vaak te weinig waarnemingen om op
    grootte te splitsen. Daarom nemen we de grootteklasse als vorm en schalen
    die naar het niveau van de buurt.
    """
    band = groottebandje(opp)
    band_reeks = huur_k.get((klasse, band), [])
    buurt_reeks = huur_bk.get((klasse, buurt), [])
    stad_reeks = huur_k.get(klasse, [])

    # Buurtniveau ten opzichte van de stad, alleen bij genoeg waarnemingen
    factor, factor_bron = 1.0, ""
    if len(buurt_reeks) >= 2 and len(stad_reeks) >= 5:
        factor = st.median(buurt_reeks) / st.median(stad_reeks)
        factor = max(0.7, min(1.4, factor))  # extreme uitslagen dempen
        factor_bron = f", geschaald naar {buurt} ({factor:.2f}x)"

    if len(band_reeks) >= 3:
        return (st.median(band_reeks) * factor,
                f"gemeten, {len(band_reeks)} panden {band}{factor_bron}")

    if len(buurt_reeks) >= 3:
        return st.median(buurt_reeks), f"gemeten, {len(buurt_reeks)} in {buurt}"

    if len(stad_reeks) >= 3:
        return st.median(stad_reeks) * factor, f"gemeten, {len(stad_reeks)} stadsbreed{factor_bron}"

    return HUUR_M2_MND.get(buurt, 18), "aanname"



WOZ_PAD = "woz.txt"


def _woz_sleutel(adres):
    """Adressen matchen ongeacht punten, spaties en afkortingen."""
    a = adres.lower()
    a = a.replace("professor ", "prof").replace("prof. ", "prof")
    a = a.replace("burgemeester ", "burg").replace("burg. ", "burg")
    a = a.replace("sint ", "st").replace("st. ", "st")
    return re.sub(r"[^a-z0-9]", "", a)


def lees_woz():
    """
    Handmatig ingevoerde WOZ-waarden. Formaat per regel: adres | woz | jaar.
    Het jaar is de waardepeildatum, want de WOZ wordt jaarlijks opnieuw
    vastgesteld; zonder jaartal weet je later niet of een bedrag nog klopt.

    De WOZ is niet vrij op te vragen: de officiele API van het Kadaster vereist
    een organisatiecertificaat. Zoek een pand op via wozwaardeloket.nl.
    Regels waar nog geen bedrag in staat worden overgeslagen.
    """
    if not os.path.exists(WOZ_PAD):
        return {}
    uit = {}
    try:
        with open(WOZ_PAD, encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if not regel or regel.startswith("#"):
                    continue
                delen = [d.strip() for d in regel.split("|")]
                if len(delen) < 2:
                    continue
                bedrag = re.sub(r"[^\d]", "", delen[1])
                if not bedrag or int(bedrag) < 10_000:
                    continue   # nog niet ingevuld
                jaar = None
                if len(delen) > 2:
                    j = re.sub(r"[^\d]", "", delen[2])
                    if len(j) == 4:
                        jaar = int(j)
                uit[_woz_sleutel(delen[0])] = {"woz": int(bedrag), "jaar": jaar}
    except Exception:
        return {}
    return uit


def woz_van(w, woz_tabel):
    """De bekende WOZ, anders None."""
    return woz_tabel.get(_woz_sleutel(w["adres"]))


def vul_woz_aan(kandidaten, woz_tabel):
    """
    Zet grensgevallen als lege regel in het WOZ-bestand, zodat er alleen nog
    een bedrag ingevuld hoeft te worden. Alleen panden waar de WOZ het verschil
    maakt tussen wel en niet mogen verhuren.
    """
    ontbreekt = []
    for k in kandidaten:
        w = k[-1]
        if woz_van(w, woz_tabel):
            continue
        if opkoop_signaal(w) != "grensgeval":
            continue
        ontbreekt.append(w["adres"])
    if not ontbreekt:
        return 0
    jaar = dt.date.today().year
    try:
        with open(WOZ_PAD, "a", encoding="utf-8") as f:
            f.write(f"\n# Toegevoegd op {dt.date.today().isoformat()}: "
                    f"grensgevallen, vul het bedrag in via wozwaardeloket.nl\n")
            for adres in sorted(set(ontbreekt)):
                f.write(f"{adres} |  | {jaar}\n")
        print(f"{len(set(ontbreekt))} grensgevallen toegevoegd aan {WOZ_PAD}",
              file=sys.stderr)
    except Exception as e:
        print(f"Kon {WOZ_PAD} niet aanvullen: {e}", file=sys.stderr)
    return len(set(ontbreekt))


def opkoop_signaal(w):
    """
    Valt dit pand onder de opkoopbescherming? De WOZ kennen we niet, maar de
    vraagprijs ligt vrijwel altijd boven de WOZ. Ligt de vraagprijs al onder de
    grens, dan de WOZ vrijwel zeker ook.

    Uitzondering die er in de praktijk het meest toe doet: koop je een pand dat
    al verhuurd wordt en in verhuurde staat wordt geleverd, dan mag je de
    verhuur voortzetten. Wordt het leeg opgeleverd, dan niet. Voor panden met
    een kamerverhuurvergunning geldt daarbij de eis van minstens zes maanden
    verhuur voorafgaand aan de levering.
    """
    prijs = w["prijs"] if isinstance(w, dict) else w
    # Kennen we de echte WOZ, dan toetsen we daarop en is er geen marge nodig:
    # de grens is dan hard in plaats van een schatting op de vraagprijs.
    zeker = isinstance(w, dict) and bool(w.get("woz"))
    if zeker:
        prijs = w["woz"]
    verhuurd = (isinstance(w, dict)
                and (w.get("status") or "").lower() == "belegging")

    if prijs >= OPKOOPBESCHERMING_WOZ * (1.0 if zeker else 1.25):
        return "vrij"
    if verhuurd:
        return "voortzetting"
    if prijs < OPKOOPBESCHERMING_WOZ:
        return "beschermd"
    return "grensgeval"


def verkameren_signaal(prijs):
    """
    Richtinggevende zeef op basis van de vraagprijs. De WOZ zelf is niet vrij
    op te vragen, maar de vraagprijs ligt vrijwel altijd boven de WOZ. Een
    vraagprijs onder de ondergrens betekent dus vrijwel zeker een WOZ eronder.
    """
    if prijs < WOZ_ONDERGRENS:
        return "niet toegestaan"
    if prijs < WOZ_BOVENGRENS * 1.25:
        return "omzettingsvergunning nodig"
    # Boven de bovengrens is geen omzettingsvergunning nodig; de omgevings-
    # vergunning voor drie of meer kamers blijft wel gelden.
    return "geen omzettingsvergunning nodig"


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


def pct(x, cijfers=2):
    """Percentage met een komma, zoals het in het Nederlands hoort."""
    return f"{x:.{cijfers}f}".replace(".", ",").rstrip("0").rstrip(",")


def eu(x):
    """Bedrag met punten als duizendtalscheiding."""
    return f"{int(x):,}".replace(",", ".")



def eerste_datum(w):
    """
    Sinds wanneer kennen we dit pand?

    Kijkt eerst naar datum_eerst, dat alleen wordt gezet bij meerdere
    waarnemingen. Ontbreekt dat, dan naar de historie, en anders naar de datum
    van de waarneming zelf. Zonder deze volgorde blijft "dagen te koop" leeg
    bij panden die we maar een keer hebben gezien, terwijl ze er wel staan.
    """
    if w.get("datum_eerst"):
        return w["datum_eerst"]
    historie = w.get("historie") or []
    for h in historie:
        if h.get("datum"):
            return h["datum"]
    return w.get("datum") or ""


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
    inclusief_weg = 0
    for w in huur_aanbod:
        # Alleen kale huur telt. Servicekosten zijn doorbelasting van werkelijke
        # kosten waar geen rendement uit komt, en het puntenstelsel toetst er
        # ook niet op. Advertenties met een bedrag inclusief vaste lasten laten
        # we daarom weg in plaats van er een aftrek op te verzinnen.
        if (w.get("bron") or "").endswith("incl"):
            inclusief_weg += 1
            continue

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
    if inclusief_weg:
        print(f"Huur: {inclusief_weg} advertenties inclusief vaste lasten weggelaten",
              file=sys.stderr)
        per_klasse["_inclusief_weggelaten"] = inclusief_weg
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

Bouw het memo zo op:
1. Waarom valt dit pand op en wat zeggen de cijfers over de positie in de markt.
2. Wat kost het en wat brengt het op bij de huidige rente: investering, eigen inleg, operationeel resultaat, netto aanvangsrendement.
3. Wat de meest voor de hand liggende route is naar meer huur of waarde.
4. OF HET UITVOERBAAR IS. Dit is geen bijzaak maar de kern van een investeringsvoorstel. Behandel: ligt er al een vergunning op het pand, zijn er kamerverhuurpanden in de straat en welke adressen, welke voorwaarden gelden er voor een omzettingsvergunning, staat er iets aan handhaving in de omgeving, en hoe staat het met veiligheid en overlast in de buurt. Noem de adressen en de cijfers die je krijgt aangeleverd; schrijf niet "mogelijk vergunningplichtig" als er concrete gegevens bij staan.
5. Sluit af met een oordeel in een of twee zinnen: is dit het bekijken waard, en wat zou je als eerste uitzoeken voordat je een bod doet.

LENGTE: maximaal 450 woorden per pand. Dat is een harde grens. Je krijgt veel meer feiten aangeleverd dan erin passen, en dat is opzet: kies.

WAT ALTIJD MOET: de cijfers die het oordeel dragen, en elke blokkade. Loopt een route vast op de opkoopbescherming, op de WOZ-ondergrens of op twee kamerpanden naast elkaar, dan hoort dat erin, ook als de rest goed oogt.

WAT MAG WEGVALLEN: gronden waar niets aan de hand is, cijfers die het oordeel niet veranderen, en achtergrond die in elke case hetzelfde zou zijn. Een opsomming van tien weigeringsgronden waarvan er negen in orde zijn, is geen analyse maar een afvinklijst.

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
    from bouwkosten_index import indexfactor, omschrijf as omschrijf_index
except Exception:  # noqa
    indexfactor = omschrijf_index = None

try:
    from ov_haltes import dichtstbijzijnde_halte, omschrijf as omschrijf_halte
except Exception:  # noqa
    dichtstbijzijnde_halte = omschrijf_halte = None

try:
    from bronnen import verwijs
except Exception:  # noqa
    def verwijs(*_namen):
        return ""

try:
    from toets_artikel15 import (toets_kamerverhuur, toets_splitsing,
                                 samenvatting as toets_samenvatting)
except Exception:  # noqa
    toets_kamerverhuur = toets_splitsing = toets_samenvatting = None

try:
    from wwso import wwso_bandbreedte, wws_punten, wws_max_huur
except Exception:  # noqa
    wwso_bandbreedte = None
    wws_punten = None
    wws_max_huur = None


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
                     f"€{eu(w['prijs'])}{merk} | €{eu(b['laag'])} tot €{eu(b['hoog'])} |")
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

        # Dezelfde rekenwijze als de dagelijkse brief, inclusief verbouwing en
        # aanloopperiode, zodat de twee elkaar niet tegenspreken.
        reno_uit = renovatiekosten(opp, w.get("energielabel"), uitsplitsen=True)
        reno = reno_uit["totaal"]
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
        # Het scenario bepaalt de exploitatiekosten: kamerverhuur kost meer aan
        # onderhoud, mutaties en beheer dan verhuur aan een huishouden.
        # In de zondagsbrief is _scenario niet gevuld, dus berekenen we het hier.
        sc_case = (w.get("_scenario")
                   or kies_scenario(w, huur_bk, huur_k, buurt, None,
                                    per_buurt.get(buurt, [])))
        sc_naam = (sc_case or {}).get("naam", "één woning")
        opex = opex_voor(sc_naam)

        # Splitsen kent een heel ander regime dan kamerverhuur: artikel 15 gaat
        # over omzetting naar onzelfstandige woonruimte en geldt daar niet.
        if toets_splitsing and "splitsen" in sc_naam.lower():
            regels_s = toets_splitsing(w, aantal_units=(sc_case or {}).get("aantal"))
            f.append("TOETS splitsing, " + toets_samenvatting(regels_s))
            for grond, oordeel, toel in regels_s:
                f.append(f"  {grond}: {oordeel}. {toel}")

        # Bij een pand in verhuurde staat: huidige huur naast het maximum
        hp_case = huurpositie(w, sc_case, lees_huidige_huur())
        if hp_case:
            f.append(f"huidige huurstroom: €{n(hp_case['nu'])} per jaar"
                     + (f" over {hp_case['eenheden']} eenheden"
                        if hp_case.get("eenheden") else ""))
            f.append(f"wettelijk maximum volgens het puntenstelsel: "
                     f"€{n(hp_case['maximaal'])} per jaar; het verschil van "
                     f"€{n(hp_case['ruimte'])} komt vrij bij mutatie")
        netto = jaarhuur * (1 - opex / 100)
        fin = financiering(prijs, netto, reno)
        lening, rentelast = fin["lening"], fin["rente"]
        jaarlast, aflossing = fin["jaarlast"], fin["aflossing"]
        ovb, bijkomend, eigen = fin["ovb"], fin["bijkomend"], fin["eigen"]
        cashflow = fin["na_aflossing"]
        f += [f"financiering: lening €{n(lening)}, begrensd door de {fin['knelpunt']} "
              f"(financieringsgraad {LTV:.0f}%, dekkingseis {DEKKINGSEIS}x)",
              f"verbouwing: €{n(reno)} totaal. Opbouw: "
              f"{opp} m2 x €{reno_uit['per_m2_verduurzaming']}/m2 = "
              f"€{n(reno_uit['verduurzaming'])} verduurzaming bij label "
              f"{_labeltekst(w.get('energielabel'))}, plus "
              f"{opp} m2 x €{reno_uit['per_m2_verhuurklaar']}/m2 = "
              f"€{n(reno_uit['verhuurklaar'])} verhuurklaar maken. "
              + _herkomst_verbouwing(reno_uit) + " "
              f"Asbest, funderingsherstel en slechte bouwkundige staat zitten er niet "
              f"in en de werkelijke kosten wijken 20 tot 30% af. Komt uit eigen "
              f"vermogen, want banken financieren verbouwing bij verhuurd vastgoed "
              f"doorgaans niet mee. Subsidie loopt voor een particuliere verhuurder "
              f"via SVOH, niet via ISDE",
              f"aanloop: {AANLOOPMAANDEN} maanden zonder huur, kost €{n(fin['aanloop_rente'])} "
              f"aan rente en €{n(fin['gemiste_huur'])} aan gemiste huur",
              f"eigen vermogen: €{n(prijs - lening)} niet gefinancierd, plus "
              f"€{n(ovb)} overdrachtsbelasting ({OVERDRACHTSBELASTING_PCT}%), "
              f"€{n(bijkomend)} notaris, makelaar en taxatie "
              f"({BIJKOMENDE_KOSTEN_PCT}%), €{n(reno)} verbouwing en "
              f"€{n(fin['aanloop_rente'])} aanlooprente, samen €{n(eigen)} in te leggen",
              f"rente: {pct(RENTE)}%, rentelast €{n(rentelast)} per jaar",
              f"aflossing: over {LOOPTIJD_JAAR} jaar annuitair, €{n(aflossing)} per jaar"
              if LOOPTIJD_JAAR else "aflossing: geen, aflossingsvrij",
              f"totale jaarlast op de lening: €{n(jaarlast)}",
              f"huur per m2 per maand: €{huur_m2:.0f} ({bron_huur})",
              f"kale huur: €{n(jaarhuur)} per jaar, na {opex}% exploitatiekosten "
              f"€{n(netto)}. Dat percentage hoort bij het scenario {sc_naam} en "
              f"dekt groot onderhoud, verzekering, gemeentelijke lasten, beheer, "
              f"leegstand en mutatie. Gas, water, licht en schoonmaak van "
              f"gemeenschappelijke ruimten zitten er niet in: die worden via de "
              f"servicekosten doorbelast en drukken dus niet op het rendement. "
              f"Het is een aanname, geen gemeten cijfer",
              f"operationeel resultaat: nettohuur min rente is "
              f"€{n(fin['operationeel'])} per jaar",
              f"aflossing: €{n(aflossing)} per jaar, geen kosten maar vermogensopbouw",
              f"onder de streep: "
              f"€{n(cashflow) if cashflow >= 0 else '-' + n(abs(cashflow))} per jaar",
              f"bruto aanvangsrendement over de koopsom: {jaarhuur / prijs * 100:.1f}%",
              f"netto aanvangsrendement over de totale investering van "
              f"€{n(fin['investering'])}: {fin['nar']:.1f}%",
              f"operationeel rendement op eigen vermogen: {fin['op_eigen']:.1f}%"
              if eigen > 0 else ""]
        f = [x for x in f if x]
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

        # Wat bepaalt of je dit plan ook mág uitvoeren
        vergunningen_c = lees_kamervergunningen()
        archief_c = lees_archief()

        m_adres = re.match(r"^(.+?)\s+(\d+)", w["adres"])
        if m_adres:
            straat_c, nr_c = m_adres.group(1), int(m_adres.group(2))
            eigen_v = vergunningen_c.get(archief_sleutel(straat_c, str(nr_c)), [])
            if eigen_v:
                f.append(f"vergunning op dit pand: {eigen_v[0].get('soort')} uit "
                         f"{eigen_v[0].get('datum', '')[:4]}, dat scheelt een traject")
            else:
                f.append("vergunning op dit pand: niet in de gemeentelijke lijst "
                         "vanaf 2013; kan ouder zijn of niet vereist")

            # Kamerverhuur in de directe omgeving: bepaalt of omzetting nog mag
            buren_v = []
            for offset in range(-5, 6):
                if offset == 0:
                    continue
                for v in vergunningen_c.get(archief_sleutel(straat_c,
                                                            str(nr_c + offset)), []):
                    buren_v.append(f"{v.get('adres')} ({v.get('soort')}, "
                                   f"{v.get('datum','')[:4]})")
                    break
            # Ook de hele straat tellen: de directe buren bepalen of omzetting
            # nog mag, maar het aantal in de straat zegt iets over hoe verzadigd
            # het gebied is en dus over de leefbaarheidstoets.
            straat_norm = _verg_straat(straat_c)
            in_straat = []
            for lijst_v in vergunningen_c.values():
                for v in lijst_v:
                    m_v = re.match(r"^(.+?)\s+(\d+)", v.get("adres", ""))
                    if m_v and _verg_straat(m_v.group(1)) == straat_norm:
                        in_straat.append((int(m_v.group(2)), v))
                        break
            in_straat.sort()

            if buren_v:
                f.append(f"kamerverhuur naast dit pand: {', '.join(buren_v[:6])}. "
                         f"Nijmegen staat niet meer dan twee direct naast, onder of "
                         f"boven elkaar gelegen kamergewijs bewoonde woningen toe")
            else:
                f.append("kamerverhuur naast dit pand: geen vergunningen op de "
                         "buurpanden in de lijst vanaf 2013")

            if in_straat:
                nummers = ", ".join(str(nr) for nr, _v in in_straat[:12])
                jaren_v = sorted({v.get("datum", "")[:4] for _nr, v in in_straat
                                  if v.get("datum")})
                f.append(f"in de hele {straat_c} "
                         + ("is sinds 2013 1 vergunning verleend"
                            if len(in_straat) == 1 else
                            f"zijn sinds 2013 {len(in_straat)} vergunningen verleend")
                         + f", op nummer {nummers}"
                         + (f" ({jaren_v[0]} tot {jaren_v[-1]})" if jaren_v else "")
                         + ". Hoe voller de straat, hoe zwaarder de "
                           "leefbaarheidstoets weegt")
            else:
                f.append(f"in de hele {straat_c} staat geen enkele vergunning in de "
                         f"lijst vanaf 2013. Dat betekent niet dat er geen "
                         f"kamerverhuur is: oudere vergunningen en panden met een WOZ "
                         f"boven de grens staan er niet in")

            # Handhaving op of rond het pand
            hh = handhaving_op_adres(w["adres"], archief_c, straal=3)
            if hh:
                f.append("handhaving in de omgeving: " + "; ".join(
                    f"{t['adres']} {t['soort']} {t['datum']}" for t in hh[:4]))

        # Voorwaarden die een omzettingsvergunning in de weg kunnen staan
        if "kamer" in (sc_naam or "").lower():
            # Puntsgewijze toets in plaats van een opsomming van de regels
            if toets_kamerverhuur:
                kamers_n = None
                if sc_case and sc_case.get("opp"):
                    kamers_n = max(2, round(sc_case["opp"] / 22))
                regels_t = toets_kamerverhuur(w, aantal_kamers=kamers_n,
                                              vergunningen=vergunningen_c,
                                              woz=w.get("woz"))
                f.append("TOETS artikel 15, " + toets_samenvatting(regels_t))
                for grond, oordeel, toel in regels_t:
                    f.append(f"  {grond}: {oordeel}. {toel}")

            f.append("weigeringsgronden omzettingsvergunning, Huisvestingsverordening "
                     "Nijmegen 2024 artikel 15. Altijd geweigerd bij een WOZ van "
                     f"€{n(WOZ_ONDERGRENS)} of minder, en bij strijd met het "
                     "omgevingsplan zonder omgevingsvergunning")
            f.append("kan verder geweigerd worden bij: onaanvaardbare geluidhinder, "
                     "waarbij het luchtgeluidniveauverschil volgens NEN 5077 niet "
                     "kleiner mag zijn dan 52 dB en het contactgeluidniveau niet "
                     "groter dan 54 dB; niet voldoen aan het Bouwbesluit voor "
                     "bestaande bouw, voor kamergewijze verhuur en voor brandveilig "
                     "gebruik; geen fietsenstalling op eigen terrein van 1,5 m2 per "
                     "bewoner, niet hoger dan de begane grond en in een afzonderlijke "
                     "daartoe bestemde ruimte; omzetting voor kortdurend verblijf "
                     "vergelijkbaar met logies; het insluiten van een naast, onder of "
                     "boven gelegen zelfstandig bewoonde woning; en meer dan twee "
                     "direct naast, onder of boven elkaar gelegen kamergewijs "
                     "bewoonde woningen")
            f.append("LET OP: de leefbaarheidstoets door de ambtelijke adviesgroep "
                     "vervalt. De gemeente trok op 9 september 2026 de Beleidsregels "
                     "omzetting en onttrekking 2021 in, omdat die toets vervalt en "
                     "goed verhuurderschap via de landelijke wet is geborgd. De "
                     "intrekking gaat in zodra de gewijzigde Huisvestingsverordening "
                     "2024 in werking treedt. De harde gronden hierboven blijven wel "
                     "staan")
            f.append("vanaf vijf kamers geldt daarnaast een melding brandveilig "
                     f"gebruik; boete bij omzetten zonder vergunning is €10.000 "
                     f"bij bedrijfsmatige exploitatie, €15.000 bij herhaling")

        # Veiligheid en leefbaarheid van de buurt
        mis = lees_misdrijven().get(buurt)
        if mis:
            jaren_m = sorted(mis)
            laatst_m = mis[jaren_m[-1]]
            delen_m = []
            for soort in ("woninginbraak", "vernieling", "drugs- en drankoverlast"):
                n_m = laatst_m.get(soort)
                if n_m is not None and g.get("inwoners"):
                    delen_m.append(f"{soort} {n_m} "
                                   f"({n_m / g['inwoners'] * 1000:.1f} per 1000)")
            if delen_m:
                f.append(f"veiligheid in {buurt} in {jaren_m[-1][:4]}: "
                         + ", ".join(delen_m)
                         + ". Dit woog in de leefbaarheidstoets, die vervalt, maar "
                           "het blijft relevant voor de verhuurbaarheid en voor wat "
                           "een pand bij verkoop opbrengt")

        gezicht_c = gezichtswaarschuwing(buurt)
        if gezicht_c:
            f.append(f"{buurt} is {gezicht_c}: wijzigingen aan het uiterlijk zijn "
                     f"vergunningplichtig, wat gevelisolatie, kozijnen en "
                     f"zonnepanelen aan de voorzijde raakt")

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
                         f"dezelfde buurten voor mediaan €{eu(bel_med)}/m², tegen "
                         f"€{eu(voh_med)}/m² vrij van huurder. Dat verschil van "
                         f"€{eu(marge)}/m² is de ruimte die uitponden oplevert, "
                         f"gerekend op {len(beleggingen)} beleggingen en {len(voh)} "
                         f"verkopen._")
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



GEZIEN_PAD = "brief_gezien.json"


def lees_gezien():
    """Wat er eerder in de brief heeft gestaan, om herhaling te beperken."""
    if not os.path.exists(GEZIEN_PAD):
        return {}
    try:
        with open(GEZIEN_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def schrijf_gezien(gezien):
    try:
        with open(GEZIEN_PAD, "w", encoding="utf-8") as f:
            json.dump(gezien, f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Kon {GEZIEN_PAD} niet schrijven: {e}", file=sys.stderr)


def _pandsleutel(w):
    return re.sub(r"[^a-z0-9]", "", w["adres"].lower())


def is_nieuw_of_gewijzigd(w, gezien):
    """
    Een pand krijgt de volle behandeling zolang het nieuw is of net veranderd,
    en daarna alleen nog een regel. Zo blijft de brief te lezen zonder dat er
    iets uit beeld verdwijnt.
    """
    sleutel = _pandsleutel(w)
    eerder = gezien.get(sleutel)
    if not eerder:
        return True, "nieuw"
    if eerder.get("prijs") != w["prijs"]:
        return True, "prijs gewijzigd"
    if eerder.get("status") != (w.get("status") or ""):
        return True, "status gewijzigd"
    return False, ""


def werk_gezien_bij(w, gezien):
    gezien[_pandsleutel(w)] = {
        "adres": w["adres"],
        "prijs": w["prijs"],
        "status": w.get("status") or "",
        "laatst": dt.date.today().isoformat(),
    }




# Verhuurders eisen doorgaans dat het jaarinkomen minstens drie keer de
# jaarhuur is. De huur mag dan hooguit een derde van het inkomen zijn.
INKOMENSNORM = 3.0



# ---------------------------------------------------------------------------
# HUURTOESLAG 2026
# Bedragen per 1 januari 2026. Jaarlijks controleren op rijksoverheid.nl.
#
# Twee wijzigingen in 2026 die ertoe doen: er is geen huurtoeslag meer over
# servicekosten, dus alleen de kale huur telt. En de maximale huurgrens is geen
# harde voorwaarde meer; boven die grens blijft een gedeeltelijke vergoeding
# mogelijk, maar de toeslag wordt tot die grens berekend.
# ---------------------------------------------------------------------------
HT_MAX_HUUR = 932.93          # grens waarover toeslag wordt berekend
HT_KWALITEITSKORTING = 498.20
HT_AFTOPPING_LAAG = 713.02    # een- en tweepersoonshuishoudens
HT_AFTOPPING_HOOG = 764.14    # drie personen of meer
HT_VERMOGEN_ALLEEN = 38_479
HT_VERMOGEN_PARTNERS = 76_958


def huurtoeslag_positie(maandhuur, meerpersoons=False):
    """
    Waar valt deze kale huur in het huurtoeslagstelsel? Dat bepaalt hoe groot
    je huurderspoule is: onder de aftoppingsgrens is de groep die toeslag
    krijgt het grootst, erboven dunt hij snel uit.
    """
    if not maandhuur:
        return None
    aftopping = HT_AFTOPPING_HOOG if meerpersoons else HT_AFTOPPING_LAAG
    if maandhuur <= HT_KWALITEITSKORTING:
        segment = "onder de kwaliteitskortingsgrens"
        uitleg = ("volledige vergoeding over dit deel, maar je laat huur liggen "
                  "die de huurder toch vergoed zou krijgen")
    elif maandhuur <= aftopping:
        segment = "tussen kwaliteitskorting en aftoppingsgrens"
        uitleg = ("hier is de huurderspoule het grootst: 65% van dit deel wordt "
                  "vergoed en corporaties wijzen tot deze grens passend toe")
    elif maandhuur <= HT_MAX_HUUR:
        segment = "tussen aftoppings- en maximumgrens"
        uitleg = ("boven de aftoppingsgrens wordt nog 40% vergoed, dus de huurder "
                  "draagt zelf fors bij en de groep dunt uit")
    else:
        segment = "boven de maximale rekenhuur"
        uitleg = ("de toeslag wordt tot €932,93 berekend; daarboven betaalt de "
                  "huurder alles zelf, dus je richt je op huurders zonder toeslag")
    return {"segment": segment, "uitleg": uitleg, "aftopping": aftopping,
            "boven_aftopping": maandhuur > aftopping}



# ---------------------------------------------------------------------------
# BESCHERMD STADSGEZICHT
#
# Nijmegen kent twee rijksbeschermde stadsgezichten: de Benedenstad en de
# negentiende-eeuwse schil rond de binnenstad. Daarnaast acht gemeentelijke
# beschermde stadsbeelden. In zo'n gebied is voor wijzigingen aan het uiterlijk
# een omgevingsvergunning nodig, ook bij panden die zelf geen monument zijn.
#
# De grenzen volgen niet de buurtgrenzen, dus dit is een waarschuwing en geen
# uitsluitsel. Controleer per pand in de monumentenlijst van de gemeente.
# ---------------------------------------------------------------------------
BESCHERMD_GEZICHT = {
    "Benedenstad": "rijksbeschermd stadsgezicht Benedenstad",
    "Stadscentrum": "grotendeels rijksbeschermd stadsgezicht",
    "Bottendaal": "deels de negentiende-eeuwse schil",
    "Galgenveld": "deels de negentiende-eeuwse schil",
    "Altrade": "deels de negentiende-eeuwse schil",
}


def gezichtswaarschuwing(buurt):
    """Ligt deze buurt in of tegen een beschermd stadsgezicht?"""
    return BESCHERMD_GEZICHT.get(buurt, "")


def past_bij_buurt(sc, cbs_buurt):
    """
    Past het doorgerekende scenario bij het huishoudenstype in deze buurt?

    Niet het aantal kamers is de vraag, maar of de eenheid aansluit bij wie er
    woont. Een kleine eenheid in een buurt met veel alleenwonenden verhuurt
    zichzelf; een grote woning in zo'n buurt zoekt langer naar een huurder.
    """
    if not sc or not cbs_buurt:
        return ""
    alleen = cbs_buurt.get("eenpersoons")
    gezin = cbs_buurt.get("met_kinderen")
    if alleen is None:
        return ""
    opp_per_eenheid = sc.get("unit_m2") or sc.get("opp")
    naam = (sc.get("naam") or "").lower()
    if "kamer" in naam:
        return ""   # kamerverhuur richt zich per definitie op alleenwonenden

    if opp_per_eenheid and opp_per_eenheid < 60 and alleen >= 55:
        return (f"past bij de buurt: {alleen}% woont hier alleen, en dit is een "
                f"kleine zelfstandige eenheid")
    if opp_per_eenheid and opp_per_eenheid >= 100 and alleen >= 60:
        return (f"let op: {alleen}% van de huishoudens hier woont alleen en maar "
                f"{gezin if gezin is not None else '?'}% heeft kinderen. Voor een "
                f"woning van deze omvang is de lokale vraag dun")
    if opp_per_eenheid and opp_per_eenheid >= 100 and (gezin or 0) >= 20:
        return (f"past bij de buurt: {gezin}% van de huishoudens hier heeft "
                f"kinderen, en dit is een gezinswoning")
    return ""


def draagkracht(maandhuur, cbs_buurt):
    """
    Past de berekende huur bij wat er in deze buurt verdiend wordt?

    Het CBS geeft besteedbaar inkomen per inwoner. Vermenigvuldigd met de
    huishoudensgrootte geeft dat het gemiddelde huishoudinkomen terug, want zo
    is dat cijfer opgebouwd. Verhuurders toetsen op bruto inkomen; die
    omrekening laten we achterwege, dus dit is een strenge toets.
    """
    if not cbs_buurt or not maandhuur:
        return None
    inkomen_pp = cbs_buurt.get("inkomen")
    grootte = cbs_buurt.get("huishoudgrootte")
    if not inkomen_pp or not grootte:
        return None
    huishoudinkomen = inkomen_pp * 1000 * grootte
    jaarhuur = maandhuur * 12
    if huishoudinkomen <= 0:
        return None
    aandeel = jaarhuur / huishoudinkomen * 100
    nodig = jaarhuur * INKOMENSNORM
    return {
        "huishoudinkomen": huishoudinkomen,
        "aandeel": aandeel,
        "nodig": nodig,
        "haalbaar": aandeel <= 100 / INKOMENSNORM,
    }



def render_bijlage(woningen, per_buurt, stad_breed, huur_bk=None, huur_k=None):
    """
    De bijlage: cijfers in tabellen, zonder verhaal.

    De brief zelf legt uit wat er speelt. Deze bijlage is om in te kijken:
    per buurt de kengetallen op een rij, en daaronder elk pand dat wordt
    aangeboden met wat het kost en wat het volgens de rekensom waard is.
    """
    if huur_bk is None or huur_k is None:
        huur_bk, huur_k = gemeten_huren(
            [w for w in woningen
             if (w.get("status") or "").lower().startswith("te huur")])

    cbs = lees_cbs()
    verg = lees_vergunningen_per_buurt()
    mis = lees_misdrijven()
    trend = lees_trend()

    r = ["", "## De cijfers per buurt", ""]

    # Eerst een overzicht van alle buurten naast elkaar
    r.append("| Buurt | Woningen | Koop | Corporatie | WOZ | Studenten | "
             "Kamervergunningen | Mediaan €/m² |")
    r.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for buurt in sorted(per_buurt, key=lambda b: -len(per_buurt[b])):
        g = cbs.get(buurt) or {}
        rijen = per_buurt.get(buurt, [])
        med = st.median([p for p, _ in rijen]) if rijen else None
        r.append(
            f"| {buurt} | {eu(g['won']) if g.get('won') else '—'} "
            f"| {str(g.get('koop', '—')) + '%' if g.get('koop') is not None else '—'} "
            f"| {str(g.get('corp', '—')) + '%' if g.get('corp') is not None else '—'} "
            f"| {'€' + eu(g['woz'] * 1000) if g.get('woz') else '—'} "
            f"| {eu(g['studenten']) if g.get('studenten') else '—'} "
            f"| {verg.get(buurt, '—')} "
            f"| {'€' + eu(med) if med else '—'} |")
    r.append("")

    # Dan per buurt de panden
    for buurt in sorted(per_buurt, key=lambda b: -len(per_buurt[b])):
        panden = [w for _p, w in per_buurt.get(buurt, [])
                  if (w.get("status") or "").lower() not in ("verkocht", "transactie")]
        if not panden:
            continue

        r.append(f"### {buurt}")
        stukken = []
        t = trendregel(buurt, trend)
        if t:
            stukken.append(f"prijspeil {t}")
        m_b = mis.get(buurt)
        if m_b and (cbs.get(buurt) or {}).get("inwoners"):
            jaar = sorted(m_b)[-1]
            inw = cbs[buurt]["inwoners"]
            bruikbaar_b = _bruikbare_soorten(mis)
            per_soort = [f"{s} {v} ({v / inw * 1000:.1f}".replace(".", ",") + " per 1.000)"
                         for s, v in sorted(m_b[jaar].items())
                         if s in ("woninginbraak", "vernieling",
                                  "drugs- en drankoverlast")
                         and s in bruikbaar_b]
            if per_soort:
                stukken.append(f"misdrijven {jaar[:4]}: " + ", ".join(per_soort))
        if stukken:
            r.append("_" + " . ".join(stukken) + "._")
        r.append("")

        r.append("| Adres | Vraagprijs | m² | €/m² | Afwijking van de buurtmediaan "
                 "| Dagen te koop | OV | Scenario | Huur per maand | Richtprijs "
                 "| Richtprijs t.o.v. vraagprijs |")
        r.append("|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|")
        rijen_b = [(p, w) for p, w in per_buurt.get(buurt, [])
                   if w in panden]
        med_b = st.median([p for p, _ in per_buurt.get(buurt, [])]) if per_buurt.get(buurt) else None
        for ppm2, w in sorted(rijen_b, key=lambda x: x[0]):
            sc = w.get("_scenario") or kies_scenario(
                w, huur_bk, huur_k, buurt, None, per_buurt.get(buurt, []))
            plafond = (richtprijs(sc["opp"], sc["huur_m2"], opex_voor(sc["naam"]))
                       if sc else None)
            afw = ((ppm2 - med_b) / med_b * 100) if med_b else None
            verschil_s = (f"{(plafond - w['prijs']) / w['prijs'] * 100:+.0f}%"
                          if plafond else "—")
            r.append(
                f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} "
                f"| €{eu(w['prijs'])} | {w.get('oppervlakte') or '—'} | €{eu(ppm2)} "
                f"| {f'{afw:+.0f}%' if afw is not None else '—'} "
                + (f"| {_dagen_sinds(eerste_datum(w))} "
                   if eerste_datum(w) else "| — ")
                + (f"| {w['ov_halte']['meters']} m " if w.get("ov_halte") else "| — ")
                + f"| {sc['naam'] if sc else '—'} "
                f"| {'€' + eu(sc['maand']) if sc else '—'} "
                f"| {'€' + eu(plafond) if plafond else '—'} "
                f"| {verschil_s} |")
        r.append("")

    r.append(f"_Bronnen: buurtcijfers uit de Kerncijfers wijken en buurten, "
             f"vergunningen uit het gemeentelijk overzicht, misdrijven uit de "
             f"politiedata, vraagprijzen uit de attenderingen en huren uit de "
             f"gemeten advertenties. "
             f"{verwijs('Kerncijfers wijken en buurten', 'Kamerverhuurvergunningen', 'Politiedata', 'Aanbod', 'Huurniveaus')}_")
    r.append("")
    r.append("_Afwijking van de buurtmediaan vergelijkt de prijs per vierkante "
             "meter met vergelijkbare panden in die buurt; het is geen "
             "prijswijziging. Richtprijs is de hoogste koopsom waarbij de "
             "nettohuur rente en aflossing nog dekt. De laatste kolom zet die "
             "richtprijs af tegen de vraagprijs: positief betekent ruimte, "
             "negatief betekent te duur voor verhuur._")
    return r


def render_bieden(woningen, huur_bk, huur_k, per_buurt):
    """
    Panden die bij opbod worden aangeboden, zoals via Vendr. Er is geen
    vraagprijs, dus geen vergelijking met de mediaan. Wat we wel kunnen geven
    is het maximum dat je kunt bieden voordat het pand geld gaat kosten, en
    dat is bij een biedplatform precies het getal dat telt.
    """
    panden = [w for w in woningen
              if (w.get("status") or "").lower() == "bieden" and w.get("oppervlakte")]
    if not panden:
        return []

    r = ["", "### Bij opbod aangeboden", "",
         "_Geen vraagprijs, dus geen vergelijking met de markt. Wel het bedrag "
         "waarboven het pand geld gaat kosten._", ""]
    for w in sorted(panden, key=lambda x: -(x.get("oppervlakte") or 0)):
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or w.get("plaats", "")
        sc = kies_scenario(w, huur_bk, huur_k, buurt, None, per_buurt.get(buurt, []))
        if not sc:
            continue
        opex = opex_voor(sc["naam"])
        plafond = richtprijs(sc["opp"], sc["huur_m2"], opex)
        if not plafond:
            continue
        reno = renovatiekosten(w["oppervlakte"], w.get("energielabel"))
        # Verbouwing en kosten koper gaan van je maximale bod af
        kosten = (OVERDRACHTSBELASTING_PCT + BIJKOMENDE_KOSTEN_PCT) / 100
        max_bod = (plafond - reno) / (1 + kosten)

        regel = (f"**{kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))}**"
                 f" in {buurt}, {w['oppervlakte']} m²")
        lab = _labeltekst(w.get("energielabel"))
        if lab != "onbekend":
            regel += f", label {lab}"
        regel += (f". Als {sc['naam']} bij €{eu(sc['maand'])} huur per maand ligt de "
                  f"grens op €{eu(plafond)}. Na aftrek van €{eu(reno)} verbouwing en "
                  f"de kosten koper kun je tot ongeveer **€{eu(max_bod)}** bieden "
                  f"voordat het pand geld gaat kosten.")
        budget = max_koopsom_bij_budget(sc["maand"] * 12 * (1 - opex / 100),
                                        renovatie=reno)
        if budget and budget["max"] < max_bod:
            vraag = w.get("prijs") or 0
            if vraag and budget["max"] < 0.5 * vraag:
                regel += (" Met het ingestelde eigen vermogen is dit pand niet "
                          "haalbaar: de verbouwing, de kosten koper en het deel "
                          "boven de lening vragen samen meer dan er is.")
            else:
                regel += (f" Met het ingestelde eigen vermogen is de hoogste "
                          f"koopsom €{eu(budget['max'])}; daarboven is de eigen "
                          f"inleg groter dan het vermogen.")
        r.append(regel)
        r.append("")
    return r



# ---------------------------------------------------------------------------
# WAT VERDIENT AANDACHT
#
# Beleggingspanden komen met een huurstroom en vaak met een vergunning, dus
# daar zit het werk al in. Gewone koopwoningen vragen een heel traject en zijn
# vooral waardevol als vergelijkingsmateriaal. Ze komen alleen in beeld als er
# een concrete aanleiding is.
# ---------------------------------------------------------------------------
DREMPEL_SCHERP = -15      # procent onder de mediaan van de eigen klasse



def haalbare_routes(w, sc, vergunningen=None):
    """
    Welke routes staan voor dit pand open?

    Kamerverhuur en splitsen worden allebei getoetst, want een pand dat op
    artikel 15 vastloopt kan prima splitsbaar zijn, en omgekeerd. Gewone
    verhuur kan altijd, maar levert bij de huidige rente zo weinig op dat het
    op zichzelf geen reden is om een pand te tonen.

    Geeft terug welke routes vrij zijn en waarom de andere niet.
    """
    if not toets_kamerverhuur:
        return {"vrij": ["kamers", "splitsen"], "geblokkeerd": {}}

    vrij, geblokkeerd = [], {}
    opp = w.get("oppervlakte") or 0

    # Kamerverhuur is alleen zinvol bij voldoende oppervlak
    if opp >= 100:
        kamers_n = max(3, round(opp * VERHUURBAAR_AANDEEL / 22))
        regels = toets_kamerverhuur(w, aantal_kamers=kamers_n,
                                    vergunningen=vergunningen, woz=w.get("woz"))
        blok = [g for g, o, _t in regels if o == "voldoet niet"]
        if blok:
            geblokkeerd["kamers"] = ", ".join(blok)
        else:
            vrij.append("kamers")

    # Splitsen vraagt ruimte voor minstens twee eenheden
    if opp and opp * VERHUURBAAR_SPLITSING >= 2 * MIN_UNIT_M2:
        units = int(opp * VERHUURBAAR_SPLITSING // MIN_UNIT_M2)
        regels_s = toets_splitsing(w, aantal_units=units)
        blok_s = [g for g, o, _t in regels_s if o == "voldoet niet"]
        if blok_s:
            geblokkeerd["splitsen"] = ", ".join(blok_s)
        else:
            vrij.append("splitsen")

    return {"vrij": vrij, "geblokkeerd": geblokkeerd}


def verdient_aandacht(w, afwijking, archief=None, vergunningen=None):
    """
    Waarom zou dit pand vandaag je aandacht krijgen? Geeft de reden terug, of
    een lege tekst als er geen aanleiding is.
    """
    status = (w.get("status") or "").lower()

    # Beleggingspanden altijd: verhuurd, vaak met vergunning, minder werk
    if status == "belegging":
        return "beleggingspand, wordt in verhuurde staat aangeboden"

    # Een bestaande vergunning scheelt een heel traject
    m = re.match(r"^(.+?)\s+(\d+)", w["adres"])
    if m and vergunningen:
        eigen = vergunningen.get(archief_sleutel(m.group(1), m.group(2)), [])
        if eigen:
            return (f"heeft al een {eigen[0]['soort']}svergunning uit "
                    f"{eigen[0].get('datum', '')[:4]}")

    # Prijswijziging: de verkoper beweegt
    if w.get("prijs_eerst") and w["prijs"] < w["prijs_eerst"]:
        verschil = w["prijs_eerst"] - w["prijs"]
        return f"prijs verlaagd met €{eu(verschil)}"

    # Fors onder de markt: dan is het de moeite van het bekijken waard
    if afwijking is not None and afwijking <= DREMPEL_SCHERP:
        return f"{afwijking:+.0f}% onder de mediaan van zijn klasse"

    # Staat er nog een route open die waarde toevoegt? Zo niet, dan is dit
    # pand alleen nog vergelijkingsmateriaal en hoef je het niet te zien.
    routes = haalbare_routes(w, w.get("_scenario"), vergunningen)
    w["_routes"] = routes
    if routes["vrij"]:
        sc = w.get("_scenario") or {}
        if "splitsen" in routes["vrij"] and (sc.get("verkoopmarge") or 0) > 100_000:
            return (f"splitsen kan hier en levert op papier "
                    f"€{eu(sc['verkoopmarge'])} marge")
        if len(routes["vrij"]) == 2:
            return "zowel verkameren als splitsen staat open"
        return f"{routes['vrij'][0]} staat open als route"

    return ""



HUIDIGE_HUUR_PAD = "huidige_huur.txt"


def lees_huidige_huur():
    """
    Werkelijke jaarhuur van panden die in verhuurde staat worden aangeboden.
    Formaat per regel: adres | kale jaarhuur | aantal eenheden | peildatum

    Bij een pand in verhuurde staat neem je de bestaande contracten over. Die
    liggen vaak onder het maximum doordat er niet is geindexeerd. De huidige
    huur bepaalt dan je cashflow; het WWSO-maximum bepaalt je potentie bij
    mutatie. Het verschil is de ruimte die vrijkomt zodra een huurder vertrekt.
    """
    if not os.path.exists(HUIDIGE_HUUR_PAD):
        return {}
    uit = {}
    try:
        with open(HUIDIGE_HUUR_PAD, encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if not regel or regel.startswith("#"):
                    continue
                d = [x.strip() for x in regel.split("|")]
                if len(d) < 2:
                    continue
                bedrag = re.sub(r"[^\d]", "", d[1])
                if not bedrag:
                    continue
                uit[_woz_sleutel(d[0])] = {
                    "jaarhuur": int(bedrag),
                    "eenheden": int(re.sub(r"[^\d]", "", d[2]) or 0)
                                if len(d) > 2 else None,
                    "peildatum": d[3] if len(d) > 3 else "",
                }
    except Exception:
        return {}
    return uit


def huurpositie(w, sc, huidige):
    """
    Waar staat dit pand tussen de huidige huurstroom en het wettelijk maximum?
    Geeft niets terug als we de huidige huur niet kennen.
    """
    gegevens = huidige.get(_woz_sleutel(w["adres"]))
    if not gegevens or not sc:
        return None
    nu = gegevens["jaarhuur"]
    maximaal = (sc.get("maand") or 0) * 12     # al afgetopt op het puntenstelsel
    if maximaal <= 0:
        return None
    return {
        "nu": nu,
        "maximaal": maximaal,
        "ruimte": maximaal - nu,
        "pct": (maximaal - nu) / nu * 100 if nu else 0,
        "eenheden": gegevens.get("eenheden"),
        "peildatum": gegevens.get("peildatum", ""),
    }


def _verg_straat(straat):
    """Straatnaam normaliseren, zodat schrijfwijzen op elkaar matchen."""
    a = straat.lower()
    for lang, kort in (("sint ", "st"), ("st. ", "st"), ("professor ", "prof"),
                       ("prof. ", "prof"), ("burgemeester ", "burg"),
                       ("burg. ", "burg"), ("doctor ", "dr"), ("dr. ", "dr")):
        a = a.replace(lang, kort)
    return re.sub(r"[^a-z0-9]", "", a)


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

        # Klopt de oppervlakte niet, dan klopt de prijs per m2 ook niet en
        # geven we geen oordeel. Het pand blijft wel zichtbaar.
        if w.get("opp_onbetrouwbaar"):
            kandidaten.append((999, ppm2, klasse, None, None, w))
            continue

        mediaan = st.median(reeks)
        afwijking = (ppm2 - mediaan) / mediaan * 100
        kandidaten.append((afwijking, ppm2, klasse, afwijking, basis, w))

    if not kandidaten:
        return r, []

    cbs = lees_cbs()
    gezien = lees_gezien()
    woz_tabel = lees_woz()
    for _k in kandidaten:
        _w = _k[-1]
        _gegevens = woz_van(_w, woz_tabel)
        if _gegevens:
            _w["woz"] = _gegevens["woz"]
            _w["woz_jaar"] = _gegevens.get("jaar")
    vul_woz_aan(kandidaten, woz_tabel)
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
        # De buurtcijfers veranderen jaarlijks; die elke ochtend herhalen voegt
        # niets toe. Doordeweeks alleen de prijstrend, zondag het hele beeld.
        kenmerken = buurtregel(buurt, cbs, opp_bag.get(buurt), studenten_ring,
                               lees_trend())
        if kenmerken and not kort:
            r.append(f"_{kenmerken}_")
        elif kort:
            # Doordeweeks is de tendens het enige buurtcijfer dat verandert
            hist = lees_trend() or {}
            trend = trendregel(buurt, hist)
            rijen_b = per_buurt.get(buurt, [])
            delen_t = []
            if rijen_b:
                delen_t.append(f"mediaan €{eu(st.median([p for p, _ in rijen_b]))}/m² "
                               f"op {len(rijen_b)} waarnemingen")
            if trend:
                delen_t.append(trend)
            if delen_t:
                r.append("_" + " . ".join(delen_t) + "._")
        r.append("")

        # Panden zonder vergelijkingsmateriaal apart houden: vijf keer dezelfde
        # mededeling in een tabel leest slecht.
        # Panden die je niet mag verhuren tonen we niet dagelijks; ze blijven
        # wel meetellen in de medianen waartegen we vergelijken.
        verborgen = 0
        if kort:
            zichtbaar = []
            for k in rijen_buurt:
                if opkoop_signaal(k[-1]) == "beschermd":
                    verborgen += 1
                else:
                    zichtbaar.append(k)
            rijen_buurt = zichtbaar

        beoordeeld = [k for k in rijen_buurt if k[3] is not None]
        onbeoordeeld = [k for k in rijen_buurt if k[3] is None]
        if not rijen_buurt and not bm.get(buurt):
            r.pop()  # lege buurtregel weer weghalen
            r.pop()
            r.pop()
            continue

        # Doordeweeks scheiden we wat nieuw is van wat er al stond. Anders is
        # driekwart van de brief elke ochtend hetzelfde.
        if kort:
            vergunningen_nu = lees_kamervergunningen()
            vers, oud, stil = [], [], []
            for k in beoordeeld:
                w = k[-1]
                reden = verdient_aandacht(w, k[3], vergunningen=vergunningen_nu)
                if not reden:
                    stil.append(k)          # telt mee, komt niet in beeld
                elif is_nieuw_of_gewijzigd(w, gezien)[0]:
                    w["_reden"] = reden
                    vers.append(k)
                else:
                    w["_reden"] = reden
                    oud.append(k)
        else:
            vers, oud, stil = beoordeeld, [], []

        if vers:
            kop = ("| Adres | Vraagprijs | m² | €/m² | Afwijking van de "
                   "buurtmediaan | Waarom | Verhuurd als | Richtprijs |")
            streep = "|---|---:|---:|---:|---:|---|---|---:|"
            if toon_dagen:
                kop += " Dagen |"
                streep += "---:|"
            r.append(kop)
            r.append(streep)
            for _, ppm2, klasse, afwijking, basis, w in sorted(vers, key=lambda x: x[0]):
                prijs_s = f"{w['prijs']:,}".replace(",", ".")
                ppm2_s = f"{int(ppm2):,}".replace(",", ".")
                merk = "🟢" if afwijking <= -10 else ("🟡" if afwijking < 10 else "🔴")
                staart = "" if basis == buurt else f" ({basis})"
                # Mediaan binnen dezelfde grootteklasse, eerst in de buurt en
                # anders stadsbreed, want grootte bepaalt de prijs per m2 sterk
                band = groottebandje(w["oppervlakte"])
                zelfde_band = [p for p, x in per_buurt.get(buurt, [])
                               if groottebandje(x.get("oppervlakte")) == band]
                if len(zelfde_band) < 4:
                    zelfde_band = [p for b, rijen_x in per_buurt.items()
                                   for p, x in rijen_x
                                   if groottebandje(x.get("oppervlakte")) == band]
                med_b = st.median(zelfde_band) if len(zelfde_band) >= 4 else None
                sc = kies_scenario(w, huur_bk, huur_k, buurt, med_b,
                                   per_buurt.get(buurt, []))
                # Bij een pand in verhuurde staat telt de bestaande huurstroom
                # voor de cashflow; het maximum is de potentie bij mutatie.
                # Kennen we de werkelijke huur, dan rekenen we daarmee: een
                # geschatte huur is nooit beter dan een gemeten huur.
                hp0 = huurpositie(w, sc, lees_huidige_huur())
                if hp0 and sc:
                    sc = dict(sc)
                    sc["maand"] = hp0["nu"] / 12
                    sc["huur_m2"] = (sc["maand"] / sc["opp"]) if sc.get("opp") else 0
                    sc["bron"] = "gemeten uit de verkoopgegevens"
                w["_scenario"] = sc
                w["_huurpositie"] = hp0
                plafond = (richtprijs(sc["opp"], sc["huur_m2"], opex_voor(sc["naam"]))
                           if sc else None)
                if plafond:
                    verschil = (plafond - w["prijs"]) / w["prijs"] * 100
                    plafond_s = ("€" + f"{int(plafond):,}".replace(",", ".")
                                 + f" ({verschil:+.0f}%)")
                else:
                    plafond_s = "—"
                scenario = (f"{sc['naam']}, €" + f"{int(sc['maand']):,}".replace(",", ".")
                            + "/mnd") if sc else "—"
                if sc and sc.get("verkoopmarge"):
                    marge = sc["verkoopmarge"]
                    scenario += (f" . bij verkoop €{eu(sc['verkoopwaarde'])}"
                                 f" ({'+' if marge > 0 else ''}{eu(marge)})")
                hp = w.get("_huurpositie")
                if hp and hp["ruimte"] > 0:
                    scenario += (" . werkelijke huur, "
                                 + f"{hp['pct']:.0f}".replace(".", ",")
                                 + "% onder het puntenmaximum")
                elif hp:
                    scenario += " . werkelijke huur, al op of boven het puntenmaximum"
                eenh = w.get("eenheden_in_pand") or []
                if len(eenh) > 1:
                    scenario += (f" . pand bevat al {len(eenh)} woningen volgens "
                                 f"de BAG")
                if w.get("splitsing_geregistreerd"):
                    nieuw = w["splitsing_geregistreerd"]
                    scenario += (f" . splitsing al geregistreerd in de BAG: "
                                 + ", ".join(f"{x['adres']} {x['oppervlakte']} m²"
                                             for x in nieuw))
                if w.get("opp_onbetrouwbaar"):
                    scenario = ("oppervlakte onbekend: de BAG rekent "
                                f"{w.get('oppervlakte')} m² voor "
                                f"{len(w['object_adressen'])} adressen samen")
                elif w.get("object_adressen"):
                    scenario += (f" (oppervlakte uit de advertentie; de BAG rekent "
                                 f"{w.get('oppervlakte_bag')} m² voor "
                                 f"{len(w['object_adressen'])} adressen samen)")
                elif w.get("opp_verschil"):
                    scenario += f" (BAG zegt {w.get('oppervlakte_bag')} m²)"
                if sc and sc.get("let_op"):
                    scenario += " ✱"
                if sc and sc.get("gereguleerd"):
                    scenario += f" ({sc['punten']} pt, {sc['segment']})"
                elif sc and sc.get("beschermd"):
                    scenario += " ⚠"
                regel = (f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} | "
                         f"€{prijs_s} | {w['oppervlakte']} | €{ppm2_s} | "
                         f"{merk} {afwijking:+.0f}%{staart} | "
                         f"{w.get('_reden', '')} | {scenario} | {plafond_s} |")
                if toon_dagen:
                    dagen = _dagen_sinds(w.get("datum_eerst") or w.get("datum"))
                    regel += f" {dagen if dagen is not None else '—'} |"
                r.append(regel)
            r.append("")

        # Panden zonder oordeel splitsen naar reden: te weinig vergelijking,
        # of een oppervlakte die niet klopt. Dat is iets heel anders.
        onbetrouwbaar_hier = [k for k in onbeoordeeld if k[-1].get("opp_onbetrouwbaar")]
        onbeoordeeld = [k for k in onbeoordeeld if not k[-1].get("opp_onbetrouwbaar")]

        for _a, ppm2, _k, _b, _c, w in onbetrouwbaar_hier:
            r.append(f"_**{kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))}** "
                     f"€{eu(w['prijs'])}: geen oordeel, want de oppervlakte klopt niet. "
                     f"De BAG rekent {w.get('oppervlakte')} m² voor "
                     f"{len(w['object_adressen'])} adressen samen "
                     f"({', '.join(w['object_adressen'][:3])}), en kent geen cijfer per "
                     f"huisnummer. Zet de oppervlakte uit de advertentie in verkopen.txt, "
                     f"dan rekent de brief er wel mee._")
            r.append("")

        # Wat je bij de vraagprijs moet inleggen. Alleen bij nieuwe of
        # gewijzigde panden, anders staat het er elke dag opnieuw.
        if vers:
            r.append(f"_Vraagprijs uit de attendering, oppervlakte en bouwjaar uit "
                     f"de BAG, energielabel uit EP-Online, huur uit de gemeten "
                     f"advertenties. {verwijs('Aanbod', 'BAG', 'EP-Online', 'Huurniveaus')}_")
            r.append("")

        # De financiering in een tabel in plaats van een alinea per pand. Bij
        # meer dan een paar panden is doorlopende tekst niet te scannen.
        if vers:
            r.append("| Adres | Investering | Lening | Eigen inleg "
                     "| Operationeel per jaar | NAR |")
            r.append("|---|---:|---:|---:|---:|---:|")
            for _a, _p, _k, _afw, _b, w in sorted(vers, key=lambda x: x[0]):
                sc = w.get("_scenario") or {}
                netto = ((sc.get("maand") or 0) * 12
                         * (1 - opex_voor(sc.get("naam")) / 100))
                reno_uit = renovatiekosten(w.get("oppervlakte"),
                                           w.get("energielabel"), uitsplitsen=True)
                fin = financiering(w["prijs"], netto, reno_uit["totaal"])
                w["_fin"] = fin
                w["_reno"] = reno_uit
                r.append(
                    f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} "
                    f"| €{eu(fin['investering'])} | €{eu(fin['lening'])} "
                    f"| €{eu(fin['eigen'])} | €{eu(fin['operationeel'])} | "
                    + f"{fin['nar']:.1f}".replace(".", ",") + "% |")
            r.append("")
            knel = {(w.get("_fin") or {}).get("knelpunt")
                    for _a, _p, _k, _afw, _b, w in vers
                    if (w.get("_fin") or {}).get("knelpunt")}
            r.append(f"_Investering is de koopsom plus "
                     + f"{OVERDRACHTSBELASTING_PCT}".replace(".", ",") + "% "
                     f"overdrachtsbelasting, "
                     + f"{BIJKOMENDE_KOSTEN_PCT:.0f}" + "% notaris en "
                     f"makelaar, de verbouwing en {AANLOOPMAANDEN} maanden rente zonder "
                     f"huur. Operationeel is de nettohuur min de rente; de aflossing "
                     f"staat daar los van, want dat is vermogensopbouw. NAR is het netto "
                     f"aanvangsrendement over de hele investering. De lening is "
                     f"begrensd door de "
                     + " en de ".join(sorted(knel))
                     + f". {verwijs('Verhuurhypotheekrente', 'Verbouwkosten', 'Exploitatiekosten', 'Aanloopperiode')}_")
            r.append("")

            # Waar het budget knelt, alleen bij de panden waar dat speelt
            krap = []
            for _a, _p, _k, _afw, _b, w in sorted(vers, key=lambda x: x[0]):
                sc = w.get("_scenario") or {}
                netto = ((sc.get("maand") or 0) * 12
                         * (1 - opex_voor(sc.get("naam")) / 100))
                reno = (w.get("_reno") or {}).get("totaal", 0)
                budget = max_koopsom_bij_budget(netto, renovatie=reno)
                if budget and budget["max"] < w["prijs"]:
                    krap.append((w["adres"], budget["max"]))
            if krap:
                if all(m < 50_000 for _a2, m in krap):
                    r.append(f"_Met het beschikbare eigen vermogen komt geen van deze "
                             f"panden in beeld: de verbouwing slokt het budget vrijwel "
                             f"volledig op._")
                else:
                    delen = [f"{adres} tot €{eu(m)}" for adres, m in krap]
                    r.append("_Met het beschikbare eigen vermogen kom je: "
                             + " . ".join(delen) + "._")
                r.append("")

        boven_grens = [w["adres"] for _a, _p, _k, _afw, _b, w in vers
                       if ((w.get("_scenario") or {}).get("maand") or 0) > HT_MAX_HUUR
                       and "kamer" not in ((w.get("_scenario") or {}).get("naam") or "")]
        if len(boven_grens) == len(vers) and vers:
            r.append(f"_Alle panden hier komen bij de berekende huur boven de maximale "
                     f"rekenhuur van €{HT_MAX_HUUR:.2f}".replace(".", ",")
                     + " voor huurtoeslag uit. Je huurders krijgen dus geen toeslag._")
            r.append("")
        elif boven_grens:
            r.append(f"_Boven de huurtoeslaggrens: {', '.join(boven_grens)}. "
                     f"Daar krijgt je huurder geen toeslag._")
            r.append("")

        # Waarschuwingen die voor de hele buurt gelden: eenmaal, niet per pand
        gezicht = gezichtswaarschuwing(buurt)
        if gezicht and vers:
            r.append(f"_{buurt} is {gezicht}. Voor wijzigingen aan het uiterlijk is "
                     f"een omgevingsvergunning nodig, ook bij panden die zelf geen "
                     f"monument zijn. Dat raakt gevelisolatie, kozijnen en zonnepanelen "
                     f"aan de voorzijde._")
            r.append("")

        # Doelgroep: alleen benoemen waar het scenario niet bij de buurt past
        mismatch = []
        for _a, _p, _k, _afw, _b, w in vers:
            uit = past_bij_buurt(w.get("_scenario"), cbs.get(buurt))
            if uit.startswith("let op"):
                mismatch.append(w["adres"])
        if mismatch:
            g = cbs.get(buurt) or {}
            r.append(f"_Doelgroep: {g.get('eenpersoons')}% van de huishoudens in "
                     f"{buurt} woont alleen en {g.get('met_kinderen')}% heeft kinderen. "
                     f"Voor {', '.join(mismatch)} is de lokale vraag naar een woning "
                     f"van die omvang dus dun; je huurder komt van buiten de buurt._")
            r.append("")

        # Een pand dat feitelijk al is opgedeeld maar juridisch niet, of juist
        # wel: dat verschil bepaalt of je nog een vergunning nodig hebt.
        for _a, _p, _k, _afw, _b, w in vers:
            halte_w = w.get("ov_halte")
            if halte_w and (halte_w["meters"] > 800
                            or halte_w.get("omweg", 1) >= 2.0):
                r.append(f"_**{w['adres']}** en het openbaar vervoer: "
                         f"{omschrijf_halte(halte_w)}. Bij kamerverhuur en kleine "
                         f"eenheden verhuur je aan mensen zonder auto, dus dat telt "
                         f"mee in de verhuurbaarheid._")
                r.append("")

            # Monumenten moeten sinds 29 mei 2026 ook een energielabel hebben
            if w.get("monument") and not (w.get("energielabel") or {}).get("label"):
                r.append(f"_**{w['adres']}** is een monument zonder geregistreerd "
                         f"energielabel. Sinds {LABEL_PLICHT_VANAF} is dat ook voor "
                         f"monumenten verplicht bij verkoop, verhuur of oplevering; "
                         f"de oude uitzondering is vervallen door de Europese "
                         f"richtlijn EPBD IV. Verduurzamingseisen gelden nog steeds "
                         f"niet, maar het label moet er zijn._")
                r.append("")

            eenh = w.get("eenheden_in_pand") or []
            if len(eenh) > 1:
                namen_e = ", ".join(f"{e['adres']}"
                                    + (f" ({e['oppervlakte']} m²)"
                                       if e.get("oppervlakte") else "")
                                    for e in eenh[:4])
                r.append(f"_**{w['adres']}** zit in een pand met volgens de BAG "
                         f"{len(eenh)} woningen, elk met een eigen adres: "
                         f"{namen_e}. Het aangeboden object is daar een van. De "
                         f"oppervlakte per adres komt uit de BAG en kan afwijken "
                         f"van de advertentie. Dat de BAG aparte woningen telt, "
                         f"zegt niet of het pand juridisch in appartementsrechten "
                         f"is gesplitst; dat staat in het Kadaster. Een "
                         f"splitsingsvergunning kent Nijmegen niet._")
                r.append("")

        if stil:
            prijzen_stil = sorted(p for _a, p, _k, _afw, _b, _w in
                                  [(k[0], k[1], k[2], k[3], k[4], k[5]) for k in stil])
            # Waarom ze niet in beeld komen: geen route, of gewoon niets bijzonders
            geblokt = {}
            for k in stil:
                for route, reden in (k[-1].get("_routes") or {}).get(
                        "geblokkeerd", {}).items():
                    geblokt.setdefault(reden, set()).add(route)
            regel_stil = (f"_{len(stil)} pand" + ("en" if len(stil) > 1 else "")
                          + f" buiten beeld, mediaan "
                          + f"€{eu(st.median(prijzen_stil))}/m². "
                          + "Die tellen mee in de vergelijking maar vragen geen actie")
            if geblokt:
                delen_g = [_uitleg_blokkade(r, reden)
                           for reden, routes in sorted(geblokt.items())
                           for r in sorted(routes)]
                regel_stil += ": " + " ".join(delen_g[:3])
            r.append(regel_stil + "._")
            r.append("")

        if oud:
            stukken = []
            for _a, ppm2, _k, afw, _b, w in sorted(oud, key=lambda x: x[0]):
                dagen = _dagen_sinds(w.get("datum_eerst") or w.get("datum"))
                stukken.append(
                    kaartlink(w["adres"], w.get("plaats", "Nijmegen"), w.get("bron", ""))
                    + f" €{eu(w['prijs'])} ({afw:+.0f}% t.o.v. de buurtmediaan"
                    + (f", {dagen} dagen in aanbod" if dagen is not None else "") + ")")
            r.append("_Stond er al, vraagprijs ongewijzigd: " + " . ".join(stukken)
                     + ". Het percentage is de afwijking van de mediaanprijs per "
                       "vierkante meter in die buurt, niet een prijswijziging._")
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

            # Gemengde panden hebben een woonfunctie erbij en lenen zich vaak voor
            # splitsing van de bovenverdiepingen. De commerciele plint drukt de
            # prijs per m2, terwijl kleine appartementen er juist meer opbrengen.
            gemengd = [k for k in onbeoordeeld if k[2] == "gemengd"]
            for _a, ppm2, _k, _b, _c, w in gemengd:
                sp = splitsscenario(w, huur_bk, huur_k, buurt,
                                    per_buurt.get(buurt, []))
                if not sp or not sp.get("verkoopwaarde"):
                    continue
                marge = sp["verkoopmarge"]
                r.append(f"_**{w['adres']}** is een gemengd pand. Bij splitsing van de "
                         f"woonlagen in {sp['aantal']} eenheden van circa "
                         f"{sp['unit_m2']} m² is de verkoopwaarde €{eu(sp['verkoopwaarde'])}, "
                         f"dus {'+' if marge > 0 else ''}{eu(marge)} ten opzichte van de "
                         f"vraagprijs. Verbouwen mag naar het niveau van bestaande bouw, "
                         f"wat bij vooroorlogse panden veel scheelt. Verhuur van de nieuwe "
                         f"eenheden loopt vast op de opkoopbescherming en het "
                         f"puntenstelsel; dit is dus een verkoopscenario._")
                r.append("")

        met_woz = [k[-1] for k in rijen_buurt if k[-1].get("woz")]
        if met_woz:
            stukken = []
            for w in met_woz:
                jaar = w.get("woz_jaar")
                oud = jaar and jaar < dt.date.today().year - 1
                deel = (f"{w['adres']} €{eu(w['woz'])}"
                        + (f" ({jaar}{', verouderd' if oud else ''})" if jaar else ""))
                wws = wws_indicatie(w)
                if wws and wws.get("punten") is not None:
                    deel += (f", puntenstelsel ondergrens {wws['punten']} punten "
                             f"({wws['basis']}): {wws['oordeel']}")
                elif wws:
                    deel += f" ({wws['basis']}): {wws['oordeel']}"
                stukken.append(deel)
            r.append("_Bekende WOZ-waarden: " + " . ".join(stukken)
                     + ". Daar toetsen we op in plaats van op de vraagprijs. De "
                       "punten zijn een ondergrens: keuken, sanitair en "
                       "buitenruimte als gewone woning aangenomen, verwarming "
                       "niet meegeteld._")
            r.append("")

        # Buren met kamerverhuur: dat blokkeert een omzettingsvergunning
        vergunningen = lees_kamervergunningen()
        archief = lees_archief()

        # Handhaving op een pand in het aanbod: dat wil je weten voordat je biedt.
        # Alleen bij nieuwe of gewijzigde panden, anders staat het er elke dag.
        for k in (rijen_buurt if not kort else vers + onbeoordeeld):
            w = k[-1]
            hh = handhaving_op_adres(w["adres"], archief, straal=2)
            if not hh:
                continue
            eigen = [t for t in hh if t["eigen"]]
            anderen = [t for t in hh if not t["eigen"]]
            if eigen:
                t = eigen[0]
                r.append(f"_**Handhaving op {w['adres']}**: {t['titel']} "
                         f"({t['datum']}). Dat is een besluit op dit pand zelf en "
                         f"weegt mee bij een nieuwe vergunningaanvraag._")
                r.append("")
            elif anderen:
                namen = ", ".join(f"{t['adres']} ({t['soort']}, {t['datum'][:4]})"
                                  for t in anderen[:3])
                r.append(f"_Handhaving in de directe omgeving van {w['adres']}: "
                         f"{namen}. Dat telt mee in de leefbaarheidstoets._")
                r.append("")
        if archief or vergunningen:
            for k in rijen_buurt:
                w = k[-1]
                sc = w.get("_scenario") or {}
                if "kamers" not in (sc.get("naam") or ""):
                    continue
                # Heeft het pand zelf al een vergunning?
                eigen = vergunningen.get(archief_sleutel(
                    *(re.match(r"^(.+?)\s+(\d+)", w["adres"]).groups()
                      if re.match(r"^(.+?)\s+(\d+)", w["adres"]) else ("", "0"))), [])
                if eigen:
                    r.append(f"_**{w['adres']}** heeft al een {eigen[0]['soort']}"
                             f"svergunning uit {eigen[0]['datum'][:4]}. Dat scheelt een "
                             f"vergunningtraject._")
                    r.append("")
                buren = buren_met_kamerverhuur(w["adres"], archief, vergunningen)
                if buren:
                    namen = ", ".join(f"{b['adres']} ({b['soort']}, {b['datum']})"
                                      for b in buren)
                    r.append(f"_**Let op bij {w['adres']}**: in het archief staan "
                             f"vergunningsignalen op {namen}. Nijmegen staat niet meer "
                             f"dan twee direct naast, onder of boven elkaar gelegen "
                             f"kamergewijs bewoonde woningen toe, dus dit kan een "
                             f"omzettingsvergunning in de weg staan. De vergunningenlijst "
                             f"loopt van 2016 tot 2025; oudere vergunningen staan er niet "
                             f"in, dus geen treffer is geen vrijbrief._")
                    r.append("")

        if verborgen:
            r.append(f"_{verborgen} pand" + ("en" if verborgen > 1 else "")
                     + " onder de WOZ-grens niet getoond: die mag je na aankoop niet "
                       "verhuren. Ze tellen wel mee in de vergelijkingscijfers. "
                       "In de zondagsbrief staan ze er wel bij._")
            r.append("")

        # Opkoopbescherming: dit bepaalt of je het pand uberhaupt mag verhuren
        toon_bij = rijen_buurt if not kort else (vers + onbeoordeeld)
        beschermd = [k[-1] for k in toon_bij
                     if opkoop_signaal(k[-1]) == "beschermd"]
        grens = [k[-1] for k in toon_bij
                 if opkoop_signaal(k[-1]) == "grensgeval"]
        voortzetting = [k[-1] for k in toon_bij
                        if opkoop_signaal(k[-1]) == "voortzetting"]
        if beschermd:
            namen = ", ".join(w["adres"] for w in beschermd)
            grens = f"{OPKOOPBESCHERMING_WOZ:,}".replace(",", ".")
            r.append(f"_**Opkoopbescherming** bij {namen}: de vraagprijs ligt onder "
                     f"€{grens}, dus de WOZ vrijwel zeker ook. Deze woningen mag je de "
                     f"eerste {OPKOOPBESCHERMING_JAAR} jaar na levering niet verhuren "
                     f"zonder verhuurvergunning. De richtprijs hiernaast gaat uit van "
                     f"verhuur en is dus alleen relevant als een uitzondering geldt. "
                     f"Huisvestingsverordening Nijmegen 2024 art. 19._")
            r.append("")
        elif grens:
            namen = ", ".join(w["adres"] for w in grens)
            grens = f"{OPKOOPBESCHERMING_WOZ:,}".replace(",", ".")
            r.append(f"_Grensgeval voor de opkoopbescherming: {namen}. Controleer de WOZ, "
                     f"want onder €{grens} mag je niet zonder meer verhuren._")
            r.append("")
        if voortzetting:
            namen = ", ".join(w["adres"] for w in voortzetting)
            r.append(f"_{namen} wordt in verhuurde staat aangeboden. Was het pand op de "
                     f"leveringsdatum al langer dan zes maanden verhuurd, dan is het geen "
                     f"beschermde woonruimte en geldt de vergunningplicht niet. Bij lege "
                     f"oplevering of een kortere verhuurperiode vervalt die route._")
            r.append("")

        # Verkameren: welke panden vallen buiten de Nijmeegse WOZ-band
        woningen_hier = [k[-1] for k in (rijen_buurt if not kort else vers)
                         if k[2] == "woning"]
        if woningen_hier:
            uitgesloten = [w for w in woningen_hier
                           if verkameren_signaal(w["prijs"]) == "niet toegestaan"]
            if uitgesloten:
                namen = ", ".join(w["adres"] for w in uitgesloten)
                ondergrens = f"{WOZ_ONDERGRENS:,}".replace(",", ".")
                r.append(f"_Verkameren valt af bij {namen}: de vraagprijs ligt onder "
                         f"€{ondergrens}, en onder die WOZ-grens staat Nijmegen "
                         f"kamerverhuur niet toe. Als gewone verhuur kunnen deze panden "
                         f"wel uitkomen; kijk daarvoor naar de kolom Richtprijs. "
                         f"Huisvestingsverordening Nijmegen 2024 art. 15 lid 1._")
                r.append("")

        if bm.get(buurt):
            r.extend(bekendmakingregels(bm[buurt]))
            r.append("")

    if kort and buiten_ring:
        r.append(f"_{buiten_ring} panden staan in buurten buiten de ring. Die staan in de "
                 f"uitgebreide brief van zondag._")
        lastsoort = ("rente en aflossing" if LOOPTIJD_JAAR
                     else "rente")
        r.append("_De uitleg bij de kolommen, de aannames achter de scenario's en de "
                 "regels rond verkameren en splitsen staan in de uitgebreide brief van "
                 "zondag._")
        r.append("")
        if not kort:
            r.append("_Staat er **kamers, mits vergunning**, dan is dat een rekenscenario "
                     "en geen advies. Het model kent alleen oppervlakte en prijs, en kan een "
                     "eengezinswoning niet onderscheiden van een pand dat er zich voor leent. "
                     "Beoordeel zelf of het past: verkameren verzilvert vierkante meters en "
                     "niet de kwaliteit waarvoor je bij een duur pand betaalt, de "
                     "leefbaarheidstoets sneuvelt juist in rustige straten, er mogen niet "
                     "meer dan twee kamergewijs bewoonde woningen naast elkaar liggen, en een "
                     "verkamerd pand verkoop je niet meer aan een gezin. Een ✱ betekent dat "
                     "de prijs per m² boven het gemiddelde van vergelijkbaar grote panden "
                     "ligt, wat een extra reden tot terughoudendheid is._")
            r.append(f"_Splitsen wordt getoond zodra dat meer oplevert dan de andere routes. "
                     f"Nijmegen kent geen splitsingsvergunning, maar een omgevingsvergunning "
                     f"is wel nodig en het Bouwbesluit stelt eisen aan geluid, brandveiligheid "
                     f"en toegang. Gerekend met minimaal {MIN_UNIT_M2} m² per eenheid en "
                     f"{int(VERHUURBAAR_SPLITSING*100)}% van het vloeroppervlak verhuurbaar; "
                     f"dat zijn aannames, geen normen. Verbouwkosten zitten er niet in. "
                     f"Een ⚠ betekent dat de nieuwe eenheden onder €{eu(OPKOOPBESCHERMING_WOZ)} "
                     f"uitkomen en dus vier jaar lang niet vrij verhuurd mogen worden. Staat er "
                     f"een puntenaantal bij, dan blijven de eenheden onder de 187 punten en is "
                     f"de huur wettelijk begrensd; de getoonde markthuur mag dan niet gevraagd "
                     f"worden. Punten zijn een ondergrens: verwarming en enkele rubrieken "
                     f"ontbreken in onze telling._")
            # Diagnose: welke huren liggen er onder de berekening?
            stukken = []
            for band in ("klein", "middel", "groot"):
                reeks = huur_k.get(("woning", band), [])
                if reeks:
                    stukken.append(f"{band} €{st.median(reeks):.0f} (n={len(reeks)})")
            kamers_r = huur_k.get("kamer", [])
            if kamers_r:
                stukken.append(f"kamers €{st.median(kamers_r):.0f} (n={len(kamers_r)})")
            if stukken:
                r.append("_Gemeten huur per m² per maand: " + " . ".join(stukken)
                         + ". Wijkt dit sterk af van wat je in de markt ziet, dan klopt er "
                           "iets niet in de huurgegevens en zijn de richtprijzen onbetrouwbaar._")
            r.append(f"_**Verhuurd als** toont het scenario dat is doorgerekend. Boven "
                     f"{MAX_M2_EEN_HUISHOUDEN} m² of €{eu(MAX_HUUR_EEN_HUISHOUDEN)} per maand "
                     f"rekenen we met kamers, want de markt betaalt zulke bedragen niet voor "
                     f"één huishouden. Bij kamers telt {int(VERHUURBAAR_AANDEEL*100)}% van het "
                     f"vloeroppervlak als verhuurbaar; de rest is gang en trappenhuis. "
                     f"'Mits vergunning' is geen formaliteit: omzetting is in de hele ring "
                     f"vergunningplichtig. **Richtprijs** is de hoogste koopsom waarbij de "
                     f"nettohuur {lastsoort} nog dekt, bij {LTV:.0f}% financiering en "
                     f"{pct(RENTE)}% rente._")
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
            r.append(f"_Kamerverhuur in Nijmegen, op WOZ-waarde: onder €{WOZ_ONDERGRENS:,} "
                     f"niet toegestaan. Tussen €{WOZ_ONDERGRENS:,} en €{WOZ_BOVENGRENS:,} een "
                     f"omzettingsvergunning nodig bij drie of meer kamers of drie of meer "
                     f"bewoners die geen huishouden vormen. Daarboven vervalt die vergunning, "
                     f"maar blijft de omgevingsvergunning gelden. Vanaf vijf kamers ook een "
                     f"melding brandveilig gebruik. Verhuur aan maximaal twee personen is "
                     f"vergunningvrij. Let op: de opkoopbescherming gaat hieraan vooraf, want "
                     f"onder €{eu(OPKOOPBESCHERMING_WOZ)} mag je een gekocht pand sowieso niet "
                     f"zonder meer verhuren. Wij toetsen op de vraagprijs; controleer de WOZ "
                     f"zelf op wozwaardeloket.nl. Bedragen worden jaarlijks "
                     f"opnieuw vastgesteld._")
            r.append("")
    # Vastleggen wat er is getoond, zodat het morgen niet opnieuw hoeft
    for k in kandidaten:
        werk_gezien_bij(k[-1], gezien)
    schrijf_gezien(gezien)

    return r, kandidaten


KAART_URL = ("https://derksenvastgoed.github.io/"
             "DerksenVastgoed-Vastgoedrapport-Nijmegen/kaart-eigendom-ring.html")



def render_samenvatting(woningen, kandidaten, bm_per_buurt=None, kort=True,
                        gezien_vooraf=None):
    """
    Opening met wat er vandaag speelt, niet met achtergrondcijfers. Alles hier
    volgt uit wat elders in de brief staat; er komt geen nieuwe bron bij.
    """
    def n(x):
        return f"{int(x):,}".replace(",", ".")

    zinnen = []
    aanbod = [k for k in kandidaten if k[3] is not None]
    # Nieuw telt op hetzelfde geheugen als de tabel, anders spreekt de
    # samenvatting de rest van de brief tegen.
    gezien_nu = gezien_vooraf if gezien_vooraf is not None else lees_gezien()
    in_beeld = {id(k[-1]) for k in aanbod}
    nieuw = [w for w in woningen
             if id(w) in in_beeld and is_nieuw_of_gewijzigd(w, gezien_nu)[0]]
    gewijzigd = [w for w in woningen
                 if w.get("prijs_eerst") and w["prijs_eerst"] != w["prijs"]]

    kop = f"{len(aanbod)} panden in beeld"
    if nieuw:
        kop += (f", {len(nieuw)} nieuw of gewijzigd"
                if len(nieuw) > 1 else ", 1 nieuw of gewijzigd")
    else:
        kop += ", geen mutaties sinds gisteren"
    if gewijzigd:
        kop += f", waarvan {len(gewijzigd)} met een prijswijziging"
    zinnen.append(kop + ".")

    # Het scherpst geprijsde pand, met het scenario erbij
    # Panden die je niet mag verhuren horen niet als tip in de opening
    toonbaar = [k for k in aanbod if opkoop_signaal(k[-1]) != "beschermd"]
    if toonbaar and nieuw:
        beste = sorted(toonbaar, key=lambda x: x[0])[0]
        afw, ppm2, klasse, _a, basis, w = beste
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
        zin = (f"Scherpst geprijsd is **{w['adres']}** in {buurt}: €{n(w['prijs'])} "
               f"voor {w['oppervlakte']} m², {afw:+.0f}% ten opzichte van de mediaan "
               f"van zijn klasse")
        sc = w.get("_scenario")
        if sc:
            plafond = richtprijs(sc["opp"], sc["huur_m2"], opex_voor(sc["naam"]))
            if plafond:
                ruimte = (plafond - w["prijs"]) / w["prijs"] * 100
                zin += (f". Als {sc['naam']} loopt het rond tot €{n(plafond)}, "
                        f"dus {ruimte:+.0f}% ten opzichte van de vraagprijs")
        zinnen.append(zin + ".")

    # Bewegingen benoemen, want dat is het enige dat sinds gisteren veranderde
    if gewijzigd:
        w = sorted(gewijzigd, key=lambda x: (x["prijs"] - x["prijs_eerst"]))[0]
        verschil = w["prijs"] - w["prijs_eerst"]
        if verschil < 0:
            zinnen.append(f"Grootste verlaging: **{w['adres']}** ging €{n(abs(verschil))} "
                          f"omlaag naar €{n(w['prijs'])}.")

    # Gemeentelijke berichten
    bm = bm_per_buurt or {}
    aantal_bm = sum(len(v) for v in bm.values())
    if aantal_bm:
        kern = sum(1 for v in bm.values() for b in v if b.get("kern"))
        zin = f"{aantal_bm} gemeentelijke bericht" + ("en" if aantal_bm > 1 else "")
        if kern:
            zin += f", waarvan {kern} over splitsen, verkameren of transformatie"
        zinnen.append(zin + ".")

    if not zinnen:
        return []
    return ["", "## Vandaag", "", " ".join(zinnen), ""]


def render_intro(cbs, woningen, kort=False):
    """
    Achtergrondcijfers over de stad en de ring. Dit is context, geen nieuws,
    en staat daarom onderaan de brief in plaats van bovenaan.
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

    slot = (f"De brief volgt {n(len(woningen))} panden, waarvan er {in_aanbod} nu "
            f"in aanbod zijn. Bijgewerkt {vandaag}. "
            f"[Bekijk de eigendomskaart]({KAART_URL}).")
    zinnen.append(slot)

    return ["", "### Achtergrond", "", " ".join(zinnen), ""]



def vul_ov_afstand(woningen):
    """
    Loopafstand tot de dichtstbijzijnde halte, voor panden die hem nog missen.

    Dit staat los van de BAG-verrijking, want die draait alleen voor panden die
    nieuw zijn. Een pand dat al in de cache stond zou anders nooit een
    loopafstand krijgen. De uitkomst wordt per coordinaat bewaard, dus dit kost
    alleen de eerste keer tijd.
    """
    if not dichtstbijzijnde_halte:
        return
    haltes = lees_haltes_bestand()
    if not haltes:
        print("Geen haltebestand gevonden; loopafstanden overgeslagen",
              file=sys.stderr)
        return

    nieuw = 0
    for w in woningen:
        if w.get("ov_halte") or (w.get("status") or "").lower() == "verkocht":
            continue
        punt = coordinaten(w["adres"], w.get("plaats", "Nijmegen"))
        if not punt:
            continue
        halte = dichtstbijzijnde_halte(punt[0], punt[1], haltes)
        if halte:
            w["ov_halte"] = halte
            nieuw += 1
    if nieuw:
        print(f"Loopafstand tot een halte bepaald voor {nieuw} panden",
              file=sys.stderr)


def lees_haltes_bestand():
    try:
        from ov_haltes import lees_haltes
        return lees_haltes()
    except Exception:
        return []


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

    r = ["", ""]   # samenvatting wordt hierna ingevoegd, zodra we de kandidaten hebben

    per_buurt = defaultdict(list)
    beleggingen = []
    huur_aanbod = []
    onbetrouwbaar = []
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

        # De BAG kent geen oppervlakte per huisnummer, alleen per verblijfsobject.
        # Hangen er meer adressen aan hetzelfde object en hebben we geen cijfer
        # uit de advertentie, dan klopt de prijs per m2 niet en mag dit pand de
        # mediaan niet beinvloeden. In het aanbod blijft het wel staan.
        if (len(w.get("object_adressen") or []) > 1
                and not w.get("oppervlakte_bron")):
            w["opp_onbetrouwbaar"] = True
            onbetrouwbaar.append(w)
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

    historie = bewaar_prijspeil(per_buurt, stad_breed)

    if onbetrouwbaar:
        print(f"Buiten de statistiek gehouden: {len(onbetrouwbaar)} panden waarvan "
              f"de oppervlakte niet klopt met wat er te koop staat", file=sys.stderr)

    if not per_buurt and not beleggingen:
        r.append("_Geen woningen met bruikbare data._")
        return "\n".join(r)

    vul_ov_afstand([w for w in woningen
                    if (w.get("status") or "").lower() != "verkocht"])

    # Het geheugen lezen voordat het aanbod het bijwerkt, anders ziet de
    # samenvatting alles als al gezien.
    gezien_vooraf = lees_gezien()

    # Doordeweeks de volledige lijst per buurt, zondag uitgewerkte cases
    aanbod_regels, kandidaten = render_nieuw_aanbod(
        woningen, per_buurt, stad_breed, bm_per_buurt, bm_overig, kort=kort)
    if kort:
        # Samenvatting vooraan, daarna het aanbod, dan de bewegingen en als
        # laatste de achtergrondcijfers
        huur_bk_b, huur_k_b = gemeten_huren(huur_aanbod)
        r = (render_samenvatting(woningen, kandidaten, bm_per_buurt, kort=True,
                                 gezien_vooraf=gezien_vooraf)
             + aanbod_regels
             + render_bieden(woningen, huur_bk_b, huur_k_b, per_buurt)
             + render_prijswijzigingen(woningen)
             + render_looptijd(woningen)
             + render_intro(lees_cbs(), woningen, kort=True))

    # De bijlage: dezelfde cijfers, maar als tabellen zonder verhaal
    pad_bijlage = globals().get("_BIJLAGE_PAD")
    if pad_bijlage:
        try:
            regels_b = render_bijlage(woningen, per_buurt, stad_breed)
            with open(pad_bijlage, "w", encoding="utf-8") as fb:
                fb.write("\n".join(regels_b) + "\n")
            print(f"Bijlage weggeschreven naar {pad_bijlage}", file=sys.stderr)
        except Exception as e:
            print(f"Bijlage maken mislukt: {e}", file=sys.stderr)

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
    r.extend(render_bieden(woningen, huur_bk, huur_k, per_buurt))
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
                 f"Gerekend met rente {pct(RENTE)}% aflossingsvrij, LTV {LTV:.0f}% en "
                 f"{OPEX_PER_SCENARIO['woning']}% exploitatiekosten voor gewone verhuur en "
                 f"{OPEX_PER_SCENARIO['kamers']}% bij kamerverhuur. Daarin zitten groot "
                 f"onderhoud, verzekering, gemeentelijke lasten, beheer en mutatie, maar "
                 f"niet de posten die via de servicekosten worden doorbelast._")
    else:
        r.append(f"_De mediaan €/m² is gemeten. De huur per m² is nog een **aanname**, "
                 f"want er zijn nog geen huuraanbiedingen verzameld. "
                 f"Gerekend met rente {pct(RENTE)}% aflossingsvrij, LTV {LTV:.0f}% en "
                 f"{OPEX_PER_SCENARIO['woning']}% exploitatiekosten voor gewone verhuur en "
                 f"{OPEX_PER_SCENARIO['kamers']}% bij kamerverhuur. Daarin zitten groot "
                 f"onderhoud, verzekering, gemeentelijke lasten, beheer en mutatie, maar "
                 f"niet de posten die via de servicekosten worden doorbelast._")
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
        netto_huur = kale_huur * (1 - OPEX_PER_SCENARIO["woning"] / 100)
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
            weg = huur_k.get("_inclusief_weggelaten")
            if weg:
                r.append(f"_{weg} advertenties met een bedrag inclusief vaste lasten zijn "
                         f"weggelaten. Alleen kale huur telt: servicekosten zijn "
                         f"doorbelasting van werkelijke kosten en het puntenstelsel "
                         f"toetst er niet op._")
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
    ap.add_argument("--bijlage", default="",
                    help="schrijf daarnaast een bijlage met alleen tabellen")
    ap.add_argument("--bag", default="",
                    help="toon de volledige BAG-respons voor een adres")
    ap.add_argument("--debug", action="store_true",
                    help="toon de velden die de BAG teruggeeft, voor het eerste adres")
    args = ap.parse_args()

    global DEBUG
    DEBUG = args.debug

    if args.bag:
        bag_dump(args.bag)
        return

    global RENTE
    actueel = lees_actuele_rente()
    if actueel and abs(actueel - RENTE) > 0.01:
        print(f"Rente bijgesteld van {RENTE}% naar {actueel}% "
              f"op basis van de gemeten stand", file=sys.stderr)
        RENTE = actueel

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
    for i, w in enumerate(woningen):
        obj = w.get("adresseerbaarObjectIdentificatie")
        heeft_nummer = bool(re.search(r"\d", w["adres"]))
        if obj:
            sleutel = obj
        elif heeft_nummer:
            sleutel = re.sub(r"[^a-z0-9]", "", w["adres"].lower())
        else:
            # Adres zonder huisnummer, zoals Pararius en Kamernet dat tonen.
            # Die mogen niet samengevoegd worden: twee advertenties aan dezelfde
            # straat zijn verschillende panden, geen prijswijziging.
            sleutel = f"_los_{i}"
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
            laatste["historie"] = [
                {"datum": r.get("datum", ""), "prijs": r["prijs"], "status": r["status"]}
                for r in reeks
            ]
            laatste["waarnemingen"] = len(reeks)

            # Een prijswijziging bestaat alleen als het twee keer om hetzelfde
            # gaat. Een huuradvertentie naast een koopadvertentie van hetzelfde
            # pand is geen verlaging van zeven ton, en een verkochte woning
            # naast een nieuw aanbod is geen prijsstijging.
            def soort(w):
                st_ = (w.get("status") or "").lower()
                if st_.startswith("te huur"):
                    return "huur"
                if "belegging" in st_:
                    return "belegging"
                if "verkocht" in st_ or "transactie" in st_:
                    return "verkocht"   # referentie, geen lopend aanbod
                return "koop"

            zelfde = [r for r in reeks if soort(r) == soort(laatste)]
            if len(zelfde) > 1 and zelfde[0]["prijs"] != laatste["prijs"]:
                laatste["prijs_eerst"] = zelfde[0]["prijs"]
                laatste["datum_eerst"] = zelfde[0].get("datum", "")
            else:
                laatste["datum_eerst"] = reeks[0].get("datum", "")
        ontdubbeld.append(laatste)

    weg = len(woningen) - len(ontdubbeld)
    if weg:
        print(f"Samengevoegd: {weg} herhaalde waarnemingen, {len(ontdubbeld)} panden over",
              file=sys.stderr)
    woningen = ontdubbeld

    bm_per_buurt, bm_overig = lees_bekendmakingen(cache)
    schrijf_cache(cache)
    if args.bijlage:
        globals()["_BIJLAGE_PAD"] = args.bijlage
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
