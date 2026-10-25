#!/usr/bin/env python3
"""
Welke panden werkelijk zijn opgedeeld, gezien in de BAG.

Een vergunning zegt dat het mág. De BAG zegt dat het gebeurd ís: zodra het
aantal woningen met een eigen adres in een pand omhoog gaat, zijn de nieuwe
eenheden geregistreerd. Dat is het enige harde bewijs van een voltooide
splitsing dat we hebben, en het komt uit een registratie en niet uit een
advertentie.

Drie dingen vallen daaruit af te leiden:

1. De doorlooptijd van besluit tot registratie. Hoe lang duurt het werkelijk
   voordat een vergund pand ook een opgedeeld pand is? Dat is een getal dat
   nergens te vinden is en dat elke ontwikkelcase nodig heeft.
2. Splitsingen zonder bekende vergunning. Dan hebben we de bekendmaking gemist,
   of het is zonder vergunning gegaan. Allebei interessant.
3. Vergunningen die niet tot een splitsing hebben geleid. Verleend, en daarna
   gebeurt er niets; dat zegt iets over hoe haalbaar zo'n plan in de praktijk is.

Beperking die erbij hoort: het aantal woningen wordt alleen bij een volledige
ronde opnieuw opgehaald, dus wekelijks. Een splitsing is daarmee hooguit een
week na registratie zichtbaar, en een pand dat voor eind september is opgedeeld
zien we helemaal niet, want toen begonnen we pas met meten.
"""
import argparse
import datetime as dt
import json
import re
import sys

UIT_PAD = "splitsingen.json"
# Woorden die op woningvorming wijzen. "Omzetten" staat er bewust niet bij:
# dat is kamerverhuur en dat is iets anders.
SPLITS_WOORDEN = ("splits", "woningvorming", "zelfstandige woningen",
                  # "WOONRUIMTE" EN NIET ALLEEN "WONING". De gemeente schrijft
                  # beide: "splitsen tot 2 zelfstandige woningen" en
                  # "verbouwen en uitbreiden tot 6 zelfstandige woonruimtes".
                  # Alleen de eerste werd herkend, dus het besluit voor
                  # Hatertseweg 338 van 6 oktober bereikte dit blok niet.
                  # Daardoor stond het verschil tussen vergunning en BAG niet
                  # in het hoofdstuk dat er het voorbehoud bij zet, en pakte de
                  # brief de ruwe getallen zelf op en maakte er haar
                  # hoofdthema van.
                  "zelfstandige woonruimte", "zelfstandige wooneenhe",
                  "appartementen", "appartementsrechten", "opdelen",
                  "verbouwen van een woning naar", "naar twee woningen",
                  "naar drie woningen")


def _is_splitsing(tekst):
    laag = (tekst or "").lower()
    return any(w in laag for w in SPLITS_WOORDEN)


def _aantallen(tekst):
    """Uit 'de BAG telt nu 3 woningen in dit pand, was 1' komt (1, 3).

    De tekst kan sinds 11 oktober een staart hebben ("; daarnaast 1 ander
    object met een eigen adres"), want de woningen worden nu apart van de
    overige adresseerbare objecten geteld. Die staart staat achter het stuk
    waar deze regex op zoekt, dus hij verandert niets aan het zoeken; dit
    commentaar staat er zodat de volgende lezer dat niet hoeft uit te vinden.

    Een tekst zonder "was" wordt met opzet niet gelezen. Die vorm komt uit de
    eerste ronde na 11 oktober, waarin er van vroeger nog geen woningtelling
    op dezelfde grondslag bestond. Daar een groei uit lezen zou een splitsing
    melden die niet is waargenomen.
    """
    m = re.search(r"telt nu (\d+) woningen in dit pand, was (\d+)", tekst or "")
    if not m:
        return None
    return int(m.group(2)), int(m.group(1))


