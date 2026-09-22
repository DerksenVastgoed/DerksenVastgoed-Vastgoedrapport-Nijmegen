#!/usr/bin/env python3
"""
De bronnenlijst onder de brief.

Elk cijfer in deze brief komt ergens vandaan, en niet elke bron is even hard.
Een BAG-oppervlakte is een registratie, een gemeten kamerhuur is een handvol
advertenties, en een verbouwingsraming is een aanname. Dat verschil hoort
zichtbaar te zijn, anders lezen ze allemaal even stellig.

Per bron staat er wat hij levert, hoe actueel hij is en waar hij vandaan komt.
"""

import datetime as dt
import json
import os
import sys

# De bronnen die de brief gebruikt, met hun aard. Drie soorten:
#   registratie: officiele vastlegging, het hardst
#   meting:      eigen waarneming uit advertenties of publicaties
#   aanname:     door ons gekozen, te vervangen door eigen cijfers
BRONNEN = [
    # --- Registraties ---
    ("BAG", "registratie",
     "oppervlakte, bouwjaar en gebruiksdoel per verblijfsobject",
     "Kadaster, api.bag.kadaster.nl", "doorlopend"),
    ("EP-Online", "registratie",
     "energielabel en registratiedatum",
     "RVO, public.ep-online.nl", "doorlopend"),
    ("Kerncijfers wijken en buurten", "registratie",
     "woningvoorraad, eigendom, inkomen, vermogen, huishoudens en studenten",
     "CBS via PDOK", "jaarlijks, inkomen loopt twee jaar achter"),
    ("Politiedata", "registratie",
     "geregistreerde misdrijven per buurt en soort",
     "politie via dataderden.cbs.nl, tabel 47018NED", "jaarcijfers"),
    ("Officiele bekendmakingen", "registratie",
     "vergunningen, meldingen, besluiten en beleidsstukken van de gemeente",
     "KOOP, repository.overheid.nl", "dagelijks"),
    ("CVDR en Basiswettenbestand", "registratie",
     "gemeentelijke verordeningen en landelijke wetgeving",
     "KOOP, zoekservice.overheid.nl", "dagelijks"),
    ("Staatsblad en Staatscourant", "registratie",
     "gepubliceerde wetten, besluiten en regelingen op rijksniveau",
     "KOOP, repository.overheid.nl", "dagelijks"),
    ("Rijksoverheid", "meting",
     "persberichten over voorgenomen beleid en wetsvoorstellen",
     "rijksoverheid.nl", "dagelijks"),
    ("Kamerverhuurvergunningen", "registratie",
     "verleende onttrekkings-, omzettings- en omgevingsvergunningen",
     "gemeente Nijmegen, Woo-verzoek", "2013 tot 2025, niet bijgewerkt"),
    ("OV-haltes", "registratie",
     "bus-, tram- en treinhaltes met coordinaten",
     "OpenStreetMap via Overpass", "eens per jaar opgehaald"),
    ("Looproutes", "meting",
     "werkelijke loopafstand van pand naar halte over het wegennet",
     "OSRM, voetgangersprofiel", "per pand berekend en bewaard"),
    ("Rijksmonumenten", "registratie",
     "monumentenstatus per adres",
     "Rijksdienst voor het Cultureel Erfgoed", "doorlopend"),
    ("ECB Data Portal", "registratie",
     "tienjaars AAA-staatsrente in de eurozone",
     "data-api.ecb.europa.eu", "dagelijks"),
    ("WOZ", "registratie",
     "waarde per pand, handmatig ingevoerd",
     "wozwaardeloket.nl", "jaarlijks, alleen voor ingevoerde panden"),

    # --- Metingen ---
    ("Aanbod", "meting",
     "vraagprijzen en oppervlaktes uit attenderingen",
     "Funda, Funda Business, Vendr", "dagelijks"),
    ("Huurniveaus", "meting",
     "gevraagde huur per m2 per grootteklasse en buurt",
     "Pararius en Kamernet", "dagelijks, kleine aantallen"),
    ("Verhuurhypotheekrente", "meting",
     "scherpste tarief per financieringsgraad",
     "financieren.nl", "dagelijks"),
    ("Vakpublicaties", "meting",
     "marktberichten met duiding",
     "PropertyNL, Vastgoed Insider, Vastgoedmarkt en overige", "dagelijks"),

    # --- Aannames ---
    ("Exploitatiekosten", "aanname",
     "20% bij gewone verhuur, 25% bij kamerverhuur, 22% bij splitsing",
     "eigen aanname, te vervangen door de eigen administratie", "vast"),
    ("Verbouwkosten", "aanname",
     "verduurzaming naar energielabel plus verhuurklaar maken, inclusief btw",
     "eigen aanname in bouwkosten_eigen.txt, anders een schatting van het "
     "script; de RVO-kentallen zijn nog niet ingelezen",
     "peildatum mei 2025, geindexeerd naar nu"),
    ("Bouwkostenindex", "registratie",
     "inputprijsindex bouwkosten, loon en materiaal, om de kentallen te "
     "indexeren",
     "CBS tabel 85728NED", "maandelijks, circa 30 dagen vertraging"),
    ("Aanloopperiode", "aanname",
     "drie maanden zonder huur bij aanvang",
     "eigen aanname", "vast"),
    ("Verhuurbaar aandeel", "aanname",
     "79% bij kamerverhuur, 90% bij splitsing",
     "afgeleid uit twee verkoopbrochures", "vast"),
]

