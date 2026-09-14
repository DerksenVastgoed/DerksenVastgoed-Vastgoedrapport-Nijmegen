#!/usr/bin/env python3
"""
Toetst een pand aan de weigeringsgronden van de Huisvestingsverordening
Nijmegen 2024, artikel 15, en aan de eisen voor splitsing.

Twee verschillende regimes, en dat onderscheid is de kern:

  KAMERVERHUUR is omzetting naar onzelfstandige woonruimte. Daarvoor geldt
  artikel 15 met acht weigeringsgronden, plus een omzettingsvergunning zolang
  de WOZ tussen de twee grenzen ligt.

  SPLITSEN naar zelfstandige appartementen is GEEN omzetting. Artikel 15 geldt
  daar niet. Nijmegen kent ook geen splitsingsvergunning. Wat overblijft is de
  omgevingsvergunning en het Bouwbesluit.

Elk oordeel is een van drie: voldoet, voldoet niet, of niet te toetsen. Dat
laatste is geen tekortkoming maar eerlijkheid: geluidsisolatie en het
omgevingsplan vragen onderzoek dat wij niet kunnen doen.
"""

import re

# Grenzen uit de verordening
WOZ_ONDERGRENS = 278_000
WOZ_BOVENGRENS = 396_000

# Bouwbesluit en verordening
FIETS_PER_BEWONER = 1.5      # m2 op eigen terrein, begane grond, aparte ruimte
GELUID_LUCHT_DB = 52         # NEN 5077, minimaal
GELUID_CONTACT_DB = 54       # NEN 5077, maximaal
MAX_NAAST_ELKAAR = 2

VOLDOET = "voldoet"
VOLDOET_NIET = "voldoet niet"
ONBEKEND = "niet te toetsen"


def _sleutel(straat, nr):
    a = straat.lower()
    for lang, kort in (("sint ", "st"), ("st. ", "st"), ("professor ", "prof"),
                       ("prof. ", "prof"), ("burgemeester ", "burg"),
                       ("burg. ", "burg"), ("doctor ", "dr"), ("dr. ", "dr")):
        a = a.replace(lang, kort)
    return re.sub(r"[^a-z0-9]", "", a) + str(nr)


def _buren(adres, vergunningen):
    """
    Welke panden grenzen er direct aan, en hebben die een vergunning?

    In Nederlandse straten liggen even en oneven nummers tegenover elkaar. De
    directe buren van nummer 42 zijn dus 40 en 44, niet 41 en 43. De regel over
    maximaal twee kamergewijs bewoonde woningen naast elkaar gaat over de
    aangrenzende panden, dus over dezelfde zijde van de straat.
    """
    m = re.match(r"^(.+?)\s+(\d+)", adres.strip())
    if not m or not vergunningen:
        return {}
    straat, nr = m.group(1), int(m.group(2))
    uit = {}
    for kant, offset in (("links", -2), ("rechts", 2)):
        buur = nr + offset
        if buur < 1:
            continue
        treffers = vergunningen.get(_sleutel(straat, str(buur)), [])
        if treffers:
            uit[kant] = treffers[0]
    return uit


