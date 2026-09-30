# Verbeterlijst Nijmegen-vastgoedbrief

Wat we nog willen bouwen, en waarom. Geen planning maar een geheugen: ideeën
verdwijnen anders tussen twee sessies in.

Peildatum: 17 september 2026.

---

## 1. Toetsen of het nieuws klopt met de openbare data

**Het idee.** Een artikel schrijft iets over de markt. Wij hebben de
onderliggende cijfers. Klopt wat er staat?

Dit is de meest eigen bijdrage die de brief kan leveren. Een vakblad schrijft
over de landelijke woningmarkt; wij weten wat er in deze zes buurten gebeurt.
Wijkt dat af, dan is dát het bericht.

**Les uit de eerste toepassing, 17 september 2026.** De brief legde een
renteartikel naast onze eigen cijfers en concludeerde dat de voorspelde
stijging niet zichtbaar was. Dat klopte niet: de vergelijking liep tegen de
stand van gisteren, terwijl de rente over de maanden ervoor wel degelijk fors
was opgelopen.

Een toets is alleen geldig over een passende periode. Bij rente en prijzen
betekent dat maanden, niet dagen. Daarom levert het rentescript nu een
terugblik over een maand, een kwartaal en een jaar, en staat in de opdracht dat
er zonder zo'n reeks geen conclusie over een trend getrokken mag worden.

**Voorbeelden van wat zo'n toets zou opleveren:**
- "Woningprijzen stijgen verder in 2026" tegenover onze eigen prijstrend per
  buurt. Zien wij die stijging ook, of juist niet?
- "De uitpondgolf zet door" tegenover het aantal panden dat in verhuurde staat
  wordt aangeboden in onze ring.
- "Tekort aan studentenwoningen daalt" tegenover het aantal
  kamerverhuurvergunningen dat Nijmegen verleent.
- Een makelaar die schrijft dat een buurt in trek is, tegenover het aantal
  dagen dat panden daar in aanbod staan.

**Hoe het zou werken.** Bij een artikel met een toetsbare bewering zoekt het
script de eigen cijfers erbij en zet ze ernaast. Komt het overeen, dan een
bevestiging in één zin. Wijkt het af, dan is dat een eigen bevinding.

**Wat er nog voor nodig is.** Het model moet herkennen welke bewering
toetsbaar is, en welke eigen reeks daarbij hoort. Dat is een koppeling tussen
trefwoorden en onze eigen gegevens.

---

## 2. Terugkijken op de eigen voorspellingen

**Het probleem.** De brief doet elke dag uitspraken: deze richtprijs, deze
huur, dit rendement. Niemand toetst ooit of dat klopte. Het systeem verzamelt
wel, maar leert niet.

**Wat ervoor nodig is.** Bijhouden welke panden uit het aanbod verdwijnen. Een
pand dat weg is en niet verlaagd was, is vermoedelijk verkocht. Dan kun je onze
richtprijs naast de werkelijke transactieprijs leggen, via het Kadaster voor
€1,50 per adres.

**Wat het oplevert.** Na twintig vergelijkingen weet je of het model
structureel te hoog of te laag zit. Dan stel je de aannames bij op meting in
plaats van op vuistregels. Dat is het verschil tussen accumuleren en leren.

**Wanneer het kan.** Pas als er genoeg panden zijn verdwenen. Een paar maanden
draaien is het minimum.

---

## 3. De onderwerpenlijst die zichzelf aanvult — GEBOUWD 17 september 2026

**Wat er werkt.** Wekelijks doorzoekt het script de digests en het
bekendmakingen-archief op namen van wetten, besluiten en regelingen. Komt een
term vier keer of vaker terug en hebben we er geen achtergrondstuk over, dan
komt hij in onderwerpen_voorstel.md met de context erbij.

Namen van wetgeving zijn consistent geschreven, dus die zijn betrouwbaar te
herkennen. Werkwoorden die achter de naam plakken worden eraf geknipt, anders
telt dezelfde wet als vier verschillende termen.

**Wat het bewust niet doet: de tekst schrijven.** Een model dat zijn eigen
naslagwerk maakt over fiscaal of juridisch terrein produceert met evenveel
stelligheid iets wat niet klopt. Deze week gebeurde dat drie keer: bij de
leefbaarheidstoets, bij de overdrachtsbelasting en bij de renteconclusie. Het
systeem signaleert het gat en levert de bron; wij schrijven het stuk.

**De lus is rond.** Een gesignaleerde term komt in onderwerpen_volgen.json, en
publicaties_vastgoed.py maakt daar een eigen zoekopdracht van. Vanaf dezelfde
run wordt er dus gericht naar artikelen over die term gezocht, en komen die door
de trefwoordfilter heen. De signaalstap draait vóór het ophalen van de
publicaties, anders zou een nieuwe term pas een week later meelopen.

Termen die een half jaar niet meer in het nieuws zijn geweest, vallen vanzelf
af. Anders groeit het aantal zoekopdrachten eindeloos.

**Drie bewakingen dat het bij het vak blijft:**

1. Een term telt alleen als er een vakwoord omheen staat: huur, verhuur,
   vergunning, splitsen, belasting, energielabel en zo. Daarmee vallen
   "Besluit standplaatsen woonwagens" en "Wet maatschappelijke ondersteuning"
   er vanzelf uit, zonder dat we ze bij naam hoeven te kennen.
2. Voorstellen landen uitgecommentarieerd in onderwerpen_volgen.txt. Pas als
   Mark het hekje weghaalt, wordt de term gevolgd. Het script voegt alleen
   onderaan toe en verandert nooit iets aan wat er staat.
3. Een goedgekeurde term die een half jaar niet meer in het nieuws is geweest,
   valt vanzelf af. En terugzetten naar voorstel kan altijd door het hekje
   terug te plaatsen.

**Wat er dus wel en niet automatisch gaat:**
- automatisch: herkennen dat een term terugkeert en voorstellen hem te volgen
- Marks keuze: welke voorstellen worden aangenomen
- handwerk: het achtergrondstuk dat uitlegt hoe de regel werkt

**Nog te doen:** de wetstekst zelf erbij halen via de regelgevingsmonitor, zodat
er bij het voorstel niet alleen een krantenzin staat maar ook de bron.

---

## 3b. Een geheugen voor gemaakte correcties

**Het probleem.** Als er iets fout blijkt, repareren we het en vergeet het
systeem het. Er is geen plek waar staat wat er ooit misging.

De lijst van deze week alleen al:
- BAG-oppervlakte die het hele pand gaf in plaats van de eenheid
- prijswijzigingen die er geen waren, doordat huur- en koopadvertenties van
  hetzelfde pand werden samengevoegd
- een percentage zonder label dat als prijsverlaging werd gelezen
- misdrijfsoorten die overal nul waren en toch als nul werden getoond
- bouwjaar als tekst waar een getal werd verwacht

**Wat het zou zijn.** Een bestand met toetsen die bij elke run draaien, zodat
een fout die we ooit hebben gemaakt niet terug kan komen. Niet de reparatie
zelf, maar de controle erop.

---

## 4. De brief om actualiteit bouwen, niet om de buurten

**De aanleiding.** Zowel Mark als zijn vader leest vaak hetzelfde. De brief is
opgezet als een rondje langs zes buurten, en dan moet er over elke buurt iets
staan, ook als er niets is. "Geen mutaties" wordt dan het nieuws.

**De andere opzet.** Beginnen bij wat er werkelijk speelt. Is dat een
gemeentelijk besluit, dan gaat de brief daarover. Is het een artikel dat
schuurt met onze eigen cijfers, dan daarover. Zijn er nieuwe panden, dan
daarover. Is er niets, dan is de brief kort.

De buurtportretten blijven, maar als achtergrond bij het nieuws van die dag en
niet als vaste rubriek.

**Wat Mark het liefst leest:** de gemeentelijke updates met een brede
onderbouwing uit de openbare gegevens. Dat is de kern waar de brief omheen
gebouwd zou moeten worden.

---

## 5. De brief als analyse in plaats van een overzicht — GEBOUWD 17 september 2026

**De opzet.** Inleiding met de actualiteit, dan een aanleiding, dan de analyse
vanuit meerdere bronnen, en een conclusie. Dat is de klassieke vorm van een
achtergrondstuk: in het recht IRAC, in beleid een memo.

**Wat er nu werkt.** Het achtergrondstuk rouleert niet meer op datum maar wordt
gekozen op aansluiting bij het nieuws van die dag. Bericht over box 3 levert het
stuk over vennootschapsbelasting op, een splitsingsbesluit het stuk over
splitsen in Nijmegen. Het gaat mee de brief in als materiaal, niet als los
blokje eronder.

In de opdracht staat dat een onderwerp dat van meerdere kanten komt, dus zowel
in de pers als bij de gemeente, het hoofdstuk van de brief wordt: wat zegt het
nieuws, wat zeggen onze cijfers, wat zegt de regelgeving, wat betekent het.

**Hoe de lengte meebeweegt.** Het script telt hoeveel er te melden valt:
kernsignalen, splitsings- en kamerverhuurberichten, prijswijzigingen, nieuwe
panden en artikelen. Daar rolt een schrijfruimte uit.

- Twaalf punten of meer: 800 woorden, actualiteit vult de brief, verdieping is
  een alinea.
- Vijf tot elf: 700 woorden, actualiteit plus een echte verdieping.
- Onder de vijf: 600 woorden, en dan wordt de verdieping het hoofdstuk.

Het maximum is een harde grens en geen streven. Gaat het model er meer dan
twintig procent overheen, dan staat dat in de log.

**De onderwerpen** zijn uitgebreid tot zeventien, waaronder de Wet goed
verhuurderschap, de risico's van verkameren en de relatie tussen veiligheid en
verhuurbaarheid. Elk met trefwoorden, zodat het stuk aansluit bij het nieuws.

---

## 5b. Frequentie heroverwegen

Als er op een dag niets gebeurt, is een brief sturen misschien niet nodig.
Alternatieven:

- Alleen sturen bij een aanleiding: nieuw aanbod, prijswijziging, gemeentelijk
  besluit of een artikel dat schuurt met de cijfers. Anders niets.
- Twee vaste dagen per week plus een extra bericht zodra er iets belangrijks is.
- Dagelijks blijven sturen maar met een harde ondergrens: onder een bepaalde
  hoeveelheid nieuws wordt het een berichtje van vijf regels.

Te bespreken. Het hangt ervan af of de dagelijkse gewoonte waarde heeft op
zichzelf, los van de inhoud.

---

## 6. Voorvallen op adresniveau

**Gebouwd op 17 september 2026.** De misdrijfcijfers van het CBS zijn
jaartotalen per buurt; daar hoort geen publicatie bij. Wat er nu naast ligt is
een laag op adresniveau: berichten van de politie en de regionale pers over
voorvallen in de straten die we volgen.

Het script haalt de straatnamen uit verkopen.txt en zet een bericht dat een van
die straten noemt bovenaan de publicaties, ook als er geen vastgoedterm in
staat. Een brand of een woningsluiting raakt het pand, ongeacht de woordkeus.

**Nog te doen:** ook de straten uit de eigen portefeuille meenemen, en de
melding koppelen aan het handhavingsarchief zodat een sluiting op grond van de
Opiumwet zichtbaar wordt bij het pand zelf.

---

## 7. Afstand tot het OV per object — GEBOUWD 17 september 2026

**Hoe het werkt.** Eerst hemelsbreed de drie dichtstbijzijnde haltes zoeken,
wat niets kost. Dan alleen voor die drie de werkelijke looproute opvragen bij
OSRM. Dat is een bevraging per pand in plaats van per halte, en het resultaat
wordt bewaard want een pand verhuist niet.

Haltes komen uit OpenStreetMap via Overpass en worden eens per jaar opgehaald.
Lukt de routering niet, dan valt het terug op de rechte lijn maal 1,35.

**Wat het extra oplevert.** Is de looproute meer dan twee keer de rechte lijn,
dan meldt de brief dat er een barriere is. In Nijmegen is dat meestal het spoor
of een hoogteverschil van de stuwwal.

**Nog te doen:** de looptijd meewegen in het scenario, want bij kamerverhuur aan
studenten telt de afstand tot de campus zwaarder dan tot de dichtstbijzijnde
bushalte.

**Wat er daarvoor lag.** Per buurt de gemiddelde afstand tot een treinstation,
supermarkt en huisarts, uit de Kerncijfers wijken en buurten. Plus de
gemiddelde leeftijd, berekend uit de leeftijdsgroepen die het CBS wel levert.

**Wat er nog niet is.** Afstand tot de dichtstbijzijnde bus- of tramhalte per
adres. Daarvoor is een bestand met haltecoördinaten nodig; wij hebben wel de
coordinaten van elk pand via PDOK, maar geen haltebestand.

**Mogelijke bronnen om te onderzoeken:**
- NDOV of OVapi, die haltegegevens als open data publiceren
- OpenStreetMap via Overpass, met de tags highway=bus_stop en railway=tram_stop
- PDOK, mocht daar een halteset in staan

**Waarom het de moeite waard is.** Bij kamerverhuur en kleine eenheden verhuur
je aan mensen zonder auto. De afstand tot een halte bepaalt dan mede de
verhuurbaarheid, en in Nijmegen is dat zeker relevant richting de campus. Het
buurtgemiddelde is daarvoor te grof: binnen Galgenveld scheelt het of je aan de
Sint Annastraat zit of aan de rand.

---

## 7b. Leesbaarheid van de brief — bijgesteld 18 september 2026

**Het probleem.** De verdieping werd inhoudelijk goed maar taalkundig zwaar:
lange zinnen, gestapelde bijzinnen, vaktermen zonder uitleg.

**De regel die nu in de opdracht staat:** schrijf eenvoudig, niet simpel. Het
onderwerp mag ingewikkeld zijn, de zinnen niet. Eén gedachte per zin, een
vakterm uitleggen bij de eerste keer, en een alinea beginnen bij de hoofdzaak.
Het niveau blijft; de zinsbouw gaat omlaag.

**Panden worden nu geintroduceerd.** Een pand dook op als "het
Krayenhofflaan-pand" zonder dat de lezer wist wat dat was. Nu moet de eerste
vermelding het adres, de vraagprijs, de oppervlakte en het aantal dagen te koop
bevatten. Daarvoor staat "Dagen te koop" nu ook in de bijlagetabel.

**En een fout die eruit is.** De brief schreef "operationeel resultaat van
€4.665 per maand" waar per jaar bedoeld was. De kolom in de bijlage had geen
eenheid, dus het model koos er zelf een. Beide tabellen dragen nu hun eenheid
in de kop, en in de opdracht staat dat een bedrag zonder eenheid ook zonder
eenheid genoemd wordt.

---

## 7c. De zondagsbijlage was leeg — hersteld 20 september 2026

**Wat er misging.** Toen de bijlage een tabellenversie werd, ging de mail die
gebruiken in plaats van de volledige werkbrief. Die tabellenversie is in beide
modi hetzelfde, dus alles wat zondag extra is viel weg: de investeringscases,
de referentietabellen, de beleggingslijst, de regelgevingsmonitor en het
onderwerpenvoorstel.

De zondagsbrief van 20 september was daardoor inhoudelijk een dagelijkse brief.

**Nu:** doordeweeks de tabellen, op zondag de volledige werkbrief. De
inleidende zin bij de bijlage beweegt mee.

**De les.** Bij een wijziging die één modus raakt, allebei de modi nalopen. Ik
had de tabellenbijlage doordeweeks getest en aangenomen dat zondag vanzelf goed
ging.

---

## 7d. Twee inhoudelijke fouten in de brief van 21 september

**Eigen woning en verhuurd vastgoed vermengd.** De brief las een artikel over
het eigenwoningforfait en de hypotheekrenteaftrek, en concludeerde dat dit
"voor verhuurd vastgoed geen eenrichtingsverkeer" was. Die regels gelden alleen
voor de woning waar je zelf woont. Voor panden in een BV bestaan ze niet. In de
opdracht staat nu expliciet welke regels bij welk regime horen.

Dit is het gevaarlijkste soort fout: grammaticaal en logisch overtuigend, maar
fiscaal onjuist, en gericht aan iemand die er op kan handelen.

**Een vergelijking die niet klopte.** Bottendaal zou tussen Stadscentrum en
Altrade liggen, terwijl het onder allebei lag. Het model vergelijkt getallen
niet betrouwbaar. De rangorde wordt nu door het script berekend en meegegeven,
zodat het model niet zelf hoeft te vergelijken.

**Het patroon achter beide.** Waar het model zelf moet redeneren over een
getal of een regel, gaat het soms mis. Waar het script het vooraf uitrekent of
vastlegt, gaat het goed. Dat pleit voor meer voorbewerking en minder vrije
interpretatie, zeker bij fiscale en rekenkundige uitspraken.

---

## 7e. De ECB-koppeling werkte niet — hersteld 21 september 2026

Het rentescript probeerde de tienjaars AAA-staatsrente van de eurozone op te
halen bij het ECB Data Portal, maar kreeg telkens een 403. Nu probeert het drie
vraagvormen achter elkaar en meldt het in de log welke werkte, of waarom ze
allemaal faalden.

**Waarom het ertoe doet.** Banken zetten hun hypotheekrente als opslag bovenop
deze kapitaalmarktrente. Die beweegt eerst, de hypotheekrente volgt weken later.
De rente staat nu ook bij stilstand in de brief, met de opslag die banken
rekenen.

**Waarom geen Fed.** De Nederlandse hypotheekrente volgt de eurozone. De Fed
werkt hooguit indirect door via de wereldwijde obligatiemarkt. Dat nieuws-
berichten de Fed noemen maakt hem nog geen goede graadmeter voor Nijmegen.

**Nog te doen:** de kapitaalmarktrente ook over een maand bijhouden, zodat de
brief kan zeggen dat die al is opgelopen terwijl banken nog niet volgden. Dat is
de eigenlijke vooruitblik.

---

## 7f. De huurbron lag stil — hersteld 21 september 2026

**Het grootste probleem van de hele opzet.** Pararius-mails werden sinds de
opmaak veranderde niet meer uitgelezen: "4 nieuwe huurwoningen, 0 objecten
herkend". Pararius zet boven de postcode nu alleen de straatnaam in plaats van
"Appartement Straatnaam", en de oppervlakte staat op een regel met kamers en
bouwjaar in plaats van los.

Daardoor rekende elke case met "huur per m2: €20 (AANNAME, er is nog geen
huurdata verzameld)". Elke richtprijs in de brief rustte op een aanname, niet
omdat er geen data was maar omdat de parser hem niet las.

Gemeubileerde woningen worden nu bewust overgeslagen: daar zit de inrichting in
de huur, en dat vertekent de prijs per m2 naar boven. "Gestoffeerd of
gemeubileerd" telt wel mee, want dan kiest de huurder.

**Wat er meteen uitkwam:** 33 m2 in de Priemstraat voor €37,88 per m2, 135 m2
in de Kievitstraat voor €11,74. Ruim drie keer verschil, waar het model een
vlakke €20 aannam.

---

## 7g. Stand van de externe koppelingen, 21 september 2026

Werkt aantoonbaar, gezien in de logs: Funda, BAG, EP-Online, PDOK buurtkaart
2024, CBS misdrijven, financieren.nl, officiële bekendmakingen, Staatsblad,
Google News, Overpass, OSRM.

Gerepareerd deze week, nog te bevestigen in een echte run: Pararius, ECB,
CBS bouwkostenindex, PDOK oudere jaargang, vergunningen per buurt.

Nooit bevestigd: CVDR en Basiswettenbestand in de regelgevingsmonitor, Kamernet
en Vendr. Die draaien, maar ik heb geen log gezien waarin ze iets opleverden.

---

## 7h. Zelfherstel binnen regels, met controlespoor — 21 september 2026

**De opzet.** Waar een bron van naam verandert, zoekt het script zelf een
alternatief, maar alleen binnen een strikte regel: het veld moet bepaalde
woorden bevatten en andere juist niet. Elke automatische keuze komt als
[CONTROLEER] in het gezondheidsrapport, ook als het onderdeel groen is.

**Het bewijs dat dat nodig is.** In de eerste run met deze opzet koos het script
vier velden zelf. Drie waren goed. Het vierde was de afstand tot de
buitenschoolse opvang, gekozen als afstand tot een school, omdat
"buitenschoolse" het woord school bevat. Zonder de controleregel was dat als
schoolafstand in de brief gekomen: geen fout, wel een verkeerd getal.

De bevestigde CBS-namen staan nu vast in de code, zodat er niets meer te raden
valt. Voor de school eist de regel nu "basis" en sluit hij opvang uit.

**De les.** Een systeem dat zichzelf repareert zonder dat een mens meekijkt,
repareert soms de verkeerde kant op. Aanpassen binnen regels, en elke
aanpassing zichtbaar maken.

---

## 7i. Controleren na het schrijven — 21 september 2026

**De opening.** Ondanks een regel in hoofdletters opende de brief herhaaldelijk
met "vandaag weinig beweging". Nu controleert het script de eerste zin na het
schrijven. Gaat die over een afwezigheid, dan krijgt het model de foute zin
terug met de opdracht alleen de opening te herschrijven. Lukt dat niet, dan
blijft de eerste versie staan; de brief komt er altijd.

**Een verborgen crash.** Het weetje vergeleek velden met een getal, en een leeg
veld gaf None in plaats van nul. Zolang het CBS alles leverde ging dat goed,
maar bij een leeg veld was de hele brief gecrasht, niet alleen het weetje. Nu
telt een leeg veld als nul of wordt overgeslagen, en staat het weetje in een
vangnet: faalt het, dan komt de brief er toch.

**Het patroon van deze week.** Drie keer bleek een instructie aan het model
geen garantie: bij vergelijkingen, bij fiscale regels en bij de opening. Waar
het ertoe doet, moet het script het controleren of vooraf uitrekenen.

