#!/usr/bin/env python3
"""
Bekendmakingen-blok voor de Nijmegen Vastgoedmonitor.

Haalt officiele bekendmakingen van gemeente Nijmegen op via de KOOP SRU-API,
filtert op de ring rond het Keizer Karelplein, gooit ruis weg, splitst de rest
in KERNSIGNALEN en OVERIGE, en zet bij elk bericht een korte duiding
"wat betekent dit voor Derksen" via de Anthropic-API. Schrijft markdown weg.

Bronnen:
  Bekendmakingen : https://repository.overheid.nl/sru  (open, geen sleutel)
  Duiding        : https://api.anthropic.com/v1/messages (vereist ANTHROPIC_API_KEY)

Zonder ANTHROPIC_API_KEY werkt alles gewoon, alleen zonder de duiding-zin.
"""

import argparse
import datetime as dt
import json
import os
import sys
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
    "Graafsedwarsstraat", "Eerste Oude Heselaan",
    "Fransestraat", "Van Spaenstraat",
    "Bottendaalseweg", "Groesbeekseweg", "Berg en Dalseweg", "Sint Annastraat",
    "Graafseweg", "Voorstadslaan", "Waterstraat", "Biezenstraat",
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
MODEL = "claude-sonnet-5"
PROFIEL = """Je bent de vastgoedanalist van Derksen Vastgoed in Nijmegen. Context:
- Verhuurt woningen via BV. Eigen panden: Graafsedwarsstraat 58-60 en Eerste Oude Heselaan 86-88A (Waterkwartier).
- Acquisitietargets: Fransestraat en Van Spaenstraat (Galgenveld).
- Waardecreatie-model: kopen, bij mutatie renoveren, label omhoog, splitsen waar kan, beter verhuren. Vuistregel: bod = 17x jaarhuur.

Je krijgt bekendmakingen uit zijn ring (geografische filter is AL toegepast). Geef per bekendmaking EEN korte zakelijke zin met concrete betekenis. Kies uit:
- referentiepunt voor waardering van zijn eigen bezit
- signaal voor huurniveau in zijn segment (studenten/starters/middenhuur)
- concurrent-activiteit (andere splitser/verhuurder in vergelijkbaar model)
- acquisitiekans of -risico (pand komt vrij, buurtbeweging)
- betekenis voor huurderskwaliteit of verhuurbaarheid

STRIKTE REGELS:
- NOOIT commentaar op locatie of afstand tot zijn ring. Dat filter is al gedaan; noemen is ruis.
- NOOIT algemeenheden ("bevestigt trend", "interessant marktsignaal", "brengt weinig verandering").
- Als een item echt marginaal is (bv. kleine kozijnwijziging elders): geef alsnog EEN zin, bv. "geen impact op eigen bezit of huurniveau" of "administratieve wijziging zonder marktbetekenis". Laat NIET leeg.
- Kort en zakelijk. Nederlands. Max 25 woorden per zin."""
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


def _parse_annotaties(tekst: str, n: int) -> dict:
    """Haalt {index: gevolg} uit het JSON-antwoord van het model."""
    schoon = tekst.strip()
    if schoon.startswith("```"):
        schoon = schoon.split("```")[1]
        if schoon.startswith("json"):
            schoon = schoon[4:]
    data = json.loads(schoon)
    uit = {}
    for rij in data:
        i = rij.get("i")
        if isinstance(i, int) and 0 <= i < n:
            uit[i] = str(rij.get("gevolg", "")).strip()
    return uit


def verrijk(items: list):
    """Zet bij elk item een duiding-zin via de Anthropic-API."""
    if not ANTHROPIC_API_KEY or not items:
        return
    lijst = "\n".join(f"{i}. {it['titel']}" for i, it in enumerate(items))
    prompt = (f"Bekendmakingen:\n{lijst}\n\n"
              "Antwoord met ALLEEN een JSON-array, per bekendmaking een object "
              '{"i": <index>, "gevolg": "<een zin>"}. Geen tekst eromheen.')
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 1200, "system": PROFIEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        resp.raise_for_status()
        tekst = "".join(b.get("text", "") for b in resp.json().get("content", []))
        annotaties = _parse_annotaties(tekst, len(items))
        for i, it in enumerate(items):
            it["gevolg"] = annotaties.get(i, "")
    except Exception as e:  # noqa
        print(f"Duiding overgeslagen: {e}", file=sys.stderr)


def _regel(it: dict) -> str:
    link = f"([bron]({it['url']}))" if it["url"] else ""
    regel = f"- **{it['datum']}** . {it['titel']} {link}"
    if it.get("gevolg"):
        regel += f"\n  → _{it['gevolg']}_"
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

    verrijk(kern + overige)  # duiding voor alle getoonde items in een call

    digest = render_digest(kern, overige, vanaf)
    print(digest)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(digest)
    print(f"\nDigest opgeslagen in {args.uit}", file=sys.stderr)


if __name__ == "__main__":
    main()
