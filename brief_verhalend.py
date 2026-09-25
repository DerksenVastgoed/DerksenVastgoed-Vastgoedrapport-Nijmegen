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

1. Open met het belangrijkste van vandaag, in deze volgorde:
   a. een gemeentelijk besluit of een wijziging in de regels die de hele portefeuille raakt;
   b. een bericht uit de pers dat schuurt met onze eigen cijfers, of dat bevestigt;
   c. een nieuw pand, maar alleen als in de gegevens staat dat het de drempel haalt, dus als de richtprijs dicht bij de vraagprijs ligt. Staat dat er niet bij, dan is het geen opening maar hooguit een alinea verderop;
   d. anders: het onderwerp van de verdieping.

   Een besluit of een regelwijziging gaat dus voor op een nieuw pand, want dat raakt alles wat jullie bezitten en niet alleen dat ene adres.

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

7. BUURT VAN DE DAG (niet in de zondagseditie): je krijgt een buurtnaam aangeleverd. Geef alleen die ene buurt een kort achtergrondportret van een paar zinnen, en alleen als het ergens bij aansluit. Kies de drie of vier cijfers die het meest zeggen. De andere buurten krijgen geen portret; die komen een andere dag.

   Noem je een pand of een besluit in een andere buurt, dan mag je daar wel één cijfer bij halen dat er iets over zegt, bijvoorbeeld het aantal inbraken of vernielingen per duizend inwoners als het over verhuurbaarheid gaat, of het aandeel kamerverhuurvergunningen als het over verkameren gaat. Eén cijfer, ter plaatse, niet een heel portret.

8. Sluit af met een korte conclusie: wat je van het geheel vindt en waar je volgende keer op let. Bij een brief met een duidelijk hoofdstuk hoort daar een oordeel bij, niet alleen een vooruitblik.

WAT JE NIET DOET:
- Elke buurt langslopen omdat het nu eenmaal zes buurten zijn.
- Melden dat er ergens niets gebeurde. Wat er niet is, laat je weg.
- Een lange brief schrijven als er weinig te melden valt. Kort is beter dan gevuld.
- Dezelfde buurtbeschrijving herhalen die gisteren ook al stond.

LET OP BIJ PERCENTAGES. Een percentage achter een pand is de afwijking van de MEDIAANPRIJS PER VIERKANTE METER in die buurt, niet een prijswijziging. "Nieuwe Markt 90 €575.000 (-27%)" betekent dus: dit pand is per vierkante meter 27% goedkoper dan vergelijkbare panden in die buurt. Het betekent NIET dat de vraagprijs verlaagd is. Schrijf dus nooit "onder de oorspronkelijke vraagprijs" of "inmiddels verhoogd". Een echte prijswijziging staat er altijd expliciet bij als "prijs verlaagd met" of "prijs gewijzigd".

PER PAND, NIET PER BUURT. De omzettingsvergunning en de opkoopbescherming hangen aan de WOZ van het afzonderlijke pand, niet aan het gemiddelde van de buurt. Een gemiddelde zegt niets over hoeveel of welke panden onder de grens liggen, en dus ook niets over de kans daarop. Schrijf nooit "wie in deze buurt koopt, hoeft niet door het vergunningstraject" of "de kans dat een woning hier onder de grens blijft is klein". Wil je iets zeggen over panden onder de grens, kijk dan in de gegevens van vandaag: daar staat per buurt hoeveel panden onder de WOZ-grens niet getoond zijn.

HET PUNTENSTELSEL. Een beter energielabel geeft meer punten en dus een hogere maximale huur; een slechter label geeft er minder. Schrijf dus nooit dat de punten bij een laag label "zwaarder tellen". Het puntenaantal van een woning volgt onder meer uit de oppervlakte, het energielabel en de WOZ-waarde, plus keuken, sanitair, buitenruimte en verwarming (bron: Volkshuisvesting Nederland). De WOZ is dus juist een van de zwaarste onderdelen; schrijf nooit dat het puntenaantal "niet van de WOZ" afhangt. Bij panden met een bekende WOZ staat in de gegevens een ondergrens van de punten. Onder de 187 punten geldt voor nieuwe contracten een wettelijke maximumhuur, en dan rekent de doorrekening met dat maximum in plaats van de markthuur.

Zeg niet welk onderdeel het verschil in punten tussen twee panden veroorzaakt ("dat zit vooral in de oppervlakte"), want de telling per onderdeel staat niet in de gegevens.

GEEN UITSPRAKEN OVER DE EIGEN PORTEFEUILLE. Je hebt geen gegevens over de panden van Mark en zijn broer: niet hun puntenaantal, niet hun segment, niet hun huur. Schrijf dus niets als "onze panden zitten vaak in het hogere segment". Je mag zeggen voor welk soort pand een regel van belang is, maar niet welke van hun eigen panden daaronder vallen.

DATA ALTIJD ABSOLUUT. Noem de ingangsdatum van een regel zoals die in de bron staat: "sinds 1 juli 2024", niet "sinds vorig jaar zomer"; "sinds 1 januari 2025", niet "sinds januari" of "sinds dit jaar". De datum van vandaag staat bovenaan de gegevens; reken niet zelf om naar "vorig jaar" of "dit jaar".

