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


def _getal(waarde):
    """
    Maakt er een getal van, of None.

    Nodig omdat bouwjaar, oppervlakte en prijs uit verschillende bronnen komen
    en soms als tekst binnenkomen: de BAG geeft het bouwjaar als string.
    """
    if waarde is None:
        return None
    if isinstance(waarde, (int, float)):
        return waarde
    cijfers = re.sub(r"[^\d.]", "", str(waarde))
    if not cijfers:
        return None
    try:
        return float(cijfers) if "." in cijfers else int(cijfers)
    except ValueError:
        return None


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
    opp = _getal(w.get("oppervlakte"))
    prijs = _getal(w.get("prijs")) or 0
    woz = _getal(woz) or _getal(w.get("woz"))
    bouwjaar = _getal(w.get("bouwjaar"))
    aantal_kamers = _getal(aantal_kamers)

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
    Splitsen naar zelfstandige woningen, getoetst aan de Huisvestingsverordening
    gemeente Nijmegen 2024.

    Drie dingen die vaak door elkaar lopen:
    - juridisch of kadastraal splitsen in appartementsrechten: een notariele
      akte, ingeschreven in het Kadaster. Nijmegen vraagt daar geen vergunning
      voor; de verordening regelt alleen onttrekken en omzetten (artikel 13).
    - fysiek splitsen, woningvorming: van een woning meerdere zelfstandige
      woningen maken. Geen huisvestingsvergunning, wel een omgevingsvergunning.
    - omzetten of verkameren: van zelfstandig naar onzelfstandig. Dat is
      artikel 13 en 15, en valt hier buiten.

    De opkoopbescherming (artikel 19) toetst de WOZ van wat je koopt, op de
    datum dat de akte van levering wordt ingeschreven. Niet de WOZ van de
    eenheden die je daarna zelf maakt. Tot 21 september 2026 deed deze toets
    dat per eenheid, en dat was fout: het verborg panden die je wel mag
    splitsen en verhuren.
    """
    uit = [("artikel 15", VOLDOET,
            "niet van toepassing: splitsen naar zelfstandige woningen is geen "
            "omzetting naar onzelfstandige woonruimte"),
           ("splitsingsvergunning", VOLDOET,
            "Nijmegen kent die niet; de begrippen komen in de verordening niet voor")]

    opp = _getal(w.get("oppervlakte"))
    aantal_units = _getal(aantal_units)
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

    # De opkoopbescherming kijkt naar de WOZ van het pand dat je koopt, op de
    # datum van inschrijving van de akte. Een bekende WOZ gaat voor; anders de
    # vraagprijs als benadering, en dat zeggen we erbij.
    woz = _getal(w.get("woz"))
    waarde = woz or _getal(w.get("prijs")) or 0
    bron = "WOZ" if woz else "vraagprijs als benadering van de WOZ"
    grens = f"€{WOZ_BOVENGRENS:,}".replace(",", ".")
    if waarde:
        bedrag = f"€{waarde:,.0f}".replace(",", ".")
        if waarde <= WOZ_BOVENGRENS:
            uit.append(("opkoopbescherming", VOLDOET_NIET,
                        f"{bedrag} ({bron}) ligt op of onder {grens}. Koop je het "
                        f"vrij van huur, dan mag je het vier jaar na inschrijving "
                        f"van de akte niet verhuren zonder vergunning, gesplitst of "
                        f"niet. Splitsen om te verkopen blijft mogelijk"))
        else:
            uit.append(("opkoopbescherming", VOLDOET,
                        f"{bedrag} ({bron}) ligt boven {grens}. Dan is het geen "
                        f"beschermde woonruimte. Splitsen na aankoop is geen nieuwe "
                        f"levering aan jou, dus de eenheden die je zelf maakt vallen "
                        f"er niet onder"))

    # Wat wel verandert na fysiek splitsen: elke zelfstandige woning wordt een
    # eigen WOZ-object (artikel 16 Wet WOZ), ook zonder appartementsrechten.
    # Een lagere WOZ per eenheid geeft minder WWS-punten en dus een lagere
    # maximale huur. Dat is geen verbod maar een rekenfactor.
    if aantal_units and aantal_units > 1:
        uit.append(("WOZ per eenheid", ONBEKEND,
                    "na fysiek splitsen krijgt elke zelfstandige woning een eigen "
                    "WOZ, ook zonder juridische splitsing. Een lagere WOZ per "
                    "eenheid geeft minder punten in het woningwaarderingsstelsel "
                    "en dus een lagere maximale huur. En wie later een eenheid van "
                    f"jou koopt met een WOZ tot {grens}, valt zelf wel onder de "
                    "opkoopbescherming; dat raakt de verkoopbaarheid aan beleggers"))

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
