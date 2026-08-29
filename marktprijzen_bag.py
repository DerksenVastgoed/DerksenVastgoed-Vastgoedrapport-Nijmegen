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
    if not varianten:
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
        if status == "te huur" and opp and opp >= 15:
            return w["prijs"] / opp
    except (TypeError, ZeroDivisionError):
        return None
    return None


def gemeten_huren(huur_aanbod):
    """Mediane huur per m2 per maand, per buurt en per assetklasse."""
    per_buurt_klasse = defaultdict(list)
    per_klasse = defaultdict(list)
    for w in huur_aanbod:
        hm2 = huur_per_m2_maand(w)
        if not hm2 or hm2 < 4 or hm2 > 80:
            continue  # buiten dit bereik is het vrijwel zeker een leesfout
        klasse = assetklasse(w)
        buurt = normaliseer_buurt(w.get("buurtnaam", ""))
        per_klasse[klasse].append(hm2)
        if buurt:
            per_buurt_klasse[(klasse, buurt)].append(hm2)
    return per_buurt_klasse, per_klasse


def render_nieuw_aanbod(woningen, per_buurt, stad_breed):
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
        return r

    r.append("### Aanbod beoordeeld binnen de eigen assetklasse")
    r.append("")
    r.append("| Adres | Buurt | Klasse | Prijs | m² | €/m² | Tegen mediaan | Label | Dagen |")
    r.append("|---|---|---|---:|---:|---:|---:|---|---:|")
    for _, ppm2, klasse, afwijking, basis, w in sorted(kandidaten, key=lambda x: x[0]):
        buurt = normaliseer_buurt(w.get("buurtnaam", "")) or "?"
        prijs_s = f"{w['prijs']:,}".replace(",", ".")
        ppm2_s = f"{int(ppm2):,}".replace(",", ".")
        if afwijking is None:
            oordeel = "te weinig vergelijking"
        else:
            merk = "🟢" if afwijking <= -10 else ("🟡" if afwijking < 10 else "🔴")
            staart = "" if basis == buurt else f" ({basis})"
            oordeel = f"{merk} {afwijking:+.0f}%{staart}"
        dagen = _dagen_sinds(w.get("datum_eerst") or w.get("datum"))
        r.append(f"| {kaartlink(w['adres'], w.get('plaats', 'Nijmegen'), w.get('bron', ''))} | {buurt} | "
                 f"{klasse} | €{prijs_s} | {w['oppervlakte']} | "
                 f"€{ppm2_s} | {oordeel} | {_labeltekst(w.get('energielabel'))} | "
                 f"{dagen if dagen is not None else '—'} |")
    r.append("")
    r.append("_Elk pand is afgezet tegen de mediaan van zijn eigen assetklasse, want een "
             "winkelpand en een woning zijn verschillende producten. Lukt dat niet in de "
             "eigen buurt, dan tegen heel Nijmegen; staan er ook stadsbreed te weinig "
             f"vergelijkbare objecten (minder dan {MINIMUM}), dan volgt er geen oordeel._")
    r.append("_Groen is meer dan 10% onder de mediaan van de eigen klasse, rood meer dan "
             "10% erboven._")

    # Hoeveel objecten per klasse hebben we eigenlijk?
    tellen = ", ".join(f"{k}: {len(v)}" for k, v in sorted(per_klasse.items()))
    r.append(f"_Omvang per klasse in de dataset: {tellen}._")
    r.append("")
    return r


def render(woningen, modus="weekelijks"):
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

    kop = "## Aanbod" if kort else "## Aanbod en marktprijzen"
    r = ["", kop,
         f"_{len(woningen)} panden gevolgd. Oppervlakte uit BAG. Bijgewerkt {vandaag}._",
         ""]

    # Bewegingen eerst: dat is het enige dat sinds gisteren veranderd kan zijn
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

    # Het aanbod eerst, de tabel eronder als meetlat
    r.extend(render_nieuw_aanbod(woningen, per_buurt, stad_breed))

    if kort:
        # Dagelijks houdt het hier op. De referentietabellen, yield, uitpond-marge
        # en beleggingstabel staan in de zondagsbrief.
        if len(r) <= 4:
            return ""  # niets bewogen en geen aanbod: blok helemaal weglaten
        r.append("_Referentietabellen, rendement en de beleggingslijst staan in de "
                 "uitgebreide brief van zondag._")
        r.append("")
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
    HUUR_M2_MND = {
        "Stadscentrum": 20, "Benedenstad": 20, "Bottendaal": 18,
        "Galgenveld": 18, "Altrade": 17, "Biezen": 18,
    }
    RENTE = 5.75  # huidige verhuurhypotheek indicatie
    OPEX_PCT = 25
    LTV = 66.7

    # Gemeten huren waar we ze hebben, aanname alleen waar die ontbreekt
    huur_bk, huur_k = gemeten_huren(huur_aanbod)

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
            r.append("**Gemeten huurniveaus per assetklasse:** " + " . ".join(regels_klasse))
            r.append("_Commerciële huur wordt vaak per m² per jaar geadverteerd; "
                     "die is hier door twaalf gedeeld zodat alles vergelijkbaar is._")
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

    md = render(woningen, modus=args.modus)
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