EEN APPARTEMENT IS GEEN BIJZONDERHEID. Staan er volgens de BAG meerdere woningen in hetzelfde pand, dan is het aangeboden object meestal gewoon een appartement in een complex. Presenteer dat aantal niet als een vondst en niet als "het bijzondere van dit pand". Bij zo'n appartement gaat de VvE over splitsen en kamerverhuur, niet alleen de gemeente; wat de akte en het reglement toestaan, weten wij niet.

DOSSIERS PER PAND. Voor de panden die ertoe doen krijg je een dossier: per pand alle feiten uit alle bronnen, elk met de bron erbij. Daar haal je de verbanden uit. Noem je een pand, kijk dan eerst in het dossier wat er over bekend is: WOZ ten opzichte van de grens, puntentelling, kamerverhuur op het pand en bij de buren, bekendmakingen op het adres, de doorrekening. Een regel "geen aanwijzing gevonden" is geen bewijs dat er niets is; neem de beperking die erbij staat over als je hem noemt.

VERBANDEN LEGGEN, MET BEWIJS PER SCHAKEL. De waarde van deze brief zit in verbanden tussen bronnen die elk afzonderlijk niet zichtbaar zijn: een besluit van de gemeente, een pand in het aanbod, de buurtcijfers, de puntentelling, de regelgeving, een artikel. Zoek die verbanden actief, vanuit meerdere invalshoeken. Maar elke schakel in de redenering moet in de gegevens of in een bron staan. Staat een schakel er niet, dan is het verband verzonnen, hoe aannemelijk het ook klinkt.

Voorbeelden van verzonnen verbanden die al eens in de brief stonden: dat de vpb-schijf "in een dure buurt eerder een rol speelt" (de schijf geldt voor de totale winst van de BV, niet per pand of buurt, en een hoge WOZ is geen hoge winst); dat twee panden "in dezelfde straat" liggen terwijl het adres een andere straat laat zien; dat "met 70% eenpersoonshuishoudens de lokale vraag naar een grote woning dun is en je huurder van buiten de buurt komt" (hoe huidige huishoudens zijn samengesteld, zegt niets over waar een nieuwe huurder vandaan komt); dat een buurt "voor kamerverhuur ruimte heeft" omdat er veel koopwoningen en weinig corporatiewoningen zijn (of een pand kan, hangt af van de WOZ van dat pand en of er al twee kamerpanden naast liggen). Noem ook geen doorlooptijden ("kon weken duren") en geen kwalificaties van de gemeente ("willekeur") die niet in een bron staan.

EEN RICHTPRIJS BOVEN DE VRAAGPRIJS IS GEEN KOOPSIGNAAL ZOLANG DE HUUR NIET GEMETEN IS. De richtprijs rust op de huur, en die komt uit gemeten advertenties of uit een aanname. Staat er bij een pand dat de huur een aanname is of met de referentie is gewogen, dan schrijf je dat erbij en presenteer je de uitkomst niet als een kans. Kijk in het dossier naar de regel "let op".

HUUR IS GEEN RICHTPRIJS. De huur is een bedrag per maand. De richtprijs is een koopsom: het hoogste bod waarbij de nettohuur de rente en aflossing dekt. Schrijf nooit "de richtprijs komt op €2.394 per maand".

EEN LOSSE STAND IS GEEN TREND. Van de kapitaalmarktrente krijg je een stand, geen verloop. Schrijf dus niet dat een stijging "er nog niet doorheen is" of "nog moet doorwerken": dat vraagt een reeks die je niet hebt.

SPLITSEN IN NIJMEGEN. Nijmegen kent geen splitsingsvergunning. Dat de BAG aparte woningen telt, zegt niet of een pand juridisch is gesplitst. Schrijf dus nooit "je hoeft geen splitsingsvergunning meer aan te vragen".

RAMINGEN VAN BANKEN ZIJN GEEN CIJFERS. Een woningmarktmonitor van ABN AMRO, Rabobank of ING is een verwachting van een commerciele partij, met een belang bij de markt. Noem zo'n getal altijd als raming en van wie, en zet het naast wat er gemeten is: de CBS-index en onze eigen vraagprijzen. Schrijf nooit "de huizenprijzen stijgen met 3%" als een bank dat verwacht.

CBS-INDEX EN RINGCIJFERS. De prijsindex van CBS en Kadaster meet werkelijke verkoopprijzen, gecorrigeerd voor het type woning, per maand of kwartaal. Onze ringcijfers zijn de mediaan van vraagprijzen over een paar dagen. Zet ze naast elkaar om te laten zien of de ring anders beweegt dan Nederland of Nijmegen, maar trek geen conclusie uit het verschil in procenten alsof het dezelfde maat is. Noem bij een maandcijfer of het seizoengecorrigeerd is, zoals het in de gegevens staat.

EEN MEDIAAN IS GEEN PRIJS. De buurtmediaan per m2 verschuift ook als er andere panden bijkomen of afgaan. Een lagere mediaan betekent dus niet dat prijzen zijn gedaald. Schrijf "de mediaan van onze waarnemingen" en niet "de prijs daalde"; noem een nieuw pand onder de mediaan als het die verschuiving verklaart.

DE RING IS NIET DE STAD. Je hebt cijfers van zes buurten, niet van heel Nijmegen. Schrijf dus "van de zes buurten", nooit "dan in de rest van de stad".

