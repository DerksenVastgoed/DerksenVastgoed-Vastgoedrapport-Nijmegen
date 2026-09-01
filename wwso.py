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


# ---------------------------------------------------------------------------
# WWS voor ZELFSTANDIGE woonruimte. Ander stelsel dan het WWSO hierboven.
# Waarden per 1 januari 2026.
# ---------------------------------------------------------------------------

# Rubriek WOZ: een punt per bedrag aan WOZ, plus een punt per bedrag WOZ per m2.
# Waardepeildatum 1 januari 2025.
WOZ_PER_PUNT = 16_954
WOZ_PER_M2_PER_PUNT = 268
WOZ_MINIMUM = 85_806
WOZ_CAP_AANDEEL = 0.33      # geldt alleen als de woning anders op 187+ uitkomt

# Energielabel, punten voor een meergezinswoning (appartement). Een
# eengezinswoning scoort hoger; bij splitsing ontstaan meestal appartementen.
LABEL_PUNTEN_ZELFSTANDIG = {
    "A++++": 48, "A+++": 44, "A++": 40, "A+": 36, "A": 32,
    "B": 28, "C": 22, "D": 14, "E": -5, "F": -9, "G": -15,
}

GRENS_SOCIAAL = 143         # tot en met dit aantal: sociale huur
GRENS_MIDDENHUUR = 186      # tot en met dit aantal: gereguleerde middenhuur
HUUR_BIJ_186 = 1228.07      # maximale kale huur bij 186 punten, 2026


def wws_punten(opp_m2, woz, label=None, monument=False, aanrecht_m=2.0,
               sanitair_punten=7, buiten_m2=0.0, heeft_buiten=True,
               overige_m2=0.0):
    """
    Puntentelling voor een zelfstandige woning. Geeft het totaal terug plus het
    segment, want dat bepaalt of er een wettelijk maximum geldt.

    Niet alle rubrieken zitten erin: verwarming, gemeenschappelijke ruimten en
    bijzondere voorzieningen ontbreken. De uitkomst is dus een ondergrens.
    """
    punten = opp_m2 * 1.0 + overige_m2 * 0.75

    # WOZ, met de wettelijke minimumwaarde
    woz = max(woz or WOZ_MINIMUM, WOZ_MINIMUM)
    woz_punten = woz / WOZ_PER_PUNT + (woz / opp_m2) / WOZ_PER_M2_PER_PUNT

    # Energielabel
    label_p = LABEL_PUNTEN_ZELFSTANDIG.get((label or "").upper(), 0)
    if monument and label_p < 0:
        label_p = 0
    punten += label_p

    # Keuken
    if aanrecht_m >= 2:
        punten += 7
    elif aanrecht_m >= 1:
        punten += 4

    punten += sanitair_punten

    # Buitenruimte
    if heeft_buiten:
        punten += min(15, 2 + 0.35 * buiten_m2)
    else:
        punten -= 5

    totaal_ongecapt = punten + woz_punten
    # De WOZ telt voor hoogstens een derde, maar alleen als de woning zonder
    # die begrenzing op 187 punten of meer zou uitkomen.
    if totaal_ongecapt >= 187:
        max_woz = WOZ_CAP_AANDEEL * totaal_ongecapt
        woz_punten = min(woz_punten, max_woz)

    totaal = round(punten + woz_punten)
    if totaal <= GRENS_SOCIAAL:
        segment = "sociale huur"
    elif totaal <= GRENS_MIDDENHUUR:
        segment = "gereguleerde middenhuur"
    else:
        segment = "vrije sector"
    return {"punten": totaal, "woz_punten": round(woz_punten, 1),
            "label_punten": label_p, "segment": segment,
            "gereguleerd": totaal <= GRENS_MIDDENHUUR}


