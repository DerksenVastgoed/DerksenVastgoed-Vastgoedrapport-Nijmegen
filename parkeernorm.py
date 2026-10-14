#!/usr/bin/env python3
"""
De parkeernorm die bij een zone en een woningtype hoort.

WAAROM DIT BESTAAT. splitsingstoets.py rekende met PARKEERNORM = 0.70, een
enkele constante, met in de uitleg erbij "de norm is 0,70 per woning in de
binnenstad". Die werd op elk pand toegepast. Van de 20.321 adressen in onze
voorraad liggen er 14.171 buiten de Binnenstad, en daar is de norm hoger: in
het Buitengebied tot 2,00 voor een vrijstaande koopwoning. De uitkomst was
daar dus te laag, en niets liet dat zien.

Sinds 14 oktober kent elk pand zijn zone, uit MOB_PARKEERNORMERING. Daarmee
kan de norm erbij, uit de tabel in parkeernormen.txt.

DRIE DINGEN DIE DEZE MODULE WEIGERT TE DOEN:

  1. Rekenen met een onzekere waarde. Twee cellen in het brondocument zijn
     beschadigd; die staan met een vraagteken in het bestand en leveren hier
     een norm met onzeker=True. De toets zegt dan dat de norm in de
     beleidsregels moet worden nagekeken.
  2. Een woningtype kiezen. Of een pand een koopappartement duur of een
     huurappartement betaalbaar wordt, bepaalt de norm sterk: in het
     Centrumgebied 1,20 tegen 0,50. Dat weet de BAG niet. Zonder opgegeven
     type geeft deze module de BANDBREEDTE voor die zone, en dan rekent de
     toets niet met een getal maar noemt hij de uiterste waarden.
  3. Zeggen of de vrijstelling geldt. Die hangt aan het gereguleerde gebied,
     en dat is uit de gepubliceerde lagen niet te bepalen; zie parkeerzone.py.
"""

import argparse
import os
import sys

PAD = "parkeernormen.txt"
# De gebiedsnamen van de zonekaart, in de volgorde van de kolommen.
ZONES = ["Binnenstad", "Centrumgebied", "1e Schil", "2e Schil",
         "Rest bebouwde kom", "Buitengebied"]


def _getal(tekst):
    """Een cel uit de tabel: (waarde, onzeker). Een streepje is geen norm."""
    kaal = (tekst or "").strip()
    if not kaal or kaal == "-":
        return None, False
    onzeker = kaal.endswith("?")
    kaal = kaal.rstrip("?").strip().replace(",", ".")
    try:
        return float(kaal), onzeker
    except ValueError:
        return None, False


def lees(pad=None):
    """
    De tabel als {woningtype: {zone: (norm, onzeker)}}.

    De kop staat niet in het bestand als regel maar als commentaar, want de
    kolomvolgorde hoort bij de code en niet bij de gegevens: anders kan een
    regel met vijf kolommen stil als zes worden gelezen.
    """
    pad = pad or PAD
    uit = {}
    try:
        with open(pad, encoding="utf-8") as f:
            regels = f.read().splitlines()
    except Exception:
        return uit
    for regel in regels:
        kaal = regel.strip()
        if not kaal or kaal.startswith("#"):
            continue
        velden = [v.strip() for v in kaal.split("|")]
        if len(velden) != len(ZONES) + 1:
            # NIET HALF INLEZEN. Een regel met te weinig kolommen zou anders
            # de laatste zones leeg laten en dan is er geen norm waar er wel
            # een hoort te zijn.
            continue
        soort = velden[0].lower()
        uit[soort] = {}
        for zone, cel in zip(ZONES, velden[1:]):
            waarde, onzeker = _getal(cel)
            if waarde is not None:
                uit[soort][zone] = (waarde, onzeker)
    return uit


