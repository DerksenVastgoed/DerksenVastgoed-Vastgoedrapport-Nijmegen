#!/usr/bin/env python3
"""
De potentie van elke woning in de ring: welke routes staan open, los van de prijs.

WAAROM DIT BESTAAT. Mark, 15 oktober 2026: "alle panden inzichtelijk maken, en
op het moment dat een pand voldoet en ook te koop wordt aangeboden, komt het
op de lijst." De shortlist in de bijlage beoordeelt wat te koop staat. Dit is
de laag eronder: voor elke woning in de zes ringbuurten wat er juridisch en
fysiek kan, zodat een pand al bekend is voordat het in de verkoop komt.

WAT PER WONING WORDT BEPAALD, en waar het vandaan komt:
  kamers      open, geblokkeerd (insluiting, reeks, weerszijden), niet te
              toetsen, al kamerpand, of te klein. Uit kamerroute_geblokkeerd()
              in marktprijzen_bag, dezelfde toets die de terugtoets heeft
              doorstaan. Te klein onder 100 m2, dezelfde grens als
              haalbare_routes().
  splitsen    open als 90 procent van de oppervlakte minstens twee woningen
              van MIN_UNIT_M2 oplevert. Een appartement in een complex van vier
              of meer woningen gaat via de VvE en staat apart.
  label       E, F of G is een labelsprong, de kern van de thesis van Derksen
              Vastgoed.
  te koop     uit het aanbod, en of het op de shortlist van vandaag staat.

WAT ER NIET IN ZIT, en dus bij elk getal hoort:
  - de WOZ van de meeste woningen kennen we niet, dus de WOZ-ondergrens voor
    kamers en de opkoopbescherming zitten hier niet in; die toetst de
    shortlist bij verkoop;
  - de indeling per etage kennen we niet. Mark splitst geen etage van 40 m2
    in twee woningen; die regel kan hier pas mee als de bouwlagen bekend zijn.

  python3 potentie.py            # schrijft potentie_ring.json en .md
  python3 potentie.py --proef
"""
import argparse
import collections
import datetime as dt
import json
import sys

import marktprijzen_bag as mb
import pandsleutel as _psl

VOORRAAD = "voorraad.json"
SHORTLIST = "shortlist.json"
UIT_JSON = "potentie_ring.json"
UIT_MD = "potentie_ring.md"

KAMERS_VANAF_M2 = 100          # zelfde grens als haalbare_routes()
LABELSPRONG = ("E", "F", "G")
COMPLEX_VANAF = 4              # zelfde als APPARTEMENT_VANAF


def kamerstatus(adres, opp, kamerpand):
    """open, geblokkeerd, niet te toetsen, al kamerpand of te klein."""
    if kamerpand:
        return "al kamerpand", ""
    if not opp or opp < KAMERS_VANAF_M2:
        return "te klein", ""
    _ing, reden = mb.kamerroute_geblokkeerd(adres)
    if reden in ("insluiting", "reeks", "weerszijden"):
        return "geblokkeerd", reden
    if reden == "gekeken en niets gevonden":
        return "open", ""
    return "niet te toetsen", reden


def splitsstatus(opp, in_complex):
    if in_complex:
        return "via VvE"
    if opp and opp * mb.VERHUURBAAR_SPLITSING >= 2 * mb.MIN_UNIT_M2:
        return "open"
    return "te klein"


def bepaal(voorraad, te_koop=(), shortlist=()):
    """Een record per woning in de ringbuurten."""
    adressen = {k: r for k, r in (voorraad.get("adressen") or {}).items()
                if r.get("herkomst") == "focusbuurt"
                and "in gebruik" in (r.get("status") or "").lower()}
    per_pand = collections.Counter(r.get("pand") for r in adressen.values()
                                   if r.get("pand"))
    koop = {_psl.sleutel(a) for a in te_koop}
    # Op object-id waar de shortlist het kent, anders op adres.
    lijst = {_psl.sleutel(p.get("adres") or ""): p for p in shortlist}
    lijst_vbo = {p["vbo"]: p for p in shortlist if p.get("vbo")}
    uit = {}
    for vbo, r in adressen.items():
        adres = r.get("adres") or ""
        opp = r.get("oppervlakte")
        complex_ = per_pand.get(r.get("pand"), 0) >= COMPLEX_VANAF
        kamerpand = bool(mb.kamerverhuur_bekend({"adres": adres}))
        k, k_reden = kamerstatus(adres, opp, kamerpand)
        sl = _psl.sleutel(adres)
        label = (r.get("label") or "")[:1].upper() or None
        uit[vbo] = {
            "adres": adres, "punt": r.get("punt"),
            "buurt": (r.get("buurten") or [None])[0],
            "m2": opp, "bouwjaar": r.get("pand_bouwjaar"), "label": label,
            "kamers": k, "kamers_reden": k_reden,
            "splitsen": splitsstatus(opp, complex_),
            "labelsprong": label in LABELSPRONG,
            "te_koop": sl in koop,
            "shortlist": ((lijst_vbo.get(vbo) or lijst.get(sl) or {})
                          .get("factor")),
        }
    return uit