---

## 7j. De opkoopbescherming werd per eenheid getoetst — hersteld 22 september 2026

**Wat er fout was.** De splitsingstoets deelde de vraagprijs door het aantal
eenheden en paste de opkoopbescherming per eenheid toe. Dat verborg panden als
de Ruyterstraat 37 (WOZ €514.000) en de Pontanusstraat 19 (WOZ €523.000),
waarvoor splitsen wel een open route is.

**Wat de verordening zegt.** Artikel 19 Huisvestingsverordening Nijmegen 2024:
beschermd is een woonruimte waarvan de WOZ op de datum van inschrijving van de
akte van levering niet meer dan €396.000 is en die toen vrij van huur was (of
korter dan zes maanden verhuurd). De toets gaat dus over wat je koopt, op het
moment dat je het koopt. Splitsen na aankoop is geen nieuwe levering aan jou.

**Drie soorten splitsen**, op aanwijzing van Mark:
- juridisch of kadastraal: appartementsrechten, notariele akte, geen
  vergunning in Nijmegen;
- fysiek: woningvorming, geen huisvestingsvergunning, wel omgevingsvergunning;
- verkameren: omzetten naar onzelfstandig, artikel 13 en 15.

**WOZ.** Elke zelfstandige woning is een eigen WOZ-object (artikel 16 Wet WOZ),
ook zonder appartementsrechten. Een verkamerd pand houdt een WOZ, omdat kamers
geen eigen keuken, douche en toilet hebben.

**Wat blijft staan.** Na fysiek splitsen daalt de WOZ per eenheid, en daarmee
het aantal WWS-punten en de maximale huur. Dat is geen verbod maar een
rekenfactor. De eerdere conclusie bij de Pontanusstraat dat splitsen onaantrek-
kelijk is, klopt daarom nog voor de huur, maar niet vanwege de opkoopbescherming.

**Nog na te gaan bij de gemeente.** De Pontanusstraat 19 bestaat feitelijk al
uit twee zelfstandige woonlagen maar heeft een WOZ. Welke WOZ telt bij aankoop
als de gemeente het object later alsnog in tweeen deelt, is een vraag voor de
gemeente.

---

## 7k. Brief van 22 september: vier fouten uit twee bronnen

**Uit mijn eigen achtergrondtekst over verkameren:** de leefbaarheidstoets werd
genoemd zonder te zeggen dat de gemeente hem laat vervallen, en de boete van
€10.000 geldt alleen bij bedrijfsmatige exploitatie (anders €5.000). Tekst
herschreven naar de verordening.

**Uit het model zelf:**
- "geen twee kamerpanden naast elkaar" waar artikel 15 meer dan twee weigert;
- de veiligheidsvergelijking omgedraaid (Bottendaal zou onder Galgenveld
  zitten qua vernieling, het zit er ruim boven);
- een WOZ van €394.000 "torenhoog" genoemd, terwijl die vlak onder de grens van
  €396.000 ligt en dat het eigenlijke punt is;
- de achtergrondtekst toegeschreven aan de gemeente;
- "77% van de bewoners woont alleen" waar het 77% van de huishoudens is.

**Wat eraan gedaan is.** Rangorde per misdrijfsoort en de positie van de WOZ
ten opzichte van de grens worden nu vooraf uitgerekend. Het huishoudenlabel
zegt expliciet dat het een aandeel huishoudens is. En in de opdracht staat dat
het achtergrondstuk van ons is, niet van de gemeente.

---

## 7l. De achtergrondstukken nagelopen tegen de bronnen — 22 september 2026

**Aanleiding.** Drie keer in een week kwam een fout in de brief uit een
achtergrondtekst die uit het geheugen was geschreven. Mark: "Informatie moet
uit de bronnen komen." Alle zeventien stukken zijn daarom naast de bron gelegd.

**Klopte, met aanvullingen:** overdrachtsbelasting (maar de doorverkoopregel
was te simpel), btw-herziening, vennootschapsbelasting, Wet goed
verhuurderschap (30 dagen bij verrekening, vier verrekenbare posten), het
puntenstelsel (143/144/186/187), beschermd stadsgezicht, de registratie van
misdrijven op de plaats van plegen.

**Verwijderd omdat er geen bron voor was:**
- "valt een tot twee procentpunt lager uit" en "het cijfer waarop taxateurs
  vergelijken" (netto aanvangsrendement);
- "boven de zestig punten vlakt de tabel af" en "kleinere kamers brengen per m2
  meer op" (kamers);
- "een eenheid van vijftig m2 haalt die grens zelden" (woningen);
- "de BV is bijna altijd de juiste structuur" (een advies, geen feit);
- "Nijmegen heeft toezichthouders die woningen mogen betreden";
- "je kunt in de akte afspreken dat hij jouw belasting vergoedt";
- "internet" als servicekosten, en "drukken dus niet op je rendement";
- "voor wijzigingen aan het uiterlijk is een omgevingsvergunning nodig"
  (beschermd stadsgezicht; dat staat per adres in het omgevingsplan).

**Omgezet naar eigen aanname:** de rentedekkingseis van 1,25 is geen norm maar
een keuze van deze brief, en staat er nu zo in.

**Nieuw:** elk stuk heeft een bron in ACHTERGROND_BRONNEN, die mee gaat naar de
brief. In de opdracht staat dat het model die bron noemt en zelf geen regels,
bedragen of vuistregels toevoegt.

**Nog niet zelf ingezien:** het intrekkingsbesluit van de leefbaarheidstoets.
Dat is gevonden door de bekendmakingenmonitor; de beleidsregels uit 2021 zelf
zijn wel nagelopen.

---

## 7m. Brief van 22 september, samen beoordeeld

**Wat werkte:** alle getallen over het puntenstelsel klopten en de bron werd
genoemd; per pand in plaats van per buurt; veiligheid op woninginbraak; de
opening bij het onderwerp; de marktrente alleen voor nieuwe aankopen.

