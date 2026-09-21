#!/usr/bin/env python3
"""
Maakt een verhalende versie van de vastgoedbrief.

Zelfde bronnen als de werkbrief, maar geschreven als een brief: doorlopende
tekst, geen tabellen, cijfers in zinnen in plaats van in kolommen. Bedoeld om
rustig te lezen, niet om beslissingen mee te nemen.

Gebruik:
  python brief_verhalend.py --datum 2026-09-04 --uit digests/2026-09-04-verhaal.md
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time

import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-5"
# Let op: een secret dat bestaat maar leeg is, geeft een lege tekst terug en
# niet de standaardwaarde. Vandaar de or in plaats van een default.
AANHEF = (os.environ.get("BRIEF_AANHEF") or "").strip() or "Beste pa"

PROFIEL = """Je schrijft een lange brief van Mark aan zijn vader over de vastgoedmarkt in Nijmegen. Zij kennen elkaar goed en werken allebei in vastgoed; Mark en zijn broer runnen samen Derksen Vastgoed. Zijn vader volgt de Nijmeegse markt al zijn hele leven.

Je krijgt per brief een maximum aantal woorden mee. Houd je daaraan: een brief die in vier minuten uit is, wordt gelezen; een brief van drie kwartier niet. Doorlopende tekst, geen opsommingen van kale cijfers.

SCHRIJF EENVOUDIG, NIET SIMPEL. Het onderwerp mag ingewikkeld zijn, de zinnen niet. Concreet:
- Korte zinnen. Eén gedachte per zin. Loopt een zin over drie regels, hak hem door.
- Leg een vakterm uit bij de eerste keer, in gewone woorden en tussen komma's. Dus: de herzieningsregeling, de regel dat de fiscus terugkijkt of je de btw terecht hebt afgetrokken.
- Geen stapeling van bijzinnen en geen verwijzingen als "die", "dat" en "hetgeen" als de lezer moet terugzoeken waar dat op slaat.
- Noem een bedrag of een percentage liever één keer goed dan drie keer terloops.
- Begin een alinea met de hoofdzaak, niet met de aanloop.

Het niveau blijft hetzelfde: je vader is niet dom, hij leest alleen 's ochtends. Schrijf zoals je het aan tafel zou uitleggen.

ACTUALITEIT KRIJGT ALTIJD VOORRANG. Is er nieuws, dan gaat de brief daarover. Is er weinig nieuws, dan is er altijd een onderwerp dat verdieping verdient; dan wordt dat het hoofdstuk. Een lege brief bestaat niet, een gevulde brief wel: die moet je vermijden.

Schrijf in de ik-vorm. Spreek hem aan met 'je' en 'jij', nooit met 'u'.

OPBOUW: begin bij wat er werkelijk speelt, niet bij een vast rondje langs de buurten.

1. Open met het belangrijkste van vandaag. Dat is meestal een gemeentelijk besluit, soms een nieuw pand, soms een bericht dat schuurt met onze eigen cijfers.

   DE EERSTE ZIN GAAT NOOIT OVER WAT ER NIET IS. Begin dus niet met "het is een rustige dag", "geen mutaties", "weinig te melden" of iets van die strekking, ook niet als dat waar is. Begin bij het onderwerp zelf. Ligt het aanbod stil, dan is het belangrijkste van die dag iets anders: een besluit, een artikel, een cijfer dat opvalt. Dat wordt dan je opening.

   Dat er geen mutaties waren mag je later noemen, in een halve zin en terloops. Het is achtergrond, geen nieuws.

   Is er werkelijk helemaal niets, schrijf dan drie of vier zinnen over het enige dat er wel is en houd op. Een korte brief is geen mislukking.

2. Werk dat belangrijkste uit. Bij een gemeentelijk besluit: wat is er besloten, op welk adres, wat betekent het voor de voorraad en voor iemand die daar iets vergelijkbaars wil. Gebruik de achtergrondcijfers van die buurt om het besluit te plaatsen, dus als onderbouwing en niet als losse opsomming. Dit is het soort passage waar Marks vader het meest aan heeft.

3. TOETS HET NIEUWS AAN DE CIJFERS. Staat er in een artikel een bewering over de markt, kijk dan of onze eigen gegevens dat bevestigen. Komt het overeen, zeg dat in één zin. Wijkt het af, dan is dat een eigen bevinding. Dit is het waardevolste wat de brief kan doen: wij hebben cijfers die de schrijver van dat artikel niet had.

   MAAR VERGELIJK OVER DE JUISTE PERIODE. Een artikel over een trend gaat over weken of maanden, niet over gisteren. Concludeer dus nooit dat een stijging "niet zichtbaar is in onze cijfers" op grond van een stand die sinds gisteren gelijk is. Kijk naar de terugblik over een maand, een kwartaal en een jaar als die erbij staat, en naar de prijstrend per buurt over vier weken en een kwartaal.

   Staat die langere reeks er niet bij, trek dan geen conclusie over de trend. Schrijf dan dat je het op deze termijn niet kunt beoordelen. Dat is eerlijker dan een conclusie die op één dag rust.

