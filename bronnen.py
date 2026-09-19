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

ACHTERGROND = [
    ("Overdrachtsbelasting",
     "Sinds 1 januari 2026 betaal je 8% overdrachtsbelasting voor een woning "
     "die niet je hoofdverblijf is, verlaagd van 10,4%. Verkoop je binnen zes "
     "maanden door, dan betaalt je koper op grond van artikel 13 van de Wet op "
     "belastingen van rechtsverkeer alleen belasting over de meerwaarde. Dat "
     "voordeel ligt bij de koper, maar je kunt in de akte afspreken dat hij "
     "jouw betaalde belasting vergoedt."),
    ("Rentedekking",
     "Banken kijken bij verhuurd vastgoed niet alleen naar de "
     "financieringsgraad maar ook naar de rentedekking: de nettohuur moet "
     "minstens 1,25 keer de rentelast zijn. Bij de huidige rente knelt die eis "
     "meestal eerder dan de financieringsgraad, waardoor je minder kunt lenen "
     "dan 67% van de koopsom en je eigen inleg hoger uitvalt."),
    ("Aflossing is geen kostenpost",
     "Aflossing verlaat wel je rekening maar verdwijnt niet uit je vermogen: "
     "het verschuift van geld naar pand. Wie aflossing van de huur aftrekt en "
     "dat rendement noemt, onderschat elke belegging. Het operationeel "
     "resultaat is de nettohuur min de rente; de aflossing komt daarna apart."),
    ("Netto aanvangsrendement",
     "Het bruto aanvangsrendement rekent de huur af tegen de koopsom, maar je "
     "betaalt meer dan de koopsom: overdrachtsbelasting, notaris, makelaar en "
     "verbouwing. Het netto aanvangsrendement rekent over die hele investering "
     "en valt daardoor een tot twee procentpunt lager uit. Dat is het cijfer "
     "waarop taxateurs vergelijken."),
    ("Opkoopbescherming",
     "In Nijmegen mag je een gekochte woning met een WOZ tot en met €396.000 "
     "vier jaar lang niet verhuren zonder vergunning. Die bescherming geldt "
     "niet als het pand op de leveringsdatum al langer dan zes maanden "
     "verhuurd was. Dat maakt een pand in verhuurde staat wezenlijk anders dan "
     "hetzelfde pand leeg."),
    ("Het puntenstelsel voor kamers",
     "Onzelfstandige woonruimte valt altijd in de sociale sector, hoe duur het "
     "pand ook is. Het WWSO bepaalt de maximale kale huur per kamer, en boven "
     "de zestig punten vlakt de tabel af. Kleinere kamers brengen daardoor per "
     "vierkante meter meer op, tot de bouwkundige ondergrens."),
    ("Het puntenstelsel voor woningen",
     "Bij zelfstandige woningen ligt de grens naar de vrije sector op 187 "
     "punten. Daaronder is de huur wettelijk gemaximeerd. Een gesplitste "
     "eenheid van vijftig vierkante meter haalt die grens zelden, waardoor de "
     "marktprijs per meter niet gevraagd mag worden."),
    ("Servicekosten",
     "Gas, water, licht, schoonmaak van gemeenschappelijke ruimten en internet "
     "worden via de servicekosten doorbelast en drukken dus niet op je "
     "rendement. Het puntenstelsel begrenst alleen de kale huur. Wie die "
     "posten als exploitatiekosten meerekent, onderschat kamerverhuur."),
    ("Leefbaarheidstoets",
     "De ambtelijke toets bij een omzettingsvergunning vervalt: de gemeente "
     "trok in september 2026 de beleidsregels uit 2021 in, omdat goed "
     "verhuurderschap landelijk is geborgd. Wat blijft zijn de harde gronden "
     "van artikel 15: geluid, fietsenstalling, Bouwbesluit en maximaal twee "
     "kamergewijs bewoonde woningen naast elkaar."),
    ("Splitsen in Nijmegen",
     "Nijmegen kent geen splitsingsvergunning; die begrippen komen in de "
     "verordening niet voor. Voor de verbouwing is wel een omgevingsvergunning "
     "nodig, maar bij bestaande bouw geldt het van rechtens verkregen niveau "
     "in plaats van de nieuwbouwnorm. Dat scheelt aanzienlijk bij vooroorlogse "
     "panden."),
    ("Btw op verbouwing",
     "Woningverhuur is vrijgesteld van btw, dus de btw op de verbouwing kun je "
     "niet terugvorderen. Sinds 1 januari 2026 geldt bovendien een "
     "herzieningsregeling voor kostbare diensten aan onroerend goed, met een "
     "termijn van vijf jaar en een drempel van €30.000 exclusief btw."),
    ("Vennootschapsbelasting",
     "In een BV betaal je 19% over de eerste €200.000 winst en 25,8% "
     "daarboven. Bij actief handelen, dus kopen, verbouwen en snel "
     "doorverkopen, is de BV bijna altijd de juiste structuur: prive loopt zo'n "
     "strategie het risico dat de winst in box 1 valt als resultaat uit overige "
     "werkzaamheden, tegen een tarief tot bijna vijftig procent."),
    ("Beschermd stadsgezicht",
     "De Benedenstad en de negentiende-eeuwse schil zijn rijksbeschermd "
     "stadsgezicht. In zo'n gebied is voor wijzigingen aan het uiterlijk een "
     "omgevingsvergunning nodig, ook bij panden die zelf geen monument zijn. "
     "Dat raakt precies de maatregelen waarmee je het energielabel verbetert: "
     "gevelisolatie, kozijnen en zonnepanelen aan de voorzijde."),
    ("Wet goed verhuurderschap",
     "Sinds 2023 gelden landelijke verplichtingen voor elke verhuurder: een "
     "schriftelijke huurovereenkomst, een gespecificeerde servicekostenafrekening, "
     "de waarborgsom van hooguit twee maanden huur en binnen veertien dagen na "
     "einde huur terug, en informatie aan de huurder over zijn rechten. Nijmegen "
     "heeft toezichthouders aangewezen die woningen mogen betreden om hierop te "
     "controleren, zo nodig met machtiging."),
    ("Verkameren en het risico daarvan",
     "Verkameren verzilvert vierkante meters, maar het is geen route zonder "
     "risico. Je verliest de verkoopbaarheid aan een gezin, de leefbaarheids"
     "toets sneuvelt juist in rustige straten, meer dan twee kamerpanden naast "
     "elkaar mag niet, en bij vijf kamers komt de brandveiligheid erbij. Boete "
     "bij omzetten zonder vergunning: tienduizend euro, bij herhaling vijftien."),
    ("Veiligheid en verhuurbaarheid",
     "De politiecijfers gaan per buurt en per jaar, dus ze zeggen niets over een "
     "straat. Wat ze wel doen is het verschil laten zien: Stadscentrum telt bijna "
     "vijf keer zoveel vernielingen per duizend inwoners als Galgenveld. Dat "
     "raakt je huurderspoule en je exitwaarde, ook nu de leefbaarheidstoets "
     "vervalt."),
    ("Waarom oppervlakte zo vaak misgaat",
     "De BAG kent een oppervlakte per verblijfsobject, niet per huisnummer. "
     "Bij een pand dat is opgedeeld in een boven- en benedenhuis staat soms "
     "het geheel geregistreerd, en bij een geregistreerde splitsing staan er "
     "twee objecten op hetzelfde adres. Daarom telt de oppervlakte uit de "
     "advertentie zwaarder dan die uit de registratie."),
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
    return ["", f"**Over {titel.lower()}.** {tekst}", ""]


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