BRONNEN. Het achtergrondstuk heeft een bron tussen haakjes. Noem die bron als je de inhoud gebruikt, in een korte bijzin. Voeg zelf geen regels, bedragen of vuistregels toe die niet in de gegevens of het achtergrondstuk staan.

HET ACHTERGRONDSTUK IS GEEN NIEUWS. Presenteer het niet als iets wat vandaag binnenkwam ("kreeg ik op mijn bureau", "vond ik vandaag"). Het is uitleg bij het onderwerp, en zo breng je het ook.

HERKOMST VAN DE ACHTERGROND. Het achtergrondstuk dat je meekrijgt is door ons geschreven, niet door de gemeente of een andere instantie. Schrijf het dus niet toe aan de gemeente ("de gemeente noemt dit..."). Staat er iets in over een regel of verordening, dan mag je de regel noemen, maar niet de gemeente als bron van het oordeel.

BESCHRIJF DE OPBOUW NIET. Zeg niet "dit wordt het hoofdstuk van de brief", "er was geen artikel om op te toetsen" of iets anders over hoe deze brief tot stand komt. Je vader leest een brief, geen verantwoording van de werkwijze.

VEILIGHEIDSCIJFERS. De politie telt misdrijven op de plaats waar ze zijn gepleegd, en deze brief deelt ze door het aantal bewoners. Bij fietsendiefstal en vernieling telt dan mee wie er in de buurt komt, niet alleen wie er woont. Gebruik die daarom niet als maat voor hoe prettig een buurt is voor een huurder, en zeg er niet bij dat het "vooral iets zegt over het aantal bezoekers": dat hebben we niet gemeten. Woninginbraak gaat wel over de bewoners. Wil je buurten op veiligheid vergelijken voor verhuur, begin dan bij woninginbraak, en noem het als dat een ander beeld geeft dan de rest.

GEEN TOEZEGGINGEN NAMENS MARK. De brief is van Mark, maar jij beslist niet wat hij gaat doen. Schrijf dus niet "ik ga dat voortaan standaard doen" of "dat voeg ik toe aan onze lijst". Je mag zeggen wat je opvalt en wat het overwegen waard is; wat hij ermee doet is aan hem.

DE RENTE IS DE MARKTRENTE, NIET DIE VAN ONS. De rentecijfers in de gegevens zijn de tarieven die een bank vandaag rekent voor een nieuwe verhuurhypotheek, per financieringsgraad. Het is NIET de rente op de eigen portefeuille: die is vast gefinancierd en beweegt niet mee met de markt. Schrijf dus nooit "onze rente", "bij ons staat hij", "onze hypotheek" of "onze financiering" als je deze cijfers bedoelt. Zeg "de marktrente voor een verhuurhypotheek" of "wat een bank nu rekent".

Trek er ook geen conclusie uit voor het bestaande bezit. Een stijgende marktrente maakt een NIEUWE aankoop duurder en drukt de prijs die je kunt bieden; op de panden die er al zijn heeft hij geen invloed zolang de rente vaststaat. Noem nooit de voorwaarden of de herkomst van de eigen financiering: die horen niet in de brief.

FISCAAL ONDERSCHEID DAT JE NIET MAG VERMENGEN. Het eigenwoningforfait, de hypotheekrenteaftrek en het box 1-regime gelden uitsluitend voor de woning waar iemand zelf woont. Ze gelden NIET voor verhuurd vastgoed. Mark en zijn broer houden hun panden in een BV: daar gelden de vennootschapsbelasting, de overdrachtsbelasting en de btw, en er is geen eigenwoningforfait en geen hypotheekrenteaftrek. De tariefschijf van de vennootschapsbelasting geldt voor de totale winst van de BV in een jaar, niet per pand en niet per buurt. Gaat een artikel over de eigen woning, zeg dan dat het de eigen woning betreft en niet de verhuurportefeuille, en trek er geen conclusie uit voor verhuurd vastgoed.

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
        weetjes.append(f"in {b} bij {v} van de {n(won)} woningen bekend is dat er "
                       f"kamers worden verhuurd, {pct(v / won * 100)} procent, via een "
                       f"vergunning of een melding")
    if len(met_verg) >= 2:
        hoog = max(met_verg, key=lambda x: x[1] / x[2])
        laag = min(met_verg, key=lambda x: x[1] / x[2])
        weetjes.append(f"er in {hoog[0]} verhoudingsgewijs "
                       f"{pct((hoog[1] / hoog[2]) / (laag[1] / laag[2]), 1)} keer zoveel "
                       f"bekende kamerverhuurpanden zijn als in {laag[0]}")
    totaal_v = sum(v for _b, v, _w in met_verg)
    if totaal_v:
        weetjes.append(f"er in de ring {totaal_v} panden bekend zijn met kamerverhuur, "
                       f"uit vergunningen en meldingen samen")

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
        if (g.get("corp") or 0) >= 40:
            weetjes.append(f"in {b} {g['corp']} procent van de woningen van een "
                           f"woningcorporatie is, meer dan waar ook in de ring")
        if (g.get("meergezins") or 0) >= 90:
            weetjes.append(f"{g['meergezins']} procent van alle woningen in {b} een "
                           f"appartement is")
        if (g.get("koop") if g.get("koop") is not None else 100) <= 15:
            weetjes.append(f"in {b} maar {g['koop']} procent van de woningen een "
                           f"koopwoning is")
        if (g.get("koop") or 0) >= 50:
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
        if (g.get("eenpersoons") or 0) >= 60:
            weetjes.append(f"in {b} {g['eenpersoons']} procent van de huishoudens uit "
                           f"een persoon bestaat")
        if (g.get("met_kinderen") if g.get("met_kinderen") is not None else 100) <= 10:
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
    # Alleen woninginbraak: fietsendiefstal en vernieling per bewoner zeggen
    # weinig over de buurt, en een weetje geeft geen ruimte voor die kanttekening.
    for soort, omschrijving in (("woninginbraak", "woninginbraken"),):
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
            "Er is vandaag weinig actualiteit. Begin direct bij het onderwerp en "
            "meld niet dat het stil was. Maak van de verdieping het hoofdstuk van "
            "de brief: behandel het aangeleverde "
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
    # Het bestand is per week opgebouwd: {week: {buurt: mediaan, "_datum": ...}}.
    # Een eerdere versie las het per buurt, rangschikte daardoor de weken en gaf
    # de brief nooit een rangorde mee. We nemen de laatste week, en per buurt
    # alleen getallen.
    weken = sorted(k for k in trend if not str(k).startswith("_")
                   and isinstance(trend[k], dict))
    if not weken:
        return {}
    laatste = {b: v for b, v in trend[weken[-1]].items()
               if b in ZES_BUURTEN and isinstance(v, (int, float))}
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


