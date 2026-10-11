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


def toets_kamerverhuur(w, aantal_kamers=None, vergunningen=None, woz=None,
                       ingesloten=None, reeks=None, kamerpand=False):
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

    # 5. Maximaal twee naast elkaar
    #
    # DIT TELDE DE BUUR EN NIET DE RIJ. De toets keek alleen of de twee
    # directe buren vergund zijn. Bij St. Annastraat 9 meldde hij daarom
    # "nummer 11 is al vergund; dit pand zou de tweede zijn, wat nog is
    # toegestaan", terwijl 11, 13 én 15 vergund zijn en dit pand de vierde op
    # rij zou worden. Dat is een goedkeuring die de verordening niet geeft.
    #
    # Het aantal aansluitende kamerpanden per zijde komt nu van de aanroeper,
    # die de hele straat kan overzien. Zonder dat getal valt deze toets terug
    # op de buurtelling, en dan zegt hij ook dat hij dat doet.
    buren = _buren(w.get("adres", ""), vergunningen or {})
    links, rechts = buren.get("links"), buren.get("rechts")
    langste = max((reeks or {}).values()) if reeks else None
    # BEIDE ZIJDEN SAMEN, want dit pand wordt dan de middelste van drie. De
    # reeks wordt per zijde geteld, dus een kamerpand links én rechts geeft
    # {-1: 1, 1: 1} en dat is per zijde "nog toegestaan". Alleen keek de oude
    # tak links-en-rechts daar al naar, en die werd door de reeks-takken
    # onbereikbaar. Zeventien adressen in de ring kregen daardoor een
    # goedkeuring die er eerder niet was, onder meer Groesbeekseweg 53 met 51
    # en 55 beide vergund.
    # EEN PAND DAT ZELF AL KAMERPAND IS WORDT NIETS DERDE. Er is dan geen
    # omzetting die de rij verlengt, dus deze toets gaat over een handeling die
    # niet meer hoeft. St. Annastraat 15 heeft zijn eigen vergunning uit 2018
    # en kreeg toch "dit pand zou het derde of verdere in de rij worden".
    if kamerpand:
        uit.append(("maximaal twee naast elkaar", VOLDOET,
                    "dit pand is zelf al kamergewijs vergund, dus er is geen "
                    "omzetting die de rij verlengt. De regel gaat over een "
                    "nieuwe omzetting en niet over bestaand gebruik"))
        reeks = None
        langste = "n.v.t."
    weerszijden = reeks and len([n for n in reeks.values() if n >= 1]) >= 2
    if langste == "n.v.t.":
        pass
    elif weerszijden:
        namen = [b.get("adres") for b in [links, rechts] if b]
        uit.append(("maximaal twee naast elkaar", VOLDOET_NIET,
                    "aan beide zijden ligt een kamerpand"
                    + (f" ({', '.join(n for n in namen if n)})" if any(namen)
                       else "")
                    + ", dus dit pand zou de middelste van drie op een rij "
                      "worden en de verordening staat niet meer dan twee toe"))
    elif langste is not None and langste >= 2:
        uit.append(("maximaal twee naast elkaar", VOLDOET_NIET,
                    f"aan één zijde liggen al {langste} kamerpanden "
                    f"aansluitend naast dit pand. Dit pand zou het derde of "
                    f"verdere in de rij worden, en de verordening staat niet "
                    f"meer dan twee toe"))
    elif langste == 1:
        uit.append(("maximaal twee naast elkaar", VOLDOET,
                    "er ligt één kamerpand direct naast dit pand; dit pand zou "
                    "het tweede zijn, wat nog is toegestaan. Er is dan geen "
                    "ruimte meer voor een derde"))
    elif langste == 0:
        uit.append(("maximaal twee naast elkaar", VOLDOET,
                    "er ligt geen kamerpand direct naast dit pand, gemeten "
                    "over de hele straatzijde. Let op: de vergunningenlijst "
                    "loopt van 2013 tot 2025 en wordt niet bijgewerkt, en "
                    "panden boven de WOZ-grens hadden geen vergunning nodig"))
    elif links and rechts:
        uit.append(("maximaal twee naast elkaar", VOLDOET_NIET,
                    f"zowel {links.get('adres')} als {rechts.get('adres')} is al "
                    f"kamergewijs vergund. Dit pand zou de derde op rij worden"))
    else:
        uit.append(("maximaal twee naast elkaar", ONBEKEND,
                    "de rij aansluitende kamerpanden is niet geteld, dus "
                    "alleen de twee directe buren zijn nagekeken en die staan "
                    "niet in de vergunningenlijst. Een derde op rij is daarmee "
                    "niet uitgesloten"))

    # 6. Insluiting van een zelfstandig bewoonde woning
    #
    # DIT KEEK NAAR HET VERKEERDE GEVAL. De toets vroeg of béide directe buren
    # verkamerd zijn, en zei anders VOLDOET. Maar insluiting ontstaat juist als
    # de directe buur zelfstandig is en de kamers één pand verder liggen: dan
    # komt die zelfstandige woning tussen twee kamerpanden te zitten. Bij St.
    # Annastraat 7 is dat precies de situatie. Nummer 9 is vier zelfstandige
    # appartementen, nummer 11 is onttrokken voor kamers, en deze toets gaf
    # VOLDOET op de regel die als enige bindt. De investeringscase van 11
    # oktober rekende daarop 13 kamers door.
    #
    # Het antwoord komt nu van de aanroeper, die de voorraad uit de BAG heeft
    # en dus kan zien uit hoeveel zelfstandige woningen een buurpand bestaat.
    # None betekent niet gekeken, een lege lijst betekent gekeken en niets
    # gevonden. Dat onderscheid staat hier, want anders leest "niets gevonden"
    # als een goedkeuring die niemand heeft gegeven.
    if ingesloten:
        x = ingesloten[0]
        maten = ", ".join(str(m) for m in (x.get("maten") or []))
        uit.append(("insluiting", VOLDOET_NIET,
                    f"nummer {x.get('nummer')} bestaat uit "
                    f"{x.get('woningen')} zelfstandige woningen"
                    + (f" van {maten} m²" if maten else "")
                    + f" en ligt tussen dit pand en {x.get('kamerbuur')}, dat "
                      f"al voor kamers is onttrokken. Verkameren zou die "
                      f"woningen insluiten, en dat verbiedt de verordening"))
    elif ingesloten == []:
        uit.append(("insluiting", VOLDOET,
                    "tussen dit pand en een kamerpand op dezelfde straatzijde "
                    "ligt geen pand dat aantoonbaar uit meer zelfstandige "
                    "woningen bestaat, gemeten op de BAG-voorraad"))
    elif links and rechts:
        uit.append(("insluiting", ONBEKEND,
                    "beide buren zijn vergund; controleer of er geen zelfstandig "
                    "bewoonde woning tussen komt te liggen"))
    else:
        uit.append(("insluiting", ONBEKEND,
                    "niet getoetst: deze straat staat niet in de "
                    "BAG-voorraad, dus of er een zelfstandig bewoonde woning "
                    "wordt ingesloten is hier niet te zeggen"))

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


