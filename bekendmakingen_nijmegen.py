#!/usr/bin/env python3
"""
Bekendmakingen-blok voor de Nijmegen Vastgoedmonitor.

Haalt officiele bekendmakingen van gemeente Nijmegen op via de KOOP SRU-API,
filtert op de ring rond het Keizer Karelplein, gooit ruis weg, splitst de rest
in KERNSIGNALEN en OVERIGE, en zet bij elk bericht een korte duiding
een strategie-label en marktduiding via de Anthropic-API. Schrijft markdown weg.

Bronnen:
  Bekendmakingen : https://repository.overheid.nl/sru  (open, geen sleutel)
  Duiding        : https://api.anthropic.com/v1/messages (vereist ANTHROPIC_API_KEY)

Zonder ANTHROPIC_API_KEY werkt alles gewoon, alleen zonder de duiding-zin.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import requests

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
SRU_URL = "https://repository.overheid.nl/sru"
GEMEENTE = "Nijmegen"

RING_POSTCODES = ["6511", "6512", "6521", "6522", "6524", "6525", "6541", "6542"]
RING_STRATEN = [
    "Berg en Dalseweg", "Biezenstraat", "Bijleveldsingel", "Bottendaalseweg",
    "Burghardt van den Berghstraat", "Coehoornstraat", "Daalseweg",
    "Dommer van Poldersveldtweg", "Eerste Oude Heselaan", "Fransestraat",
    "Graafsedwarsstraat", "Graafseweg", "Groenestraat", "Groesbeekseweg",
    "Groesbeeksedwarsweg", "Hertogstraat", "Krayenhofflaan", "Marialaan",
    "Molenstraat", "Prins Hendrikstraat", "Sint Annastraat", "Tooropstraat",
    "van Nispenstraat", "Van Spaenstraat", "Voorstadslaan", "Waterstraat",
    "Weurtseweg", "Wolfskuilseweg", "Ziekerstraat",
]

UITSLUITEN = [
    "reclame", "uithangbord", "gevelbelettering", "naambord", "sticker",
    "spandoek", "vlaggenmast", "dakkapel", "dakterras", "dakraam", "veranda",
    "overkapping", "carport", "airco", "oprit", "inrit", "puinbak", "container",
    "hekwerk", "erfafscheiding", "schutting", "schuur", "tuinhuis", "zwembad",
    "alcohol", "leidinggevende", "exploitatievergunning", "terras", "evenement",
    "standplaats", "kappen", "kapvergunning", "boom", "bomen",
    "termijnverlenging", "buiten behandeling", "intrekking", "rectificatie",
]
KERN = [
    "splits", "samenvoeg", "omzetten", "omgezet", "omzetting",
    "zelfstandige woon", "zelfstandige wooneenhe", "zelfstandige woning",
    "wooneenhe", "appartement", "transformatie", "herbestemm",
    "kamerverhuur", "logiesfunctie", "logies", "bopa",
    "nieuwbouw", "starters", "optoppen", "woningen",
]
REL_BASIS = [
    "verbouw", "renove", "verduurz", "sloop", "woning", "woon", "warmtepomp",
    "monument", "pand", "klooster", "nokverhoging", "dakopbouw", "uitbouw",
    "aanbouw", "kozijn", "pui", "gevel",
]

MAX_PER_PAGINA = 100

# --- Duiding via Anthropic ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BAG_API_KEY = os.environ.get("BAG_API_KEY", "")
MODEL = "claude-sonnet-5"
PROFIEL = """Je bent vastgoedanalist voor een marktbrief over de binnenring van Nijmegen (rond het Keizer Karelplein, oost en west). Lezers zijn particuliere vastgoedinvesteerders en kleine ontwikkelaars. Denk als MSRE-professional, schrijf toegankelijk.

Marktcontext: in dit segment is de lopende cashflow bij huidige rentestanden ongeveer nul. Rendement komt uit waardecreatie: uitponden, splitsen, renoveren bij mutatie, functie omzetten. Beoordeel signalen door die bril.