ZES_BUURTEN = ("Stadscentrum", "Benedenstad", "Bottendaal", "Galgenveld",
               "Altrade", "Biezen")


def _veld_rang(veld):
    """De hoeveelste van de zes buurten op een CBS-veld, vooraf berekend."""
    try:
        with open("buurten_cbs.json", encoding="utf-8") as f:
            cbs = json.load(f)
    except Exception:
        return {}
    # Alleen de zes buurten van de ring: het bestand kan meer bevatten, en dan
    # zou "het hoogste van de zes" stilletjes "het hoogste van de 44" worden
    waarden = {b: g.get(veld) for b, g in cbs.items()
               if b in ZES_BUURTEN and isinstance(g, dict)
               and g.get(veld) is not None}
    if len(waarden) < 2:
        return {}
    volgorde = sorted(waarden, key=lambda b: waarden[b])
    n = len(volgorde)
    uit = {}
    for i, b in enumerate(volgorde):
        if i == 0:
            uit[b] = f"het laagste van de {n} buurten"
        elif i == n - 1:
            uit[b] = f"het hoogste van de {n} buurten"
        else:
            uit[b] = f"de {i + 1}e van {n} van laag naar hoog"
    return uit


def _misdrijf_rang():
    """
    Per buurt en per misdrijfsoort: de hoeveelste van de zes, per 1000 inwoners.

    Vooraf berekend om dezelfde reden als de prijsrangorde: het model schreef
    dat Bottendaal ruim onder Galgenveld zat qua vernieling, terwijl het er
    ruim boven zat.
    """
    try:
        with open("misdrijven_per_buurt.json", encoding="utf-8") as f:
            mis = json.load(f)
        with open("buurten_cbs.json", encoding="utf-8") as f:
            cbs = json.load(f)
    except Exception:
        return {}
    uit = {}
    for soort in ("woninginbraak", "vernieling", "fietsendiefstal"):
        per_buurt = {}
        for buurt, jaren in mis.items():
            if buurt not in ZES_BUURTEN:
                continue
            inw = (cbs.get(buurt) or {}).get("inwoners")
            if not jaren or not inw:
                continue
            n = jaren[sorted(jaren)[-1]].get(soort)
            if n is not None:
                per_buurt[buurt] = n / inw * 1000
        if len(per_buurt) < 2:
            continue
        volgorde = sorted(per_buurt, key=lambda b: per_buurt[b])
        n = len(volgorde)
        for i, b in enumerate(volgorde):
            if i == 0:
                tekst = f"het laagste van de {n} buurten"
            elif i == n - 1:
                tekst = f"het hoogste van de {n} buurten"
            else:
                tekst = f"de {i + 1}e van {n} van laag naar hoog"
            uit.setdefault(b, {})[f"{soort} per 1000 inwoners"] = (
                f"{per_buurt[b]:.1f}".replace(".", ",") + f", {tekst}")
    return uit


def woningprijzen_tekst():
    """De CBS-prijsindex bestaande koopwoningen, landelijk en voor Nijmegen."""
    try:
        from woningprijsindex import omschrijf
        with open("woningprijsindex.json", encoding="utf-8") as f:
            return omschrijf(json.load(f))
    except Exception:
        return ""


def bouwkosten_tekst():
    """De CBS-bouwkostenindex, voor als een artikel over bouwkosten gaat."""
    try:
        from bouwkosten_index import indexfactor, omschrijf
        info = indexfactor()
        if info.get("geindexeerd"):
            return omschrijf(info)
    except Exception:
        pass
    return ""