**Wat niet klopte:**
- uitspraken over de eigen portefeuille ("onze panden zitten vaak in het
  hogere segment") zonder enig gegeven daarover;
- data omgerekend naar "vorig jaar" en "dit jaar", en daarbij fout: 1 juli
  2024 werd "vorig jaar zomer", 1 januari 2025 werd "sinds dit jaar";
- een kansuitspraak over panden onder de WOZ-grens, tegengesproken door drie
  panden onder de grens in het aanbod van die week; mijn eigen regel met het
  woord "waarschijnlijk" nodigde daartoe uit;
- het weetje herhaalde een getal uit de brief.

**Hersteld:** regels voor de eigen portefeuille en absolute data, de datum van
vandaag bovenaan de opdracht, de regel over buurtgemiddelden zonder
kansuitspraak, en een weetje dat al in de brief staat wordt weggelaten.

---

## 7n. Het puntenstelsel werd niet getoetst bij verhuur als een woning — 22 september 2026

**Aanleiding.** De brief schreef dat het puntenaantal "niet van de WOZ" afhangt.
Mark wees erop dat de WOZ juist een van de zwaarste onderdelen is, naast
oppervlakte en energielabel, en dat die gegevens per pand bekend zijn.

**Wat daaronder lag.** wwso.py rekende de punten al uit, maar alleen in het
splitsscenario werd daarmee de huur begrensd. Een pand dat als een woning werd
doorgerekend, kreeg de markthuur per m2, ook als het volgens de telling in de
middenhuur valt, waar sinds 1 juli 2024 voor nieuwe contracten een wettelijke
maximumhuur geldt. De richtprijs stond daardoor te hoog, juist bij de
goedkopere panden.

**Voorbeeld.** De Ruyterstraat 37 (99 m2, WOZ €514.000): ondergrens 165
punten. Huur van €1.782 naar €1.083 per maand, richtprijs van €372.761 naar
€220.600. De Pontanusstraat 19 (210 punten) blijft vrije sector.

**Nu.** Bij bekende WOZ wordt de huur in het scenario "een woning" begrensd
op het wettelijk maximum. De telling is een ondergrens, want verwarming
ontbreekt en keuken, sanitair en buitenruimte zijn als gewone woning
aangenomen; het maximum is daarmee voorzichtig. Zonder bekende WOZ staat erbij
dat de huur niet is getoetst. De brief krijgt per pand de telling mee.

**Gevolg voor het invoeren van WOZ-waarden.** Hoe meer WOZ-waarden in woz.txt,
hoe meer panden getoetst worden. Zonder WOZ kan de richtprijs te hoog zijn.

---

## 7o. Een kamerpand kreeg een telling als zelfstandige woning — 22 september 2026

De St. Annastraat 28 kreeg 476 punten en het oordeel "vrije sector", terwijl
het pand een vergunning voor kamerverhuur heeft. Per kamer verhuurd geldt het
puntenstelsel voor onzelfstandige woonruimte, en daar geldt altijd een maximale
huur. Het gegeven stond in de vergunningenlijst, maar werd alleen in de
investeringscases gebruikt.

Nu kijken de puntentelling en de keuze van het huurscenario allebei naar de
vergunningenlijst. Een pand met een vergunning voor kamerverhuur krijgt geen
telling als zelfstandige woning en wordt als kamerpand doorgerekend. Een pand
groter dan 150 m2 krijgt die telling evenmin, omdat het script het dan niet
als een huishouden doorrekent.

In de brief ook: een opbouwzin midden in de tekst ("dus dit wordt het
onderwerp van vandaag"), een verzonnen verband ("verderop in dezelfde straat"
voor twee verschillende straten) en een ongefundeerde doorlooptijd. De
controle na het schrijven kijkt nu naar de hele brief, niet alleen de opening.

---

## 7p. Verbanden leggen, met bewijs per schakel — 22 september 2026

**Mark:** verbanden tussen bronnen, vanuit meerdere invalshoeken, maken de
brief relevant; die moeten juist naar voren komen. De regel van 22 september
("geen verzonnen verbanden") ontmoedigde dat te veel.

**Het onderscheid.** Een goed verband is niet een verrassend verband, maar een
waarvan elke schakel in een bron of in onze gegevens staat. Voorbeeld van een
fout verband uit de brief van die dag: de vpb-schijf zou "in een dure buurt
eerder een rol spelen". De schijf geldt voor de totale winst van de BV, niet
per pand of buurt, en een hoge WOZ is geen hoge winst.

**Nu in de opdracht:** zoek verbanden actief, maar elke schakel moet in de
gegevens of een bron staan. Plus: de vpb-schijf geldt voor de BV als geheel;
de ring is zes buurten en niet de stad; het achtergrondstuk is geen nieuws.

**Ook:** rangorde voor inkomen en vermogen vooraf berekend; de opening "er kwam
vandaag geen" wordt herkend; de vergunningopzoeking vindt nu ook een nummer met
lettertoevoeging of een vergunning waarvan de sleutel afwijkt.

**Volgende stap die het meest oplevert:** per pand een dossier dat alle bronnen
al aan elkaar koppelt (bekendmakingen op het adres en in de straat,
vergunningen, WOZ ten opzichte van de grens, puntentelling, buurtrangorde),
elk met de bron erbij. Dan krijgt het model de verbanden aangereikt in plaats
van ze zelf te moeten bedenken.

---

## 7q. De vergunningenlijst is per definitie onvolledig — 22 september 2026

**Mark:** de St. Annastraat 28 staat niet in de lijst, vermoedelijk omdat bij
die WOZ geen vergunning nodig was. Hoe weten we dan of een buurpand kamers
verhuurt?

**Waarom de lijst gaten heeft.** Boven de WOZ-grens van €396.000 is geen
omzettingsvergunning nodig, dus kamerpanden in die klasse staan er nooit in.
Artikel 15 telt feitelijk kamergewijs bewoonde woningen, niet vergunde. De
toets "niet meer dan twee naast elkaar" leunt daardoor op een lijst die juist
de duurdere kamerpanden mist.

**Wat nu is aangevuld.** De melding brandveilig gebruik hangt niet aan de WOZ
maar aan het gebruik: verplicht vanaf vijf verhuurde kamers (Bbl artikel 6.6),
minstens vier weken voor het gebruik, en zaakgebonden. Die meldingen staan in
het bekendmakingenarchief. Het pand zelf wordt nu getoetst op de vergunningen-
lijst en op meldingen en besluiten in het archief; een aanvraag telt niet mee.

**Wat nog steeds ontbreekt:** kamerpanden met drie of vier kamers boven de
WOZ-grens, en meldingen van voor het archief of die niet gepubliceerd zijn.

**Wat het gat het meest zou dichten:** een Woo-verzoek aan de gemeente voor
alle meldingen brandveilig gebruik voor kamergewijze verhuur, zoals eerder
voor de vergunningen. Omdat een melding zaakgebonden is, blijft een oude melding
geldig, en zou zo'n lijst de kamerpanden vanaf vijf kamers vrijwel volledig
dekken.

**Uit de brief van die dag ook hersteld:** de BAG-regel beweerde dat een
"splitsing geregistreerd" was en je die "niet meer hoeft aan te vragen"; de
eigen-vermogensregel gaf een koopsom van €72.640 die eigenlijk "niet haalbaar"
betekende; een vuistregel over de kapitaalmarkt zonder bron; en het weetje
herhaalde de brief in woorden.

---

## 7r. Wat een advertentie wel heeft en de telling mist — 22 september 2026

**Pontanusstraat 40, advertentie op Funda.** Verklaart het verschil tussen 133
en 197 m2: 133 m2 wonen plus 68 m2 overige inpandige ruimte, samen vrijwel de
BAG-oppervlakte. Geen fout, een definitieverschil. De advertentie meldt ook een
VvE die moet worden opgestart, dus het pand is in appartementsrechten gesplitst.

**De advertentie bevat de onderdelen die de puntentelling nu aanneemt:**
verwarming (cv-ketel), sanitair (douche, toilet, wastafel, apart toilet),
buitenruimte (achtertuin 88 m2) en de woon- en overige oppervlakte. Daarmee
wordt een ondergrens een volledige telling.

**Niet automatiseren.** Funda staat geautomatiseerd uitlezen van de site niet
toe. Mogelijke opzet: een bestand pand_details.txt waarin Mark voor panden die
hij serieus bekijkt die gegevens invult, zoals nu met woz.txt.

**Oorzaak van de opening over afwezigheid gevonden:** mijn eigen sturing op
stille dagen zei "Meld dat kort". Die zin is weg, en meldingen dat er niets
gebeurde worden nu uit de gegevens gehaald voordat het model ze ziet.

**Ook:** het weetje noemt geen fietsendiefstal of vernieling per bewoner meer;
de veiligheidsregel zegt niet meer dat het "vooral iets over bezoekers" zegt,
want dat hebben we niet gemeten.

---

## 7s. Kamerverhuurregister en dossiers per pand — GEBOUWD 22 september 2026

**Getest of we de meldingen zelf kunnen ophalen.** Ja, deels: Nijmegen
publiceert meldingen brandveilig gebruik in het gemeenteblad, met adres, datum
en kenmerk. Alle gevonden meldingen zijn van 2025 en 2026. Oudere meldingen
zijn niet gepubliceerd en alleen bij de gemeente op te vragen.

**kamerverhuur_register.py** combineert de vergunningenlijst met meldingen en
besluiten uit het bekendmakingenarchief. Per buurt het aantal bekende
kamerverhuurpanden, uitgesplitst naar alleen vergunning, alleen melding of
besluit, en beide. Een aanvraag en een samenvoeging tellen niet mee. De telling
is een ondergrens en staat zo in de bijlage en in de brief.

Valkuil opgelost: een titel "aan de Pijnboomstraat 19" gaf de straat "de
Pijnboomstraat". Blind "de" weghalen kan niet ("de Ruyterstraat"), dus alleen
als de straat zonder "de" bekend is en met "de" niet.

**Dossiers per pand** (digests/<datum>-dossiers.md): voor de panden die de brief
waarschijnlijk noemt, alle feiten uit alle bronnen met de bron erbij, en
expliciet wat we niet weten. De brief krijgt ze mee als bron voor verbanden.

**Het gezondheidsrapport** toont nu het aantal bekende kamerverhuurpanden en
het aantal meldingen per jaar, zodat de dekking zichtbaar groeit.

**Later aan te vullen:** een Woo-verzoek voor de meldingen van 2008 tot 2024,
als de historie voor een concrete aankoop nodig blijkt. Het register neemt die
dan zonder aanpassing op.

---

## 7t. Eerste run van het register — 22 september 2026

948 adressen met een aanwijzing voor kamerverhuur in heel Nijmegen, alle aan een
buurt gekoppeld. Meldingen per jaar: 2025: 102, 2026: 83, geen enkele eerder.
Dat bevestigt dat Nijmegen meldingen sinds 2025 publiceert. Galgenveld: 71
bekende kamerpanden, waar de vergunningenlijst er 62 had.

**In de brief van die dag:**
- een gemist verband: een artikel over hogere bouwkosten, en de brief schreef
  dat er geen cijfers waren om het te toetsen. De CBS-bouwkostenindex gaat nu mee
  naar de brief;
- "Galgenveld heeft ruimte voor kamerverhuur" op grond van koopaandeel en
  corporatiebezit, een verband zonder schakel;
- fietsendiefstal en vernieling als "pluspunt voor verhuur", tegen de regel in;
- "verder is er weinig te melden" midden in de brief;
- het weetje telde vergunningen in plaats van bekende kamerpanden.

De controle na het schrijven vangt nu ook afwezigheid midden in de brief en
veiligheidsconclusies over fietsendiefstal en vernieling, ook als het cijfer in
de zin ervoor staat.

**Inhoudelijk aangevuld:** voor een pand dat als een woning in de vrije sector
valt, voert verhuur per kamer juist een maximumhuur in. Dat staat nu in het
achtergrondstuk over het puntenstelsel voor kamers.

---

## 7u. Brief van 22 september: goed, op vier verbanden na

**Wat goed ging:** de overdrachtsbelasting correct en met bron, de berekening
klopte, de WOZ-toets per pand, veiligheid op woninginbraak, geen opbouwzinnen.

**Wat niet klopte, alle vier verbanden zonder schakel:** "even verderop" voor
een ander adres; "de omzettingsvergunning is meestal geen obstakel" afgeleid
uit het buurtgemiddelde; een lagere mediaan gebracht als "de prijs daalde",
terwijl er een nieuw pand onder de mediaan bijkwam; en een stroef weetje.

**Hersteld:** de controle na het schrijven vangt nu ruimtelijke beweringen en
uitspraken over hoe vaak een vergunningsregel geldt. De trendregel zegt erbij
dat een verschuiving van de mediaan ook door nieuwe panden komt. Het weetje is
herschreven.

---

## 7v. Drie fouten die ik zelf had veroorzaakt — 22 september 2026

**Splitsen won zonder kosten.** Sinds de maximumhuur ook bij een woning geldt,
koos het script bij kleine woningen van 73 tot 86 m2 "splitsen in 2", omdat dat
tien procent meer maandhuur gaf. De kosten van een tweede keuken, badkamer en
scheiding werden niet meegeteld. Nu kiest het script bij een gewone woning
splitsen alleen als de kosten per extra eenheid zijn ingevuld
(bouwkosten_eigen.txt, regel splitsen-eenheid) en splitsen daarna op richtprijs
wint. Anders blijft het een woning, met het alternatief in het dossier.

**Een nieuw pand werd opzijgeschoven.** Een nieuw pand telt twee punten
nieuwswaarde, en onder de vijf zei de sturing "maak van de verdieping het
hoofdstuk". De Stieltjesstraat 10, nieuw en 36% onder de buurtmediaan, kwam
daardoor niet in de brief. Nu begint de brief bij een nieuw pand.

**De prijsrangorde heeft nooit gewerkt.** _mediaan_rang las prijstrend.json per
buurt, terwijl het bestand per week is opgebouwd. Het rangschikte de weken en
gaf de brief nooit een rangorde. Mijn test gebruikte het verkeerde formaat. Nu
leest het de laatste week, en alle rangordes zijn vastgezet op de zes buurten.

**Les:** een test met zelfgemaakte gegevens bewijst alleen dat de code werkt op
die gegevens. Testgegevens horen het formaat van het echte bestand te volgen.

---

## 7w. Prijsindex bestaande koopwoningen van het CBS — GEBOUWD 23 september 2026

**Aanleiding.** Mark: het CBS meldde dat de huizenprijzen in augustus 0,1% lager
lagen dan een maand eerder, seizoengecorrigeerd, en 3,3% hoger dan een jaar
eerder. Dat wil hij naast de ring zetten.

**woningprijsindex.py** haalt tabel 85773NED (landelijk, per maand) en 85792NED
(per regio, per kwartaal, Nijmegen of anders Gelderland). Kolommen en regio's
worden opgezocht; een kolom met een verandering wordt nooit als indexniveau
gebruikt. Het maandcijfer staat erbij als niet seizoengecorrigeerd, tenzij de
tabel een seizoengecorrigeerde kolom heeft; anders zou de brief een ander
maandcijfer naast het CBS-bericht zetten zonder uitleg.

**De vergelijking met de ring is naast elkaar, niet een op een.** De CBS-index
meet werkelijke verkoopprijzen, gecorrigeerd voor type woning. De ring is de
mediaan van vraagprijzen, die ook verschuift door nieuwe panden. Dat staat in
de tekst die naar de brief gaat, en als regel in de opdracht.

**Nog te bevestigen in de eerste run:** of Nijmegen als eigen regio in 85792NED
staat, en of er een seizoengecorrigeerde kolom is. Het gezondheidsrapport en
de diagnose laten het zien.

---

## 7x. Vraagprijzen naast de CBS-index, met vertraging — 23 september 2026

**Mark:** tussen onze vraagprijzen en de CBS-cijfers zit waarschijnlijk een
verband met vertraging; dat is het monitoren waard.

**Waarom dat klopt:** het CBS telt notaristransacties van het Kadaster. Een
vraagprijs komt eerder: advertentie, koopcontract, levering. Onze reeks zou dus
voor moeten lopen.

**Wat gebouwd is.** marktprijzen_bag.py legt elke run de mediaan van de
vraagprijzen per m2 over de hele ring vast, per maand, in
vraagprijzen_ring.json. woningprijsindex.py bewaart de CBS-maandreeks en
vergelijkt beide op jaar-op-jaar mutatie, bij een vertraging van nul tot zes
maanden. Onder de dertien maanden rekent het niets uit en meldt het alleen hoe
lang de reeks loopt. De uitkomst wordt gebracht als samenhang, niet als bewijs.

**Getest** op een reeks waarin de ring bewust drie maanden vooruitliep: het
script vindt drie maanden.

**Beperking:** Nijmegen staat niet in de regiotabel 85792NED; de run koos
Gelderland, per kwartaal. Voor Nijmegen zelf bestaat alleen een jaarlijkse
gemiddelde verkoopprijs, en het CBS zegt er zelf bij dat een gemiddelde geen
indicator is voor de prijsontwikkeling.

## 7y. Testruns aten het nieuws op

De Stieltjesstraat 10, nieuw en 36% onder de mediaan, bleef twee brieven lang
buiten beeld. Oorzaak: een handmatige testrun schreef het geheugen van geziene
panden bij, waardoor het pand bij de volgende brief niet meer nieuw was. Bij een
run met "alleen naar mij" wordt het geheugen nu niet meer bijgewerkt, en de
maandreeks van vraagprijzen evenmin.

## 7z. Gezien maar niet hersteld, voor de weekbespreking

- "Verder was het rustig" midden in de brief: de controle herkent wel "weinig te
  melden" maar niet deze vorm. Bewust laten staan om niet elke dag een regel toe
  te voegen.
- De afwijking van de buurtmediaan verschilt een procentpunt tussen brief en
  bijlage (16% tegen 17%); vermoedelijk een andere noemer, nog na te gaan.

---

## 7aa. De Stadsbegroting als bron — GEBOUWD 23 september 2026

**Waarom.** De begroting is een raadsstuk en geen bekendmaking, dus de monitor
zag hem niet. De Stadsbegroting 2027 verscheen op 22 september 2026 zonder dat
de brief er iets van merkte, terwijl er €146,9 mln voor Wonen en stedelijke
ontwikkeling in staat en een paragraaf Lokale heffingen.

**begroting_monitor.py** leest nijmegen.begroting-<jaar>.nl, hooguit een keer
per week, en haalt uit de pagina's Lokale heffingen, Grondbeleid,
Investeringen, Wonen en Financieel beeld de zinnen met OZB, rioolheffing,
afvalstoffenheffing, leges, woonfonds, grondprijs, middenhuur en woonlasten.
Alleen wat nieuw is sinds de vorige keer gaat naar de brief. De tekst zegt
erbij dat de tarieven een voornemen zijn; vastgesteld worden ze in de
belastingverordeningen.

**Ook toegevoegd aan regelgeving_monitor.py:** de verordeningen
onroerendezaakbelastingen, rioolheffing, afvalstoffenheffing en leges. Negen
verordeningen in plaats van vijf. Daarmee zien we het voornemen in de begroting
en de vaststelling in de verordening.

**Niet gebouwd:** een koppeling op het raadsinformatiesysteem. De dataset op
data.overheid.nl zegt zelf dat de raadsstukken over meerdere portalen verspreid
staan en noemt alleen een landingspagina. Zonder een ingang die ik heb kunnen
testen, bouw ik hem niet.

**Volgende stap als het werkt:** het OZB-tarief uit de begroting of de
verordening halen als getal, en de gemeentelijke lasten per pand berekenen uit
de WOZ. Dan vervangt een berekend bedrag een deel van de aanname van 20 tot 25
procent exploitatiekosten.

---

## 7bb. Tarieven als getal, en bankramingen — 23 september 2026

**Het OZB-tarief wordt nu als getal uitgelezen** uit de begroting, met drie
voorwaarden: de zin moet zeggen welke heffing het is en voor wie, twee
tegenstrijdige waarden leveren niets op (en een diagnoseregel), en de zin
wordt bewaard als bewijs. Getest op de schrijfwijze van dit jaar, op een
andere schrijfwijze met spatie en het woord waarde, en op meervoud
("voor eigenaren"). Dat laatste ging eerst mis.

**In het dossier per pand** staat nu de berekende gemeentelijke last:
OZB eigenaar uit WOZ maal tarief, plus rioolheffing als die bij de eigenaar
ligt. De afvalstoffenheffing telt niet mee, want dat is een gebruikersheffing
en die betaalt de huurder. Ernaast staat wat de exploitatieaanname van 20 tot
25 procent in euro's is, zodat zichtbaar is welk deel daarvan nu berekend is en
welk deel nog aanname.

**Bankramingen.** ABN AMRO en Rabobank stonden al in de feeds; ik had ze bijna
dubbel toegevoegd. De ABN-zoekterm miste wel de naam Woningmarktmonitor,
waardoor alleen losse sectorberichten binnenkwamen; die is aangevuld. ING is
toegevoegd. In de opdracht staat dat een raming van een bank een verwachting is
van een commerciele partij en naast het CBS-cijfer hoort, niet ervoor in de
plaats.

**Nog na te gaan:** of de rioolheffing in Nijmegen bij de eigenaar of de
gebruiker ligt. Dat staat in de verordening en bepaalt of hij bij onze
exploitatie hoort of bij de servicekosten.

---

## 7cc. Een appartement werd als bijzonder pand gebracht — 24 september 2026

**Mark:** de Castellastraat 15 is gewoon een appartement in een complex, en de
brief doet er vreemd over.

**Klopt, en er zat een fout onder.** Mijn BAG-regel was bedoeld als
waarschuwing bij een pand dat feitelijk is opgedeeld, maar bij een
appartementencomplex leest hij als een vondst. Belangrijker: het script zei dat
verkameren en splitsen "openstaan". Bij een appartement gaat de VvE daarover:
splitsen vraagt wijziging van de splitsingsakte, en kamerverhuur is in veel
splitsingsreglementen aan toestemming gebonden.

**Nu:** vanaf vier woningen in hetzelfde pand geldt het aangeboden object als
appartement. Splitsen en kamers zijn dan geen vrije routes, met die reden
erbij, en de BAG-regel zegt dat een appartement in een complex op zichzelf
niets bijzonders is. Het dossier bevat nu ook de routes met hun reden, want die
bereikten de brief niet.

**Twee andere fouten uit dezelfde brief:**
- "Bij label E tellen de WWS-punten zwaarder" is omgekeerd; een beter label
  geeft meer punten. Als regel toegevoegd.
- "46 bekende kamerverhuurpanden, de laagste van de zes": als aantal onjuist
  (Benedenstad heeft er 15). Er is nu een rangorde per buurt, als aandeel van
  de woningen, met de melding "nagenoeg gelijk aan" als twee buurten vlak bij
  elkaar liggen. Biezen en Benedenstad zitten beide op 0,9%.
- Ook gezien, niet hersteld: het woord "thirteen" midden in een Nederlandse
  zin. Eerste keer dat dit voorkomt; bij herhaling een controle waard.

---

## 7dd. Bijlage gesorteerd op wat telt bij aankoop — 24 september 2026

**Mark:** de bijlage sorteerde op de afwijking van de buurtmediaan, terwijl de
richtprijs ten opzichte van de vraagprijs bepaalt of een pand koopbaar is voor
verhuur.

De tabel is nu gesorteerd op die laatste kolom, aflopend. De mediaanafwijking
blijft als kolom staan, want die zegt of een pand relatief duur in de markt
staat. In de toelichting staat er nu bij dat de richtprijs op aannames rust
(huur, exploitatie, rente) en de mediaanafwijking gemeten is; sorteren op de
richtprijs zet dus de uitkomst van ons model bovenaan.

**Nog open:** in de dagelijkse brief kiest het script het pand voor de opening
nog op "scherpst geprijsd", dus op de mediaanafwijking. Dat past bij die naam,
maar het kan ook de richtprijs worden.

**Opgelost op 24 september:** de dagelijkse brief kiest het pand voor de
opening nu ook op de richtprijs, en een besluit of artikel gaat voor.

## 7ee. Volgorde van de opening vastgelegd — 24 september 2026

**Mark:** een belangrijk artikel of een gemeentelijke bekendmaking hoort voor
te gaan op een nieuw pand, tenzij dat pand echt interessant is.

**De volgorde in de opdracht:** eerst een besluit of regelwijziging die de hele
portefeuille raakt, dan een bericht dat schuurt met onze cijfers, dan een nieuw
pand, en anders het onderwerp van de verdieping. Met de reden erbij: een besluit
raakt alles wat er staat, een pand alleen dat adres.

**"Interessant" is een gemeten drempel**, geen oordeel van het model. Het
script markeert een nieuw pand als de richtprijs binnen tien procent van de
vraagprijs ligt (DREMPEL_INTERESSANT in marktprijzen_bag.py, een keuze die op
een plek staat). Haalt geen pand die drempel, dan zegt de sturing dat het
aanbod kort genoemd wordt en de brief met iets anders opent.

**Ook aangepast:** de digest noemt niet meer het "scherpst geprijsde" pand maar
het pand dat het dichtst bij haalbaar is, met beide getallen erbij: de ruimte
ten opzichte van de vraagprijs en de afwijking per m2.

---

## 7ff. De zondagseditie omgebouwd — 24 september 2026

**Mark:** zondag korter, het belangrijkste van de week als hoofdtekst, losse
kopjes bij losse onderwerpen, geen buurtportret en geen vast rentekopje. In de
bijlage alleen de uitgewerkte analyse van het object met de meeste kans.

**Zo gebouwd, met drie voorwaarden die ik erbij heb gezet:**
- het object wordt gekozen op de richtprijs ten opzichte van de vraagprijs, en
  haalt niets de drempel van tien procent, dan staat er dat er deze week geen
  case is, met het beste pand en zijn afstand erbij. Geen case is beter dan het
  minst slechte pand promoveren;
- de rente wordt alleen genoemd als die deze week is veranderd, in een halve
  zin in de lopende tekst;
- de brief krijgt de besluiten en het nieuws van zeven dagen mee, met de datum
  per dag, in plaats van alleen die van zondag. Anders zou het model zich de
  week moeten herinneren, en het ziet alleen wat in de opdracht staat.

**Verder weggevallen op zondag:** het biedadvies en de kamerhuurtoets stonden
nog onder de cases. Die horen bij "verder niks" en zijn eruit; ze staan zes
dagen per week in de dagelijkse editie.

**Woordgrens zondag: 500.**

---

## 7gg. De huur werd nergens aan de markt getoetst — 24 september 2026

**Mark:** is die huur wel gecontroleerd aan de markthuur? Nee.

**Wat er misging.** De Burg. Hustinxstraat 56 kreeg een richtprijs van €621.337
bij een vraagprijs van €415.000. Dat hoort bij ongeveer €30 per m2, terwijl de
referentie voor het Stadscentrum €20 is. Twee vangnetten stonden uit: de
wettelijke maximumhuur wordt alleen getoetst bij een bekende WOZ, en die was
onbekend, en een toets op de markthuur bestond niet.

**Nu:** een gemeten huur wordt gewogen met de referentie voor die buurt, met
het gewicht n / (n + 10). Bij drie waarnemingen telt de meting voor bijna een
kwart, bij tien voor de helft, bij dertig voor driekwart. Daarbuiten geldt nog
een band van 0,7 tot 1,4 keer de referentie. Drie waarnemingen van €30 leveren
nu €22,3 op en een richtprijs van €463.000 in plaats van €621.000.

**En een richtprijs boven de vraagprijs moet zichzelf verantwoorden:** rust die
op een aangenomen of gewogen huur, dan staat er in het dossier een regel "let
op" dat het geen koopsignaal is, en in de opdracht staat dat de brief dat
overneemt.

**Waarom dit nu pas naar boven kwam:** met twee huurwaarnemingen valt alles
terug op de aanname, en dan valt het niet op. Zodra er wel metingen zijn, gaan
ze meteen zwaar wegen. De Kamernet-melding aanzetten is dus niet alleen goed
voor meer data, maar ook de reden dat deze weging nodig was.

---

## 7hh. Kamernet via plakken, en de inclusief-val — 25 september 2026

**Kamernet laat automatisch uitlezen niet toe**, maar de tekst van de pagina is
te plakken. kamernet_plak.py leest kamernet_plak.txt en zet er regels van in
verkopen.txt, in hetzelfde formaat als de attenderingsmails. Alleen Nijmegen;
Arnhem, Lent, Groesbeek, Elst, Weurt en Zetten vallen af. De staat van
oplevering en "incl." komen in de bron te staan.

**De grotere vondst zat in onze eigen filters.** Van de negen Nijmeegse kamers
in de eerste plaktekst waren er zeven "incl.", en die gooide het script weg.
Bij woningen is dat terecht, op de kamermarkt is inclusief eerder regel dan
uitzondering. We hielden twee waarnemingen over, allebei uit dezelfde straat.
Inclusief-kamers worden nu apart bewaard: ze tellen niet mee in de richtprijs,
maar laten wel zien wat er gevraagd wordt.

**Wat ook al werkte:** een kamer van 100 m2 voor €455 en een van 120 m2 voor
€950 zijn het hele huis en niet de kamer. Die vielen al af op de bestaande
grenzen.

**Volgende stap:** de gevraagde kale kamerhuur naast het wettelijk maximum uit
het WWSO leggen, en de inclusief-reeks apart tonen als marktbeeld.

---

## 7ii. Gemeubileerd en short stay — 25 september 2026

**Aanleiding:** op Kamernet valt op dat gemeubileerd aanbod per m2 veel meer
opbrengt. De vraag was of dat een route is.

**Gemeubileerd:** meubels verhogen de kale huur niet, want die wordt begrensd
door het puntenstelsel. Meubilering gaat via de servicekosten als
gebruiksvergoeding voor roerende zaken, en dat is afschrijving: tien jaar voor
duurzame zaken, vijf jaar voor overige stoffering en meubilair, en zonder
inventarislijst een standaardbedrag van 12 euro per jaar. All-in mag niet, en
de Huurcommissie kan sinds 1 juli 2024 ook bij middenhuur en vrije sector over
servicekosten oordelen. Dat verklaart meteen waarom het script Kamernet-
appartementen buiten de richtprijs houdt: die huren zijn deels een vergoeding
die bij toetsing kan sneuvelen.

**Short stay:** Nijmegen staat tijdelijke verhuur van de eigen woning toe
zonder vergunning, maar alleen als je er zelf het grootste deel van het jaar
woont, en niet telkens voor korte tijd terwijl je er niet woont. Landelijk wil
de minister short-stay-contracten beperken tot 30 dagen. Voor een verhuurpand
is het dus geen vrije route.

**Open punt, opgelost op 25 september:** de vijf jaar voor onzelfstandige
woonruimte is vervallen. Wat blijft is een tijdelijk contract van hoogstens
twee jaar met iemand uit de limitatieve lijst, en dat geldt voor zelfstandige
en onzelfstandige woonruimte. De commerciele bron die vijf jaar beloofde, zat
ernaast. Zie 7jj.

**Toegevoegd aan de monitor:** het omgevingsplan (tien verordeningen nu), en de
feed "Short stay en toeristische verhuur". Aanleiding: een raadsbrief van
9 september 2025 kondigde een wijziging van het omgevingsplan over short stay
aan, met besluitvorming voorzien in maart 2026. Die hebben we gemist omdat we
noch raadsstukken noch het omgevingsplan volgden.

**Twee achtergrondstukken erbij**, met bron: "Gemeubileerd verhuren" en
"Short stay". Nu 19 stukken.

---

## 7jj. Tijdelijke contracten bij studentenkamers — 25 september 2026

**De werkwijze van Derksen Vastgoed** (een tijdelijk contract van twee jaar bij
een bewoner uit een andere gemeente, alleen bij onzelfstandige studentenkamers)
valt samen met de wettelijke uitzondering: personen die voor hun studie
tijdelijk in een andere gemeente willen wonen of uit het buitenland komen om
hier te studeren, hoogstens twee jaar, zelfstandig of onzelfstandig.

**Drie punten die makkelijk misgaan:**
- in het contract moet staan dat het tijdelijk is en op welke uitzondering het
  rust;
- de toelichting adviseert vooraf bewijsstukken op te vragen, dus een
  inschrijfbewijs van de opleiding;
- een student die al in Nijmegen woont, valt niet onder de uitzondering.

**En het overgaan in onbepaalde tijd is geen automatisme maar een gevolg:** een
tijdelijk contract eindigt alleen als de verhuurder het einde tijdig
schriftelijk aankondigt. Gebeurt dat niet, dan loopt het door voor onbepaalde
tijd en kan er geen tweede tijdelijk contract met dezelfde huurder komen. Voor
doorstroming in een kamerpand is het campuscontract waarschijnlijk passender;
dat is een vraag voor de huurrechtjurist.

**Achtergrondstuk toegevoegd:** "Tijdelijke huurcontracten", met bron. Nu 20
stukken.

---

## 7kk. Verkochte woningen uit een geplakte Funda-lijst — 27 september 2026

**funda_verkocht_plak.py** leest funda_verkocht_plak.txt en doet drie dingen:
- de verkopen worden waarnemingen in verkopen.txt, met woonoppervlakte,
  postcode en energielabel; herhaalde advertenties en parkeerplaatsen vallen af;
- panden die bij ons nog te koop staan maar op Funda verkocht zijn, worden
  gemeld. Vendr meldt een verkoop niet, dus die bleven anders in de lijst;
- elk verkocht adres wordt tegen het bekendmakingenarchief gelegd: staat er na
  het begin van de advertentie een vergunning of melding op dat adres, dan is
  dat een spoor van een koper die gaat verbouwen, splitsen of verkameren.

**De beperking staat erbij:** Funda noemt alleen hoe lang een advertentie er
staat, niet wanneer er is verkocht. De afgeleide datum is dus het begin van de
advertentie, en een bekendmaking daarna is een aanwijzing en geen bewijs.

**Let op bij de eerste run:** een paar honderd verkopen tegelijk verschuift de
buurtmediaan in een keer. De trendregel zegt al dat een verandering van de
mediaan ook door nieuwe waarnemingen komt, maar die sprong is eenmalig en geen
marktbeweging.

**Extra gegevens** staan in verkocht_details.json: label, perceel en de
advertentieduur. Dat maakt later de kruising label tegen verkoopprijs mogelijk.

---

## 7ll. Geschiedenis per pand — GEBOUWD 27 september 2026

**Waarom op het pand en niet op het adres.** Bij een splitsing verdwijnt het
oude huisnummer niet, er komen nieuwe bij. Op het adres vastgelegd zie je drie
losse nieuwe woningen zonder verleden; op het BAG-pand zie je dat 180 m2 in
drieen is gegaan. In de test kwam een melding op huisnummer 42-A terecht in de
geschiedenis van nummer 42.

**pandgeschiedenis.py** legt per pand vast: te koop, prijswijziging, verkocht
(uit verkopen.txt), vergunningen en meldingen (uit het archief), het aantal
woningen en hun oppervlaktes volgens de BAG, en het energielabel per adres.
Verandert de BAG of komt er een label bij, dan is dat een eigen gebeurtenis;
na een splitsing volgen de labels vaak weken later.

**Cadans:** dagelijks de gebeurtenissen uit bestanden die we al hebben; op
zondag ook de BAG en de labels, hoogstens 60 panden per ronde, en alleen voor
panden waar iets mee gebeurd is. Anders kost het te veel verzoeken.

**Fout in mijn eigen woordkeuze, hersteld tijdens de test:** er stond "verkocht
voor X", terwijl Funda de laatste vraagprijs toont en niet de koopsom. Die
staat alleen bij het Kadaster. Overal aangepast naar "verkocht, laatste
vraagprijs", ook in de opdracht aan de brief.

**Wat hier later uit volgt:** doorlooptijd tot verkoop en de samenhang met de
afwijking van de buurtmediaan, en de toets van ons eigen model tegen wat een
koper werkelijk met een pand deed. Beide wachten op eigen waarnemingen; de
reeks begint nu.

---

## 7mm. Alles volgen dat een signaal geeft — 27 september 2026

**Vraag van Mark:** hoeveel panden zitten er in het zoekgebied, en kunnen we ze
allemaal volgen?

**In de zes buurten staan 19.061 woningen** (CBS). Het aantal panden is kleiner,
want een complex van 26 woningen is een pand; dat getal kennen we niet en zou
een eenmalige BAG-ronde van duizenden opvragingen kosten.

**Allemaal volgen hoeft niet.** Een pand zonder gebeurtenis heeft geen
geschiedenis. De signalen komen naar ons toe: bekendmakingen, het aanbod, de
meldingen. Wat wel ontbrak: de geschiedenis maakte alleen panden aan die ooit
in het aanbod stonden, dus een eigenaar die iets aanvraagt zonder te verkopen
viel buiten beeld. Juist daar zit een verhaal.

**Nu:** elk adres uit het bekendmakingenarchief wordt een pand, en de 948
adressen uit het kamerverhuurregister ook. De BAG en de labels worden nog
steeds alleen opgevraagd voor panden waar iets mee gebeurd is.

**Valkuil, opgelost tijdens de test:** de sleutel kwam uit de titel van een
bekendmaking, en "aan de Dominicanenstraat 30" leverde dan een sleutel met
"de" erin. Dat pand matchte niet met zijn eigen bekendmakingen. De sleutel komt
nu uit het archief zelf.

---

## 7nn. Wat de buren deden — 27 september 2026

**Vraag van Mark:** als een pand te koop komt, kunnen we dan zien of er in
diezelfde straat eerder is gesplitst of verkamerd?

**Ja, en het volgde rechtstreeks uit de geschiedenis.** precedenten() zoekt in
dezelfde straat naar panden met een route: verkocht, vergunning, splitsing in
de BAG, nieuw energielabel, weer te koop. Die route staat nu in het dossier van
elk pand dat te koop komt, onder "eerder in deze straat".

In de test bij een nieuw pand aan de Fagelstraat 60:
- nummer 42: 2026-06 verkocht, 2026-07 aanvraag splitsen naar drie
  appartementen, 2026-08 vergunning verleend, 2026-09 melding brandveilig
  gebruik op 42-A;
- nummer 38: 2025-03 verkocht, 2025-06 vergunning splitsen, 2025-11 label A op
  38-A, 2026-02 weer te koop.

Dat tweede is de volledige route die Mark beschreef: gekocht, gesplitst,
verduurzaamd, opnieuw aangeboden.

**Eerlijk over wat ontbreekt:** staat er niets, dan betekent dat niet dat er
niets gebeurd is. We zien alleen wat sinds 2012 is gepubliceerd. Die zin staat
in het dossier en de brief moet hem overnemen.

---

## 7oo. Vier fouten in de eerste zondagsbrief — 27 september 2026

**De hele geschiedenis van de belastingverordeningen kwam binnen als nieuws.**
Oorzaak: de monitor beschouwt elke regeling die hij voor het eerst ziet als
nieuw, en de zoektermen voor OZB, riool, afval en leges waren net toegevoegd.
Dus alle jaargangen sinds 2011. Nu legt het script bij een nieuwe zoekterm de
gevonden regelingen stil vast als uitgangspunt en meldt het alleen wat daarna
verandert. In de test: 16 regelingen stil vastgelegd, alleen de echte wijziging
gemeld.

**"Bekijk de drie panden op de kaart"** stond er vast ingebakken, ook nu er nog
maar een case is. De link telt nu wat er werkelijk op staat.

**De case was mager en ging alleen over de vraagprijs.** Alle feiten uit het
dossier gaan nu mee naar het memo: de huur en of die gemeten of aangenomen is,
de puntentelling en of het pand onder de 187 valt, de WOZ tegenover de
vergunninggrens, de gemeentelijke lasten, de kamerverhuursignalen en wat de
buren in dezelfde straat deden. In de opdracht staan nu drie vragen die altijd
beantwoord moeten worden: mag het, wat is de huur en waar komt die vandaan, en
wat deden de buren. De lengte ging van 450 naar 550 woorden.

**Publicaties van de laatste 24 uur stonden in de zondagsbijlage.** Dat hoort
niet: de brief behandelt op zondag de hele week. Dat blok vervalt op zondag.

---

## 7pp. Drie storingen na de zondagsrun — 27 september 2026

**401 bij de BAG, honderden keren.** De stap Geschiedenis per pand kreeg de
BAG-sleutel niet mee; die stond alleen bij de marktprijzenstap. Nu staat hij
erbij, en zonder sleutel slaat het script de BAG en de labels over met een
melding in plaats van honderden mislukte verzoeken.

**Gezondheidsrapport viel om op de regelgeving.** Mijn sleutel _termen in het
statusbestand is een lijst, en de controle liep er met .get overheen. De
controle slaat sleutels die met een liggend streepje beginnen nu over.

**CBS onbereikbaar.** De woningprijsindex liep op een verbindingsfout naar
opendata.cbs.nl, geen foutcode. Er zitten nu drie pogingen met oplopende
wachttijd op. Blijft het mislukken, dan staat de host in de diagnose. Let op:
de bouwkostenindex gebruikt dezelfde host en stond op OK omdat de controle het
bestand van een eerdere run leest; die kan dus stilletjes hetzelfde probleem
hebben.

**Dubbel energielabel in de case.** Het dossier voegde het label toe dat er al
stond. Dubbelingen worden er nu uit gefilterd.

**Nog na te gaan:** de brief schreef "ik heb geen reeks over de afgelopen
weken" voor de rente, terwijl eerdere brieven wel een terugblik over een maand
hadden. Volgende run controleren of de terugblik in de rentedigest zat.

---

## 7qq. Een hele run verloren door een git-conflict — 27 september 2026

**Wat er gebeurde.** Twee runs schreven allebei regels bij in woz.txt. Git kan
twee aanvullingen aan hetzelfde bestand niet vanzelf samenvoegen, de rebase
liep vast, en daarna mislukte elke volgende poging ook. Alle gegevensbestanden
van die run zijn verloren.

**De oplossing staat in .gitattributes**, een nieuw bestand in de repo: voor
bestanden waar alleen regels bij komen (verkopen.txt, woz.txt, huidige_huur.txt
en de plakbestanden) houdt git beide kanten.

**Twee dingen die de test blootlegde:**
- het bestand moet in de repo staan, niet door de workflow worden aangemaakt.
  Bij een rebase leest git de instelling uit de bestaande boom, en een
  gelijktijdig aangemaakt bestand telt dan niet mee;
- definieer de samenvoeger "union" niet zelf in de workflow. Die zit in git
  ingebouwd. Mijn eigen definitie overschreef hem, en dan verdween juist een
  van de twee kanten. In de eerste test was precies de regel van de tweede run
  weg.

**Vangnet:** blijft er toch een conflict staan, dan lost de workflow het nu
zelf op. Bij tekstbestanden worden beide kanten samengevoegd en ontdubbeld, bij
de rest wint de versie van deze run, en daarna gaat de rebase door.

## 7rr. CBS bereikbaar via een tweede ingang

opendata.cbs.nl gaf twee runs achter elkaar een verbindingsfout, geen
foutcode. Er is nu een terugval op de v4-API van het CBS
(datasets.cbs.nl/odata/v1/CBS), met dezelfde tabellen en een andere opbouw:
elke cel staat er apart, met een code voor wat er gemeten is. Die code wordt
opgezocht en niet aangenomen, met dezelfde regel als elders: een maat die over
een ontwikkeling gaat is geen index.

**Vervolg 27 september:** ook de tweede ingang gaf een verbindingsfout. Twee
CBS-hosts onbereikbaar terwijl dataderden.cbs.nl en alle andere bronnen wel
werkten. Dat patroon hoort bij een host met zowel een IPv4- als een
IPv6-adres op een machine waar het IPv6-verkeer nergens heen kan: de naam wordt
gevonden, de verbinding niet opgebouwd. Het script vraagt nu alleen naar
IPv4-adressen, en probeert drie ingangen op volgorde: opendata.cbs.nl,
datasets.cbs.nl en odata4.cbs.nl. De bouwkostenindex gebruikt dezelfde host en
krijgt dezelfde behandeling.

---

## 7ss. "Aangewezen wijk" bestond niet — 27 september 2026

**De brief schreef** dat Galgenveld een aangewezen wijk is waardoor omzetting
hoe dan ook vergunningplichtig blijft, en tegelijk dat de vergunningplicht bij
een WOZ van €523.000 niet geldt. Dat spreekt elkaar tegen.

**Nagezocht bij de gemeente zelf.** Boven €396.000 geldt de opkoopbescherming
niet en is geen omzettingsvergunning nodig, maar is wel een omgevingsvergunning
nodig om de woning geschikt te maken voor kamerverhuur. De conclusie "je hebt
sowieso een vergunning nodig" klopte dus, de grond niet: het loopt via het
omgevingsplan, het vroegere facetbestemmingsplan kamerverhuur uit 2022, en niet
via aangewezen wijken. Die grond bestaat niet.

Op drie plekken hersteld: het beleidsstuk, de feiten bij de case en de
opdracht voor het memo. Het heet nu "twee sporen bij kamerverhuur".

**Twee bedragen voor hetzelfde begrip, nu een.** Naast de richtprijs stond een
"bod voor cashflow nul": dezelfde berekening met een andere
exploitatie-aanname. In de brief van 27 september stond €610.142 naast
€779.861. Het tweede bedrag is eruit.

**En de verbouwkosten heten geen begroting.** Zolang bouwkosten_eigen.txt leeg
is, is €45.020 een aanname van het script. Dat staat nu in de opdracht.

---

## 7tt. Achterstand in de BAG-controle inlopen — 27 september 2026

De BAG- en labelcontrole draaide alleen op zondag en hoogstens 60 panden per
ronde. Met ongeveer duizend gevolgde panden duurt een eerste ronde dan vier
maanden.

**Nu:** 200 panden per ronde, en de volledige controle draait ook bij elke
handmatige start, niet alleen op zondag. Met BAG_PER_RONDE is het aantal
tijdelijk te verhogen. Er zit 0,2 seconde tussen de opvragingen, en na elke
ronde staat in het logboek hoeveel panden nog nooit zijn gecontroleerd.

**Getest:** opeenvolgende runs gaan verder waar de vorige stopte (10, 20, 30
van de 30), en zodra iedereen is nagekeken begint hij opnieuw bij de oudste.
Dat laatste is de bedoeling: zo worden splitsingen en nieuwe labels opgemerkt.

**Bij het inlopen: vink "alleen naar mij" aan.** Anders krijgt Marks vader vijf
brieven op een dag. Die vlag blokkeert ook het geheugen van geziene panden en
de maandreeks, maar niet de geschiedenis; die wordt gewoon bijgewerkt.

---

## 7uu. Bij een testrun kreeg vader toch een brief — 27 september 2026

**De valkuil.** De ontvangerslijst stond als GitHub-expressie in de mailstap:
`voorwaarde && '' || secret`. In een GitHub-expressie telt een lege string als
onwaar, dus valt zo'n constructie altijd door naar de rechterkant. Het adres
van Marks vader stond er dus bij elke run in, ook bij een testrun. Het
onderwerp werkte wel, want "TESTRUN" is niet leeg.

**Nu** wordt bij het bepalen van de modus ook de cc gezet, in bash, waar een
lege waarde gewoon leeg blijft. De mailstap gebruikt die variabele. De tweede
mailstap, zonder verhaal, had al geen cc en krijgt nu hetzelfde
TESTRUN-onderwerp.

**Les:** een vlag die "niets" moet betekenen, hoort niet in een expressie die
leeg als onwaar leest. Bepaal hem in een stap en zet hem in een variabele.

---

## 7vv. Het rapport zegt nu welke ingang en hoeveel er nog wachten — 27 september 2026

**Aanleiding:** het CBS werkte weer, maar uit het rapport viel niet af te lezen
welke van de drie ingangen het deed. Staat de eerste weer aan, of vangt de
terugval het al weken op? Dat verschil bepaalt of er nog iets te repareren is.
Het script legt nu vast welke host antwoordde en het rapport toont dat.

**En het rapport toont nu de stand van de geschiedenis:** hoeveel panden we
volgen, hoeveel er meer dan een gebeurtenis hebben, en hoeveel er nog nooit
tegen de BAG zijn gehouden. Bij een achterstand staat erbij hoeveel runs dat
nog kost bij de huidige ronde-grootte. Dat is de vraag die Mark stelde, en die
hoort inderdaad in het rapport: het is een achterstand, geen storing.

**Waarom LET OP en geen FOUT:** een achterstand in de BAG-controle betekent
niet dat er iets kapot is. Zodra iedereen een keer is nagekeken, wordt het OK
en begint de ronde opnieuw bij het oudste pand.

---

## 7ww. Het buurtportret wordt stroom in plaats van voorraad — 27 september 2026

**Waarom.** Het portret bestond uit jaarcijfers: voorraad, koop, WOZ, studenten,
misdrijven. Die veranderen een keer per jaar, dus elke keer dat een buurt aan
de beurt kwam stond er vrijwel hetzelfde. De pandgeschiedenis geeft wat er in
die buurt gebeurt.

**buurtbeeld() telt per buurt en per jaar** de aanvragen om te splitsen of te
verkameren en hoe ze afliepen: verleend, geweigerd, of buiten behandeling
gesteld. Terug tot 2012, zodat een trend zichtbaar wordt in plaats van een
momentopname. Daarbij de mediane doorlooptijd van aanvraag tot vergunning, en
hoe vaak er na een verkoop een ingreep werd aangevraagd.

**In de brief** begint het portret nu bij die gebeurtenissen; de jaarcijfers
zijn achtergrond en komen er alleen bij als ze iets verklaren.

**De kanttekening staat er standaard bij:** we zien alleen wat gepubliceerd is
en wat onze zoekwoorden vangen. Een laag aantal bewijst niet dat er weinig
gebeurt. Dat geldt sterker naarmate je verder terugkijkt.

---

## 7xx. Een afgekapte brief werd goedgekeurd — 28 september 2026

De brief van 28 september eindigde midden in een zin: "Een BV betaalt in 2026,
meldt de". Oorzaak: de herstelronde leverde een afgebroken versie, en mijn
controle keurde die goed. Logisch, want een afgekapte brief heeft per definitie
minder probleemzinnen dan het origineel; precies waar de controle op toetst.

**Nu** wordt een herschreven versie geweigerd als hij minder dan tachtig
procent van de woorden van het origineel telt, met een melding in het logboek.
En eindigt de brief niet op een leesteken, dan komt dat in de diagnose te
staan.

**Les:** een controle die op "minder fouten" toetst, keurt ook verminking goed.
Meet er altijd iets naast dat niet meebeweegt, zoals lengte.

## 7yy. Splitsen in elf eenheden van veertien meter

Doddendaal 101 (159 m2) kreeg het scenario "splitsen in 11". Oorzaak: het
script neemt het aantal woningen dat de BAG in het pand kent over als het
aantal waarin je kunt splitsen. Bij een appartementencomplex van elf woningen
wordt dat elf. De routecheck blokkeerde dat al voor appartementen, maar de
scenariokeuze raadpleegde die niet.

**Nu:** een appartement in een complex krijgt geen splitsscenario en wordt als
een woning doorgerekend, ook als het groter is dan 150 m2; splitsen en
kamerverhuur vragen daar allebei toestemming van de VvE. En het aantal uit de
BAG telt alleen mee tot het maximum dat het script zelf hanteert.

---

## 7zz. Het archief kende alleen ingrepen in de voorraad — 28 september 2026

**Vraag van Mark:** we hebben meldingen vanaf 2012, waarom halen we niet van
elk pand met een aanvraag de geschiedenis op?

**Dat gebeurde al**: sinds 27 september krijgt elk adres uit het archief een
pandgeschiedenis, ook zonder dat het ooit te koop stond. Daar komt het aantal
van 1143 gevolgde panden vandaan.

**Het echte gat zat in het archief zelf.** Dat bewaarde alleen bekendmakingen
over splitsen, verkameren, transformatie, onttrekking en handhaving. Een pand
dat na aankoop gewoon is verbouwd, stond er niet in, terwijl dat juist het
spoor is dat we zoeken: gekocht en daarna aangepakt. En een pand dat in tien
jaar niets heeft aangevraagd, is waarschijnlijk nooit aangepakt; ook dat is
informatie.

**Toegevoegd:** het signaal "verbouwing", met woorden als verbouwen, aanbouw,
dakkapel, dakopbouw, gevelwijziging, constructief en renovatie. Bewust zonder
kap-, inrit-, evenement- en standplaatsberichten; die zeggen niets over het
pand als investering.

**Twee gevolgen om te weten:**
- het archief moet opnieuw worden opgehaald om de verbouwingen sinds 2012 mee
  te krijgen: een handmatige start met een datum in het verleden;
- het aantal gevolgde panden groeit daardoor fors, en daarmee de achterstand in
  de BAG-controle. Die pakt nu eerst de panden die in het aanbod zitten of
  verkocht zijn; een pand met alleen een dakkapel uit 2015 wacht.

---

## 7aaa. De labelcontrole was niet begrensd — 28 september 2026

**Aanleiding:** de vraag of de ronde van 200 naar 1000 panden kan. Bij het
nakijken bleek de labelcontrole helemaal geen grens te hebben: die liep elke
volledige run langs alle gevolgde panden. Met 1143 panden zijn dat al ruim
tweeduizend opvragingen bij de BAG en EP-Online, en na de archiefbackfill zou
dat een veelvoud worden.

**Nu** kijkt de labelcontrole alleen de panden na die in diezelfde ronde tegen
de BAG zijn gehouden. In de test: 10 in plaats van 40. De standaard per ronde
is van 200 naar 500 gegaan, met BAG_PER_RONDE hoger te zetten.

**Rekensom bij 1000 per ronde:** ongeveer vier opvragingen per pand en 0,2
seconde pauze, dus zo'n tien tot vijftien minuten per run. Dat past ruim binnen
een GitHub-run, maar het is wel een flinke belasting van twee diensten die we
gratis gebruiken. Vandaar 500 als standaard en niet 1000.

---

## 7bbb. De BAG-controle deed niets en meldde niets — 28 september 2026

Na meerdere runs stonden alle 1146 panden nog op "nooit gecontroleerd". In de
code zat een stille uitgang: kon het pand-id niet worden gevonden, dan werd het
pand overgeslagen zonder markering en zonder te tellen. Gebeurde dat bij alle
panden, dan deed de stap niets en meldde het rapport niets.

**Nu:**
- een pand zonder pand-id wordt gemarkeerd, zodat het niet elke ronde opnieuw
  vooraan staat en de rest wel aan de beurt komt;
- het logboek meldt hoeveel panden zijn bekeken, hoeveel zijn afgehandeld en
  hoeveel er geen pand-id hadden;
- levert geen enkel bekeken pand een pand-id op, dan komt dat in de diagnose te
  staan, met de twee waarschijnlijke oorzaken: het adres komt niet door de
  BAG-opzoeking, of de sleutel ontbreekt in die stap;
- het rapport toont hoeveel panden zonder pand-id zijn.

**Ook hersteld:** het gezondheidsrapport had een eigen kopie van het aantal per
ronde en noemde 200 terwijl het script op 500 stond. Het leest nu de waarde uit
het script.

**Les, dezelfde als bij de afgekapte brief:** een stap die niets doet, hoort
dat te melden. Zonder teller zie je het verschil niet tussen "niets te doen" en
"niets gelukt".

---

## 7ccc. De verkeerde BAG-functie aangeroepen — 28 september 2026

**Wat de teller van gisteren opleverde:** 500 panden bekeken, nul met een
pand-id. Systematisch, dus geen adresprobleem.

**De oorzaak.** bag_dump is een hulpfunctie om met de hand te kijken wat de BAG
teruggeeft: hij print de respons en geeft niets terug. Die had ik aangeroepen
alsof het de opzoekfunctie was. Vandaar ook de regels "=== met expand=panden
===" die eerder in het logboek stonden; die kwamen daarvandaan.

**Nu** gebruikt de geschiedenis dezelfde opzoeking als de verrijking,
bag_adres_uitgebreid, met de huisnummervarianten die het script al kent. En de
500 panden die onterecht als "zonder pand-id" zijn weggezet, krijgen hun
markering terug zodat ze opnieuw aan de beurt komen.

**Les:** de teller die ik gisteren inbouwde heeft dit in een run zichtbaar
gemaakt. Zonder die teller had ik nu nog geraden.

---

## 7ddd. Testruns aten het nieuws alsnog op — 28 september 2026

**Vraag van Mark:** beïnvloeden testruns de echte brief? Ja, meer dan ik dacht.
De vlag GEHEUGEN_ALLEEN_LEZEN beschermde alleen het geheugen van geziene panden
en de maandreeks. De gelezen artikelen, het weetje van de dag en het
achtergrondstuk werden gewoon afgestreept. Na zes testruns op een dag zijn de
artikelen van die dag dus "al geweest" en komen ze niet meer in de echte brief.

**Nu** staat er een gedeelde controle in diagnose.py, en die wordt gebruikt bij
publicaties_gezien.json, weetjes_gezien.json en achtergrond_gezien.json. Bij
een testrun wordt er niets afgestreept en staat dat in het logboek.

**Ook toegevoegd: een controle op de handmatige lijsten.** Het rapport laat nu
zien of funda_verkocht_plak.txt en kamernet_plak.txt in de repo staan en hoeveel
verkochte woningen er zijn verwerkt. Ze ontbreken allebei nog, dus de 572
verkopen zitten er niet in.

---

## 7eee. Drie punten van Mark — 28 september 2026

**De plakbestanden bestonden niet.** Ik bouwde de parser en vroeg om de lijst,
maar maakte het bestand nooit aan. funda_verkocht_plak.txt en
kamernet_plak.txt staan er nu, met een uitleg erin; regels met een hekje worden
door de parsers overgeslagen. De lijst uit het gesprek heb ik bewust niet
gereconstrueerd: dan zou ik adressen of bedragen kunnen verzinnen.

**Verbouwkosten worden afgerond op duizend euro** zolang ze een aanname zijn.
€45.020 suggereert een begroting, terwijl het een tarief per m2 maal de
oppervlakte is. Staat het bedrag in bouwkosten_eigen.txt, dan komt het uit een
echte opgave en blijft het staan. WOZ, OZB en heffingen worden niet afgerond;
die zijn exact.

**Twee runs tegelijk kan niet meer.** De workflow heeft nu een
concurrency-groep: start je handmatig terwijl de geplande run bezig is, dan
wacht de tweede tot de eerste klaar is in plaats van ernaast te draaien. Dat is
de oorzaak van de git-botsing van 27 september bij de wortel aangepakt; de
samenvoegregel in .gitattributes blijft als vangnet.

---

## 7fff. De verkooplijst kent meer dan "Verkocht" — 28 september 2026

De tweede plaktekst liet zien dat mijn parser het grootste deel zou missen.
Funda toont vier statussen, en ik zocht naar een regel die exact "Verkocht" is.

**Nu herkend:** Verkocht, Verkocht onder voorbehoud, Onder bod en Onder optie,
ook als de status aan "Nieuwbouwwoning" vastgeplakt zit. Ze worden apart
vastgelegd, want het zijn verschillende dingen: verkocht onder voorbehoud is
een gesloten koop met ontbindende voorwaarden en telt als verkoop, onder bod is
dat niet.

**Nieuwbouw valt eruit:** Metterswane, Joie de Vivre en Amber zijn bouwnummers
met v.o.n.-prijzen en een project in plaats van een adres. Dat is geen
bestaande voorraad en hoort niet in onze reeks. Herkend aan het woord
nieuwbouw, aan "Bouwnr." en aan de v.o.n.-prijs.

**En de rest van het script telt nu mee op dezelfde manier:** er is een functie
is_verkocht() in plaats van vijf losse vergelijkingen met de tekst "verkocht".
Zo kan een nieuwe status niet meer op de ene plek wel en op de andere niet
meetellen.

---

## 7ggg. Waarom ik de lijst niet overtyp — 28 september 2026

Mark vroeg of ik de geplakte verkooplijst als bestand kon opleveren. Dat doe ik
niet: het zijn ruim zevenhonderd blokken, en bij het overtypen kan er een adres
of een prijs verhaspeld raken. Dan staat er een verzonnen waarneming in de
reeks die niemand meer terugvindt. Plakken in GitHub kost een minuut en heeft
die kans niet.

**Wel gedaan:** het plakbestand heeft nu een uitleg die vertelt wat er
automatisch afvalt en welke vier statussen worden herkend. En er is een korte
regel bijgekomen voor handwerk:
status | prijs | adres | postcode | m2 | label. Die mag door de geplakte tekst
heen staan; het script leest beide.

---

## 7hhh. Verkopen horen niet met de hand te komen — 28 september 2026

**Mark:** ik ga geen 700 panden invoeren, en waarom kan dat niet als tekst?

**Twee dingen rechtgezet.** Invoeren hoeft niet, plakken is genoeg. Maar Funda
toont vijftien tot vijfentwintig panden per pagina, dus 753 resultaten zijn een
stuk of veertig pagina's. Dat is geen werk voor een mens, en mijn voorstel was
dus niet goed.

**De kern van het probleem:** ons systeem kan een verkoop niet zelf ontdekken.
De attendering meldt nieuw aanbod; een pand dat verdwijnt, meldt niemand.
Daarom stond de Ruyterstraat 135 bij ons nog te koop terwijl hij al verkocht
was.

**De oplossing ligt bij de attendering.** Mark heeft het filter op verkocht en
onder bod inmiddels aangezet. Komen die statussen in de mail, dan leest
funda_mail.py ze net als het andere aanbod en hoeft er niets geplakt te worden.

**Daarom eerst meten, niet bouwen.** Het gezondheidsrapport toont nu hoeveel
verkopen er zijn en of ze uit de mail komen of geplakt zijn. Komt er niets uit
de mail, dan staat het filter niet goed of neemt Funda die statussen niet mee
in de attendering, en dan pas is het zinvol iets anders te verzinnen.

**Het plakken blijft voor de geschiedenis**, en dan in eigen tempo: het script
ontdubbelt, dus een pagina per keer mag ook.

---

## 7iii. Zwijgt een bron, of begrijpen we hem niet? — 28 september 2026

**Mark:** die Kamernet-mails komen toch gewoon binnen en worden toch vanzelf
toegevoegd?

Dat klopt als route: funda_mail.py accepteert kamernet.nl als afzender en heeft
er een eigen parser voor. Het plakbestand is alleen een noodoplossing. Maar het
gezondheidsrapport meldt al dagen nul Kamernet-waarnemingen, en er was geen
manier om te zien waarom.

**Nu legt de mailstap per bron vast** hoeveel mails er waren en hoeveel
objecten eruit kwamen, in mail_status.json. Het rapport vertaalt dat naar twee
verschillende conclusies:
- geen mails van een bron: de attendering staat niet aan of komt in een andere
  mailbox binnen;
- wel mails maar geen objecten: de opmaak van die mails is veranderd en de
  parser moet worden bijgewerkt.

Dat zijn twee heel verschillende problemen, en zonder deze telling waren ze
niet uit elkaar te houden. Ontbreekt een bron helemaal in de telling, dan geldt
hij ook als zwijgend; anders zie je een bron die nooit mailt gewoon niet.

---

## 7jjj. Onveranderd is geen nieuws — 28 september 2026

**Mark:** ik lees te vaak dat de rente niet is gewijzigd. Dat is geen nieuws.

De rentestap schrijft bij een rustige dag "Onveranderd deze week: ...". Dat is
naslag, en de brief maakte er een alinea van. Die regel begint nu met "GEEN
NIEUWS, ALLEEN NASLAG", en in de opdracht staat dat zo'n regel niet in de brief
hoort: geen alinea, geen zin, ook niet terloops. Alleen bij een verandering, of
als een bericht of doorrekening er aanleiding toe geeft. De regel geldt meteen
voor elk ander cijfer dat gelijk is gebleven.

## 7kkk. De mailstap zweeg over zichzelf

Het rapport meldde "nog geen mailstand vastgelegd", terwijl de stap draait.
Oorzaak: de stand werd pas aan het eind weggeschreven, dus bij een vroegtijdige
stop (geen inloggegevens, mislukte login) bleef er niets achter. Nu wordt de
stand altijd weggeschreven, met de reden erbij.

**Correctie op mijn eerste vermoeden:** ik dacht dat het aan ongelezen mails
lag, maar de workflow geeft al --dagen 3 mee, dus gelezen mails tellen mee. Dat
was dus niet de oorzaak. De standaard in het script staat nu ook op 3, zodat
een run zonder die vlag hetzelfde doet.

**Goed nieuws in dezelfde run:** 575 verkochte woningen verwerkt, 505 verkopen
in de reeks. Het plakken werkte.

---

## 7lll. Kamernet-mails kwamen binnen en werden niet begrepen — 28 september 2026

De diagnose van vanmiddag wees twee mogelijkheden aan; het is de tweede
geworden. Mark ontvangt tien Kamernet-mails per dag en de parser haalde er nul
uit. Getest op een echte mail: nul objecten.

**Oorzaak:** het script kende alleen het Kamernet-overzicht, een lijst met
meerdere woningen. De losse attendering heeft labels:
Locatie: Graafseweg, Nijmegen / Oppervlakte: 21 m2 / Prijs: € 852 incl. g/w/e.
Daar was geen parser voor.

**Nu wel**, met de overzichtsparser eerst en deze als terugval. Er staat geen
huisnummer in, alleen de straat; dat is hetzelfde als bij het huuraanbod van
Pararius en daar kan de rest van het script mee omgaan. "incl." komt in de
bron te staan, zodat het geen kale huur wordt genoemd.

**Twee fouten die de test blootlegde:**
- "studentenhuis" bevat "huis", waardoor een kamer als zelfstandige woning werd
  geteld. Nu op hele woorden, en "kamer" wint;
- Kamernet attendeert ook buiten de stad. Een kamer in Arnhem zou de Nijmeegse
  mediaan verschuiven; die wordt nu overgeslagen met de reden erbij.

---

## 7mmm. Oude attenderingen inhalen — 28 september 2026

**Mark:** leest hij hiermee ook de oude Kamernet-mails? Dan is de lijst meteen
gevuld.

Dat kan, maar er zat eerst een fout onder. Alle parsers stempelden elke
waarneming met de datum van vandaag. Bij het inhalen van een paar maanden aan
mails zouden tweehonderd advertenties dezelfde dag krijgen, en dan lijkt de
hele huurmarkt in een dag te zijn ontstaan. De doorlooptijden en de
weekcijfers zouden daarop stuklopen.

**Nu komt de datum uit de mailkop.** Getest: een mail van 2 september levert
een waarneming van 2026-09-02. Zonder leesbare datum valt hij terug op vandaag.

**En de workflow heeft een keuze gekregen bij de handmatige start:** hoeveel
dagen aan mails opgehaald worden, standaard drie. Zet hem op 180 en de oude
attenderingen komen alsnog binnen, met hun eigen datum. Ontdubbelen gebeurt op
straat, prijs en oppervlakte, dus dezelfde advertentie twee keer ophalen kan
geen kwaad.

---

## 7nnn. De mailstap liep vast op mijn eigen teller — 28 september 2026

Het rapport meldde "mailstap van ?", wat betekent dat mail_status.json er niet
was. Dat kon niet, want de stand wordt nu zelfs bij een mislukte login
geschreven. Dus liep de stap eerder vast.

**Oorzaak:** bij het inbouwen van de tellers vanmiddag is de regel tellers = {}
nooit geplaatst; mijn tekstvervanging matchte niet en ik heb dat niet
gecontroleerd. De stap liep daardoor stuk op de eerste mail, en omdat er
|| echo "overgeslagen" achter stond, gebeurde dat geruisloos. Sindsdien kwam er
geen enkele waarneming meer binnen uit de mail, ook geen Funda-aanbod.

**Hersteld**, en met twee maatregelen tegen herhaling:
- de workflow schrijft nu zelf een stand met de reden als de stap vastloopt,
  zodat het rapport het meldt in plaats van te zwijgen;
- na elke wijziging aan dat bestand wordt gecontroleerd of elke naam die in een
  functie wordt gebruikt ook ergens wordt gezet. Die controle vond deze fout in
  een seconde.

**Les:** een vervanging die niets vervangt is een stille fout, en
|| echo maakt van een crash een geruststelling. Beide moeten zichtbaar zijn.

---

## 7ooo. De mail loopt weer, en nu de duiding — 28 september 2026

Na het herstel van de teller: 29 huurwaarnemingen waarvan 13 van Kamernet, en
62 objecten uit de gewone Funda-attenderingen. De stap doet het weer.

**Wat er niet uit te lezen was:** Kamernet leverde 14 objecten uit 42 mails.
Terecht overgeslagen of niet begrepen is een heel verschil, en dat stond er
niet. De mailstap telt nu ook wat er bewust is overgeslagen, met de reden, en
bewaart een paar voorbeelden. Levert een bron niets en is er ook niets
overgeslagen, dan komt het onderwerp van zo'n mail in de diagnose te staan.

**Vendr en business leveren nul objecten uit vijf mails.** Daar is nog geen
parser voor; het rapport noemt nu het onderwerp van zo'n mail, zodat duidelijk
is wat er gemaakt moet worden.

**De plakcontrole zeurt niet meer** over de Kamernet-lijst zodra die bron via
de mail binnenkomt.

---

## 7ppp. Geplakte verkopen kregen een datum die niet bestaat — 28 september 2026

De brief schreef: "in dezelfde Krayenhofflaan zijn deze maand vier andere
panden verkocht". Dat klopt niet. De 505 geplakte verkopen dragen allemaal de
datum van het inlezen, want Funda toont geen verkoopdatum. Het model las dat
als "vandaag verkocht" en maakte er "deze maand" van.

**Twee maatregelen.** In de geschiedenis krijgt zo'n gebeurtenis de tekst
"verkoopdatum onbekend; uit een geplakte lijst", herkenbaar aan de bron. En in
de opdracht staat dat verkopen met bron funda-verkocht-plak geen datum hebben:
wel dat een pand verkocht is en hoeveel er in een straat verkocht zijn, maar
nooit wanneer.

**Wat het niet oplost:** de verkopen tellen wel mee in de prijsreeks met de
datum van vandaag. Voor de mediaan maakt dat niet uit, voor een tijdreeks wel.
Zodra de verkopen via de attendering binnenkomen, hebben ze hun eigen datum uit
de mail en is dit vanzelf opgelost voor alles wat daarna komt.

---

## 7qqq. "Ontbreekt" zei niet wat er ontbrak — 28 september 2026

In het log van 28 september stond "MAIL_USERNAME of MAIL_PASSWORD ontbreekt",
terwijl de run ervoor 42 Kamernet-mails las. Die regel stond onder de kop van
de gezondheidsstap, wat verwarring gaf: uitvoer van een vorige stap kan in
GitHub een fractie later in het log belanden. Het script zelf draait normaal.

**Wat er niet uit af te leiden was:** welke van de twee ontbrak, en of het
secret leeg is of niet is doorgegeven. De stap meldt nu bij elke run
"Mailgegevens: gebruikersnaam aanwezig, wachtwoord ONTBREEKT" en noemt de twee
plekken waar het mis kan gaan: het secret in de repo, of het env-blok bij die
stap.

**Ter controle nagelopen:** in de workflow staat MAIL_USERNAME op drie plekken,
een keer bij de mailstap en twee keer bij het versturen van de brief. Alleen
die eerste geeft hem als omgevingsvariabele door; bij de andere twee is het een
instelling van de mailactie zelf. Dat is goed.

---

## 7rrr. Hoeveel panden hebben nu echt gegevens? — 28 september 2026

Het rapport meldde hoeveel panden er gevolgd werden en hoeveel er nog wachtten,
maar niet hoeveel er daadwerkelijk gegevens hebben. Dat was alleen uit een
aftreksom te halen.

**Nu staat het er:** hoeveel panden BAG-gegevens hebben en hoeveel woningen dat
samen zijn, hoeveel er een energielabel hebben, hoeveel er nog nooit zijn
nagekeken en hoeveel er geen pand-id opleverden.

Op de stand van 28 september is dat: 1653 gevolgd, 1351 met BAG-gegevens, 114
nog nooit nagekeken en 188 zonder pand-id. Die 188 is de groep die daarna aan
de beurt is; dat is bijna een op de acht en te veel om toeval te zijn.

---

## 7sss. Twee verkopen werden een prijsverlaging — 28 september 2026

De brief meldde: "Palmstraat 40 ging €50.000 omlaag naar €485.000, de enige
echte prijsverlaging van vandaag". Dat klopt niet. In de geplakte lijst staat
dat adres twee keer: verkocht voor €535.000 en voor €485.000. Dat zijn twee
transacties op onbekende momenten, geen verlaging.

**Nu** worden prijswijzigingen alleen gemeld voor panden die te koop staan, en
nooit voor waarnemingen uit een geplakte lijst. Hetzelfde geldt in de
geschiedenis per pand.

**Waarom dit typerend is:** de geplakte lijst bevat jaren aan verkopen zonder
datum. Elke redenering die tijd of volgorde veronderstelt, klopt daar niet. Dat
was al geregeld voor de tekst van de brief, maar niet voor deze berekening.

---

## 7ttt. Welke versie draait er eigenlijk? — 28 september 2026

Twee runs achter elkaar toonden de oude tekst "MAIL_USERNAME of MAIL_PASSWORD
ontbreekt", terwijl die regel niet meer in het script staat en er maar een
script is dat de mailbox leest. Mark had het nieuwe bestand wel geuploud. Dan
draaide de run dus op een andere versie, en daarover kun je blijven praten of
je kunt het meten.

**Nieuwe eerste stap in de workflow:** hij toont de commit en de branch, en
controleert per script of een kenmerk van de nieuwste versie erin staat. Bij
funda_mail.py is dat het woord "Mailgegevens:", bij marktprijzen_bag.py de
functie is_verkocht, enzovoort. Staat er NIET de nieuwste versie, dan is de
discussie meteen voorbij.

**Waar het meestal aan ligt:** de run is gestart voordat de commit binnen was,
of het bestand is naar een andere branch gegaan. De stap toont beide.

---

## 7uuu. indebuurt.nl als bron — 28 september 2026

Werd niet uitgelezen. Een eigen RSS-adres is er niet; het is een DPG-site.
De hoofdredacteur omschrijft het platform zelf als gericht op de aangename
kanten van het leven, winkelen en uitgaan en inspirerende stadsgenoten. De
opbrengst voor vastgoed zal dus dun zijn.

**Toegevoegd als smalle zoekopdracht** via Google News: indebuurt Nijmegen
samen met wonen, woningmarkt, huurwoning of nieuwbouw. Zo komt alleen binnen
wat ergens over gaat. Levert het na een maand niets bruikbaars op, dan kan die
feed er zonder verlies weer uit.

**Wat we van die site niet nodig hebben:** besluiten over splitsen en
verkameren staan in de officiele bekendmakingen, en marktnieuws komt uit de
vakmedia. Een stadssite voegt hooguit toe wat er in een buurt speelt buiten de
formele kanalen om.

---

## 7vvv. Een huur van €2.738 voor een gezinswoning — 28 september 2026

**Mark:** zit er in de waarnemingen uberhaupt een pand dat zo'n huur vraagt, en
is dat vergelijkbaar met dat pand aan de Krayenhofflaan?

**Nee.** Die €2.738 voor 116 m2 is €23,6 per m2, en dat hoort bij een
appartement van 45 m2, niet bij een gezinswoning. De waarnemingen kwamen bijna
allemaal uit kleine eenheden van Kamernet en Pararius, en het script trok die
prijs per m2 door naar een groot pand. Kleine woningen brengen per m2 veel meer
op dan grote; dat doortrekken is geen meting maar extrapolatie.

**Drie aanpassingen:**
- zonder metingen in de eigen grootteklasse wordt er niet meer doorgerekend met
  metingen uit een andere klasse; dan geldt de referentie, die als aanname
  wordt gemarkeerd en dus geen koopsignaal oplevert;
- de bron noemt uit welke grootteklasse de waarnemingen komen, bijvoorbeeld
  "wel klein (100% van de waarnemingen)";
- metingen uit een andere klasse die wel meetellen, wegen half.

Getest: met vijf metingen in de eigen klasse rond €15/m2 komt de huur op €17
en de maandhuur op €1.972; zonder die metingen op de referentie van €18.

**Wat dit niet oplost:** de referentie per buurt is zelf grootteblind en een
aanname. De beste manier om dat te vervangen is huidige_huur.txt: wat jullie
zelf vragen per pand, met oppervlakte erbij. Dat zijn echte cijfers uit de
eigen portefeuille en die maken de referentie meteen hard.

---

## 7www. Huur splitsen op segment, niet alleen op oppervlakte — 28 september 2026

**Mark:** een gereguleerde huur is een uitkomst van het puntenstelsel, een
vrije-sectorhuur van de markt. Voor een vrije-sectorpand moet je naar
vergelijkbare vrije-sectorwoningen kijken, niet naar wat een kleine
gereguleerde woning vraagt.

**Zo gebouwd.** De grens is te berekenen uit de tabel die we al hebben: de
maximale huur bij 186 punten, €1.228,07 per maand. Een advertentie die meer
vraagt zit per definitie in de vrije sector, ook zonder dat we de punten van
dat pand kennen.

- waarnemingen worden nu ook per segment bewaard, en per segment en
  grootteklasse;
- valt een pand boven de 187 punten, dan tellen alleen vrije-sectoradvertenties
  mee. De puntentelling die het script al maakt bepaalt dat;
- zonder puntentelling blijft het segment open en verandert er niets.

Getest op de Krayenhofflaan: met vier vrije-sectorwoningen van rond €16 per m2
en zes kleine gereguleerde appartementen komt de huur op €2.017 in plaats van
€2.738.

**Nog niet gebouwd, wel Marks idee:** de maximale huur bij de eigen
puntentelling als ondergrens gebruiken voor een vrije-sectorpand. Dat is
logisch, want onder het wettelijk maximum ga je nooit verhuren. Het vraagt wel
dat de puntentelling compleet is, en die is nu een ondergrens omdat keuken,
sanitair en verwarming ontbreken.

---

## 7xxx. De grens tussen middenhuur en vrije sector schuift elk jaar — 28 september 2026

**Mark:** die lijst wordt geupdatet; hoe zorgen we dat dat automatisch meegaat?

De huurprijstabel wordt per 1 januari geindexeerd, en daarmee verschuift de
grens tussen middenhuur en vrije sector. Rekent het script dan nog met de oude
tabel, dan belandt een pand in het verkeerde segment zonder dat iemand het
merkt.

**Drie maatregelen, samen sluitend:**
- de regelgevingsmonitor volgt nu het Besluit huurprijzen woonruimte
  (BWBR0003237), waarin bijlage I met de tabel staat, en de Uitvoeringswet
  huurprijzen woonruimte. Verandert dat besluit, dan staat het in de brief;
- bij de tabel in wwso.py staat nu een peildatum en de bron;
- het gezondheidsrapport controleert of die peildatum van het lopende jaar is.
  Is hij ouder, dan komt er een melding met de vindplaats van de nieuwe tabel.

Getest: met peildatum 2026 staat het op OK, met 2025 komt de melding met de
verwijzing naar het besluit.

**Bewust niet automatisch ingelezen.** De tabel staat als bijlage in de
wettekst en heeft elk jaar een iets andere opmaak; die blind uitlezen levert
stille fouten op in precies het getal waar alles aan hangt. Een melding met de
vindplaats, en dan een handmatige controle van twee minuten, is hier
betrouwbaarder.

---

## 7yyy. Label, labelsprong, verhuur in het complex, en de juiste buurt — 29 september 2026

**Drie punten van Mark na de brief van 29 september.**

**1. Het energielabel werd niet genoemd, terwijl een labelsprong beslist of een
pand in de vrije sector komt.** Terecht, en het is nu de kern van het dossier:
het huidige label staat erbij, en daaronder wat een sprong oplevert. Voor de
Burg. Hustinxstraat 46 (105 m2, WOZ €410.000, label E): nu 155 punten, met
label B 188 punten, dus van een wettelijke maximumhuur naar de vrije sector.
Haalt geen enkel label de 187, dan staat dat er ook: "zelfs met label A++
blijft het op 138 punten".

**2. Eerdere verhuur in hetzelfde complex werd niet bijgehouden.** Nu wel:
huuradvertenties zijn gebeurtenissen in de pandgeschiedenis geworden, met
prijs, oppervlakte en of het inclusief servicekosten was. Ze tellen ook mee in
de straatprecedenten. Bij een appartement in een complex is "wat werd hier
eerder voor gevraagd" het directste antwoord op de vraag wat je kunt vragen.

**3. Het portret ging over een andere buurt dan het uitgelichte pand.** Dat las
als twee losse brieven. Staat het uitgelichte pand in een andere buurt dan de
rotatie aanwijst, dan wint het pand.

**Nog open, uit dezelfde brief:** de aanloopperiode van drie maanden leegstand
geldt nu voor elk pand. Bij een pand dat al in de vrije sector zit en een goed
label heeft, is dat te ruim; daar kun je vaak direct verhuren. Dat wordt een
aanname die afhangt van de staat, en die wil ik pas maken als de eigen
bouwkosten er zijn.

---

## 7zzz. Een gereguleerd pand met een markthuur doorgerekend — 29 september 2026

**Mark:** dit object komt in de middendure huur, dat is gereguleerd, dus je
moet naar de punthuur kijken en niet naar de markthuur.

**Klopt, en de begrenzing bestond al maar greep niet.** Het script kapt de huur
af op het wettelijk maximum zodra het pand onder de 187 punten zit, maar dat
kan alleen als de WOZ bekend is. Bij de Burg. Hustinxstraat 46 was die
onbekend, dus viel het terug op de markthuur van €2.100 en presenteerde de
brief een richtprijs van +3% als kans.

**Narekening:** bij een WOZ van €410.000 heeft dat pand 155 punten en een
maximumhuur van €1.015. Minder dan de helft van waar mee gerekend is.

**Wat er nu gebeurt zonder WOZ:** het script rekent uit bij welke WOZ het pand
op 187 punten komt. Voor dit pand is dat €1.032.974, dus bij elke realistische
WOZ is het gereguleerd. Dat staat in het dossier, met de zin dat de gerekende
markthuur daaronder niet is toegestaan. En de richtprijs krijgt een "let op":
geen koopsignaal maar een bovengrens.

**Dezelfde berekening laat zien wat verduurzamen doet:** met label B komt
hetzelfde pand al bij een WOZ van €396.743 in de vrije sector, tegen €1.032.974
bij label E. Dat is de kruising die Mark zocht, nu met een getal.

**En een fout van mij bij het bouwen:** twee invoegingen landden niet omdat de
ankertekst niet meer klopte, net als gisteren. Deze keer wel gecontroleerd voor
ik verder ging.

---

## 8a. Waarom die dure appartementen duur zijn — 29 september 2026

**Mark:** die appartementen met een hogere huur, hadden die een beter label of
waren ze groter?

**Dat kunnen we niet zien, en dat is een structureel gat.** Huuradvertenties
hebben geen energielabel, en wij kunnen het niet opzoeken: Pararius en Kamernet
tonen alleen een straatnaam zonder huisnummer. Zonder adres geen EP-Online,
dus van geen enkele huurwaarneming kennen we label, WOZ of punten. Voor de
segmentindeling gebruiken we daarom de gevraagde huur als maat, en dat werkt
juist omdat het geen label nodig heeft.

**Wat de eigen lijst wel laat zien:** Hertogplein 49 m2 voor €1.995 is €41 per
m2, Grotestraat 80 m2 voor €2.450 is €31, Bijleveldsingel 95 m2 voor €1.800 is
€19. De duurste per m2 zijn de kleinste, en alle drie gemeubileerd met korte
contracten. De hoge huur komt van meubels en shortstay, niet van een beter
label of meer meters.

**Daarom ook dit:** uit de Kamernet-mails wordt nu vastgelegd of iets
gemeubileerd, gestoffeerd of kaal is, zoals we bij de geplakte lijst al deden.
Zo kunnen gemeubileerde shortstay-advertenties uit de mediaan worden gehouden
in plaats van hem op te drijven.

---

## 8b. De WOZ zelf schatten — 29 september 2026

**Mark:** kunnen we de WOZ niet zelf berekenen in plaats van hem elke keer op
te zoeken?

**Hoe de gemeente het doet, opgezocht.** De WOZ van een belastingjaar is de
marktwaarde op 1 januari van het jaar ervoor, de waardepeildatum; voor 2026 is
dat 1 januari 2025. De gemeente gebruikt modelmatige waardebepaling: verkoop-
cijfers van vergelijkbare woningen rond die datum, gecombineerd met kenmerken
als woningtype, bouwjaar, ligging, onderhoud en gebruiksoppervlakte. Een
kernstap daarin is dat verkoopcijfers worden herleid naar de peildatum.

**Die stap kunnen wij nadoen**, want we hebben de CBS-prijsindex al. De
vraagprijs van een pand wordt teruggerekend naar 1 januari 2025 en dat is de
schatting. In de test: vraagprijs €425.000 geeft een geschatte WOZ van
€399.000, net boven de grens van €396.000.

**Wat we niet nadoen**, en dat staat er bij elke schatting bij: onderhoud,
ligging en woningtype zitten er niet in, en een vraagprijs is geen
verkoopprijs. De schatting is goed genoeg om te zien of een pand in de buurt
van de grens komt, niet om op te varen. Bij de €399.000 hierboven is dat
precies de conclusie: dit pand moet je opzoeken, want de schatting zit er
€3.000 vanaf.

**Volgende stap als we het willen verbeteren:** niet de vraagprijs gebruiken
maar de mediaan van verkochte panden in dezelfde buurt en grootteklasse, ook
herleid naar de peildatum. Daarvoor hebben we nu 505 verkopen, maar zonder
verkoopdatum; zodra verkopen via de attendering met datum binnenkomen, kan dat.

---

## 8c. De WOZ-schatting ijkt zichzelf — 29 september 2026

**Mark:** verkoopprijzen worden niet gepubliceerd, alleen de laatste vraagprijs.
Wordt de berekening per object ergens gepubliceerd, en kunnen we een leereffect
inbouwen met de WOZ-waarden die we zelf opzoeken?

**Publicatie:** de berekening per object is niet openbaar. Het taxatieverslag,
met de vergelijkbare verkopen waarop de waarde rust, krijgt alleen de eigenaar
via de gemeente of MijnOverheid. Wel openbaar is het verantwoordingsdocument
dat elke gemeente bij de Waarderingskamer indient: daarin staat hoe het model
werkt en hoe verkoopcijfers naar de peildatum worden herleid, maar niet per
pand.

**Het leereffect is gebouwd.** Voor elk pand met een ingevoerde WOZ rekent het
script de schatting opnieuw uit en vergelijkt die met de werkelijke waarde. De
mediaan van die verhouding wordt de correctie, de spreiding zegt hoeveel
vertrouwen de schatting verdient. Hoe meer WOZ-waarden Mark invoert, hoe beter
de schatting voor de panden waar we hem niet van kennen.

Getest op veertig panden met een ingebouwde afwijking van 8%: de kalibratie
vond 0,926 terug met een spreiding van 3,7%. En het verandert de conclusie:
voor een pand van €425.000 gaat de schatting van €399.000 (boven de grens) naar
€370.000 (eronder).

**Het rapport zegt wanneer je kunt stoppen met opzoeken:** onder acht panden te
weinig, bij een spreiding boven 7% blijven opzoeken, en daaronder alleen nog
bij grensgevallen. Dat is precies het punt dat Mark beschreef.

---

## 8d. WOZ schatten uit kenmerken in plaats van uit prijzen — 29 september 2026

**Mark:** verwijs niet naar verkoopprijzen maar naar oppervlakte, label en
buurt- of straatgemiddelde. Een vraagprijs zegt weinig over de WOZ, en dat
verhaal dat een verkoopprijs standaard tien procent boven de WOZ van een jaar
eerder ligt, moet eerst getoetst worden.

**Deels eens.** De WOZ is wettelijk de marktwaarde op de peildatum, dus hij
hangt wel degelijk met verkoopprijzen samen. Maar wij hebben geen
verkoopprijzen, alleen vraagprijzen, en die relatie is rommelig. Een model op
kenmerken is beter en gebruikt bovendien alleen waarden die Mark zelf heeft
opgezocht.

**Gebouwd:** de WOZ per vierkante meter uit de eigen invoer, op straatniveau
vanaf drie panden, anders op buurtniveau vanaf vijf, anders stadsbreed vanaf
vijftien. Die schatting gaat voor; alleen zonder genoeg gegevens valt hij terug
op de herleide vraagprijs.

**En de twee methoden worden tegen elkaar gemeten**, op de panden waarvan de
WOZ bekend is, waarbij het pand zelf niet meetelt in zijn eigen schatting. Het
rapport toont de mediane fout per methode. In een test met zestig panden:
kenmerken 5,6%, prijs 7,6%. Op Marks eigen cijfers kan dat anders uitvallen, en
dan beslist de data.

**Dat marktverhaal wordt meteen getoetst:** de kalibratie rekent uit hoeveel de
vraagprijs mediaan boven de herleide WOZ ligt. Staat daar 1,10, dan klopt het
verhaal; in de testdata stond er 0,82, dus het is geen natuurwet.

**Wat nog ontbreekt:** het energielabel in het model. Daarvoor is nodig dat we
van panden met een bekende WOZ ook het label kennen, en dat lukt alleen voor
panden die in het aanbod stonden. Zodra dat er genoeg zijn, kan er een
labelcorrectie bij.

---

## 8e. Niet constateren maar uitleggen — 29 september 2026

**Mark:** bij een melding brandveilig gebruik weet ik nu dat er iets gemeld is,
maar niet wanneer het moet en waar het aan moet voldoen. Dat geldt voor meer
onderwerpen; niet willekeurig in de brief, maar zodra zo'n aanvraag langskomt.

**Het stuk is er**, met de eisen opgezocht: sinds 1 januari 2024 is de
vergunningplicht vervallen en geldt een meldplicht uit het Besluit bouwwerken
leefomgeving. Verplicht bij een woonfunctie voor kamergewijze verhuur, waarvan
sprake is bij vijf of meer wooneenheden in het niet-gemeenschappelijke deel.
Ten minste vier weken voor ingebruikname via het Omgevingsloket, en eerder in
gebruik nemen mag niet. Bij de melding hoort een plattegrond per bouwlaag met
oppervlakte en bestemming per ruimte, het maximale aantal personen, en
ingetekend waar de brand- en rookwerende scheidingen, vluchtroutes,
zelfsluitende deuren, vluchtrouteaanduidingen, noodverlichting en blusmiddelen
zitten. Inhoudelijk vraagt het Bbl bij kamergewijze verhuur doorgekoppelde
rookmelders in de verblijfsruimten en op de vluchtroute. De gemeente kan in een
maatwerkvoorschrift extra eisen stellen.

**De trigger bestond al:** de achtergrondstap krijgt de bekendmakingen en de
publicaties samen mee en kiest het stuk dat aansluit. Getest met de tekst van
een melding: hij koos vanzelf dit stuk.

**Nieuw is de dekkingscontrole.** Het rapport vergelijkt de soorten
bekendmakingen die we herkennen met de achtergrondstukken die er zijn. Nu
ontbreken er vier: onrechtmatig gebruik, onttrekking, samenvoeging en sluiting.
Bij die soorten blijft het dus bij constateren. Dat is precies de lijst om de
komende tijd af te werken.

---

## 8f. De vier ontbrekende onderwerpen — 29 september 2026

De dekkingscontrole wees vier soorten aan zonder achtergrondstuk. Die zijn er
nu, met de wettelijke grond erbij. Vijfentwintig stukken, en elk soort
bekendmaking heeft er een.

- **Onttrekking van woonruimte:** artikel 21 Huisvestingswet verbiedt vijf
  handelingen zonder vergunning, waaronder onttrekken, samenvoegen en omzetten.
  Alleen in de aangewezen categorie en het aangewezen gebied; een
  eigenaar-bewoner met een kantoor aan huis valt erbuiten. De gemeente kan
  compensatie eisen en de vergunning voor een termijn verlenen.
- **Samenvoegen van woningen:** valt onder hetzelfde artikel, want er verdwijnt
  zelfstandige woonruimte. Voor de WOZ het omgekeerde van splitsen.
- **Onrechtmatig gebruik en handhaving:** verkameren of splitsen zonder
  vergunning levert een bestuurlijke boete op, en de Raad van State bevestigde
  dat "onttrekken" in een verordening ook omzetten en verbouwen kan omvatten.
  Huurder en verhuurder kunnen allebei in overtreding zijn, en een vergunning
  kan worden ingetrokken.
- **Sluiting van een pand:** op grond van artikel 13b Opiumwet door de
  burgemeester, of artikel 17 Woningwet bij bouwovertredingen met gevaar op
  herhaling. Voor een verhuurder zwaar: de bewoner moet eruit, het huurcontract
  kan worden ontbonden en daarna kan de Wet Victor worden ingezet.

**Een fout die de test blootlegde:** bij "samenvoegen" en bij "handhaving" koos
het script het stuk over de leefbaarheidstoets, omdat dat op algemene woorden
als "vergunning" matchte. De score telt nu zwaarder voor specifieke
trefwoorden: meerwoordige termen en lange woorden wegen meer dan korte,
algemene. Daarna kozen alle zes de geteste soorten het juiste stuk.

---

## 8g. Hoe ver is het zelflerend? — 29 september 2026

**De keten die er al is:** onderwerpen_signaal.py vindt termen die in het
nieuws terugkomen, toetst of er al een achtergrondstuk over bestaat en schrijft
de rest als voorstel weg. Die toets is streng op de hele term, zodat "Wet vaste
huurcontracten" niet wordt afgedaan als gedekt omdat er ergens "huurcontract"
staat.

**Wat ontbrak:** die voorstellen bleven in een bestand staan dat niemand leest.
Het rapport toont ze nu, met de eerste vier erbij. Daarmee is de keten sluitend:
het script signaleert, het rapport laat het zien, en in een gesprek komt er een
stuk met bronnen bij.

**Waar ik bewust stop.** Het script schrijft zo'n stuk niet zelf. De pijplijn
kan niet zoeken en niet controleren, en een juridisch stuk zonder nagelopen
bron is precies wat we deze week overal uit hebben gehaald: de vijf jaar voor
kamers, de aangewezen wijk, de markthuur bij een gereguleerd pand. Alle drie
klonken ze goed en waren ze fout. Een stuk dat automatisch in de rotatie komt
en elke maand terugkeert, is een fout die zichzelf herhaalt.

**Het handwerk is klein en het levert veel op:** het rapport noemt het
onderwerp, ik zoek de bron op en schrijf het stuk, en de dekkingscontrole
bevestigt dat het gat dicht is. Die drie stappen samen kostten vandaag tien
minuten voor vier onderwerpen.

---

## 8h. Aanvullen doet hij, afvoeren niet — 29 september 2026

**Mark:** haalt hij elke keer dezelfde panden op, of vult hij het bestand aan?

**Allebei, en daar zit het probleem.** verkopen.txt is aanvullend en er wordt
nooit iets uit verwijderd. Maar de panden worden niet opnieuw opgehaald: de
attenderingen melden alleen nieuw en gewijzigd aanbod, en de BAG-gegevens staan
in een cache. Een pand blijft dus in de tabellen staan omdat het in het bestand
staat, niet omdat we vandaag hebben gezien dat het er nog staat. Vandaar elke
dag dezelfde rijen met een oplopend aantal dagen te koop.

**Nieuw in het rapport:** hoeveel panden te koop staan, hoe lang geleden ze
voor het laatst zijn bevestigd, en hoeveel er langer dan zestig dagen niet meer
zijn gezien. Die laatste groep is waarschijnlijk al van de markt en rekent wel
mee in de buurtmedianen.

**De oplossing is de geplakte verkooplijst**, die panden als verkocht markeert,
of verkopen via de attendering zodra dat filter aanstaat. Zolang dat niet
loopt, is dit cijfer de waarschuwing.

---

## 8i. De VvE-bijdrage ontbrak in de businesscase — 29 september 2026

**Mark:** bij het uitgelichte appartement is de VvE-bijdrage €275,15 per maand,
en die zit niet in de doorrekening. Stookkosten lopen apart via een eigen ketel,
dus dit is groot onderhoud. Die kosten zijn niet door te belasten aan de
huurder en horen dus in de businesscase.

**Klopt, en het ontbrak volledig.** €275,15 per maand is €3.302 per jaar,
rechtstreeks van de nettohuur af.

**Gebouwd:** vve_kosten.txt, een regel per adres met de maandbijdrage, zoals
woz.txt. De bijdrage gaat van de huur af, en het exploitatiepercentage wordt
verlaagd omdat de VvE onderhoud van casco en gemeenschappelijke delen en de
opstalverzekering al dekt. Zonder die verlaging zou onderhoud er twee keer in
zitten.

**Een aanname die aandacht verdient:** welk deel van de exploitatiekosten de
VvE dekt. Op 55% scheelt de hele VvE netto maar €530 per jaar, want die 20%
exploitatie bevatte al bijna evenveel onderhoud. Op 0% kost hij €3.302. Het
dossier noemt daarom beide uitkomsten en zegt dat het een aanname is; het
aandeel is te zetten met de omgevingsvariabele OPEX_DEEL_VVE.

**En zonder ingevoerde bijdrage:** een pand dat in een complex zit krijgt nu de
melding dat de richtprijs te hoog is zolang het bedrag ontbreekt, en de brief
mag het dan niet als kans presenteren. Het rapport telt van hoeveel panden de
bijdrage bekend is.

**Marks bredere punt klopt ook:** appartementen in een VvE zijn hierdoor
structureel minder interessant dan de tabel suggereerde, en dat gold voor elke
regel met "complex" in het dossier.

---

## 8j. Vier punten uit de brief van 29 september

**1. De VvE-bijdrage stond er niet in.** Oorzaak: in mijn sjabloon stond het
voorbeeld uitgecommentarieerd, en een regel met een hekje wordt overgeslagen.
De €275,15 voor de Burg. Hustinxstraat 46 staat nu als echte regel in het
bestand, met de waarschuwing erbij dat een hekje de regel uitschakelt.

**2. Het stuk over sluiting kwam uit de lucht vallen.** Zonder aansluiting bij
het nieuws koos het script toch een stuk, gewoon het eerstvolgende uit de
rotatie. Dat maakt de brief langer zonder hem beter te maken. Nu geldt: geen
aansluiting, geen achtergrondstuk.

**3. De aanhef volgt het moment.** Goedemorgen, goedemiddag of goedenavond,
naar de klok van de run. Met BRIEF_AANHEF is het te overrulen.

**4. De weekeditie begint vrijdagnacht** in plaats van zondagochtend, en werkt
dan de hele pandgeschiedenis bij: de rem van 500 panden per ronde gaat eraf.
Een GitHub-job stopt na zes uur, dus "een dag laten draaien" kan niet; het
script stopt zelf na vier uur en bewaart wat af is. De brief komt daarmee in de
loop van het weekend binnen. De modus geldt van vrijdagavond tot en met zondag,
zodat een run die 's nachts begint de juiste editie oplevert.

---

## 8k. Drie fouten en een langere adem — 29 september 2026

**1. De WOZ-kalibratie stond op nul door een leesfout van mij.** Het
indexbestand heeft "reeks" op het hoogste niveau; ik las hem onder een sleutel
"landelijk" die niet bestaat. Daardoor gaf elke schatting niets terug en telde
geen enkel pand mee. Nu worden beide vormen geaccepteerd; in de test levert
hetzelfde bestand twaalf geijkte panden op. Marks redenering klopte: die
WOZ-waarden zijn juist ingevoerd bij panden die te koop stonden.

**2. Geen enkel energielabel, en ook dat was een naamfout.** De workflow gaf de
geschiedenisstap EP_ONLINE_KEY mee, terwijl de code EP_API_KEY leest. Zonder
sleutel geeft EP-Online niets terug en de stap sloeg elke fout stil over. De
workflow geeft nu de goede naam door, en het script meldt het voortaan hardop
als die sleutel ontbreekt in plaats van nul labels op te leveren.

**3. Waarom vier uur en niet vijf?** Nergens goed voor: de job stopt na 330
minuten en de rest van de pijplijn heeft daar zo'n 25 minuten van nodig. Het
budget staat nu op 295 minuten.

**4. En de zes uur is te overbruggen.** Blijft er werk liggen, dan legt het
script vast hoeveel panden er nog wachten, en start de workflow zichzelf
opnieuw met een teller. Elke ronde krijgt weer zes uur; na drie vervolgrondes
stopt het, zodat het niet blijft rondzingen. Een vervolgronde gaat altijd
alleen naar Mark, niet naar zijn vader.

---

## 8l. Drie fouten uit de brief van 29 september, middag

**1. Dubbele aanhef.** "Goedemiddag pa," stond er twee keer: het script kende
alleen "beste", "hoi" en dat soort woorden als aanhef, herkende de eigen groet
van het model niet en zette er een tweede voor. De nieuwe groeten staan nu in
die lijst.

**2. De VvE-bijdrage stond alleen in de tekst, niet in de som.** Ik had hem
toegevoegd aan het dossier maar niet aan de functie die de richtprijs
uitrekent; die draait op een ander punt in het script. Daardoor bleef de
richtprijs onveranderd op €439.280. Nu telt hij mee: voor de Burg.
Hustinxstraat 46 gaat de richtprijs van €427.411 naar €416.179, en daarmee van
+1% naar -2% ten opzichte van de vraagprijs. Het pand valt dus af op precies de
kosten die Mark opmerkte.

**3. De WOZ-kalibratie stond nog steeds op nul**, en ook dat was een koppeling.
De waarden staan in woz.txt onder een genormaliseerde sleutel en worden pas
later aan de panden gehangen, terwijl de ijking aan het begin van de run draait.
Nu leest die functie het bestand zelf, met dezelfde sleutel, en vangt hij beide
vormen af waarin een waarde kan staan. In de test: tien panden, correctie
0,980, spreiding 3,0%.

**Wat deze drie gemeen hebben:** het waren alle drie koppelfouten, geen
denkfouten. De logica klopte, maar hij stond op de verkeerde plek of las de
verkeerde sleutel. Dat is deze week het vaakst voorgekomen, en het is ook de
soort fout die een testrun niet laat zien zolang je alleen naar de tekst kijkt.

---

## 8m. Negen plekken, één berekening — 29 september 2026

De brief noemde €427.736 en de tabel €439.280 voor hetzelfde pand. Oorzaak: de
richtprijs werd op negen plekken in het bestand apart uitgerekend, en toen de
VvE-bijdrage erbij kwam kreeg de helft hem wel en de andere helft niet.

**Nu loopt alles langs richtprijs_van(w)**, die het scenario en de VvE van dat
pand pakt. Twee vergelijkingen tussen scenario's onderling blijven zonder VvE,
want die geldt daar voor beide kanten en verandert de uitkomst niet.

**De WOZ-kalibratie werkt:** 22 panden, correctie 1,041, spreiding ±23,9%. Dat
beantwoordt meteen het marktverhaal dat een verkoopprijs zo'n tien procent
boven de WOZ van een jaar eerder zou liggen: in onze cijfers ligt de WOZ juist
4% boven de naar de peildatum herleide vraagprijs. Maar met een spreiding van
bijna een kwart is dat geen wet, en het rapport zegt daarom terecht dat je de
WOZ moet blijven opzoeken.

---

## 8n. De wachtrij kwam nooit bij de achterblijvers — 30 september 2026

"146 nog nooit nagekeken" werd er elke ronde eentje meer in plaats van minder.
Oorzaak: de wachtrij zette panden uit het aanbod en de verkopen vooraan, en
sinds de 505 geplakte verkopen erin zitten vulden die in hun eentje de quota
van 500 per ronde. De achterblijvers kwamen dus nooit aan de beurt, hoe vaak er
ook werd gedraaid, en nieuwe adressen uit bekendmakingen kwamen er sneller bij
dan ze konden worden afgewerkt.

**Nu gaan panden die nog nooit zijn nagekeken voorop**, daarna het aanbod en de
verkopen, dan de rest, telkens de langst niet bekekene eerst. In de test met
600 verkochte en 146 nieuwe panden zitten alle 146 in de eerste ronde.

**Les:** een voorrangsregel die klopt bij honderd panden kan omslaan bij
zeshonderd. Dezelfde soort fout als bij de achtergrondstukken, waar een
algemeen trefwoord ging winnen zodra er meer stukken bij kwamen.

---

## 8o. COROP naast landelijk en provincie — 30 september 2026

Naar aanleiding van het ING-artikel. Van de vier bevindingen daarin konden we
er drie al maken: de oplopende rente meten we zelf en scherper, de landelijke
prijsontwikkeling komt uit het CBS, en lokale verschillen zien we in onze eigen
buurtcijfers. De prognose van +2,5% en +1% nemen we niet over; dat is een model
en geen meting.

**Wat ontbrak, was het niveau ertussenin.** De brief zette onze buurtmedianen
af tegen heel Gelderland, waar Winterswijk en Nijmegen in dezelfde bak zitten.
CBS-tabel 85819NED geeft per COROP-gebied de prijsindex, de ontwikkeling per
kwartaal en per jaar, het aantal transacties en de gemiddelde verkoopprijs,
ongeveer 22 dagen na afloop van een kwartaal. Nijmegen valt onder
Arnhem/Nijmegen.

**Naast elkaar, niet in plaats van.** Landelijk, provincie en COROP blijven
alle drie in beeld: lopen ze uiteen, dan is dat verschil zelf het nieuws. Loopt
alles gelijk op, dan noemt de brief alleen het COROP-cijfer.

**De regiocode wordt opgezocht, niet geraden.** Het CBS hernummert gebieden af
en toe, en een verkeerde code levert stilletjes de cijfers van een andere regio
op. Wordt het gebied niet gevonden, dan schrijft het script niets weg en meldt
het rapport dat.

**Wat we nog steeds niet kunnen meten:** het aanbod, oftewel hoeveel woningen
er te koop staan. Dat is in dit artikel juist de kern. Wij zien alleen wat via
onze attendering binnenkomt, dus groei in ons aanbod kan ook groei van onze
meting zijn. Een open bron bestaat er niet; NVM en brainbay publiceren het per
kwartaal als persbericht. Het aantal transacties uit deze tabel is het beste
alternatief dat wel meetbaar is.

---

## 8p. De ketting hield de ochtendbrief tegen — 30 september 2026

Om 10:48 was de brief van vanochtend nog niet verstuurd. Het annuleren van
gisteren is niet de oorzaak; dat raakt het schema niet.

**Wat wel:** de workflow heeft een concurrency-groep zodat er nooit twee runs
tegelijk draaien, en sinds gisteravond start een run zichzelf opnieuw als er
BAG-werk blijft liggen, tot drie keer, elk tot 5,5 uur. Een ketting die om half
acht 's avonds begint, loopt tot ver in de ochtend door en zet de geplande run
van 5:17 in de wachtrij in plaats van hem te laten draaien.

**Aangepast:** doorketenen gebeurt alleen nog in het weekend, waar die lange
inhaalronde ook voor bedoeld was. Doordeweeks stopt een run na zijn eigen
venster en blijft 5:17 vrij.

**Les:** een voorziening die een run langer laat duren, botst met een
voorziening die runs serialiseert. Allebei goed bedacht, samen een brief die
niet aankomt. Dat is precies het soort samenloop dat pas zichtbaar wordt in
gebruik, en niet in een test.

---

## 9. Van bouwjaar naar bouwkosten — het plan, 30 september 2026

Marks voorstel: koppel het bouwjaar aan het bouwbesluit dat toen gold, toets
dat met het energielabel en met vergunningen, bepaal daarna hoeveel vierkante
meter er werkelijk aan de buitenlucht grenst, en vermenigvuldig dat met een
prijs per maatregel. Subsidie voor verhuurders gaat er weer af.

Dat is vier stappen, en ze moeten in deze volgorde.

**Stap 1, gebouwd: bouwnorm.py.** De Rc-eisen per bouwjaarklasse staan erin,
opgezocht en consistent over meerdere bronnen: gevel 0,43 tot 1975, daarna
1,30, 2,00, 2,50, 3,50 en 4,50; dak begint op 0,86; vloer op 0,17. Voor 1965
golden er geen eisen. De huidige nieuwbouweis is gevel 4,7, dak 6,3, vloer 3,7,
en bij vervanging van een bouwdeel geldt altijd minimaal 1,3 voor gevel, 2,0
voor dak en 2,5 voor vloer.

Daaruit volgt per pand welke bouwdelen nog een ingreep vragen. Een pand uit
1968 vraagt alles; een pand uit 2005 niets. Het label is de tegenproef: label B
bij bouwjaar 1930 betekent dat er na de bouw is geisoleerd, en dan klopt de
tabel niet meer. Dat wordt gemeld in plaats van genegeerd. Bouwdelen die
volgens een vergunning al zijn aangepakt, vallen af.

**Stap 2, nog te bouwen: de geometrie uit de BAG.** Dit is het waardevolste
stuk en het is nog nergens gebruikt. De BAG bevat de omtrek van elk pand, dus
daaruit is te berekenen welk deel van de gevel aan een buurpand grenst en welk
deel aan de buitenlucht. Bij een tussenwoning hoeven alleen voor- en achtergevel;
bij een hoekwoning drie zijden. Het aantal bouwlagen volgt uit de
gebruiksoppervlakte gedeeld door het grondvlak. Bij een appartement in een
complex grenzen vloer en plafond aan verwarmde ruimten en tellen ze niet mee.
Precies wat Mark beschrijft, en het is rekenwerk en geen aanname.

**Stap 3: de prijs per maatregel per m2.** Dat is bouwkosten_eigen.txt, dat al
maanden wacht. Zonder die getallen blijft de uitkomst een aanname, hoe goed de
geometrie ook is.

**Stap 4: de subsidie.** Voor verhuurders bestaan er regelingen per maatregel
per m2. Die bedragen veranderen jaarlijks en moeten worden opgezocht, niet
geschat, en ze krijgen een peildatum zoals de huurprijstabel.

**Volgorde is hier het punt:** stap 2 zonder stap 1 geeft oppervlakten zonder
te weten wat eraan moet, en stap 3 zonder stap 2 geeft een prijs per m2 zonder
te weten hoeveel meters. Stap 4 kan pas als 2 en 3 kloppen, want subsidie
rekent ook per m2.

---

## 9a. De 3D BAG in eigen beheer — 30 september 2026

**Mark:** die bestanden wil ik zelf op GitHub hebben, bijgewerkt via de run als
er iets verandert, zodat we geen gat hebben als de bron wegvalt.

**Zo gebouwd, met een beperking.** Het landelijke bestand is ruim een gigabyte
en past niet in een repo; GitHub weigert bestanden boven 100 MB. Onze eigen
panden wel: een paar duizend regels met tien velden is enkele megabytes. Dus
niet de bron kopieren, maar onze eigen doorsnede ervan bewaren.

**Wat er per pand in komt:** buitenmuuroppervlak, dakoppervlak gesplitst in plat
en schuin, grondvlak, aantal bouwlagen, nokhoogte, maaiveldhoogte, daktype en
een kwaliteitsindicator. Dat laatste veld zegt of er AHN-dekking was; zonder
dekking zijn de waarden leeg of onbruikbaar en dat moet zichtbaar blijven.

**Hoogte hoeft dus niet te worden aangenomen.** Mijn eerste plan was omtrek maal
een aangenomen verdiepingshoogte; dat zou een schatting in de basis van de hele
keten zetten. De 3D BAG meet het met de landelijke laserhoogtemeting, en geeft
het buitenmuuroppervlak zelfs al uitgerekend.

**Bijwerken gebeurt alleen bij een nieuwe versie van de bron.** Staat er een
ander versienummer, dan wordt alles opnieuw opgehaald, want dan is de
hoogtemeting vernieuwd. Anders alleen panden die we nog niet hebben, 300 per
ronde doordeweeks en 2000 in het weekend.

**De velden worden gezocht en niet op een vaste plek verwacht**, zodat een
verandering in de opzet van de bron geen lege waarden oplevert zonder dat
iemand het merkt. Bij meer dan twintig fouten stopt de stap en meldt hij dat de
bron onbereikbaar of veranderd lijkt.

**Wat hierna komt:** de zijgevels die tegen de buren staan eraf halen, want dat
buitenmuuroppervlak is de hele schil. En bij een pand met meerdere woningen het
dak toerekenen aan de bovenste woning in plaats van aan alle eenheden.

---

## 9b. Hoeveelheden wel, prijzen niet — 30 september 2026

**Mark:** is er een bron voor de materiaalkosten van na-isoleren aan de
binnenzijde?

**Nee, en dat is geen gemakzucht.** Bouwkosten.nl, Archidat en het
Bouwkostenkompas zitten achter een abonnement, en bouwmarkten hebben geen open
prijsfeed. Scrapen is bovendien fragiel en tegen hun voorwaarden. Elk
landelijk gemiddelde dat ik wel zou vinden, zou een geschat getal in de basis
van de berekening zetten.

**Wat wel kan, is het stuk ervoor, en dat is het lastigste:** van vierkante
meters muur naar hoeveelheden materiaal. Dat volgt uit de opbouw en is
rekenwerk. Voor 62,4 m2 binnengevel bij 2,6 m hoogte: 41 stijlen, 154,6 meter
hout, 59 m2 isolatie, 68,6 m2 OSB, 68,6 m2 gipsplaat, 62,4 m2 stucwerk en
evenveel sloopwerk. De houtmaat 60 cm hart op hart, 10% houtaandeel, 10%
snijverlies op plaatmateriaal en 5% op isolatie.

**Met eigen prijzen erbij is het een berekening.** materiaalprijzen.txt heeft
een regel per post; ontbreekt er een, dan staat die apart in de uitkomst in
plaats van stilletjes op nul. In de test met vijf van de zes posten: €2.988 en
€47,89 per m2, met sloop zichtbaar als ontbrekend.

**Een punt dat hierbij hoort:** de houten stijlen vormen een koudebrug en
nemen ongeveer een tiende van het vlak in. De Rc van de constructie ligt
daardoor lager dan de Rd van het isolatiemateriaal. Voor de subsidie telt de Rd
van het materiaal, voor het energielabel de Rc van het geheel. Die twee door
elkaar halen levert een pand op dat de subsidie haalt maar het label niet.

**Nog te doen:** de twee methodes voor het geveloppervlak naast elkaar leggen,
het buitenmuuroppervlak uit de 3D BAG tegen omtrek maal hoogte uit de gewone
BAG. Lopen ze uiteen, dan weten we dat er iets niet klopt in de aanname over
welke muren aan de buitenlucht grenzen. En uit nokhoogte min maaiveld gedeeld
door het aantal bouwlagen rolt de werkelijke verdiepingshoogte, in plaats van
de 2,6 m die nu als invoer wordt meegegeven.

---

## 9c. Het eerste echte bouwkostencijfer — 30 september 2026

Factuur F2026-004 van Noordermeer Bouw, Eerste Oude Heselaan 88: voorzetwanden
met frame en folies, 38 m2 geisoleerd met 100 mm Soprema Efyos, plus een
afvalcontainer. €3.882,45 voor het werk en €425,88 voor de container, samen
€4.308,33 exclusief btw.

**Dat is €113 per m2 inclusief arbeid**, of €102 zonder de container. Daarmee
staat er voor het eerst een gemeten bedrag in bouwkosten_eigen.txt in plaats
van een aanname van het script.

**Belangrijk onderscheid met materiaalprijzen.txt:** dit is een aanneemsom,
materiaal en arbeid samen, van een aannemer. Die twee bestanden vullen dus
verschillende gaten: het ene voor als je zelf inkoopt en bouwt, het andere voor
uitbesteed werk. Voor een doorrekening van een aankoop is de aanneemsom de
juiste, want daar reken je niet met eigen uren.

**Twee dingen om na te gaan bij Mark:** of het plaatwerk en het stucwerk in die
prijs zitten of apart zijn gefactureerd, en wat de Rd van dat materiaal is.
Voor de ISDE-subsidie bij gevelisolatie geldt een minimum-Rd, en 100 mm is
dik genoeg om daar overheen te komen, maar dat moet uit het productblad komen
en niet uit een schatting.

---

## 9d. Drie bonnen, en een correctie op mijn eigen cijfer — 30 september 2026

**Correctie eerst.** Gisteren noteerde ik €113 per m2 uit de aannemersfactuur.
Dat was niet het hele plaatje: het plaatmateriaal is zelf gekocht bij
Sleiderink en zat dus niet in die aanneemsom. Met €20 per m2 aan platen erbij
komt binnenwandisolatie op €133 per m2, en dan nog zonder het hout.

**Wat er nu hard in staat, uit de bonnen:**
- OSB 3 mes en groef 18 mm: €6,93 per m2 (€9,98 per plaat 2440x590)
- gipsplaat Siniat AK 12,5 mm: €4,53 per m2 (€7,06 per plaat 2600x600)
- stucplaat RK 9,5 mm: €4,67 per m2 (€3,74 per plaat 2000x400)
- Knauf Brio vloerplaat 33 mm: €29,31 per m2 (€21,10 per plaat 1200x600)

Daarmee is vloerisolatie ook een gemeten post: €32 per m2 inclusief lijm en
randisolatiestroken, over 50,4 m2.

**Wat nog niet hard is, en waarom:**
- de isolatie. Knauf Acoustifit 150 mm, €31,91 per pak, tien pakken voor 38 m2.
  Hoeveel m2 er in een pak zit staat niet op de bon. Terugrekenen geeft €8,40
  per m2, maar dat is een afgeleide en geen bonprijs.
- het hout. Bouwmaat 11 november, €805,06, geboekt als aanbetaling klantorder
  zonder specificatie. Zonder aantal meters geen prijs per meter.

**De verhouding materiaal en arbeid is nu zichtbaar**, en dat is het nuttigste
van deze drie bonnen: materiaal komt op ongeveer €28 per m2 inclusief isolatie,
de aanneemsom op €113. Arbeid en marge zijn dus grofweg driekwart van de
rekening. Voor een pand dat je zelf verbouwt scheelt dat aanzienlijk, en dat
verschil stond nergens in het model.

**Het resultaat van deze ingreep:** van label F of E naar label A. Dat is
precies de sprong waar de labelkruising sinds gisteren op rekent, en nu is er
een echt pand waar hij aan geijkt kan worden.

---

## 9e. De hele verbouwing in cijfers — 30 september 2026

Met de laatste drie bonnen erbij is de Eerste Oude Heselaan 88 compleet genoeg
om als ijkpunt te dienen. Alles exclusief btw:

- Sleiderink 20-11-2025, vloerplaten, lijm, randstroken en OSB: €1.884,29
- Sleiderink 08-01-2026, isolatie, gipsplaat, stucplaat, primer, schroeven: €938,32
- Bouwmaat 11-11-2025, aanbetaling klantorder zonder specificatie: €805,06
- Bouwmaat 18-11-2025, twee rollen isolatietape: €26,49
- Hornbach 19-12-2025, 70 panlatten en zes platen OSB3: €188,63
- Hornbach 13-11-2025, een rol Miofol 125G: €82,60
- Noordermeer Bouw, werk inclusief frame, folies, isolatie en container: €4.308,33

**Samen €8.233,72 voor 38 m2 binnenwand en 50,4 m2 vloer**, en daarmee van
label F of E naar A.

**Nieuw hard cijfer:** isolatietape €0,53 per meter. Niet te herleiden blijven
de folie, want de maat van de rol staat niet op de bon, en de panlatten, want
de lengte per lat ontbreekt.

**Een bijvangst die het noteren waard is:** hetzelfde OSB3 met mes en groef
kostte €9,98 per plaat bij Sleiderink en €10,32 bij Hornbach. Drie procent
verschil op hetzelfde product, en dat is een van de weinige posten waar we
twee prijzen naast elkaar hebben.

---

## 9f. Prijzen met een peildatum, en indexeren met een bron die we al hebben

**Mark:** die bonnen zijn verouderd en zouden geindexeerd moeten worden.

**Terecht, en het hoeft niet geschat.** De CBS-bouwkostenindex halen we al op
voor de brief. Elke prijs in materiaalprijzen.txt heeft nu een peildatum, en
het script rekent hem daarmee om naar vandaag. Zonder peildatum blijft een
bedrag staan zoals het is, met die melding erbij, zodat niemand denkt dat het
actueel is.

**De begroting van de aannemer is completer dan de bonnen** en vult de twee
gaten die overbleven: hout €13,18 per balk van 3 meter is €4,39 per meter, en
de folie €102,04 per rol van 50 meter is €2,04 per meter. Ook staat er wat de
isolatie is: PIR 100 mm met Rd 4,54. Dat beantwoordt de subsidievraag, want de
eis ligt op 3,5.

**Een vergelijking die de moeite waard is.** Hetzelfde OSB 18 mm kost €6,93 per
m2 bij Sleiderink, €7,17 bij Hornbach en €7,98 in de begroting van de aannemer.
Maar gipsplaat gaat de andere kant op: €4,53 bij Sleiderink tegen €3,38 in de
begroting. Zelf inkopen scheelt dus niet bij elke post, en dat is precies het
soort detail dat je alleen ziet als je beide naast elkaar legt.

**Met alles erin komt de wandopbouw op €48 per m2 aan materiaal**, geindexeerd
naar vandaag, met stucwerk en sloop nog als ontbrekende posten. Tegenover de
€113 per m2 van de aannemer betekent dat: ruwweg €48 materiaal en €65 arbeid en
marge.

---

## 9g. De stukadoor, en een rekensom die niet sluit — 30 september 2026

Twee termijnen van €1.717,50, samen €3.435,00 exclusief 9% btw, voor 109 m2
wand en 39 m2 plafond aan de Eerste Oude Heselaan 88. Daarmee staat stucwerk er
als gemeten post in: €20 per m2 wand en €25 per m2 plafond.

**Een verschil in de opgave dat de moeite van het navragen waard is.** De
stukadoor schrijft 30 meter hoekstrips maal €7, wat €210 zou zijn, maar rekent
€280. Of het gaat om 40 meter, of om €9,33 per meter. Het totaal klopt wel,
want 2180 plus 975 plus 280 is precies de som van de twee termijnen. Voorlopig
staat €9,33 per meter in het bestand, met de opmerking erbij.

**En een datum die niet kan kloppen.** De eerste factuur vermeldt 25-2-2025 met
vervaldatum 5-3-2025, een jaar voor het werk, terwijl de tweede 11-3-2026 is en
beide naar week 9 en week 11 verwijzen. Vrijwel zeker een typefout bij de
stukadoor; voor het indexeren is 2026 aangehouden.

**Het 9%-tarief is hier juist**, want het is arbeid aan een woning ouder dan
twee jaar. Voor de doorrekening maakt dat weinig uit omdat de btw in de BV
verrekenbaar is, maar het is wel het verschil tussen een offerte die klopt en
een die te laag is ingeschat.

**Daarmee komt de wandopbouw op €68 per m2**, geindexeerd naar vandaag en
inclusief stucwerk, met alleen sloop nog open. Tegenover de €113 per m2 van de
aannemer voor frame, folies, isolatie en arbeid is dat een compleet beeld van
beide routes.

---

## 9h. Btw is voor ons kosten, geen doorlopende post — 30 september 2026

**Mark:** de btw is niet verrekenbaar, want het gaat om woningen. Alleen bij een
utiliteitspand mag die worden teruggevraagd.

**Dat maakt alle cijfers van vandaag te laag**, en ik had het zelf andersom
opgeschreven bij de stukadoorsfactuur. Woningverhuur is vrijgesteld, dus er
valt niets terug te vragen en de btw hoort gewoon in de kostprijs.

**Opnieuw gerekend, inclusief btw:**
- binnenwandisolatie €161 per m2, was €133
- vloerisolatie €39 per m2, was €32
- stucwerk €21,80 per m2 wand en €27,25 per m2 plafond
- de wandopbouw uit eigen inkoop: €80 per m2, was €68

Het script telt de btw nu zelf op: 21% op materiaal en 9% op arbeid aan een
woning ouder dan twee jaar. In de prijsbestanden blijven de bedragen staan
zoals ze op de bon staan, dus exclusief; dat voorkomt dat er ooit twee keer
btw overheen gaat.

**Een observatie die geld kan schelen.** Noordermeer heeft 21% gerekend over de
hele factuur, terwijl over arbeid aan een woning ouder dan twee jaar 9% mag.
Het verschil tussen die twee tarieven is €517 op deze ene factuur. De aannemer
moet dan wel arbeid en materiaal splitsen op de rekening, en dat is bij hem
niet gebeurd. Voor jullie, die de btw niet kunnen verrekenen, is dat direct
geld; bij een volgende opdracht is het het vragen waard.

---

## 9i. De scheidingswand voor kamers — 30 september 2026

Opbouw volgens Mark: gips, OSB 18 mm, isolatie tussen de balken, OSB 18 mm,
gips, en aan beide zijden stucwerk. Het verschil met de voorzetwand zit in wat
dubbel telt: een frame en een laag isolatie, maar twee lagen OSB, twee lagen
gips en twee keer stuken. Geen folie, want de wand grenst niet aan de
buitenlucht, en geen sloopwerk, want er staat nog niets.

Bij 10 m2 wand: €82 per m2 voor een voorzetwand tegen €119 per m2 voor een
scheidingswand, allebei inclusief btw. Dat verschil van bijna de helft komt
vrijwel volledig uit het dubbele plaat- en stucwerk.

**Een fout die deze berekening blootlegt:** hij rekende met de PIR van €24,93
per m2, terwijl in een scheidingswand geluidsisolatie hoort. PIR is er voor de
warmte, minerale wol voor het geluid, en die is per m2 goedkoper. Die post
staat nu apart in het prijzenbestand, nog zonder bedrag, want hoeveel m2 er in
een pak Acoustifit zit staat niet op de bon.

**En een punt dat voor de vergunning telt:** een scheidingswand tussen
wooneenheden moet voldoen aan de eisen voor geluid en brandwerendheid uit het
Besluit bouwwerken leefomgeving. Of deze opbouw dat haalt, hangt af van de
dikte en het soort isolatie. Dat staat als waarschuwing bij de uitkomst, want
een wand die de eisen niet haalt is bij kamerverhuur geen besparing maar een
probleem bij de melding brandveilig gebruik.

**Wat hierna kan:** het aantal meters scheidingswand per extra kamer volgt uit
een plattegrond, en dat hebben we niet. Wel kan het model straks rekenen met
"zoveel m2 wand per kamer" zodra jij uit een eigen verbouwing weet hoeveel dat
in de praktijk is. Dan is de post splitsen-eenheid ook een berekening in plaats
van een aanname.

---

## 9j. Twee isolatieprijzen hard, en een vergelijking die verrast — 30 september 2026

Met de opgave van Mark, Acoustifit 40 mm van €33,93 per pak van 12,96 m2, komt
geluidsisolatie op €2,62 per m2. En het productblad van Knauf geeft ook de m2
per pak voor de 150 mm van de Sleiderink-bon: 4,05 m2 per pak, dus €7,88 per
m2. Daarmee is ook die post hard in plaats van een afgeleide van tien pakken
over 38 m2.

**De vergelijking die daaruit volgt.** Per eenheid Rd kost glaswol €1,95 per m2
en PIR €5,49. Glaswol is dus bijna drie keer goedkoper per eenheid
isolatiewaarde, maar heeft er wel de helft meer dikte voor nodig. Waar ruimte
geen probleem is, zoals in een dak of een vloer, is glaswol de goedkoopste weg
naar dezelfde Rd; in een voorzetwand die zo dun mogelijk moet blijven, is PIR
dat. Dat is een afweging die het model straks per bouwdeel kan maken.

**Met de juiste isolatie erin zakt de scheidingswand** van €119 naar €93 per m2
inclusief btw. Het verschil van €26 zat volledig in de verkeerde isolatie:
PIR waar glaswol hoort.

**Wat nu in het oog springt:** van die €93 is €44 stucwerk en €31 plaatwerk.
Isolatie is met €3 per m2 de kleinste post van allemaal. Bij kamerverhuur
betaal je dus vooral voor afwerken, niet voor isoleren, en dat is precies
andersom dan bij een voorzetwand.

---

## 9k. Analyse van de verbouwingskosten — 30 september 2026

**De hele ingreep aan de Eerste Oude Heselaan 88, inclusief btw: €13.150,86.**
Aannemer 40%, stukadoor 28%, vloermateriaal 15%, overig materiaal 10%,
wandmateriaal 7%. Grofweg 54% arbeid en 46% materiaal.

**Wat daarin opvalt.** De stukadoor is met bijna €3.750 de op een na grootste
post, groter dan al het materiaal voor wand en vloer samen. Isolatie, waar het
project om begonnen is, is juist de kleinste: de PIR zat in de aanneemsom en de
glaswol kostte €2,62 tot €7,88 per m2. Je betaalt bij verduurzamen dus vooral
voor arbeid en afwerking, niet voor isolatiemateriaal.

**De twee routes lopen een factor twee uiteen.** Zelf inkopen en bouwen komt op
€80 per m2 wand inclusief btw; de aannemer op €161. Bij 38 m2 is dat een
verschil van ruim €3.000 op een klus van een paar dagen.

**Voor het kamerscenario telt iets anders.** Van de €93 per m2 scheidingswand
is €44 stucwerk. De gevoeligheid zit daar dus bij de stukadoorsprijs, niet bij
de isolatiekeuze: een euro per m2 bij de stukadoor weegt zwaarder dan het hele
verschil tussen glaswol en PIR.

**Wat een handrun nu wel en niet oplevert.** De brief leest alleen de posten
verduurzaming, verhuurklaar en splitsen-eenheid en rekent die per m2
woonoppervlak. Mijn posten staan per m2 bouwdeel en worden dus nog niet
gebruikt. Een run verandert daardoor geen enkele richtprijs.

**Wat er nodig is om dat te sluiten:** de gebruiksoppervlakte van de Eerste
Oude Heselaan 88. Dan wordt verduurzaming-a €337 per m2 bij 39 m2, €263 bij 50
of €219 bij 60. Dat ene getal zet vijf uur uitzoekwerk om in een cijfer dat
elke dag in de brief meerekent.

---

## 9l. Het eigen verduurzamingstarief erin, en twee fouten onderweg

Met 58 m2 uit de BAG komt de ingreep aan de Eerste Oude Heselaan 88 op €227 per
m2 woonoppervlak, inclusief btw. Dat staat nu in bouwkosten_eigen.txt en de
brief rekent ermee.

**Fout een: het verkeerde label.** Ik had het weggeschreven als
verduurzaming-a, alsof het over een pand met label A ging. Het script bedoelt
met die letter het HUIDIGE label: wat kost het om dit pand aan te pakken. Het
pand had F of E, dus hoort het bedrag onder verduurzaming-f en -e. Met de
verkeerde sleutel zou een pand dat al op A staat €13.000 aan verduurzaming
krijgen en een pand op F het oude kental.

**Fout twee: dubbel indexeren en dubbele btw.** De RVO-kentallen hebben
peildatum mei 2025 en worden naar nu bijgewerkt, met de btw erbovenop. Een
eigen factuur van maart 2026 met de btw er al in kreeg die correctie ook: €227
werd €261. Eigen cijfers worden nu geindexeerd vanaf hun eigen peildatum en
krijgen daarna geen opslag meer.

**Het resultaat voor een woning van 58 m2:** bij label F of E €13.166 aan
verduurzaming, precies 227 maal 58. Bij label C nog het kental van €10.000, tot
we daar ook een eigen factuur van hebben. Bij label A nul, want dan valt er
niets te verduurzamen.

---

## 9m. Ventilatie hoort bij isoleren — 30 september 2026

Duco ventilatiesysteem met CO2-sensoren, €2.750 exclusief btw en €3.327,50
inclusief. Daarmee komt de hele ingreep aan de Eerste Oude Heselaan 88 op
€16.478,36 en het verduurzamingstarief op €284 per m2 in plaats van €227.

**Waarom dit geen bijkomende post is maar onderdeel van de maatregel.** Een
woning luchtdicht maken zonder de ventilatie aan te pakken levert vocht en
schimmel op. En een CO2-gestuurd systeem telt mee in de labelberekening, dus
het draagt bij aan diezelfde sprong naar A. Wie de isolatie begroot en de
ventilatie vergeet, begroot een vijfde te laag: ventilatie is 20% van deze hele
ingreep.

**Voor een woning van 58 m2 met label F of E** komt verduurzaming nu op
€16.472 en de totale verbouwing op €34.814. Bij label C staat er nog het kental
van €10.000, en dat is het laatste geschatte getal in deze kolom.

---

## 9n. De SVOH als rekenmodule — 30 september 2026

De laatste stap uit Marks keten: subsidie verlaagt de investering en dus de
richtprijs. De bedragen per 1 januari 2026 staan nu in subsidie_svoh.py, met
een peildatum, want ze worden jaarlijks opnieuw vastgesteld. Het
gezondheidsrapport meldt het zodra dat jaartal achterloopt, net als bij de
huurprijstabel.

**De bedragen bij twee of meer maatregelen**, en dat is het gewone geval want
de regeling vraagt er minimaal twee: gevelisolatie €40,50 per m2, dakisolatie
€32,50, vloerisolatie €11, spouwmuur €10,50, bodemisolatie €6,
zoldervloer €8, HR++ glas €50. Biobased materiaal geeft een bonus per m2.
CO2-gestuurde ventilatie loopt niet per m2 maar op 30% van de kosten met een
maximum van €1.200. Plafond €10.000 per woning, of €15.000 met een warmtepomp
of zonneboiler.

**Voor de Eerste Oude Heselaan 88** zou dat uitkomen op €1.539 voor de gevel,
€554 voor de vloer en €825 voor de ventilatie, samen €2.918. De investering
zakt daarmee van €284 naar €234 per m2, een zesde eraf.

**Een voorwaarde om na te gaan:** voor vloerisolatie geldt een minimale Rd van
3,5. De Knauf Brio-elementen zijn een droge dekvloer van 33 mm; of die die
waarde halen, is de vraag. Zonder de vloer komt de subsidie op €2.364 en de
investering op €243 per m2.

**De voorwaarden staan erbij in de module:** minimaal twee maatregelen, de
woning wordt al verhuurd voordat het werk begint, bestaande bouw met een
woonfunctie in de BAG, uitvoering door een erkend bedrijf, aanvragen binnen 24
maanden, en ventilatie alleen in combinatie met een isolatiemaatregel.

---

## 9o. De subsidie valt precies te reconstrueren — 30 september 2026

Ontvangen: €2.537,25, voor de gevelisolatie en de ventilatie-unit. Voor de
brioplaten kwam niets, omdat die niet op de begane grond liggen.

- gevelisolatie 38 m2 maal €40,50 is €1.539,00
- CO2-gestuurde ventilatie, 30% van €3.327,50 is €998,25

Samen €2.537,25, precies wat er binnenkwam.

**Mijn eerste reconstructie zat ernaast.** Ik kwam ook op €2.537,25 uit, maar
met een derde regel voor 15,75 m2 vloerisolatie en de ventilatie over het
bedrag exclusief btw. Twee fouten die elkaar toevallig opheffen; dat het totaal
klopte betekende dus niets.

**Twee dingen die dit leert, en die in de module staan:**
- het percentage voor ventilatie gaat over het bedrag INCLUSIEF btw. Logisch
  voor een verhuurder van woningen, die de btw niet kan verrekenen en dus
  werkelijk dat hele bedrag betaalt. Dat scheelde hier €173;
- vloer- en bodemisolatie gaan over de begane grond, boven de kruipruimte of
  op de grond. Een droge dekvloer op een verdieping valt er niet onder, ook
  niet als er isolerend materiaal in zit.

**Het verduurzamingstarief gaat van €284 naar €240 per m2**, want de tarieven
in bouwkosten_eigen.txt staan nu netto, na aftrek van subsidie. Dat is het
bedrag waarmee je een aankoop beoordeelt: die subsidie krijg je hoe dan ook als
je de maatregelen uitvoert.

**De subsidie dekte 15% van de investering.** Dat is een bruikbaar kengetal om
te onthouden bij een volgende doorrekening, maar het is geen vuistregel: bij
een pand met veel dakoppervlak, waar €32,50 per m2 geldt, ligt het aandeel
hoger.

---

## 9p. De bouwkosten zijn verkeerd gestructureerd — 30 september 2026

**Mark twijfelt aan de opzet, en terecht.** Een hele verbouwing teruggerekend
naar een bedrag per m2 woonoppervlak, en dat vervolgens op elk pand met label E
of F plakken, is te grof. Drie bezwaren, en ze zijn alle drie hard:

1. **Er zit werk in dat niets met verduurzamen te maken heeft.** Van de €240 is
   €65 stucwerk, 27%. Er is 109 m2 wand gestuukt tegenover 38 m2 voorzetwand,
   dus het meeste daarvan hoort bij het opknappen van de woning.
2. **Niet elk pand heeft alles nodig.** Een pand uit 1985 heeft volgens
   bouwnorm.py alleen dak en vloer nodig, geen gevel. Nu krijgt het hetzelfde
   bedrag als een pand uit 1930 dat alles vraagt.
3. **Het schaalt met het verkeerde getal.** Gevelisolatie schaalt met het
   geveloppervlak, dakisolatie met het dakvlak, ventilatie met de woning. Geen
   van drieen schaalt met het woonoppervlak.

**De betere opzet, en de onderdelen liggen er al:**
- bouwnorm.py zegt uit het bouwjaar welke bouwdelen onder de maat zijn, en het
  energielabel corrigeert dat als er al is geisoleerd;
- de 3D BAG geeft het buitenmuuroppervlak, het dakvlak en het grondvlak;
- maatregelprijzen.txt geeft wat elke maatregel per m2 van dat bouwdeel kost;
- subsidie_svoh.py trekt de subsidie er per maatregel af;
- en het puntenstelsel in wwso.py zegt wat de labelsprong oplevert aan huur.

**Gemeten per maatregel, inclusief btw en na subsidie:** gevelisolatie €156 per
m2 gevel, vloerisolatie €39 per m2 vloer, ventilatie €2.329 per woning,
stucwerk €25 per m2 afgewerkt vlak. Die staan nu in maatregelprijzen.txt.

**Wat er nog tussen zit:** de 3D BAG-stap moet eerst draaien, en de zijgevels
die tegen de buren staan moeten van het buitenmuuroppervlak af. Zonder die twee
is er geen oppervlak om mee te vermenigvuldigen. De €240 per m2 blijft tot dan
staan als noodgreep, met die waarschuwing erbij in het bestand.

---

## 9q. Vals alarm bij Pararius — 30 september 2026

Het rapport meldde dat Pararius wel mails stuurt maar dat het script er niets
uithaalt, met als voorbeeld "St. Stephanusstraat (gemeubileerd, andere markt)".
Dat voorbeeld is juist het bewijs dat het goed ging: die woning is bewust
overgeslagen omdat gemeubileerde verhuur een andere markt is.

De controle keek alleen naar het aantal objecten en niet naar het aantal
bewust overgeslagen mails. Nu slaat hij alleen alarm als er niets uitkwam en er
ook niets is overgeslagen.

**Twee dingen uit dit rapport die nog open staan:**
- de COROP-stap leverde niets op; wat er in het logboek van die stap staat,
  moet eerst bekend zijn voordat ik iets aanpas;
- de 3D BAG-controle staat in geen van beide lijsten, dus die draait niet mee.
  Samen met het aantal nooit nagekeken panden, dat van 146 naar 148 ging in
  plaats van naar nul, wijst dat erop dat niet alle bestanden van gisteravond
  in de repo staan.

---

## 9r. COROP: de regio werd gevonden, de cijfers niet — 30 september 2026

Het logboek zegt "Geen kwartaalcijfers gevonden". Dat betekent dat de regio wel
is opgezocht maar dat er geen kwartaalrijen uitkwamen. Twee oorzaken zijn
mogelijk en ik heb ze allebei afgevangen in plaats van er een te kiezen:

1. **De regiocode met spaties.** Het CBS bewaart codes als "CR12  " met
   spaties erachter. Een filter op de afgeknipte code kan dan nul rijen
   opleveren. Levert het filter niets op, dan haalt het script de tabel nu
   zonder filter op en zoekt het de regio er zelf uit.
2. **Andere kolomnamen.** De namen eindigen op een volgnummer dat per
   tabelversie verandert, en het CBS biedt sommige tabellen ook in het Engels
   aan. Het script zoekt nu op woorden in de kolomnaam, in beide talen, in
   plaats van op een vaste sleutel.

**En het logboek vertelt voortaan wat de bron wel teruggaf:** hoeveel rijen er
kwamen, hoeveel daarvan bij Arnhem/Nijmegen horen, en bij niets een voorbeeld
van de eerste rij met de kolomnamen erin. Dan is de volgende diagnose een
kwestie van kijken in plaats van opnieuw raden.

---

## 9s. Een paklijst in plaats van een tekstcontrole — 30 september 2026

**Mark:** beide bestanden staan wel in de repo; is werken met versies niet
beter?

**Mijn versiestap deugde niet.** Die zocht naar een stukje tekst dat ook in
oudere versies stond, en meldde daarom "nieuwste versie" terwijl dat niet zo
was. Zo'n controle kan alleen heel oude bestanden herkennen, en precies de
gevallen waar het om gaat, een versie van een uur eerder, glippen erdoor.

**Nu een paklijst met vingerafdrukken.** versies.json bevat per bestand de
eerste twaalf tekens van de sha256 op het moment van opleveren. De workflow
vergelijkt dat bij elke run en meldt per bestand ANDERE VERSIE of ONTBREEKT.
Daar valt niets aan te interpreteren.

**Belangrijk bij het gebruik:** versies.json hoort altijd mee in dezelfde
upload als de bestanden waar hij bij hoort. Hij is de pakbon; upload je hem
niet, dan klopt de vergelijking niet meer.

**Een fout die de test blootlegde, en het is dezelfde als eerder deze week:**
de map .github viel weg omdat de negeerlijst op tekst vergeleek en ".github"
het woord ".git" bevat. Nu wordt er op mapnaam vergeleken. Dat is de derde keer
dat een insluiting toesloeg: studentenhuis op huis, ongemeubileerd op
gemeubileerd, en nu .github op .git.

---

## 8. Kleinere punten

- **Verkoopprijzen ontbreken.** Alles wat de brief vergelijkt zijn vraagprijzen.
  De mediaan per buurt is dus een mediaan van wat verkopers vrágen.
- **Huurdata is dun.** Drie tot dertien waarnemingen per klasse, terwijl elke
  richtprijs daaraan hangt.
- **Eigen portefeuille zit er niet in**, terwijl dat de meest directe benchmark
  is. Begrijpelijk gezien de openbare repo; kan via een secret of een apart
  bestand dat niet wordt gecommit.
- **De staat van het pand is onbekend.** De verbouwschatting rust op label en
  oppervlakte. Asbest, fundering en installaties zitten er niet in.
- **Off-market aanbod zien we niet.** De brief kijkt naar wat publiek is
  aangeboden, en dat is per definitie wat anderen ook zien.
- **De puntentelling is een ondergrens**; verwarming en enkele rubrieken
  ontbreken.
- **Exploitatiekosten zijn aannames** van Claude, geen ervaringscijfers van
  Derksen Vastgoed. Te vervangen zodra Mark de eigen getallen aanlevert.
- **De verbouwkentallen zijn aannames van Claude, geen RVO-cijfers.** De brief
  schreef "naar de kostenkentallen van RVO", en dat was te veel eer: die tabel
  is nooit ingelezen. Sinds 19 september staat de werkelijke herkomst erbij en
  kun je eigen cijfers zetten in bouwkosten_eigen.txt, die dan voorgaan. Twee
  getallen zouden al veel schelen: wat verhuurklaar maken per m2 kost, en wat
  verduurzaming per m2 kost bij een slecht label.
- **Verbouwkosten worden sinds 18 september geindexeerd** met de CBS
  inputprijsindex bouwkosten, tabel 85728NED, vanaf de RVO-peildatum mei 2025.
  BDB is de gangbare index in het vak maar zit achter een abonnement; deze CBS-
  reeks meet loon en materiaal apart en volgt dezelfde beweging. De kentallen
  zelf blijven aannames en zijn te vervangen door eigen cijfers.
- **Gemeentelijke monumentenlijst** is nog niet ingelezen; nijmegen.nl zit
  achter een botcontrole.
- **Opendata.nijmegen.nl** is nooit getest op toegang zonder token.

---

## 9. Wat werkt en niet vervangen moet worden

Ter herinnering, zodat we niet iets weggooien dat zijn werk doet:

- Het bekendmakingen-archief loopt terug tot 2012 met 315 adressen.
- De vergunningenlijst telt 816 vergunningen op 279 straten.
- Het geheugen tegen herhaling: panden die niets doen krijgen één regel.
- De routefilter: panden zonder haalbare route verdwijnen uit beeld maar
  blijven meetellen in de cijfers.
- De toets aan artikel 15, met onderscheid tussen wat hard te toetsen is en
  wat onderzoek vraagt.
- De regelgevingsmonitor op CVDR, Basiswettenbestand en Staatsblad.
