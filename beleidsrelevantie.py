#!/usr/bin/env python3
"""
Welk gemeentelijk beleid raakt onze portefeuille en welk beleid niet.

WAAROM DIT BESTAAT. De beleidsfilter in bekendmakingen_nijmegen.py vist op
woorden als "verordening", "beleidsregel" en "nadere regels". Dat is een breed
net, en breed is goed: een stuk missen is erger dan een stuk te veel zien. Maar
alles wat erin zwemt kwam ook in de brief, en daardoor stond de intrekking van
de Beleidsregels omzetting en onttrekking van zelfstandige woonruimte, het stuk
dat precies over verkamering en splitsen gaat, als gelijkwaardig blok tussen de
Beleidsregel veilige jaarwisseling en de Beleidsregels handhaving Wet
kinderopvang. Het signaal verdronk in de ruis.

HOE DIT WERKT. Twee lijsten. Een stuk raakt ons als er een vastgoedwoord in de
titel of de samenvatting staat, tenzij er een woord in staat dat het onderwerp
buiten onze portefeuille plaatst. De weglijst gaat voor, want "Subsidieregeling
Duurzame en Frisse scholen" bevat zowel "duurzame" als niets van ons.

WAT ER NIET GEBEURT. Een stuk dat niet relevant is, verdwijnt niet. Het gaat
naar de staartregel met alleen de titel. Dat is met opzet: in dit project is
de gevaarlijke fout steeds de afwezigheid geweest en niet de melding. Zou dit
een filter zijn dat stukken weggooit, dan zou een verkeerd woord in de lijst
iets belangrijks onzichtbaar maken zonder dat iemand dat merkt.

DE PROEF ONDERAAN IS HET PUNT. Daar staan de achttien stukken die sinds
september werkelijk in de brief hebben gestaan, met de indeling die ik erbij
vind horen. Wie een woord aan een lijst toevoegt en daarmee een van die
achttien omklapt, ziet dat meteen. Zonder die proef is elke aanpassing van de
lijsten een gok.
"""

import re
import sys

# Onderwerpen die onze portefeuille of de Nijmeegse woningmarkt raken.
RAAKT_ONS = (
    # wonen en verhuren
    "woonruimte", "woning", "wonen", "huurder", "verhuur", "verhuurder",
    "huurprijs", "huisvesting", "woonvisie", "woonagenda", "kamerverhuur",
    "onzelfstandige", "zelfstandige woonruimte", "studentenhuisvesting",
    "goed verhuurderschap", "leegstand", "opkoopbescherming",
    "zelfbewoning", "woonruimteverdeling", "huisvestingsvergunning",
    # ingrepen in een pand
    "omzetting", "onttrekking", "splitsing", "splitsen", "verkamering",
    "transformatie", "functiewijziging", "bouwlaag", "plint", "begane grond",
    "woningbouw", "appartement", "pand",
    # ruimtelijk en beschermd
    "omgevingsplan", "bestemmingsplan", "bopa", "voorbereidingsbesluit",
    "stadsbeeld", "welstand", "monument", "beschermd", "erfpacht",
    # verduurzaming en installaties
    "energielabel", "isolatie", "isoleren", "warmtepomp", "blokverwarming",
    "warmtenet", "zonnepanelen", "transportcapaciteit", "netcongestie",
    "vve", "vereniging van eigenaren",
)

# Onderwerpen die ergens anders over gaan, ook als er een vastgoedwoord in de
# titel staat. Deze lijst gaat voor op de lijst hierboven.
NIET_ONS = (
    "kinderopvang", "jaarwisseling", "vuurwerk", "school", "scholen",
    "woonwagen", "standplaats", "ggd", "publieke gezondheid", "mandaatbesluit",
    "evenement", "kermis", "markt en standplaats", "terras",
    "parkeergarage", "parkeerterrein", "parkeertarief", "tarieven parkeer",
    "hondenbelasting", "toeristenbelasting", "reclamebelasting",
    "jeugdhulp", "participatiewet", "bijstand", "schuldhulp", "inburgering",
    "alcohol", "coffeeshop", "prostitutie", "speelautomaten",
)


# De reden die betekent "geen van beide lijsten plaatst dit stuk". Dat is iets
# anders dan "gaat niet over ons": het is nog niet beoordeeld. De aanroeper
# haalt voor zo'n stuk de publicatietekst op en vraagt het daarna opnieuw.
# Als constante en niet als losse tekst op twee plekken, want een typefout in
# die vergelijking zou de tweede trap stil uitschakelen.
NIET_GEPLAATST = "geen vastgoedonderwerp gevonden"


