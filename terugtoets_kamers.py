#!/usr/bin/env python3
"""
De kamertoets tegen de werkelijkheid: wat zei de gemeente, en wat zeiden wij?

WAAROM DIT BESTAAT. Op 15 oktober werd de vergunning voor Professor
Molkenboerstraat 20A herroepen, en onze toets gaf voor dat adres "gekeken en
niets gevonden". Na de reparatie (PR 124) blokkeert de toets 479 adressen in
de ring die eerder vrij waren. Of dat terecht is, zegt geen proef die op onze
eigen aanname rust; dat zeggen alleen echte besluiten. Mark: "we gaan gewoon
onze module testen aan de werkelijke situatie."

HOE. Per zaak met een bekende uitkomst draait de toets zoals hij er op de
besluitdatum uitzag: alleen buurvergunningen en bekendmakingen van VOOR die
datum tellen mee. Anders toetsen we met kennis achteraf, en dan is elke
overeenkomst gratis.

WAT HIER NIET IN ZIT, EN DUS ALS VOORBEHOUD BIJ ELK GETAL HOORT.
- De BAG is die van vandaag. Een tussenpand dat toen anders was ingedeeld,
  zien wij zoals het nu is.
- Kamerverhuur zonder vergunning of van voor de lijsten (2013, archief vanaf
  de backfill) zien wij niet. De gemeente ziet die via de BRP wel, zoals bij
  22A.
- De WOZ van toen kennen we niet, dus de WOZ-ondergrens doet niet mee. Deze
  terugtoets gaat over de buren: insluiting en aaneenschakeling.
- Vrijwel geen besluit heet "geweigerd". Een kansloze aanvraag eindigt
  meestal als ingetrokken of buiten behandeling. Die tellen hier apart en
  niet als weigering, want de reden staat niet in de titel.

  python3 terugtoets_kamers.py             # draaien, schrijft terugtoets_kamers.md
  python3 terugtoets_kamers.py --proef     # de logica nameten op 20A
"""
import argparse
import json
import re
import sys

import marktprijzen_bag as mb

UIT_JSON = "terugtoets_kamers.json"
UIT_MD = "terugtoets_kamers.md"

# De peildatum van de huidige regels: het voorbereidingsbesluit van het
# facetbestemmingsplan Kamerverhuur. Zaken daarvoor zijn onder een ander
# regime beslist en worden apart geteld.
NIEUW_REGIME = "2021-10-07"



def uitkomst_van(titel):
    """verleend, negatief, teruggetrokken, aanvraag, ontwerp of None."""
    return mb.fase_van(titel)


def _is_kamer(soorten):
    s = " ".join(x.lower() for x in (soorten or []))
    return any(k in s for k in ("kamerverhuur", "omzetting", "onttrekking")) \
        and not any(g in s for g in mb.GEEN_KAMERSOORT)


def zaken(archief, vergunningen):
    """
    Alle zaken met een uitkomst, een per adres en datum.

    Uit het archief: de titels met een kamersignaal en een uitkomst. Uit de
    vergunningenlijst: elke verleende kamervergunning (onttrekking, omzetting,
    omgevingsvergunning), want die lijst bevat alleen verleende.
    """
    uit, gezien = [], set()
    for sleutel, items in (archief or {}).items():
        for t in items:
            if not _is_kamer(t.get("soorten")):
                continue
            u = uitkomst_van(t.get("titel"))
            if u in (None, "aanvraag", "ontwerp"):
                continue
            adres = mb_adres(t.get("titel")) or sleutel
            datum = (t.get("datum") or "")[:10]
            if (sleutel, datum) in gezien:
                continue
            gezien.add((sleutel, datum))
            uit.append({"adres": adres, "sleutel": sleutel, "datum": datum,
                        "uitkomst": u, "bron": "bekendmaking",
                        "titel": t.get("titel"), "url": t.get("url", "")})
    for sleutel, items in (vergunningen or {}).items():
        for v in items:
            soort = (v.get("soort") or "").lower()
            if any(g in soort for g in mb.GEEN_KAMERSOORT):
                continue
            datum = (v.get("datum") or "")[:10]
            if not datum or (sleutel, datum) in gezien:
                continue
            # Een vergunning die kamerverhuur beeindigt is geen verleende
            # kamerverhuur; die zaak hoort hier niet.
            if mb.beeindigt_kamerverhuur(v):
                continue
            gezien.add((sleutel, datum))
            uit.append({"adres": v.get("adres") or sleutel, "sleutel": sleutel,
                        "datum": datum, "uitkomst": "verleend",
                        "bron": "vergunningenlijst", "titel": soort, "url": ""})
    # EEN BESLUIT DAT LATER IS HERROEPEN, IS GEEN VERLEENDE ZAAK. 20A werd op
    # 23 juni verleend en op 8 oktober herroepen; als twee zaken geteld staat
    # er een "verleend en wij geblokkeerd" die in werkelijkheid een gelijk is.
    # De eerdere uitkomst blijft zichtbaar, maar telt niet mee.
    negatief = {}
    for z in uit:
        if z["uitkomst"] == "negatief":
            negatief.setdefault(z["sleutel"], []).append(z["datum"])
    for z in uit:
        if z["uitkomst"] == "verleend" and any(
                d > z["datum"] for d in negatief.get(z["sleutel"], [])):
            z["uitkomst"] = "verleend, later herroepen"
    return sorted(uit, key=lambda z: (z["datum"], z["adres"]))