def norm(zone, woningtype, tabel=None):
    """
    De norm voor deze zone en dit type.

    Geeft een woordenboek met norm, onzeker en reden. Is de norm er niet, dan
    staat er None in norm en zegt reden waarom, want "geen eis" en "niet
    bekend" zijn twee verschillende antwoorden.
    """
    tabel = tabel if tabel is not None else lees()
    if not tabel:
        return {"norm": None, "onzeker": False,
                "reden": f"de normtabel is niet gelezen ({PAD})"}
    soort = (woningtype or "").lower().strip()
    if soort not in tabel:
        return {"norm": None, "onzeker": False,
                "reden": f"woningtype {woningtype!r} staat niet in de tabel"}
    if zone not in tabel[soort]:
        return {"norm": None, "onzeker": False,
                "reden": f"voor zone {zone!r} staat bij {soort!r} geen norm"}
    waarde, onzeker = tabel[soort][zone]
    return {"norm": waarde, "onzeker": onzeker,
            "reden": ("de cel in het brondocument is beschadigd; nakijken in "
                      "de Beleidsregels parkeren 2025" if onzeker else "")}


def bandbreedte(zone, tabel=None):
    """
    De laagste en hoogste norm in deze zone, over alle woningtypen.

    Dit is het antwoord als het woningtype nog niet bekend is. Onzekere cellen
    doen niet mee, want een bandbreedte die op een beschadigde cel rust is
    geen bandbreedte.
    """
    tabel = tabel if tabel is not None else lees()
    waarden = []
    for soort, per_zone in tabel.items():
        if soort.startswith("bezoek"):
            continue
        if zone in per_zone:
            waarde, onzeker = per_zone[zone]
            if not onzeker:
                waarden.append((waarde, soort))
    if not waarden:
        return {"laag": None, "hoog": None, "aantal": 0,
                "reden": f"geen bruikbare normen voor zone {zone!r}"}
    waarden.sort()
    return {"laag": waarden[0][0], "laag_type": waarden[0][1],
            "hoog": waarden[-1][0], "hoog_type": waarden[-1][1],
            "aantal": len(waarden), "reden": ""}