def _treffer(hooi, woorden, sluitend=False):
    """
    Het eerste woord uit de lijst dat in de tekst staat.

    WAAROM TWEE VARIANTEN. Aan de voorkant staat altijd een woordgrens. Aan de
    achterkant hangt het ervan af welke kant een fout op valt:

    - Bij de raaktlijst laten we de staart open, zodat "woning" ook "woningen"
      en "woningbouw" vindt. Een treffer te veel kost daar niets: het stuk komt
      dan voluit in de brief terwijl een regel had gekund.
    - Bij de weglijst moet de grens sluiten. Zonder sluitende grens valt
      "school" op "Schoolstraat", en dat is een echte Nijmeegse straat in
      Bottendaal. Een bekendmaking over kamerverhuur op de Schoolstraat zou dan
      tot een staartregel krimpen omdat het woord "school" erin staat. Daar
      kost een treffer te veel dus wel iets: dan verdwijnt er iets.

    Dit is de kant die een losse beoordelaar vond door alle 366 straatnamen en
    alle 470 bewaarde titels langs de lijsten te halen: één straat en zeven
    titels vielen verkeerd, allemaal op de weglijst.
    """
    for w in woorden:
        staart = r"(?:en|s|e)?\b" if sluitend else ""
        if re.search(r"\b" + re.escape(w) + staart, hooi):
            return w
    return ""


def relevantie(titel, samenvatting="", alleen_promoveren=False):
    """
    Raakt dit stuk ons? Geeft (True/False, reden) terug.

    De reden is het woord waarop de beslissing rust, zodat in het
    gezondheidsrapport en in de staartregel te zien is waarom een stuk niet
    voluit in de brief staat.

    alleen_promoveren=True slaat de weglijst over. Dat is bedoeld voor de
    tweede trap: een stuk waarvan de titel niets zei en waarvan we daarom de
    publicatietekst hebben opgehaald. Zonder die schakelaar kan één woord in
    een samengevatte tekst een stuk degraderen dat op de titel al was
    goedgekeurd, en dan krimpt juist het stuk waar het om gaat tot een grijze
    regel. Een losse beoordelaar liet zien dat dat met echte titels gebeurt:
    een samenvatting van de plintregel die "horeca met een terras" noemt valt
    op het woord "terras" en de hele beleidsregel verdwijnt uit de brief.
    """
    hooi = f"{titel} {samenvatting}".lower()
    if not alleen_promoveren:
        weg = _treffer(hooi, NIET_ONS, sluitend=True)
        if weg:
            return False, f"gaat over {weg}"
    raak = _treffer(hooi, RAAKT_ONS)
    if raak:
        return True, raak
    return False, NIET_GEPLAATST


def splits(items, alleen_promoveren=False):
    """
    Deelt beleidsitems in twee lijsten: wat ons raakt en de rest.

    Werkt op dezelfde dicts als bekendmakingen_nijmegen.py gebruikt en zet de
    reden op het item, zodat de staartregel en de toets hem kunnen lezen.

    alleen_promoveren geeft de schakelaar door aan relevantie(). Gebruik hem
    voor de tweede trap, zodat een eerder goedgekeurd stuk niet alsnog kan
    afvallen op een woord uit zijn eigen samenvatting.
    """
    raakt, overig = [], []
    for it in items:
        ja, reden = relevantie(it.get("titel", ""), it.get("samenvatting", ""),
                               alleen_promoveren=alleen_promoveren)
        it["relevant"] = ja
        it["relevantie_reden"] = reden
        (raakt if ja else overig).append(it)
    return raakt, overig


def staartregel(overig):
    """
    Eén regel onder het beleidsblok met de stukken die ons niet raken.

    De reden staat erbij, en dat is het punt. Valt een stuk weg op een woord
    dat in de weglijst niet thuishoort, dan is dat in de brief zelf te zien
    ("gaat over school") in plaats van pas als iemand een stuk mist.
    """
    if not overig:
        return ""
    namen = []
    for it in overig:
        reden = (it.get("relevantie_reden") or "").strip()
        titel = it.get("titel", "")
        namen.append(f"{titel} ({reden})" if reden else titel)
    woord = "stuk" if len(overig) == 1 else "stukken"
    return (f'<div style="font-size:12px;color:#7a8a92;margin:0 0 12px 0">'
            f'Ook gepubliceerd, buiten ons onderwerp: {len(overig)} {woord}. '
            f'{", ".join(namen)}</div>')