# Wettelijke kaders waarop de brief toetst, met de vindplaats
KADERS = [
    ("NTA 8800:2025 en EPBD IV",
     "rekenmethodiek energielabel; nieuwe klasse A0 en labelplicht voor "
     "monumenten bij verkoop of verhuur",
     "geldt voor labels geregistreerd vanaf 29 mei 2026; oudere labels blijven "
     "geldig"),
    ("Huisvestingsverordening gemeente Nijmegen 2024",
     "opkoopbescherming, omzetting, onttrekking, weigeringsgronden artikel 15",
     "geldend van 01-01-2024 tot en met 31-12-2027"),
    ("Woningwaarderingsstelsel onzelfstandige woonruimte",
     "maximale kamerhuur en puntentelling",
     "Beleidsboek Huurcommissie, januari 2026"),
    ("Woningwaarderingsstelsel zelfstandige woonruimte",
     "maximale huur en de grens naar de vrije sector bij 187 punten",
     "huurprijstabel per 1 januari 2026"),
    ("Wet op belastingen van rechtsverkeer",
     "overdrachtsbelasting 8% sinds 1 januari 2026, doorverkoopregeling "
     "artikel 13 bij verkoop binnen zes maanden",
     "tarief jaarlijks controleren"),
    ("Huurtoeslaggrenzen",
     "kwaliteitskorting, aftopping en maximale rekenhuur",
     "bedragen per 1 januari 2026"),
]


# De nummering: de volgorde van BRONNEN bepaalt het cijfer. Zo staat er in de
# tekst [3] en onderaan bij 3 dezelfde bron.
NUMMER = {naam: i + 1 for i, (naam, *_rest) in enumerate(BRONNEN)}


def verwijs(*namen):
    """
    Geeft de verwijzing bij een of meer bronnen, als [1] of [1,4,7].

    Gebruik dit onder een tabel of achter een bewering, niet achter elk cijfer:
    een brief vol cijfertjes leest niet meer.
    """
    nummers = sorted(NUMMER[n] for n in namen if n in NUMMER)
    return f"[{','.join(str(x) for x in nummers)}]" if nummers else ""


def bestandsdatum(pad):
    """Wanneer is dit gegevensbestand voor het laatst bijgewerkt?"""
    try:
        return dt.date.fromtimestamp(os.path.getmtime(pad)).isoformat()
    except Exception:
        return ""


def tel(pad, sleutel=None):
    """Hoeveel zit er in dit bestand?"""
    try:
        with open(pad, encoding="utf-8") as f:
            data = json.load(f)
        return len(data) if isinstance(data, (dict, list)) else None
    except Exception:
        return None