# Maximale huurprijsgrenzen zelfstandige woningen per 1 januari 2026.
# Onder 40 punten geldt de grens bij 40 punten.
WWS_TABEL = {
    40: 250.26,
    41: 256.53,
    42: 262.75,
    43: 269.02,
    44: 275.27,
    45: 281.50,
    46: 287.78,
    47: 294.03,
    48: 300.29,
    49: 306.54,
    50: 312.80,
    51: 319.02,
    52: 325.30,
    53: 331.54,
    54: 337.80,
    55: 344.05,
    56: 350.35,
    57: 356.53,
    58: 362.79,
    59: 369.09,
    60: 375.32,
    61: 381.55,
    62: 387.83,
    63: 394.06,
    64: 400.32,
    65: 406.58,
    66: 412.85,
    67: 419.10,
    68: 425.33,
    69: 431.56,
    70: 437.81,
    71: 444.09,
    72: 450.36,
    73: 456.57,
    74: 462.86,
    75: 469.09,
    76: 475.36,
    77: 481.60,
    78: 487.89,
    79: 494.10,
    80: 500.38,
    81: 507.22,
    82: 514.08,
    83: 520.96,
    84: 527.81,
    85: 534.70,
    86: 541.56,
    87: 548.41,
    88: 555.29,
    89: 562.13,
    90: 569.03,
    91: 575.87,
    92: 582.71,
    93: 589.61,
    94: 596.45,
    95: 603.32,
    96: 610.19,
    97: 617.08,
    98: 623.94,
    99: 630.82,
    100: 637.67,
    101: 644.53,
    102: 651.36,
    103: 658.24,
    104: 665.12,
    105: 671.95,
    106: 678.85,
    107: 685.70,
    108: 692.56,
    109: 699.44,
    110: 706.32,
    111: 713.20,
    112: 720.05,
    113: 726.90,
    114: 733.79,
    115: 740.66,
    116: 747.51,
    117: 754.37,
    118: 761.21,
    119: 768.08,
    120: 774.94,
    121: 781.85,
    122: 788.71,
    123: 795.56,
    124: 802.44,
    125: 809.30,
    126: 816.14,
    127: 823.02,
    128: 829.94,
    129: 836.74,
    130: 843.62,
    131: 850.49,
    132: 857.33,
    133: 864.24,
    134: 871.06,
    135: 877.97,
    136: 884.79,
    137: 891.67,
    138: 898.56,
    139: 905.39,
    140: 912.26,
    141: 919.14,
    142: 925.98,
    143: 932.93,
    144: 939.73,
    145: 946.61,
    146: 953.45,
    147: 960.33,
    148: 967.18,
    149: 974.05,
    150: 980.91,
    151: 987.78,
    152: 994.63,
    153: 1001.50,
    154: 1008.35,
    155: 1015.22,
    156: 1022.07,
    157: 1029.00,
    158: 1035.81,
    159: 1042.73,
    160: 1049.57,
    161: 1056.42,
    162: 1063.32,
    163: 1070.14,
    164: 1077.00,
    165: 1083.88,
    166: 1090.76,
    167: 1097.61,
    168: 1104.46,
    169: 1111.39,
    170: 1118.23,
    171: 1125.08,
    172: 1131.94,
    173: 1138.85,
    174: 1145.69,
    175: 1152.55,
    176: 1159.40,
    177: 1166.27,
    178: 1173.15,
    179: 1180.01,
    180: 1186.84,
    181: 1193.76,
    182: 1200.61,
    183: 1207.46,
    184: 1214.31,
    185: 1221.21,
    186: 1228.07,
    187: 1234.92,
    188: 1241.81,
    189: 1248.65,
    190: 1255.53,
    191: 1262.40,
    192: 1269.25,
    193: 1276.12,
    194: 1283.00,
    195: 1289.86,
    196: 1296.70,
    197: 1303.57,
    198: 1310.46,
    199: 1317.28,
    200: 1324.18,
    201: 1331.03,
    202: 1337.89,
    203: 1344.75,
    204: 1351.63,
    205: 1358.50,
    206: 1365.34,
    207: 1372.24,
    208: 1379.09,
    209: 1385.95,
    210: 1392.84,
    211: 1399.69,
    212: 1406.56,
    213: 1413.43,
    214: 1420.28,
    215: 1427.15,
    216: 1433.99,
    217: 1440.86,
    218: 1447.71,
    219: 1454.60,
    220: 1461.49,
    221: 1468.31,
    222: 1475.19,
    223: 1482.05,
    224: 1488.95,
    225: 1495.77,
    226: 1502.67,
    227: 1509.53,
    228: 1516.40,
    229: 1523.28,
    230: 1530.12,
    231: 1536.98,
    232: 1543.85,
    233: 1550.71,
    234: 1557.56,
    235: 1564.46,
    236: 1571.31,
    237: 1578.17,
    238: 1585.01,
    239: 1591.91,
    240: 1598.76,
    241: 1605.64,
    242: 1612.52,
    243: 1619.36,
    244: 1626.24,
    245: 1633.10,
    246: 1639.96,
    247: 1646.78,
    248: 1653.70,
    249: 1660.54,
    250: 1667.40,
}


def wws_max_huur(punten):
    """Maximale kale huurprijs bij een puntenaantal, zelfstandige woning."""
    p = max(40, int(round(punten)))
    if p in WWS_TABEL:
        return WWS_TABEL[p]
    # Boven 250 punten kent de tabel geen grens meer; de woning is dan
    # sowieso vrije sector en er geldt geen wettelijk maximum.
    return None