def mb_adres(titel):
    """Het adres uit een bekendmakingstitel, als straat en nummer met letter."""
    m = re.search(r"\baan (?:de )?([A-Z][^,\d]*?)\s+(\d+\s*[A-Za-z]?)"
                  r"(?:[-/]\S+)?,?\s+\d{4}\s?[A-Z]{2}", titel or "")
    return f"{m.group(1).strip()} {m.group(2).replace(' ', '')}" if m else None


def tot_datum(archief, vergunningen, datum):
    """Archief en vergunningenlijst zoals ze op die datum waren."""
    a = {k: [t for t in v if (t.get("datum") or "")[:10] < datum]
         for k, v in (archief or {}).items()}
    g = {k: [x for x in v if (x.get("datum") or "")[:10] < datum]
         for k, v in (vergunningen or {}).items()}
    return ({k: v for k, v in a.items() if v}, {k: v for k, v in g.items() if v})


def voorspel(zaak, archief, vergunningen):
    """Onze toets op de besluitdatum: geblokkeerd, vrij of onbekend, met reden."""
    a, g = tot_datum(archief, vergunningen, zaak["datum"])
    ing, reden = mb.kamerroute_geblokkeerd(zaak["adres"], a, g)
    if reden in ("reeks", "weerszijden", "insluiting"):
        return "geblokkeerd", reden, ing
    if reden == "gekeken en niets gevonden":
        return "vrij", reden, ing
    return "onbekend", reden, ing


def terugtoets(archief=None, vergunningen=None):
    archief = mb.lees_archief() if archief is None else archief
    vergunningen = (mb.lees_kamervergunningen() if vergunningen is None
                    else vergunningen)
    rijen = []
    for z in zaken(archief, vergunningen):
        v, reden, ing = voorspel(z, archief, vergunningen)
        rijen.append(dict(z, voorspelling=v, reden=reden,
                          regime="nieuw" if z["datum"] >= NIEUW_REGIME else "oud",
                          tussen=[x.get("nummer") for x in (ing or [])],
                          kamerbuur=[x.get("kamerbuur") for x in (ing or [])]))
    return rijen


def tabel(rijen, regime):
    """Telling uitkomst tegen voorspelling, voor een regime."""
    t = {}
    for r in rijen:
        if r["regime"] != regime:
            continue
        sleutel = (r["uitkomst"], r["voorspelling"])
        t[sleutel] = t.get(sleutel, 0) + 1
    return t


def oneens(rijen):
    """De zaken waarin wij en de gemeente het oneens zijn, onder de huidige regels."""
    return [r for r in rijen if r["regime"] == "nieuw" and (
        (r["uitkomst"] == "verleend" and r["voorspelling"] == "geblokkeerd")
        or (r["uitkomst"] == "negatief" and r["voorspelling"] == "vrij"))]


def schrijf(rijen):
    with open(UIT_JSON, "w", encoding="utf-8") as f:
        json.dump(rijen, f, ensure_ascii=False, indent=1)
    regels = ["# Terugtoets kamerverhuur", "",
              "Onze toets op de besluitdatum, tegen de uitkomst. Voorbehoud: "
              "de BAG is die van vandaag, de WOZ doet niet mee, en kamerverhuur "
              "zonder vergunning zien wij niet.", ""]
    for regime, kop in (("nieuw", f"Huidige regels (vanaf {NIEUW_REGIME})"),
                        ("oud", f"Oude regels (voor {NIEUW_REGIME}), "
                                f"alleen ter vergelijking")):
        t = tabel(rijen, regime)
        regels += [f"## {kop}", "",
                   "| uitkomst | geblokkeerd | vrij | onbekend |",
                   "|---|---|---|---|"]
        for u in ("verleend", "negatief", "teruggetrokken",
                  "verleend, later herroepen"):
            regels.append(f"| {u} | {t.get((u, 'geblokkeerd'), 0)} | "
                          f"{t.get((u, 'vrij'), 0)} | {t.get((u, 'onbekend'), 0)} |")
        regels.append("")
    regels += ["## Oneens, onder de huidige regels", ""]
    for r in oneens(rijen):
        regels.append(f"- {r['datum']} {r['adres']}: gemeente {r['uitkomst']}, "
                      f"wij {r['voorspelling']} ({r['reden']}"
                      + (f", tussen {r['tussen']} en {r['kamerbuur']}"
                         if r["tussen"] else "") + ")"
                      + (f" [bron]({r['url']})" if r["url"] else ""))
    regels += ["", "## Teruggetrokken, onder de huidige regels", "",
               "Geen weigering, maar ook geen vergunning. Wat wij ervan dachten:", ""]
    for r in rijen:
        if r["regime"] == "nieuw" and r["uitkomst"] == "teruggetrokken":
            regels.append(f"- {r['datum']} {r['adres']}: wij {r['voorspelling']} "
                          f"({r['reden']})")
    with open(UIT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(regels) + "\n")
    return regels