def render(uitgebreid=True):
    """De bronnenlijst. Kort in de dagelijkse brief, volledig op zondag."""
    r = ["", "## Bronnen", "",
         "_De cijfers in deze brief verwijzen met een nummer tussen haakjes "
         "naar deze lijst. Een registratie is vastgelegd door een instantie, "
         "een meting is onze eigen waarneming uit advertenties, en een aanname "
         "is door ons gekozen. Dat laatste is het zwakst en het eerst te "
         "vervangen door eigen cijfers._", ""]

    if not uitgebreid:
        per_soort = {}
        for naam, soort, _wat, _waar, _hoe in BRONNEN:
            per_soort.setdefault(soort, []).append(naam)
        meervoud = {"registratie": "Registraties", "meting": "Metingen",
                    "aanname": "Aannames"}
        for soort in ("registratie", "meting", "aanname"):
            if per_soort.get(soort):
                r.append(f"**{meervoud[soort]}:** "
                         + ", ".join(f"[{NUMMER[n]}] {n}"
                                     for n in sorted(per_soort[soort],
                                                     key=lambda x: NUMMER[x]))
                         + ".")
        r.append("")
        r.append("_De volledige lijst met vindplaatsen staat in de brief van "
                 "zondag._")
        return r

    r.append("| # | Bron | Aard | Wat het levert | Vindplaats | Actualiteit |")
    r.append("|---:|---|---|---|---|---|")
    for naam, soort, wat, waar, hoe in BRONNEN:
        r.append(f"| {NUMMER[naam]} | {naam} | {soort} | {wat} | {waar} | {hoe} |")
    r.append("")

    # Hoeveel waarnemingen liggen er inmiddels?
    tellingen = []
    for pad, omschrijving in (
            ("verkopen.txt", "waarnemingen in het aanbodbestand"),
            ("kamervergunningen.json", "adressen met een vergunning"),
            ("bekendmakingen_archief.json", "adressen in het bekendmakingen-archief"),
            ("woz.txt", "handmatig ingevoerde WOZ-waarden"),
            ("misdrijven_per_buurt.json", "buurten met misdrijfcijfers")):
        if pad.endswith(".json"):
            n = tel(pad)
        else:
            try:
                with open(pad, encoding="utf-8") as f:
                    n = sum(1 for x in f
                            if x.strip() and not x.startswith("#"))
            except Exception:
                n = None
        if n:
            datum = bestandsdatum(pad)
            tellingen.append(f"{n} {omschrijving}"
                             + (f" (bijgewerkt {datum})" if datum else ""))
    if tellingen:
        r.append("_Omvang van de eigen bestanden: " + " . ".join(tellingen) + "._")
        r.append("")

    r.append("### Wettelijk kader")
    r.append("")
    r.append("| Regeling | Waarvoor | Peildatum |")
    r.append("|---|---|---|")
    for naam, waarvoor, peil in KADERS:
        r.append(f"| {naam} | {waarvoor} | {peil} |")
    r.append("")
    r.append("_De brief toetst hierop, maar is geen juridisch of fiscaal advies. "
             "Tarieven en grenzen wijzigen; de regelgevingsmonitor meldt het "
             "zodra een van deze regelingen verandert._")
    return r


