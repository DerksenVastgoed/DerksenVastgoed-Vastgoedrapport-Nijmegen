#!/usr/bin/env python3
"""
Van bouwjaar naar isolatie, en van isolatie naar maatregelen.

De gedachte: het bouwjaar uit de BAG zegt welke eisen er golden toen het pand
werd gebouwd, en daarmee wat er waarschijnlijk in de gevel, het dak en de vloer
zit. Een pand uit 1930 heeft geen isolatie, een pand uit 2016 heeft bijna
nieuwbouwwaarden. Het energielabel is de tegenproef: is dat label veel beter
dan het bouwjaar doet vermoeden, dan is er na de bouw geisoleerd.

Wat hier staat is een uitgangspunt en geen meting. Zolang er geen opname is
gedaan, weten we niet wat er werkelijk in de spouw zit. Daarom geeft elke
uitkomst zijn grond mee: uit het bouwjaar, uit het label, of uit een vergunning.

Bron van de eisen: de Rc-waarden per bouwjaarklasse zoals die in het Bouwbesluit
en zijn voorgangers golden, en de huidige nieuwbouweisen uit het Besluit
bouwwerken leefomgeving.
"""

# Rc-waarde in m2K/W die gold toen het pand werd gebouwd. Voor 1965 golden er
# geen isolatie-eisen: muren waren massief of spouw zonder isolatie.
EISEN = [
    # (vanaf, tot, gevel, dak, vloer)
    (0,    1965, 0.00, 0.00, 0.00),
    (1965, 1975, 0.43, 0.86, 0.17),
    (1975, 1983, 1.30, 1.30, 0.52),
    (1983, 1988, 1.30, 1.30, 1.30),
    (1988, 1992, 2.00, 2.00, 1.30),
    (1992, 2014, 2.50, 2.50, 2.50),
    (2014, 2015, 3.50, 3.50, 3.50),
    (2015, 2021, 4.50, 6.00, 3.50),
    (2021, 9999, 4.70, 6.30, 3.70),
]

# Waar je naartoe moet bij een ingreep. De bovenste rij is de nieuwbouweis, die
# geldt bij een ingrijpende renovatie; de onderste is het minimum dat altijd
# geldt als je een bouwdeel vervangt.
NIEUWBOUW = {"gevel": 4.70, "dak": 6.30, "vloer": 3.70}
MINIMUM_BIJ_VERVANGING = {"gevel": 1.30, "dak": 2.00, "vloer": 2.50}

# Een label dat veel beter is dan het bouwjaar toelaat, betekent dat er na de
# bouw is geisoleerd. Deze grens is grof: hij zegt alleen "hier is aan gewerkt".
LABEL_RANG = {"A++++": 0, "A+++": 1, "A++": 2, "A+": 3, "A": 4, "B": 5,
              "C": 6, "D": 7, "E": 8, "F": 9, "G": 10}


def eisen_bij_bouwjaar(bouwjaar):
    """De Rc-waarden die golden toen dit pand werd gebouwd."""
    if not bouwjaar:
        return None
    for vanaf, tot, gevel, dak, vloer in EISEN:
        if vanaf <= int(bouwjaar) < tot:
            return {"periode": f"{vanaf if vanaf else 'voor'}-{tot}",
                    "gevel": gevel, "dak": dak, "vloer": vloer}
    return None


def label_wijst_op_ingreep(bouwjaar, label):
    """
    Is dit label beter dan het bouwjaar doet verwachten?

    Zo ja, dan is er na de bouw geisoleerd en kloppen de waarden uit de tabel
    niet meer. We weten dan niet wat er precies is gedaan, alleen dat er iets
    is gedaan; dat is genoeg om de aanname niet blind te gebruiken.
    """
    if not bouwjaar or not label:
        return None
    rang = LABEL_RANG.get(label.upper())
    if rang is None:
        return None
    jaar = int(bouwjaar)
    # Wat je zonder ingreep ongeveer mag verwachten: oude bouw eindigt laag,
    # nieuwbouw hoog. De grens ligt bij label C voor bouw vanaf 1992.
    verwacht_slechter_dan = 5 if jaar < 1992 else 7   # B respectievelijk D
    if jaar < 1975 and rang <= LABEL_RANG["C"]:
        return ("label {} bij bouwjaar {}: veel beter dan een pand uit die tijd "
                "zonder ingreep haalt, dus er is na de bouw geisoleerd"
                .format(label, jaar))
    if rang < verwacht_slechter_dan and jaar < 1992:
        return ("label {} bij bouwjaar {}: beter dan verwacht, waarschijnlijk "
                "deels geisoleerd".format(label, jaar))
    return None


def maatregelen(bouwjaar, label=None, uitgevoerd=None):
    """
    Welke bouwdelen vragen nog om een ingreep, en waarom.

    uitgevoerd is een verzameling bouwdelen waarvan we uit vergunningen of uit
    de pandgeschiedenis weten dat ze al zijn aangepakt; die vallen af.
    """
    eis = eisen_bij_bouwjaar(bouwjaar)
    if not eis:
        return {"bekend": False,
                "reden": "geen bouwjaar bekend; zonder bouwjaar geen uitgangspunt"}
    uitgevoerd = {d.lower() for d in (uitgevoerd or [])}
    uit = []
    for deel in ("gevel", "dak", "vloer"):
        huidig = eis[deel]
        doel = NIEUWBOUW[deel]
        if deel in uitgevoerd:
            uit.append({"deel": deel, "nodig": False,
                        "reden": "al uitgevoerd volgens een vergunning of de "
                                 "pandgeschiedenis"})
            continue
        if huidig >= MINIMUM_BIJ_VERVANGING[deel]:
            uit.append({"deel": deel, "nodig": False,
                        "van": huidig, "naar": doel,
                        "reden": f"Rc {huidig} uit het bouwjaar haalt het "
                                 f"minimum bij vervanging al"})
            continue
        uit.append({"deel": deel, "nodig": True, "van": huidig, "naar": doel,
                    "reden": f"Rc {huidig} uit bouwjaarklasse {eis['periode']}, "
                             f"onder het minimum van "
                             f"{MINIMUM_BIJ_VERVANGING[deel]} bij vervanging"})
    twijfel = label_wijst_op_ingreep(bouwjaar, label)
    return {"bekend": True, "periode": eis["periode"], "delen": uit,
            "waarschuwing": twijfel,
            "grond": "Rc-eisen per bouwjaarklasse; uitgangspunt, geen opname"}