4. Panden die aandacht verdienen. Introduceer een pand altijd bij de eerste vermelding, ook als je het verderop in de brief nog eens noemt. Dus niet "het Krayenhofflaan-pand" zonder dat je hebt verteld wat dat is, maar: het huis aan de Krayenhofflaan staat sinds zes dagen te koop voor €575.000, 135 vierkante meter, vijftien procent onder de buurtmediaan. Pas daarna mag je er kort naar terugverwijzen. Behoud de links precies zoals ze in de gegevens staan, in de vorm [naam](adres). Staan er geen bijzondere panden, sla dit dan over.

5. VERDIEPING. Je krijgt een achtergrondstuk mee dat aansluit bij het nieuws van vandaag. Gebruik dat niet als los blokje onderaan, maar verweef het waar het hoort: het artikel meldt iets, en dit legt uit hoe die regel precies werkt en wat hij voor ons betekent. Neem de inhoud over in je eigen woorden.

   Is er een onderwerp dat vandaag van meerdere kanten komt, bijvoorbeeld een bericht in de pers en een besluit van de gemeente over hetzelfde thema, maak daar dan het hoofdstuk van de brief van. Bekijk het van meerdere kanten: wat zegt het nieuws, wat zeggen onze eigen cijfers, wat zegt de regelgeving, en wat betekent het voor ons. Sluit af met wat je ervan vindt.

   Is er geen duidelijk thema, houd het dan bij een paar zinnen verdieping bij het belangrijkste bericht.

6. De rente, kort, en alleen als er iets aan veranderd is of als het iets verklaart.

7. BUURT VAN DE DAG: je krijgt een buurtnaam aangeleverd. Geef alleen die ene buurt een kort achtergrondportret van een paar zinnen, en alleen als het ergens bij aansluit. Kies de drie of vier cijfers die het meest zeggen. De andere buurten krijgen geen portret; die komen een andere dag.

   Noem je een pand of een besluit in een andere buurt, dan mag je daar wel één cijfer bij halen dat er iets over zegt, bijvoorbeeld het aantal inbraken of vernielingen per duizend inwoners als het over verhuurbaarheid gaat, of het aandeel kamerverhuurvergunningen als het over verkameren gaat. Eén cijfer, ter plaatse, niet een heel portret.

8. Sluit af met een korte conclusie: wat je van het geheel vindt en waar je volgende keer op let. Bij een brief met een duidelijk hoofdstuk hoort daar een oordeel bij, niet alleen een vooruitblik.

WAT JE NIET DOET:
- Elke buurt langslopen omdat het nu eenmaal zes buurten zijn.
- Melden dat er ergens niets gebeurde. Wat er niet is, laat je weg.
- Een lange brief schrijven als er weinig te melden valt. Kort is beter dan gevuld.
- Dezelfde buurtbeschrijving herhalen die gisteren ook al stond.

LET OP BIJ PERCENTAGES. Een percentage achter een pand is de afwijking van de MEDIAANPRIJS PER VIERKANTE METER in die buurt, niet een prijswijziging. "Nieuwe Markt 90 €575.000 (-27%)" betekent dus: dit pand is per vierkante meter 27% goedkoper dan vergelijkbare panden in die buurt. Het betekent NIET dat de vraagprijs verlaagd is. Schrijf dus nooit "onder de oorspronkelijke vraagprijs" of "inmiddels verhoogd". Een echte prijswijziging staat er altijd expliciet bij als "prijs verlaagd met" of "prijs gewijzigd".

GEEN TOEZEGGINGEN NAMENS MARK. De brief is van Mark, maar jij beslist niet wat hij gaat doen. Schrijf dus niet "ik ga dat voortaan standaard doen" of "dat voeg ik toe aan onze lijst". Je mag zeggen wat je opvalt en wat het overwegen waard is; wat hij ermee doet is aan hem.

