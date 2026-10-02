#!/usr/bin/env python3
"""
Wanneer stond een pand te koop, en wanneer is het verkocht?

Het probleem: alle 505 geplakte verkopen dragen de datum waarop ze zijn
geplakt, 28 september. Dat is niet onzeker maar aantoonbaar onjuist. En bij een
deel van het aanbod kennen we de plaatsingsdatum niet, waardoor "dagen te koop"
leeg blijft; juist dat getal zegt of een pand blijft hangen.

Dit haalt een INDICATIE op met het taalmodel, dat daarbij zelf het web
doorzoekt. Vier waarborgen, want een model dat iets niet kan vinden geeft
zelden "ik weet het niet" terug maar een plausibel getal:

1. Zonder bronvermelding wordt het antwoord weggegooid. Geen bron, geen datum.
2. De bron komt mee in het bestand, zodat elk getal naar zijn herkomst wijst.
3. Datums mogen meerekenen, bedragen niet. Een datum die er een week naast zit
   verandert niets aan een doorlooptijd van drie maanden; een verkoopprijs die
   5% afwijkt verschuift de groottepremie en daarmee elke ontwikkelcase.
4. Dit overschrijft nooit een Kadastercijfer of iets wat Mark zelf heeft
   ingevoerd. Komt er later een echte levering, dan vervangt die deze regels.

Gebruik:
  python verkoopdatum_model.py --proef 20     twintig panden, niets bewaren
  python verkoopdatum_model.py --per-ronde 50 vijftig panden, wel bewaren
  python verkoopdatum_model.py --controle     toetsen aan wat we al weten
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

UIT_PAD = "verkoopdatums_model.json"
AANBOD_PAD = "verkopen.txt"
API = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_PER_RONDE = 50

VRAAG = """Zoek op funda.nl of een andere openbare bron wanneer de woning op dit \
adres te koop is aangeboden en wanneer die is verkocht:

{adres}, Nijmegen

Antwoord met ALLEEN een JSON-object, zonder tekst eromheen:
{{"te_koop_vanaf": "JJJJ-MM-DD of null",
  "verkocht_op": "JJJJ-MM-DD of null",
  "laatste_vraagprijs": getal of null,
  "bron": "de url of de naam van de pagina waar je dit vond",
  "zeker": "hoog, midden of laag"}}

Regels die je strikt volgt:
- Vind je het niet, zet dan overal null en bron op null. Verzin niets.
- Een datum die je afleidt uit "3 maanden te koop" zonder dat de datum er \
letterlijk staat, is een afleiding: zet zeker op laag.
- Een bedrag op funda bij een verkochte woning is de laatste vraagprijs, niet \
de verkoopprijs. Vul die in als laatste_vraagprijs."""


def _sleutel(adres):
    return "".join(c for c in (adres or "").lower() if c.isalnum())


def lees(pad=UIT_PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def te_doen(pad=AANBOD_PAD, bekend=None, alles=False):
    """
    Panden waarvan we de datum niet betrouwbaar kennen.

    Dat zijn de geplakte verkopen, die allemaal de plakdatum dragen, en de
    panden in het aanbod zonder plaatsingsdatum.
    """
    bekend = bekend or {}
    uit, gezien = [], set()
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 6:
                    continue
                adres, status, bron = v[0], v[3].lower(), v[5].lower()
                sleutel = _sleutel(adres)
                if sleutel in gezien or sleutel in bekend:
                    continue
                verdacht = ("plak" in bron
                            or status.startswith("verkocht")
                            or not v[4])
                if alles or verdacht:
                    gezien.add(sleutel)
                    uit.append(adres)
    except FileNotFoundError:
        return []
    return uit


def _vraag_model(adres, sleutel):
    """Een pand voorleggen, met webzoeken aan, en het antwoord lezen."""
    body = {
        "model": MODEL,
        "max_tokens": 600,
        "messages": [{"role": "user",
                      "content": VRAAG.format(adres=adres)}],
        "tools": [{"type": "web_search_20250305", "name": "web_search",
                   "max_uses": 4}],
    }
    verzoek = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json",
                 "x-api-key": sleutel,
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(verzoek, timeout=120) as r:
        antwoord = json.load(r)
    tekst = "".join(blok.get("text", "") for blok in antwoord.get("content", [])
                    if blok.get("type") == "text")
    m = re.search(r"\{.*\}", tekst, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _geldig(d):
    """Alleen bewaren wat een bron heeft en een bruikbare datum."""
    if not isinstance(d, dict) or not d.get("bron"):
        return None
    datums = {}
    for veld in ("te_koop_vanaf", "verkocht_op"):
        waarde = d.get(veld)
        if isinstance(waarde, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", waarde):
            try:
                dt.date.fromisoformat(waarde)
                datums[veld] = waarde
            except ValueError:
                continue
    if not datums:
        return None
    datums["bron"] = str(d.get("bron"))[:200]
    datums["zeker"] = d.get("zeker") or "laag"
    # Het bedrag gaat mee als context en wordt nergens in meegerekend.
    prijs = d.get("laatste_vraagprijs")
    if isinstance(prijs, (int, float)) and 20000 < prijs < 5000000:
        datums["laatste_vraagprijs"] = int(prijs)
    datums["herkomst"] = "model met webzoeken"
    datums["opgehaald"] = dt.date.today().isoformat()
    return datums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", type=int, default=0,
                    help="zoveel panden proberen en tonen, niets bewaren")
    ap.add_argument("--per-ronde", type=int, default=MAX_PER_RONDE)
    ap.add_argument("--controle", action="store_true",
                    help="toetsen aan panden waarvan we de datum al kennen")
    args = ap.parse_args()

    sleutel = os.environ.get("ANTHROPIC_API_KEY")
    if not sleutel:
        print("Geen ANTHROPIC_API_KEY; stap overgeslagen", file=sys.stderr)
        return 0

    bekend = lees()
    wachtrij = te_doen(bekend=bekend if not args.proef else {})
    aantal = args.proef or args.per_ronde
    wachtrij = wachtrij[:aantal]
    if not wachtrij:
        print("Niets te doen", file=sys.stderr)
        return 0

    raak = mis = 0
    for adres in wachtrij:
        try:
            rauw = _vraag_model(adres, sleutel)
        except Exception as e:
            print(f"  {adres}: {str(e)[:80]}", file=sys.stderr)
            mis += 1
            continue
        d = _geldig(rauw)
        if not d:
            mis += 1
            print(f"  {adres}: niets bruikbaars", file=sys.stderr)
            continue
        raak += 1
        print(f"  {adres}: te koop {d.get('te_koop_vanaf', '?')}, "
              f"verkocht {d.get('verkocht_op', '?')}, zeker {d['zeker']}, "
              f"bron {d['bron'][:60]}", file=sys.stderr)
        if not args.proef:
            bekend[_sleutel(adres)] = dict(d, adres=adres)

    if not args.proef:
        with open(UIT_PAD, "w", encoding="utf-8") as f:
            json.dump(bekend, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Verkoopdatums: {raak} gevonden, {mis} niet, "
          f"{len(bekend)} in het bestand"
          + (" (proef, niets bewaard)" if args.proef else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
