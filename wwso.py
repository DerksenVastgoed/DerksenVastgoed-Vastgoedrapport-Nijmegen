"""
WWSO-puntenteller volgens het Beleidsboek Waarderingsstelsel onzelfstandige
woonruimte van de Huurcommissie, versie januari 2026.

Alle puntenwaarden en de huurprijstabel komen uit dat beleidsboek.
"""

# Huurprijstabel per 1 januari 2026, punten 0 t/m 100 exact uit bijlage 2.
TABEL_0_100 = [
    0.00, 10.33, 20.56, 30.77, 40.89, 51.12, 61.29, 71.47, 81.62, 91.85,
    102.06, 112.23, 122.38, 132.57, 142.76, 152.92, 163.13, 173.33, 183.54, 193.63,
    203.87, 214.04, 224.29, 234.44, 244.59, 254.83, 264.95, 275.10, 285.37, 295.54,
    305.73, 315.89, 326.12, 336.29, 346.45, 356.69, 366.90, 377.02, 387.18, 397.42,
    407.58, 417.73, 427.95, 438.17, 448.30, 458.46, 468.73, 478.86, 489.09, 499.27,
    509.44, 519.58, 529.80, 539.99, 550.19, 560.36, 570.54, 580.70, 590.95, 601.06,
    611.28, 616.58, 621.84, 627.09, 632.41, 637.63, 642.97, 648.24, 653.44, 658.79,
    664.02, 669.35, 674.58, 679.91, 685.17, 690.38, 695.67, 700.94, 706.23, 711.49,
    716.80, 722.09, 727.34, 732.60, 737.95, 743.13, 748.46, 753.67, 759.00, 764.30,
    769.54, 774.81, 780.09, 785.36, 790.62, 795.90, 801.20, 806.50, 811.77, 817.05,
    822.35,
]
STAP_BOVEN_100 = 5.2747   # € per punt tussen 100 en 250

# Rubriek 4: punten per m2 naar energielabel (NTA 8800)
LABEL_PUNTEN = {
    "A++++": 1.00, "A+++": 0.95, "A++": 0.85, "A+": 0.75, "A": 0.65,
    "B": 0.50, "C": 0.35, "D": 0.20, "E": -0.05, "F": -0.10, "G": -0.15,
}
BOUWJAAR_PUNTEN = [(2002, 0.65), (2000, 0.50), (1992, 0.35), (1984, 0.20),
                   (1979, -0.05), (1977, -0.10), (0, -0.15)]

# Rubriek 5: keuken naar aanrechtlengte in meters
KEUKEN_PUNTEN = [(5.0, 13), (3.0, 10), (2.0, 7), (1.0, 4), (0.0, 0)]

# Rubriek 11: WOZ ten opzichte van het COROP-gemiddelde
WOZ_REGIO_2026 = {"Arnhem/Nijmegen": 3511}


def maximale_huur(punten):
    """Maximale kale huurprijs bij een puntenaantal, per 1 januari 2026."""
    p = max(0, int(round(punten)))
    if p <= 100:
        return TABEL_0_100[p]
    if p <= 250:
        return TABEL_0_100[100] + (p - 100) * STAP_BOVEN_100
    # Boven 250: elk punt telt als het verschil tussen 249 en 250 punten
    return TABEL_0_100[100] + 150 * STAP_BOVEN_100 + (p - 250) * STAP_BOVEN_100


def energiepunten_per_m2(label=None, bouwjaar=None, monument=False):
    """Rubriek 4. Monumenten krijgen geen minpunten bij label E, F of G."""
    if label and label.upper() in LABEL_PUNTEN:
        p = LABEL_PUNTEN[label.upper()]
    elif bouwjaar:
        p = next(v for j, v in BOUWJAAR_PUNTEN if bouwjaar >= j)
    else:
        p = -0.15
    if monument and p < 0:
        return 0.0
    return p


def keukenpunten(aanrecht_m, eenheden):
    """Rubriek 5. 13 punten alleen bij 8 of meer eenheden met gebruiksrecht."""
    for grens, punten in KEUKEN_PUNTEN:
        if aanrecht_m >= grens:
            if punten == 13 and eenheden < 8:
                punten = 10
            return punten
    return 0


def wozpunten(woz, gebruiksoppervlak, regio="Arnhem/Nijmegen"):
    """Rubriek 11. Vergelijking met het COROP-gemiddelde per m2."""
    if not woz or not gebruiksoppervlak:
        return 10
    eigen = woz / gebruiksoppervlak
    gem = WOZ_REGIO_2026.get(regio, 3511)
    afwijking = (eigen - gem) / gem
    if afwijking > 0.10:
        return 14
    if afwijking < -0.10:
        return 10
    return 12