DE RENTE IS DE MARKTRENTE, NIET DIE VAN ONS. De rentecijfers in de gegevens zijn de tarieven die een bank vandaag rekent voor een nieuwe verhuurhypotheek, per financieringsgraad. Het is NIET de rente op de eigen portefeuille: die is vast gefinancierd en beweegt niet mee met de markt. Schrijf dus nooit "onze rente", "bij ons staat hij", "onze hypotheek" of "onze financiering" als je deze cijfers bedoelt. Zeg "de marktrente voor een verhuurhypotheek" of "wat een bank nu rekent".

Trek er ook geen conclusie uit voor het bestaande bezit. Een stijgende marktrente maakt een NIEUWE aankoop duurder en drukt de prijs die je kunt bieden; op de panden die er al zijn heeft hij geen invloed zolang de rente vaststaat. Noem nooit de voorwaarden of de herkomst van de eigen financiering: die horen niet in de brief.

FISCAAL ONDERSCHEID DAT JE NIET MAG VERMENGEN. Het eigenwoningforfait, de hypotheekrenteaftrek en het box 1-regime gelden uitsluitend voor de woning waar iemand zelf woont. Ze gelden NIET voor verhuurd vastgoed. Mark en zijn broer houden hun panden in een BV: daar gelden de vennootschapsbelasting, de overdrachtsbelasting en de btw, en er is geen eigenwoningforfait en geen hypotheekrenteaftrek. Gaat een artikel over de eigen woning, zeg dan dat het de eigen woning betreft en niet de verhuurportefeuille, en trek er geen conclusie uit voor verhuurd vastgoed.

LET OP DE EENHEID. Bedragen in de gegevens staan er met hun eenheid bij: per jaar of per maand. Neem die letterlijk over. Een operationeel resultaat per jaar is geen bedrag per maand. Staat er geen eenheid bij, noem het bedrag dan zonder eenheid in plaats van er een te kiezen.

VERGELIJKINGEN. Zeg je dat een buurt "tussen" twee andere ligt, of "hoger" of "lager" dan een andere, controleer dan de getallen voordat je het opschrijft. Bij de buurtcijfers staat de rangorde er al bij, dus gebruik die liever dan zelf te vergelijken.

ABSOLUUT VERBOD OP VERZONNEN CIJFERS. Alleen getallen die in de aangeleverde gegevens staan.