Je krijgt bekendmakingen uit de ring, elk met de feiten die bekend zijn. Geef per bekendmaking:
1. "strategie": voor welk type investeerder dit signaal relevant is. Kies EEN uit:
   uitponden | buy-and-hold | splitsen | kamerverhuur | transformatie | verduurzaming | geen

   Gebruik "geen" alleen bij echt marktloze items (kozijnwijziging, garagegevel, administratieve correctie). Bij twijfel kies je het dichtstbijzijnde label. Richtlijn:
   - samenvoegen, woningonttrekking, kadastrale splitsing -> splitsen
   - tijdelijke verhuur, huisvestingsvergunning, verhuurvergunning -> buy-and-hold
   - kamerverhuur, brandveilig gebruik, onzelfstandige woonruimte -> kamerverhuur
   - functiewijziging, BOPA, kantoor of winkel naar wonen -> transformatie
   - isolatie, warmtepomp, label, zonnepanelen, gevelrenovatie -> verduurzaming
   - nieuwbouw of oplevering die het aanbod raakt -> uitponden

2. "duiding": EEN zin over wat dit mechanisch betekent voor de markt.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS. Dit is de belangrijkste regel.
- Je mag UITSLUITEND getallen noemen die letterlijk in de aangeleverde feiten staan.
- Verzin NOOIT huurprijzen, koopsommen, rendementen, yields, percentages, investeringsbedragen of huurstromen. Die gegevens heb je niet.
- Schrijf ook geen vage schattingen als "circa", "ruwweg" of "naar schatting" bij een bedrag. Als je het bedrag niet hebt gekregen, noem je het niet.
- Staan er geen cijfers in de feiten? Dan is je duiding puur kwalitatief. Dat is prima en beter dan een gok.

Goede duiding gaat over het MECHANISME, niet over verzonnen bedragen:
- "Samenvoegen haalt een unit uit de kleine voorraad, wat het aanbod in dat segment verkrapt."
- "Vergunning bevestigt dat verkamering op deze locatie planologisch haalbaar is, relevant voor wie een vergelijkbaar pand overweegt."
- "Vergunde isolatie laat zien dat labelverbetering aan de buitenzijde hier vergunbaar is, ook bij oudere bebouwing."
- "Tijdelijke verhuur wijst op overbrugging voor verkoop of verbouwing; het pand komt op termijn waarschijnlijk op de markt."

