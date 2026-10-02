#!/usr/bin/env python3
"""
Hoeveel panden staan er te koop en te huur, en hoe verandert dat?

Aanleiding: om te zien of er een uitpondgolf is, moet je een reeks hebben. Wij
telden elke dag wel hoeveel panden er in beeld waren, maar bewaarden het niet.

Drie maten, en ze zijn niet even betrouwbaar:

- VOORRAAD, het aantal panden dat bij ons als te koop staat. Dit is de zwakste
  maat, want ons aanbod groeit alleen aan: een pand dat verkocht wordt zonder
  dat wij het horen, blijft staan. Een oplopende voorraad kan dus ophoping zijn
  in plaats van marktgroei. Staat er wel in, met die waarschuwing.
- INSTROOM, het aantal panden dat er op een dag bij komt. Dit is wel zuiver,
  want elke nieuwe advertentie is een waarneming met een datum. Voor een golf
  is dit de maat om naar te kijken.
- UITPONDSIGNAAL, nieuw aangeboden panden die bij ons als kamerverhuur bekend
  staan, uit het register of een melding brandveilig gebruik. Dat is geen
  omweg: het is precies waar een uitpondgolf uit bestaat, namelijk verhuurd
  bezit dat te koop gaat.
"""
import argparse
import datetime as dt
import json
import sys

REEKS_PAD = "aanbod_reeks.json"
AANBOD_PAD = "verkopen.txt"
KAMER_PAD = "kamerverhuur_objecten.json"


def _sleutel(adres):
    return "".join(c for c in (adres or "").lower() if c.isalnum())


def lees_kamerpanden(pad=KAMER_PAD):
    """Adressen die bij ons als kamerverhuur bekend staan."""
    try:
        with open(pad, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return set()
    uit = set()
    rijen = d.values() if isinstance(d, dict) else d
    for rij in rijen:
        if isinstance(rij, dict):
            adres = rij.get("adres") or rij.get("straat")
            if adres:
                uit.add(_sleutel(adres))
        elif isinstance(rij, str):
            uit.add(_sleutel(rij))
    return uit


def tel(pad=AANBOD_PAD, vandaag=None):
    """De drie maten voor vandaag."""
    vandaag = vandaag or dt.date.today().isoformat()
    kamerpanden = lees_kamerpanden()
    te_koop, te_huur = set(), set()
    nieuw_koop, nieuw_huur, uitpond = [], [], []
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 5:
                    continue
                adres, status, datum = v[0], v[3].lower(), v[4]
                if status.startswith("te koop"):
                    te_koop.add(_sleutel(adres))
                    if datum == vandaag:
                        nieuw_koop.append(adres)
                        if _sleutel(adres) in kamerpanden:
                            uitpond.append(adres)
                elif status.startswith("te huur"):
                    te_huur.add(_sleutel(adres))
                    if datum == vandaag:
                        nieuw_huur.append(adres)
    except FileNotFoundError:
        return None
    return {"datum": vandaag,
            "te_koop": len(te_koop), "te_huur": len(te_huur),
            "nieuw_te_koop": len(nieuw_koop), "nieuw_te_huur": len(nieuw_huur),
            "uitpond": len(uitpond), "uitpond_adressen": uitpond[:10]}


def bijwerken(stand, pad=REEKS_PAD):
    """De reeks aanvullen. Dezelfde dag overschrijft, dus een tweede run telt niet dubbel."""
    try:
        with open(pad, encoding="utf-8") as f:
            reeks = json.load(f) or {}
    except Exception:
        reeks = {}
    reeks[stand["datum"]] = {k: v for k, v in stand.items() if k != "datum"}
    with open(pad, "w", encoding="utf-8") as f:
        json.dump(reeks, f, ensure_ascii=False, indent=1, sort_keys=True)
    return reeks


def samenvatting(reeks, weken=4):
    """
    Wat de reeks zegt over de instroom.

    Per week optellen in plaats van per dag, want dagcijfers zijn te klein en
    attenderingen komen met pieken binnen.
    """
    per_week = {}
    for datum, d in sorted(reeks.items()):
        try:
            week = dt.date.fromisoformat(datum).strftime("%G-W%V")
        except ValueError:
            continue
        w = per_week.setdefault(week, {"nieuw_te_koop": 0, "nieuw_te_huur": 0,
                                       "uitpond": 0, "te_koop": 0})
        w["nieuw_te_koop"] += d.get("nieuw_te_koop", 0)
        w["nieuw_te_huur"] += d.get("nieuw_te_huur", 0)
        w["uitpond"] += d.get("uitpond", 0)
        w["te_koop"] = d.get("te_koop", 0)      # stand aan het eind van de week
    laatste = sorted(per_week)[-weken:]
    return {w: per_week[w] for w in laatste}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=REEKS_PAD)
    args = ap.parse_args()
    stand = tel()
    if not stand:
        print(f"{AANBOD_PAD} niet gevonden", file=sys.stderr)
        return 0
    reeks = bijwerken(stand, args.uit)
    print(f"Aanbod {stand['datum']}: {stand['te_koop']} te koop, "
          f"{stand['te_huur']} te huur; vandaag nieuw "
          f"{stand['nieuw_te_koop']} koop en {stand['nieuw_te_huur']} huur"
          + (f"; {stand['uitpond']} daarvan staan bij ons als kamerverhuur "
             f"bekend" if stand["uitpond"] else ""), file=sys.stderr)
    for week, w in samenvatting(reeks).items():
        print(f"  {week}: {w['nieuw_te_koop']} nieuw te koop, "
              f"{w['nieuw_te_huur']} nieuw te huur, {w['uitpond']} uitpond",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