WAT ER NIET STAAT, BESTAAT NIET. Ontbreekt een cijfer in de gegevens, laat het dan weg. Maak er geen nul van, geen schatting en geen "geen gevallen geregistreerd". Dat een soort misdrijf niet wordt genoemd betekent dat wij dat cijfer niet hebben, niet dat het nul is. Hetzelfde geldt voor een ontbrekend energielabel, bouwjaar of oppervlakte: die laat je onbesproken."""


def met_laag_inkomen(cbs, buurten):
    """De twee buurten met het hoogste aandeel lage inkomens."""
    reeks = [(b, cbs[b].get("laag_inkomen")) for b in buurten
             if cbs[b].get("laag_inkomen") is not None]
    return sorted(reeks, key=lambda x: -x[1])[:2]


def wist_je_dat(cbs, verg, misdrijven=None):
    """
    Elke dag een ander weetje uit de eigen cijfers. Rouleert op dagnummer,
    zodat het niet elke ochtend hetzelfde is.
    """
    def n(x):
        return f"{int(x):,}".replace(",", ".")

    def pct(x, cijfers=1):
        return f"{x:.{cijfers}f}".replace(".", ",")

    weetjes = []
    buurten = [b for b in cbs if not b.startswith("_")]

    def per(b, veld):
        return cbs[b].get(veld)

    # --- Kamerverhuur en vergunningen ---
    met_verg = [(b, verg[b], cbs[b]["won"]) for b in buurten
                if verg.get(b) and cbs[b].get("won")]
    for b, v, won in sorted(met_verg, key=lambda x: -x[1] / x[2])[:3]:
        weetjes.append(f"in {b} {pct(v / won * 100)} procent van alle woningen een "
                       f"vergunning voor kamerverhuur heeft, {v} stuks op {n(won)} "
                       f"woningen")
    if len(met_verg) >= 2:
        hoog = max(met_verg, key=lambda x: x[1] / x[2])
        laag = min(met_verg, key=lambda x: x[1] / x[2])
        weetjes.append(f"er in {hoog[0]} verhoudingsgewijs "
                       f"{pct((hoog[1] / hoog[2]) / (laag[1] / laag[2]), 1)} keer zoveel "
                       f"kamerverhuurvergunningen zijn als in {laag[0]}")
    totaal_v = sum(v for _b, v, _w in met_verg)
    if totaal_v:
        weetjes.append(f"er in de ring sinds 2013 {totaal_v} vergunningen voor "
                       f"kamerverhuur zijn verleend")

    # --- Studenten ---
    met_stud = [(b, cbs[b]["studenten"], cbs[b]["inwoners"]) for b in buurten
                if cbs[b].get("studenten") and cbs[b].get("inwoners")]
    for b, st_, inw in sorted(met_stud, key=lambda x: -x[1] / x[2])[:3]:
        weetjes.append(f"in {b} bijna {round(st_ / inw * 100)} van elke honderd "
                       f"inwoners student is")
    totaal_stud = sum(x[1] for x in met_stud)
    if met_stud and totaal_stud:
        b, st_, _ = max(met_stud, key=lambda x: x[1])
        weetjes.append(f"{round(st_ / totaal_stud * 100)} procent van alle studenten "
                       f"in de ring in {b} woont")
        weetjes.append(f"er in de zes buurten samen {n(totaal_stud)} studenten wonen")

    # --- Woningvoorraad en eigendom ---
    for b in buurten:
        g = cbs[b]
        if g.get("corp", 0) >= 40:
            weetjes.append(f"in {b} {g['corp']} procent van de woningen van een "
                           f"woningcorporatie is, meer dan waar ook in de ring")
        if g.get("meergezins", 0) >= 90:
            weetjes.append(f"{g['meergezins']} procent van alle woningen in {b} een "
                           f"appartement is")
        if g.get("koop", 100) <= 15:
            weetjes.append(f"in {b} maar {g['koop']} procent van de woningen een "
                           f"koopwoning is")
        if g.get("koop", 0) >= 50:
            weetjes.append(f"{b} met {g['koop']} procent koopwoningen de meest "
                           f"eigen-bezit buurt van de ring is")
    grootste = max((b for b in buurten if per(b, "won")),
                   key=lambda b: per(b, "won"), default=None)
    if grootste:
        weetjes.append(f"{grootste} met {n(per(grootste, 'won'))} woningen de "
                       f"grootste buurt van de ring is")
    kleinste = min((b for b in buurten if per(b, "won")),
                   key=lambda b: per(b, "won"), default=None)
    if kleinste:
        weetjes.append(f"{kleinste} met {n(per(kleinste, 'won'))} woningen juist de "
                       f"kleinste is")

    # --- Huishoudens ---
    for b in buurten:
        g = cbs[b]
        if g.get("eenpersoons", 0) >= 60:
            weetjes.append(f"in {b} {g['eenpersoons']} procent van de huishoudens uit "
                           f"een persoon bestaat")
        if g.get("met_kinderen", 100) <= 10:
            weetjes.append(f"in {b} maar {g['met_kinderen']} procent van de "
                           f"huishoudens kinderen heeft")
    met_gr = [(b, per(b, "huishoudgrootte")) for b in buurten
              if per(b, "huishoudgrootte")]
    if met_gr:
        b, gr = max(met_gr, key=lambda x: x[1])
        weetjes.append(f"een huishouden in {b} gemiddeld uit {pct(gr, 1)} personen "
                       f"bestaat, het hoogste van de ring")

    # --- Inkomen, vermogen en waarde ---
    met_ink = [(b, per(b, "inkomen")) for b in buurten if per(b, "inkomen")]
    if len(met_ink) >= 2:
        hoog = max(met_ink, key=lambda x: x[1])
        laag = min(met_ink, key=lambda x: x[1])
        weetjes.append(f"het gemiddelde inkomen per inwoner in {hoog[0]} "
                       f"{n(hoog[1] * 1000)} euro is en in {laag[0]} "
                       f"{n(laag[1] * 1000)} euro, een verschil van "
                       f"{round((hoog[1] - laag[1]) / laag[1] * 100)} procent")
    met_verm = [(b, per(b, "vermogen")) for b in buurten
                if per(b, "vermogen") is not None]
    if len(met_verm) >= 2:
        hoog = max(met_verm, key=lambda x: x[1])
        laag = min(met_verm, key=lambda x: x[1])
        weetjes.append(f"het mediane vermogen van een huishouden in {hoog[0]} "
                       f"{n(hoog[1] * 1000)} euro is, tegen {n(laag[1] * 1000)} euro "
                       f"in {laag[0]}")
    met_woz = [(b, per(b, "woz")) for b in buurten if per(b, "woz")]
    if len(met_woz) >= 2:
        hoog = max(met_woz, key=lambda x: x[1])
        laag = min(met_woz, key=lambda x: x[1])
        weetjes.append(f"een huis in {hoog[0]} volgens de gemeente gemiddeld "
                       f"{n(hoog[1] * 1000)} euro waard is en in {laag[0]} "
                       f"{n(laag[1] * 1000)} euro")
    for b, v in met_laag_inkomen(cbs, buurten):
        weetjes.append(f"in {b} {v} procent van de huishoudens een laag inkomen heeft")

    # --- Veiligheid ---
    for soort, omschrijving in (("woninginbraak", "woninginbraken"),
                                ("vernieling", "gevallen van vernieling"),
                                ("fietsendiefstal", "fietsendiefstallen"),
                                ("drugs- en drankoverlast",
                                 "meldingen van drugs- en drankoverlast")):
        reeks = []
        for b in buurten:
            mis = misdrijven.get(b) if misdrijven else None
            if not mis or not cbs[b].get("inwoners"):
                continue
            laatst = mis[sorted(mis)[-1]]
            aantal = laatst.get(soort)
            if aantal:
                reeks.append((b, aantal, cbs[b]["inwoners"]))
        if len(reeks) >= 2:
            b, aantal, inw = max(reeks, key=lambda x: x[1] / x[2])
            weetjes.append(f"{b} met {pct(aantal / inw * 1000)} {omschrijving} per "
                           f"duizend inwoners het hoogste van de ring scoort")
            b2, a2, i2 = min(reeks, key=lambda x: x[1] / x[2])
            weetjes.append(f"{b2} juist het laagste scoort op {omschrijving}, met "
                           f"{pct(a2 / i2 * 1000)} per duizend inwoners")

    if not weetjes:
        return ""

    # Niet op de datum vertrouwen maar bijhouden wat er al geweest is. Een
    # rekentruc met het dagnummer gaat mis zodra de lijst van lengte verandert,
    # en dan zie je hetzelfde weetje dagen achter elkaar.
    pad = "weetjes_gezien.json"
    try:
        with open(pad, encoding="utf-8") as fh:
            gezien = json.load(fh)
    except Exception:
        gezien = []

    nieuw = [w for w in weetjes if w not in gezien]
    if not nieuw:          # alles geweest: de ronde begint opnieuw
        gezien, nieuw = [], weetjes
    keuze = nieuw[0]

    gezien.append(keuze)
    # Alleen de laatste ronde onthouden, anders groeit het bestand eindeloos
    gezien = gezien[-max(len(weetjes), 1):]
    try:
        with open(pad, "w", encoding="utf-8") as fh:
            json.dump(gezien, fh, ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"Kon {pad} niet schrijven: {e}", file=sys.stderr)
    print(f"Weetje {len(gezien)} van {len(weetjes)}: {keuze[:60]}", file=sys.stderr)
    return keuze



MAX_WOORDEN = 800


def nieuwswaarde(bronnen):
    """
    Hoeveel valt er vandaag te melden?

    Bepaalt of de actualiteit de brief vult of dat er ruimte is voor een
    verdieping. Niet elke dag heeft nieuws, maar er is altijd wel een onderwerp
    dat uitleg verdient; de vraag is alleen hoeveel ruimte dat krijgt.
    """
    tekst = " ".join(t for _naam, t in bronnen if t).lower()
    punten = 0
    punten += tekst.count("kernsignalen") and 2 or 0
    punten += 3 * tekst.count("[splitsen]")
    punten += 2 * tekst.count("[kamerverhuur]")
    punten += 2 * tekst.count("prijs verlaagd")
    punten += 2 * tekst.count("nieuw of gewijzigd")
    punten += tekst.count("besluit voor")
    punten += tekst.count("lezen]")          # ruwweg het aantal artikelen
    return punten


def schrijfruimte(punten):
    """Hoeveel woorden krijgt de brief, en waar ligt de nadruk?"""
    if punten >= 12:
        return (MAX_WOORDEN,
                "Er is vandaag veel te melden. Laat de actualiteit de brief "
                "vullen en houd de verdieping bij een alinea. Kies streng: "
                "liever drie onderwerpen goed dan zes vluchtig.")
    if punten >= 5:
        return (700,
                "Er is vandaag genoeg te melden, maar niet overvloedig. "
                "Behandel de actualiteit en geef daarna een echte verdieping "
                "van een alinea of drie bij het onderwerp dat het meest speelt.")
    return (600,
            "Er is vandaag weinig actualiteit. Meld dat kort en maak van de "
            "verdieping het hoofdstuk van de brief: behandel het aangeleverde "
            "onderwerp grondig, van meerdere kanten, met de eigen cijfers en de "
            "regelgeving erbij, en sluit af met wat het voor ons betekent. Dit "
            "is geen opvulling maar de reden dat de brief vandaag de moeite "
            "waard is.")


def achtergrondtekst():
    """
    Het achtergrondstuk dat bij het nieuws van vandaag past.

    Wordt aan de brief meegegeven in plaats van er los onder geplakt, zodat het
    dienst kan doen als verdieping bij het bericht waar het bij hoort.
    """
    try:
        from bronnen import achtergrond_van_de_dag
    except Exception:
        return ""
    nieuws = ""
    for pad in ("nieuws_vandaag.md",):
        try:
            with open(pad, encoding="utf-8") as f:
                nieuws = f.read()
        except Exception:
            pass
    return "\n".join(achtergrond_van_de_dag(nieuws)).strip()


def _mediaan_rang():
    """
    De rangorde van de buurten op prijs per vierkante meter.

    Het model vergelijkt getallen niet betrouwbaar: het schreef dat Bottendaal
    tussen Stadscentrum en Altrade lag, terwijl het onder allebei lag. Door de
    rangorde zelf te berekenen en mee te geven hoeft het dat niet te doen.
    """
    try:
        with open("prijstrend.json", encoding="utf-8") as f:
            trend = json.load(f)
    except Exception:
        return {}
    laatste = {}
    for buurt, reeks in trend.items():
        if isinstance(reeks, dict) and reeks:
            laatste[buurt] = reeks[sorted(reeks)[-1]]
    if len(laatste) < 2:
        return {}
    volgorde = sorted(laatste, key=lambda b: laatste[b])
    n = len(volgorde)
    uit = {}
    for i, b in enumerate(volgorde):
        if i == 0:
            omschrijving = f"de laagste prijs per m2 van de {n}"
        elif i == n - 1:
            omschrijving = f"de hoogste prijs per m2 van de {n}"
        else:
            omschrijving = f"de {i + 1}e van {n} van laag naar hoog in prijs per m2"
        uit[b] = omschrijving
    return uit


def buurtcijfers_tekst():
    """De buurtcijfers als platte regels, zodat het model ze kan verwerken."""
    try:
        with open("buurten_cbs.json", encoding="utf-8") as f:
            cbs = json.load(f)
    except Exception:
        return ""
    try:
        with open("vergunningen_per_buurt.json", encoding="utf-8") as f:
            verg = json.load(f)
    except Exception:
        verg = {}
    try:
        with open("misdrijven_per_buurt.json", encoding="utf-8") as f:
            misdrijven = json.load(f)
    except Exception:
        misdrijven = {}

    regels = []
    for buurt in ("Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
                  "Altrade", "Biezen"):
        g = cbs.get(buurt)
        if not g:
            continue
        d = [f"{buurt}: {g.get('won')} woningen"]
        if g.get("koop") is not None:
            d.append(f"{g['koop']}% koop")
        if g.get("corp") is not None:
            d.append(f"{g['corp']}% woningcorporatie")
        if g.get("meergezins") is not None:
            d.append(f"{g['meergezins']}% appartement")
        if g.get("woz"):
            d.append(f"gemiddelde waarde volgens de gemeente "
                     f"{g['woz'] * 1000} euro")
        if g.get("studenten"):
            d.append(f"{g['studenten']} studenten")
        if g.get("inwoners"):
            d.append(f"{g['inwoners']} inwoners")
        if verg.get(buurt):
            d.append(f"{verg[buurt]} vergunningen voor kamerverhuur sinds 2013")

        rang = _mediaan_rang().get(buurt)
        if rang:
            d.append(f"prijs per m2: {rang}")

        # Wie er woont, wat ze verdienen en bezitten
        if g.get("eenpersoons") is not None:
            d.append(f"{g['eenpersoons']}% woont alleen")
        if g.get("met_kinderen") is not None:
            d.append(f"{g['met_kinderen']}% van de huishoudens heeft kinderen")
        if g.get("huishoudgrootte"):
            d.append(f"gemiddeld {g['huishoudgrootte']} personen per huishouden")
        if g.get("inkomen"):
            d.append(f"gemiddeld inkomen {g['inkomen'] * 1000} euro per inwoner")
        if g.get("vermogen") is not None:
            d.append(f"mediaan vermogen {g['vermogen'] * 1000} euro per huishouden")
        if g.get("laag_inkomen") is not None:
            d.append(f"{g['laag_inkomen']}% met een laag inkomen")

        # Misdrijven, afgezet tegen het aantal inwoners
        mis = misdrijven.get(buurt)
        if mis:
            jaren = sorted(mis)
            laatst = mis[jaren[-1]]
            per = []
            for soort in ("woninginbraak", "vernieling", "drugs- en drankoverlast",
                          "fietsendiefstal"):
                n = laatst.get(soort)
                # Een ontbrekend cijfer is geen nul: dan laten we het weg
                if n is None:
                    continue
                tekst = f"{n} {soort}"
                if g.get("inwoners"):
                    tekst += f" ({n / g['inwoners'] * 1000:.1f} per 1000 inwoners)"
                per.append(tekst)
            if per:
                d.append(f"misdrijven in {jaren[-1][:4]}: " + ", ".join(per))
        regels.append(", ".join(d))
    return "\n".join(regels)


def weetje_van_de_dag():
    """Een weetje onder de brief, dat elke dag rouleert."""
    def lees_json(pad):
        try:
            with open(pad, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    cbs = lees_json("buurten_cbs.json")
    verg = lees_json("vergunningen_per_buurt.json")
    if not cbs:
        return ""
    try:
        with open("misdrijven_per_buurt.json", encoding="utf-8") as f:
            misdrijven = json.load(f)
    except Exception:
        misdrijven = {}
    return wist_je_dat(cbs, verg, misdrijven)



AANHEF_WOORDEN = ("beste", "hoi", "hallo", "dag", "lieve", "pa", "pap", "papa",
                  "vader", "hey", "hé")


# De afsluiting kan op een of twee regels staan: "Groet, Mark" maar ook
# "Met vriendelijke groet," met de naam eronder.
ONDERTEKENING = re.compile(
    r"\n+\s*(?:met vriendelijke groet(?:en)?|met hartelijke groet(?:en)?|"
    r"groet(?:en)?|hartelijke groet(?:en)?|tot (?:morgen|volgende week|zondag|snel)|"
    r"liefs|hoogachtend|vriendelijke groet(?:en)?)\b[^\n]*"
    r"(?:\n[^\n]{0,40})?\s*$",
    re.IGNORECASE)


def haal_ondertekening_weg(brief):
    """
    Het model zet er soms toch een ondertekening onder. Die hoort er niet:
    de mail komt van Mark, dus zijn naam eronder is dubbelop.
    """
    vorige = None
    while brief != vorige:
        vorige = brief
        brief = ONDERTEKENING.sub("", brief).rstrip()
    return brief


def zet_aanhef(brief, aanhef):
    """
    Vervangt de aanhef door de ingestelde. Het model neemt de opgegeven aanhef
    niet altijd letterlijk over en maakt er soms Pap of Beste vader van; dat is
    niet aan het model om te bepalen.
    """
    if not brief:
        return brief
    regels = brief.split("\n")
    # Zoek de eerste niet-lege regel; is dat een aanhef, dan vervangen we hem
    for i, regel in enumerate(regels):
        if not regel.strip():
            continue
        kaal = regel.strip()
        eerste = kaal.rstrip(",.!").lower()
        # Een lege of bijna lege eerste regel is een mislukte aanhef: het model
        # kreeg een lege aanhef aangeleverd en zette alleen de komma neer.
        if len(eerste) <= 1:
            regels[i] = f"{aanhef},"
            return "\n".join(regels)
        kort = len(eerste.split()) <= 4
        if kort and any(eerste.startswith(w) for w in AANHEF_WOORDEN):
            regels[i] = f"{aanhef},"
            return "\n".join(regels)
        # Geen aanhef gevonden: we zetten hem er alsnog voor
        return f"{aanhef},\n\n" + brief
    return brief


def lees(pad):
    """Leest een digest-bestand, of een lege string."""
    try:
        with open(pad, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def strip_opmaak(tekst, maxlen=14000):
    """Haalt tabellen en HTML eruit; het model krijgt de inhoud, niet de vorm."""
    tekst = re.sub(r"<[^>]+>", " ", tekst)
    regels = []
    for regel in tekst.split("\n"):
        r = regel.strip()
        if not r or r.startswith("|---") or set(r) <= set("|-: "):
            continue
        if r.startswith("|"):
            r = " . ".join(x.strip() for x in r.strip("|").split("|") if x.strip())
        # Links laten staan: de lezer moet kunnen doorklikken naar het artikel
        r = r.replace("**", "").replace("_", "")
        if r:
            regels.append(r)
    return "\n".join(regels)[:maxlen]


def schrijf_brief(bronnen):
    if not ANTHROPIC_API_KEY:
        print("Geen ANTHROPIC_API_KEY", file=sys.stderr)
        return ""
    inhoud = "\n\n".join(f"=== {naam} ===\n{tekst}"
                         for naam, tekst in bronnen if tekst)
    if not inhoud.strip():
        return ""
    # Elke dag krijgt een andere buurt het achtergrondportret, zodat de brief
    # niet elke ochtend dezelfde zes beschrijvingen herhaalt.
    ronde = ["Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
             "Altrade", "Biezen"]
    buurt_vandaag = ronde[dt.date.today().toordinal() % len(ronde)]
    punten = nieuwswaarde(bronnen)
    woorden, sturing = schrijfruimte(punten)
    print(f"Nieuwswaarde vandaag: {punten} punten, ruimte {woorden} woorden",
          file=sys.stderr)

    prompt = (f"AANHEF: {AANHEF}\n"
              f"BUURT VAN DE DAG: {buurt_vandaag}\n"
              f"MAXIMUM: {woorden} woorden. Dat is een harde grens, geen streven. "
              f"Ga er niet overheen; schrap liever een onderwerp dan dat je alles "
              f"half behandelt.\n"
              f"NADRUK VANDAAG: {sturing}\n\n"
              f"GEGEVENS VAN VANDAAG:\n\n{inhoud}\n\n"
              f"Schrijf de brief. Alleen de brieftekst, niets eromheen.")
    # Een lange brief schrijven duurt; twee minuten was te krap. Drie pogingen
    # met ruime wachttijd, want dit is de enige stap die de brief oplevert.
    resp = None
    for poging in range(1, 4):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 16000, "system": PROFIEL,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=(30, 600))
            resp.raise_for_status()
            break
        except Exception as e:
            if poging == 3:
                print(f"Brief schrijven mislukt na 3 pogingen: {e}", file=sys.stderr)
                return ""
            print(f"  poging {poging} mislukt ({e}), opnieuw", file=sys.stderr)
            time.sleep(poging * 10)
    try:
        body = resp.json()
        tekst = "".join(b.get("text", "")
                        for b in body.get("content", [])).strip()
        reden = body.get("stop_reason")
        if reden == "max_tokens":
            print("LET OP: de brief is afgekapt omdat de limiet is bereikt. "
                  "Verhoog max_tokens in dit bestand.", file=sys.stderr)
        gebruikt = (body.get("usage") or {}).get("output_tokens")
        n_woorden = len(tekst.split())
        if gebruikt:
            print(f"Brief geschreven: {gebruikt} tokens, {n_woorden} woorden "
                  f"(ruimte was {woorden})", file=sys.stderr)
        if n_woorden > woorden * 1.2:
            print(f"LET OP: de brief is {n_woorden - woorden} woorden langer dan "
                  f"de ruimte. Scherp de sturing aan als dit vaker gebeurt.",
                  file=sys.stderr)
        return tekst
    except Exception as e:
        print(f"Antwoord verwerken mislukt: {e}", file=sys.stderr)
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datum", default=dt.date.today().isoformat())
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    d = args.datum

    bronnen = [
        ("Cijfers per buurt", buurtcijfers_tekst()),
        ("Achtergrond bij het nieuws van vandaag", achtergrondtekst()),
        ("Aanbod en buurten", strip_opmaak(lees(f"digests/{d}-marktprijzen.md"))),
        ("Gemeentelijke besluiten", strip_opmaak(lees(f"digests/{d}-bekendmakingen.md"))),
        ("Nieuws", strip_opmaak(lees(f"digests/{d}-publicaties.md"), 6000)),
        ("Rente", strip_opmaak(lees(f"digests/{d}-rente.md"), 3000)),
    ]
    brief = zet_aanhef(haal_ondertekening_weg(schrijf_brief(bronnen) or ""), AANHEF)
    if not brief:
        print("Geen brief gemaakt", file=sys.stderr)
        return

    datum_nl = dt.date.fromisoformat(d).strftime("%d %B %Y")
    for en, nl in {"January": "januari", "February": "februari", "March": "maart",
                   "April": "april", "May": "mei", "June": "juni", "July": "juli",
                   "August": "augustus", "September": "september",
                   "October": "oktober", "November": "november",
                   "December": "december"}.items():
        datum_nl = datum_nl.replace(en, nl)

    tekst = f"# Vastgoed in Nijmegen, {datum_nl}\n\n{brief}\n"
    weetje = weetje_van_de_dag()
    if weetje:
        tekst += f"\n---\n\n**Wist je dat** {weetje}?\n"
    uit = args.uit or f"digests/{d}-verhaal.md"
    os.makedirs(os.path.dirname(uit) or ".", exist_ok=True)
    with open(uit, "w", encoding="utf-8") as f:
        f.write(tekst)
    print(f"Brief weggeschreven naar {uit}", file=sys.stderr)
    print(tekst)


if __name__ == "__main__":
    main()