WOORDGETAL = {"een": 1, "één": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5,
              "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10}

# VANAF WELKE DATUM "WONINGEN" IN EEN GEBEURTENISTEKST OOK WONINGEN BETEKENT.
# Tot en met 11 oktober telde pandgeschiedenis.py elk adresseerbaar object in
# een pand en noemde dat een woning, dus ook een garage of berging met een
# eigen adres. Vanaf de eerste ronde met de nieuwe code wordt de woonfunctie
# apart geteld. Oude teksten worden niet herschreven, want dat zou valse
# wijzigingen melden op de 1.777 panden die al gevolgd worden. Dus moet deze
# lezer weten welke grondslag onder een getal zit, en de enige harde grens die
# daarvoor bestaat is de datum waarop de code veranderde.
GRONDSLAG_VANAF = "2026-10-12"

# EN VANAF WELKE DATUM "WONINGEN" ALLEEN WONINGEN IN GEBRUIK ZIJN. Van 12 tot
# en met 17 oktober telde pandgeschiedenis.py ook objecten met status
# "Verblijfsobject gevormd" als woning: geregistreerd, nog niet in gebruik.
# Graafseweg 18 stond daardoor als "van 1 naar 7" in de brief, terwijl er 1
# woning in gebruik was en 6 gevormde objecten, precies de 6 appartementen uit
# de aanvraag. Mark vroeg op 17 oktober of er dan een route buiten de gemeente
# om bestond. Een groei uit een tekst van voor deze datum wordt daarom alleen
# geloofd als het pand nu geen gevormde objecten heeft.
GEVORMD_APART_VANAF = "2026-10-18"


def _eenheid(datum, meervoud=True):
    """Hoe een getal uit een gebeurtenistekst van die datum mag heten."""
    if (datum or "") >= GRONDSLAG_VANAF:
        return "woningen" if meervoud else "woning"
    return ("objecten met een eigen adres" if meervoud
            else "object met een eigen adres")


def _dag(n):
    """'1 dag' en niet '1 dagen'."""
    return f"{n} dag" if n == 1 else f"{n} dagen"

# Hoeveel eenheden de vergunning noemt. Bij een reeks als "van 2 naar 4" is het
# laatste getal de uitkomst, dus pakken we de laatste treffer en niet de eerste.
#
# "WOONRUIMTES" STOND ER NIET BIJ, EN DAT DEKTE EEN FOUT. Het besluit voor
# Hatertseweg 338 noemt "6 zelfstandige woonruimtes"; dit stond er niet in,
# dus het vergunde aantal bleef onbekend en het pand kwam niet in het
# hoofdstuk over verschillen. Dat zag eruit als goed gedrag, maar het was
# toeval: de BAG telde daar 7 objecten, en zodra dit woord erbij kwam was dat
# een verschil van 1 dat er niet is. Het echte verschil zat in de telling, en
# die is apart rechtgezet (zie de vergelijking in zoek()). Beide moeten
# kloppen; hierop vertrouwen om het andere te verbergen is geen ontwerp.
RE_VERGUND = re.compile(
    # \b rond het voorzetsel, want "in" zonder woordgrens zit ook in het eind
    # van een ander woord ("terrein 2 woningen" zou dan matchen).
    r"\b(?:tot|naar|in)\b\s+(\d{1,2}|een|één|twee|drie|vier|vijf|zes|zeven|"
    r"acht|negen|tien)\s+(?:zelfstandige\s+|nieuwe\s+|extra\s+)*"
    r"(?:woningen|woning|wooneenheden|woonruimtes|woonruimten|woonruimte|"
    r"appartementen|appartement|studio's)",
    re.IGNORECASE)


def _vergund_aantal(tekst):
    """
    Hoeveel eenheden de vergunningtekst noemt, of None.

    Dit bestaat om één vraag te kunnen stellen die we tot nu toe niet stelden:
    klopt het aantal dat de BAG na een splitsing telt met het aantal waarvoor
    vergunning is gegeven? Bij de Biezenstraat 110 stond in het besluit "tot 2
    zelfstandige woningen" en telt de BAG er sinds 3 oktober 3, van 168, 203 en
    44 m2. Die 44 is vermoedelijk de garage. De brief van 9 oktober noemde
    beide getallen in één alinea zonder het verschil op te merken.

    Op 17 oktober bleek het verschil er niet te zijn: 203 m2 is de oude woning
    in gebruik, en 168 m2 en Maasstraat 2 van 44 m2 zijn de twee vergunde
    nieuwe, met status gevormd. Zie GEVORMD_APART_VANAF.

    Let op wat dit NIET vaststelt. Een verschil kan betekenen dat er meer is
    gerealiseerd dan mocht, maar ook dat de vergunningtekst iets anders telt
    dan de BAG: een garage die een eigen adres krijgt is in de BAG een woning
    en in de aanvraag een bijgebouw. Het is dus een aanwijzing om na te kijken
    en nooit een conclusie. Die formulering staat ook in de uitvoer.
    """
    treffers = RE_VERGUND.findall(tekst or "")
    if not treffers:
        return None
    ruw = treffers[-1].lower()
    if ruw.isdigit():
        n = int(ruw)
    else:
        n = WOORDGETAL.get(ruw)
    return n if n and 1 <= n <= 30 else None


def _dagen(van, tot):
    try:
        return (dt.date.fromisoformat(tot[:10])
                - dt.date.fromisoformat(van[:10])).days
    except Exception:
        return None


def zoek(geschiedenis):
    """
    Per pand: is het aantal woningen omhooggegaan, en was er een vergunning?

    De vergunning mag van voor de registratie zijn; een besluit dat erna komt
    hoort niet bij deze splitsing en telt dus niet mee.
    """
    gerealiseerd, zonder_vergunning, vergund_niets = [], [], []
    aangekondigd, wacht = [], []
    for pand in geschiedenis.values():
        if not isinstance(pand, dict):
            continue
        gebeurtenissen = sorted(pand.get("gebeurtenissen") or [],
                                key=lambda g: g.get("datum") or "")
        groei = [(g["datum"], _aantallen(g.get("tekst")))
                 for g in gebeurtenissen if g.get("soort") == "bag"]
        groei = [(d, a) for d, a in groei if a and a[1] > a[0]]
        besluiten = [g for g in gebeurtenissen
                     if g.get("soort") in ("bekendmaking", "kamerverhuur")
                     and _is_splitsing(g.get("tekst"))
                     and "besluit" in (g.get("tekst") or "").lower()]
        aanvragen = [g for g in gebeurtenissen
                     if g.get("soort") == "bekendmaking"
                     and _is_splitsing(g.get("tekst"))
                     and "aanvraag" in (g.get("tekst") or "").lower()]

        # GEVORMD EERST. Een pand met objecten die geregistreerd en nog niet
        # in gebruik zijn, is aangekondigd en niet gerealiseerd. Een groei uit
        # een tekst van voor GEVORMD_APART_VANAF telde die objecten mee, dus
        # die zegt hier niets; weten we nog niet of er gevormde objecten zijn,
        # dan wacht het pand een ronde in plaats van te raden.
        gev = pand.get("bag_gevormd")
        oude_groei = bool(groei) and groei[-1][0] < GEVORMD_APART_VANAF
        if oude_groei and gev is None:
            wacht.append(pand.get("adres"))
            continue
        if gev and (oude_groei or besluiten or aanvragen):
            woon_nu = pand.get("bag_woningen")
            rij = {"adres": pand.get("adres"), "gevormd": len(gev),
                   "gevormd_maten": [o for _a, o in gev if o],
                   "in_gebruik": (len(woon_nu) if isinstance(woon_nu, list)
                                  else None),
                   # Wanneer wij het zagen. De BAG geeft hier geen datum van
                   # registratie mee, dus is dit de eerste gebeurtenis die
                   # het liet zien, en anders de laatste bekendmaking.
                   "datum": (groei[-1][0] if groei else
                             max(g["datum"] for g in besluiten + aanvragen))}
            # EEN AANVRAAG NA HET BESLUIT HOORT ER NIET BIJ. 25 oktober 2026,
            # van Goorstraat 87: aanvraag 20 januari (drie woningen), besluit
            # 28 juli (twee), en op 22 oktober een nieuwe aanvraag (twee).
            # Hier stond de laatste aanvraag naast het laatste besluit, en de
            # regel zei alleen "Besluit van 2026-07-28 voor 2". De
            # feitencontrole las dat als het besluit op de aanvraag van 22
            # oktober, en de brief aan pa schreef dat die aanvraag "inmiddels
            # gehonoreerd" was: een besluit van drie maanden voor de aanvraag.
            # Dus: de aanvraag bij het besluit is de laatste ervoor, en een
            # latere staat er apart bij, met erbij dat het besluit er niet bij
            # hoort. Gemeten op 25 oktober: 1 van de 58 aangekondigde panden.
            if besluiten:
                voor = [a for a in aanvragen
                        if a["datum"] <= besluiten[-1]["datum"]]
                na = [a for a in aanvragen
                      if a["datum"] > besluiten[-1]["datum"]]
                if voor:
                    rij["aanvraag"] = voor[-1]["datum"]
                if na:
                    rij["aanvraag_na_besluit"] = na[-1]["datum"]
            elif aanvragen:
                rij["aanvraag"] = aanvragen[-1]["datum"]
            if besluiten:
                rij["besluit"] = besluiten[-1]["datum"]
                vergund = _vergund_aantal(besluiten[-1].get("tekst"))
                if vergund:
                    rij["vergund_aantal"] = vergund
                    if vergund != len(gev):
                        rij["wijkt_af"] = len(gev) - vergund
            aangekondigd.append(rij)
            continue

        if groei:
            datum, (van, naar) = groei[-1]
            eerder = [b for b in besluiten if b["datum"] <= datum]
            rij = {"adres": pand.get("adres"), "datum": datum,
                   "van": van, "naar": naar}
            if eerder:
                besluit = eerder[-1]
                rij["besluit"] = besluit["datum"]
                rij["dagen_na_besluit"] = _dagen(besluit["datum"], datum)
                rij["tekst"] = besluit.get("tekst", "")[:160]
                # De aanvraag die bij dit besluit hoort, voor de echte
                # doorlooptijd. Besluit tot registratie is de laatste stap en
                # niet de route: bij de Biezenstraat 110 was dat één dag,
                # terwijl er 241 dagen tussen aanvraag en besluit zaten.
                voor = [a for a in aanvragen if a["datum"] <= besluit["datum"]]
                if voor:
                    rij["aanvraag"] = voor[-1]["datum"]
                    rij["dagen_aanvraag_tot_besluit"] = _dagen(
                        voor[-1]["datum"], besluit["datum"])
                vergund = _vergund_aantal(besluit.get("tekst"))
                if vergund:
                    rij["vergund_aantal"] = vergund
                    # TEGEN DE TELLING VAN NU, NIET TEGEN DE TEKST VAN TOEN.
                    # Het getal in "naar" komt uit de tekst van een
                    # gebeurtenis van vroeger, en die tekst telde elk
                    # adresseerbaar object in het pand als woning: een garage
                    # of een berging met een eigen adres telde mee. De
                    # vergunning telt zelfstandige woonruimtes. Die twee naast
                    # elkaar leggen levert een verschil op dat er niet is, en
                    # bij Hatertseweg 338 was dat verschil op 11 oktober het
                    # hoofdthema van de brief: 7 objecten tegen 6 vergunde
                    # woonruimtes, terwijl het zes tegen zes was.
                    #
                    # Oude gebeurtenisteksten worden niet herschreven, met
                    # opzet: de vergelijking in pandgeschiedenis.py blijft op
                    # bag_eenheden staan zodat er geen valse wijziging wordt
                    # gemeld op de panden die al gevolgd worden. Dus moet dit
                    # hoofdstuk de telling van nu gebruiken.
                    #
                    # Is die er nog niet, dan zegt dit hoofdstuk niets. Een
                    # pand komt pas in beeld als het opnieuw is opgehaald. Dat
                    # is stil, en stilte is deze week vaker een fout gebleken
                    # dan een foutmelding, dus het aantal wachtende panden
                    # gaat mee naar buiten in plaats van weg te vallen.
                    nu_woon = pand.get("bag_woningen")
                    if isinstance(nu_woon, list):
                        rij["bag_nu"] = len(nu_woon)
                        if vergund != len(nu_woon):
                            rij["wijkt_af"] = len(nu_woon) - vergund
                    else:
                        wacht.append(pand.get("adres"))
                gerealiseerd.append(rij)
            else:
                # Geen besluit gevonden voor de registratie. Dat betekent niet
                # dat er geen vergunning was: wij zien alleen wat is
                # gepubliceerd, en pas sinds 2012.
                rij["aanvraag"] = aanvragen[-1]["datum"] if aanvragen else None
                zonder_vergunning.append(rij)
        elif besluiten:
            # Vergund, maar in de BAG is er niets veranderd. Interessant zodra
            # het lang genoeg geleden is; daaronder is het gewoon nog in
            # uitvoering.
            laatste = besluiten[-1]
            dagen = _dagen(laatste["datum"], dt.date.today().isoformat())
            if dagen and dagen > 365:
                vergund_niets.append({
                    "adres": pand.get("adres"), "besluit": laatste["datum"],
                    "dagen": dagen, "tekst": laatste.get("tekst", "")[:160]})

    for rij in (gerealiseerd, zonder_vergunning, vergund_niets, aangekondigd):
        rij.sort(key=lambda r: r.get("datum") or r.get("besluit") or "",
                 reverse=True)
    uit = {"gerealiseerd": gerealiseerd,
           "zonder_bekende_vergunning": zonder_vergunning,
           "vergund_maar_niets_gebeurd": vergund_niets,
           "aangekondigd_nog_niet_in_gebruik": aangekondigd,
           "wijkt_af_van_vergunning": [r for r in gerealiseerd
                                       if r.get("wijkt_af")],
           "wacht_op_woningtelling": sorted(a for a in wacht if a)}
    looptijden = [r["dagen_na_besluit"] for r in gerealiseerd
                  if r.get("dagen_na_besluit") is not None
                  and 0 <= r["dagen_na_besluit"] < 3000]
    if looptijden:
        looptijden.sort()
        uit["mediaan_dagen_besluit_tot_bag"] = looptijden[len(looptijden) // 2]
        uit["aantal_looptijden"] = len(looptijden)
    return uit


# Hoe lang een gebeurtenis als nieuw in de bijlage staat. Daarna één regel.
VERS_DAGEN = 7


def _vers(datum, vandaag):
    """Is dit binnen VERS_DAGEN gezien? Zonder vandaag telt alles als vers."""
    if vandaag is None or not datum:
        return True
    try:
        return (vandaag - dt.date.fromisoformat(str(datum)[:10])).days <= VERS_DAGEN
    except ValueError:
        return True


def tekst(uit, vandaag=None):
    """
    Een blok voor de bijlage. Alleen wat er werkelijk is, geen kopjes leeg.

    ÉÉN REGEL PER PAND, EN OUD NIEUWS KORT. 17 oktober 2026, Mark: "er zitten
    dubbel in, lijkt wel". Twee dingen. Hatertseweg 338 en Biezenstraat 110
    stonden elke dag twee keer in de bijlage, onder "Splitsingen die de BAG
    inmiddels telt" en direct daaronder nog eens onder "De BAG telt een ander
    aantal dan de vergunning noemt". En ze stonden er zo van 10 tot en met 17
    oktober, elke dag met de volledige tekst, terwijl er niets aan veranderde.
    Nu staat het verschil met de vergunning op de regel van het pand zelf, en
    wat langer dan VERS_DAGEN geleden is gezien, krijgt één regel onderaan.
    """
    r = []
    ger = uit.get("gerealiseerd") or []
    afw = {rij["adres"]: rij for rij in (uit.get("wijkt_af_van_vergunning") or [])}
    wacht = uit.get("wacht_op_woningtelling") or []
    vers = [rij for rij in ger if _vers(rij.get("datum"), vandaag)]
    oud = [rij for rij in ger if not _vers(rij.get("datum"), vandaag)]

    def verschil(rij):
        a = afw.get(rij["adres"])
        if not a:
            return ""
        meer = a["wijkt_af"]
        return (f". De vergunning noemt {a['vergund_aantal']}, de BAG telt "
                f"{a['bag_nu']} woningen: {abs(meer)} "
                f"{'meer' if meer > 0 else 'minder'}, om na te kijken")

    if vers:
        r.append("## Splitsingen die de BAG inmiddels telt")
        r.append("")
        r.append("_Een vergunning zegt dat het mag; de BAG zegt dat het is "
                 "gebeurd. Zodra het aantal woningen met een eigen adres omhoog "
                 "gaat, staan de nieuwe eenheden geregistreerd._")
        r.append("")
        for rij in vers[:8]:
            # De eenheid komt uit de datum van de gebeurtenis en niet uit de
            # tekst van dit hoofdstuk. Tot 12 oktober heette elk adresseerbaar
            # object hier een woning, en bij Hatertseweg 338 werd dat verschil
            # van 1 het hoofdthema van de zondagsbrief.
            deel = (f"- **{rij['adres']}**: van {rij['van']} naar "
                    f"{rij['naar']} {_eenheid(rij['datum'])}, gezien op "
                    f"{rij['datum']}")
            if rij.get("bag_nu") is not None:
                deel += (f", waarvan er nu {rij['bag_nu']} een woonfunctie "
                         f"hebben")
            if rij.get("dagen_na_besluit") is not None:
                deel += (f", {_dag(rij['dagen_na_besluit'])} na het besluit "
                         f"van {rij['besluit']}")
            if rij.get("dagen_aanvraag_tot_besluit") is not None:
                deel += (f". De route zelf duurde langer: "
                         f"{_dag(rij['dagen_aanvraag_tot_besluit'])} van "
                         f"aanvraag ({rij['aanvraag']}) tot besluit")
            deel += verschil(rij)
            r.append(deel + ".")
        if any(afw.get(rij["adres"]) for rij in vers):
            r.append("")
            r.append("_Een verschil met de vergunning is een aanwijzing om na "
                     "te kijken en geen conclusie. Het kan betekenen dat er "
                     "meer is gerealiseerd dan mocht, maar ook dat de "
                     "vergunningtekst iets anders telt dan de BAG. Vergeleken "
                     "wordt het aantal woningen in gebruik, dus een garage met "
                     "een eigen adres en een object dat alleen nog gevormd is "
                     "tellen hier niet mee._")
        if uit.get("mediaan_dagen_besluit_tot_bag"):
            r.append("")
            r.append(f"_Mediane tijd tussen besluit en registratie: "
                     f"{uit['mediaan_dagen_besluit_tot_bag']} dagen, gemeten op "
                     f"{uit['aantal_looptijden']} panden. Dat is de laatste "
                     f"stap en niet de doorlooptijd van de route: de procedure "
                     f"begint bij de aanvraag, en die staat per pand hierboven "
                     f"waar we hem kennen._")
        r.append("")
    if wacht:
        r.append(f"_Van {len(wacht)} "
                 f"{'pand' if len(wacht) == 1 else 'panden'} met een "
                 f"opdeling in de BAG is nog niet te zeggen of die gerealiseerd "
                 f"of alleen aangekondigd is, of hoe die zich tot de vergunning "
                 f"verhoudt: de woningen in gebruik zijn daar nog niet apart "
                 f"van de bergingen, de garages en de gevormde objecten "
                 f"geteld. Dat gebeurt zodra het pand weer langskomt in de "
                 f"BAG-ronde. "
                 f"{'Dat is' if len(wacht) == 1 else 'Dat zijn'}: "
                 f"{', '.join(wacht[:6])}"
                 + (" en meer" if len(wacht) > 6 else "") + "._")
        r.append("")
    aan = uit.get("aangekondigd_nog_niet_in_gebruik") or []
    aan_vers = [rij for rij in aan if _vers(rij.get("datum"), vandaag)]
    aan_oud = [rij for rij in aan if not _vers(rij.get("datum"), vandaag)]
    if aan_vers:
        r.append("## Aangekondigd in de BAG, nog niet in gebruik")
        r.append("")
        r.append("_Een object met status gevormd staat in de registratie maar "
                 "is nog niet in gebruik. De gemeente legt het zelf vast, "
                 "meestal na een vergunning; dat dat in Nijmegen altijd zo "
                 "gaat, is niet nagekeken. Het is de aankondiging van een "
                 "splitsing en geen bewijs dat hij is gebeurd. Staat er geen "
                 "besluit bij, dan hebben wij het waarschijnlijk gemist of is "
                 "het nog niet gepubliceerd._")
        r.append("")
        for rij in aan_vers[:8]:
            maten = ", ".join(str(m) for m in rij.get("gevormd_maten") or [])
            deel = (f"- **{rij['adres']}**: {rij['gevormd']} "
                    f"{'object' if rij['gevormd'] == 1 else 'objecten'} "
                    f"gevormd" + (f" ({maten} m2)" if maten else ""))
            if rij.get("in_gebruik") is not None:
                deel += (f", naast {rij['in_gebruik']} "
                         f"{'woning' if rij['in_gebruik'] == 1 else 'woningen'}"
                         f" in gebruik")
            if rij.get("besluit"):
                deel += f". Besluit van {rij['besluit']}"
                if rij.get("vergund_aantal"):
                    deel += f" voor {rij['vergund_aantal']}"
                    if rij.get("wijkt_af"):
                        deel += (f", dat is {abs(rij['wijkt_af'])} "
                                 f"{'meer' if rij['wijkt_af'] > 0 else 'minder'}"
                                 f" gevormd dan vergund, om na te kijken")
                    else:
                        deel += ", evenveel als er gevormd zijn"
                if rij.get("aanvraag_na_besluit"):
                    # Zie zoek(): van Goorstraat 87, 25 oktober 2026.
                    deel += (f". Na dat besluit kwam op "
                             f"{rij['aanvraag_na_besluit']} een nieuwe "
                             f"aanvraag; daarop is nog geen besluit bekend, "
                             f"en het besluit van {rij['besluit']} is er dus "
                             f"geen antwoord op")
            elif rij.get("aanvraag"):
                deel += (f". Aanvraag van {rij['aanvraag']} bekend, besluit "
                         f"niet in ons archief")
            r.append(deel + ".")
        r.append("")
    zon = uit.get("zonder_bekende_vergunning") or []
    zon_vers = [rij for rij in zon if _vers(rij.get("datum"), vandaag)]
    zon_oud = [rij for rij in zon if not _vers(rij.get("datum"), vandaag)]
    if zon_vers:
        r.append("## Opgedeeld zonder dat wij een vergunning kennen")
        r.append("")
        r.append("_Dat bewijst niets: we zien alleen wat is gepubliceerd, en "
                 "pas sinds 2012. Het is wel een aanwijzing dat er een route is "
                 "die wij missen._")
        r.append("")
        for rij in zon_vers[:5]:
            r.append(f"- **{rij['adres']}**: van {rij['van']} naar "
                     f"{rij['naar']} {_eenheid(rij['datum'])}, gezien op "
                     f"{rij['datum']}.")
        r.append("")
    eerder = ([f"{rij['adres']} ({rij['datum']}"
               + (f", vergunning {afw[rij['adres']]['vergund_aantal']}, BAG "
                  f"{afw[rij['adres']]['bag_nu']}" if rij["adres"] in afw else "")
               + ")" for rij in oud]
              + [f"{rij['adres']} ({rij['datum']}, zonder bekende vergunning)"
                 for rij in zon_oud])
    # NIET ONDER "EERDER GEMELD". De datum van een aangekondigd pand is vaak
    # die van de bekendmaking, omdat de BAG geen registratiedatum meegeeft.
    # Zo'n pand is dus niet per se eerder gemeld, en dat er toch zetten zou
    # een bewering zijn die we niet kunnen staven.
    if aan_oud:
        r.append(f"_Ook met gevormde objecten, bij een gebeurtenis van langer "
                 f"dan {VERS_DAGEN} dagen geleden: "
                 + "; ".join(f"{rij['adres']} ({rij['gevormd']})"
                             for rij in aan_oud[:12])
                 + (f" en {len(aan_oud) - 12} meer" if len(aan_oud) > 12
                    else "") + "._")
        r.append("")
    if eerder:
        r.append(f"_Eerder gemeld en sindsdien ongewijzigd: "
                 f"{'; '.join(eerder[:10])}"
                 + (" en meer" if len(eerder) > 10 else "") + "._")
        r.append("")
    return "\n".join(r)


def _pand(adres, pand_id, gebeurtenissen, woningen=None, gevormd=None):
    """Een pandrecord in de vorm die pandlezer.laad() oplevert.

    Met een woningtelling is het pand op de grondslag van nu geteld, en dan
    kent het ook bag_gevormd, standaard leeg."""
    p = {"adres": adres, "pand_id": pand_id,
         "gebeurtenissen": list(gebeurtenissen)}
    if woningen is not None:
        p["bag_woningen"] = [[adres, 50] for _ in range(woningen)]
        p["bag_gevormd"] = [[adres, m] for m in (gevormd or [])]
        p["bag_eenheden"] = (p["bag_woningen"] + p["bag_gevormd"]
                             + [[adres, 50]])
    return p


def proef():
    """
    De zeef nameten op echte teksten, zonder een aanroep te doen.

    Dit bestaat omdat dit bestand twee keer stil het verkeerde deed. Het
    vergunde aantal werd niet gelezen als het besluit "woonruimtes" schreef in
    plaats van "woningen", en het gelezen aantal werd vergeleken met een getal
    uit een oude gebeurtenistekst dat elk adresseerbaar object als woning
    telde. Beide gaven geen foutmelding. De eerste leek zelfs goed te gaan,
    omdat de ene fout de andere verborg.
    """
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    def eerste(rijen, veld):
        """Het veld van de eerste rij, of None. Zonder dit valt de proef om
        met een IndexError zodra een rij ontbreekt, en dan is niet te lezen
        welke controle rood stond."""
        return (rijen[0].get(veld) if rijen else None)

    # Echte besluitteksten uit pandgeschiedenis.json.
    hatert = ("Besluit voor Het verbouwen en uitbreiden tot 6 zelfstandige "
              "woonruimtes, aan Hatertseweg 338, 6533GP Nijmegen")
    biezen = ("Besluit (met BOPA) voor  het splitsen van een bestaande woning "
              "met garage tot 2 zelfstandige woningen , aan Biezenstraat 110, "
              "6541ZW Nijmegen")
    check("vergund woonruimtes", _vergund_aantal(hatert), 6)
    check("vergund woningen", _vergund_aantal(biezen), 2)
    check("vergund woord", _vergund_aantal("omzetten naar twee woningen"), 2)
    check("vergund reeks", _vergund_aantal("van 2 naar 4 appartementen"), 4)
    check("vergund niets", _vergund_aantal("Besluit voor een dakkapel"), None)
    check("vergund geen getal", _vergund_aantal("tot zelfstandige woningen"),
          None)
    # "in" mag geen woordstaart zijn.
    check("vergund woordgrens",
          _vergund_aantal("een terrein 3 woningen"), None)
    check("splitswoord woonruimte", _is_splitsing(hatert), True)
    check("splitswoord omzetting",
          _is_splitsing("het omzetten tot 4 onzelfstandige kamers"), False)

    # De gebeurtenistekst, in beide vormen die pandgeschiedenis.py schrijft.
    check("aantallen oud", _aantallen(
        "de BAG telt nu 7 woningen in dit pand, was 1: 20, 147, 46 m2"),
        (1, 7))
    check("aantallen met staart", _aantallen(
        "de BAG telt nu 3 woningen in dit pand, was 1: 168, 203 m2; "
        "daarnaast 1 ander object met een eigen adres"), (1, 3))
    check("aantallen zonder was", _aantallen(
        "de BAG telt nu 6 woningen in dit pand: 147, 46 m2"), None)

    gebeurtenissen = [
        {"datum": "2026-10-06", "soort": "bekendmaking", "tekst": hatert},
        {"datum": "2026-10-09", "soort": "bag",
         "tekst": "de BAG telt nu 7 woningen in dit pand, was 1: 20, 147, 46, "
                  "24, 19, 23, 19 m2"},
    ]

    # 1. Zes vergund, zes woningen in de BAG: geen verschil, ook al zegt de
    #    oude gebeurtenistekst zeven. Dit is het geval van Hatertseweg 338.
    uit = zoek({"a": _pand("Hatertseweg 338", "P1", gebeurtenissen, 6)})
    check("zes tegen zes geen verschil", uit["wijkt_af_van_vergunning"], [])
    check("zes tegen zes wel gerealiseerd", len(uit["gerealiseerd"]), 1)
    # NIET IN HET HOOFDSTUK ZONDER VERGUNNING. Dat is geen schoonheidsfoutje
    # maar een valse beschuldiging: de brief van 11 oktober zette Hatertseweg
    # 338 onder "Opgedeeld zonder dat wij een vergunning kennen", terwijl het
    # besluit van 6 oktober in hetzelfde bestand stond. Het kwam daar terecht
    # omdat _is_splitsing() "woonruimtes" niet herkende en er dus geen besluit
    # bij de groei te vinden was. Beide hoofdstukken hangen aan dat ene woord,
    # dus hoort het hier vast te staan.
    check("niet onder zonder vergunning", uit["zonder_bekende_vergunning"],
          [])
    check("zes tegen zes bag_nu", eerste(uit["gerealiseerd"], "bag_nu"), 6)
    check("zes tegen zes vergund",
          eerste(uit["gerealiseerd"], "vergund_aantal"), 6)
    check("zes tegen zes wacht niet", uit["wacht_op_woningtelling"], [])

    # 2. Zeven woningen met woonfunctie tegen zes vergund: wel een verschil.
    uit = zoek({"a": _pand("Hatertseweg 338", "P1", gebeurtenissen, 7)})
    check("zeven tegen zes verschil", len(uit["wijkt_af_van_vergunning"]), 1)
    check("zeven tegen zes hoeveel",
          eerste(uit["wijkt_af_van_vergunning"], "wijkt_af"), 1)

    # 3. Nog geen woningtelling: niets melden, maar wel laten weten dat er
    #    gewacht wordt. Zonder deze regel zou het hoofdstuk er stil uit zien
    #    alsof er niets te vinden was.
    # bag_gevormd staat er wel: dit meet het wachten op de woningtelling, en
    # niet het wachten op de gevormd-telling (dat doet 6).
    p3 = _pand("Hatertseweg 338", "P1", gebeurtenissen)
    p3["bag_gevormd"] = []
    uit = zoek({"a": p3})
    check("zonder telling geen verschil", uit["wijkt_af_van_vergunning"], [])
    check("zonder telling wacht", uit["wacht_op_woningtelling"],
          ["Hatertseweg 338"])
    blok = tekst(uit)
    check("zonder telling tekst noemt het",
          "nog niet apart" in blok, True)
    # De eenheid in het eerste hoofdstuk hangt van de datum af, want een
    # getal van voor 12 oktober telde ook garages en bergingen.
    check("oude grondslag heet anders", _eenheid("2026-10-09"),
          "objecten met een eigen adres")
    check("nieuwe grondslag heet woningen", _eenheid("2026-10-12"), "woningen")
    check("oude eenheid in de tekst",
          "naar 7 objecten met een eigen adres" in blok, True)
    check("een dag enkelvoud", _dag(1), "1 dag")
    check("twee dagen meervoud", _dag(2), "2 dagen")
    for geval, n in (("zes", 6), ("zeven", 7), ("geen", None)):
        uit = zoek({"a": _pand("Hatertseweg 338", "P1", gebeurtenissen, n)})
        try:
            tekst(uit)
        except Exception as e:
            fouten.append(f"tekst() valt om bij {geval}: {type(e).__name__} {e}")

    # 3b. HET VOORBEHOUD MOET OOK IN DE BRIEFINSTRUCTIE KLOPPEN.
    #
    # Dit blok zegt wat er wordt vergeleken. De schrijfinstructie in
    # brief_verhalend.py zei tot 11 oktober iets anders: dat een garage met
    # een eigen adres in de BAG als woning meetelt. Dat was juist tot de
    # telling op woonfunctie overging, en daarna niet meer. Het model volgde
    # de instructie, dus stonden er die dag twee tegengestelde beweringen in
    # één brief aan pa, en de verkeerde stond bovenaan.
    #
    # Erger: die verklaring praatte het signaal weg. Bij de Biezenstraat 110
    # noemt het besluit "een bestaande woning met garage tot 2 zelfstandige
    # woningen" en telt de BAG er drie met een woonfunctie, van 168, 203 en
    # 44 m2. Die 44 m2 is de garage, en die staat dus als wooneenheid
    # geregistreerd. Dat is precies het interessante.
    #
    # Dezelfde tekst op twee plekken loopt uiteen, dus bindt deze controle de
    # twee aan elkaar: verandert het voorbehoud hier, dan is de proef rood
    # tot de instructie mee is.
    uit = zoek({"a": _pand("Hatertseweg 338", "P1", gebeurtenissen, 7)})
    blok = tekst(uit)
    check("het blok noemt de grondslag", "woonfunctie" in blok, True)
    try:
        with open("brief_verhalend.py", encoding="utf-8") as f:
            instructie = f.read()
    except Exception:
        instructie = ""
    if instructie:
        # De grondslag uit het blok zelf halen en díe in de instructie
        # zoeken, niet een eigen kopie van de zin. Anders bindt deze
        # controle de twee teksten niet: een eerste versie vergeleek twee
        # hardgecodeerde zinnen, en toen "objecten" in het blok veranderde
        # bleef de proef groen terwijl de twee uiteen waren gelopen.
        m = re.search(r"Vergeleken wordt ([^,.]+)", blok)
        if not m:
            fouten.append("het blok zegt niet meer waarop wordt vergeleken, "
                          "dus de brief kan het voorbehoud niet overnemen")
        else:
            grondslag = m.group(1).strip()
            check(f"de briefinstructie noemt de grondslag {grondslag!r}",
                  grondslag in instructie, True)
        for verboden in ("is in de BAG een woning",
                         "telt daar als woning mee"):
            if verboden in instructie:
                fouten.append(
                    f"brief_verhalend.py zegt nog {verboden!r}; sinds de "
                    f"telling op woonfunctie staat is dat onjuist en praat "
                    f"het het verschil weg")
    else:
        fouten.append("brief_verhalend.py niet te lezen, dus het voorbehoud "
                      "in de briefinstructie is niet nagemeten")

    # 3c. ÉÉN REGEL PER PAND, OUD NIEUWS KORT (17 oktober). Met een verschil
    #     staat het pand één keer in het blok, en een week later alleen nog in
    #     de regel "eerder gemeld".
    uit = zoek({"a": _pand("Hatertseweg 338", "P1", gebeurtenissen, 7)})
    blok = tekst(uit, dt.date(2026, 10, 10))
    check("een pand met een verschil staat één keer in het blok",
          blok.count("Hatertseweg 338"), 1)
    check("het verschil staat op de regel van het pand",
          "de BAG telt 7 woningen" in blok, True)
    blok = tekst(uit, dt.date(2026, 10, 30))
    check("oud nieuws krijgt één korte regel",
          ("Eerder gemeld" in blok, "## Splitsingen" in blok), (True, False))

    # 4. Een besluit zonder leesbaar aantal hoort niet te wachten: er valt
    #    niets te vergelijken, dus er is ook niets in te halen.
    zonder = [dict(gebeurtenissen[0], tekst="Besluit voor het splitsen van "
                                            "een woning"), gebeurtenissen[1]]
    p4 = _pand("Ergens 1", "P2", zonder)
    p4["bag_gevormd"] = []
    uit = zoek({"a": p4})
    check("onleesbaar aantal wacht niet", uit["wacht_op_woningtelling"], [])

    # 5. De weg waarlangs bag_woningen bij dit bestand aankomt. Het veld werd
    #    per pand opgeslagen maar stond niet in de rij gedeelde velden van
    #    pandlezer, dus het kwam er per adres in terecht. Twee adressen op
    #    hetzelfde pand laten dat zien.
    try:
        from pandlezer import compact, laad as _laad
        heen = {"a": _pand("Aubadestraat 12", "P3", gebeurtenissen, 6),
                "b": _pand("Aubadestraat 16", "P3", gebeurtenissen, 6)}
        kort = compact(heen)
        check("compact deelt bag_woningen",
              "bag_woningen" in (kort.get("_panden", {}).get("P3") or {}), True)
        check("compact laat niets per adres staan",
              [s for s in ("a", "b") if "bag_woningen" in kort[s]], [])
        import tempfile, os as _os
        fd, pad = tempfile.mkstemp(suffix=".json")
        _os.close(fd)
        with open(pad, "w", encoding="utf-8") as f:
            json.dump(kort, f)
        terug = _laad(pad)
        _os.unlink(pad)
        check("laad vouwt bag_woningen weer uit",
              len(terug["a"].get("bag_woningen") or []), 6)
        check("zoek na de ronde om schijf",
              zoek(terug)["wijkt_af_van_vergunning"], [])
    except ImportError:
        fouten.append("pandlezer niet te importeren")

    # 6. GEVORMD IS AANGEKONDIGD, NIET GEREALISEERD (17 oktober). Echte
    #    teksten van Graafseweg 18: drie aanvragen voor 6 appartementen, geen
    #    besluit in het archief, en een BAG-tekst die 1 woning in gebruik en 6
    #    gevormde objecten samen "7 woningen" noemde. De brief maakte daar een
    #    zevende eenheid zonder vergunning van.
    graaf = [
        {"datum": "2026-04-13", "soort": "bekendmaking",
         "tekst": "Aanvraag omgevingsvergunning voor het splitsen van de "
                  "woning in zes zelfstandige appartementen, aan Graafseweg "
                  "18, 6512CB Nijmegen"},
        {"datum": "2026-10-17", "soort": "bag",
         "tekst": "de BAG telt nu 7 woningen in dit pand, was 1: 55, 374, 55, "
                  "35, 29, 60, 50 m2"}]
    uit = zoek({"g": _pand("Graafseweg 18", "P4", graaf, 1,
                           [55, 55, 35, 29, 60, 50])})
    check("gevormd is niet gerealiseerd", uit["gerealiseerd"], [])
    check("gevormd is niet zonder vergunning",
          uit["zonder_bekende_vergunning"], [])
    aan = uit["aangekondigd_nog_niet_in_gebruik"]
    check("gevormd is aangekondigd",
          [(r["gevormd"], r["in_gebruik"], r.get("aanvraag")) for r in aan],
          [(6, 1, "2026-04-13")])
    blok = tekst(uit, dt.date(2026, 10, 17))
    check("het blok zegt 6 gevormd naast 1 in gebruik",
          "6 objecten gevormd (55, 55, 35, 29, 60, 50 m2), naast 1 woning in "
          "gebruik" in blok, True)
    check("het blok noemt geen zevende", "naar 7" in blok, False)
    # Nog niet opnieuw geteld: wachten, niet raden.
    zonder_gev = _pand("Graafseweg 18", "P4", graaf, 7)
    zonder_gev.pop("bag_gevormd")
    uit = zoek({"g": zonder_gev})
    check("zonder gevormd-telling wacht het", (uit["wacht_op_woningtelling"],
          uit["gerealiseerd"]), (["Graafseweg 18"], []))
    # Hatertseweg 338: 6 vergund, 6 gevormd, 1 in gebruik. Geen verschil.
    uit = zoek({"a": _pand("Hatertseweg 338", "P1", gebeurtenissen, 1,
                           [20, 46, 24, 19, 23, 19])})
    aan = uit["aangekondigd_nog_niet_in_gebruik"]
    check("zes vergund zes gevormd",
          [(r.get("vergund_aantal"), r["gevormd"], r.get("wijkt_af"))
           for r in aan], [(6, 6, None)])
    check("zes gevormd geen verschil met de vergunning",
          uit["wijkt_af_van_vergunning"], [])
    # Een groei van na de overgang op een pand zonder gevormde objecten is
    # wel gerealiseerd: de regel mag echte splitsingen niet wegfilteren.
    nieuw = [dict(gebeurtenissen[0]),
             {"datum": "2026-10-20", "soort": "bag",
              "tekst": "de BAG telt nu 6 woningen in dit pand, was 1: 147, "
                       "46, 24, 19, 23, 19 m2"}]
    uit = zoek({"a": _pand("Hatertseweg 338", "P1", nieuw, 6)})
    check("echte splitsing na de overgang blijft gerealiseerd",
          (len(uit["gerealiseerd"]), uit["aangekondigd_nog_niet_in_gebruik"]),
          (1, []))

    # 7. EEN AANVRAAG NA HET BESLUIT (25 oktober). Echte teksten van van
    #    Goorstraat 87 uit pandgeschiedenis.json. De brief schreef dat de
    #    aanvraag van 22 oktober "inmiddels gehonoreerd" was, met het besluit
    #    van 28 juli als bewijs.
    goor = [
        {"datum": "2026-01-20", "soort": "bekendmaking",
         "tekst": "Aanvraag omgevingsvergunning voor het bouwkundig splitsen "
                  "van een woning naar drie zelfstandige woningen, aan van "
                  "Goorstraat 87, 6512EC Nijmegen"},
        {"datum": "2026-07-28", "soort": "bekendmaking",
         "tekst": "Besluit voor het bouwkundig splitsen van een woning naar "
                  "twee zelfstandige woningen, aan van Goorstraat 87, 6512EC "
                  "Nijmegen"},
        {"datum": "2026-10-22", "soort": "bekendmaking",
         "tekst": "Aanvraag omgevingsvergunning voor het bouwkundig splitsen "
                  "van een woning naar 2 zelfstandige woningen, aan van "
                  "Goorstraat 87, 6512EC Nijmegen"}]
    uit = zoek({"v": _pand("van Goorstraat 87", "P5", goor, 1, [95, 120])})
    aan = uit["aangekondigd_nog_niet_in_gebruik"]
    check("een aanvraag na het besluit hoort er niet bij",
          [(r.get("aanvraag"), r.get("besluit"), r.get("aanvraag_na_besluit"))
           for r in aan], [("2026-01-20", "2026-07-28", "2026-10-22")])
    blok = tekst(uit, dt.date(2026, 10, 25))
    check("het blok zegt dat het besluit geen antwoord is op de latere "
          "aanvraag", "Na dat besluit kwam op 2026-10-22 een nieuwe aanvraag"
          in blok and "is er dus geen antwoord op" in blok, True)
    # Zonder latere aanvraag blijft de regel zoals hij was.
    uit = zoek({"v": _pand("van Goorstraat 87", "P5", goor[:2], 1,
                           [95, 120])})
    check("zonder latere aanvraag geen extra zin",
          "Na dat besluit" in tekst(uit, dt.date(2026, 10, 25)), False)

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=UIT_PAD)
    ap.add_argument("--tekst", default="")
    ap.add_argument("--proef", action="store_true",
                    help="De zeef nameten zonder iets op te halen.")
    args = ap.parse_args()
    if args.proef:
        return proef()
    try:
        from pandlezer import laad
        geschiedenis = laad("pandgeschiedenis.json")
    except Exception as e:
        print(f"Geschiedenis niet te lezen: {str(e)[:80]}", file=sys.stderr)
        return 0
    uit = zoek(geschiedenis)
    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False, indent=1)
    if args.tekst:
        blok = tekst(uit, dt.date.today())
        if blok:
            with open(args.tekst, "w", encoding="utf-8") as f:
                f.write(blok)
    print(f"Splitsingen: {len(uit['gerealiseerd'])} gerealiseerd, "
          f"{len(uit['zonder_bekende_vergunning'])} zonder bekende vergunning, "
          f"{len(uit['vergund_maar_niets_gebeurd'])} vergund zonder resultaat",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