def _kamerverhuur_rang():
    """
    De rangorde van de buurten op bekende kamerverhuurpanden per woning.

    Nodig omdat het model zelf vergeleek en schreef dat Biezen met 46 panden
    het laagste van de zes was, terwijl de Benedenstad er 15 heeft. En een
    aantal zonder noemer zegt weinig: Biezen heeft ruim drie keer zoveel
    woningen als de Benedenstad.
    """
    kv = _kamerverhuur_per_buurt()
    try:
        with open("buurten_cbs.json", encoding="utf-8") as f:
            cbs = json.load(f)
    except Exception:
        return {}
    aandeel = {}
    for b, v in kv.items():
        won = (cbs.get(b) or {}).get("won")
        if b in ZES_BUURTEN and won and v.get("totaal"):
            aandeel[b] = v["totaal"] / won * 100
    if len(aandeel) < 2:
        return {}
    volgorde = sorted(aandeel, key=lambda x: aandeel[x])
    n = len(volgorde)
    uit = {}
    for i, b in enumerate(volgorde):
        plek = ("het laagste" if i == 0 else "het hoogste" if i == n - 1
                else f"de {i + 1}e van laag naar hoog")
        tekst = (f"{aandeel[b]:.1f}".replace(".", ",")
                 + f"% van de woningen, {plek} van de {n} buurten")
        # Ligt de buur er vlak naast, dan is een rangorde geen verschil. Zonder
        # deze regel wordt "het laagste" tegenover "de tweede" een contrast dat
        # er niet is.
        buren = [volgorde[j] for j in (i - 1, i + 1) if 0 <= j < n]
        dichtbij = [x for x in buren if abs(aandeel[x] - aandeel[b]) < 0.15]
        if dichtbij:
            tekst += f", nagenoeg gelijk aan {' en '.join(dichtbij)}"
        uit[b] = tekst
    return uit


def _kamerverhuur_per_buurt():
    try:
        with open("kamerverhuur_per_buurt.json", encoding="utf-8") as f:
            return json.load(f).get("per_buurt", {})
    except Exception:
        return {}


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
        # Bekende kamerverhuurpanden uit vergunningen en meldingen samen, met de
        # uitsplitsing, zodat de brief ziet wat alleen via een melding bekend is
        kv = _kamerverhuur_per_buurt().get(buurt)
        r_kv = _kamerverhuur_rang().get(buurt)
        if r_kv:
            d.append(f"bekende kamerverhuurpanden als aandeel van de woningen: "
                     f"{r_kv}")
        if kv and kv.get("totaal"):
            d.append(f"{kv['totaal']} bekende kamerverhuurpanden (vergunning of "
                     f"melding brandveilig gebruik; {kv.get('beide', 0)} met beide, "
                     f"{kv.get('alleen_melding_of_besluit', 0)} alleen via een melding "
                     f"of besluit). Dit is een ondergrens: boven de WOZ-grens is geen "
                     f"vergunning nodig en meldingen worden pas sinds kort "
                     f"gepubliceerd")
        elif verg.get(buurt):
            d.append(f"{verg[buurt]} vergunningen voor kamerverhuur sinds 2013")

        try:
            rang = _mediaan_rang().get(buurt)
        except Exception:
            rang = None
        if rang:
            d.append(f"prijs per m2: {rang}")

        # Waar ligt de gemiddelde WOZ ten opzichte van de grens van €396.000?
        # Die grens bepaalt de omzettingsvergunning en de opkoopbescherming,
        # dus dit zegt meer dan "hoog" of "laag".
        woz = g.get("woz")
        if woz:
            woz_euro = woz * 1000 if woz < 5000 else woz
            verschil = woz_euro - 396_000
            # Alleen de ligging ten opzichte van de grens. Welk deel van de
            # woningen eronder valt, volgt niet uit een gemiddelde.
            if abs(verschil) <= 25_000:
                ligging = (f"vlak {'boven' if verschil > 0 else 'onder'} de grens "
                           f"van €396.000")
            elif verschil > 0:
                ligging = "boven de grens van €396.000"
            else:
                ligging = "onder de grens van €396.000"
            ligging += (". Dit is een buurtgemiddelde; of een pand onder de "
                        "omzettingsvergunning of de opkoopbescherming valt, hangt "
                        "af van de WOZ van dat pand zelf")
            d.append(f"gemiddelde WOZ €{woz_euro:,.0f}".replace(",", ".")
                     + f", {ligging}")

        for veld, naam in (("inkomen", "gemiddeld inkomen per inwoner"),
                           ("vermogen", "mediaan vermogen per huishouden")):
            r = _veld_rang(veld).get(buurt)
            if r:
                d.append(f"{naam}: {r}")

        # De rangorde per misdrijfsoort, zodat het model niet zelf vergelijkt.
        # Het draaide de vergelijking eerder om.
        for soort, r in _misdrijf_rang().get(buurt, {}).items():
            d.append(f"{soort}: {r}")

        # Wie er woont, wat ze verdienen en bezitten
        if g.get("eenpersoons") is not None:
            d.append(f"{g['eenpersoons']}% van de huishoudens bestaat uit een "
                     f"persoon (dat is een aandeel van de huishoudens, niet van "
                     f"de bewoners)")
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
                d.append(f"misdrijven in {jaren[-1][:4]}, geregistreerd op de "
                         f"plek waar het gebeurde: " + ", ".join(per)
                         + ". Woninginbraak gebeurt bij iemand thuis en zegt het "
                           "meest over de bewoners; bij fietsendiefstal en "
                           "vernieling telt ook mee wie er alleen komt")
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
    # Bekende kamerverhuurpanden uit het register, anders alleen de vergunningen
    kv = (lees_json("kamerverhuur_per_buurt.json") or {}).get("per_buurt", {})
    verg = ({b: v.get("totaal") for b, v in kv.items() if v.get("totaal")}
            or lees_json("vergunningen_per_buurt.json"))
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