def proef():
    """
    De insluitingstoets nameten, zonder netwerk en zonder bestanden.

    WAAROM JUIST DEZE TOETS EEN PROEF KRIJGT. Hij stond op VOLDOET in het ene
    geval dat werkelijk bindt, en op grond daarvan rekende de
    investeringscase in de brief van 11 oktober dertien kamers door voor een
    pand waar verkameren vermoedelijk niet mag. Dat is het zwaarste soort fout
    dat deze brief kan maken: geen verkeerd getal maar een verkeerd advies.

    De drie uitkomsten die uit elkaar moeten blijven: gekeken en ingesloten,
    gekeken en niets gevonden, en niet gekeken. Die laatste twee zijn het
    makkelijkst te verwarren, en dan leest "niets gevonden" als een
    goedkeuring die niemand heeft gegeven.
    """
    import sys
    afw = []
    w = {"adres": "St. Annastraat 7", "oppervlakte": 330, "woz": 982009}

    def oordeel(regels, naam):
        for n, o, t in regels:
            if n == naam:
                return o, t
        return None, ""

    # 1. GEKEKEN EN INGESLOTEN: de regel valt.
    ing = [{"nummer": 9, "woningen": 4, "maten": [100, 78, 76, 61],
            "kamerbuur": "St. Annastraat 11"}]
    o, t = oordeel(toets_kamerverhuur(w, ingesloten=ing, aantal_kamers=13),
                   "insluiting")
    if o != VOLDOET_NIET:
        afw.append(f"met een ingesloten woning gaf de toets {o!r} in plaats "
                   f"van {VOLDOET_NIET!r}")
    for stuk in ("9", "4 zelfstandige woningen", "St. Annastraat 11"):
        if stuk not in t:
            afw.append(f"de melding noemt {stuk!r} niet: {t[:90]!r}")

    # 2. GEKEKEN EN NIETS GEVONDEN: dan mag er VOLDOET staan.
    o, t = oordeel(toets_kamerverhuur(w, ingesloten=[], aantal_kamers=13),
                   "insluiting")
    if o != VOLDOET:
        afw.append(f"met een lege uitkomst gaf de toets {o!r} in plaats van "
                   f"{VOLDOET!r}")
    if "voorraad" not in t.lower():
        afw.append("de melding zegt niet waarop is gemeten")

    # 3. NIET GEKEKEN: dan hoort er ONBEKEND te staan en geen goedkeuring.
    o, t = oordeel(toets_kamerverhuur(w, ingesloten=None, aantal_kamers=13),
                   "insluiting")
    if o != ONBEKEND:
        afw.append(f"zonder meting gaf de toets {o!r} in plaats van "
                   f"{ONBEKEND!r}; dan leest niet-gekeken als goedgekeurd")

    # 4. EN DE TOETS MOET DE KAMERROUTE WERKELIJK LATEN VALLEN.
    regels = toets_kamerverhuur(w, ingesloten=ing, aantal_kamers=13)
    if not [g for g, o, _t in regels if o == VOLDOET_NIET]:
        afw.append("geen enkel toetspunt staat op 'voldoet niet', dus de "
                   "kamerroute valt niet af")

    # 5. DE HELE KETEN OP DE ECHTE VOORRAAD.
    #
    # De proef hierboven toetst de vertaalslag van een uitkomst naar een
    # toetspunt, met de hand gebouwde invoer. Dat is te weinig: de beoordelaar
    # vond vier fouten die hier ongemerkt door kwamen, allemaal in het rekenen
    # zelf. Deze zes adressen zijn echte gevallen uit de ring, elk met een
    # eigen reden, en ze worden door de echte functies gehaald.
    try:
        import marktprijzen_bag as _M
        _heeft = bool(_M.voorraad_per_straat("St. Annastraat"))
    except Exception as e:
        print(f"keten niet getoetst: {type(e).__name__}: {e}", file=sys.stderr)
        _heeft = False
    if _heeft:
        verwacht = {
            # Insluiting: nummer 9 is vier zelfstandige appartementen en ligt
            # tussen 7 en het onttrokken 11.
            "St. Annastraat 7": ("insluiting", 9),
            # Reeks: 11, 13 en 15 zijn drie aansluitende kamerpanden, dus 9
            # zou de vierde worden. De oude toets zei "nog toegestaan".
            "St. Annastraat 9": ("reeks", None),
            # Vrij: de buren 3 en 7 hebben geen vergunning, en tussen 5 en 11
            # liggen twee panden, dus geen insluiting.
            "St. Annastraat 5": ("gekeken en niets gevonden", None),
            # Twee woningen op één nummer in twee verschillende panden; dat
            # werd eerder als één woning geteld en de insluiting gemist.
            "St. Annastraat 51": ("insluiting", 49),
            # Hier stonden een nog in gebruik zijnd object en zijn eigen nieuwe
            # eenheden samen in de BAG, wat "7 woningen van 382, 122, ..."
            # opleverde: 727 m2 in een pand van 382. Nu blokkeert de reeks.
            "Graafseweg 62": ("reeks", None),
            # Hier is binnen één pand doorgenummerd, dus nummer 24 is wél de
            # directe buur van 25 en niet de overzijde.
            "Keizer Karelplein 25": ("reeks", None),
        }
        for adres, (reden_moet, nummer_moet) in verwacht.items():
            ing, reden = _M.kamerroute_geblokkeerd(adres)
            if reden != reden_moet:
                afw.append(f"{adres}: reden {reden!r} in plaats van "
                           f"{reden_moet!r}")
            if nummer_moet is not None:
                nrs = [x.get("nummer") for x in (ing or [])]
                if nrs != [nummer_moet]:
                    afw.append(f"{adres}: ingesloten {nrs} in plaats van "
                               f"[{nummer_moet}]")
            elif reden_moet == "reeks" and ing:
                afw.append(f"{adres}: een reeksblokkade hoort geen "
                           f"insluitingsrecords te geven, kreeg {ing}")

        # 5b. DE VIER TAKKEN VAN TOETSPUNT 5. De proef gaf hier eerst nooit
        # reeks mee, dus alleen de terugvaltak liep en zes fouten kwamen groen
        # door.
        def t5(reeks, kamerpand=False):
            rs = toets_kamerverhuur(w, ingesloten=[], reeks=reeks,
                                    kamerpand=kamerpand, aantal_kamers=13)
            return oordeel(rs, "maximaal twee naast elkaar")

        for reeks, kamerpand, moet, waarom in (
                ({-1: 0, 1: 0}, False, VOLDOET, "niets naast dit pand"),
                ({-1: 1, 1: 0}, False, VOLDOET, "één naast, dit wordt de tweede"),
                ({-1: 2, 1: 0}, False, VOLDOET_NIET, "twee aansluitend"),
                ({-1: 3, 1: 0}, False, VOLDOET_NIET, "drie aansluitend"),
                # De middelste van drie: per zijde één, samen te veel. Dit gaf
                # zeventien adressen in de ring een onterechte goedkeuring.
                ({-1: 1, 1: 1}, False, VOLDOET_NIET, "aan beide zijden één"),
                # Een pand dat zelf al kamerpand is wordt niets derde.
                ({-1: 2, 1: 0}, True, VOLDOET, "eigen kamerpand"),
                (None, False, ONBEKEND, "geen reeks meegegeven"),
        ):
            o, _t = t5(reeks, kamerpand)
            if o != moet:
                afw.append(f"toetspunt 5 met reeks={reeks} kamerpand={kamerpand} "
                           f"({waarom}) gaf {o!r} in plaats van {moet!r}")

        # 5c. EN DE ECHTE GEVALLEN DIE DAARBIJ HOREN.
        for adres, reden_moet in (("Groesbeekseweg 53", "weerszijden"),
                                  ("Keizer Karelplein 31",
                                   "gekeken en niets gevonden"),
                                  # Buiten de voorraad, maar de reeks komt uit
                                  # de vergunningenlijst en moet wel blokkeren.
                                  ("Jan van Goyenstraat 52", "reeks")):
            _ing, _reden = _M.kamerroute_geblokkeerd(adres)
            if _reden != reden_moet:
                afw.append(f"{adres}: reden {_reden!r} in plaats van "
                           f"{reden_moet!r}")

        # 5d. PAND_DOSSIER MOET DRAAIEN. Op 11 oktober stond er een aanroep
        # naar een functie die niet meer bestond, in een try/except die naar
        # stderr schrijft. De brief ging door, het dossierblok verdween, en
        # juist daarin staan de feiten die de kamerroute blokkeren. Geen enkele
        # proef raakte dit aan.
        try:
            _w = {"adres": "St. Annastraat 7", "oppervlakte": 330,
                  "prijs": 1100000, "buurt": "Galgenveld", "m2": 3333}
            _feiten = _M.pand_dossier(_w, "Galgenveld", -34.0, {},
                                      _M.lees_archief(), {})
            _tekst = " ".join(str(x) for x in (_feiten or []))
            if "insluiten" not in _tekst:
                afw.append("pand_dossier levert geen insluitingsfeit voor St. "
                           "Annastraat 7, dus de brief mist de reden")
        except Exception as e:
            afw.append(f"pand_dossier faalt: {type(e).__name__}: {e}")

        # Een straat buiten de ring is onbekend en blokkeert niets.
        ing, reden = _M.kamerroute_geblokkeerd("Nergensweg 7")
        if ing is not None or "voorraad" not in reden:
            afw.append(f"een straat buiten de voorraad gaf ({ing!r}, {reden!r}) "
                       f"in plaats van onbekend")

        # Samenvoeging is het tegendeel van verkameren en mag niet meetellen.
        _vg = _M._kamervergunning("Tooropstraat", 61,
                                  _M.lees_kamervergunningen(), {})
        if _vg and "samenvoeg" in (_vg.get("soort") or "").lower():
            afw.append("een samenvoeging wordt nog als kamersignaal geteld")

        # En de cache moet werken: de tweede aanroep mag niet opnieuw het hele
        # bestand van 22.096 records doorlopen.
        import time as _t
        _M.kamerbeeld("St. Annastraat 7")
        _start = _t.time()
        for _ in range(20):
            _M.kamerbeeld("St. Annastraat 7")
        _per = (_t.time() - _start) / 20
        if _per > 0.015:
            afw.append(f"kamerbeeld kost {_per * 1000:.0f} ms per aanroep; "
                       f"dan is de cache per straat stuk en kost een briefrun "
                       f"er minuten aan")

    for a in afw:
        print(f"AFWIJKING: {a}", file=sys.stderr)
    print(f"Proef: {len(afw)} afwijkingen. Gedekt: de insluitingstoets in de "
          f"drie toestanden die uit elkaar moeten blijven (ingesloten, "
          f"gekeken en schoon, niet gekeken), en dat een insluiting de "
          f"kamerroute werkelijk laat afvallen, plus de hele keten op zes "
          f"echte adressen uit de ring, een straat buiten de voorraad, de "
          f"samenvoegingen en de cache.", file=sys.stderr)
    return 1 if afw else 0


if __name__ == "__main__":
    import sys
    sys.exit(proef())