# ---------------------------------------------------------------------------
# ACHTERGROND VAN DE DAG
#
# Elke dag een ander aspect van het vak, kort uitgelegd. Niet omdat het nieuws
# is, maar omdat de brief anders alleen uit cijfers bestaat. Het rouleert op
# dezelfde manier als de weetjes: bijhouden wat geweest is.
# ---------------------------------------------------------------------------
# Per onderwerp de trefwoorden waarop het aansluit. Zo kiest het script het
# stuk dat past bij het nieuws van die dag, in plaats van een willekeurig stuk.
# Zonder aansluiting valt het terug op de volgorde: dan is er toch iets.
ACHTERGROND_TREFWOORDEN = {
    "Overdrachtsbelasting": ["overdrachtsbelasting", "belastingplan", "aankoop",
                             "prinsjesdag", "miljoenennota", "fiscaal", "8%"],
    "Rentedekking": ["rente", "hypotheek", "financiering", "bank", "lenen",
                     "ecb", "kapitaalmarkt"],
    "Aflossing is geen kostenpost": ["rendement", "cashflow", "aflossing",
                                     "financiering"],
    "Netto aanvangsrendement": ["rendement", "yield", "aanvangsrendement",
                                "taxatie", "waardering"],
    "Opkoopbescherming": ["opkoopbescherming", "zelfbewoningsplicht",
                          "verhuurverbod", "huisvestingsverordening"],
    "Het puntenstelsel voor kamers": ["kamerverhuur", "studenten",
                                      "onzelfstandig", "puntenstelsel",
                                      "verkameren"],
    "Het puntenstelsel voor woningen": ["puntenstelsel", "betaalbare huur",
                                        "middenhuur", "huurprijs",
                                        "huurregulering", "wws"],
    "Servicekosten": ["servicekosten", "energie", "gas", "warmte"],
    "Leefbaarheidstoets": ["omzetting", "vergunning", "leefbaarheid",
                           "verkameren", "overlast"],
    "Splitsen in Nijmegen": ["splitsen", "splitsing", "woningvorming",
                             "appartement", "transformatie"],
    "Btw op verbouwing": ["btw", "verbouwing", "renovatie", "verduurzaming",
                          "isolatie", "subsidie"],
    "Vennootschapsbelasting": ["box 3", "vermogen", "vennootschapsbelasting",
                               "belasting", "uitponden", "fiscaal"],
    "Beschermd stadsgezicht": ["monument", "erfgoed", "stadsgezicht", "gevel",
                               "kozijn", "welstand"],
    "Waarom oppervlakte zo vaak misgaat": ["bag", "oppervlakte", "kadaster",
                                           "woningwaardering"],
    "Wet goed verhuurderschap": ["goed verhuurderschap", "verhuurder",
                                 "huurcontract", "waarborgsom", "toezicht",
                                 "handhaving", "servicekosten"],
    "Verkameren en het risico daarvan": ["kamerverhuur", "verkameren",
                                         "omzetting", "studenten", "onzelfstandig"],
    "Veiligheid en verhuurbaarheid": ["inbraak", "vernieling", "overlast",
                                      "criminaliteit", "politie", "veiligheid",
                                      "drugs"],
}

# Per achtergrondstuk de bron waarop het rust. Nagelopen op 22 september 2026.
# Een stuk zonder externe bron beschrijft de rekenmethode van deze brief.
ACHTERGROND_BRONNEN = {
    "Overdrachtsbelasting": "Belastingdienst, tarieven overdrachtsbelasting 2026",
    "Rentedekking": "rekenmethode van deze brief; de eis van 1,25 is een eigen aanname",
    "Aflossing is geen kostenpost": "rekenmethode van deze brief",
    "Netto aanvangsrendement": "rekenmethode van deze brief",
    "Opkoopbescherming": "Huisvestingsverordening gemeente Nijmegen 2024, artikel 19",
    "Het puntenstelsel voor kamers": "Volkshuisvesting Nederland, Wet betaalbare huur",
    "Het puntenstelsel voor woningen": "Volkshuisvesting Nederland, Wet betaalbare huur",
    "Servicekosten": "Burgerlijk Wetboek boek 7, artikel 259 en 261; Wet goed verhuurderschap",
    "Leefbaarheidstoets": ("Huisvestingsverordening Nijmegen 2024, artikel 15; "
                           "Beleidsregels omzetting en onttrekking Nijmegen 2021; "
                           "officiele bekendmakingen september 2026"),
    "Splitsen in Nijmegen": ("Huisvestingsverordening Nijmegen 2024, artikel 13; "
                             "Wet WOZ, artikel 16"),
    "Btw op verbouwing": "Belastingplan 2025, herziening investeringsdiensten per 2026",
    "Vennootschapsbelasting": "Belastingdienst, tarieven vennootschapsbelasting 2026",
    "Beschermd stadsgezicht": ("Rijksdienst voor het Cultureel Erfgoed, aanwijzing "
                               "De 19de-eeuwse Stadsuitleg Nijmegen, 11 december 2013"),
    "Wet goed verhuurderschap": "Rijksoverheid, Wet goed verhuurderschap",
    "Verkameren en het risico daarvan": ("Huisvestingsverordening Nijmegen 2024, "
                                         "artikel 12, 13, 15 en bijlage 5"),
    "Veiligheid en verhuurbaarheid": ("Politie en CBS, geregistreerde misdrijven "
                                      "per wijk en buurt"),
    "Waarom oppervlakte zo vaak misgaat": "Basisregistratie Adressen en Gebouwen",
}