def toets_kamerverhuur(w, aantal_kamers=None, vergunningen=None, woz=None):
    """
    Loopt de weigeringsgronden van artikel 15 langs. Geeft een lijst van
    (grond, oordeel, toelichting).
    """
    uit = []
    opp = w.get("oppervlakte")
    prijs = w.get("prijs") or 0
    woz = woz or w.get("woz")
    bouwjaar = w.get("bouwjaar")

    # 1. WOZ-ondergrens: absolute weigeringsgrond
    basis = woz or prijs
    herkomst = "WOZ" if woz else "vraagprijs als benadering"
    if basis and basis <= WOZ_ONDERGRENS:
        uit.append(("WOZ-ondergrens", VOLDOET_NIET,
                    f"€{basis:,.0f}".replace(",", ".")
                    + f" ({herkomst}) ligt op of onder €{WOZ_ONDERGRENS:,}".replace(",", ".")
                    + ". Omzetting wordt dan altijd geweigerd"))
    elif basis:
        uit.append(("WOZ-ondergrens", VOLDOET,
                    f"€{basis:,.0f}".replace(",", ".")
                    + f" ({herkomst}) ligt boven €{WOZ_ONDERGRENS:,}".replace(",", ".")))
    else:
        uit.append(("WOZ-ondergrens", ONBEKEND, "geen waarde bekend"))

    # Vergunningplicht zelf hangt aan de bovengrens
    if basis and basis > WOZ_BOVENGRENS:
        uit.append(("vergunningplicht", VOLDOET,
                    f"boven €{WOZ_BOVENGRENS:,}".replace(",", ".")
                    + " is geen omzettingsvergunning nodig, wel een "
                      "omgevingsvergunning vanaf drie kamers"))

    # 2. Strijd met het omgevingsplan
    uit.append(("omgevingsplan", ONBEKEND,
                "vraagt een raadpleging van het omgevingsplan op dit perceel; "
                "dat kunnen wij niet automatisch doen"))

    # 3. Geluidhinder
    if bouwjaar and bouwjaar < 1945:
        uit.append(("geluidhinder", ONBEKEND,
                    f"bouwjaar {bouwjaar}: vooroorlogse panden hebben vaak houten "
                    f"vloeren en dunne woningscheidende wanden, dus de kans dat "
                    f"{GELUID_CONTACT_DB} dB contactgeluid gehaald wordt zonder "
                    f"ingrijpende maatregelen is klein. Akoestisch onderzoek nodig"))
    else:
        uit.append(("geluidhinder", ONBEKEND,
                    f"vraagt akoestisch onderzoek: minimaal {GELUID_LUCHT_DB} dB "
                    f"luchtgeluidverschil en hooguit {GELUID_CONTACT_DB} dB "
                    f"contactgeluid volgens NEN 5077"))

    # 4. Fietsenstalling: wel te berekenen
    if aantal_kamers:
        nodig = aantal_kamers * FIETS_PER_BEWONER
        uit.append(("fietsenstalling", ONBEKEND,
                    f"bij {aantal_kamers} bewoners is {nodig:.1f}".replace(".", ",")
                    + " m² nodig op eigen terrein, op de begane grond, in een "
                      "afzonderlijke daartoe bestemde ruimte. Controleer of het "
                      "pand die ruimte heeft"))
    else:
        uit.append(("fietsenstalling", ONBEKEND,
                    f"{FIETS_PER_BEWONER} m² per bewoner nodig op eigen terrein"))

    # 5. Maximaal twee naast elkaar, en geen insluiting
    buren = _buren(w.get("adres", ""), vergunningen or {})
    links, rechts = buren.get("links"), buren.get("rechts")
    if links and rechts:
        uit.append(("maximaal twee naast elkaar", VOLDOET_NIET,
                    f"zowel {links.get('adres')} als {rechts.get('adres')} is al "
                    f"kamergewijs vergund. Dit pand zou de derde op rij worden"))
    elif links or rechts:
        buur = links or rechts
        uit.append(("maximaal twee naast elkaar", VOLDOET,
                    f"{buur.get('adres')} is al vergund; dit pand zou de tweede "
                    f"zijn, wat nog is toegestaan. Er is dan geen ruimte meer "
                    f"voor een derde"))
    else:
        uit.append(("maximaal twee naast elkaar", VOLDOET,
                    "de aangrenzende panden aan weerszijden staan niet in de "
                    "vergunningenlijst vanaf 2013. Let op: oudere vergunningen en "
                    "panden boven de WOZ-grens staan er niet in"))

    # 6. Insluiting van een zelfstandig bewoonde woning
    if links and rechts:
        uit.append(("insluiting", ONBEKEND,
                    "beide buren zijn vergund; controleer of er geen zelfstandig "
                    "bewoonde woning tussen komt te liggen"))
    else:
        uit.append(("insluiting", VOLDOET,
                    "geen aanwijzing dat een zelfstandig bewoonde woning wordt "
                    "ingesloten door kamerpanden"))

    # 7. Bouwbesluit: ruwe toets op oppervlakte per kamer
    if opp and aantal_kamers:
        per_kamer = opp * 0.79 / aantal_kamers
        if per_kamer < 10:
            uit.append(("Bouwbesluit kamergewijze verhuur", VOLDOET_NIET,
                        f"{per_kamer:.1f}".replace(".", ",")
                        + " m² per kamer is te krap; onder ongeveer 10 m² per "
                          "kamer loop je tegen eisen voor verblijfsruimte aan"))
        else:
            uit.append(("Bouwbesluit kamergewijze verhuur", ONBEKEND,
                        f"{per_kamer:.1f}".replace(".", ",")
                        + " m² per kamer lijkt haalbaar, maar daglicht, "
                          "ventilatie en vluchtwegen vragen een bouwkundige toets"))

    # 8. Brandveilig gebruik
    if aantal_kamers and aantal_kamers >= 5:
        uit.append(("brandveilig gebruik", ONBEKEND,
                    f"bij {aantal_kamers} kamers is een melding brandveilig gebruik "
                    f"verplicht, met eisen aan rookmelders, vluchtwegen en "
                    f"brandwerende scheidingen"))

    return uit