def proef():
    fouten = []
    tabel = lees()

    # DE TABEL IS VOLLEDIG GELEZEN. Zestien regels: veertien woningtypen en
    # twee bezoekregels.
    if len(tabel) != 16:
        fouten.append(f"de tabel heeft {len(tabel)} regels in plaats van 16")
    for soort in ("koop vrijstaand", "kamerverhuur per kamer",
                  "huur appartement betaalbaar"):
        if soort not in tabel:
            fouten.append(f"{soort!r} staat niet in de gelezen tabel")

    # DRIE WAARDEN DIE IK UIT HET DOCUMENT HEB AFGELEZEN, als ijkpunt. Gaat er
    # iets mis bij het inlezen, dan valt dat hier op en niet in de brief.
    for zone, soort, verwacht in (
            ("Binnenstad", "koop vrijstaand", 0.70),
            ("Buitengebied", "koop vrijstaand", 2.00),
            ("Centrumgebied", "huur appartement betaalbaar", 0.50),
            ("2e Schil", "koop rij", 1.30),
            ("Rest bebouwde kom", "kleine eenkamerwoning huur", 0.60)):
        uit = norm(zone, soort, tabel)
        if uit["norm"] != verwacht:
            fouten.append(f"{soort} in {zone} geeft {uit['norm']} in plaats "
                          f"van {verwacht}")
        if uit["onzeker"]:
            fouten.append(f"{soort} in {zone} heet onzeker en is dat niet")

    # DE TWEE ONZEKERE CELLEN HETEN ONZEKER. Dit is de hele reden dat het
    # vraagteken in het bestand staat.
    for zone, soort in (("1e Schil", "koop appartement betaalbaar"),
                        ("Binnenstad", "huur eengezins sociaal")):
        uit = norm(zone, soort, tabel)
        if not uit["onzeker"]:
            fouten.append(f"{soort} in {zone} komt uit een beschadigde cel en "
                          f"heet toch zeker")
        if uit["norm"] is None:
            fouten.append(f"{soort} in {zone} geeft geen waarde; de waarde "
                          f"mag blijven, zolang hij onzeker heet")
        if not uit["reden"]:
            fouten.append(f"{soort} in {zone} is onzeker zonder reden")

    # ZORGWONEN IN HET BUITENGEBIED IS NIET VAN TOEPASSING, en dat is iets
    # anders dan nul.
    uit = norm("Buitengebied", "zorgwonen per wooneenheid", tabel)
    if uit["norm"] is not None:
        fouten.append(f"een streepje in de tabel wordt als norm gelezen: "
                      f"{uit['norm']}")
    if "geen norm" not in uit["reden"]:
        fouten.append(f"een ontbrekende norm zegt niet dat hij ontbreekt: "
                      f"{uit['reden']!r}")

    # EEN ONBEKEND TYPE OF EEN ONBEKENDE ZONE GEEFT GEEN GETAL.
    if norm("Binnenstad", "landhuis met gracht", tabel)["norm"] is not None:
        fouten.append("een onbekend woningtype levert toch een norm op")
    if norm("Mars", "koop rij", tabel)["norm"] is not None:
        fouten.append("een onbekende zone levert toch een norm op")

    # DE BANDBREEDTE ALS HET TYPE NOG NIET BEKEND IS. In het Centrumgebied
    # loopt de norm van 0,20 (studentenwoning) tot 1,20 (koop duur), en dat
    # verschil is de reden dat de toets niet zelf een type kiest.
    band = bandbreedte("Centrumgebied", tabel)
    if (band["laag"], band["hoog"]) != (0.20, 1.20):
        fouten.append(f"de bandbreedte in het Centrumgebied is "
                      f"{band['laag']} tot {band['hoog']} in plaats van 0,2 "
                      f"tot 1,2")
    if band["aantal"] != 14:
        fouten.append(f"de bandbreedte rekent met {band['aantal']} typen in "
                      f"plaats van 14")
    # De bezoekregels mogen niet als woningtype meedoen.
    band_bi = bandbreedte("Binnenstad", tabel)
    if band_bi["laag"] == 0.05 or band_bi["laag"] == 0.20 and band_bi["aantal"] > 14:
        fouten.append("een bezoekregel doet mee als woningtype in de "
                      "bandbreedte")
    # In de 1e Schil valt een onzekere cel buiten de bandbreedte.
    band_1e = bandbreedte("1e Schil", tabel)
    if band_1e["aantal"] != 13:
        fouten.append(f"de onzekere cel in de 1e Schil doet mee in de "
                      f"bandbreedte: {band_1e['aantal']} typen in plaats "
                      f"van 13")

    # EEN REGEL MET TE WEINIG KOLOMMEN WORDT NIET HALF GELEZEN.
    import tempfile
    with tempfile.TemporaryDirectory() as m:
        p = os.path.join(m, "half.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("# kop\n"
                    "koop rij | 0,70 | 1,20\n"
                    "koop vrijstaand | 0,70 | 1,20 | 1,30 | 1,50 | 1,60 | 2,00\n")
        half = lees(p)
        if "koop rij" in half:
            fouten.append("een regel met drie kolommen wordt gelezen alsof er "
                          "zes zijn; dan staat er geen norm waar er wel een "
                          "hoort")
        if norm("Buitengebied", "koop vrijstaand", half)["norm"] != 2.00:
            fouten.append("een goede regel naast een halve wordt niet gelezen")
    # En een bestand dat er niet is geeft een reden, geen stilte.
    uit = norm("Binnenstad", "koop rij", lees("bestaat-echt-niet.txt"))
    if uit["norm"] is not None or "niet gelezen" not in uit["reden"]:
        fouten.append(f"een ontbrekende normtabel leest als een ontbrekende "
                      f"norm: {uit!r}")

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--zone", default="")
    ap.add_argument("--type", default="", dest="soort")
    args = ap.parse_args()
    if args.proef:
        return proef()
    if args.zone and args.soort:
        print(norm(args.zone, args.soort), file=sys.stderr)
        return 0
    if args.zone:
        print(bandbreedte(args.zone), file=sys.stderr)
        return 0
    tabel = lees()
    for zone in ZONES:
        b = bandbreedte(zone, tabel)
        print(f"{zone:<20} {b['laag']} ({b['laag_type']}) tot {b['hoog']} "
              f"({b['hoog_type']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