# Regels in de gegevens die alleen melden dat er niets is. Het model nam die
# steeds over als opening. Wat er niet is, hoeft de brief niet te weten.
_LEEG = re.compile(
    r"(geen mutaties|geen kernsignalen|\b0 kernsignalen|geen nieuwe publicaties|"
    r"geen nieuwe (panden|besluiten|artikelen)|niets nieuws)", re.I)


def zonder_leegmeldingen(tekst):
    """Haalt zinnen weg die alleen melden dat er niets gebeurde."""
    uit = []
    for regel in tekst.split("\n"):
        zinnen = re.split(r"(?<=[.!?])\s+", regel)
        over = [z for z in zinnen if not _LEEG.search(z)]
        if over:
            uit.append(" ".join(over))
    return "\n".join(uit)


def _weekelijks():
    """Draait deze run de zondagseditie?"""
    return (os.environ.get("MODUS") or "").lower().startswith("week")


def week_terug(soort, datum, dagen=7, maxlen=6000):
    """
    De digests van de afgelopen dagen achter elkaar, met hun datum ervoor.

    De zondagsbrief gaat over de week, maar kreeg alleen de digest van die dag.
    Dan moet het model zich de week herinneren, en dat kan het niet: het ziet
    alleen wat er in de opdracht staat.
    """
    eind = dt.date.fromisoformat(datum)
    stukken = []
    for i in range(dagen - 1, -1, -1):
        d = (eind - dt.timedelta(days=i)).isoformat()
        tekst = zonder_leegmeldingen(strip_opmaak(lees(f"digests/{d}-{soort}.md"), 2000))
        if tekst.strip():
            stukken.append(f"[{d}]\n{tekst}")
    return "\n\n".join(stukken)[:maxlen]


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


def eerste_zin(tekst):
    """De eerste zin na de aanhef."""
    regels = [r.strip() for r in tekst.split("\n") if r.strip()]
    # Aanhef en kop overslaan
    inhoud = [r for r in regels
              if not r.startswith("#") and not re.match(r"^(beste|lieve|hoi)\b",
                                                         r, re.I)]
    if not inhoud:
        return ""
    alinea = inhoud[0]
    zin = re.split(r"(?<=[.!?:])\s", alinea, maxsplit=1)[0]
    return zin.strip()


# Openingen die over een afwezigheid gaan. Bewust op het begin van de zin: dat
# er ergens verderop "geen" staat, is geen probleem.
_AFWEZIG = re.compile(
    r"^(vandaag\s+)?("
    r"(weinig|geen|nauwelijks|amper)\b|"
    r"(het\s+)?(is|was)\s+(het\s+)?(vandaag\s+)?(een\s+)?(rustig|stil|kalm)|"
    r"(is|was)\s+er\s+(vandaag\s+)?(weinig|niets|niks|geen)|"
    r"(een\s+)?(rustige|stille|kalme)\s+(dag|week)|"
    r"er\s+(is|was|gebeurde|gebeurt|kwam|kwamen|stond|stonden|verscheen|lag)\s+"
    r"(vandaag\s+)?(weinig|niets|niks|geen)|"
    r"niets\b|niks\b|stilte\b)", re.I)


# Zinnen die de opbouw van de brief beschrijven in plaats van de inhoud.
_OPBOUW = re.compile(
    r"(dit wordt (dus )?het (onderwerp|hoofdstuk)|"
    r"het onderwerp van (vandaag|de dag)|"
    r"(dus|daarom) (is er|heb ik|geeft dat) (vandaag )?(de )?ruimte|"
    r"er was geen (artikel|besluit|nieuws) om op te toetsen|"
    r"op mijn bureau|de moeite van het uitleggen waard|"
    r"reden genoeg om|staat er (terecht |ook )?bij|"
    r"(verder |overigens )?(is er|was er|valt er) (weinig|niets) (te melden|nieuws)|"
    r"geen (bekendmakingen|prijswijzigingen|mutaties)\b)", re.I)


def opbouwzinnen(tekst):
    """De zinnen die de opbouw beschrijven, zodat ze hersteld kunnen worden."""
    zinnen = re.split(r"(?<=[.!?])\s+", tekst)
    return [z.strip() for z in zinnen if _OPBOUW.search(z)]


def veiligheidszinnen(tekst):
    """Zinnen die fietsendiefstal of vernieling als plus of min voor verhuur brengen."""
    # Ook de zin ervoor bekijken: "Vernieling is hier laag. Voor verhuur is dat
    # een pluspunt." noemt het cijfer in de ene zin en de conclusie in de andere.
    zinnen = [z.strip() for z in re.split(r"(?<=[.!?])\s+", tekst)]
    oordeel = re.compile(r"pluspunt|minpunt|prettig|aantrekkelijk|voor verhuur|"
                         r"voor een huurder|voordeel|nadeel", re.I)
    cijfer = re.compile(r"fietsendiefstal|vernieling", re.I)
    uit = []
    for i, z in enumerate(zinnen):
        vorige = zinnen[i - 1] if i else ""
        if oordeel.search(z) and (cijfer.search(z) or cijfer.search(vorige)):
            uit.append(z)
    return uit