ACHTERGROND = [
    ("Overdrachtsbelasting",
     "Sinds 1 januari 2026 is de overdrachtsbelasting voor een woning die niet "
     "je hoofdverblijf wordt 8%, was 10,4%. Voor bedrijfspanden en kantoren "
     "blijft het 10,4%. Koopt iemand een woning binnen zes maanden nadat de "
     "vorige eigenaar hem kocht, dan mag die koper de overdrachtsbelasting die "
     "de verkoper betaalde in mindering brengen; een aanvullende bepaling "
     "voorkomt dat het tariefverschil daarbij te veel voordeel geeft."),
    ("Rentedekking",
     "Naast de financieringsgraad kijken banken bij verhuurd vastgoed naar de "
     "rentedekking: hoe vaak de nettohuur de rentelast dekt. De eis verschilt "
     "per bank. Deze brief rekent met 1,25 keer, en dat is een eigen aanname, "
     "geen norm. Knelt die eis eerder dan de financieringsgraad, dan kun je "
     "minder lenen en wordt je eigen inleg hoger."),
    ("Aflossing is geen kostenpost",
     "Aflossing verlaat wel je rekening maar verdwijnt niet uit je vermogen: "
     "het verschuift van geld naar pand. Deze brief rekent daarom het "
     "operationeel resultaat als nettohuur min rente, en zet de aflossing daar "
     "apart naast als vermogensopbouw."),
    ("Netto aanvangsrendement",
     "Het bruto aanvangsrendement zet de huur af tegen de koopsom. Het netto "
     "aanvangsrendement rekent met de nettohuur over de totale investering, "
     "dus inclusief overdrachtsbelasting, notaris, makelaar en verbouwing. Hoe "
     "groot het verschil is, hangt af van die kosten en staat per pand in de "
     "doorrekening, niet in een vuistregel."),
    ("Opkoopbescherming",
     "In Nijmegen mag je een woning vier jaar na inschrijving van de akte van "
     "levering niet verhuren zonder verhuurvergunning als de WOZ op die datum "
     "niet hoger was dan €396.000 en de woning toen vrij van huur was, of "
     "korter dan zes maanden verhuurd. De toets gaat over wat je koopt, op het "
     "moment dat je het koopt. Nieuwbouw, en woningen van de gemeente of een "
     "corporatie, vallen erbuiten."),
    ("Het puntenstelsel voor kamers",
     "Voor kamers, dus onzelfstandige woonruimte, geldt een apart puntenstelsel, "
     "het WWSO. Een verhuurder van een kamer moet zich altijd aan de maximale "
     "huurprijs houden, ongeacht het aantal punten of wanneer het contract is "
     "gesloten. Sinds de Wet betaalbare huur telt ook de WOZ-waarde mee in het "
     "puntenstelsel voor kamers."),
    ("Het puntenstelsel voor woningen",
     "Voor zelfstandige woningen bepaalt het woningwaarderingsstelsel de "
     "maximale huur. Tot en met 143 punten is het sociale huur, van 144 tot en "
     "met 186 punten middenhuur, en vanaf 187 punten vrije sector zonder "
     "maximale huurprijs. De regulering van de middenhuur geldt voor contracten "
     "vanaf 1 juli 2024. Sinds 1 januari 2025 moet de verhuurder het "
     "puntenaantal aan de huurder laten zien, en kan de gemeente een boete geven "
     "bij een te hoge huur."),
    ("Servicekosten",
     "Een verhuurder mag alleen servicekosten rekenen die het Burgerlijk "
     "Wetboek toestaat, en moet jaarlijks een volledige kostenspecificatie "
     "geven. Het puntenstelsel begrenst de kale huur, niet de servicekosten. "
     "Worden kosten via de servicekosten doorbelast, dan horen ze niet ook "
     "nog eens bij de exploitatiekosten; dan tel je ze dubbel."),
    ("Leefbaarheidstoets",
     "De leefbaarheidstoets staat in artikel 15 van de Huisvestingsverordening "
     "en wordt uitgewerkt in beleidsregels uit 2021, waarin een ambtelijke "
     "adviesgroep de leefbaarheid rond het pand beoordeelt. Volgens een "
     "besluit dat onze bekendmakingenmonitor in september 2026 vond, trekt de "
     "gemeente die beleidsregels in zodra de gewijzigde verordening ingaat. "
     "Tot dan geldt de toets nog. De andere weigeringsgronden van artikel 15 "
     "blijven: WOZ-ondergrens, geluid, fietsenstalling, Bouwbesluit en niet "
     "meer dan twee kamergewijs bewoonde woningen naast, onder of boven elkaar."),
    ("Splitsen in Nijmegen",
     "Splitsen betekent drie verschillende dingen. Juridisch of kadastraal "
     "splitsen in appartementsrechten gebeurt bij de notaris en wordt in het "
     "Kadaster ingeschreven; de Nijmeegse verordening kent daar geen vergunning "
     "voor. Fysiek splitsen, van een woning meerdere zelfstandige woningen "
     "maken, vraagt geen huisvestingsvergunning maar wel een omgevingsvergunning. "
     "Verkameren is iets anders: omzetten naar onzelfstandige woonruimte, met "
     "een eigen vergunningplicht. Voor de WOZ telt de fysieke situatie: "
     "zelfstandige woningen zijn aparte WOZ-objecten, ook zonder "
     "appartementsrechten, terwijl een verkamerd pand een WOZ houdt omdat "
     "kamers geen eigen keuken, douche en toilet hebben."),
    ("Btw op verbouwing",
     "Woningverhuur is vrijgesteld van btw, dus de btw op een verbouwing trek je "
     "daarbij niet af. Sinds 1 januari 2026 geldt een herzieningstermijn voor "
     "diensten aan onroerende zaken vanaf €30.000 exclusief btw per dienst: het "
     "jaar van ingebruikname en de vier jaren daarna. Dat raakt vooral wie de "
     "btw wel aftrok, bijvoorbeeld bij tijdelijk btw-belaste verhuur, en het "
     "pand daarna vrijgesteld gaat verhuren."),
    ("Vennootschapsbelasting",
     "Een BV betaalt in 2026 19% vennootschapsbelasting over de winst tot en met "
     "€200.000 en 25,8% over het meerdere; die tarieven zijn sinds 2023 gelijk. "
     "Wat de aandeelhouder daarna als dividend ontvangt, wordt in box 2 belast. "
     "Welke structuur past, hangt af van de situatie en is een vraag voor de "
     "fiscalist."),
    ("Beschermd stadsgezicht",
     "De Benedenstad is van rijkswege beschermd stadsgezicht, en in december "
     "2013 werd ook De 19de-eeuwse Stadsuitleg aangewezen, de eerste grote "
     "uitbreiding van de stad na 1874. Het gevolg van zo'n aanwijzing is dat de "
     "gemeente de bescherming vastlegt in het plan voor dat gebied. Of een "
     "straat binnen de begrenzing valt en wat dat betekent voor gevel, "
     "kozijnen of zonnepanelen, staat in het omgevingsplan en verschilt per "
     "adres."),
    ("Wet goed verhuurderschap",
     "Sinds 1 juli 2023 gelden landelijke regels voor elke verhuurder. Een "
     "schriftelijk huurcontract is verplicht. De borg is maximaal twee maanden "
     "kale huur en moet binnen 14 dagen na het einde van de huur terug, of "
     "binnen 30 dagen als er wordt verrekend; verrekenen mag alleen met "
     "achterstallige huur, servicekosten, schade en een energieprestatie"
     "vergoeding. De gemeente handhaaft en kan een boete opleggen."),
    ("Verkameren en het risico daarvan",
     "Bij een WOZ tot en met €396.000 is voor verkameren een omzettingsvergunning "
     "nodig, en tot en met €278.000 wordt die altijd geweigerd. Artikel 15 "
     "weigert ook als er door de omzetting meer dan twee kamergewijs bewoonde "
     "woningen direct naast, onder of boven elkaar komen; twee mag dus wel. "
     "Geluidsisolatie, een fietsenstalling op eigen terrein, het Bouwbesluit en "
     "brandveilig gebruik worden getoetst. De boete voor omzetten zonder "
     "vergunning is €5.000, en €10.000 bij bedrijfsmatige exploitatie."),
    ("Veiligheid en verhuurbaarheid",
     "De politie telt misdrijven per buurt op de plaats waar ze zijn gepleegd, "
     "inclusief pogingen; wat niet aan een buurt is toe te kennen, telt niet "
     "mee. Deze brief deelt die aantallen door het aantal bewoners. Bij delicten "
     "die op straat gebeuren, zoals fietsendiefstal en vernieling, telt dan "
     "mee wie er in de buurt komt, niet alleen wie er woont. Woninginbraak "
     "gebeurt bij iemand thuis en zegt daarom het meest over de bewoners."),
    ("Waarom oppervlakte zo vaak misgaat",
     "De BAG registreert de gebruiksoppervlakte per verblijfsobject, en elk "
     "verblijfsobject heeft een eigen adres. Is een pand feitelijk opgedeeld "
     "maar staat het als een verblijfsobject geregistreerd, dan geeft de BAG de "
     "oppervlakte van het geheel. Daarom gebruikt deze brief de oppervlakte uit "
     "de advertentie als die er is, en anders de BAG."),
]