OVERIGE REGELS:
- Geen geografisch commentaar over afstand of ligging. Het filter is al toegepast.
- Geen algemeenheden zoals "bevestigt de trend" of "interessant signaal".
- Komen meerdere gelijksoortige items voor, geef elk een EIGEN invalshoek. Nooit twee keer dezelfde zin.
- Nooit specifieke beleggers of portefeuilles benoemen. Schrijf onpersoonlijk over de markt.
- Maximaal 30 woorden per duiding. Nederlands."""
# --------------------------------------------------------------------------


def bouw_cql(vanaf_datum: str) -> str:
    return " and ".join([
        "c.product-area==officielepublicaties",
        "w.organisatietype==gemeente",
        f'dt.creator=="{GEMEENTE}"',
        f'dt.date>="{vanaf_datum}"',
    ])


def haal_records(cql: str):
    records, start = [], 1
    while True:
        params = {"version": "2.0", "operation": "searchRetrieve", "query": cql,
                  "maximumRecords": MAX_PER_PAGINA, "startRecord": start}
        url = SRU_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        pagina = [el for el in root.iter() if _lokaal(el.tag) == "record"]
        if not pagina:
            break
        records.extend(pagina)
        totaal = _eerste_tekst(root, "numberOfRecords")
        totaal = int(totaal) if totaal and totaal.isdigit() else len(records)
        start += MAX_PER_PAGINA
        if start > totaal or start > 4200:
            break
    return records


def _lokaal(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _eerste_tekst(element, local_name: str):
    for el in element.iter():
        if _lokaal(el.tag) == local_name and el.text:
            return el.text.strip()
    return None


def _url_uit_record(record):
    for el in record.iter():
        if _lokaal(el.tag) in ("preferredUrl", "itemUrl") and el.text and el.text.startswith("http"):
            return el.text.strip()
    for el in record.iter():
        for waarde in el.attrib.values():
            if isinstance(waarde, str) and waarde.startswith("http"):
                return waarde
    return None


def parse_record(record) -> dict:
    return {
        "titel": _eerste_tekst(record, "title") or "(geen titel)",
        "datum": _eerste_tekst(record, "date") or _eerste_tekst(record, "available") or "",
        "type": _eerste_tekst(record, "type") or "",
        "url": _url_uit_record(record) or "",
        "gevolg": "",
    }


def in_ring(item: dict) -> bool:
    hooi = (item["titel"] + " " + item["type"]).lower()
    if any(pc in hooi for pc in RING_POSTCODES):
        return True
    return any(s.lower() in hooi for s in RING_STRATEN)


def classificeer(item: dict):
    hooi = (item["titel"] + " " + item["type"]).lower()
    if any(w in hooi for w in KERN):
        return "kern"
    if any(w in hooi for w in UITSLUITEN):
        return None
    if any(w in hooi for w in REL_BASIS):
        return "overige"
    return None


def _adres_uit_titel(titel: str):
    """Haalt (straat, huisnummer, letter) uit een bekendmakingstitel.
    Voorbeeld: '... aan St. Annastraat 240, 6525GZ Nijmegen' -> ('St. Annastraat','240',None)
    Titels bevatten vaak eerder al het woord 'aan' ('aan de voorgevel'), dus we nemen
    de LAATSTE 'aan' voor de postcode. Bij meerdere nummers ('51 en 53') het eerste."""
    pc = re.search(r",?\s+\d{4}\s?[A-Z]{2}\s+Nijmegen", titel)
    if not pc:
        return None
    kop = titel[:pc.start()]
    delen = re.split(r"\baan\s+", kop, flags=re.IGNORECASE)
    if len(delen) < 2:
        return None
    straatdeel = delen[-1].strip().rstrip(",").strip()
    straatdeel = re.split(r"\s+en\s+\d", straatdeel)[0].strip()
    a = re.match(r"^(.+?)\s+(\d+)\s*([A-Za-z])?\s*$", straatdeel)
    if not a:
        return None
    return a.group(1).strip(), a.group(2), (a.group(3) or "").upper() or None


def _kamers_uit_titel(titel: str):
    """Haalt het aantal kamers uit bijvoorbeeld '(9 kamers)' of 'met 15 kamers'."""
    m = re.search(r"(\d+)\s*kamers", titel, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _bag_feiten(straat, huisnr, letter):
    """Oppervlakte en bouwjaar uit de BAG. Geeft None terug zonder key of bij een misser."""
    if not BAG_API_KEY:
        return None
    params = {
        "openbareRuimteNaam": straat,
        "huisnummer": huisnr,
        "woonplaatsNaam": "Nijmegen",
        "exacteMatch": "true",
    }
    if letter:
        params["huisletter"] = letter
    try:
        r = requests.get(
            "https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2/adressenuitgebreid",
            headers={"X-Api-Key": BAG_API_KEY,
                     "Accept": "application/hal+json",
                     "Accept-Crs": "epsg:28992"},
            params=params, timeout=20)
        if r.status_code != 200:
            return None
        adressen = r.json().get("_embedded", {}).get("adressen", [])
        if not adressen:
            return None
        a = adressen[0]
        bouwjaar = a.get("adresseerbaarObjectBouwjaar")
        if isinstance(bouwjaar, list) and bouwjaar:
            bouwjaar = bouwjaar[0]
        return {"oppervlakte": a.get("oppervlakte"), "bouwjaar": bouwjaar}
    except Exception as e:
        print(f"  BAG-fout {straat} {huisnr}: {e}", file=sys.stderr)
        return None


def verrijk_met_bag(items: list):
    """Zet harde feiten uit de BAG bij elk item. Deze cijfers zijn gemeten, niet geschat."""
    if not BAG_API_KEY:
        print("Geen BAG_API_KEY: bekendmakingen zonder oppervlakte-feiten", file=sys.stderr)
        return
    raak = 0
    for it in items:
        it["feiten"] = {}
        adres = _adres_uit_titel(it["titel"])
        if not adres:
            continue
        feiten = _bag_feiten(*adres)
        time.sleep(1.1)  # BAG fair use
        if not feiten:
            continue
        if feiten.get("oppervlakte"):
            it["feiten"]["oppervlakte_m2"] = feiten["oppervlakte"]
        if feiten.get("bouwjaar"):
            it["feiten"]["bouwjaar"] = feiten["bouwjaar"]
        kamers = _kamers_uit_titel(it["titel"])
        if kamers:
            it["feiten"]["kamers"] = kamers
            if feiten.get("oppervlakte"):
                it["feiten"]["m2_per_kamer"] = round(feiten["oppervlakte"] / kamers)
        if it["feiten"]:
            raak += 1
    print(f"BAG-feiten gevonden voor {raak}/{len(items)} bekendmakingen", file=sys.stderr)


def _parse_annotaties(tekst: str, n: int) -> dict:
    """Haalt {index: {strategie, duiding}} uit het JSON-antwoord.
    Bestand tegen afgekapte JSON: redt losse objecten uit een halve array."""
    schoon = tekst.strip()
    if schoon.startswith("```"):
        schoon = schoon.split("```")[1]
        if schoon.startswith("json"):
            schoon = schoon[4:]
    schoon = schoon.strip()

    data = None
    try:
        data = json.loads(schoon)
    except json.JSONDecodeError:
        # Afgekapte respons: pak losse {...} objecten eruit
        data = []
        for m in re.finditer(r"\{[^{}]*\}", schoon):
            try:
                data.append(json.loads(m.group(0)))
            except json.JSONDecodeError:
                continue
        if not data:
            raise

    uit = {}
    for rij in data:
        if not isinstance(rij, dict):
            continue
        i = rij.get("i")
        if isinstance(i, int) and 0 <= i < n:
            uit[i] = {
                "strategie": str(rij.get("strategie", "")).strip().lower(),
                "duiding": str(rij.get("duiding", rij.get("gevolg", ""))).strip(),
            }
    return uit


def verrijk(items: list):
    """Zet bij elk item een strategie-label en duiding via de Anthropic-API."""
    for it in items:
        it["strategie"] = ""
        it["gevolg"] = ""
    if not ANTHROPIC_API_KEY or not items:
        return
    regels = []
    for i, it in enumerate(items):
        feiten = it.get("feiten") or {}
        if feiten:
            feitentekst = ", ".join(f"{k}={v}" for k, v in feiten.items())
            regels.append(f"{i}. {it['titel']}\n   BEKENDE FEITEN: {feitentekst}")
        else:
            regels.append(f"{i}. {it['titel']}\n   BEKENDE FEITEN: geen")
    lijst = "\n".join(regels)
    prompt = (f"Bekendmakingen:\n{lijst}\n\n"
              "Gebruik uitsluitend de getallen onder BEKENDE FEITEN. Staat daar 'geen', "
              "noem dan geen enkel cijfer in je duiding.\n\n"
              "Antwoord met ALLEEN een JSON-array, per bekendmaking een object "
              '{"i": <index>, "strategie": "<label>", "duiding": "<een zin>"}. '
              "Geen tekst eromheen.")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 4000, "system": PROFIEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=90)
        resp.raise_for_status()
        body = resp.json()
        tekst = "".join(b.get("text", "") for b in body.get("content", []))
        if body.get("stop_reason") == "max_tokens":
            print("LET OP: antwoord afgekapt op max_tokens", file=sys.stderr)
        annotaties = _parse_annotaties(tekst, len(items))
        print(f"Duiding gelukt voor {len(annotaties)}/{len(items)} items", file=sys.stderr)
        for i, it in enumerate(items):
            a = annotaties.get(i, {})
            it["strategie"] = a.get("strategie", "")
            it["gevolg"] = a.get("duiding", "")
    except Exception as e:  # noqa
        print(f"Duiding overgeslagen: {e}", file=sys.stderr)


def _regel(it: dict) -> str:
    link = f"([bron]({it['url']}))" if it["url"] else ""
    regel = f"- **{it['datum']}** . {it['titel']} {link}"

    feiten = it.get("feiten") or {}
    if feiten:
        delen = []
        if feiten.get("oppervlakte_m2"):
            delen.append(f"{feiten['oppervlakte_m2']} m²")
        if feiten.get("bouwjaar"):
            delen.append(f"bouwjaar {feiten['bouwjaar']}")
        if feiten.get("m2_per_kamer"):
            delen.append(f"{feiten['m2_per_kamer']} m² per kamer")
        if delen:
            regel += f"\n  `BAG: {' . '.join(delen)}`"

    strat = (it.get("strategie") or "").strip()
    duiding = (it.get("gevolg") or "").strip()
    if duiding:
        if strat and strat != "geen":
            regel += f"\n  **[{strat}]** _{duiding}_"
        else:
            regel += f"\n  _{duiding}_"
    return regel


def render_digest(kern: list, overige: list, vanaf: str) -> str:
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    r = [f"# Bekendmakingen ring Keizer Karelplein - {vandaag}",
         f"_Gemeente {GEMEENTE}, publicaties vanaf {vanaf}. "
         f"{len(kern)} kernsignalen, {len(overige)} overige._", ""]
    r.append(f"## Kernsignalen ({len(kern)})")
    r.append("_Splitsen, samenvoegen, omzetten, transformatie, kamerverhuur, nieuwbouw._")
    r.append("")
    if kern:
        for it in sorted(kern, key=lambda x: x["datum"], reverse=True):
            r.append(_regel(it))
    else:
        r.append("Geen kernsignalen in deze periode.")
    r.append("")
    if overige:
        r.append(f"## Overige relevante bekendmakingen ({len(overige)})")
        r.append("_Verbouw, renovatie, sloop, verduurzaming e.d._")
        r.append("")
        for it in sorted(overige, key=lambda x: x["datum"], reverse=True):
            r.append(_regel(it))
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dagen", type=int, default=2)
    ap.add_argument("--alles", action="store_true")
    ap.add_argument("--uit", default="bekendmakingen_digest.md")
    args = ap.parse_args()

    vanaf = (dt.date.today() - dt.timedelta(days=args.dagen)).isoformat()
    cql = bouw_cql(vanaf)
    print(f"Query: {cql}", file=sys.stderr)

    try:
        records = haal_records(cql)
    except Exception as e:  # noqa
        print(f"Ophalen mislukt: {e}", file=sys.stderr)
        sys.exit(1)

    items = [parse_record(r) for r in records]
    if not args.alles:
        items = [it for it in items if in_ring(it)]

    gezien, kern, overige = set(), [], []
    for it in items:
        sleutel = (it["titel"], it["datum"])
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        soort = classificeer(it)
        if soort == "kern":
            kern.append(it)
        elif soort == "overige":
            overige.append(it)

    verrijk_met_bag(kern + overige)  # harde feiten uit de BAG, gemeten niet geschat
    verrijk(kern + overige)  # duiding voor alle getoonde items in een call

    digest = render_digest(kern, overige, vanaf)
    print(digest)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"\nDigest opgeslagen in {args.uit}", file=sys.stderr)


if __name__ == "__main__":
    main()