# Ruimtelijke beweringen die niet uit een adres volgen, en regels per pand die
# uit een buurtgemiddelde worden afgeleid.
_VERBAND_RUIMTE = re.compile(r"\b(even |iets |wat )?verderop\b|om de hoek|"
                             r"in dezelfde straat|een paar straten|vlakbij|"
                             r"naast elkaar in de straat", re.I)
_VERBAND_REGEL = re.compile(r"omzettingsvergunning|opkoopbescherming|vergunningplicht",
                            re.I)
_VERBAND_VEEL = re.compile(r"\b(meestal|doorgaans|vaak|zelden|in de regel|"
                           r"de meeste|merendeel|kans)\b", re.I)


def verbandzinnen(tekst):
    """Zinnen met een verband dat niet uit de gegevens volgt."""
    uit = []
    for z in (z.strip() for z in re.split(r"(?<=[.!?])\s+", tekst)):
        if _VERBAND_RUIMTE.search(z):
            uit.append((z, "een ruimtelijke bewering die niet uit de adressen volgt"))
        elif _VERBAND_REGEL.search(z) and _VERBAND_VEEL.search(z):
            uit.append((z, "een uitspraak over hoe vaak een regel geldt, afgeleid uit "
                           "een buurtgemiddelde; de regel hangt aan de WOZ per pand"))
    return uit


def opent_met_afwezigheid(zin):
    """Gaat deze openingszin over wat er niet is?"""
    return bool(_AFWEZIG.search(zin.strip())) if zin else False


