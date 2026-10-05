#!/usr/bin/env python3
"""
Wat kost een vierkante meter in een klein pand, en wat in een groot?

Dit is de kern van elke splitsingscase: je koopt vierkante meters goedkoop in
een groot pand en verkoopt ze duur in kleine eenheden. In onze eigen cijfers
scheelt dat een factor twee, maar dat moet gemeten worden en niet geschat.

Hoe het werkt: elke waarneming wordt eerst gedeeld door de mediaan van zijn
eigen buurt. Daarmee valt het prijspeil van de buurt eruit en blijft alleen het
effect van de grootte over. Anders meet je ligging in plaats van omvang, want
kleine eenheden zitten vaker in het centrum.

De uitkomst is een verhoudingsgetal per grootteklasse, met de klasse van 80 tot
100 m2 als ijkpunt. Staat er 1,45 bij de klasse onder de 40 m2, dan is een
vierkante meter daar 45% duurder dan in een doorsnee pand van die buurt.

Dit bestand rekent elke run opnieuw uit wat er op dat moment bekend is. Komen
er waarnemingen bij, dan wordt de curve vanzelf beter; het aantal staat er
altijd bij, zodat te zien is hoeveel een getal waard is.
"""
import argparse
import json
import statistics as st
import sys

UIT_PAD = "grootte_premie.json"
AANBOD_PAD = "verkopen.txt"
BUURT_CACHE = "straat_buurt_cache.json"

# Grenzen in m2; de laatste klasse heeft geen bovengrens.
KLASSEN = ((0, 40), (40, 60), (60, 80), (80, 100), (100, 130), (130, 10000))
IJKKLASSE = (80, 100)
MINIMUM_PER_KLASSE = 8       # minder waarnemingen: geen getal tonen
MINIMUM_PER_BUURT = 5        # minder: die buurt doet niet mee als ijkpunt


def _straat(adres):
    """De straatnaam zonder huisnummer, als sleutel voor de buurtcache."""
    delen = []
    for woord in (adres or "").split():
        if any(c.isdigit() for c in woord):
            break
        delen.append(woord)
    return " ".join(delen).lower().strip()


def lees_buurten(pad=BUURT_CACHE):
    try:
        with open(pad, encoding="utf-8") as f:
            d = json.load(f) or {}
    except Exception:
        return {}
    uit = {}
    for sleutel, waarde in d.items():
        buurt = waarde.get("buurt") if isinstance(waarde, dict) else waarde
        if buurt:
            uit[sleutel.lower().strip()] = buurt
    return uit


def lees_waarnemingen(pad=AANBOD_PAD):
    """
    Alle panden met een prijs en een oppervlakte, koop en verkocht.

    Verkochte panden dragen de laatste vraagprijs en niet de transactieprijs;
    Funda toont die niet. Voor een verhouding tussen grootteklassen is dat
    bruikbaar, want die vertekening zit in alle klassen even hard.
    """
    uit = []
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 7:
                    continue
                status = v[3].lower()
                if not (status.startswith(("te koop", "nieuw"))
                        or status.startswith("verkocht")):
                    continue
                try:
                    prijs, opp = int(v[2]), int(v[6])
                except ValueError:
                    continue
                if not opp or prijs < 50000 or opp < 15:
                    continue
                uit.append({"adres": v[0], "prijs": prijs, "opp": opp,
                            "ppm2": prijs / opp, "straat": _straat(v[0])})
    except FileNotFoundError:
        return []
    return uit


def _klasse(opp):
    for onder, boven in KLASSEN:
        if onder <= opp < boven:
            return (onder, boven)
    return None