def proef():
    """
    De logica op de straat van 20A, zonder bestanden. Drie dingen: de zaak
    wordt herkend als negatief, de toets ziet de herroeping zelf niet (die is
    van na de besluitdatum en mag niet meetellen), en het oordeel is
    geblokkeerd op insluiting, zoals de gemeente besliste.
    """
    afw = []
    straat = "Proefstraat"
    def _rec(nr, pand):
        return [{"adres": f"{straat} {nr}", "status": "Verblijfsobject in gebruik",
                 "oppervlakte": 100, "pand": pand}]
    mb._VOORRAAD[mb._straatsleutel_voorraad(straat)] = {
        18: _rec(18, "p18"), 20: _rec(20, "p20"), 22: _rec(22, "p22"),
        24: _rec(24, "p24")}
    verg = {mb.archief_sleutel(straat, "18"): [
                {"adres": f"{straat} 18A", "soort": "onttrekking",
                 "datum": "2018-07-03"}],
            mb.archief_sleutel(straat, "24"): [
                {"adres": f"{straat} 24", "soort": "omgevingsvergunning",
                 "datum": "2015-02-12"}],
            # Een vergunning van NA de besluitdatum mag niet meetellen.
            mb.archief_sleutel(straat, "16"): [
                {"adres": f"{straat} 16", "soort": "onttrekking",
                 "datum": "2027-01-01"}]}
    arch = {mb.archief_sleutel(straat, "20"): [
        {"datum": "2026-10-14", "soorten": ["kamerverhuur"],
         "titel": f"Beslissing op bezwaar voor bezwaar tegen Z1 Vergunning "
                  f"kamerverhuur herroepen, aan {straat} 20A, 6524RP Nijmegen"}]}
    rijen = terugtoets(arch, verg)
    z = [r for r in rijen if r["bron"] == "bekendmaking"]
    # En een eerdere verlening op hetzelfde adres telt niet als verleend.
    arch2 = {k: v + [{"datum": "2026-06-25", "soorten": ["kamerverhuur"],
                      "titel": f"Besluit voor afwijken omgevingsplan kamerverhuur, "
                               f"aan {straat} 20A, 6524RP Nijmegen"}]
             for k, v in arch.items()}
    eerder = [r for r in terugtoets(arch2, verg) if r["datum"] == "2026-06-25"]
    if not eerder or eerder[0]["uitkomst"] != "verleend, later herroepen":
        afw.append(f"een later herroepen verlening telt als verleend: {eerder}")
    if len(z) != 1 or z[0]["uitkomst"] != "negatief":
        afw.append(f"de herroeping wordt niet als negatief herkend: {z}")
    elif z[0]["voorspelling"] != "geblokkeerd" or z[0]["reden"] != "insluiting":
        afw.append(f"20A wordt niet geblokkeerd op insluiting: "
                   f"{z[0]['voorspelling']} {z[0]['reden']}")
    a, g = tot_datum(arch, verg, "2026-10-14")
    if mb.archief_sleutel(straat, "16") in g:
        afw.append("een vergunning van na de besluitdatum telt mee")
    if uitkomst_van("Intrekking verzoek voor kamerverhuur, aan X 1") != "teruggetrokken":
        afw.append("een intrekking wordt niet als teruggetrokken herkend")
    # De titelvorm van voor 2024, uit gmb-2023-3231: de fase staat achteraan.
    if uitkomst_van("de Kluijskamp 1159 Nijmegen: aanvraag kamerverhuurvergunning "
                    "- onttrekkingsvergunning - Aanvraag ontvangen") != "aanvraag":
        afw.append("een oude aanvraag wordt niet als aanvraag herkend")
    for a_ in afw:
        print("AFWIJKING: " + a_, file=sys.stderr)
    print(f"Proef terugtoets_kamers: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    args = ap.parse_args()
    if args.proef:
        return proef()
    rijen = terugtoets()
    for regel in schrijf(rijen):
        print(regel)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