# De achttien stukken die sinds september werkelijk in de brief stonden, met de
# indeling die erbij hoort. Dit is geen verzonnen voorbeeldmateriaal: deze
# titels komen uit de bewaarde digests.
PROEF = (
    (True,  "Beleidsregels Woonruimte op de eerste bouwlaag toevoegen binnenstad"),
    (True,  "Intrekking Beleidsregels omzetting en onttrekking van zelfstandige "
            "woonruimte Nijmegen 2021"),
    (True,  "Aanwijzing toezichthouders afdeling Stadsrealisatie, Team "
            "Omgevingstoezicht en Advies (SR60), Wet goed verhuurderschap en "
            "Omgevingswet (augustus 2026)"),
    (True,  "Beleidsregels aanvraag prioriteit transportcapaciteit "
            "woningbouwprojecten gemeente Nijmegen 2026"),
    (True,  "Ontwerp aanwijzingsbesluit Stadsbeeld Wederopbouwcentrum - "
            "kennisgeving ter inzage legging digitaal"),
    (True,  "Regeling noodfonds blokverwarming gemeente Nijmegen"),
    (True,  "Subsidieregeling Isoleren Woningen - Vereniging van Eigenaren Nijmegen"),
    (True,  "Subsidieregeling Isoleren Woningen – Grondgebonden Koopwoningen Nijmegen"),
    (True,  "Subsidieregeling Isoleren Woningen – HR++(+) glas voor individuele "
            "VvE-leden Nijmegen"),
    (True,  "Subsidieregeling doe-het-zelf isolatie maatregelen woningen Nijmegen"),
    (True,  "Subsidieregeling Tegemoetkoming stijging VvE bijdrage Nijmegen"),
    (False, "Beleidsregel veilige jaarwisseling Nijmegen"),
    (False, "Beleidsregels handhaving Wet kinderopvang Gemeente Nijmegen 2026"),
    (False, "Aanwijzingsbesluit Directeur Publieke gezondheid van de GGD "
            "Gelderland-Zuid"),
    (False, "Mandaatbesluit gemeente Nijmegen 2019"),
    (False, "Subsidieregeling Duurzame en Frisse scholen Nijmegen 2026"),
    (False, "Intrekking Beleidsregels voor toewijzing van standplaatsen voor "
            "woonwagens Nijmegen 2022"),
    (False, "Tarieven parkeergarages en afgesloten parkeerterreinen 2025"),
)


# De gevallen die een losse beoordelaar vond door alle straatnamen en alle
# bewaarde titels langs de lijsten te halen. Elk hiervan ging mis in de eerste
# opzet. Ze staan hier zodat een volgende aanpassing van de lijsten of van de
# woordgrens ze niet opnieuw kan breken.
VALKUILEN = (
    # Schoolstraat is een echte straat in Bottendaal. Zonder sluitende grens
    # aan de weglijst viel elke bekendmaking op die straat op "school".
    (True, "Omzettingsvergunning Schoolstraat 12 Nijmegen", ""),
    (True, "Beleidsregels kamerverhuur Schoolstraat en omgeving", ""),
    # Een samenvatting die een weglijstwoord noemt mag een stuk dat op de
    # titel al is goedgekeurd niet degraderen. Dit is het geval dat de hele
    # plintregel uit de brief liet verdwijnen.
    (True, "Beleidsregels Woonruimte op de eerste bouwlaag toevoegen binnenstad",
     "De regel geldt voor winkels en voor horeca met een terras aan de straat."),
    (True, "Huisvestingsverordening gemeente Nijmegen 2026",
     "De verordening regelt ook de toewijzing bij scholen in de wijk."),
    # En omgekeerd: zonder een vastgoedwoord blijft het gewoon buiten beeld.
    (False, "Verordening afvalstoffenheffing 2026", ""),
)


def proef():
    """Loopt de bewaarde titels en de bekende valkuilen langs."""
    fout = 0
    for verwacht, titel in PROEF:
        uit, reden = relevantie(titel)
        if uit != verwacht:
            fout += 1
            hoort = "raakt ons" if verwacht else "overig"
            print(f"AFWIJKING: '{titel[:60]}' kwam uit als "
                  f"{'raakt ons' if uit else 'overig'} ({reden}), "
                  f"hoort {hoort} te zijn")
    raakt = sum(1 for v, _ in PROEF if v)
    print(f"{len(PROEF)} bewaarde titels: {raakt} raken ons, "
          f"{len(PROEF) - raakt} niet, {fout} afwijkend")

    # De valkuilen lopen langs de tweede trap, want zo wordt een stuk met een
    # samenvatting in de praktijk beoordeeld.
    vk = 0
    for verwacht, titel, samenvatting in VALKUILEN:
        uit, reden = relevantie(titel, samenvatting, alleen_promoveren=True)
        if uit != verwacht:
            vk += 1
            print(f"AFWIJKING (valkuil): '{titel[:50]}' kwam uit als "
                  f"{'raakt ons' if uit else 'overig'} ({reden})")
    # De weglijst moet in de eerste trap nog wel werken.
    for titel, hoort_weg in (("Beleidsregel veilige jaarwisseling Nijmegen", True),
                             ("Omzettingsvergunning Schoolstraat 12", False)):
        uit, reden = relevantie(titel)
        if uit is hoort_weg:
            vk += 1
            print(f"AFWIJKING (weglijst): '{titel[:50]}' gaf {uit} ({reden})")
    print(f"{len(VALKUILEN) + 2} bekende valkuilen: {vk} afwijkend")
    return fout + vk


if __name__ == "__main__":
    sys.exit(1 if proef() else 0)