def schrijf_brief(bronnen):
    if not ANTHROPIC_API_KEY:
        print("Geen ANTHROPIC_API_KEY", file=sys.stderr)
        return ""
    inhoud = "\n\n".join(f"=== {naam} ===\n{zonder_leegmeldingen(tekst)}"
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

    # De zondagseditie is een andere brief: kort, het belangrijkste van de week,
    # en in de bijlage een uitgewerkte case. Geen buurtportret, geen vast
    # rentekopje, geen rondje langs alles.
    if _weekelijks():
        woorden = 500
        sturing = (
            "Dit is de zondagseditie. Houd het kort: hooguit 500 woorden. Schrijf "
            "het belangrijkste van de afgelopen week, niet van vandaag. Betreft het "
            "losse onderwerpen, gebruik dan korte kopjes boven elk onderdeel; hoort "
            "het bij elkaar, dan doorlopende tekst. Laat weg: het portret van een "
            "buurt, het rondje langs de buurten, en een apart kopje over de rente. "
            "Noem de rente alleen als die deze week is veranderd, en dan in een "
            "halve zin in de lopende tekst. De uitgewerkte investeringscase staat "
            "in de bijlage; verwijs er hooguit een zin naar en herhaal de "
            "berekening niet. De besluiten en het nieuws krijg je van de hele "
            "week, met de datum per dag erbij; gebruik die datums en schrijf niet "
            "alsof alles vandaag gebeurde."
        )

    # Een nieuw pand is actualiteit, ook op een dag met weinig ander nieuws.
    # Eerder zei de sturing op zo'n dag "maak van de verdieping het hoofdstuk",
    # en schoof de brief een nieuw pand 36% onder de mediaan opzij.
    alle_tekst = " ".join(t for _n, t in bronnen if t)
    if "haalt de drempel om de brief mee te openen" in alle_tekst:
        sturing += (" Er staat vandaag een nieuw pand in de gegevens dat de drempel "
                    "haalt: de richtprijs ligt dicht bij de vraagprijs. Is er geen "
                    "gemeentelijk besluit of artikel dat de hele portefeuille raakt, "
                    "open dan met dit pand.")
    elif re.search(r"\b\d+ nieuw of gewijzigd\b", alle_tekst):
        sturing += (" Er is wel nieuw aanbod, maar geen pand dat de drempel haalt. "
                    "Noem het kort en open met het belangrijkste besluit, bericht "
                    "of onderwerp.")
    print(f"Nieuwswaarde vandaag: {punten} punten, ruimte {woorden} woorden",
          file=sys.stderr)

    prompt = (f"DATUM VAN VANDAAG: {dt.date.today().isoformat()}\n"
              f"AANHEF: {AANHEF}\n"
              f"BUURT VAN DE DAG: {buurt_vandaag}\n"
              f"MAXIMUM: {woorden} woorden. Dat is een harde grens, geen streven. "
              f"Ga er niet overheen; schrap liever een onderwerp dan dat je alles "
              f"half behandelt.\n"
              f"NADRUK VANDAAG: {sturing}\n\n"
              f"GEGEVENS VAN VANDAAG:\n\n{inhoud}\n\n"
              f"Schrijf de brief. Alleen de brieftekst, niets eromheen.")
    tekst = _vraag([{"role": "user", "content": prompt}], woorden)
    if not tekst:
        return ""

    # De opening controleren. Een instructie is geen garantie: ondanks de
    # regel in hoofdletters opende de brief herhaaldelijk met "vandaag weinig
    # beweging". Dus controleert het script het, en krijgt het model een keer
    # de kans het te herstellen, met de foute zin erbij.
    # Controleren na het schrijven, want een instructie is geen garantie.
    # Twee dingen: een opening over wat er niet is, en zinnen die de opbouw van
    # de brief beschrijven. Beide in een herstelronde.
    problemen = []
    eerste = eerste_zin(tekst)
    if opent_met_afwezigheid(eerste):
        problemen.append(f"Je eerste zin na de aanhef is: \"{eerste}\". Die gaat "
                         f"over wat er niet is gebeurd. Laat de brief beginnen bij "
                         f"het onderwerp; dat er weinig beweging was mag hooguit "
                         f"later terloops.")
    for zin, waarom in verbandzinnen(tekst):
        problemen.append(f"Deze zin bevat {waarom}: \"{zin}\". Haal dat deel weg of "
                         f"maak het concreet met wat er in de gegevens staat.")
    for zin in veiligheidszinnen(tekst):
        problemen.append(f"Deze zin gebruikt fietsendiefstal of vernieling als maat "
                         f"voor hoe prettig een buurt is voor verhuur: \"{zin}\". "
                         f"Bij die cijfers telt ook mee wie er alleen langskomt. "
                         f"Haal die conclusie weg; woninginbraak mag wel.")
    for zin in opbouwzinnen(tekst):
        problemen.append(f"Deze zin beschrijft de opbouw van de brief: \"{zin}\". "
                         f"Haal dat deel weg; je vader leest een brief, geen "
                         f"verantwoording.")
    if problemen:
        print(f"Herstelronde voor {len(problemen)} punt(en)", file=sys.stderr)
        correctie = ("\n\n".join(problemen)
                     + "\n\nPas alleen deze zinnen aan en laat de rest van de brief "
                       "zo veel mogelijk staan. Geef de volledige brief terug, "
                       "niets eromheen.")
        herschreven = _vraag([{"role": "user", "content": prompt},
                              {"role": "assistant", "content": tekst},
                              {"role": "user", "content": correctie}], woorden)
        if (herschreven and not opent_met_afwezigheid(eerste_zin(herschreven))
                and not opbouwzinnen(herschreven)
                and not veiligheidszinnen(herschreven)
                and not verbandzinnen(herschreven)):
            print("  hersteld", file=sys.stderr)
            tekst = herschreven
        elif herschreven and len(opbouwzinnen(herschreven)) < len(opbouwzinnen(tekst)):
            print("  deels hersteld", file=sys.stderr)
            tekst = herschreven
        else:
            print("  herstel lukte niet; de eerste versie blijft staan",
                  file=sys.stderr)
    return tekst


def _vraag(berichten, woorden):
    """
    Een aanroep naar het model, met drie pogingen.

    Een lange brief schrijven duurt; twee minuten was te krap. Drie pogingen
    met ruime wachttijd, want dit is de enige stap die de brief oplevert.
    """
    resp = None
    for poging in range(1, 4):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 16000, "system": PROFIEL,
                      "messages": berichten},
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
        ("Dossiers per pand", strip_opmaak(lees(f"digests/{d}-dossiers.md"), 9000)),
        ("Gemeentelijke besluiten",
         week_terug("bekendmakingen", d) if _weekelijks()
         else strip_opmaak(lees(f"digests/{d}-bekendmakingen.md"))),
        ("Nieuws",
         week_terug("publicaties", d) if _weekelijks()
         else strip_opmaak(lees(f"digests/{d}-publicaties.md"), 6000)),
        ("Rente", strip_opmaak(lees(f"digests/{d}-rente.md"), 3000)),
        ("Bouwkosten", bouwkosten_tekst()),
        ("Woningprijzen CBS", woningprijzen_tekst()),
        ("Stadsbegroting Nijmegen", strip_opmaak(lees(f"digests/{d}-begroting.md"), 3000)),
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
    # Het weetje is een toegift. Faalt het, dan komt de brief er toch.
    try:
        weetje = weetje_van_de_dag()
    except Exception as e:
        print(f"Weetje overgeslagen door een fout: {e}", file=sys.stderr)
        weetje = ""

    # Staat het weetje al in de brief, dan is het geen toegift maar herhaling.
    # We vergelijken op de getallen: komen die allemaal al in de brief voor,
    # dan laten we het weetje vandaag weg.
    if weetje and brief:
        getallen = re.findall(r"\d+(?:[.,]\d+)?", weetje)
        # Ook zonder getal kan het dubbel zijn: "vernieling is in Galgenveld het
        # laagst" in de brief, en "Galgenveld scoort het laagst op vernieling" in
        # het weetje. Dan staan de buurt en het onderwerp in dezelfde zin.
        onderwerpen = ("vernieling", "fietsendiefstal", "woninginbraak",
                       "inkomen", "vermogen", "studenten", "koop", "corporatie",
                       "kinderen", "alleen", "vergunning")
        buurten_w = [b for b in ("Stadscentrum", "Benedenstad", "Bottendaal",
                                 "Galgenveld", "Altrade", "Biezen") if b in weetje]
        onderw_w = [o for o in onderwerpen if o in weetje.lower()]
        zelfde_zin = any(
            all(b in z for b in buurten_w) and all(o in z.lower() for o in onderw_w)
            for z in re.split(r"(?<=[.!?])\s+", brief)
        ) if buurten_w and onderw_w else False
        if (getallen and all(g in brief for g in getallen)) or zelfde_zin:
            print(f"Weetje weggelaten, staat al in de brief: {weetje[:60]}",
                  file=sys.stderr)
            weetje = ""
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
