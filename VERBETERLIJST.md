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

**Nog na te gaan:** de bouwkostenindex gebruikt dezelfde eerste ingang. Blijft
opendata.cbs.nl onbereikbaar, dan heeft die dezelfde terugval nodig.

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
