#!/usr/bin/env python3
"""
Geplakte Funda-lijst met verkochte woningen verwerken.

Drie dingen tegelijk, uit dezelfde lijst:

1. De verkopen worden waarnemingen. Let op: Funda toont bij een verkocht pand
   de laatste vraagprijs en niet de koopsom; die staat alleen bij het Kadaster.
   Het is dus de vraagprijs waarop het pand van de markt ging, en dat is iets
   anders dan wat er is betaald.
2. Panden die bij ons nog te koop staan maar op Funda verkocht zijn, worden
   gemeld. Vendr stuurt geen bericht als een project verkocht is, dus die
   blijven anders eeuwig in de lijst staan.
3. Elk verkocht adres wordt tegen het bekendmakingenarchief gelegd: is er na
   het plaatsen van de advertentie een vergunning aangevraagd of verleend op
   dat adres? Dat is het spoor van een koper die is gaan verbouwen, splitsen of
   verkameren.

Let op bij punt 3: Funda noemt alleen hoe lang een advertentie er staat, niet
wanneer er is verkocht. De datum die we afleiden is dus het begin van de
advertentie, en een bekendmaking daarna is een aanwijzing en geen bewijs.

Gebruik:
  python funda_verkocht_plak.py --uit digests/2026-09-27-verkocht.md
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

PLAK_PAD = "funda_verkocht_plak.txt"
UIT_PAD = "verkopen.txt"
DETAIL_PAD = "verkocht_details.json"
ARCHIEF_PAD = "bekendmakingen_archief.json"

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass

# Funda kent meer dan "Verkocht": een pand kan onder bod staan of verkocht zijn
# onder voorbehoud. Dat zijn verschillende dingen, en "onder bod" is helemaal
# geen verkoop. We leggen ze apart vast in plaats van ze op een hoop te gooien.
STATUS = {
    "verkocht": "verkocht",
    "verkocht onder voorbehoud": "verkocht onder voorbehoud",
    "onder bod": "onder bod",
    "onder optie": "onder bod",
}
# Nieuwbouw is geen bestaande voorraad: bouwnummers, v.o.n.-prijzen en een
# project in plaats van een adres. Die horen niet in onze reeks.
NIEUWBOUW = re.compile(r"nieuwbouw|bouwnr\.|^project\[", re.I)
PRIJS = re.compile(r"^€\s*([\d.]+)\s*(k\.k\.|v\.o\.n\.)", re.I)
ADRES = re.compile(r"^\[([^\]]+)\]\((https://www\.funda\.nl/detail/koop/[^)]+)\)")
POSTCODE = re.compile(r"^\[(\d{4}\s?[A-Z]{2})\s+(.+?)\]\(")
OPP = re.compile(r"^\*\s*(\d{1,4})\s*m²")
LABEL = re.compile(r"^\*\s*(A\+{0,4}|[B-G])\s*$")
SINDS = re.compile(r"^Sinds\s+(\d+)\s+(week|weken|maand|maanden)", re.I)


def _sleutel(adres):
    return re.sub(r"[^a-z0-9]", "", adres.lower())


def parse(tekst):
    """De verkochte woningen uit de geplakte tekst."""
    regels = [r.strip() for r in tekst.split("\n")]
    uit, huidig, sinds_dagen = [], None, None
    for regel in regels:
        s = SINDS.match(regel)
        if s:
            aantal, eenheid = int(s.group(1)), s.group(2).lower()
            sinds_dagen = aantal * (7 if eenheid.startswith("week") else 30)
            continue
        # De statusregel kan er "Verkocht onder voorbehoudNieuwbouwwoning" of
        # "Onder optieNieuwbouwwoning" uitzien: status en soort aan elkaar
        kaal = regel.lower().replace("nieuwbouwwoning", "").strip()
        if kaal in STATUS:
            if huidig:
                uit.append(huidig)
            huidig = {"prijs": None, "adres": None, "plaats": None,
                      "postcode": None, "opp": [], "label": None,
                      "sinds_dagen": sinds_dagen, "url": None,
                      "status": STATUS[kaal],
                      "nieuwbouw": bool(NIEUWBOUW.search(regel))}
            continue
        if not huidig:
            continue
        p = PRIJS.match(regel)
        if p and huidig["prijs"] is None:
            huidig["prijs"] = int(p.group(1).replace(".", ""))
            if p.group(2).lower().startswith("v"):
                huidig["nieuwbouw"] = True   # v.o.n. hoort bij nieuwbouw
            continue
        if NIEUWBOUW.search(regel):
            huidig["nieuwbouw"] = True
            continue
        a = ADRES.match(regel)
        if a and not huidig["adres"]:
            huidig["adres"] = a.group(1).strip()
            huidig["url"] = a.group(2)
            continue
        pc = POSTCODE.match(regel)
        if pc and not huidig["postcode"]:
            huidig["postcode"] = pc.group(1).replace(" ", "")
            huidig["plaats"] = pc.group(2).strip()
            continue
        o = OPP.match(regel)
        if o:
            huidig["opp"].append(int(o.group(1)))
            continue
        lb = LABEL.match(regel)
        if lb and not huidig["label"]:
            huidig["label"] = lb.group(1)
    if huidig:
        uit.append(huidig)

    # Ontdubbelen: de geplakte pagina herhaalt zich vaak
    gezien, schoon = set(), []
    for w in uit:
        if not (w["adres"] and w["prijs"] and w["opp"] and w["plaats"]):
            continue
        if w.get("nieuwbouw"):
            continue
        k = (_sleutel(w["adres"]), w["prijs"])
        if k in gezien:
            continue
        gezien.add(k)
        # Bij een huis staan er twee oppervlaktes: wonen en perceel. De eerste
        # is de woonoppervlakte.
        w["woonopp"] = w["opp"][0]
        w["perceel"] = w["opp"][1] if len(w["opp"]) > 1 else None
        schoon.append(w)
    return schoon


def lees_regels(pad):
    if not os.path.exists(pad):
        return []
    with open(pad, encoding="utf-8") as f:
        return [r.strip() for r in f if r.strip()]


def nog_te_koop(bestaand):
    """Adressen die bij ons als te koop staan, met hun laatste status."""
    status_per_adres = {}
    for r in bestaand:
        velden = [v.strip() for v in r.split("|")]
        if len(velden) < 5:
            continue
        status_per_adres[_sleutel(velden[0])] = velden[3].lower()
    return {k for k, v in status_per_adres.items() if v.startswith("te koop")}


def vergunningen_na_plaatsing(verkocht, archief):
    """
    Bekendmakingen op een verkocht adres, na het begin van de advertentie.

    Een aanwijzing dat de koper iets met het pand doet. Geen bewijs: de
    advertentiedatum is een benadering van het verkoopmoment, en een
    bekendmaking kan ook van de vorige eigenaar zijn.
    """
    if not archief:
        return []
    uit = []
    vandaag = dt.date.today()
    for w in verkocht:
        m = re.match(r"^(.+?)\s+(\d+)", w["adres"])
        if not m:
            continue
        straat, nr = m.group(1), m.group(2)
        sl = re.sub(r"[^a-z0-9]", "", straat.lower()) + nr
        items = archief.get(sl, [])
        if not items:
            continue
        grens = None
        if w.get("sinds_dagen"):
            grens = (vandaag - dt.timedelta(days=w["sinds_dagen"])).isoformat()
        na = [t for t in items
              if not grens or (t.get("datum") or "") >= grens]
        if na:
            uit.append({"adres": w["adres"], "prijs": w["prijs"],
                        "vanaf": grens, "bekendmakingen": na[:3]})
    return uit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    wis("verkocht")

    if not os.path.exists(PLAK_PAD):
        print(f"{PLAK_PAD} staat er niet; niets te doen", file=sys.stderr)
        return
    with open(PLAK_PAD, encoding="utf-8") as f:
        verkocht = parse(f.read())
    if not verkocht:
        leg_vast("verkocht", f"Geen verkochte woningen uit {PLAK_PAD} te halen. "
                             f"Is de opmaak van de pagina veranderd?")
        print("Niets gevonden", file=sys.stderr)
        return

    bestaand = lees_regels(UIT_PAD)
    te_koop = nog_te_koop(bestaand)
    kern = set()
    for r in bestaand:
        velden = [v.strip() for v in r.split("|")]
        if len(velden) >= 4:
            kern.add((_sleutel(velden[0]), velden[2], velden[3].lower()))

    datum = dt.date.today().isoformat()
    nieuw, alsnog_verkocht = [], []
    for w in verkocht:
        sl = _sleutel(w["adres"])
        if (sl, str(w["prijs"]), w.get("status") or "verkocht") in kern:
            continue
        nieuw.append(f"{w['adres']} | {w['plaats']} | {w['prijs']} | "
                     f"{w.get('status') or 'verkocht'} | "
                     f"{datum} | funda-verkocht-plak | {w['woonopp']} | "
                     f"{w['postcode'] or ''}")
        if sl in te_koop:
            alsnog_verkocht.append(w)

    if nieuw:
        with open(UIT_PAD, "a", encoding="utf-8") as f:
            f.write("\n".join(nieuw) + "\n")

    # De extra gegevens die niet in verkopen.txt passen
    try:
        with open(DETAIL_PAD, encoding="utf-8") as f:
            details = json.load(f)
    except Exception:
        details = {}
    for w in verkocht:
        details[_sleutel(w["adres"])] = {
            "adres": w["adres"], "prijs": w["prijs"], "woonopp": w["woonopp"],
            "perceel": w["perceel"], "label": w["label"],
            "sinds_dagen": w["sinds_dagen"], "gezien": datum, "url": w["url"]}
    with open(DETAIL_PAD, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=1, sort_keys=True)

    try:
        with open(ARCHIEF_PAD, encoding="utf-8") as f:
            archief = json.load(f)
    except Exception:
        archief = {}
    sporen = vergunningen_na_plaatsing(verkocht, archief)

    print(f"Verkocht: {len(verkocht)} woningen gelezen, {len(nieuw)} nieuw, "
          f"{len(alsnog_verkocht)} stonden bij ons nog te koop, "
          f"{len(sporen)} met een bekendmaking na plaatsing", file=sys.stderr)
    for w in alsnog_verkocht:
        print(f"  stond nog te koop: {w['adres']} (€{w['prijs']:,})".replace(",", "."),
              file=sys.stderr)

    if args.uit and (alsnog_verkocht or sporen):
        r = ["# Verkochte woningen", ""]
        if alsnog_verkocht:
            r.append("_Deze panden stonden bij ons nog in het aanbod maar zijn op "
                     "Funda verkocht. Vendr meldt een verkoop niet._")
            for w in alsnog_verkocht:
                r.append(f"- **{w['adres']}**, laatste vraagprijs "
                         + f"€{w['prijs']:,}".replace(",", ".")
                         + f", {w['woonopp']} m2")
            r.append("")
        if sporen:
            r.append("_Bekendmakingen op een verkocht adres, na het begin van de "
                     "advertentie. Een aanwijzing dat de koper iets met het pand "
                     "doet, geen bewijs: de datum is een benadering._")
            for s in sporen:
                regels = "; ".join(f"{(t.get('datum') or '')[:10]} "
                                   f"{(t.get('titel') or '')[:90]}"
                                   for t in s["bekendmakingen"])
                r.append(f"- **{s['adres']}** (verkocht, laatste vraagprijs "
                         + f"€{s['prijs']:,}".replace(",", ".")
                         + f"): {regels}")
        os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write("\n".join(r) + "\n")


if __name__ == "__main__":
    main()