def samenvatting(rijen):
    per_buurt = collections.defaultdict(collections.Counter)
    for r in rijen.values():
        b = r["buurt"] or "onbekend"
        per_buurt[b]["woningen"] += 1
        per_buurt[b]["kamers " + r["kamers"]] += 1
        per_buurt[b]["splitsen " + r["splitsen"]] += 1
        if r["labelsprong"]:
            per_buurt[b]["labelsprong"] += 1
        if r["te_koop"]:
            per_buurt[b]["te koop"] += 1
        if r["shortlist"]:
            per_buurt[b]["shortlist"] += 1
    regels = ["# Potentie van de ring", "",
              f"Bijgewerkt {dt.date.today().isoformat()}. Per woning in de zes "
              f"ringbuurten welke routes openstaan, los van de prijs. De WOZ "
              f"en de indeling per etage zitten hier niet in; de shortlist "
              f"toetst die bij verkoop.", "",
              "| buurt | woningen | kamers open | kamers geblokkeerd | al kamerpand "
              "| splitsen open | labelsprong E-G | te koop | shortlist |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for b, c in sorted(per_buurt.items(), key=lambda x: -x[1]["woningen"]):
        regels.append(f"| {b} | {c['woningen']} | {c['kamers open']} "
                      f"| {c['kamers geblokkeerd']} | {c['kamers al kamerpand']} "
                      f"| {c['splitsen open']} | {c['labelsprong']} "
                      f"| {c['te koop']} | {c['shortlist']} |")
    return regels


def proef():
    """De indeling op vaste gevallen, zonder bestanden of netwerk."""
    afw = []
    if kamerstatus("Proefstraat 1", 80, False)[0] != "te klein":
        afw.append("een woning van 80 m2 krijgt een kamerroute")
    if kamerstatus("Proefstraat 1", 200, True)[0] != "al kamerpand":
        afw.append("een bekend kamerpand wordt opnieuw getoetst")
    if splitsstatus(120, True) != "via VvE":
        afw.append("een appartement in een complex kan zomaar worden gesplitst")
    if splitsstatus(40, False) != "te klein":
        afw.append("40 m2 wordt gesplitst")
    if splitsstatus(120, False) != "open":
        afw.append("120 m2 kan niet worden gesplitst")
    # Een te koop staand pand op de shortlist komt erin met zijn factor.
    v = {"adressen": {"v1": {"adres": "Proefstraat 1", "herkomst": "focusbuurt",
                             "status": "Verblijfsobject in gebruik",
                             "oppervlakte": 60, "pand": "p1", "label": "F",
                             "buurten": ["Bottendaal"]}}}
    r = bepaal(v, te_koop=["Proefstraat 1"],
               shortlist=[{"adres": "Proefstraat 1", "factor": 12.5}])["v1"]
    if not (r["te_koop"] and r["shortlist"] == 12.5 and r["labelsprong"]):
        afw.append(f"te koop, shortlist of labelsprong niet gezet: {r}")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef potentie: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    args = ap.parse_args()
    if args.proef:
        return proef()
    try:
        with open(VOORRAAD, encoding="utf-8") as f:
            voorraad = json.load(f)
    except Exception as e:
        print(f"Voorraad niet te lezen: {e}", file=sys.stderr)
        return 1
    try:
        import aanbodprofiel
        te_koop = [w["adres"] for w in aanbodprofiel.lees_aanbod()]
    except Exception:
        te_koop = []
    try:
        with open(SHORTLIST, encoding="utf-8") as f:
            shortlist = json.load(f).get("panden") or []
    except Exception:
        shortlist = []
    rijen = bepaal(voorraad, te_koop, shortlist)
    # COMPACT, want dit bestand gaat elke dag mee in de commit en de kaart
    # laadt het in de browser: korte sleutels, lege velden weg. De legenda
    # van de sleutels staat erin.
    kort = {"a": "adres", "p": "punt", "b": "buurt", "m": "m2", "j": "bouwjaar",
            "l": "label", "k": "kamers", "r": "kamers_reden", "s": "splitsen",
            "e": "labelsprong", "t": "te_koop", "f": "shortlist"}
    terug = {v: k for k, v in kort.items()}
    compact = {vbo: {terug[k]: v for k, v in r.items() if v not in (None, "", False)}
               for vbo, r in rijen.items()}
    with open(UIT_JSON, "w", encoding="utf-8") as f:
        json.dump({"datum": dt.date.today().isoformat(), "sleutels": kort,
                   "woningen": compact}, f, ensure_ascii=False,
                  separators=(",", ":"))
    regels = samenvatting(rijen)
    with open(UIT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(regels) + "\n")
    print("\n".join(regels))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
