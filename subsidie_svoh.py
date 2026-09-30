#!/usr/bin/env python3
"""
De SVOH: Subsidieregeling Verduurzaming en Onderhoud Huurwoningen.

Waarom dit in het model hoort: subsidie verlaagt de investering en dus de
richtprijs die je kunt betalen. Bij de Eerste Oude Heselaan scheelde het
duizenden euro's op een ingreep van zestienduizend.

De bedragen worden jaarlijks opnieuw vastgesteld, net als de huurprijstabel.
Daarom staat er een peildatum bij en meldt het gezondheidsrapport het zodra
die verouderd is.

Bedragen per 1 januari 2026, bron RVO. De tweede kolom geldt zodra er twee of
meer maatregelen tegelijk worden uitgevoerd; dat is het gewone geval, want de
regeling vraagt sowieso om minimaal twee maatregelen.
"""

PEILDATUM = "2026-01-01"
BRON = "RVO, Subsidieregeling Verduurzaming en Onderhoud Huurwoningen"

# maatregel: (bedrag per m2 bij een maatregel, bij twee of meer,
#             biobased bonus per m2, minimale Rd)
PER_M2 = {
    "spouwmuurisolatie": (5.25, 10.50, 1.50, 1.5),
    "gevelisolatie": (20.25, 40.50, 6.00, 3.5),
    # Vloer- en bodemisolatie gaan over de vloer van de begane grond, boven de
    # kruipruimte of op de grond. Een droge dekvloer op een verdieping valt er
    # niet onder, ook niet als er isolerend materiaal in zit.
    "vloerisolatie": (5.50, 11.00, 2.00, 3.5),
    "bodemisolatie": (3.00, 6.00, 1.00, 3.5),
    "dakisolatie": (16.25, 32.50, 5.00, 3.5),
    "zoldervloerisolatie": (4.00, 8.00, 1.50, 3.5),
    "hr_glas": (25.00, 50.00, 0.0, None),
    "triple_glas_met_kozijn": (111.00, 222.00, 0.0, None),
}

# CO2-gestuurde ventilatie gaat niet per m2 maar als deel van de kosten, en
# dat deel wordt gerekend over het bedrag INCLUSIEF btw. Bij de Eerste Oude
# Heselaan kwam er €998,25 binnen, en dat is 30% van €3.327,50 inclusief en
# niet van €2.750 exclusief. Logisch voor een verhuurder van woningen, die de
# btw niet kan verrekenen en dus werkelijk dat hele bedrag betaalt.
VENTILATIE_DEEL = (0.15, 0.30)
VENTILATIE_MAX = (600.0, 1200.0)
VENTILATIE_OVER_INCLUSIEF = True

# Maximum per woning. Zonder warmtepomp of zonneboiler ligt het lager.
MAX_PER_WONING = 10000.0
MAX_PER_WONING_MET_WARMTE = 15000.0


def per_maatregel(soort, m2, meerdere=True, biobased=False):
    """
    Wat een isolatiemaatregel oplevert, en waarom.

    meerdere is standaard waar, want de regeling vraagt om minimaal twee
    maatregelen; bij een enkele maatregel geldt het halve bedrag.
    """
    if soort not in PER_M2 or not m2:
        return None
    een, twee, bonus, rd = PER_M2[soort]
    tarief = twee if meerdere else een
    if biobased:
        tarief += bonus
    return {"soort": soort, "m2": m2, "tarief": tarief,
            "bedrag": round(tarief * m2, 2), "minimale_rd": rd,
            "grond": f"SVOH {PEILDATUM}, €{tarief:.2f} per m2"}


def ventilatie(kosten, meerdere=True, inclusief_btw=True):
    """
    CO2-gestuurde ventilatie: een deel van de kosten, met een plafond.

    Geef de kosten inclusief btw mee, want daarover wordt gerekend. Staat er
    een bedrag exclusief, zet inclusief_btw op False en dan telt het script de
    21% er zelf bij.
    """
    if not kosten:
        return None
    if not inclusief_btw:
        kosten = kosten * 1.21
    deel = VENTILATIE_DEEL[1 if meerdere else 0]
    plafond = VENTILATIE_MAX[1 if meerdere else 0]
    bedrag = min(kosten * deel, plafond)
    return {"soort": "co2_ventilatie", "kosten": round(kosten, 2), "deel": deel,
            "bedrag": round(bedrag, 2), "plafond": plafond,
            "grond": f"SVOH {PEILDATUM}, {int(deel * 100)}% van de kosten "
                     f"inclusief btw, met een maximum van €{plafond:.0f}"}


def totaal(posten, met_warmtepomp=False):
    """
    Alles bij elkaar, met het plafond per woning erop.

    Het plafond wordt apart gemeld, want als het bindt is elke extra maatregel
    voor de subsidie niets meer waard en verandert dat de volgorde waarin je
    ingrepen doet.
    """
    posten = [p for p in posten if p]
    ruw = sum(p["bedrag"] for p in posten)
    plafond = MAX_PER_WONING_MET_WARMTE if met_warmtepomp else MAX_PER_WONING
    return {"posten": posten, "ruw": round(ruw, 2),
            "bedrag": round(min(ruw, plafond), 2),
            "plafond": plafond, "plafond_bindt": ruw > plafond,
            "peildatum": PEILDATUM, "bron": BRON}


VOORWAARDEN = (
    "minimaal twee maatregelen, of een verduurzamings- en een "
    "onderhoudsmaatregel; de woning wordt al verhuurd voordat het werk begint; "
    "bestaande bouw met een woonfunctie in de BAG; uitgevoerd door een erkend "
    "bedrijf; aanvragen binnen 24 maanden na uitvoering; ventilatie alleen in "
    "combinatie met minstens een isolatiemaatregel"
)