def _kwart(x):
    """Afronden per rubriek op 0,25 punt, vanaf 1/8 naar boven."""
    return round(x * 4 + 1e-9) / 4 if (x * 4) % 1 != 0.5 else (x * 4 + 0.5) // 1 / 4


def punten_kamer(prive_m2, gemeen_vertrek_m2, eenheden, label=None, bouwjaar=None,
                 monument=False, woz=None, gebruiksoppervlak=None,
                 aanrecht_m=2.5, keuken_extra=3.0, sanitair_punten=9.0,
                 verwarmd_prive=True, gemeen_vertrekken=1, buiten_m2=0.0,
                 aftrek=0):
    """
    Puntentelling voor een onzelfstandige woonruimte. Gedeelde punten worden
    gelijk over de eenheden verdeeld, ongeacht de grootte van de kamer.
    """
    toegerekend_gemeen = gemeen_vertrek_m2 / eenheden

    r1 = _kwart(prive_m2 + toegerekend_gemeen)                       # vertrekken
    r3 = _kwart((2 if verwarmd_prive else 0)
                + 2 * gemeen_vertrekken / eenheden)                  # verwarming
    r4 = _kwart((prive_m2 + toegerekend_gemeen)
                * energiepunten_per_m2(label, bouwjaar, monument))   # energie
    r5 = _kwart((keukenpunten(aanrecht_m, eenheden)
                 + min(keuken_extra, keukenpunten(aanrecht_m, eenheden)))
                / eenheden)                                          # keuken
    r6 = _kwart(sanitair_punten / eenheden)                          # sanitair
    r8 = _kwart(min(15, 0.75 * buiten_m2 / eenheden))                # buitenruimte
    r11 = wozpunten(woz, gebruiksoppervlak)                          # WOZ
    r13 = -4 * aftrek                                                # aftrekpunten

    totaal = r1 + r3 + r4 + r5 + r6 + r8 + r11 + r13
    return {"rubriek1": r1, "rubriek3": r3, "rubriek4": r4, "rubriek5": r5,
            "rubriek6": r6, "rubriek8": r8, "rubriek11": r11, "rubriek13": r13,
            "totaal": round(totaal), "max_huur": maximale_huur(totaal)}


def wwso_bandbreedte(kamer_m2, label=None, bouwjaar=None, monument=False,
                     eenheden=6, woz_punten=12):
    """
    Schat de maximale kale huur voor een kamer als bandbreedte.

    Van een advertentie kennen we alleen de kameroppervlakte en meestal het
    label van het pand. Gemeenschappelijke ruimte, keukenlengte en sanitair
    weten we niet, terwijl die het puntenaantal wel beinvloeden. Daarom twee
    scenario's: karig en ruim. Ligt de vraaghuur boven de ruime variant, dan
    is er iets aan de hand, want dan haalt zelfs een gunstige telling het niet.
    """
    if not kamer_m2 or kamer_m2 < 4:
        return None

    scenarios = {
        # naam: gemeenschappelijk m2 per eenheid, keuken, sanitair, buiten
        "karig": (4.0, 4, 9, 0),
        "ruim": (12.0, 14, 20, 30),
    }
    uit = {}
    for naam, (gemeen_pp, keuken, sanitair, buiten) in scenarios.items():
        aftrek = 1 if kamer_m2 < 8 else 0
        r = punten_kamer(
            prive_m2=kamer_m2,
            gemeen_vertrek_m2=gemeen_pp * eenheden,
            eenheden=eenheden,
            label=label, bouwjaar=bouwjaar, monument=monument,
            aanrecht_m=2.5 if naam == "karig" else 4.0,
            keuken_extra=keuken, sanitair_punten=sanitair,
            gemeen_vertrekken=1 if naam == "karig" else 2,
            buiten_m2=buiten, aftrek=aftrek)
        # WOZ los meegeven, want die kennen we per pand meestal niet
        totaal = r["totaal"] - r["rubriek11"] + woz_punten
        uit[naam] = {"punten": round(totaal), "huur": maximale_huur(totaal)}

    opslag = 1.35 if monument else 1.0
    return {"laag": uit["karig"]["huur"] * opslag,
            "hoog": uit["ruim"]["huur"] * opslag,
            "punten_laag": uit["karig"]["punten"],
            "punten_hoog": uit["ruim"]["punten"]}