def achtergrond_van_de_dag(nieuwstekst=""):
    """
    Het achtergrondstuk dat aansluit bij het nieuws van vandaag.

    Een los weetje naast het nieuws leest als een invuloefening. Sluit het aan
    bij wat er speelt, dan wordt het een verdieping: het artikel meldt dat de
    overdrachtsbelasting verandert, het stuk eronder legt uit hoe die precies
    werkt bij doorverkoop binnen zes maanden.

    Zonder aansluiting valt het terug op wat nog niet geweest is, zodat er toch
    iedere dag iets staat.
    """
    pad = "achtergrond_gezien.json"
    try:
        with open(pad, encoding="utf-8") as f:
            gezien = json.load(f)
    except Exception:
        gezien = []

    nieuw = [x for x in ACHTERGROND if x[0] not in gezien]
    if not nieuw:
        gezien, nieuw = [], ACHTERGROND

    # Welk onderwerp sluit het beste aan bij het nieuws van vandaag?
    keuze = None
    if nieuwstekst:
        laag = nieuwstekst.lower()
        beste_score = 0
        for titel_k, tekst_k in nieuw:
            woorden = ACHTERGROND_TREFWOORDEN.get(titel_k, [])
            score = sum(1 for w in woorden if w in laag)
            if score > beste_score:
                beste_score, keuze = score, (titel_k, tekst_k)
        if keuze:
            print(f"Achtergrond gekozen op aansluiting bij het nieuws: "
                  f"{keuze[0]}", file=sys.stderr)

    titel, tekst = keuze or nieuw[0]
    gezien.append(titel)
    try:
        with open(pad, "w", encoding="utf-8") as f:
            json.dump(gezien[-len(ACHTERGROND):], f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    bron = ACHTERGROND_BRONNEN.get(titel, "")
    staart = f" _(Bron: {bron}.)_" if bron else ""
    return ["", f"**Over {titel.lower()}.** {tekst}{staart}", ""]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kort", action="store_true")
    ap.add_argument("--uit", default="")
    ap.add_argument("--nieuws", default="",
                    help="bestand met het nieuws van vandaag, voor de aansluiting")
    ap.add_argument("--achtergrond", action="store_true",
                    help="alleen het achtergrondstukje van vandaag")
    args = ap.parse_args()
    if args.achtergrond:
        # Het nieuws van vandaag erbij, zodat het stuk erop aansluit
        nieuws = ""
        for pad in (args.nieuws, f"digests/{dt.date.today().isoformat()}-publicaties.md",
                    f"digests/{dt.date.today().isoformat()}-bekendmakingen.md"):
            if pad and os.path.exists(pad):
                try:
                    with open(pad, encoding="utf-8") as f:
                        nieuws += f.read()
                except Exception:
                    pass
        regels = achtergrond_van_de_dag(nieuws)
    else:
        regels = render(uitgebreid=not args.kort)
    tekst = "\n".join(regels) + "\n"
    if args.uit:
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(tekst)
    print(tekst)