def toets_splitsing(w, aantal_units=None):
    """
    Splitsen naar zelfstandige woningen valt niet onder artikel 15: het is geen
    omzetting naar onzelfstandige woonruimte, en Nijmegen kent geen
    splitsingsvergunning. Wat blijft is de omgevingsvergunning en het
    Bouwbesluit, plus de opkoopbescherming per nieuwe eenheid.
    """
    uit = [("artikel 15", VOLDOET,
            "niet van toepassing: splitsen naar zelfstandige woningen is geen "
            "omzetting naar onzelfstandige woonruimte"),
           ("splitsingsvergunning", VOLDOET,
            "Nijmegen kent die niet; de begrippen komen in de verordening niet voor")]

    opp = w.get("oppervlakte")
    if opp and aantal_units:
        per_unit = opp * 0.90 / aantal_units
        uit.append(("oppervlakte per eenheid", ONBEKEND,
                    f"{per_unit:.0f} m² per woning. Nijmegen verleende in september "
                    f"2026 een vergunning voor eenheden van 53, 43 en 32 m², dus "
                    f"kleine eenheden worden geaccepteerd"))

    uit.append(("omgevingsvergunning", ONBEKEND,
                "wel vereist voor de verbouwing. Ingediend worden doorgaans: "
                "constructierapport, brandveiligheidstekening, ventilatierapport, "
                "riolering, gevelaanzichten, ruimtetabel volgens NEN 2580 en een "
                "parkeernotitie"))
    uit.append(("Bouwbesluit", VOLDOET,
                "bij bestaande bouw geldt het van rechtens verkregen niveau, niet "
                "de nieuwbouwnorm. Dat scheelt aanzienlijk bij vooroorlogse panden"))

    prijs = w.get("prijs") or 0
    if prijs and aantal_units:
        per_unit_waarde = prijs / aantal_units
        if per_unit_waarde < WOZ_BOVENGRENS:
            uit.append(("opkoopbescherming", VOLDOET_NIET,
                        f"€{per_unit_waarde:,.0f}".replace(",", ".")
                        + f" per eenheid ligt onder €{WOZ_BOVENGRENS:,}".replace(",", ".")
                        + ". De nieuwe woningen mogen dan vier jaar na levering niet "
                          "verhuurd worden zonder vergunning. Verkopen mag wel"))
        else:
            uit.append(("opkoopbescherming", VOLDOET,
                        f"€{per_unit_waarde:,.0f}".replace(",", ".")
                        + " per eenheid ligt boven de grens"))

    uit.append(("parkeren", ONBEKEND,
                "in gereguleerd gebied geldt geen parkeereis, maar de nieuwe "
                "huisnummers krijgen ook geen parkeervergunning"))
    return uit


def samenvatting(regels):
    """Kort oordeel: waar loopt het op vast, en wat moet je uitzoeken."""
    blokkades = [r for r in regels if r[1] == VOLDOET_NIET]
    open_punten = [r for r in regels if r[1] == ONBEKEND]
    if blokkades:
        return (f"{len(blokkades)} blokkade" + ("s" if len(blokkades) > 1 else "")
                + ": " + ", ".join(r[0] for r in blokkades)
                + f". Daarnaast {len(open_punten)} punt"
                + ("en" if len(open_punten) != 1 else "") + " uit te zoeken")
    return (f"geen blokkades gevonden, {len(open_punten)} punt"
            + ("en" if len(open_punten) != 1 else "") + " uit te zoeken: "
            + ", ".join(r[0] for r in open_punten[:4]))