def meet(waarnemingen, buurten):
    """De premie per grootteklasse, gecorrigeerd voor het prijspeil per buurt."""
    per_buurt = {}
    for w in waarnemingen:
        buurt = buurten.get(w["straat"])
        if buurt:
            per_buurt.setdefault(buurt, []).append(w["ppm2"])
    mediaan_buurt = {b: st.median(v) for b, v in per_buurt.items()
                     if len(v) >= MINIMUM_PER_BUURT}

    # Zonder buurt vallen panden terug op de mediaan van de hele ring. Dat is
    # minder precies maar beter dan ze weggooien, want het zijn er veel.
    alles = [w["ppm2"] for w in waarnemingen]
    ring = st.median(alles) if alles else 0
    if not ring:
        return None

    per_klasse = {}
    for w in waarnemingen:
        k = _klasse(w["opp"])
        if not k:
            continue
        ijk = mediaan_buurt.get(buurten.get(w["straat"]), ring)
        per_klasse.setdefault(k, []).append(w["ppm2"] / ijk)

    ijk_waarden = per_klasse.get(IJKKLASSE) or []
    basis = st.median(ijk_waarden) if len(ijk_waarden) >= MINIMUM_PER_KLASSE else None

    uit = {}
    for k, waarden in sorted(per_klasse.items()):
        naam = (f"{k[0]}-{k[1]} m2" if k[1] < 10000 else f"{k[0]} m2 en groter")
        rij = {"aantal": len(waarden)}
        if len(waarden) >= MINIMUM_PER_KLASSE:
            rij["verhouding"] = round(st.median(waarden), 3)
            if basis:
                rij["premie"] = round(st.median(waarden) / basis, 3)
        uit[naam] = rij
    return {"klassen": uit, "buurten_met_ijkpunt": len(mediaan_buurt),
            "waarnemingen": len(waarnemingen),
            "ijkklasse": f"{IJKKLASSE[0]}-{IJKKLASSE[1]} m2",
            "basis_gemeten": basis is not None}


def premie_voor(opp, gemeten):
    """De premie van een eenheid van dit oppervlak, of None als die ontbreekt."""
    k = _klasse(opp)
    if not k or not gemeten:
        return None
    naam = (f"{k[0]}-{k[1]} m2" if k[1] < 10000 else f"{k[0]} m2 en groter")
    return (gemeten.get("klassen", {}).get(naam) or {}).get("premie")


def waarde_na_splitsing(opp_totaal, aantal, ppm2_nu, gemeten):
    """
    Wat de eenheden samen waard zijn als je het pand opdeelt.

    Geen verbouwkosten, geen belasting, geen verkoopkosten: dit is alleen de
    waardesprong door de grootte. De rest hoort in de doorrekening, zodat
    zichtbaar blijft welk deel waar vandaan komt.
    """
    if not (opp_totaal and aantal and ppm2_nu and gemeten):
        return None
    opp_eenheid = opp_totaal / aantal
    premie_nieuw = premie_voor(opp_eenheid, gemeten)
    premie_nu = premie_voor(opp_totaal, gemeten)
    if not premie_nieuw or not premie_nu:
        return None
    ppm2_nieuw = ppm2_nu / premie_nu * premie_nieuw
    return {
        "opp_per_eenheid": round(opp_eenheid, 1),
        "ppm2_nu": round(ppm2_nu),
        "ppm2_na": round(ppm2_nieuw),
        "waarde_na": round(ppm2_nieuw * opp_totaal),
        "sprong": round(ppm2_nieuw * opp_totaal - ppm2_nu * opp_totaal),
        "grond": (f"gemeten premie {premie_nieuw} voor "
                  f"{round(opp_eenheid)} m2 tegen {premie_nu} voor "
                  f"{opp_totaal} m2"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=UIT_PAD)
    args = ap.parse_args()
    waarnemingen = lees_waarnemingen()
    if not waarnemingen:
        print("Geen waarnemingen met prijs en oppervlakte", file=sys.stderr)
        return 0
    gemeten = meet(waarnemingen, lees_buurten())
    if not gemeten:
        print("Niets te meten", file=sys.stderr)
        return 0
    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(gemeten, f, ensure_ascii=False, indent=1)
    print(f"Groottepremie uit {gemeten['waarnemingen']} waarnemingen, "
          f"{gemeten['buurten_met_ijkpunt']} buurten met een eigen ijkpunt:",
          file=sys.stderr)
    for naam, rij in gemeten["klassen"].items():
        deel = (f"premie {rij['premie']}" if rij.get("premie")
                else "te weinig waarnemingen")
        print(f"  {naam:18} {rij['aantal']:>4} panden, {deel}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
