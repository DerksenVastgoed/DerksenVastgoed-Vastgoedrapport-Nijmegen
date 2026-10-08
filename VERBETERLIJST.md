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

## 9t. De versiecontrole in het rapport zelf — 30 september 2026

**Mark:** weet jij dan precies welke versies er draaiden als ik het rapport
stuur?

**Zoals het was: nee.** De versiestap en het gezondheidsrapport staan op
verschillende plekken in het logboek. Wie alleen het rapport plakt, laat de
versies achter, en dan ben ik terug bij vermoeden.

**Nu staat de controle in het rapport**, als eerste regel. Eén blok plakken
levert dan drie dingen tegelijk: welke code er draaide, wat elke bron heeft
opgeleverd en wat er mis is. Bij een afwijking noemt hij de bestandsnamen,
dus ik weet meteen welke.

**Wat het rapport nog steeds niet bevat**, en dat is goed om te weten: de
uitvoer van de losse stappen. Loopt de COROP-stap vast, dan zegt het rapport
dat er geen cijfers zijn, maar niet waarom. Voor dat waarom blijft de regel uit
die stap nodig. Datzelfde geldt voor de mailstap en de 3D BAG.

---

## 9u. Het rapport korter, maar niet blind — 30 september 2026

**Mark:** het rapport wordt steeds langer; is het een idee om alleen te tonen
wat opvalt?

**Ja, met een voorbehoud dat vandaag bewezen is.** We vonden een probleem
doordat de 3D BAG-controle in geen van beide lijsten stond. Zou het rapport
alleen problemen tonen, dan was die controle geruisloos verdwenen en had
niemand iets gemerkt. Alleen problemen tonen is dus wel gevaarlijk; alleen
veranderingen tonen niet.

**Zo is het nu opgezet.** De onderdelen die goed gaan worden niet meer
uitgeschreven, alleen geteld; dat scheelt de helft van het rapport. Daarvoor in
de plaats komt wat er is veranderd sinds de vorige run: een controle die van OK
naar LET OP ging, een nieuwe controle, en met nadruk een controle die niet meer
draait. Die laatste regel begint met WEG, want dat is het gevaarlijke geval.

**Staat er niets veranderd, dan zegt hij dat ook**, met de datum van de vorige
run erbij. Dan weet je in een oogopslag dat er niets nieuws is in plaats van
dat je twintig regels moet vergelijken.

**Het volledige rapport blijft bestaan** in het digestbestand, met alle
adviesregels. Dat is er voor als je wilt weten wat je aan een melding moet
doen; het korte blok is er om te zien of er iets aan de hand is.

---

## 9v. De eerste run met de nieuwe opzet — 30 september 2026

**Goed nieuws:** COROP Arnhem/Nijmegen staat op OK, dus die kwartaalcijfers
komen binnen. Een van de twee oorzaken die ik afving, was de juiste.

**Twee fouten in mijn eigen nieuwe onderdelen.**

De lijst met veranderingen noemde alle dertig controles nieuw, omdat er nog
geen vorige stand was om mee te vergelijken. Dat zegt niets en maakt het
rapport juist langer. Bij een eerste run staat er nu een regel dat de
vergelijking vanaf morgen pas zin heeft.

De paklijst nam ook gegevensbestanden mee. verkopen.txt, woz.txt en de
plakbestanden worden door de run zelf bijgewerkt of door Mark aangevuld, dus
die wijken per definitie af. Elke dag zes valse meldingen. De paklijst gaat nu
alleen over code: python en de workflow, 33 bestanden.

**Wat er van de melding overblijft en wel klopt:** er staan bestanden in de
paklijst die niet in de repo zitten. Dat is precies waar het ding voor is, en
na deze aanpassing is die melding weer betekenisvol in plaats van ruis.

---

## 9w. De tabellen stonden niet meer op volgorde — 30 september 2026

In de brief van 30 september staat Achter de Bank met +5% op plek veertien van
Stadscentrum, terwijl dat de enige positieve is. De tabellen waren dus niet
gesorteerd op richtprijs ten opzichte van vraagprijs, zoals er onder de tabel
staat, maar stonden in de volgorde waarin de panden binnenkwamen.

**Oorzaak:** de sorteerfunctie kijkt naar het scenario van een pand, en dat
wordt pas berekend in de lus die de tabelregels schrijft. Bij het sorteren had
bijna geen pand een scenario, dus kreeg alles dezelfde waarde en bleef de
oorspronkelijke volgorde staan.

**Hersteld** door het scenario in de sorteerfunctie te berekenen als het er nog
niet is, en het daarna te bewaren zodat de lus eronder het hergebruikt en er
geen dubbel werk ontstaat.

**Eerlijk over de test:** de volledige bijlagetabel krijg ik in een
testopstelling niet gereproduceerd, dus deze fix is nagekeken maar niet
end-to-end getest. In de eerstvolgende brief moet de eerste regel van elke
buurttabel het hoogste percentage hebben.

**Twee kleinere dingen uit dezelfde brief.** Er staat "Gelderland 5,6% per
kwartaal", terwijl dat een jaarcijfer is; eerdere brieven schreven het wel
goed, dus dat is een uitglijder van het model en geen rekenfout. En de laatste
kolom van de laatste regel van elke tabel viel bij het overnemen weg; dat is
een plakartefact en geen fout in de brief.

---

## 9x. Huisly als mogelijke bron — 30 september 2026

Niet bekend, en de zoekmachine kent hem ook niet, dus het is waarschijnlijk een
nieuw of klein platform. Het adres dat Mark stuurde is een gegevensingang van
hun eigen webapplicatie; zonder zoekopdracht geeft die een foutstatus terug.

**Technisch zou het aanbod daar als gestructureerde gegevens uit te halen
zijn**, netter dan wat we bij Funda doen met geplakte tekst. Twee bezwaren: ik
weet niet of hun voorwaarden dat toestaan, en een ingang die voor hun eigen
site is bedoeld kan morgen veranderen zonder aankondiging.

**De route die deze week steeds werkte is de attendering per mail.** Die komt
met hun instemming binnen en verandert niet als ze hun site verbouwen.
huisly.nl staat nu bij de afzenders die de mailstap accepteert. Er is nog geen
parser, dus de teller zal "huisly: N mails, 0 objecten" melden zodra de eerste
binnenkomt. Dat is precies wat ik nodig heb om er een te schrijven.

---

## 9y. Veertien platforms, en de vraag eronder — 30 september 2026

Mark vond via Huisly een stuk of veertien sites met huuraanbod in Nijmegen, en
vraagt of we die kunnen koppelen zonder overal een account en een attendering.

**Veertien koppelingen bouwen is de verkeerde afslag.** Elk heeft zijn eigen
opmaak, geen van allen een open ingang, en ze verbouwen hun site zonder
aankondiging. Dan repareer je elke week parsers in plaats van panden te
beoordelen. Dat is dezelfde afweging als bij de Funda-lijst: een route die
niemand onderhoudt, houdt geen stand.

**De vraag eronder is beter te beantwoorden met een meting.** Hoeveel van dat
aanbod missen we werkelijk? huur_dekking.py leest de adressen die je op zo'n
site ziet uit huur_elders.txt en zegt welke we al hadden. Op de twaalf adressen
uit Marks eigen links: drie bekend, negen gemist. Dat is 25%, en het
gezondheidsrapport meldt het zolang het onder de zestig procent ligt.

**Wat dat betekent voor de volgorde van werken.** Zolang we driekwart van het
huuraanbod niet zien, weegt een extra bron zwaarder dan welke verfijning van de
berekening ook. De huurprijs bepaalt elke richtprijs in de brief, en die rust
nu op 29 waarnemingen.

**De praktische route blijft een aggregator.** Huisly bundelt kennelijk precies
deze partijen; een attendering daar is een account in plaats van veertien. Dat
is ook waarom huisly.nl al bij de geaccepteerde afzenders staat.

---

## 9z. Huuradvertenties vervallen nooit — 30 september 2026

**Mark:** we horen nooit wanneer een woning verhuurd is, dus we zien alleen de
vraagprijs op de dag dat hij beschikbaar kwam. Is dat het?

**Ja, en bij huur is dat minder erg dan bij koop**, want een advertentie zegt
wat er op dat moment werd gevraagd, en dat is precies de maat die we willen.
Maar er zitten twee gaten in, en die zijn deels te dichten.

**Een vraagprijs die drie dagen staat is de markt; een die vier maanden hangt,
niet.** Toch wegen ze even zwaar in de mediaan. Dat is niet op te lossen zonder
de verhuurdatum, maar wel te beperken: waarnemingen ouder dan achttien maanden
tellen niet meer mee. Een huur uit 2024 is geen marktprijs van nu. Het venster
staat in een omgevingsvariabele, dus het is te verzetten zodra er genoeg
waarnemingen zijn om korter te kunnen.

**En er is een signaal dat we wel kunnen lezen: opnieuw aangeboden.** Komt
hetzelfde adres later terug voor minder geld, dan is dat het bewijs dat de
eerste vraagprijs niet werd betaald. Komt hij terug voor meer, dan is het een
gewone mutatie in een krappe markt. Het rapport telt beide en noemt de
verlagingen met bedrag erbij. Dat is het enige wat we hebben over wat er
werkelijk betaald wordt, en het wordt beter naarmate de reeks langer loopt.

**Wat we hiermee niet oplossen:** een woning die nooit terugkomt, kan verhuurd
zijn of van de markt gehaald. Dat blijft onbekend.

---

## 9aa. De wachtrij liep vol door een noodreparatie — 30 september 2026

De versiecontrole wees uit dat bag3d.py ontbrak, wat verklaart waarom de 3D BAG
niets ophaalde. Maar pandgeschiedenis.py werd niet als afwijkend gemeld,
terwijl het aantal nooit nagekeken panden toch opliep. Dan ligt het niet aan de
upload maar aan de code, en zo bleek het ook.

**Oorzaak:** een noodreparatie van 28 september, na de bag_dump-fout, haalde bij
elk pand zonder pand-id de markering weg zodat het opnieuw aan de beurt kwam.
Dat blok is blijven staan. Elke run werden dus dezelfde 188 panden opnieuw
geprobeerd, mislukten ze opnieuw, en liep het aantal "nooit nagekeken" op in
plaats van af. Ze vulden bovendien elke ronde een deel van de quota, waardoor
de echte achterstand niet werd ingelopen.

**Nu krijgt zo'n pand drie pogingen en daarna niet meer.** Het rapport meldt
hoeveel er zijn opgegeven, zodat die groep zichtbaar blijft in plaats van
stilletjes te verdwijnen of eeuwig terug te komen.

**En de paklijst negeert voortaan drie bestanden** die ik niet zelf lever:
ov_haltes.py, rijksmonumenten.py en bag_uitzoeken.py. Mijn kopie daarvan wijkt
af van de repo en dat zou elke run als afwijking worden gemeld, terwijl er
niets aan de hand is.

---

## 9bb. De 149 bewogen niet, en nu weten we waarom — 1 oktober 2026

De versiecontrole meldde nul ontbrekende bestanden, dus de code klopte. En
toch bleef het aantal nooit nagekeken panden op 149 staan. Dan is het geen
uploadprobleem meer.

**Oorzaak:** de vlag --volledig zet de BAG-ronde aan, maar geeft niet door dat
alle panden mee mogen doen. De functie houdt standaard alleen panden over met
een verkoop, een bekendmaking of kamerverhuur in hun geschiedenis. Precies die
149 panden kennen we alleen uit het aanbod, dus ze werden overgeslagen voordat
ze geteld werden, elke ronde opnieuw.

**Een tweede fout die daarbij boven kwam:** zonder BAG-sleutel gaf de functie
een enkele nul terug terwijl de aanroeper er twee uitpakt. Dan loopt de hele
stap vast op precies het moment dat je een nette melding wilt. Nu geeft hij
twee waarden terug en meldt hij waarom hij overslaat.

**Wat dit zegt over de week:** dit is de derde keer dat een getal dat niet
beweegt belangrijker bleek dan een melding die oplichtte. De 505 verkopen die
de wachtrij vulden, de 146 die opliepen door een noodreparatie, en nu deze. Een
teller die stil blijft staan is een signaal, geen rust.

---

## 9cc. 502 op elk verzoek: twee fouten tegelijk — 1 oktober 2026

De 3D BAG-stap gaf een 502 op elk pand, eenentwintig keer, en stopte toen
netjes. Dat laatste werkte dus zoals bedoeld. De oorzaak was tweeledig en ik
heb het opgezocht in plaats van opnieuw te gokken.

**Het pand-id moet met NL.IMBAG.Pand. ervoor.** Wij bewaren het kale nummer uit
de BAG; de 3D BAG verwacht het voorvoegsel. Zonder dat antwoordt de bron met
een 502 in plaats van een 404, en dat is een fout die zichzelf niet verklaart.

**En het antwoord is CityJSON, geen GeoJSON.** De kenmerken zitten onder
feature.CityObjects.<id>.attributes en niet in properties. Mijn zoekfunctie
keek alleen op de GeoJSON-plekken, dus zelfs met het juiste id was het
resultaat leeg geweest.

Getest met een antwoord in de echte vorm: elf velden eruit, en uit nokhoogte
min maaiveld gedeeld door het aantal bouwlagen rolt de verdiepingshoogte. Dat
is precies het getal dat ik anders had moeten aannemen.

**Wat hieraan opvalt:** de stap meldde "de bron lijkt onbereikbaar of
veranderd", en dat was de verkeerde conclusie uit een juiste waarneming. Een
502 betekende hier niet dat de bron plat lag, maar dat wij de verkeerde vraag
stelden.

---

## 9dd. COROP werkt, maar haalde elke run de hele tabel op — 1 oktober 2026

Het logboek eindigde na "126 rijen voor Arnhem/Nijmegen" zonder uitkomst, wat
leek op een stap die halverwege stopt. Hij was juist geslaagd: met --stil werd
de slotregel onderdrukt. Die regel komt er nu altijd, want een logboek dat
zonder uitkomst eindigt leest als een fout.

**Wel zat er verspilling in.** Het filter op de afgeknipte code CR15 gaf nul
rijen, dus viel het script terug op de hele tabel: 5040 rijen per run voor 126
die we nodig hebben. Het CBS plakt spaties achter zijn sleutels; die geven we
nu ongewijzigd mee in het filter.

**De terugval blijft bestaan** als vangnet, met een duidelijker melding erbij:
gebeurt dit elke run, dan klopt de sleutel niet.

**En de cijfers zijn binnen:** Arnhem/Nijmegen heeft nu een eigen prijsindex,
een eigen aantal transacties en een eigen gemiddelde verkoopprijs per kwartaal.
Daarmee staat in de brief voortaan een regiocijfer naast het landelijke en het
provinciale, in plaats van alleen die bak waar Winterswijk ook in zit.

---

## 9ee. Een huur van vijf euro — 1 oktober 2026

In het logboek van de mailstap staat "Hegdambroek, 20m2, €5 p/m". Zo'n
waarneming valt later wel buiten de mediaan, want de prijs per m2 zakt onder
de ondergrens die daar al staat, maar hij belandt wel in verkopen.txt en telt
mee in de tellingen.

**Nu wordt dat bij de bron tegengehouden:** onder €150 of boven €10.000 per
maand, en buiten €3 tot €120 per m2, wordt de advertentie overgeslagen met de
reden erbij. Die reden komt in de telling van bewust overgeslagen mails
terecht, dus het blijft zichtbaar.

**Wat het logboek verder laat zien, en dat is goed nieuws:** 23 berichten
gelezen, zestien objecten herkend, vier bewust overgeslagen (drie buiten
Nijmegen, een gemeubileerd) en nul nieuw. Dat laatste klopt: met een venster
van drie dagen worden dezelfde mails elke run opnieuw gelezen en het
ontdubbelen doet zijn werk.

**En de Kamernet-parser draait zoals bedoeld.** Cuijk, Molenhoek en
Beek-Berg en Dal worden eruit gefilterd, precies waarvoor die plaatscontrole
is gebouwd.

---

## 9ff. Aanmeldingen bij nieuwe platforms waren onzichtbaar — 1 oktober 2026

**Mark:** ik heb me bij meerdere sites aangemeld; is dat terug te zien?

**Nee, en dat was een blinde vlek.** De mailstap kijkt alleen naar afzenders op
de lijst; alles daarbuiten wordt genegeerd. Je zou pas merken dat een
aanmelding werkt als je het zelf in de mailbox nagaat.

**Nu telt de stap ook de post van platforms zonder parser**, van de vijftien
sites die in deze sessies langskwamen: huurwoningen.nl, rentola, huurflits,
hestiva, rebogroep, huislijn, ikwilhuren, nmgwonen, vastgoednederland, level2,
vgmdestijl, expatrentals, hansjanssen, nextmove en funda. Alleen tellen, niet
lezen. Het rapport schrijft het als "zonder parser: huurwoningen.nl (3),
rentola.nl (1)".

**Waarom dat nuttig is:** het zegt welke parser het eerst de moeite waard is.
Komt er elke dag post van een platform, dan loont een parser; komt er eens per
maand iets, dan niet. Dat is dezelfde afweging als bij de dekkingsmeting, maar
dan op volume in plaats van op adressen.

**Een bijvangst:** funda.nl staat ook in die lijst terwijl het wel een parser
heeft. Dat is met opzet: het rapport meldt al weken dat er geen Funda-mail
binnenkomt, en zo zien we of dat aan de afzender ligt of aan de attendering.

---

## 9gg. Vier ontbrekende bestanden met dezelfde oorzaak — 1 oktober 2026

De terugcommit-stap meldt vier bestanden als ONTBREEKT, alle vier van de
onderwerpensignalering: onderwerpen_gezien.json, onderwerpen_volgen.json,
onderwerpen_volgen.txt en onderwerpen_voorstel.md.

**Oorzaak, na navraag van Mark:** de bestandsnaam was al goed. Het zit in de
voorwaarde van de stap: if env.MODUS != 'dagelijks'. Alle handruns draaien in
de dagelijkse modus, dus die stap werd elke keer overgeslagen en heeft sinds
zijn bestaan alleen op zondag kunnen draaien. De stap loopt nu ook mee bij een
handmatige start.

**Les over diagnose:** ik wees naar de bestandsnaam omdat die er vreemd uitzag
in de bestandslijst, en dat was plausibel maar niet nagekeken. De voorwaarde in
de workflow stond twee regels boven de aanroep. Eerst kijken waar iets wordt
aangeroepen, dan pas naar hoe het heet.

**En het rapport meldde daar OK.** De controle keek of er voorstellen waren;
nul voorstellen was geen alarm. Nu kijkt hij eerst of de stap ooit iets heeft
weggeschreven. Is er geen enkel spoor, dan is dat een melding met de
bestandsnaam erbij. Dezelfde soort fout als bij de mailstap: een nul kan
betekenen dat er niets was, of dat er niemand gekeken heeft.

**Een bevestiging in hetzelfde logboek:** bag3d.json is wel aangemaakt, dus die
stap schrijft weg zoals bedoeld. Leeg, omdat alle verzoeken strandden op het
ontbrekende voorvoegsel, en dat is inmiddels verholpen.

---

## 9hh. Het sterkste stuk van de brief was toeval — 1 oktober 2026

De brief van 1 oktober opent met een patroon: drie panden met een
splitsingsvergunning die inmiddels verkocht zijn, St. Annastraat 165, van
Oldenbarneveltstraat 61 en Dominicanenstraat 103. Mark noemt dit precies het
deel waar zijn vader enthousiast van wordt, en terecht: het is de kruising van
twee bronnen die alleen samen iets zeggen.

**Maar het model viste het zelf uit de lijsten, en dat is geen methode.** De
volgende dag kan het er net zo goed langs kijken. Daarom wordt het nu geteld:
pandgeschiedenis.py schrijft vergund_verkocht.json met alle panden die een
besluit over splitsen, verkameren, woningvorming of omzetten hebben en die in
onze gegevens als verkocht staan.

**De formulering is met zorg gekozen:** "met een vergunning en inmiddels
verkocht", niet "verkocht na de vergunning". Van de geplakte verkopen kennen we
de datum niet, dus de volgorde staat niet vast. Dat verschil is het verschil
tussen een waarneming en een verhaal, en de opdracht aan de brief zegt dat
met zoveel woorden.

**Ook bevestigd in deze run:** de sortering werkt weer. Achter de Bank met +5%
bovenaan in Stadscentrum, Krayenhofflaan met -1% in Biezen, van Goorstraat 34
met -2% in Bottendaal.

---

## 9ii. Twee winsten en twee meldingen die niet deugden — 1 oktober 2026

**De 3D BAG staat op OK**, dus met dat voorvoegsel loopt hij. En de
onderwerpensignalering draait voor het eerst: 22 voorstellen. Die twee stonden
gisteren nog open.

**Maar de melding over die voorstellen was onleesbaar:** er stond "_88 keer
genoemd._" als onderwerp. De voorstellen staan in dat bestand als kopregel,
"## term", met de telling en een citaat eronder. Mijn controle las elke korte
regel en pakte dus de tellingen mee. Nu leest hij alleen de kopregels, en dan
staat er "vermogenswinstbelasting; warmtewet aansluitplicht".

**En de versiecontrole viel om op een importfout.** De versies.py in de repo
kent de functie controleer niet, dus is het een oudere versie. Dat toonde het
rapport als een pythonfout van drie regels. Nu staat er wat er aan de hand is
en wat eraan te doen valt.

**22 voorstellen is veel**, en dat komt doordat die stap weken niet heeft
gedraaid. De eerste keer is dus een inhaalslag; daarna zijn het er een paar per
week. Die lijst is het waard om langs te lopen, want elk onderwerp dat in het
nieuws terugkomt zonder achtergrondstuk is een gemiste uitleg in de brief.

---

## 9jj. De 22 onderwerpen waren ruis — 1 oktober 2026

Het digest laat zien wat die voorstellen werkelijk zijn: "88x besluit
gevonden", "31x besluit voor vergunning aanvragen", "20x besluit voor het
renoveren". Dat zijn geen onderwerpen maar standaardzinnen uit de
bekendmakingen.

**Oorzaak:** het patroon voor "Besluit ..." vangt ook gewone ambtelijke
formuleringen op. Een echte regeling heeft een naam, zoals Besluit bouwwerken
leefomgeving; een zin heeft een werkwoord of een voorzetsel erachter. Daarop
wordt nu gefilterd, en het bestand met eerdere voorstellen wordt bij elke ronde
opgeschoond.

**In het echte bestand bleken er drie vondsten tussen de ruis te zitten:**
EPBD IV, NTA 8800 en de regeling noodfonds blokverwarming. Het filter moest dus
scherper dan "begint met besluit": het kijkt nu naar het woord erachter. Een
voorzetsel of een werkwoord betekent een zin, een naam betekent een regeling.
"Wet op belastingen van" blijft daarom staan en "wet is geborgd" niet.

Op het echte bestand losgelaten: zes regels weg, vier over, en dat zijn precies
de vier die ergens over gaan. Het opruimen kan ook met regels die met een hekje
beginnen, want zo staan de voorstellen erin; zonder dat bleef de ruis staan.

**Wat dit zegt over de maat van 326.945 woorden:** een detector die op patronen
zoekt vindt altijd iets, en het aantal zegt niets over de waarde. Pas toen het
digest de termen zelf liet zien, bleek dat er nul bruikbare tussen zaten. Dat
is dezelfde les als bij de dekkingsmeting: een getal zonder de onderliggende
regels is geen meting maar een gevoel.

---

## 9kk. Drie achtergrondstukken uit het signaal — 1 oktober 2026

De drie vondsten uit de voorstellenlijst zijn uitgezocht en geschreven.
Achtentwintig stukken nu.

**NTA 8800** is de norm die bepaalt hoe het energielabel wordt uitgerekend.
Dat raakt ons direct: het label bepaalt punten in het woningwaarderingsstelsel
en die punten bepalen of een woning gereguleerd is of vrij. Per 29 mei 2026
geldt NTA 8800:2026, met een klasse A0 voor emissievrije gebouwen en een
waardering voor thuisbatterijen. Belangrijk: een nieuwe rekenmethode kan het
puntenaantal verschuiven zonder dat er aan het gebouw iets verandert. Eerder
geregistreerde labels blijven geldig.

**EPBD IV** is sinds 29 mei 2026 in de Nederlandse regels verwerkt, in
tranches die doorlopen tot 2033. De belangrijkste uitkomst voor Mark is
geruststellend: voor bestaande woongebouwen komen er geen individuele
verplichtingen, dus geen verplicht minimumlabel zoals bij kantoren. Wat wel
verandert: het label is voortaan ook verplicht bij het vernieuwen van een
huurovereenkomst en na een grootschalige renovatie, monumenten zijn niet langer
uitgezonderd, en de keuringsplicht voor verwarmings- en aircosystemen vervalt.

**Noodfonds Energie** kent in de opzet voor 2026 wel huishoudens met een
blokaansluiting, die er jarenlang buiten vielen. Inkomen tot 200% van het
sociaal minimum, drempel van 8 of 10% van het inkomen, en vergoed wordt de
helft van het bedrag boven die drempel. Bij blokverwarming krijgt de huurder
het bedrag zelf, maar hij moet bij de aanvraag de afrekening van de verhuurder
of de VvE kunnen laten zien. Een late eindafrekening kost een huurder dus geld.

**Een fout die de test blootlegde:** de EPBD-tekst koos eerst het stuk over
servicekosten, omdat die op een algemener woord matchte. Met "epbd iv" en
"nieuw energielabel" als meerwoordige trefwoorden kiest hij nu het juiste. Dat
is dezelfde weging als bij de eerdere vier stukken.

---

## 9ll. Wie zit er achter die panden? — 1 oktober 2026

**Mark:** kunnen we de eigenaar of het bedrijf achter die vergunde en verkochte
panden achterhalen?

**Niet uit een open bron.** Eigendom staat bij het Kadaster: betaald per
object, ongeveer drie euro, en de gegevens mogen niet worden herpubliceerd. De
BAG kent geen eigenaren en bekendmakingen noemen meestal alleen het adres.

**Wat we wel hebben en weggooiden: de makelaar.** In de geplakte Funda-lijst
staat bij elk pand een link naar de pagina van de makelaar. Die naam wordt nu
bewaard en meegegeven aan het signaal vergund-en-verkocht, met een telling
erbij. Komt dezelfde naam bij meerdere van die panden terug, dan is dat de
partij om te bellen.

**De formulering is beperkt gehouden:** de brief mag schrijven dat een makelaar
deze panden verkocht, nooit dat hij de eigenaar of de ontwikkelaar is. Wie
verkoopt is niet wie bezit, en dat verschil moet niet in een zin verdwijnen.

**Wat nog wel kan, als je het echt wilt weten:** een losse
eigendomsinformatie bij het Kadaster voor een pand dat je serieus overweegt.
Dat is drie euro voor een pand van vier ton, dus voor een concreet bod is dat
geen bezwaar; voor het volgen van een patroon over honderden panden wel.

---

## 10. Van buurtportret naar trechter, en een logboek — 1 oktober 2026

Drie dingen gebouwd na het sparren met Mark.

**Het losse buurtportret vervalt.** Die cijfers komen uit de CBS-kerncijfers en
veranderen een keer per jaar; je las dus elke zes dagen dezelfde zinnen, terwijl
diezelfde getallen al in de tabel eronder staan. Voortaan alleen buurtcijfers
als er een pand of een besluit aanleiding voor geeft, en dan alleen de twee of
drie die iets over dat pand verklaren.

**Een pand wordt behandeld van buurt naar straat naar pand**, als een blok.
Hoe dichter bij het pand, hoe harder de gegevens: de buurt is statistiek, de
straat is een handvol gevallen die je kunt natrekken, het pand is een dossier.
straatprofiel() in pandgeschiedenis.py levert per straat de aanvragen met hun
afloop, de bekende kamerverhuurpanden, wat er verkocht is, wat er te koop staat
en de labels die we hebben.

**Geen kansen en geen scores.** Mark wilde dit expliciet niet: bij een handvol
gevallen per straat is een percentage een toevalscijfer, en het gooit weg wat
telt, namelijk welk pand het was en waarom het wel of niet doorging. De
opdracht aan de brief verbiedt het nu met zoveel woorden. Een geweigerde
aanvraag telt daarbij net zo zwaar als een verleende.

**Wat er niet in gaat: misdrijfcijfers per straat.** Die worden niet
gepubliceerd, en terecht, want ze zijn dan herleidbaar tot panden. Het
buurtcijfer blijft, met vermelding dat het de buurt betreft.

**Het logboek, en wat het bewust niet is.** brief_logboek.py legt per brief
vast welk onderwerp is gekozen en wat er verder lag. Geen wachtrij: een
onderwerp dat drie dagen wacht is vaak alleen nog waar en geen nieuws meer, en
een brief die op leeftijd kiest in plaats van op nieuwswaarde opent met iets
van vorige week. Dezelfde fout die de BAG-wachtrij liet vastlopen.

Het logboek dient twee momenten: de brief mag iets van eerder oppakken als er
iets nieuws bij is gekomen, en de weekeditie loopt na wat er bleef liggen.

**TESTRUNS SCHRIJVEN NIETS IN HET LOGBOEK.** Dat was Marks harde eis, en
terecht: op 28 september streepten testruns de artikelen al af, waardoor de
echte brief zonder nieuws zat. Bij het logboek zou een onderwerp bovendien als
verteld gemarkeerd staan. De bescherming loopt via alleen_lezen() in
diagnose.py, en bij twijfel wordt er niets weggeschreven. Het rapport telt de
brieven in het logboek, zodat zichtbaar is dat er een per dag bij komt.

---

## 10a. Een juridische verwisseling in de brief — 1 oktober 2026

De brief van 1 oktober schrijft dat een omzettingsvergunning de toestemming is
om een pand in meerdere losse woningen te verdelen. Dat klopt niet, en het is
precies de verwarring die bij kamerverhuur het meest kost.

Artikel 21 van de Huisvestingswet kent vier ingrepen met elk hun eigen naam:
**omzetten** is een zelfstandige woning naar onzelfstandige woonruimte brengen,
dus kamerverhuur; **woningvorming**, in de praktijk splitsen genoemd, is een
pand verbouwen tot twee of meer zelfstandige woningen; **onttrekken** haalt
woonruimte uit de bewoning; **samenvoegen** maakt van twee woningen een. De
opdracht aan de brief legt dat nu vast, met de instructie dat "omzetting" in
een bekendmaking altijd over kamers gaat.

**En de dekkingstoets was te streng.** "Regeling noodfonds blokverwarming
gemeente" bleef als gat staan terwijl we er die ochtend een stuk over hadden
geschreven, omdat de toets de hele term wilde matchen. Nu telt een kenmerkend
woord uit de term ook; woorden als wet, regeling en gemeente zeggen daarbij
niets. Van de twee overgebleven voorstellen blijft er daarmee een echte over.

**Wat er verder goed ging in deze run:** de versiecontrole staat op OK, dus
alle 32 bestanden draaien, en het vergund-en-verkocht patroon staat nu met vier
panden in de brief. Dat was gisteren nog toeval en is nu een berekening.

---

## 10b. De versiecontrole sloeg om zonder dat er iets veranderde — 1 oktober 2026

Om 15:48 stond de versiecontrole op OK, om 17:24 op LET OP met de melding dat
versies.py een oudere versie is. Tussen die twee runs heb ik aan dat bestand
niets gewijzigd, dus er is in de repo een oudere versie overheen gekomen.

**De melding noemt nu wat er werkelijk staat:** hoeveel bytes het bestand is,
wanneer het is gewijzigd en welke functies erin zitten. Dan hoeft niemand op
mijn woord te geloven dat het een ander bestand is. In de test:
"mist de functie controleer (144 bytes, gewijzigd 18:55); hij kent:
vingerafdruk".

**Ter vergelijking:** de versies.py die ik lever is 5157 bytes en bevat
controleer. Dat is in één oogopslag te vergelijken met wat de melding zegt.

**Wat dit laat zien over de paklijst zelf:** versies.py staat bewust niet in
die lijst, want hij controleert zichzelf niet. Daardoor kan juist dit bestand
stil verouderen. De melding vangt dat nu op, en dat is precies waarom de
controle ook naar zijn eigen gereedschap moet kijken.

---

## 10c. De stand terug in het korte rapport — 1 oktober 2026

**Mark:** worden de pandgegevens inmiddels completer?

Het antwoord stond in het rapport maar niet in cijfers: "Geschiedenis per pand"
komt niet meer voor bij de meldingen, dus die 149 panden die nooit waren
nagekeken zijn weggewerkt. Dat was gisteren de grootste openstaande post.

**Maar de getallen waren verdwenen**, en dat is een gevolg van het inkorten van
vanmiddag. Onderdelen die goed gaan staan alleen nog in het digestbestand. Voor
een controle die een ja of nee geeft is dat prima; voor een teller die ergens
naartoe groeit niet, want dan zie je niet meer of de voorraad zich vult.

**Er staat nu een regel Stand in het korte blok**, met alleen de tellers die
oplopen: panden gevolgd, met BAG-gegevens, met label, nog niet nagekeken, de
3D BAG, het aantal huurwaarnemingen en verkopen, en het aantal panden met een
eigen WOZ. In de test:

Stand: 1692 panden, 1353 met BAG, 614 met label, 0 nog niet nagekeken;
3D BAG: 280 van 300; 46 huurwaarnemingen, 505 verkopen; 22 panden met eigen WOZ.

**Dat is een regel die week na week iets zegt.** Een getal dat niet beweegt is
deze week vaker een signaal gebleken dan een melding die oplichtte, en nu is
dat in het blok te zien dat Mark toch al plakt.

---

## 10d. Een reeks om een uitpondgolf in te zien — 1 oktober 2026

**Mark:** houden we bij hoeveel woningen er te koop en te huur staan, zodat we
een uitpondgolf kunnen zien?

**Nee, en dat was een gat.** Elke brief noemde het aantal panden in beeld, maar
dat werd nergens bewaard. Zonder reeks is een golf niet te zien.

**Drie maten, en ze zijn niet even betrouwbaar.** De voorraad, dus hoeveel
panden er te koop staan, is bij ons de zwakste: ons aanbod groeit alleen aan en
een pand dat verkocht wordt zonder dat wij het horen blijft staan. Een
oplopende voorraad kan dus ophoping zijn in plaats van marktgroei. De instroom
is wel zuiver, want elke nieuwe advertentie is een waarneming met een datum;
dat is de maat voor een golf.

**En er is iets scherpers: nieuw aangeboden panden die bij ons als kamerverhuur
bekend staan.** Dat is geen omweg maar precies waar een uitpondgolf uit
bestaat, namelijk verhuurd bezit dat te koop gaat. Dat getal komt uit het
kamerverhuurregister en de meldingen brandveilig gebruik, die we al hebben.

Per week opgeteld in plaats van per dag, want dagcijfers zijn te klein en
attenderingen komen met pieken binnen. Dezelfde dag overschrijft, dus een
tweede run telt niet dubbel.

**Wat je er niet mee kunt:** een golf vaststellen uit twee weken meten. Het
rapport zegt daarom hoeveel dagen er in de reeks zitten, en pas na een week of
zes begint een trend iets te betekenen.

---

## 10e. Het profiel van het nieuwe aanbod — 1 oktober 2026

Niet hoeveel panden erbij komen, maar wat voor panden. Een markt verandert vaak
eerst van samenstelling en pas daarna in aantallen: komen er een maand lang
alleen kleine woningen met een slecht label bij, dan is dat nieuws ook als het
totaal gelijk blijft.

**Drie vensters, en het derde is bewust anders.** De laatste dertig dagen, de
dertig daarvoor om mee te vergelijken, en een voortschrijdend jaar als ijkpunt.
Dat laatste is geen vergelijking: over een jaar spelen seizoen en rente mee.
Het zegt alleen of een verschil uitzonderlijk is of binnen de normale
schommeling valt. En voortschrijdend, niet vanaf 1 januari, want zo'n cijfer is
in januari leeg en in december vol en betekent elke maand iets anders.

**Wat erin staat:** mediane oppervlakte, mediane prijs per m2, de verdeling
over drie labelgroepen, en het aandeel panden dat volgens de BAG in een complex
zit. Labels in drie groepen en niet in zeven, want met zestig tot tachtig
panden per venster is zeven klassen te fijn.

**Het aandeel onbekende labels staat er altijd bij.** Zolang onze
labelverzameling groeit, kan een verschuiving in de labelverdeling net zo goed
onze eigen voortgang zijn als een verandering in de markt. Het rapport meldt
het apart zodra we van meer dan de helft het label niet kennen.

**In de weekeditie, niet in de dagelijkse brief.** Een profiel over dertig
dagen verandert niet per dag, en de opdracht zegt erbij dat een paar vierkante
meter verschil tussen twee steekproeven niets betekent.

Getest met een opzettelijke verschuiving: mediaan van 122 naar 55 m2 en van
goede naar slechte labels. Dat komt er goed uit, inclusief de melding dat van
acht van de 25 panden het label ontbreekt.

---

## 10f. De 3D BAG is rond, op vier panden na — 1 oktober 2026

274 panden opgehaald, nul zonder gegevens, vier fouten, nog nul te gaan, totaal
1168. Daarmee is de snapshot in feite compleet: we hebben voor 1168 panden het
buitenmuuroppervlak, het dakvlak, het grondvlak en de hoogte.

**Die vier fouten kwamen elke run terug**, want een mislukt pand werd niet
onthouden. Dezelfde eindeloze herhaling als bij de pand-ids in de
geschiedenisstap, nu bij een andere bron. Een pand krijgt nu drie pogingen en
daarna niet meer, en het rapport meldt hoeveel er zijn opgegeven.

**Een valkuil die de test blootlegde:** klaar is niet hetzelfde als bekend. Een
pand met een mislukte poging staat wel in het bestand maar is niet af. Keek de
wachtrij alleen of een pand bekend was, dan kreeg het nooit een tweede kans;
keek hij er helemaal niet naar, dan kwam het eeuwig terug. Nu telt een pand als
klaar zodra er gegevens zijn of de bron er na drie pogingen niets over geeft.

**Wat dit mogelijk maakt:** die 1168 panden hebben nu een gemeten
buitenmuuroppervlak en een afleidbare verdiepingshoogte. Daarmee kan de
maatregelenketen van vanmiddag, bouwjaar naar norm naar oppervlak naar prijs,
voor het eerst met echte vierkante meters rekenen in plaats van met een
aangenomen hoogte.

---

## 10g. De volledige ronde terug naar het weekend — 1 oktober 2026

**Mark:** is de pandgeschiedenis nu een keer volledig opgehaald, en kunnen we
uitzetten dat elke handrun alles naloopt?

**Ja.** "Nog niet nagekeken" staat op nul en de 3D BAG heeft nul te gaan. De
vlag --volledig stond bij elke handmatige start aan om de achterstand in te
lopen; die is weg, en hij was bedoeld voor de weekeditie.

**Het is nu een keuze bij de handmatige start**, een vinkje volledig dat
standaard uit staat. In de weekeditie gaat hij altijd aan. De 3D BAG-stap volgt
dezelfde keuze: 2000 panden per ronde in het weekend of op verzoek, anders 300.

**Een gevolg om te onthouden:** de energielabels groeien alleen mee tijdens
zo'n volledige ronde. Er staan er 614 van de 1353, dus die vullen zich vanaf nu
in het weekend. Het rapport zet dat erbij zodra het aantal labels achterblijft
bij het aantal panden met BAG-gegevens, zodat een stilstaand getal niet als
storing wordt gelezen.

Dat laatste is deze week de meest terugkerende les: een getal dat niet beweegt
moet uitleggen waarom, anders gaat iemand zoeken naar een fout die er niet is.

---

## 10h. Twee tellers, twee antwoorden — 1 oktober 2026

De nieuwe Stand-regel deed meteen waarvoor hij bedoeld is: hij meldde 648
verkopen terwijl de controle erboven 505 zei. Twee tellers op hetzelfde bestand
horen hetzelfde getal te geven.

**Oorzaak:** de Stand telde op tekst in de regel, dus "| verkocht" ergens in
een adres of een toelichting telde mee. De controle telt op het statusveld. Nu
tellen ze allebei op velden, en staan verkocht en verkocht onder voorbehoud
apart, want dat laatste is een status die nog kan omslaan.

**Wat de Stand verder laat zien, en dat is goed nieuws:** 1473 panden met
BAG-gegevens tegen 1353 gisteren, 730 met een label tegen 614, nul nog niet
nagekeken, en de 3D BAG compleet op 1168 van 1168.

**Dat die inconsistentie binnen een dag opviel, is precies het nut van die
regel.** Hij staat in het blok dat Mark toch al plakt, dus een getal dat niet
klopt valt op zonder dat iemand ernaar hoeft te zoeken.

---

## 10i. Afwijkend is niet hetzelfde als ontbrekend — 1 oktober 2026

**Mark:** die bestanden staan gewoon in de lijst; wat gaat er mis?

**Twee verschillende dingen stonden in een zin.** "Niet aanwezig" betekent dat
het bestand er niet is; dat gold alleen voor aanbod_reeks.py. "Andere inhoud"
betekent dat het er wel staat maar anders is dan de paklijst, en dat gold voor
vijf bestanden.

En bij die vijf zit nog een onderscheid dat de melding niet maakte. Vier ervan
heb ik die dag gewijzigd en wachten op een upload. Maar
bekendmakingen_nijmegen.py heb ik deze sessie niet aangeraakt; daar is
waarschijnlijk mijn kopie de oude en niet die van Mark. Dat is dezelfde
situatie als bij ov_haltes.py, dat we daarom uit de paklijst hebben gehaald.

**De melding noemt nu de datum van het bestand in de repo.** Is die nieuwer dan
de paklijst, dan is de paklijst oud en hoeft er aan dat bestand niets te
gebeuren. Dat scheelt een upload die niets oplost en een zoektocht naar een
fout die er niet is.

**En de paklijst zelf noemt zijn eigen datum**, zodat je die twee kunt
vergelijken zonder het bestand te openen.

---

## 10j. Het rapport is voor Claude, niet voor Mark — 1 oktober 2026

**Mark:** het gezondheidsrapport hoef ik niet te begrijpen; als jij maar weet
wat er staat. Ik plak het direct in de chat.

Dat verandert het ontwerp. De adviesregels onder elke melding zijn geschreven
voor iemand die zonder context moet kunnen handelen. Als de lezer Claude is,
hoeft er niet bij te staan wat "505 geplakt, 0 uit de mail" betekent of wat
eraan te doen valt; dat volgt uit de regel zelf.

**De adviesregels zijn uit het korte blok gehaald.** Dat scheelt ruwweg een
derde van wat er vanaf een telefoon gekopieerd moet worden, en bij een rapport
met veel meldingen loopt dat snel op. De uitleg blijft staan in het volledige
rapport in het digestbestand, voor als iemand het zonder context moet lezen.

**Wat er in het korte blok blijft:** de telling, een regel per melding met het
bewijs, de Stand met de tellers die groeien, en wat er is veranderd sinds de
vorige run. Dat is alles wat nodig is om te zien of er iets aan de hand is, en
genoeg om samen te analyseren.

---

## 10k. De bestandsdatum zei niets — 2 oktober 2026

Gisteren zette ik de datum van het bestand bij een afwijking, zodat te zien zou
zijn of de paklijst oud was of het bestand. In het rapport van vanochtend staan
alle vijf de afwijkende bestanden op 02-10 06:39: dat is het moment waarop
GitHub de repo uitcheckt. In een workflow heeft elk bestand dezelfde tijd,
ongeacht wanneer de inhoud is geschreven. Die hint is dus weg.

**Wat er in plaats daarvan geldt:** blijft een bestand afwijken nadat het is
geuploud, dan is de paklijst achter en moet die ververst worden. Dat is de
enige conclusie die de vingerafdruk zelf kan dragen.

**En dat is hier ook het geval.** Mijn kopie van alle zes de genoemde bestanden
is identiek aan de paklijst, dus de paklijst klopt met wat ik lever. Blijven ze
in de repo afwijken, dan is daar iets anders geuploud dan wat ik heb
meegegeven.

**Twee getallen uit dit rapport om in de gaten te houden:** 5 panden nog nooit
nagekeken, na nul gisteren, en 224 zonder pand-id tegen 188. Nieuwe panden
komen binnen via het archief en wachten op de eerstvolgende volledige ronde, en
dat is sinds vanochtend de weekeditie. Dat verklaart de eerste; de tweede niet,
want zonder volledige ronde kan die groep niet groeien. Daar wil ik het logboek
van de geschiedenisstap bij zien.

---

## 10l. Afkortingen de eerste keer voluit — 2 oktober 2026

**Mark:** wat betekent BOPA? Schrijf afkortingen altijd voluit met de afkorting
tussen haakjes erachter.

Terecht. De brief van 2 oktober opende met "een BOPA-besluit" zonder uitleg,
terwijl een eerdere brief dezelfde term wel had toegelicht. Zo moet pa per
brief maar hopen dat het er toevallig bij staat.

**De regel staat nu in de opdracht**, en de voluitschrijvingen staan in
bronnen.py zodat de brief ze niet zelf verzint en ze overal hetzelfde zijn.
Zeventien stuks: BOPA is buitenplanse omgevingsplanactiviteit, en verder onder
meer WWS, BAG, Bbl, VvE, WOZ, OZB, ISDE, SVOH, EPBD, NAR, BAR, LTV en COROP.
Die lijst gaat als blok mee in de opdracht.

**Eén nuance in de regel:** voluit bij het eerste gebruik in die brief, niet
elke keer opnieuw binnen dezelfde brief. En nooit een afkorting gebruiken die
niet eerst is uitgeschreven, ook niet als pa hem vorige week heeft gelezen.

**Een foutje bij het inbouwen:** de lijst werd tussen twee f-strings gezet
zonder plusteken, waardoor het bestand niet meer te lezen was. Gevonden met de
syntaxcontrole voordat het de repo in ging; dat is precies waarom die controle
na elke wijziging draait.

---

## 10m. Een achtergrondstuk over de BOPA — 2 oktober 2026

Negenentwintig stukken nu. De kern voor ons: een BOPA is de route zodra het
omgevingsplan iets niet toestaat, en bij splitsen en verkameren is dat in
Nijmegen vaak het geval.

**Het toetsingskader is er maar een:** een evenwichtige toedeling van functies
aan locaties, artikel 8.0a van het Besluit kwaliteit leefomgeving. Dat is geen
lijst met voorwaarden maar een afweging, en daarom weegt de onderbouwing van de
gevolgen voor de omgeving zwaar.

**Twee dingen die een plan kunnen laten stuklopen en die niet over de inhoud
gaan.** Het bindend adviesrecht van de gemeenteraad: voor categorieen die de
raad zelf heeft aangewezen moet die eerst adviseren, en het college mag daarvan
niet afwijken. In de praktijk een instemmingsrecht. En participatie: niet
verplicht tenzij de raad die categorie heeft aangewezen, maar bij de aanvraag
moet je wel opgeven of en hoe je de buren hebt betrokken, en een dossier met een
gedragen omgevingsdialoog staat bij bezwaar steviger.

**Termijnen:** acht weken, eenmalig te verlengen met zes, plus vier weken als
een ander bestuursorgaan moet instemmen. In aangewezen gevallen de uitgebreide
procedure van zesentwintig weken.

**En een gevolg dat verder reikt dan het pand zelf:** een BOPA zonder einddatum
moet de gemeente binnen vijf jaar in het omgevingsplan verwerken. Een verleende
BOPA in een straat is dus niet alleen een precedent maar op termijn ook een
wijziging van de regels zelf.

**Bij het testen koos de keuzelogica eerst het stuk over splitsen**, omdat dat
woord zwaarder weegt dan de afkorting. Met "bopa-besluit" en "afwijken van het
omgevingsplan" als meerwoordige trefwoorden kiest hij nu het juiste stuk.

---

## 10n. Het logboek was gebouwd maar nooit aangeroepen — 2 oktober 2026

De run van 09:51 was een echte, TESTRUN stond op 0 en de brief ging naar pa.
Juist daardoor viel op dat het logboek leeg bleef: ik had brief_logboek.py
gebouwd maar nergens aangeroepen. Een module die niemand aanroept doet precies
niets, en dat was in het rapport niet te zien omdat de melding "nog geen
logboek" ook klopt als er nooit iets geschreven wordt.

**Nu legt de brief na afloop vast wat hij heeft behandeld en wat er nog meer
lag.** De kandidaten komen uit de bekendmakingen en de publicaties van die dag;
een onderwerp geldt als behandeld wanneer er genoeg kenmerkende woorden van in
de brief terugkomen, zoals een adres of een straatnaam. Dat is grof, maar het
alternatief is de brief laten opgeven wat hij heeft gedaan, en dat is minder
betrouwbaar dan ernaar kijken.

Getest: van vier onderwerpen werd het besluit aan de Biezenstraat als behandeld
herkend en de andere drie als blijven liggen. En met TESTRUN aan wordt er niets
weggeschreven, zoals Mark als harde eis stelde.

**Een les over de volgorde van bouwen:** een nieuwe module hoort in dezelfde
beweging te worden aangeroepen als hij wordt geschreven. Anders staat er een
melding in het rapport die klopt om de verkeerde reden, en dat kostte hier een
dag.

---

## 10o. De testrun schreef toch in het logboek — 2 oktober 2026

In de testrun van 10:16 sloeg "Logboek van de brief" om naar OK. Dat kon niet
kloppen: TESTRUN stond op 1, en Marks harde eis was dat een testrun daar niets
schrijft.

**Oorzaak:** de bescherming hangt aan GEHEUGEN_ALLEEN_LEZEN, en die variabele
wordt in de workflow alleen in de marktprijzenstap gezet. In de briefstap vroeg
mijn controle netjes aan diagnose of dit een testrun was, kreeg "nee" terug, en
schreef weg.

**Twee dingen aangepast, allebei nodig.** De workflow zet de variabele nu bij
de bron, in dezelfde stap waar TESTRUN wordt bepaald, zodat elke stap hem ziet.
En het logboek kijkt zelf naar alle drie de signalen: TESTRUN,
GEHEUGEN_ALLEEN_LEZEN en diagnose. Staat TESTRUN uitdrukkelijk op 0, dan is het
een echte run; staat er niets en zegt diagnose niets, dan wordt er niet
geschreven.

**Wat dit zegt over de eerdere fout van deze week:** op 28 september streepten
testruns de artikelen af, en dat is toen opgelost in de marktprijzenstap. De
bescherming is daar blijven hangen in plaats van jobbreed te worden gezet, en
elke nieuwe stap erft dat gat. Daarom staat hij nu bij de bron.

**De regel die de testrun van vandaag heeft weggeschreven blijft staan.** Hij
draagt de datum van vandaag en wordt door de eerstvolgende echte brief van
dezelfde dag overschreven; daarna loopt het logboek zuiver.

---

## 11. De groottepremie: de basis van elke splitsingscase — 2 oktober 2026

**Mark:** we kopen vierkante meters goedkoop in een groot pand en verkopen ze
duur in kleine eenheden; kunnen we dat meten en automatisch laten meegroeien?

**Dat kan, en het staat al in onze eigen tabellen.** Jan de Wittstraat 6 is
22 m2 voor €8.863 per m2, van Goorstraat 34 is 102 m2 voor €3.823. Een factor
2,3 in dezelfde stad.

**Hoe het meet:** elke waarneming wordt eerst gedeeld door de mediaan van zijn
eigen buurt. Daarmee valt het prijspeil van de buurt eruit en blijft alleen het
effect van de grootte over. Zonder die correctie meet je ligging in plaats van
omvang, want kleine eenheden zitten vaker in het centrum.

De uitkomst is een verhoudingsgetal per grootteklasse met 80 tot 100 m2 als
ijkpunt. Getest met twee kunstmatige buurten met een verschillend prijspeil en
dezelfde ingebouwde premie: 1,55 kwam er terug als 1,544, 1,30 als 1,286, 0,85
als 0,842. De correctie werkt dus.

**Het groeit vanzelf mee.** Het script rekent elke run opnieuw uit wat er op dat
moment bekend is, en het aantal panden per klasse staat er altijd bij. Onder de
acht waarnemingen toont hij geen getal, want dan is het toeval.

**Wat het oplevert voor een pand:** 168 m2 in twee eenheden van 84 m2 brengt de
prijs per m2 van €4.200 naar €4.988, een waardesprong van €132.000 voor de
verbouwkosten. Bij 204 m2 in drie eenheden is dat €317.000.

**Drie waarschuwingen staan erbij.** De verkochte panden dragen de laatste
vraagprijs en niet de transactieprijs, want Funda toont die niet. De premie van
een gesplitste eenheid is aangenomen gelijk aan die van een bestaande eenheid
van dezelfde maat, en dat is pas te toetsen als we een gesplitst pand terugzien
op de markt. En dit getal is alleen de waardesprong: verbouwkosten,
overdrachtsbelasting en verkoopkosten horen in de doorrekening, zodat zichtbaar
blijft welk deel waar vandaan komt.

---

## 12. Verkoopdatums als indicatie — 2 oktober 2026

**Mark:** een indicatie is beter dan wat we nu hebben, want alle 505 verkopen
dragen de dag waarop ik plakte.

**Dat argument is sterker dan mijn bezwaar.** Die datum is niet onzeker maar
aantoonbaar onjuist, en hetzelfde geldt voor het aanbod: panden met een streepje
bij "dagen te koop" zijn panden waarvan we de plaatsingsdatum niet kennen,
terwijl juist dat getal zegt of iets blijft hangen.

**verkoopdatum_model.py vraagt het model per adres**, met webzoeken aan, en
bewaart alleen wat door vier waarborgen komt:

1. Zonder bronvermelding wordt het antwoord weggegooid. Getest: een antwoord
   met datums maar zonder bron komt er niet door.
2. De bron staat in het bestand, zodat elk getal naar zijn herkomst wijst.
3. Datums mogen meerekenen, bedragen niet. Een datum die er een week naast zit
   verandert niets aan een doorlooptijd van drie maanden; een verkoopprijs die
   5% afwijkt verschuift de groottepremie en daarmee elke ontwikkelcase.
4. Het overschrijft nooit een Kadastercijfer of wat Mark zelf invoerde.

**Waarom dat bedrag er apart in staat.** Wat Google terugmeldde als "verkocht
voor €525.000" is de laatste vraagprijs van funda, niet de transactieprijs; die
publiceert funda niet. Het model krijgt daarom de instructie dat bedrag als
laatste_vraagprijs te labelen, en het rekent nergens in mee.

**Een proefstand:** --proef 20 haalt twintig panden op en bewaart niets, zodat
de uitkomst naast wat we al weten gelegd kan worden voordat er vijfhonderd
doorheen gaan. De stap draait alleen in de weekeditie of op verzoek, want het
kost tijd en geld per pand.

**Wat dit mogelijk maakt:** de volgorde van vergunning en verkoop. Bij de
Biezenstraat 110 blijkt de woning in september 2025 verkocht en de BOPA pas een
jaar later verleend. De koper heeft dus eerst gekocht en daarna de vergunning
aangevraagd, en dat is een ander verhaal dan vergunning halen en doorverkopen.

---

## 12a. Twee bestanden met dezelfde naam — 2 oktober 2026

Het rapport meldde: "de versies.py in de repo mist de functie controleer (1500
bytes); hij kent: geen functies". Dat is geen oudere versie maar een heel ander
bestand: versies.json, opgeslagen als versies.py.

**De oorzaak ligt bij mij.** In de chat heten versies.py en versies.json allebei
"versies", want de kaart toont de bestandsnaam zonder extensie. Bij het
downloaden is daardoor de een voor de ander aangezien. Dat is twee keer
gebeurd, en de tweede keer kostte het weer een run.

**Het script heet nu paklijst.py**, de lijst blijft versies.json. Twee
verschillende namen, dus de kaarten zijn niet meer te verwisselen. De workflow
en het gezondheidsrapport verwijzen naar de nieuwe naam, en de melding zegt er
nu bij dat je het script moet pakken en niet de json.

**Verwijder versies.py uit de repo**, anders blijft er een bestand staan dat
nergens meer bij hoort.

**Wat er in deze run wel goed ging:** 31 onderdelen op OK, de verkoopdatums
draaien voor het eerst mee, en de geschiedenis staat weer op nul nog niet
nagekeken panden. De 3D BAG is gegroeid naar 1170 en de labels naar 735.

---

## 12b. De proef legde een systematische fout bloot — 2 oktober 2026

Negentien panden opgehaald, en daar zit een patroon in: het model vindt oude
advertenties en levert die als de huidige.

- St. Stephanusstraat 13: plaatsing 25 mei 2016 met €360.000, terwijl dat pand
  nu te koop staat voor €625.000 en vier dagen in de etalage ligt.
- Beijensstraat 4-A: 2023 met €295.000, terwijl het nu €275.000 vraagt.
- Vondelstraat 26: 2015.
- Burg. Hustinxstraat 140: verkocht 1 oktober 2014, uit kadastralekaart.com.

**De controle die dit afvangt hadden we al in huis: onze eigen vraagprijs.**
Wijkt het bedrag dat het model terugmeldt meer dan vijf procent af, dan gaat het
om een andere advertentie. Vijf en niet tien, want allebei de bedragen horen de
laatste vraagprijs te zijn; bij Marienburg 20 scheelde het 8,6% en dat bleek
inderdaad een andere plaatsing.

**Tweede controle:** een plaatsingsdatum van meer dan twee jaar geleden bij een
pand dat nu te koop staat. Dat kan niet kloppen.

Beide zetten de zekerheid op laag en schrijven de reden erbij, zodat de regel
blijft staan maar nergens voor doorgaat. Het rapport telt ze, en meldt het
apart zodra meer dan een derde een waarschuwing krijgt.

**En de vraag zelf is aangepast:** het model krijgt nu te horen dat het om de
meest recente plaatsing gaat, dat er van veel adressen oude advertenties online
staan, en bij een pand dat te koop staat krijgt het onze vraagprijs mee als
houvast.

**Wat de proef verder laat zien, en dat is bruikbaar:** de bronnen zijn divers.
Funda-links zijn de verkoopgeschiedenis zelf; huispedia, buurtje en drimble zijn
doorplaatsers; kadastralekaart.com geeft een oude eigendomsoverdracht. Alleen de
eerste soort is wat we zoeken, en dat staat per regel in het bestand.

---

## 12c. De modelgegevens horen in de pandgeschiedenis — 2 oktober 2026

**Mark:** een verkoop uit 2016 is geen ruis; waarom is dit geen onderdeel van
pandgeschiedenis.py?

**Daar hoort het thuis, en mijn conclusie van daarvoor was te stellig.**
€360.000 in 2016 tegen €625.000 nu is 74% in tien jaar, en dat is precies wat de
markt heeft gedaan. Die waarneming is niet fout, hij is oud. Een los bestand met
een datum per adres maakte er een momentopname van, terwijl juist de reeks het
interessant maakt.

**Elke gevonden plaatsing of verkoop is nu een gebeurtenis**, naast de
vergunningen en de kamerverhuurmeldingen. De bron gaat mee met het voorvoegsel
"model:", zodat een datum die een model ergens heeft gelezen nooit hetzelfde
gewicht krijgt als een bekendmaking uit het gemeenteblad. De waarschuwing uit de
toets staat in de tekst van de gebeurtenis, dus die blijft zichtbaar zonder dat
de regel wordt weggegooid.

**Drie dingen rollen daar vanzelf uit, en geen ervan is op te zoeken:**
- de mediane verkooptijd, dus hoe lang een pand te koop staat;
- de mediane bezitsduur, het verschil tussen twee opeenvolgende verkopen van
  hetzelfde pand. In een studentenbuurt wisselt bezit sneller dan in een
  gezinsbuurt;
- de prijsgroei per pand, van verkoop tot verkoop. Dat is zuiverder dan een
  buurtmediaan, want alles is gelijk behalve de tijd.

Getest met twee panden: verkooptijd 233 dagen, bezitsduur 16 jaar, prijsgroei
3,8% per jaar. Het rapport toont ze met het aantal panden erbij.

---

## 12d. Meerdere verkopen per pand — 2 oktober 2026

**Mark:** een pand kan in tien jaar meerdere keren verkocht zijn; is daar
ruimte voor?

**In de opslag wel, in de ophaler niet.** De pandgeschiedenis is een lijst
gebeurtenissen, dus drie verkopen staan er als drie regels in. Maar de ophaler
stelde per adres een vraag en kreeg een enkele datum terug; vond het model drie
verkopen, dan leverde het er een. De reeks zou dan heel langzaam ontstaan
doordat een volgende ronde toevallig iets anders vindt.

**Nu vraagt hij om alle plaatsingen en verkopen die het model vindt**, als
lijst, met per gebeurtenis een eigen bron en zekerheid. Een regel zonder bron of
met een onbruikbare datum valt af, de rest blijft staan. Eén ronde over de
vijfhonderd panden levert daarmee de hele reeks in plaats van alleen de laatste.

**De toets is van karakter veranderd.** Die gooide eerdere advertenties weg of
waardeerde ze af. Dat was verkeerd: een pand dat in 2016 voor €360.000 wegging
en nu €625.000 vraagt, is een gemeten prijsontwikkeling van datzelfde pand. De
toets merkt zo'n regel nu alleen aan als eerdere advertentie, zodat hij niet
wordt aangezien voor de plaatsing die wij volgen.

Getest met zeven gebeurtenissen waarvan twee onbruikbaar: vijf blijven over, de
oude vier zijn gemerkt, de huidige niet. En de inlezer leest nog steeds de oude
vorm, zodat de negentien panden uit de eerste proef niet verdwijnen.

**Wat de reeks oplevert bij drie verkopen:** twee waarnemingen van bezitsduur en
twee van prijsgroei in plaats van een. In de test 4,7 jaar en 5,6% per jaar.

---

## 13. De weekeditie kwam te vroeg en de bijlage was een rommeltje — 3 oktober 2026

**De tijd.** De weekeditie stond op vrijdagnacht 22:23 UTC, dus hij kwam
zaterdagochtend binnen. Nu zondagochtend, op dezelfde tijd als de dagelijkse
brief.

**Vier dingen in de bijlage die er niet thuishoren, en ze hebben een gemene
deler: het zijn teksten voor mij, niet voor pa.**

De voorstellenlijst met onderwerpen zonder achtergrondstuk stond integraal in
de brief, inclusief de zin "voeg het toe aan ACHTERGROND in bronnen.py, met
trefwoorden in ACHTERGROND_TREFWOORDEN". Die hoort in het digestbestand en in
het gezondheidsrapport, en is nu uit de brief gehaald.

De rente begon met "GEEN NIEUWS, ALLEEN NASLAG" als kop. Dat was een aanwijzing
voor de brief en geen zin voor de lezer; hij staat nu tussen vierkante haken,
en de opdracht zegt dat alles tussen haken nooit in de tekst terechtkomt.

Er stond een lege kop "Achtergrond van de dag" zonder iets eronder. Die
verschijnt nu alleen als er ook werkelijk iets staat.

En onder Regelgeving gewijzigd stond de Uitvoeringswet Nederlands-Duits
Executieverdrag. Dat nummer, BWBR0002481, wijst niet naar de Uitvoeringswet
huurprijzen woonruimte die wij volgen. Het script nam de opgehaalde titel over
zonder te controleren of het de goede wet was. Nu moet minstens een kenmerkend
woord overeenkomen; wijkt het af, dan blijft het uit de brief en komt er een
melding dat onze eigen lijst niet klopt.

**De algemene regel staat nu in de opdracht:** een aanwijzing tussen haken, een
bestandsnaam zoals bronnen.py, of een stuk dat uitlegt hoe het script werkt,
hoort niet in de brief en ook niet in de bijlage.

---

## 13a. De weekronde heeft gewerkt — 3 oktober 2026

33 onderdelen op OK, nul fouten, en de weekeditie heeft gedaan waarvoor de
volledige ronde is bedoeld: de energielabels sprongen van 735 naar 1366, de
BAG-gegevens naar 1560 panden en de 3D BAG naar 1241. Dat is bijna alles wat
we volgen.

**Eén gat in het ruisfilter:** "besluit lag" kwam als voorstel door. Mijn lijst
met zinwoorden bevatte voorzetsels en voltooid deelwoorden, maar geen gewone
werkwoordsvormen. Nu staan ook lag, ligt, staat, blijft, moet, kan, mag, gaat,
treedt en hun verleden tijden erin. Getest: "besluit lag", "besluit staat",
"wet treedt" en "regeling gaat" vallen eruit; Besluit bouwwerken leefomgeving,
Wet betaalbare huur en Wet op belastingen van blijven staan.

**De aanbodreeks staat op OK**, dus die meting loopt. Over een week of zes zegt
die iets over een uitpondgolf.

---

## 13b. 2709 labelwijzigingen die geen wijzigingen waren — 3 oktober 2026

Het digest meldde "2709 labelwijzigingen" terwijl het aantal panden met een
label met ruim zeshonderd groeide. De logica klopte wel, want er wordt alleen
weggeschreven bij een verschil, maar de bewoording niet: dat waren 2709
woningen die voor het eerst een label kregen, niet woningen waar het label
veranderde.

**Twee dingen deugden er niet aan.**

De gebeurtenis kreeg de datum van vandaag. Een label uit 2019 dat wij nu pas
ophalen is geen gebeurtenis van vandaag, en zo leken honderden panden ineens
iets gedaan te hebben. Dat verklaart ook waarom het aantal panden met meer dan
een gebeurtenis in een ronde van 827 naar 1390 sprong. Nu krijgt zo'n regel de
registratiedatum van het label zelf.

En de tekst maakte geen onderscheid. Nu staat er bij een eerste vondst
"energielabel van X is C, geregistreerd 2019-04-12" en bij een echte wijziging
"is nu A, was C". De tellers staan apart in het logboek: zoveel voor het eerst,
zoveel werkelijk gewijzigd.

**Waarom dat uitmaakt:** die gebeurtenissen voeden straks de doorlooptijden en
het patroon vergund-en-verkocht. Een pand dat volgens de geschiedenis vandaag
iets deed terwijl het alleen om onze eigen inhaalslag ging, vervuilt elke
tijdlijn die we erop bouwen.

---

## 13c. Het WOZ-bestand groeide met herhalingen — 3 oktober 2026

**Mark:** hij zet elke dag dezelfde panden er opnieuw in; na tien dagen staat
hetzelfde adres tien keer onder elkaar.

**Klopt, en de oorzaak was een halve controle.** Het script sloeg alleen panden
over waar al een bedrag stond. Een adres dat Mark nog niet had opgezocht, werd
niet herkend als al aanwezig en kwam dus elke dag opnieuw onderaan te staan,
met een nieuwe datumkop erboven.

**Het bestand wordt nu elke keer opnieuw opgebouwd** in plaats van aangevuld:
eerst de ingevulde regels, dan de openstaande, allebei op alfabet. Een adres
dat er al in staat komt niet terug, ingevuld of niet, en eerdere dubbelingen
verdwijnen vanzelf bij de eerstvolgende ronde.

Getest op een bestand met drie dagblokken en dubbele adressen: wat overblijft
is een ingevulde regel en vier openstaande, elk een keer, met een kop die zegt
hoeveel er in elke groep zitten.

**En de Stand in het rapport noemt nu ook het aantal openstaande regels**, zodat
zichtbaar is hoe groot die stapel is zonder het bestand te openen.

---

## 13d. Een werklijst in plaats van meer van hetzelfde — 3 oktober 2026

De kalibratie rust op 22 panden en die zijn allemaal grensgeval, dus rond de
€396.000. Over dat gebied weet het model inmiddels redelijk veel en daarbuiten
vrijwel niets: een pand van €200.000 en een van €700.000 worden geschat met een
curve die daar nooit is getoetst. Meer grensgevallen opzoeken maakt de
schatting dus nauwelijks beter.

**De werklijst kiest op drie dingen:**
- prijsklasse, zodat de curve over het hele bereik wordt getoetst: een paar
  onder de drie ton, een paar boven de zes ton en een paar in het midden;
- straten waar we nog geen enkele WOZ van hebben. Het model rekent per straat
  vanaf drie waarnemingen, dus vijftien panden in vijftien nieuwe straten
  leveren meer op dan vijftien in drie straten;
- grootteklasse, want kleine en grote panden verschillen sterk in prijs per m2
  en zitten nu allebei dun.

Bij elk adres staat de reden waarom het op de lijst staat, dus "prijsklasse
onder 300k; straat nog zonder eigen WOZ; 22 m2, buiten het middengebied".

**Hij staat in woz.txt zelf**, onder een eigen kopje, zodat Mark niet op twee
plekken hoeft te kijken. Ingevuld, nog in te vullen en werklijst, in die
volgorde. Een adres dat al ergens in het bestand staat komt niet terug.

**Wat dit naar verwachting oplevert:** met achttien goed gekozen panden daalt
de spreiding van 24% waarschijnlijk meer dan met honderd willekeurige, en het
is vol te houden. Dat is te toetsen ook: de spreiding staat elke dag in het
gezondheidsrapport.

---

## 13e. Het bestand is niet rommelig, maar telt wel dubbel — 3 oktober 2026

**Mark:** pandgeschiedenis.json ziet er rommelig uit; gaat een volgende run dan
fouten maken of langer duren?

**De ordening is in orde.** De panden staan op alfabet, de gebeurtenissen per
pand op datum, en de sleutels worden gesorteerd weggeschreven. Dat het rommelig
oogt komt door de opmaak met een inspringing van een spatie, niet door de
inhoud. Inlezen van 1704 panden kost milliseconden; de traagheid van een run
zit in de honderden netwerkverzoeken naar de BAG en EP-Online, niet hier.

**Maar in het fragment staat wel een echte fout.** Achter de Carmel 28 en 32
zijn hetzelfde gebouw, met hetzelfde pand-id en dezelfde acht eenheden, maar ze
staan als twee panden in het bestand, elk met de volledige lijst. Het aantal
woningen werd over sleutels opgeteld en telde die acht dus dubbel.

Dat verklaart waarschijnlijk het getal van 13.148 woningen bij 1560 panden, dus
ruim acht per pand, terwijl de hele ring er ongeveer negentienduizend heeft.

**Het rapport telt nu per pand-id** en meldt hoeveel er zonder die correctie
dubbel geteld zou zijn. In de test: negen woningen in plaats van zeventien.

**Wat hiermee nog niet is opgelost:** de dubbele opslag zelf. Een pand onder
twee adressen bewaart twee keer dezelfde eenhedenlijst, en dat maakt het bestand
groter dan nodig. Dat is een grotere ingreep, want de sleutel is het adres en
niet het pand-id; dat raakt elke functie die de geschiedenis opzoekt. De
telling klopt nu, en de opslag kan later.

---

## 14. De pandgeschiedenis slaat hetzelfde gebouw meerdere keren op — 3 oktober 2026

**Mark:** het bestand ziet er rommelig uit; ik hoef het niet te begrijpen, maar
ik vraag me af of de runs daardoor onnodig lang duren.

**Terecht, en het is geen kwestie van opmaak maar van dubbel werk.** Aubadestraat
12 en 16 zijn hetzelfde BAG-pand, nummer 0268100000006348, met 24 woningen. Beide
adressen staan in het bestand met diezelfde 24 eenheden, diezelfde 24 labels en
diezelfde 24 labelgebeurtenissen. Achter de Wiemelpoort 5, 5-A en 5-B delen een
pand van acht eenheden: drie keer hetzelfde. In het fragment dat Mark stuurde
staan alleen al 48 overbodige eenheidregels en 39 overbodige labelregels.

**Erger dan de opslag is het werk.** Het script vraagt die 24 energielabels voor
elk adres opnieuw op bij EP-Online. Dat verklaart waarom een volledige ronde uren
duurt en waarom er 2709 labelregels werden geschreven terwijl er maar een paar
honderd panden bij kwamen.

**Nu wordt per BAG-pand een keer opgehaald** en nemen de andere adressen van
datzelfde pand de labels over, zonder de gebeurtenissen te herhalen. In het
voorbeeld scheelt dat 49% van de opvragingen; over de hele voorraad zal het in
die orde liggen, want complexen komen veel voor in de ring.

**Wat hiermee nog niet is opgelost.** De eenhedenlijst staat nog steeds bij elk
adres apart. Netter is een bestand met de panden op pand-id en een verwijzing
per adres, maar dat raakt elke lezer van pandgeschiedenis.json. Dat is een
verbouwing die apart getest moet worden, niet iets om er achteloos bij te doen.
Het staat hiermee genoteerd als volgende stap.

---

## 14a. Gemeubileerd weggooien was zonde — 3 oktober 2026

Mark zag een advertentie aan de van Spaenstraat: €2.425 voor 103 m2,
gemeubileerd. Dat is €23,54 per m2, terwijl onze gemeten huren in die buurt
tussen de €13 en €18 liggen. Zo'n waarneming werd tot nu toe overgeslagen met
de reden "andere markt".

**De reden klopt, de behandeling niet.** Gemeubileerd hoort niet in de mediaan,
want de inrichting zit in de prijs. Maar weggooien betekent dat we nooit kunnen
meten hoe groot die opslag is, terwijl het een route is die een verhuurder kan
kiezen. Dit was de tweede in een week; eerder kwam de St. Stephanusstraat langs
met €1.188 voor 70 m2.

**Nu krijgen ze een eigen status**, "te huur gemeubileerd". Ze blijven bewaard,
tellen niet mee in de gemeten huren, en er is een berekening die de opslag per
grootteklasse geeft: de mediaan gemeubileerd gedeeld door de mediaan kaal, pas
vanaf drie waarnemingen aan beide kanten. In de test: €23,54 tegen €18,00 per
m2, een opslag van 1,31.

**Mark corrigeerde de uitleg, en terecht.** Die €23,54 is in de eerste plaats
een VRIJE prijs: 103 m2 uit 1902 komt vrijwel zeker boven de 187 punten, en dan
mag de verhuurder vragen wat de markt betaalt. Of er een bank in staat is
daarna pas aan de orde.

Mijn eerste berekening vergeleek gemeubileerd met kaal zonder op het regime te
letten. Als gemeubileerde panden vaker vrije sector zijn, meet je daarmee het
verschil tussen gereguleerd en vrij en plak je er het etiket "meubilair" op.
Dezelfde fout als bij de groottepremie, waar ligging voor omvang werd
aangezien.

**Nu wordt er binnen hetzelfde huurregime vergeleken**, gesplitst op de grens
van €1.228 per maand. Dat is een benadering, want de echte grens staat op
punten en van een huuradvertentie kennen we geen huisnummer en dus geen WOZ of
label. Die beperking staat in de uitkomst vermeld.

In de test met drie gereguleerde kale panden erbij: zonder splitsing kwam de
opslag op 1,31, met splitsing op 1,30 binnen de vrije sector en geen uitkomst
voor gereguleerd. Zodra de aantallen groeien, zegt dat verschil of er binnen de
vrije sector uberhaupt een meubilairopslag bestaat, of dat Marks verklaring de
hele verklaring is.

---

## 15. De verkoopdatumstap kostte twintig euro per run — 3 oktober 2026

**Mark:** dit is de tweede run met ongeveer twintig euro aan kosten; dat was
niet de bedoeling.

**Terecht, en die inschatting was van mij.** De stap stelt per pand een vraag
met webzoeken aan, en elke zoekopdracht kost geld bovenop het model. Vijftig
panden per ronde met vier zoekopdrachten elk is tweehonderd zoekacties. Ik had
dat moeten doorrekenen voordat ik hem in de workflow zette, zeker omdat hij ook
aan de wekelijkse ronde hing.

**De stap staat uit**, niet weg: het script werkt en de uitkomst was bruikbaar.
Hij draait alleen nog als je hem zelf start.

**De gegevens vullen we vanuit de chat aan**, waar het zoeken niets kost. Dat
past ook beter bij wat het is: de verkoopgeschiedenis van een pand verandert
vrijwel nooit, dus het is een eenmalige inhaalslag en geen dagelijkse taak.
Beginnen bij de panden die ertoe doen: de vergunde-en-verkochte panden en wat
Mark serieus overweegt.

**Les voor mezelf:** bij elke stap die per pand een betaalde dienst aanroept,
eerst de rekensom maken. Aantal panden maal aantal aanroepen maal de prijs, en
dat naast wat het aan de brief toevoegt.

---

## 15a. Meer WOZ-waarnemingen halen de spreiding er niet uit — 3 oktober 2026

Mark voerde de hele werklijst in: van 24 naar 39 panden, van 24 naar 36 straten
en van 7 naar 8 buurten. De uitkomst beantwoordt de vraag van gisteren, zij het
anders dan gehoopt.

**Wat wel verbeterde:** de systematische afwijking halveerde van 4% naar 2%.
Dat is precies wat een grotere steekproef doet met een scheve ligging.

**Wat niet verbeterde:** de spreiding bleef op ±23,9%, tot op de decimaal.
Nagekeken of het getal niet bevroren was: het bestand wordt elke run opnieuw
berekend en het aantal ging wel omhoog, dus de spreiding is werkelijk gelijk
gebleven. Dat is logisch ook: de correctie verschuift de band, hij versmalt
hem niet. De spreiding is een eigenschap van de methode en niet van de
steekproef.

**Gevolg voor de werkwijze:** nog dertig panden opzoeken verbetert dit cijfer
niet. Dat scheelt Mark werk, en het is beter dat nu te weten dan over een maand.
De weg vooruit is een betere methode, niet meer waarnemingen.

**Daarom staat de vergelijking tussen de twee methoden nu volledig in de
regel.** Die lijst was beperkt tot twee vaste namen waardoor er maar een
methode in beeld kon komen.

**Correctie, 3 oktober, avond:** ik heb bij die wijziging getallen genoemd van
11% tegen 18% alsof het een bevinding was. Die kwamen uit mijn eigen
testbestand, niet uit de gegevens van Mark. In zijn rapport ontbreekt de
vergelijking helemaal, ook in de run ervoor: woz_vergelijk_methoden levert niets
op. Dat is dezelfde fout als bij de reconstructie van de SVOH-subsidie, waar
een kloppend totaal uit twee fouten bestond: een uitkomst die past is nog geen
uitkomst die klopt.

Het rapport zegt nu met zoveel woorden "geen vergelijking tussen methoden
beschikbaar" als die ontbreekt, zodat die leegte niet nog eens voor een
uitkomst kan doorgaan. Waarom hij leeg blijft, is het eerste dat uitgezocht
moet worden voordat er iets aan de methode verandert.

---

## 15b. Kan een tikfout de spreiding verklaren? — 3 oktober 2026

**Mark:** als er maar een pand ver afwijkt, zou dat ook een invoerfout kunnen
zijn.

**Voor de spreiding kan dat niet de verklaring zijn**, en dat komt door hoe hij
is gebouwd: het tiende en het negentigste percentiel, gehalveerd. Bij 39 panden
zijn dat de vierde en de 35e waarneming op volgorde; een pand dat er ver naast
zit valt daarbuiten en verschuift niets. Precies daarom is die maat zo gekozen.

**Maar het onderliggende punt klopt wel.** Een tikfout in de handmatige invoer
valt nergens op: de spreiding gebruikt percentielen en de correctie is een
mediaan, allebei ongevoelig voor een uitschieter. Zo'n fout verdwijnt dus in de
cijfers terwijl hij bij dat ene pand de hele doorrekening scheeftrekt.

**De ijking noemt nu de panden die meer dan de helft van de mediaan afwijken**,
met adres en percentage, en het rapport zet ze achter de regel: "nakijken:
Marialaan 56 (+105%), Dokstraat 425 (-60%)". Dan is een verdwaalde nul of een
verkeerd overgenomen bedrag binnen een dag te vinden in plaats van nooit.

---

## 15c. De werklijst groeide harder dan hij werd afgewerkt — 3 oktober 2026

Het aantal openstaande WOZ-regels liep in drie runs op van 17 naar 32 naar 44.
Elke ronde zette er achttien bij, ook als de vorige nog niet waren ingevuld.
Een werklijst van honderd adressen wordt niet afgewerkt maar genegeerd.

**Nu zit er een rem op.** Staan er vijfentwintig of meer open, dan komt er niets
bij en meldt de stap dat in het logboek. Zit er nog ruimte, dan wordt die
precies opgevuld tot vijfentwintig. Getest met 26 openstaande regels: geen
enkele toevoeging. Met twintig: aangevuld tot de grens.

**Waarom vijfentwintig.** Dat is ongeveer een half uur werk op het
wozwaardeloket, en daarmee blijft het iets wat je in een keer afmaakt. Vul je
ze in, dan staat de volgende lichting er de dag erna.

**En een melding uit dezelfde run:** de paklijst werd niet gevonden.
versies.json is vermoedelijk meeverdwenen bij het opruimen van versies.py.
Zonder dat bestand kan de versiecontrole niets vergelijken en staat hij op
LET OP zonder dat er iets mis is met de code.

---

## 16. Correctie: meer waarnemingen helpen wel — 4 oktober 2026

Met 67 panden in plaats van 39 ging de spreiding van ±23,9% naar ±19,4% en de
systematische afwijking naar nul.

**Dat weerlegt mijn conclusie van gisteren.** Bij de sprong van 24 naar 39
bewoog de spreiding niet, en daar schreef ik uit op dat het aan de methode lag
en niet aan het aantal. Een vlakke stap tussen twee metingen is geen bewijs dat
een reeks vlak is. Dat is binnen twee dagen de tweede keer dat ik een uitkomst
te snel voor een bevinding aanzag; de eerste was de methodevergelijking met
cijfers uit mijn eigen testbestand.

Wat wel blijft staan: de methodevergelijking is nog altijd leeg, dus of het
kenmerkmodel beter is dan de prijsindex weten we nog steeds niet.

**Een tikfout gevonden, en dat is waarvoor de uitschietercontrole is gebouwd.**
Jan de Wittstraat 6 stond op +1113%: een pand van 22 m2 met een vraagprijs van
€195.000. Zo'n afwijking kan geen echt pand zijn, dus daar staat een nul te
veel.

**Zulke waarden tellen nu niet mee in de ijking.** Meer dan vier keer zo hoog of
laag als de schatting is vrijwel zeker een invoerfout. Ze blijven wel in de
uitschieterlijst staan met de vermelding "telt niet mee", want een fout die uit
beeld verdwijnt wordt nooit hersteld. Het rapport meldt hoeveel waarden er
buiten beschouwing zijn gelaten.

**De twee andere uitschieters zijn van een andere orde:** Derde Walstraat 108
op +109% en Havenweg 34 op -68%. Die kunnen een invoerfout zijn, maar ook een
pand dat werkelijk afwijkt, bijvoorbeeld door een bedrijfsruimte op de begane
grond of een monumentenstatus. Die blijven meetellen tot Mark ze heeft
nagekeken.

---

## 16a. Waarom de methodevergelijking leeg bleef — 4 oktober 2026

Dezelfde fout als eerder bij de ijking: woz_vergelijk_methoden zocht de WOZ op
het pand zelf, terwijl die waarden in woz.txt staan en pas later aan de panden
worden gehangen. Dus vond hij er geen een, bleef de lijst leeg, en leek het
alsof er niets te vergelijken viel.

De functie leest de tabel nu zelf, met dezelfde rem op vermoedelijke tikfouten
als de ijking. Getest met vervangende schatters die er respectievelijk 10% en
25% naast zitten: beide komen er met het juiste aantal panden uit.

**Wat er bij de volgende run moet verschijnen:** twee percentages achter
"mediane fout per methode". Is het kenmerkmodel duidelijk lager, dan wordt dat
de standaard voor panden waar genoeg straatgegevens zijn.

**Twee dingen uit hetzelfde rapport die opvallen.**

De groottepremie staat nu op 571 waarnemingen en de curve is overtuigend:
1,422 onder de 40 m2 tegen 0,911 boven de 130 m2. Dat is een factor 1,56 tussen
het kleinste en het grootste segment, gemeten en gecorrigeerd voor de buurt.
Daarmee is de kern van elke splitsingscase geen aanname meer.

En de mediane bezitsduur van 0,8 jaar klopt niet. Die komt uit paren van
verkopen waarvan er een uit de geplakte lijst komt met de datum van het plakken,
28 september. Zolang die datums ontbreken, meet dit cijfer vooral onze eigen
invoer. Dat hoort met een waarschuwing in het rapport of er voorlopig uit.

---

## 17. Een verkoopdatum uit een YouTube-video — 4 oktober 2026

In het dossier van de Veemarkt 277 staat: "te koop aangeboden, vraagprijs
€375.000 (zekerheid laag), bron youtube.com/watch?v=... (video geplaatst '128
days ago')". Het model heeft een plaatsingsdatum afgeleid uit de leeftijd van
een video.

**Dat kwam erdoor omdat mijn controle alleen eiste dat er een bron was**, niet
dat die deugde. Een YouTube-link is een bron, dus de regel kwam binnen.

Twee filters erbij. Bronnen waar geen verkoopgeschiedenis in kan staan vallen
af: video's, sociale media en marktplaatsen. En een bron die een relatieve
tijdsaanduiding bevat, zoals "128 days ago" of "3 maanden geleden", valt ook af:
dan is de datum een berekening van het model en geen gevonden datum. De
opdracht aan het model zegt dat nu ook met zoveel woorden.

**En het dossier was onleesbaar geworden.** Berg en Dalseweg 81 leverde 120
labelregels op, een per woning in het complex. Die worden nu samengevat in een
regel: "energielabels van 120 woningen in dit pand (A++: 90, A+++: 30)".

Daarbij telt een labelregel niet meer mee in de volgorde waarin panden worden
getoond. Anders staan de flats bovenaan omdat ze de meeste gebeurtenissen
hebben, terwijl een pand met drie vergunningen interessanter is dan een flat met
honderdtwintig labels. In de test komt Ackerbroekweg 31 met drie vergunningen
daardoor boven Berg en Dalseweg 81 met 122 regels.

---

## 18. Een aanwijzing die drie keer in de brief belandde — 4 oktober 2026

De renteregel stond eerst als "GEEN NIEUWS, ALLEEN NASLAG" in de bijlage. Ik
zette er vierkante haken omheen, en toen stond er "[niet opnemen: onveranderd]".
Twee keer het probleem verplaatst in plaats van opgelost.

**De fout zat in het ontwerp.** Een aanwijzing voor de brief hoort niet in de
tekst die de brief leest, want alles wat erin staat kan erin terechtkomen. Nu
staat er een gewone Nederlandse zin: "Onveranderd sinds de vorige meting:
5.10% bij 50% LTV ...". Die leest in de bijlage als naslag, en de opdracht
herkent hem aan het eerste woord.

**En er staat nu een algemene regel in de opdracht:** komt er in een bron een
stuk tussen vierkante haken voor, een woord in kapitalen dat een opdracht is,
of een zin die zegt wat de brief moet doen, dan is dat nooit tekst voor pa.

**Twee dingen die ik nog niet kan verklaren uit dit materiaal.** De brief staat
drie keer achter elkaar in wat Mark stuurde, en het HTML-bestand bevat twee
complete documenten met elk een eigen DOCTYPE. Dat kan aan het plakken liggen,
maar het kan ook betekenen dat de briefstap zijn uitvoer meerdere keren
wegschrijft. Dat is na te gaan met het bestand digests/2026-10-04-brief.md
alleen.

---

## 19. De vergelijking werkt, en mijn verwachting was fout — 4 oktober 2026

Met 82 panden staat de spreiding op ±15,0%, tegen 19,4% bij 67 en 23,9% bij 39.
Meer waarnemingen blijven dus helpen, en mijn conclusie van 3 oktober dat de
methode de beperking was, is daarmee definitief weerlegd.

**En de methodevergelijking komt er nu wel uit, met een onverwachte uitkomst:**
de prijsindexmethode zit op 11,0% mediane fout, het kenmerkmodel op 16,1%. Ik
had gezegd dat het kenmerkmodel waarschijnlijk beter zou zijn en dat we daarop
moesten overstappen. Dat was een verwachting zonder meting, en hij klopt niet.
De methode die al in gebruik is, is de betere.

Het rapport zegt nu welke methode wint, zodat die conclusie niet uit twee
percentages hoeft te worden afgeleid.

**Wat dit betekent voor de volgende stap:** niet de methode omgooien, maar
doorgaan met WOZ-waarden invoeren. Van 39 naar 82 panden halveerde de spreiding
bijna; de werklijst houdt zichzelf op vijfentwintig open regels, dus het is
behapbaar.

**Les, en het is deze week de derde van dezelfde soort:** ik trok een conclusie
uit twee metingen, uit een lege uitkomst, en uit een verwachting over welke
methode beter zou zijn. Alle drie bleken onjuist toen er gemeten werd.

---

## 19a. Beide open vragen beantwoord — 4 oktober 2026

De renteregel staat nu als "Onveranderd sinds de vorige meting: 5.10% bij 50%
LTV ..." in de bijlage. Leesbaar als naslag, en de opdracht herkent hem aan het
eerste woord. En de brief staat een keer in het bestand; de verdubbeling kwam
van het samenvoegen van meerdere digests in een bericht.

**Een echte fout in dezelfde tabel:** bij de Stadsbegroting stond als vindplaats
"nijmegen.begroting-<jaar>.nl". In de HTML-versie van de brief leest een browser
<jaar> als een onbekende tag en verdwijnt het woord, dus pa zag
"nijmegen.begroting-.nl". Nu staat er JAAR in hoofdletters; dat overleeft elke
opmaak.

**Twee andere dingen in die tabel, een samengelopen rij en een streepjeslijn van
zes tekens, laat ik staan.** Die zijn niet te onderscheiden van een
plakartefact, en ik heb deze week twee keer achter zo'n artefact aan gezeten.
Komen ze terug in een los aangeleverd bestand, dan zijn ze echt.

---

## 20. Een tegenspraak in het dossier — 4 oktober 2026

Bij de Zwaluwstraat 175 en de Krayenhofflaan 47 staat splitsen twee keer in
hetzelfde dossier: een keer als "route afgevallen op de opkoopbescherming" en
een keer als "alternatief: splitsen in 2 geeft €1.220 per maand". Voor de lezer
is dat een tegenspraak, en bij een beslissing van vier ton is dat geen detail.

Het alternatief wordt nu weggelaten voor een route die al is afgevallen. Blijft
de route open, dan blijft het alternatief staan.

**En de WOZ van de Zwaluwstraat is geland.** Met €376.000: 159 punten,
€1.042 wettelijk maximum, richtprijs €218.119 in plaats van de €321.589 die op
de gemeten markthuur rustte. Precies de uitkomst die we met de hand vonden toen
Mark de WOZ opzocht, en een verschuiving van ruim een ton.

**Wat daarbij opvalt over de schatting.** Bij de Krayenhofflaan 47 stond op 1
oktober €518.000 als schatting; de ingevoerde waarde is €360.000. Dat is 44%
ernaast, en het draait de case om: boven de grens leek het vrij, onder de grens
geldt de opkoopbescherming. Dat is het sterkste argument om bij een pand dat
ertoe doet nooit op de schatting te varen, ook niet nu de spreiding op 15% zit.

---

## 21. De labelsamenvatting werkt, de modeldatums vragen nog twee controles

**De samenvatting doet wat hij moet:** "energielabels van 15 woningen in dit
pand (C: 5, E: 3, D: 2, F: 2, G: 2, A: 1)". Dat waren vijftien regels.

**Maar de modelgegevens laten twee nieuwe soorten fouten zien.**

Verkopen die voor de plaatsing liggen. Graafsedwarsstraat 65 staat verkocht in
januari 2022 en te koop in september 2022; Bloemerstraat 22 verkocht in januari
2014 en te koop in juni 2014. Minstens een van de twee klopt dan niet. Staat er
geen eerdere plaatsing maar wel een latere binnen hetzelfde jaar, dan worden
allebei gemerkt als "volgorde klopt niet met de plaatsing".

En datums op 1 januari. Dat is vrijwel altijd een jaartal dat als exacte datum
is opgeschreven. Zulke regels blijven bruikbaar voor het jaar, maar gaan nu niet
meer voor een dag door: de zekerheid gaat naar laag en er staat "jaar bij
benadering" bij, net als bij de oude vergunningen.

**Een derde punt blijft staan en is lastiger.** Palmstraat 40 en St.
Annastraat 30 hebben allebei twee verkopen op dezelfde dag met verschillende
bedragen en oppervlaktes: 31 m2 en 23 m2 bij de St. Annastraat. Dat zijn twee
verschillende woningen die op hetzelfde BAG-pand belanden. Dat is de keerzijde
van het vastleggen op het pand, en het hoort bij de herstructurering die al
genoteerd staat: panden op pand-id, met per adres een verwijzing.

---

## 22. De pandgeschiedenis herstructureerd — 4 oktober 2026

Een BAG-pand kan meerdere adressen hebben die wij apart volgen. Aubadestraat 12
en 16 zijn hetzelfde pand met 24 woningen, en die lijst stond bij allebei;
Achter de Wiemelpoort zelfs drie keer. Dat maakte het bestand groot, de runs
traag en het dossier onleesbaar.

**De oplossing houdt alle lezers buiten schot.** Het bestand wordt compact
weggeschreven met de gedeelde pandgegevens een keer onder "_panden", en bij het
inlezen vouwt pandlezer.py het weer uit. Elk adres heeft in het geheugen dus
gewoon zijn eigen bag_eenheden en labels, en geen enkele lezer hoeft anders te
rekenen.

**Wat gedeeld wordt en wat niet.** Gedeeld: bag_eenheden, labels en de datum
waarop het pand is nagekeken; die horen bij het gebouw. Niet gedeeld: de
gebeurtenissen, want een verkoop of een vergunning hoort bij een adres. Panden
zonder pand-id blijven staan zoals ze zijn.

**Getest op vier punten:** een bestand in de oude vorm wordt nog gewoon gelezen,
een compact bestand komt uitgevouwen terug, de eigen gebeurtenissen blijven
gescheiden, en bij twee verschillende data van nakijken wint de laatste. De vier
andere lezers, marktprijzen, het aanbodprofiel, het gezondheidsrapport en de 3D
BAG, geven op een compact bestand dezelfde uitkomsten als eerst.

In de proef zakte het bestand van 2740 naar 1535 bytes en verdwenen 48 van de
97 regels. Het rapport meldt die besparing voortaan, zodat het effect op de
echte voorraad zichtbaar is in plaats van aangenomen.

---

## 23. De status "nieuw" viel buiten zes modules — 4 oktober 2026

In verkopen.txt staan twee regels met status "nieuw": Ziekerstraat 10D en
Nieuwe Marktstraat 6. De kop van het bestand noemt die status niet, maar
marktprijzen_bag kent hem wel en behandelt hem als aanbod. De zes nieuwere
modules niet: die filteren op "te koop" en sloegen die panden stilzwijgend over.

Dat raakte de aanbodreeks, het profiel van het nieuwe aanbod, de groottepremie,
de verkoopdatums, het gezondheidsrapport en de pandgeschiedenis. Niet groot in
aantal, maar wel precies het soort stille afwijking waar niemand ooit tegenaan
loopt: er ontbreekt iets en er is geen melding.

Alle zeven plekken accepteren nu "nieuw" naast "te koop". Getest op een bestand
met twee regels "nieuw" en een "te koop": alle drie komen er nu uit, waar het
er eerst een was.

**Wat dit laat zien over het bestand zelf:** de toegestane statussen staan in
een kopregel als commentaar, en daar kan geen enkel script op toetsen. Een
controle die onbekende statussen meldt, zou dit eerder hebben gevonden. Dat is
een punt voor later.

---

## 24. Twee woningen onder een adres — 4 oktober 2026

De drie regels van de St. Annastraat 30 geven het antwoord:

    St. Annastraat 30 | 165000 | onder bod | 23 m2
    St. Annastraat 30 | 189000 | verkocht  | 31 m2
    St. Annastraat 30 | 175000 | verkocht  | 23 m2

Er schuilen twee woningen onder hetzelfde adres: een van 31 m2 en een van
23 m2. Die van 23 m2 staat er twee keer, eerst onder bod en daarna verkocht, en
dat is juist goed: dat is dezelfde woning in twee stadia.

**Het huisnummer-achtervoegsel is bij het plakken weggevallen**, en dat valt
niet terug te rekenen. De oppervlakte is het enige dat de twee onderscheidt.

**Het rapport meldt zulke adressen nu.** Twee maten onder een adres die meer dan
tien procent verschillen zijn geen meetverschil maar een andere woning. Getest
op drie gevallen: de St. Annastraat (23 en 31) wordt gemeld, de Palmstraat met
twee keer 118 m2 niet, want dat is prijsgeschiedenis van een woning, en 86 tegen
87 m2 blijft eronder.

**Correctie na de eerste echte run:** de controle meldde zes adressen, maar drie
daarvan waren "berg en dalseweg", "graafseweg" en "grotestraat", zonder
huisnummer. Dat zijn de huurwaarnemingen van Pararius en Kamernet, die alleen
een straatnaam dragen; twee verschillende maten in dezelfde straat zijn daar
juist normaal. De controle kijkt nu alleen naar koopregels met een huisnummer.

**Wat Mark ermee moet doen:** het juiste adres opzoeken en de regel aanpassen,
bijvoorbeeld naar 30-A. Zolang dat niet gebeurt delen twee woningen een dossier
en een geschiedenis, en dat vertekent elke doorrekening op dat pand.

---

## 25. De rente in de brief is niet onze rente — 5 oktober 2026

**Mark:** er staat dat de rente ongewijzigd is, maar dat zijn de markttarieven
van financieren.nl. Wij hebben zelf rente afgesproken met onze eigen financier,
en dat staat er nu door elkaar.

**Terecht, en het is een verwarring die geld kan kosten.** "Onveranderd sinds de
vorige meting: 5,10% bij 50% LTV" leest als een mededeling over de eigen
portefeuille. Het zijn de scherpste tarieven die banken nu vragen voor een
nieuwe verhuurhypotheek, en die gebruiken we om de richtprijs van een aankoop
door te rekenen.

**Drie dingen aangepast.** Het blok heeft een inleiding gekregen die zegt wiens
tarieven het zijn en waarvoor ze dienen. De regel zelf begint nu met "Het
scherpste markttarief is onveranderd", niet met "Onveranderd". En de opdracht
aan de brief zegt met zoveel woorden dat dit nooit "onze rente" of "onze
financieringslasten" mag worden genoemd.

**En de formulering zelf zei niets.** "Onveranderd sinds de vorige meting" staat
er elke dag, dus een lezer leert er niets van. Nu staat er sinds wanneer de
tarieven werkelijk gelijk zijn: "Het scherpste markttarief is ongewijzigd sinds
12 augustus". Dat is informatie, want acht weken stilstand zegt iets over de
markt.

De datum komt uit de opgeslagen historie: het script loopt terug zolang alle
drie de tarieven gelijk zijn aan nu en noemt de oudste datum waarop dat nog zo
was. Getest op vier gevallen: een stand die sinds augustus gelijk is, een datum
uit een ander jaar (dan komt het jaartal erbij), een lege historie (dan valt hij
terug op de oude formulering) en een tarief dat gisteren nog anders was. In
allebei de modi, dagelijks en wekelijks, staat nu dezelfde zin.

**Wat hier nog uit volgt voor later:** de doorrekening rekent met het
markttarief, en dat is juist voor een aankoop. Maar voor een pand dat we al
bezitten is het de eigen rente die telt. Zodra de eigen financieringsafspraken
in het model staan, moet de doorrekening onderscheid maken tussen een
aankoopcase en een pand in bezit.

---

## 26. Twee regimes door elkaar in de brief — 5 oktober 2026

De brief van 5 oktober opent met de Staringstraat 2: een aanvraag om een pand te
verbouwen tot drie appartementen. Dat is woningvorming, dus splitsen. De
volgende alinea gaat over de WOZ-grens van €396.000 en de omzettingsvergunning,
en die horen bij kamerverhuur.

**De brief schuift daarmee ongemerkt van het ene regime naar het andere.** De
caveat dat het buurtgemiddelde niets zegt over dit pand staat er keurig bij,
maar dat dekt de verkeerde vraag: bij splitsen is die grens helemaal niet de
toets. Dat loopt via het omgevingsplan en zo nodig een BOPA.

De opdracht zegt dit nu met zoveel woorden: gaat een bekendmaking over splitsen,
haal er dan niet de WOZ-grens bij alsof die erover gaat, ook niet als
achtergrond bij de buurt.

**Wat er in deze brief wel goed ging**, en het is het vermelden waard: de
renteregel noemt nu "al sinds 2 september stil", het onderscheid tussen het
markttarief en de eigen financiering staat erin, en de brief toetst een artikel
van vanbruggen.nl over stijgende rente aan de eigen meting en concludeert dat
die elkaar tegenspreken. Dat laatste is precies waarvoor de brief bedoeld is.

---

## 27. De kapitaalmarktrente werd opgehaald maar niet bewaard — 5 oktober 2026

**Mark:** de brief schrijft dat hij met een meting geen trend kan beoordelen,
maar die koppeling hebben we toch gewoon?

**Klopt, en dat was een gemiste kans.** De tienjaars AAA-staatsrente werd elke
dag bij de ECB opgehaald en meteen weer weggegooid; alleen de hypotheektarieven
gingen de historie in. Daardoor kon de brief terecht schrijven dat hij geen
trend kon beoordelen, terwijl de reeks er vanaf vandaag gewoon komt.

**De ECB-stand gaat nu mee in rente_historie.json**, naast de drie
hypotheektarieven. Daaruit volgt een reeks met de stand van nu, die van een
maand geleden en die van drie maanden geleden, met het verschil in
basispunten en het aantal metingen erbij.

In de test met 97 dagen historie levert dat: "Een maand geleden stond die
staatsrente op 3,38%, dus nu +8 basispunten, gemeten over 97 dagen." Met minder
dan twee metingen blijft de regel weg, en dan geldt het oude voorbehoud nog.

De opdracht aan de brief zegt nu dat hij die vergelijking moet gebruiken als hij
er staat, en het voorbehoud alleen moet maken als hij ontbreekt.

**Wat dit over een paar maanden mogelijk maakt:** de vraag of de hypotheekrente
achterblijft bij de kapitaalmarkt. Beweegt de staatsrente wel en het
hypotheektarief niet, dan loopt de risico-opslag op, en dat is iets anders dan
een renteverhoging. Dat onderscheid kan de brief straks zelf maken.

---

## 28. Twee bestanden blijven afwijken van de paklijst — 5 oktober 2026

Na opnieuw uploaden meldt de versiecontrole nog steeds brief_verhalend.py en
rente_verhuurhypotheek.py als afwijkend. Nagekeken aan mijn kant: de paklijst
past precies bij de bestanden die ik stuurde, de regeleindes zijn gelijk en
allebei eindigen op een gewone regelovergang. Het verschil zit dus in de repo.

**De controle zei alleen DAT er iets afwijkt, niet WAT.** Daardoor viel er
alleen te raden: een oudere versie, een halve upload, of een echt verschil. Hij
noemt nu de omvang en het aantal regels van het bestand dat er staat, zodat het
te vergelijken is met wat het hoort te zijn.

Wat het moet zijn: brief_verhalend.py 81.297 bytes en 1.394 regels,
rente_verhuurhypotheek.py 27.856 bytes en 680 regels.

**Gevonden dankzij dat detail:** 81.296 tegen 81.297 bytes en 27.855 tegen
27.856, allebei bij hetzelfde aantal regels. Een byte verschil, dus de
regelovergang aan het einde van het bestand valt bij het uploaden weg.

Dat is geen inhoudelijk verschil, maar de controle kon het niet onderscheiden
van een echte wijziging. De vingerafdruk negeert nu witruimte aan het einde van
het bestand. Alles daarvoor telt onverkort mee, dus een echte wijziging valt nog
gewoon op.

Getest op twee gevallen: een bestand zonder die laatste regelovergang blijft
gelijk, en een bestand waarin een woord is veranderd wordt nog steeds gemeld.

**Wat dit kostte:** drie runs aan zoeken, en twee onterechte vermoedens van mijn
kant. Eerst dacht ik aan de volgorde van uploaden, daarna aan dezelfde val als
met versies.py. Allebei plausibel en allebei fout. Pas toen de controle zelf de
omvang meldde, was het binnen een minuut duidelijk.

---

## 29. Een melding over iets dat goed gaat — 5 oktober 2026

"2 nog nooit nagekeken" zette de geschiedenis op LET OP. Dat zijn panden die
vandaag uit de attendering binnenkwamen; hun BAG-gegevens en label worden
opgehaald bij de eerste volledige ronde, dus uiterlijk zondag. Het systeem doet
dus precies wat het hoort te doen.

**Een melding die afgaat bij normaal gedrag maakt het rapport minder waard**,
want dan went het oog eraan. Nu geldt een drempel van een tiende van wat een
ronde aankan, dus vijftig bij vijfhonderd per ronde. Daaronder staat het als
feit in de regel met de uitleg dat ze net binnen zijn; daarboven is het een
echte achterstand en blijft de melding staan.

**En de versiecontrole staat weer op OK**, met 37 bestanden gelijk. Daarmee is
het verhaal van die ene byte afgerond.

---

## 30. Nieuwe panden hoefden niet tot zondag te wachten — 5 oktober 2026

**Mark:** waarom worden de gegevens van nieuwe panden niet meteen opgehaald? Het
hele bestand nakijken op veranderingen hoort in de weekronde, maar een nieuw
object kan toch elke run?

**Terecht, en dat waren twee dingen op een hoop.** Een nieuw pand voor het eerst
ophalen is een handvol opvragingen per dag: de aanbiedingen die vandaag
binnenkwamen. De hele voorraad opnieuw nakijken op een labelsprong of een
splitsing is duizenden opvragingen. Alleen dat tweede hoort in de weekronde,
maar allebei zaten achter dezelfde vlag.

**Nu haalt elke run de nooit nagekeken panden op.** De wachtrij zette die al
vooraan, dus het script loopt tot het eerste pand met een datum en stopt daar:
geen enkele overbodige opvraging. Getest op een bestand met twee nieuwe en twee
oude panden; alleen de twee nieuwe worden gedaan.

**Wat dit praktisch oplevert:** een pand dat vandaag in de attendering komt,
staat vandaag met oppervlakte, bouwjaar en label in zijn dossier, in plaats van
over vijf dagen. Juist bij een nieuw aanbod is dat het moment waarop je ernaar
kijkt.

---

## 31. Voltooide splitsingen uit de BAG — 5 oktober 2026

Een vergunning zegt dat het mag. De BAG zegt dat het gebeurd is: zodra het
aantal woningen met een eigen adres in een pand omhoog gaat, zijn de nieuwe
eenheden geregistreerd. Dat is het enige harde bewijs van een voltooide
splitsing dat we hebben, en het komt uit een registratie en niet uit een
advertentie.

De BAG-wijziging werd al als gebeurtenis vastgelegd, met het oude en nieuwe
aantal in de tekst. Wat ontbrak was iets dat er een signaal van maakt.

**splitsing_voltooid.py levert drie dingen:**
- panden waar de vergunning is gevolgd door een registratie, met de werkelijke
  doorlooptijd van besluit tot BAG. Dat getal is nergens op te zoeken en elke
  ontwikkelcase heeft het nodig;
- panden die zijn opgedeeld zonder dat wij een vergunning kennen. Dat bewijst
  niets, want wij zien alleen wat gepubliceerd is, maar het wijst op een route
  die we missen;
- vergunningen die na een jaar nog tot niets hebben geleid. Dat zegt iets over
  hoe haalbaar zo'n plan in de praktijk is.

**Getest op vijf gevallen, waaronder twee valkuilen.** Een kamerverhuur-
vergunning telt niet mee, want omzetten is iets anders dan woningvorming. En een
besluit dat NA de registratie komt hoort niet bij die splitsing; zo'n pand komt
terecht bij "zonder bekende vergunning".

**De beperking hoort erbij en staat in het script.** Het aantal woningen wordt
alleen bij een volledige ronde opnieuw opgehaald, dus wekelijks, en we meten pas
sinds eind september. Een splitsing van voor die tijd zien we niet, en de eerste
echte waarneming kan weken op zich laten wachten.

---

## 32. Een vergunning op een pas verkocht pand — 5 oktober 2026

**Mark:** haalt hij er ook bij wanneer dat pand voor het laatst is verkocht?

**Nee, en dat was het ontbrekende stuk.** Bij een bekendmaking stonden de
oppervlakte, het bouwjaar en het label, maar niet wanneer het pand van eigenaar
wisselde. Terwijl dat de helft van het verhaal is: een splitsingsaanvraag een
maand na de verkoop is een koper met een plan, en dat is iets heel anders dan
een eigenaar die na jaren zijn eigen huis verbouwt.

De feitenregel onder een bekendmaking toont nu "verkocht 35 dagen geleden" of
"te koop 9 dagen geleden", uit onze eigen geschiedenis en dus zonder extra
opvragingen. Boven de drie jaar vervalt de regel, want dan zegt het niets meer
over de huidige eigenaar.

Getest op vijf panden: recent verkocht, lang geleden verkocht, recent te koop,
ruim een jaar geleden, en een pand dat we niet kennen. Alleen de eerste, derde
en vierde krijgen een regel.

De opdracht aan de brief zegt erbij dat het ontbreken van zo'n regel niet
betekent dat het pand niet is verkocht; dan weten we het alleen niet.

**Dit sluit het paar rond.** We hadden al vergund-en-verkocht, dus een pand dat
een vergunning kreeg en daarna werd verkocht. Dit is de andere richting:
gekocht en daarna een vergunning. Die tweede is voor ons de interessantere,
want dat is wat wij zelf zouden doen.

---

## 33. Een regel in woz.txt kon de hele tabel wegvagen — 5 oktober 2026

Mark heeft WOZ-waarden opgezocht en bij panden zonder WOZ een alternatief in het
bestand gezet. Daarna liep de handrun niet meer.

**De oorzaak zat in de manier van afvangen.** De parser ving fouten af per
BESTAND, niet per regel: bij een enkele onleesbare regel gaf hij een lege tabel
terug en waren alle 94 ingevoerde WOZ-waarden ineens onzichtbaar, zonder dat
iets dat meldde. Elke doorrekening viel dan terug op de schatting.

**Nu per regel.** Een onleesbare regel wordt overgeslagen, de rest wordt gewoon
gebruikt, en er komt een melding met de regelnummers. Een opmerking achter een
# aan het eind van een regel telt niet meer mee als gegevens, dus een notitie
naast een bedrag kan nu gewoon.

Getest op een bestand met zeven regels, waarvan drie onleesbaar: tekst in het
bedragveld, een losse zin zonder streepjes, en een bedrag van 1 euro. De drie
goede regels komen eruit, inclusief "342.000" met een punt erin.

**En het gezondheidsrapport controleert het bestand nu apart**, met de
regelnummers en een uitleg van het formaat. Zo is een fout in de invoer te zien
zonder de run te hoeven lezen.

---

## 35. Waarom huisnummer 19 geen WOZ heeft maar 19-A wel — 6 oktober 2026

**Mark:** het pand met nummer 19 staat gewoon in de BAG, maar het loket meldt
dat er geen WOZ is.

**Een WOZ-object is niet hetzelfde als een BAG-object, en dat verklaart het.**
Het wozwaardeloket publiceert alleen de waarde van woningen. Staat op 19 een
winkel of een kantoor, dan is er wel degelijk een beschikking, maar wordt die
niet getoond. En een WOZ-object kan meerdere BAG-eenheden omvatten: een pand met
een winkel beneden en een woning boven staat vaak als een object onder 19-A.

**Het gebruiksdoel werd al opgehaald maar nergens getoond.** Het dossier zegt nu
bij een verblijfsobject zonder woonfunctie dat het loket daar geen WOZ toont, en
dat een doorrekening als woning er niet bij past. Bij meerdere functies, dus een
gemengd pand, staat dat er ook bij; dat is juist interessant, want zo'n pand
leent zich vaak voor transformatie.

Getest op vier soorten: winkel, gemengd, woning en onbekend. Alleen de eerste
twee krijgen een regel.

**Wat dit praktisch betekent voor de invoer:** geeft 19 geen WOZ en 19-A wel,
kijk dan eerst wat voor object 19 is. Is het een winkel, dan is de WOZ van 19-A
de waarde van de woning erboven en hoort die bij een ander verblijfsobject dan
het pand in het aanbod. Is 19 gewoon een woning die onder 19-A geregistreerd
staat, dan is het dezelfde woning en klopt de invoer.

---

## 34a. Correctie: het waren wel metingen — 6 oktober 2026

Mark legde uit wat hij werkelijk deed: als huisnummer 19 bij het wozwaardeloket
niets opleverde en 19-A wel, heeft hij het adres in woz.txt aangepast en de
WOZ van 19-A ingevuld. Dat is geen overgenomen waarde van een ander pand maar de
meting van hetzelfde object onder het adres waaronder het geregistreerd staat.
Mijn zorg van gisteravond was dus misplaatst, en de tildemarkering is voor deze
regels niet nodig.

**Er zit wel een risico aan dat ik niet had gezien.** Staat het pand in ons
aanbod als "Havenweg 34" en in woz.txt als "Havenweg 34-A", dan vindt het model
die WOZ niet: het zoekt op adres. Het opzoekwerk is dan gedaan maar landt
nergens, en het pand blijft met een geschatte WOZ in de doorrekening staan.

Het rapport meldt nu welke ingevulde WOZ-regels bij geen enkel pand in het
aanbod horen, met de adressen erbij. Getest: een regel op 34-A terwijl het
aanbod 34 kent, wordt gemeld; de regels die wel kloppen niet.

Wat eraan te doen is, staat in de melding: zet het adres terug zoals het in het
aanbod staat, of voeg beide regels toe. Dat tweede is het veiligst, want dan
klopt het ook als het pand later onder de andere schrijfwijze binnenkomt.

---

## 34. Een overgenomen WOZ is geen meting — 5 oktober 2026

Mark vulde bij panden zonder eigen WOZ een alternatief in, bijvoorbeeld de
waarde van het buurpand. Begrijpelijk, en voor de doorrekening ook bruikbaar:
beter een onderbouwd getal dan niets.

**Maar voor de ijking is het funest.** Die vergelijkt onze schatting met de
werkelijkheid. Vul je daar een schatting in, dan vergelijkt het model zijn eigen
aanname met een andere aanname, en lijkt de uitkomst beter of slechter dan hij
is. In deze run ging de spreiding van 16,1% naar 19,4% bij vier panden erbij;
dat kan ruis zijn, maar het kan ook dit zijn.

**Een tilde voor het bedrag markeert het nu als overgenomen:**

    Havenweg 34 | ~825000 | 2026   # geen eigen WOZ, waarde van nr 36

Zo'n waarde telt gewoon mee in de doorrekening, maar niet in de ijking en niet
in de methodevergelijking. Ook "ca" en een plusminteken werken. Het rapport
telt hoeveel er zo in staan.

**Waarom dit principieel is:** het hele punt van die ijking is dat we weten hoe
goed de schatting is. Elke geschatte waarde die als meting binnenkomt, maakt dat
getal minder waard zonder dat iemand het ziet. Dat is dezelfde fout als een
vraagprijs voor een transactieprijs aanzien.

---

## 36. Hoeveel WOZ-waarden zijn er nog nodig? — 6 oktober 2026

**Mark:** moeten we er nog meer opzoeken?

**Systematisch niet meer, gericht wel.** De reeks laat zien waarom. Bij 39, 67
en 82 panden ging de spreiding van 23,9% naar 19,4% naar 15,0%; daarna, bij 94
en 98, terug naar 16,1% en 19,4%. Dat is geen verslechtering maar ruis in de
maat zelf: hij neemt het tiende en negentigste percentiel, en dat beweegt bij
honderd waarnemingen een paar punten op en neer.

Het stabiele getal is de mediane fout van de prijsindexmethode, en die ging van
11,0% naar 10,3% en beweegt sinds 82 panden nauwelijks. Tien procent mediane
fout betekent: goed genoeg om mee te sorteren, nooit goed genoeg om op te
bieden. Honderd panden erbij verandert dat niet.

**De werklijst kiest nu wel beter.** Hij keek naar prijsklasse en nieuwe
straten, maar niet naar buurten waar we weinig hebben. De kalibratie rekent per
buurt, dus een buurt met drie waarnemingen heeft meer baat bij vijf panden erbij
dan een buurt met veertig. Buurten met minder dan acht eigen WOZ-waarden staan
nu bovenaan, met de reden erbij: "Benedenstad heeft nog maar 0 eigen
WOZ-waarden".

Getest met vier kandidaten in twee buurten, waarvan een met drie waarden en een
met nul: de buurt met nul komt eerst.

**En de lijst vulde niet aan tot vijfentwintig, wat zelf het antwoord is.** Met
98 ingevulde en 8 openstaande regels staan er 106 adressen in woz.txt, tegen 96
koopobjecten in het aanbod. Vrijwel elk pand dat te koop staat heeft dus al een
WOZ of staat al op de lijst: er is niets meer te kiezen. Dat bevestigt gemeten
wat hierboven beredeneerd staat.

Het rapport zei dat niet, en dan lijkt de werklijst kapot. Nu staat er "geen
nieuwe kandidaten, elk pand in het aanbod heeft al een WOZ of staat al op de
lijst", of anders hoeveel panden er nog zonder zitten. Getest op allebei de
gevallen.

Nieuwe kandidaten komen er vanzelf zodra er panden te koop komen. Wat wel loont, blijft: de WOZ van elk pand dat Mark
serieus overweegt, want daar beslist het verschil tussen €360.000 en €518.000 de
hele case.

---

## 37. Twee vergunningen door elkaar in een achtergrondstuk — 6 oktober 2026

De brief van 6 oktober opent sterk: een aanvraag aan de Berg en Dalseweg 11-11A
om een splitsing van 2 naar 4 woningen te legaliseren, dus achteraf recht te
zetten wat zonder vergunning is gebeurd. Precies het soort bericht waarvoor dit
systeem is gebouwd.

**Maar er staat een zin in die twee stelsels door elkaar haalt**, en die komt uit
mijn eigen achtergrondstuk "Onrechtmatig gebruik en handhaving": "Woon je zonder
de vereiste huisvestingsvergunning, dan zijn huurder en verhuurder allebei in
overtreding."

Dat gaat over artikel 8 van de Huisvestingswet, een vergunning over wie er mag
wonen, die alleen geldt voor woonruimte die de gemeente daarvoor heeft
aangewezen. De rest van de alinea gaat over artikel 21: omzetten, onttrekken,
samenvoegen en woningvorming, een zaak van de eigenaar. Die twee hebben verder
niets met elkaar te maken, en of Nijmegen zo'n aanwijzing voor bewoning kent,
weet ik niet; dat staat in de verordening en moet per geval worden nagekeken.

Het achtergrondstuk zegt dat nu met zoveel woorden, en de opdracht aan de brief
verbiedt het mengen: schrijf nooit over een huisvestingsvergunning bij een
splitsings- of kamerverhuurzaak.

**Dit is dezelfde soort fout als die van gisteren met de WOZ-grens**, en het is
de derde keer deze week: twee regimes die allebei uit dezelfde wet komen en in
een alinea in elkaar overlopen. Daar zit blijkbaar een structurele zwakte, en
die zit in mijn achtergrondstukken en niet in de brief.

---

## 38. De rente stond weer bovenaan — 6 oktober 2026

Na de correctie opende de brief met vanbruggen.nl over een stijgende
hypotheekrente, weersproken door onze eigen meting. Daaronder pas de
legalisatieaanvraag aan de Berg en Dalseweg.

**Dat is de verkeerde volgorde, en wel om twee redenen.** Het rentebericht gaat
over een cijfer dat volgens onze eigen meting sinds 2 september stilstaat; het
weerspreken daarvan is nuttig maar het is geen gebeurtenis. De Berg en Dalseweg
is een pand in de eigen ring waar iets concreets gebeurt.

De opdracht kent al de regel dat een onveranderde rente geen nieuws is, maar die
sloeg niet aan omdat er een artikel over was. Nu staat er een expliciete
volgorde: eerst de stad, dan de markt. Een bekendmaking over een pand in de ring
gaat voor een landelijk marktbericht, en een gemeten verandering gaat voor een
bericht dat een verandering beweert. Een rentebericht mag alleen openen als onze
eigen meting ook werkelijk beweegt.

---

## 39. De volgorde klopt nu, en een benaderd jaartal werd hard — 6 oktober 2026

De brief van 6 oktober opent met twee splitsingsaanvragen in de ring, zet de
WOZ-grens expliciet naast het splitsingsregime in plaats van erdoorheen, en
weerspreekt het rentebericht pas verderop. Alle drie de aanpassingen van
vanochtend doen wat ze moeten.

**Een detail klopt nog niet.** De brief schrijft "op nummer 210 en 275 is in
2018 woonruimte onttrokken", terwijl in de gegevens "jaar bij benadering" staat.
Die oude kamerverhuurvergunningen komen uit de gemeentelijke lijst waarin het
jaartal is afgeleid en niet gepubliceerd. De opdracht zegt nu dat zo'n jaartal
"omstreeks 2018" moet worden, nooit "in 2018".

**Wat verder opvalt aan deze brief**, en het is het noteren waard omdat het laat
zien waar het systeem nu staat: hij legt bij de Krayenhofflaan 47 het verband
tussen WOZ, puntenaantal, opkoopbescherming en labelsprong in een alinea, met
alle vier de getallen uit onze eigen gegevens. Een labelsprong naar B geeft 14
punten en brengt het pand van 179 naar 193, dus over de grens van 187 heen. Dat
is precies de redenering waarvoor dit is gebouwd, en die stond er een week
geleden nog niet in.

---

## 40. Hoe een legalisatietraject werkt — 6 oktober 2026

**Correctie vooraf:** ik schreef dat de observatie over eerst splitsen en dan
toestemming vragen van Mark kwam. Dat klopt niet; die stond in de brief en
nergens in zijn berichten. Ik heb hem ten onrechte aan hem toegeschreven.

**Zijn werkelijke punt was beter:** we weten niet hoe zo'n legalisatietraject
verloopt, en dat is precies wat je moet weten als er een pand met zo'n aanvraag
te koop komt. Daar was geen achtergrondstuk voor; nu wel, het dertigste.

Wat erin staat, opgezocht en niet uit het hoofd:

- de beginselplicht tot handhaving, sinds 1 januari 2024 vastgelegd in artikel
  18.1 Omgevingswet en daarvoor al vaste rechtspraak: bij een overtreding moet
  het bestuursorgaan in de regel optreden met een dwangsom of bestuursdwang;
- twee uitzonderingen: concreet zicht op legalisatie, en onevenredigheid. Van
  concreet zicht is sprake bij een ontvankelijke aanvraag die de hele
  overtreding wegneemt en de bereidheid die te verlenen; bij de uitgebreide
  procedure moet er een ontwerpbesluit ter inzage liggen;
- dat verklaart waarom legalisatieaanvragen zo vaak voorkomen: zolang die loopt
  en kansrijk lijkt, kan de gemeente van handhaven afzien;
- maar het is geen vrijbrief. De Afdeling bestuursrechtspraak heeft bevestigd
  dat een bestuursorgaan ook bij concreet zicht op legalisatie toch mag
  handhaven, en het zicht wordt beoordeeld op het moment van de beslissing op
  bezwaar;
- en de beginselplicht geldt alleen voor herstelsancties. Voor een bestuurlijke
  boete geldt hij niet, dus een lopende aanvraag beschermt niet tegen een boete
  over de periode zonder vergunning.

**Waar het voor een koper om draait, staat als laatste in het stuk:** een pand
met een lopende legalisatieaanvraag is geen vergund pand. Wordt de vergunning
geweigerd, dan ligt de herstelplicht bij de eigenaar van dat moment, en dat kan
de koper zijn.

---

## 41. Een huisnummeraanvraag is een splitsingssignaal — 6 oktober 2026

Mark legde een antwoord van een andere assistent voor over de Berg en Dalseweg
11-11A. Een eigen zoekopdracht levert daar niets over op, dus de bewering dat de
appartementen in 2017 voor het laatst zijn verkocht is niet te bevestigen; dat
soort Kadastergegevens is ook niet vrij op te vragen.

**Maar een onderdeel is wel opvallend en controleerbaar:** in juni 2026 zou er
een aanvraag zijn ingediend voor twee extra huisnummers op dat adres. Dat is
precies wat woningvorming administratief is. Nieuwe zelfstandige woningen
krijgen een eigen adres, en pas daarna telt de BAG ze mee. Twee extra
huisnummers bij een pand van twee woningen is dus een splitsing naar vier, en
dat is exact de aanvraag die vandaag als legalisatie binnenkwam.

**Die signaalsoort stond niet in onze kernwoorden.** Een bekendmaking over
huisnummers of een nummeraanduiding viel bij de overige berichten, terwijl het
de stap is die vooraf gaat aan de splitsing die we later in de BAG zien
verschijnen. Nu staan "huisnummer", "huisnummers" en "nummeraanduiding" in de
kernlijst. Getest: de twee huisnummerregels komen als kernsignaal binnen, een
kapvergunning niet.

**Daarmee zit de keten compleet:** aanvraag huisnummers, dan de
vergunningaanvraag, dan het besluit, en ten slotte de BAG die de nieuwe woningen
telt. Elk van die vier stappen is nu een gebeurtenis in de pandgeschiedenis.

---

## 42. Een adres met een streepje werd niet gelezen — 6 oktober 2026

**Mark:** worden die huisnummeraanvragen ook per pand vastgelegd? Dat hoort in
het pandverhaal.

**Eens, en het ging mis op een plek die niemand zou vermoeden.** De titel "aan
Berg en Dalseweg 11-11A, 6522BB Nijmegen" leverde helemaal geen adres op. Beide
parsers, die in bekendmakingen_nijmegen.py en die in bekendmakingen_archief.py,
konden niet omgaan met een bereik van twee huisnummers. Zo'n bekendmaking kwam
daardoor in geen enkele pandgeschiedenis terecht.

Juist bij woningvorming is dat de vorm die voorkomt, want daar zijn twee
adressen in het spel. De aanvraag voor extra huisnummers, de legalisatie en het
latere besluit dragen allemaal die schrijfwijze, en ze vielen alle drie buiten
het pandverhaal.

Beide parsers nemen nu het eerste nummer uit het bereik. Getest op zes vormen:
11-11A, 110-112, een schuine streep, "51 en 53", een gewoon nummer en een
nummer met een letter. Alle zes geven nu het juiste pand, en de twee Berg en
Dalseweg-regels landen op dezelfde sleutel.

**Daarmee is de keten van signalen ook werkelijk aan elkaar geknoopt.** De
aanvraag voor huisnummers, de vergunningaanvraag, het besluit en de BAG die de
nieuwe woningen telt, staan vanaf nu alle vier in de geschiedenis van hetzelfde
pand. Dat was de bedoeling van het splitsingssignaal van gisteren, en zonder
deze reparatie had het bij dit pand niet gewerkt.

---

## 43. Een label hoort bij een adres, niet bij een pand — 6 oktober 2026

**Mark:** het gaat om twee huisnummers, maar er staat maar een energielabel.
Betekent dat dat er maar een is, of dat beide woningen hetzelfde hebben?

**Het eerste: we kennen er maar een.** Een energielabel wordt per
verblijfsobject geregistreerd, dus per adres. Is er voor 11A niets
geregistreerd, dan weten we daar niets van, en bij een pas gesplitst pand is dat
juist waarschijnlijk: nieuwe eenheden hebben vaak nog geen label.

De brief schreef "het pand heeft energielabel F", en dat suggereert meer dan we
weten. Twee aanpassingen.

Het dossier zet er nu bij voor hoeveel woningen in het pand we een label kennen:
"F; bekend voor 1 van de 2 woningen in dit pand, van de overige kennen we het
label niet". Bij een pand met een woning blijft het de gewone regel.

En de opdracht zegt dat een label bij een adres hoort en niet bij een pand, en
dat de brief "voor dit adres staat label F geregistreerd" moet schrijven in
plaats van "het pand heeft label F".

**Aanvulling, zelfde dag.** De gegevens staan al per huisnummer: in
pandgeschiedenis.json staat per pand een lijst adres-naar-label, en die wordt
per verblijfsobject opgehaald. Alleen de weergave was samengevat, en het dossier
toonde uitsluitend het label van het aangeboden adres.

Nu staat er een regel "labels per adres" bij een pand met meerdere bekende
labels, bijvoorbeeld "Berg en Dalseweg 11: F, Berg en Dalseweg 11A: A". Boven de
twaalf adressen wordt afgekapt met een telling erachter.

Dat is bij een splitsingscase het interessantste wat er staat: verschillende
labels binnen een pand betekent dat een deel is verbouwd en een deel niet. De
opdracht zegt nu dat de brief dat verschil concreet moet noemen, met de adressen
erbij.

**Waarom dit meer is dan een slag om de arm:** bij de Berg en Dalseweg gaat het
om vier woningen na splitsing. Als er straks een puntentelling op wordt
losgelaten, telt het label van elk van die vier apart. Een label F van het
oorspronkelijke adres zegt dan niets over wat de nieuwe eenheden krijgen, en die
zijn na een verbouwing vaak een stuk beter.

---

## 44. De labelnuance gold nog niet voor bekendmakingen — 6 oktober 2026

De brief schreef vanochtend nog "het pand is 116 vierkante meter groot en heeft
energielabel F", terwijl het over de Berg en Dalseweg 11-11A gaat: twee adressen,
en straks vier woningen.

**De reparatie van eerder vandaag zat in het dossier, niet bij de
bekendmakingen.** Die hebben hun eigen feitenregel met oppervlakte, bouwjaar en
label, en daar gold de nuance niet.

Nu krijgt het label daar "(alleen van dit adres bekend)" achter zich zodra de
bekendmaking over meerdere woningen gaat: een adres met een streepje erin, een
titel over verbouwen naar twee of meer woningen, of het woord appartementen.
Getest op drie titels: de huisnummeraanvraag en de verbouwing naar drie
appartementen krijgen de toevoeging, een dakkapel niet.

**Dit is dezelfde fout op een tweede plek**, en dat patroon komt vaker voor in
dit systeem: dezelfde gegevens worden op twee manieren naar de brief gebracht,
en een verbetering aan de ene kant laat de andere ongemoeid. De adresparser van
vanmiddag was precies hetzelfde geval: twee parsers, allebei met dezelfde
beperking.

---

## 45. "Weer te koop" zonder te zeggen wanneer — 6 oktober 2026

**Mark:** er staat dat de Krayenhofflaan 321 weer te koop staat, maar niet
wanneer het pand eerder werd aangeboden. Dat is jammer, want daar zit het
verhaal.

**Terecht, en die gebeurtenis staat gewoon in de geschiedenis.** Het dossier
toonde alleen sinds wanneer het pand nu te koop staat, niet de vorige keer.

Er staat nu een regel "eerder te koop" bij met de datum en, als we die kennen,
de vorige vraagprijs met het verschil erbij: "eerder aangeboden op 2025-11-12
voor €520.000, nu 7% lager". Getest op vier gevallen: lager, hoger, dezelfde
prijs en een gebeurtenis zonder bedrag.

En de opdracht zegt nu dat "weer te koop" nooit zonder dat wanneer mag. Juist
het verschil is het nieuws: een pand dat na drie maanden terugkomt voor zeven
procent minder zegt iets anders dan een pand dat na vier jaar opnieuw op de
markt komt. Ontbreekt die regel, dan schrijft de brief alleen dat het nu te koop
staat.

---

## 46. Wat er vandaag werkte, en een afgeronde periode — 6 oktober 2026

**Drie aanpassingen van vandaag zijn terug te zien in de brief:**

"Energielabel F, uit 2017 en alleen van dit adres bekend" bij een pand met twee
adressen. Bij de Krayenhofflaan 28 gebruikt de brief de labels per adres: "nu
gesplitst in 28, 28A en 28B, alle drie met label C". En hij schrijft niet meer
dat nummer 321 weer te koop staat, alleen dat het te koop staat; de eerdere
plaatsing zit niet in onze geschiedenis, dus de regel die zegt "ontbreekt die
datum, claim het dan niet" doet precies zijn werk.

**Een kleinigheid klopt niet:** "Stadscentrum +4,2% in vier weken", terwijl de
meting loopt sinds 13 september, dus drieëntwintig dagen. Een periode die langer
lijkt dan hij is, maakt een beweging kleiner dan hij is. De opdracht zegt nu dat
de brief de datum zelf of het werkelijke aantal dagen noemt en niet naar boven
afrondt.

---

## 47. Een verkooptijd die een feit is in plaats van een schatting — 6 oktober 2026

Mark plakte de verkochte woningen van funda. Zeven ervan stonden bij ons al als
te koop; acht waren nieuw. En de "Sinds 3 weken" op die pagina blijkt niet de
verkoopdatum: Hofdijkstraat 17 zagen wij op 11 september te koop en staat op
"3 weken", dus 15 september. Die labels lopen gelijk met de advertentie, niet
met de verkoop.

**Maar twee eigen waarnemingen geven wel een harde bovengrens.** Zagen we een
pand op 11 september te koop en is het op 6 oktober verkocht, dan stond het
hoogstens 25 dagen te koop. Dat is geen schatting: de werkelijke tijd is korter
of gelijk, nooit langer. Precies de maat die we de hele week misten en die het
model tot nu toe met een modelantwoord moest vullen.

verkooptijd.json bevat nu per pand de eerste keer dat we het te koop zagen, de
dag dat het verkocht bleek, en het aantal dagen ertussen, plus de mediaan.
Getest op vier panden: twee met beide waarnemingen, een alleen te koop en een
alleen verkocht; de laatste twee vallen terecht af.

**En de mailparser leest de verkochtmeldingen nu.** Het filter op verkocht staat
sinds kort aan bij Mark, en zonder deze aanpassing kwamen die mails als "te
koop" binnen, waardoor een verkocht pand eeuwig in het aanbod bleef staan. Nu
levert een mail met "verkocht" de status verkocht, en een mail met "onder
voorbehoud" of "onder bod" de status onder voorbehoud.

**De opdracht aan de brief eist de juiste formulering:** "hoogstens 25 dagen" of
"binnen 25 dagen", nooit "25 dagen te koop". Dat laatste zou een precisie
suggereren die we niet hebben.

---

## 48. Huislijn wordt nu uitgelezen — 7 oktober 2026

Huislijn was een van de veertien kandidaatplatforms die we wel telden maar niet
uitlazen. Mark stuurde het formaat: een straatnaam met "Nijmegen" erachter, en
daaronder "Huur: € 822". Verder niets.

De parser leest die paren en slaat de reclameblokken over. Getest op de echte
mail met acht woningen en drie advertentieblokken ertussen: alle acht komen
eruit, de reclame niet, en de twee St. Agnetenweg blijven apart omdat de huren
verschillen.

**Met een beperking die erbij hoort en die het rapport nu noemt.** Huislijn geeft
geen huisnummer en geen oppervlakte. Daarmee kan er geen prijs per vierkante
meter uit, en dat is wat de doorrekening gebruikt. Zulke waarnemingen tellen mee
voor de dekking van wat er in de stad te huur staat en voor het signaal
"opnieuw aangeboden", maar niet voor de gemeten huur per m2. Dat gaat
automatisch goed, want een regel zonder oppervlakte valt buiten die berekening.

Het rapport meldt nu hoeveel huurwaarnemingen geen oppervlakte hebben, zodat die
beperking zichtbaar is in plaats van verstopt.

**Waarom dit de huurdekking van 42% helpt.** Die steekproef toetst of wij de
adressen kennen die elders te huur staan. Een extra bron verhoogt die dekking
ook als de waarneming zelf niet in de mediaan meetelt: je weet dan wél dat er
aanbod is, en dat was precies het punt bij die melding.

---

## 49. Dubbelingen tussen platforms — 7 oktober 2026

**Mark:** er kunnen dubbelingen zitten ten opzichte van de andere aanbieders.

**Terecht, en het raakt twee dingen.** Dezelfde woning op Pararius en Huislijn
telt twee keer mee in de mediane huur, en twee keer in de aanbodreeks. Dan lijkt
er meer aanbod dan er is, en weegt een woning dubbel in de huur per m2.

Zonder huisnummer is een zekere match onmogelijk. Een waarschijnlijke wel:
dezelfde straat, een huur die minder dan twee procent verschilt, en waarnemingen
binnen drie weken van elkaar. Dat is vrijwel altijd een advertentie die op twee
sites staat.

**Welke waarneming blijft staan, is een bewuste keuze:** die met een
oppervlakte, want alleen daarmee komt er een prijs per vierkante meter uit. Is
die bij geen van de twee bekend, dan de oudste, zodat de eerste waarneming de
datum bepaalt.

Getest op zes waarnemingen uit de echte mails. Breehofstraat van Huislijn is
samengevoegd met die van Pararius, en de Pararius-regel met 68 m2 blijft staan.
De twee St. Agnetenweg blijven apart omdat de huren €84 verschillen. En
Maasstraat blijft apart omdat die twee waarnemingen twee maanden uiteenliggen:
dat zijn twee verhuringen, niet een dubbeling.

Het rapport meldt hoeveel er zijn samengevoegd, zodat het aantal huurwaarnemingen
niet stil lijkt te staan terwijl er wel mails binnenkomen.

---

## 50. Onder bod is het scherpste signaal — 7 oktober 2026

Mark plakte vijftien panden die onder bod of verkocht onder voorbehoud staan.
Tien ervan stonden bij ons als te koop: van Goorstraat 91, Mr. Franckenstraat 6,
Staringstraat 21, Krayenhofflaan 104, Gulden Wagengas 1, Burg. Hustinxstraat 208,
Veemarkt 213, Pontanusstraat 19, Scholenhof 8 en Palembangstraat 44. Vijf waren
nieuw, waaronder een nieuwbouwproject.

**Die status viel helemaal buiten de geschiedenis.** Er was een tak voor te koop,
voor te huur en voor verkocht, maar niet voor onder bod. Nu wel, als eigen soort
gebeurtenis.

**En het is een beter signaal dan de verkoop zelf.** Onder bod is het moment dat
een koper zich vastlegt; de overdracht bij de notaris volgt maanden later. Een
verkoop die nu wordt gemeld, is dus vaak weken oud nieuws, terwijl onder bod
vers is.

De bovengrens op de verkooptijd rekent nu ook met onder bod, en meldt die apart.
Getest op drie panden: Pontanusstraat 19 hoogstens 21 dagen tot onder bod,
Staringstraat 21 hoogstens 17 dagen, en Hofdijkstraat 17 hoogstens 25 dagen tot
verkocht.

De opdracht aan de brief zegt erbij dat onder bod nog geen verkoop is en dat een
bod kan afketsen.

**Wat opvalt aan deze vijftien, en het is te vroeg om er iets van te vinden:**
twaalf staan er twee tot drie weken. Als dat zo blijft, loopt de markt in de
ring snel, en dan zegt de huidige "mediaan 15 dagen sinds laatst bevestigd" in
het aanbodbestand iets heel anders dan het lijkt. Over een maand is dat te
toetsen met eigen cijfers.

---

## 50a. "In onderhandeling" dekt drie stadia — 7 oktober 2026

**Mark:** funda schrijft zelf dat "in onderhandeling" onder bod, onder optie en
verkocht onder voorbehoud omvat.

**Dat maakt mijn gebeurtenis van een uur eerder te grof.** Die gooide alles op
een hoop onder de naam "onder bod", en onder optie kende hij helemaal niet. Dat
zijn geen synoniemen: onder bod is onderhandelen en kan makkelijk afketsen,
onder optie betekent dat het pand voor iemand wordt vastgehouden, en verkocht
onder voorbehoud is vrijwel een deal met alleen de financiering of een
bouwkundige keuring nog open.

De gebeurtenis heet nu "in onderhandeling", de overkoepelende term, met het
werkelijke stadium in de tekst. Zo kan de meting ze samen nemen voor de
doorlooptijd, terwijl het verschil blijft staan waar het telt. De mailparser
herkent alle vier de schrijfwijzen en bewaart welke er in de mail stond.

De opdracht aan de brief zegt nu dat hij het stadium overneemt zoals het er
staat en niet vervangt door een algemener woord, en dat "in onderhandeling"
nooit als verkocht mag worden geschreven.

**Controle die ik erbij heb gedaan:** de tak voor echt verkocht toetst op
gelijkheid en niet op "begint met", dus "verkocht onder voorbehoud" wordt niet
als verkoop geteld. Dat was de fout die hier makkelijk had kunnen insluipen.

---

## 51. Nieuwbouw hoort niet in de mediaan — 7 oktober 2026

In de lijst met panden in onderhandeling staan zeven stadswoningen van Amber
fase 2, 153 m2 voor ongeveer €733.000 vrij op naam. Die zouden de mediaan per m2
en de groottepremie verschuiven zonder dat er iets in de bestaande voorraad
gebeurt: vrij op naam bevat de overdrachtskosten en de btw, en een bouwnummer is
geen bestaand pand.

Zulke regels krijgen nu de status "project". Die naam is met opzet gekozen:
negen filters in andere modules matchen op het voorvoegsel "nieuw", dus een
status "nieuwbouw" zou alsnog als gewoon aanbod worden geteld. Getest: "project"
valt buiten elk van die filters, "nieuw" en "te koop" erbinnen.

Het rapport meldt hoeveel nieuwbouwregels apart worden gehouden, en de opdracht
aan de brief zegt dat zo'n regel niet voor een prijsvergelijking of een mediaan
mag worden gebruikt. Als het nieuws is, bijvoorbeeld een heel blok dat tegelijk
onder optie gaat, mag dat als eigen bericht met vermelding dat het vrij op naam
is.

**Een tweede vondst uit dezelfde lijst, en die lost een oud raadsel op.** Er
staat "Jan de Wittstraat 6-8 studio 9, 41 m2, €246.000". Jan de Wittstraat 6 is
dus een studiocomplex. Dat verklaart de WOZ-uitschieter van +1132% op dat adres:
de ingevoerde waarde is vrijwel zeker die van het hele pand en niet van de
studio van 22 m2 die in ons aanbod staat.

En het verklaart ook de St. Annastraat 30, die als onder bod staat met 23 m2 voor
€165.000 terwijl wij er ook een van 31 m2 kennen. Funda hangt daar werkelijk
meerdere eenheden onder hetzelfde adres; dat is geen fout in onze invoer.

---

## 52. Wat de Burg. Hustinxstraat 56 oplevert voor de brief — 7 oktober 2026

Mark leverde de volledige brochure van een pand dat in onze tabel stond met
"ondergrens 186 punten, onder de 187" en daardoor met een huur van €1.228. Met
de echte kenmerken erbij komt het pand op 191 punten met het balkon van 14 m2,
196 met de berging van 7 m2, en rond de 200 met het ligbad en het tweede toilet.
Dus ruim vrije sector, en de markthuur is €1.836 in plaats van €1.228.

**Dat is geen detail maar een rekenfout van zeshonderd euro per maand**, en
daarmee ruim honderdduizend euro in de richtprijs. De oorzaak: onze telling kent
alleen oppervlakte, WOZ en label.

**Drie dingen aangepast.**

Een ondergrens binnen zeventien punten van de 187 levert nu geen conclusie meer
op. In plaats van "gereguleerd" staat er dat het regime niet is bepaald, met de
reden erbij en een verbod om er een wettelijk maximum op te plakken. Getest:
186, 179 en 172 punten geven die melding, 161 en 98 blijven gereguleerd, 192 en
210 blijven vrije sector.

De opdracht aan de brief zegt hetzelfde in woorden, en eist dat een bekende
VvE-bijdrage voorgaat op het percentage uit de aannames. Bij dit pand is €311
per maand bijna het dubbele van de aanname, en dat zakt het nettorendement van
3,68% naar 3,37%.

**En er is een kental uit gekomen dat op een bezichtiging bruikbaar is:** bij 70%
financiering tegen 5,50% is de koopsom waarbij de huur de rente dekt ongeveer
207 maal de maandhuur. Bij €1.750 huur is dat €363.000. Dat getal rust op vier
doorrekeningen uit de brief van vandaag en is dus gemeten binnen het eigen
model, niet geschat.

---

## 53. Het uitgelichte pand rustte op drie waarnemingen — 7 oktober 2026

De brief van 7 oktober lichtte de Stieltjesstraat 10 uit met een richtprijs van
€799.285 tegen een vraagprijs van €539.000, dus 48% ruimte. De brief zette er
zelf bij dat die huur op maar drie kleine panden is gemeten en dat je daar niet
blind op moet varen; dat is eerlijk, maar het pand stond er wel als beste.

**Dat is dezelfde fout als bij de groottepremie:** een huur per m2 die op kleine
eenheden is gemeten, toegepast op een pand van 158 m2.

De keuze van het uitgelichte pand slaat nu panden over waarvan de huur op minder
dan vijf waarnemingen rust of op een aanname. Zulke panden blijven gewoon in de
tabel staan, met de bron erbij, maar ze worden niet het pand dat de brief
uitlicht.

**Een valkuil in de eerste versie:** die las het eerste cijfer uit de
brontekst, en bij "wettelijk maximum bij 179 punten" werd dat 179 waarnemingen.
Nu wordt alleen het getal uit "gemeten, N panden" gelezen. Getest op vijf
bronteksten.

**Wat Mark hier zelf aan had:** de bronlinks naar de officiële bekendmakingen
staan nu in de brief, dus elke aanvraag is in een klik na te lezen.

---

## 54. Twee aanvragen naast elkaar, en een regel die ik fout had — 7 oktober 2026

Mark leverde de volledige aanvragen van beide splitsingszaken. Daaruit komt meer
dan uit een maand bekendmakingen.

**Berg en Dalseweg 11: twee HUURwoningen naar vier.** Ingediend 29 september
door DD21 B.V., Bijleveldsingel 38, KvK 84657650. De woningen 11 en 11A zijn al
gesplitst in 11 plus 11B en 11A plus 11C; er worden twee nieuwe huisnummers
aangevraagd. De tekening geeft 51 en 43 m2 boven en 57 en 62 m2 op de tweede.
Bruto vloeroppervlakte verandert niet.

Doorgerekend: alle vier de eenheden komen op 95 tot 122 punten, dus diep
gereguleerd, met samen ongeveer €2.805 wettelijk maximum. De twee bestaande
woningen van 94 en 119 m2 zitten op 154 en 183 punten, samen €2.216. De
splitsing levert dus ongeveer €590 per maand extra, niet de sprong die
uitponden geeft. Op de vrije markt zouden die vier €3.834 doen bij onze gemeten
€18 per m2; het puntenstelsel pakt daar ruim duizend euro per maand af.

**Staringstraat 2: één KOOPwoning naar drie.** Ingediend 22 september door
Bouwplan, Daalseweg 229, KvK 09127400, met Ontwerp & Tekenburo uit Siebengewald.
Drie appartementen van 69,4, 55,9 en 45,3 m2, interne verbouwing, geen
vooroverleg en geen participatie. Dit is dus een uitpondcase en geen
verhuurcase, en daar geldt de groottepremie wel.

**En de regel die ik fout had.** Ik schreef dat het ontbreken van parkeren op
eigen terrein een reële weigeringsgrond is. De parkeerberekening van de
Staringstraat laat zien dat dat in de ring vaak niet zo is: de Beleidsregels
Parkeren 2025 kennen onder bijzonder geval VII een vrijstelling voor splitsing
in het gereguleerde gebied, omdat de nieuwe huisnummers geen parkeervergunning
krijgen en de parkeerdruk dus niet stijgt. Daarmee is er geen parkeereis.

Dat staat nu als achtergrondstuk, het eenendertigste, met de keerzijde erbij:
een huurder op zo'n nieuw huisnummer kan geen parkeervergunning krijgen, en
buiten het gereguleerde gebied geldt de eis juist wel.

---

## 55. De rekenstukken van een splitsingsaanvraag zelf maken — 7 oktober 2026

**Mark:** welke documenten gaan er bij zo'n aanvraag mee, en kunnen we die
berekeningen zelf opstellen zodat ze klaarliggen bij aankoop?

**Uit de twee aanvragen blijkt welke bijlagen er zijn.** Plattegronden,
doorsneden en detailtekeningen; een constructieve berekening; een toelichting op
de constructie; mechanische ventilatie; thermische isolatie; bruikbaarheid en
toegankelijkheid; bouwwerkinstallaties; kwaliteitsverklaringen; een
parkeerberekening; bodemonderzoek; en situatietekeningen van de bestaande en de
nieuwe toestand. Bij de Staringstraat zit de constructieberekening er nog niet
bij: die wordt later nagestuurd.

**Drie daarvan zijn rekenwerk met vaste formules**, en die zijn uit de aanvraag
van de Staringstraat te herleiden:
- de 55%-toets uit het Besluit bouwwerken leefomgeving: minstens 55% van de
  gebruiksoppervlakte moet verblijfsgebied zijn;
- de ventilatie-eis, 0,9 dm3/s per m2 verblijfsruimte en vaste waarden van 7
  voor een toilet, 14 voor sanitair en berging en 21 voor een keuken;
- de spuivoorziening, 0,06 m2 per m2 verblijfsruimte;
- en de parkeerberekening met de norm van 0,70 per woning en de vrijstelling
  voor splitsing in het gereguleerde gebied.

**splitsingstoets.py doet dat, en is getest tegen de echte aanvraag.** Met de
kamermaten van de Staringstraat erin komt er exact hetzelfde uit: 56,6 en 48,2
m2 gebruiksoppervlakte, eisen van 31,1 en 26,5, verschillen van +19,9 en +8,6,
en ventilatiewaarden 18,81, 14,76 en 12,78. Dat is geen benadering maar
hetzelfde getal.

Ook getest op de twee gevallen waar het misgaat: een appartement met te veel
verkeersruimte haalt de 55%-eis niet en wordt gemeld, en een pand buiten het
gereguleerde gebied krijgt de parkeereis wel met het tekort als kritieke toets.

**Aanvulling na navraag van Mark over het huidige Bbl.** Twee dingen waren te
grof.

Het minimum van 7 dm3/s per ruimte werd niet getoetst. Een kamer van 5 m2 kwam
daardoor op 4,5 uit in plaats van op 7. Nu staat er "7,0 (minimum)" bij zo'n
ruimte.

En het onderscheid tussen verblijfsgebied en verblijfsruimte ontbrak. Voor
nieuwbouw vraagt een verblijfsgebied 0,9 dm3/s per m2 en een verblijfsruimte
0,7, allebei met dat minimum van 7. Het invoerbestand kiest nu zelf; markeer je
de ruimten als verblijfsgebied, dan komen er exact de getallen van de echte
aanvraag uit: 12,33, 18,81 en 14,76. Die aanvraag rekende dus met de zwaarste
waarde voor elke ruimte.

Ook de spuivoorziening is nu gesplitst: 6 dm3/s per m2 voor een verblijfsgebied
en 3 voor een losse verblijfsruimte, omgerekend naar 0,06 en 0,03 m2
openingsoppervlak per m2.

**En het Bbl drukt dit voor een woonfunctie niet uit in luchtwisselingen per
uur** maar in dm3/s per m2 vloeroppervlakte. De tabel zet er nu m3/h naast,
omgerekend met 1 dm3/s is 3,6 m3/h, zodat het vergelijkbaar is met wat een
installateur noemt.

**Bij verbouw mag worden teruggevallen op het rechtens verkregen niveau:** de
legale kwaliteit mag niet verslechteren, met de eisen voor bestaande bouw als
ondergrens, en dat is 0,7 dm3/s per m2 met hetzelfde minimum. Het rapport zegt
er daarom bij dat het op nieuwbouwniveau rekent en dus de zwaarste variant is.

**Wat we hiermee niet kunnen:** de constructieberekening, de bouwtekeningen en
de situatietekeningen. Daar zijn een constructeur en een tekenbureau voor nodig.
Maar de toets die bepaalt of een indeling überhaupt kan, hoeft niet meer te
wachten tot na de aankoop: met de maten van een plattegrond is in vijf minuten
te zien of drie eenheden passen.

---

## 56. De aanvraagstukken bij de investeringscase — 7 oktober 2026

**Mark:** zodra de brief voorstelt een woning in twee appartementen te
splitsen, hoort daar gelijk bij wat er aan documenten nodig is en wat we
automatisch kunnen maken.

**Eens, en het valt in twee delen uiteen.** Wat nu al kan, en wat kamermaten
vraagt.

Nu al: de parkeerberekening, want die heeft alleen het aantal woningen voor en
na nodig en of het pand in het gereguleerde gebied ligt. En de lijst met
bijlagen, die uit twee echte aanvragen bekend is, met erbij wie wat levert: het
tekenbureau de tekeningen, de constructeur de berekening (die mag worden
nagestuurd), de installateur de bouwwerkinstallaties, en wij de ruimtetabel, de
ventilatie, de spui en het parkeren.

Pas na een bezichtiging: de ruimtetabel, de ventilatieberekening en de
spuivoorziening. Die vragen de maten per ruimte, en die staan in geen enkele
registratie. Dat is een half uur werk met een rolmaat.

**Het dossier zet dat blok er nu bij zodra splitsen als alternatief in beeld
komt**, met het aantal eenheden uit de doorrekening zelf. Getest: "splitsen in
2" en "splitsen in 3" leveren het blok op, een kamerverhuurregel niet.

**Over meer aanvragen toevoegen: dat is waardevol en om een specifieke reden.**
Elke aanvraag legt een formule of een drempel bloot die we niet kenden. Uit de
Staringstraat kwamen de ventilatiewaarden, de 55%-toets en de parkeervrijstelling
die mijn eerdere oordeel onderuit haalde. Uit de Berg en Dalseweg kwam dat het
om huurwoningen gaat en dat er twee nieuwe huisnummers bij horen. Twee
aanvragen leverden meer op dan een maand bekendmakingen.

Wat ik bij een volgende vooral zou willen zien: een aanvraag die is GEWEIGERD,
of een met een conceptverzoek vooraf. Dan weten we waar de gemeente op afwijst,
en dat is precies wat er nu ontbreekt.

---

## 57. Het volledige verleende dossier van de Biezenstraat 110 — 7 oktober 2026

Hetzelfde pand waarmee deze hele draad begon, nu met het besluit erbij. Dit is
de rijkste bron tot nu toe, en hij corrigeert een aanname die we weken
meedroegen.

**De bopa was niet nodig voor de splitsing.** Die past binnen het
omgevingsplan. De strijdigheid zat in de aanbouw: vier meter achter de
achtergevellijn waar het bestemmingsplan Nijmegen Oud West 2015 maximaal drie
meter toestaat, zonder afwijkingsregels. De brief schreef steeds dat splitsen in
Nijmegen via een bopa loopt; dat hoeft dus niet. De opdracht zegt dat nu ook.

**Getallen die nergens anders staan:**
- aanvraag 3 december 2025, vergunning 29 september 2026, dus bijna tien
  maanden;
- leges €2.218,21;
- eenentwintig bijlagen;
- aanbouw 30,4 m2, vier meter diep en acht meter breed.

**De parkeerregel is nu bevestigd uit een besluit en niet uit een berekening van
een aanvrager:** de locatie ligt in gereguleerd gebied, dus geen parkeereis bij
woningsplitsing, maar een parkeervergunning voor het nieuwe huisnummer wordt
niet verleend.

**Wat er als voorschrift bij kwam, is het deel dat geld en tijd kost.** De
adviescommissie Omgevingskwaliteit adviseerde positief onder voorwaarden, waarna
er aangepaste tekeningen met groenmaatregelen zijn ingediend. Voor de huismus
moeten vier groenmaatregelen worden aangebracht en binnen een jaar geplant: 
beplanting naast de gevel, een natuurlijke haag, een kruidenrijke zoom met
bossage en een cluster bomen. De erfafscheiding aan de straatzijde moet een
groene haag van maximaal een meter zijn. En het gebied is verdacht voor
ontplofbare oorlogsresten, dus daar moet nog onderzoek naar worden gedaan.

**Twee onderzoeken bleken niet nodig maar zijn wel meegestuurd:**
bodemonderzoek, omdat de aanbouw onder 50 m2 blijft en niet tot een andere
bodemgevoelige functie leidt, en archeologisch onderzoek om dezelfde drempel.
Dat is dus geld dat niet hoefde.

Dit alles staat nu als achtergrondstuk, het tweeëndertigste, en de extra
bijlagen bij een bopa staan in splitsingstoets.py met erbij wie ze levert.

---

## 58. Het negatieve welstandsadvies dat ik zocht — 7 oktober 2026

Bij de St. Annastraat 456 staat precies wat er bij de andere twee ontbrak: een
afwijzing, en wat die kostte.

**Het verloop.** Aanvraag 14 oktober 2025 voor een extra verdieping. De
adviescommissie Omgevingskwaliteit adviseerde op 11 juni 2026 NEGATIEF. Het plan
is daarna op drie punten aangepast: de aansluiting van het voordakvlak met een
grotere hoek, de kap geheel afgedekt met leien, en de kozijnen in de
rechterzijgevel verkleind. Op 10 september was het advies positief, op 24
september de vergunning verleend.

Dat is 345 dagen van aanvraag tot besluit, waarvan ongeveer drie maanden het
gevolg van dat ene advies. Naast de Biezenstraat met 300 dagen hebben we nu twee
gemeten doorlooptijden in plaats van nul.

**De strijdigheid zelf was klein en meetbaar:** bestemmingsplan Nijmegen Zuid
2017 staat negen meter bouwhoogte en zes meter goothoogte toe, het plan kwam op
9,45 meter met een verholen goot op 8,866. Precies het soort afwijking dat op
papier marginaal lijkt.

**De les die in de doorrekening hoort:** de planologische toets is te berekenen,
het welstandsoordeel niet. Bij een ingreep die het aanzicht verandert hoort een
extra ronde van een kwartaal in de planning, plus aanpassingen aan materiaal en
detaillering die geld kosten. Leien in plaats van pannen is geen detail.

**Drie voorschriften erbij die we nog niet kenden:** de start twee dagen vooraf
melden, uiterlijk vier weken voor de start een ingevulde risicomatrix, en bij
twaalf punten of meer ook een bouwveiligheidsplan met een veiligheidscoördinator.
Die staan nu in de bijlagenlijst.

**En er bestaat een standaardmotivering voor een nokverhoging** met een vaste
inhoudsopgave: plan en omgeving, beeldkwaliteit, geluid, flora en fauna,
cultuurhistorie, financiële uitvoerbaarheid, participatie en de evenwichtige
toedeling van functies aan locaties. Dat format is herbruikbaar, en daarmee is
de motivering zelf geen reden om een bureau in te schakelen.

Alles staat als achtergrondstuk, het drieëndertigste, en de doorlooptijden staan
in splitsingstoets.py.

---

## 59. Een gestrande aanvraag, en een fout in ons eigen filter — 7 oktober 2026

De Willemsweg 98: het bouwkundig splitsen van een fietsenwinkel met showroom en
werkplaats in twee huurwoningen op de begane grond. Aanvraag 27 april 2026, op
22 september buiten behandeling gesteld. Vijf maanden kwijt, €482,53 leges
betaald, geen vergunning.

**De reden is leerzaam:** de gemeente vroeg om de aanvraag compleet te maken, en
de nieuwe stukken waren nagenoeg identiek aan de eerste. De gevraagde punten
twee tot en met vier waren niet uitgewerkt. Een besluit om niet te behandelen
gaat niet over de inhoud, dus het plan kan nog steeds kansrijk zijn.

Daarbij een waarschuwing die breder geldt: de voorgestelde vergunningsvrije
aanbouw was niet met een ingevulde checklist aangetoond, en gezien de geringe
diepte van de achtertuin twijfelt de gemeente of die wel vergunningsvrij kan
zijn. Vergunningsvrij bouwen moet je onderbouwen en niet aannemen.

En de gemeente geeft de route zelf mee: dien eerst een conceptaanvraag in. Bij
de Staringstraat staat in het formulier expliciet dat dat niet is gedaan.

**De fout in ons filter.** "Buiten behandeling" en "intrekking" stonden in de
lijst met uit te sluiten woorden, dus zulke bekendmakingen werden weggegooid als
ruis. Dat is precies verkeerd: een gestrande aanvraag is een uitkomst. Nu komen
ze door als er ook een onderwerp in zit dat ons raakt. Getest: een buiten
behandelingstelling over splitsen komt binnen, een over het kappen van een boom
niet.

Daarmee wordt ook die oude melding begrijpelijk: in de brief van 2 oktober stond
"op 24 september buiten behandeling gesteld: de procedure is gestaakt voordat er
een besluit lag". Dat kwam toen uit een ander kanaal; nu is het een regulier
signaal.

**En dit is het vierde soort ingreep dat we nu hebben gezien:** splitsen van een
woning, een aanbouw, een nokverhoging, en een functiewijziging van bedrijfsruimte
naar wonen. Die laatste is het zwaarste traject, want er komt een woonfunctie bij
op een plek waar die er niet was.

---

## 60. De lichte route, en daarmee is het beeld rond — 7 oktober 2026

De Heydenrijckstraat 40 is de schoonste van de vijf dossiers en voor Derksen
Vastgoed de meest relevante. De woning op de begane grond is gescheiden van het
souterrain, waardoor daar een tweede zelfstandige woning ontstaat.

**Aanvraag 15 april 2026, vergunning 23 september: 161 dagen.** Drie stukken
ingediend: het verzoekformulier en twee tekeningen. Eén voorschrift: de start
twee dagen vooraf melden. Geen groenmaatregelen, geen quickscan, geen
waterberging, geen welstandsronde.

**Het verschil zit in de buitenkant.** De activiteit bouwen onder het
omgevingsplan is hier vergunningsvrij: het plan past in artikel 22.27 onder i
van het omgevingsplan en in bestemmingsplan Nijmegen Oost, waar meerdere
woningen zijn toegestaan. Er verandert niets aan de voorgevel, de wijzigingen
zijn enkel inpandig, en de achtergevelwijzigingen zijn vergunningsvrij omdat het
alleen een aandachtspand is en geen monument.

**Wat wel vergunningplichtig blijft, is de technische bouwactiviteit**, en de
reden staat er precies: doordat er een zelfstandige woning wordt gerealiseerd
ontstaat een apart brandcompartiment. Daar keken de constructeur, een
bouwtechnisch specialist en de Veiligheidsregio Gelderland Zuid naar.

**Daarmee staat de vuistregel die uit vijf dossiers volgt:**

| soort ingreep | route | doorlooptijd | bijlagen |
|---|---|---|---|
| inpandig splitsen, voorgevel ongemoeid | alleen technisch | 5 maanden | 3 |
| splitsen met aanbouw buiten het plan | bopa | 10 maanden | 21 |
| dakopbouw met nokverhoging | bopa plus welstand | 11 maanden | 22 |
| functiewijziging bedrijfsruimte naar wonen | zwaarst | gestrand na 5 maanden | onvolledig |

Dat is het getal dat elke ontwikkelcase nodig heeft en dat we een week geleden
nog niet hadden. De brief krijgt de instructie dat verschil te noemen zodra een
bekendmaking over splitsen gaat, want het bepaalt of een plan maanden of een
jaar kost.

---

## 61. Berg en Dalseweg 70: vijf appartementen, en de rekensom erachter — 7 oktober 2026

Zesde dossier, ingediend 17 september 2026 door Ampire Bouw B.V. aan de
Oranjesingel 13A, KvK 83440453. Geen particulier opdrachtgeverschap: dit is een
ontwikkelaar.

**Opnieuw de lichte route.** De aanvraag kent maar een activiteit: bouwactiviteit
(technisch). Geen omgevingsplan-activiteit, dus de aanvrager gaat ervan uit dat
die vergunningsvrij is, net als bij de Heydenrijckstraat. En dat bij een
splitsing naar VIJF eenheden. De lichte route schaalt dus; het gaat niet om het
aantal woningen maar om de buitenkant.

**De vijf eenheden meten 39, 24, 24, 22 en 22 m2 GBO, samen 131 m2.** Daarmee is
de rekensom te maken, en die is verrassend:

- als een woning van 131 m2 met een WOZ rond vijf ton: ruim 210 punten, dus
  vrije sector, markthuur ongeveer €2.350 bij het gemeten niveau van €18 per m2;
- als vijf losse eenheden: elk negentig tot honderd punten, dus allemaal
  gereguleerd, samen een wettelijk maximum van ongeveer €3.000.

**Het maximum van vijf kleine woningen ligt dus hoger dan de vrije huur van een
grote**, ongeveer €665 per maand, 28 procent. De reden is dat het puntenstelsel
per woning een vaste voet kent en dat kleine woningen per vierkante meter meer
punten opleveren. Dezelfde groottepremie die bij verkoop zichtbaar is, zit ook
in de huurregels.

Wat je ervoor inlevert is vrijheid: boven dat maximum mag niet worden verhuurd,
het stijgt alleen met de indexering, en elk van die vijf huurders kan de huur
laten toetsen.

**En dat verklaart het verschil met de Berg en Dalseweg 11**, waar splitsen van
twee naar vier maar €590 opleverde: daar waren de bestaande woningen al klein.
De winst zit in het verschil tussen een grote woning en kleine eenheden, niet in
het splitsen zelf. Dat staat nu als achtergrondstuk.

**Vier partijen in zes dossiers:** DD21 B.V., Bouwplan, Ampire Bouw B.V. en een
tekenbureau uit Siebengewald. Dat is genoeg om een register te beginnen van wie
er in de ring ontwikkelt; dat zou ik als volgende bouwen.

---

## 62. Het model sloot de beste splitsing uit — 7 oktober 2026

**Mark:** wordt er op deze manier ook naar het huidige Funda-aanbod gekeken?

**Deels, en op een beslissend punt niet.** Het goede nieuws: de doorrekening
past per nieuwe eenheid al het wettelijk maximum toe. Een splitsing wordt dus
niet op markthuur gerekend als die eenheden gereguleerd zijn, en de vergelijking
met de ene woning gaat ook door het puntenstelsel.

**Maar het model hield een ondergrens van 45 m2 per eenheid aan met de
toelichting dat kleinere eenheden krap zijn.** Dat is een aanname, en de
aanvragen van vandaag weerspreken hem: de Berg en Dalseweg 70 wordt gesplitst in
vijf eenheden van 39, 24, 24, 22 en 22 m2, en in het aanbod staan studio's van
23, 24 en 28 m2 te koop. Die grens sloot dus precies de variant uit die een
ontwikkelaar werkelijk aanvraagt, en dat is de variant die het meest opbrengt
doordat het puntenstelsel per woning een vaste voet kent.

Nu rekent het model de varianten van twee tot zes eenheden door, met het
wettelijk maximum per variant, en houdt de beste over. De ondergrens is verlaagd
naar 22 m2, en dat is een gemeten grens in plaats van een aanname. Getest op vijf
pandmaten: 131 m2 kiest vier eenheden, 158 m2 vijf, 102 m2 drie, 70 m2 twee.

**Eén waarschuwing die er hard bij moet, en die staat nu ook in de opdracht aan
de brief:** de verbouwkosten zitten er niet in. Elke extra eenheid vraagt een
eigen keuken, badkamer, meterkast en entree. De doorrekening zegt dus welke
opdeling het meest OPBRENGT, niet welke het meest OPLEVERT. Bij vijf eenheden is
dat verschil groot genoeg om de rangorde om te gooien.

---

## 63. Een kamerhuur hoort per kamer, niet per vierkante meter — 7 oktober 2026

**Mark:** dat meten we zelf toch al via Kamernet en Pararius?

**Klopt, en dat maakt mijn eigen advies van een minuut eerder onzin.** Ik zei
dat hij met drie telefoontjes naar een bemiddelaar kon weten wat een kamer
opbrengt. Die telefoontjes zijn niet nodig: er staan 56 huurwaarnemingen in het
bestand, waaronder Kamernet-advertenties die per kamer zijn.

**Het echte probleem zat in de eenheid.** Het kamerscenario rekent met een prijs
per vierkante meter: €25,79 maal het verhuurbare deel van 158 m2 geeft €4.075.
Dat getal is door niemand na te rekenen. De markt praat in huur per kamer, onze
eigen waarnemingen staan per kamer, en dan is een prijs per m2 de enige
grootheid die niemand kent.

Het dossier zet er nu bij hoeveel kamers het zijn en wat dat per kamer betekent:
"zes kamers à €679, toets dit aan het kameraanbod in deze buurt". Het aantal
volgt uit de gemeten kamergrootte van ongeveer 20 m2 uit onze eigen Kamernet-
waarnemingen, niet uit een aanname. Getest op vier pandmaten.

**Daarmee wordt de gevoeligheid zichtbaar in plaats van verstopt.** Bij €679 per
kamer staat de Stieltjesstraat 10 op +56% boven de vraagprijs, bij €600 op +38%,
bij €550 op +27% en bij €450 op +4%. Het is dus geen no-brainer van +50% maar
een bandbreedte die door één getal wordt bepaald, en dat getal meten we zelf.

De opdracht aan de brief eist nu dat de huur per kamer wordt genoemd, met het
aantal waarnemingen waarop die rust.

---

## 64. Het aantal bouwlagen lag al klaar en werd nergens gebruikt — 7 oktober 2026

**Mark:** kunnen we uit onze gegevens bepalen hoeveel vierkante meter een etage
heeft, zodat we zien of een pand van 120 m2 twee of drie lagen heeft?

**Dat kan, en het lag al klaar.** De 3D BAG levert b3_bouwlagen, het geschatte
aantal bouwlagen, en b3_opp_grond, het grondvlak. Beide worden sinds weken
opgehaald voor 1.242 panden en werden in geen enkele module gebruikt.

Het dossier zet er nu bij: "3 bouwlagen, grondvlak 41 m2, dus ongeveer 40 m2
per laag bij 120 m2 gebruiksoppervlak". Bij een pand met meer dan een woning
staat erbij dat de oppervlakte niets zegt over de verdeling per laag, want dan
is de gebruiksoppervlakte van dit object niet het hele pand. Bij een pand van
een bouwlaag komt er geen regel.

**Waarom dit het bepalende getal is bij splitsen.** Een opdeling gaat in de
praktijk per woonlaag: dat is waar de trap, de meterkast en de leidingschacht
al zitten. Een pand van 120 m2 over twee lagen geeft twee eenheden van 60, over
drie lagen drie van 40. Dat verschil bepaalt in welke grootteklasse de nieuwe
eenheden vallen, en daarmee of de groottepremie 1,236 of 1,422 is.

**Deze reparatie ging drie keer mis voordat hij werkte**, en dat is het noteren
waard. De regel waarop ik aankoppelde komt drie keer in het bestand voor, met
verschillende inspringing, en mijn vervanging landde alle drie de keren. Het
bestand was daarna op twee plekken stuk. Dat is de prijs van tekstvervanging in
een bestand van zevenduizend regels; voortaan eerst tellen hoeveel keer een
anker voorkomt.

---

## 65. Een verkeerd afzenderdomein, en niemand die het merkte — 7 oktober 2026

**Mark:** de mails van server@huislijn.nl worden niet geopend in mijn mailbox,
dus die woningen komen ook niet in het bestand.

**Klopt, en de oorzaak was een domein dat niet bestaat.** In de lijst met
afzenders stond "huisly.nl" en Huislijn stuurt vanaf "huislijn.nl". Die mails
werden dus nooit opgehaald: ze bleven ongelezen staan en de woningen kwamen
nergens terecht. De parser die ik vandaag heb gebouwd stond klaar voor mails die
nooit binnenkwamen.

Beide domeinen staan er nu in; Huisly is een andere dienst. Getest op vier
afzenders.

**Wat hieraan erger is dan de fout zelf: niets meldde het.** Een verkeerd domein
levert geen foutmelding op, alleen stilte, en stilte ziet er in een rapport uit
als "geen nieuws". Het is opgemerkt doordat Mark naar zijn mailbox keek, niet
doordat het systeem iets zei.

Er is nu een controle "Bronnen die niets opleveren": hij telt per bron hoeveel
waarnemingen er in het aanbodbestand staan en meldt elke bron die op nul staat,
met als diagnose dat het afzenderdomein of de attendering zelf het probleem is.
Getest op beide gevallen. Had die controle er eerder gestaan, dan had Huislijn
vanaf 1 oktober in het rapport gestaan in plaats van in een ongelezen mailbox.

**Dat is vandaag de tweede fout van deze soort**, na de buiten-behandelingstelling
die als ruis werd weggefilterd. Beide keren werd er niets gemeld omdat er niets
gebeurde, en dat is het moeilijkste soort fout om te zien.

---

## 66. FAIL BAG op een adres met een studionummer — 7 oktober 2026

In het logboek staat "FAIL BAG: Jan de Wittstraat 6-8 studio 9". Dat is het
studiocomplex dat vandaag al eerder opdook, en de reden dat de BAG-opvraging
mislukt is het adres zelf: "6-8 studio 9" is geen huisnummer dat de BAG kent.

Twee dingen worden er nu afgehaald voordat de BAG wordt bevraagd. Een aanduiding
van een eenheid achter het adres (studio, bouwnummer, appartement, unit, kamer,
woning met een nummer erachter), en een bereik van twee huisnummers, waarvan het
eerste wordt genomen omdat dat het pand is.

Getest op acht adressen uit het echte aanbod: Jan de Wittstraat 6-8 studio 9
geeft nu nummer 6, Berg en Dalseweg 11-11A geeft 11, en de gevallen die al goed
gingen blijven goed, inclusief Plein 1944 129 met een jaartal in de straatnaam
en Graafseweg 33-A21 met een huisletter en een toevoeging. Een nieuwbouwregel
als "Amber fase 2 Stadswoning bouwnr. 608" geeft terecht geen adres: dat is geen
pand maar een bouwnummer, en zulke regels hebben sinds vandaag de status
"project" en vallen toch al buiten de berekening.

**En een tweede regel uit hetzelfde logboek werkt zoals bedoeld:** "Rente
bijgesteld van 5.75% naar 5.5% op basis van de gemeten stand". De vaste waarde
in het model is 5,75% en de gemeten marktrente bij 70% financiering staat op
5,50%, dus het model corrigeert zichzelf en zegt dat het dat doet. Dat is precies
het gedrag dat we vorige week hebben ingebouwd nadat de brief met een aangenomen
rente rekende.

---

## 67. Uitponden stond nergens in de tabel — 7 oktober 2026

**Mark:** er is nergens te zien wat het oplevert om een woning te kopen, te
splitsen in twee of drie woningen en die te verkopen, terwijl dat juist
interessant lijkt.

**Klopt, en de oorzaak is dat de tabel op huur kiest.** Het scenario wordt
bepaald door welke route de hoogste maandhuur geeft, en de richtprijs is de
koopsom waarbij de nettohuur rente en aflossing dekt. Uitponden komt daar nooit
uit, hoe goed het ook is, want er zit geen huur in.

Dat is extra zuur omdat de functie waarde_na_splitsing al sinds vrijdag in
grootte_premie.py staat, met 571 waarnemingen eronder, en door geen enkele
module werd aangeroepen. Net als de bouwlagen uit de 3D BAG.

**Het dossier heeft nu een regel "uitponden"** met het beste aantal eenheden, de
gemeten premie voor die grootteklasse, de prijs per m2 en de marge na aankoop en
kosten koper. Met de aantekening dat het puntenstelsel en de opkoopbescherming
bij verkoop niet gelden, en dat de marge VOOR verbouwing, splitsingsakte, VvE en
belasting is.

**Twee rekenfouten die ik onderweg heb gemaakt en gevonden.**

De eerste: de premie toepassen op de eigen prijs per m2 van het pand. Doddendaal
101 staat 34% boven de buurtmediaan en kwam dan op €11.290 per m2 uit, en dat is
geen prijs maar een rekenfout. Het anker moet de buurtmediaan zijn, en die is
terug te rekenen uit de afwijking die we al hebben.

De tweede: ook nog delen door de premie van de huidige grootteklasse. De
buurtmediaan hoort al bij de ijkklasse van 80 tot 100 m2 waar de premie 1,000
is, dus die deling telt dubbel. Na correctie komt Prof. Molkenboerstraat 30 op
€7.202 per m2 voor eenheden van 37 m2, en dat is te toetsen: in Galgenveld staan
nu een eenheid van 49 m2 op €7.857 en een van 35 m2 op €6.714 te koop. Het getal
ligt dus binnen wat de markt daar vraagt.

**Wat het oplevert op het huidige aanbod**, met alle vier de ontbrekende posten
nog open: Krayenhofflaan 47 drie eenheden van 39 m2 met €409.000 marge, Prof.
Molkenboerstraat 30 drie van 37 m2 met €320.000, van Goorstraat 34 drie van 34
m2 met €320.000, Zwaluwstraat 175 drie van 27 m2 met €245.000. En Doddendaal 101
komt negatief uit, want dat pand is per m2 al duur.

---

## 68. Beide routes gedekt: de strategie doorgerekend — 7 oktober 2026

**Mark:** wat als we alleen panden kopen waarvan we zeker weten dat ze bij
verhuur al rondkomen EN bij uitponden winst geven? Dan is de onderkant gedekt:
lukt verkopen niet, dan verhuren we.

**Dat is te meten, en het antwoord is ja, maar niet tegen de vraagprijs.** Met
dezelfde opdeling van drie eenheden voor beide routes:

| pand | vraagprijs | bod waarbij de huur het draagt | verkoopwaarde |
|---|---|---|---|
| Krayenhofflaan 47 | €439.000 | €314.000 (-28%) | €892.000 |
| van Goorstraat 34 | €390.000 | €326.000 (-16%) | €749.000 |
| Zwaluwstraat 175 | €349.500 | €302.000 (-14%) | €629.000 |

**De huurroute is vrijwel altijd bindend**, en de reden is structureel: het
puntenstelsel begrenst de huur van kleine eenheden en de verkoopprijs niet. Het
bod waarbij beide routes werken is dus het bod waarbij de huur het draagt, en
dat ligt veertien tot achtentwintig procent onder de vraagprijs.

Daar staat tegenover dat de verkoopwaarde bij dat bod enorme ruimte laat: bij de
Krayenhofflaan €531.000 na aftrek van bod en kosten koper, dus €177.000 per
eenheid voor verbouwing, splitsingsakte, VvE en belasting. Dat is ruim, maar het
is geen winst totdat die vier posten zijn gemeten.

Het dossier heeft nu een regel "beide routes gedekt" met het bod, het verschil
met de vraagprijs en de ruimte per eenheid. De opdracht aan de brief zegt dat
die regel prominent genoemd moet worden, en verbiedt te schrijven dat een pand
bij de vraagprijs gedekt is als dat bod eronder ligt.

**Waarom dit de scherpste screening is die we hebben.** Een pand met beide
routes gedekt is niet een pand waarop je moet hopen dat de markt meewerkt: het
rekent rond bij verhuur, en de verkoop is de bonus. Dat is een ander soort
aankoop dan de cases die de brief tot nu toe liet zien, en het verklaart ook
waarom er in de tabel nooit iets interessants stond: die kolom rekende alleen de
huur van het ONGESPLITSTE pand.

---

## 69. Kamerverhuur was niet begrensd in het model — 7 oktober 2026

**Mark:** hoe verhoudt splitsen in zelfstandige appartementen zich tot opknappen
tot losse studentenkamers?

**Bij het uitzoeken daarvan kwam een fout boven die groter is dan de vraag.**
Sinds de Wet betaalbare huur valt ook onzelfstandige woonruimte onder een
puntenstelsel, het WWSO, met per kamer een wettelijk maximum. De module wwso.py
kan dat al berekenen en wordt alleen gebruikt om huuradvertenties te toetsen.
Het kamerscenario in de doorrekening paste het maximum NIET toe, terwijl dat
voor zelfstandige woningen al jaren gebeurt.

**Wat dat betekende voor de Stieltjesstraat 10.** Het model rekende €4.075 per
maand. Het WWSO geeft voor zes kamers van 21 m2 een band van €3.117 bij een
karige telling tot €3.984 bij een ruime. De aangenomen huur lag dus BOVEN het
wettelijk maximum, ook in de gunstigste variant. De richtprijs zakt daarmee van
+48% naar een band van +20% tot +53% ten opzichte van de vraagprijs.

Het kamerscenario kapt nu af op het WWSO-maximum bij een ruime telling, en als
de uitkomst boven de karige variant ligt staat erbij dat het alleen haalbaar is
bij ruime gemeenschappelijke ruimte, keuken en sanitair.

**En dat beantwoordt Marks vraag ook.** Beide routes zijn gereguleerd, dus de
keuze gaat niet over wettelijke ruimte maar over iets anders: zelfstandige
eenheden kunnen worden verhuurd EN verkocht, kamers alleen verhuurd. Een
gesplitst pand heeft twee uitgangen, een kamerpand één. Dat is de reden om voor
splitsen te kiezen, niet een hogere huur.

**Zijn zorg dat je moet kiezen, klopt daarmee maar half.** Je kiest wel, maar de
ene keuze houdt meer open dan de andere.

---

## 70. De puntentelling omgedraaid — 7 oktober 2026

**Mark:** de telling is onvolledig omdat we de keuken en de badkamer niet
kennen, maar dat kunnen we omdraaien: wanneer we een aantal punten willen
halen, kunnen we dat als voorwaarde stellen.

**Eens, en dat haalt de angel uit de hele beperking.** Zolang je de punten
probeert te RADEN is onbekendheid een probleem. Draai je het om, dan is het een
programma van eisen: welk puntenaantal willen we halen en wat moet de
verbouwing dan opleveren.

puntendoel.py doet dat. Het meet per maatregel wat hij werkelijk oplevert door
de telling met en zonder die maatregel door te rekenen, dus de waarden komen uit
het stelsel zelf en niet uit een tabel die kan verouderen.

Drie voorbeelden uit het huidige aanbod:
- Krayenhofflaan 47, 116 m2, WOZ €360.000, label D: staat op 179 punten, acht te
  kort. Een labelstap naar C is precies genoeg.
- Burg. Hustinxstraat 56, 102 m2, WOZ €419.000, label B: staat op 186, één te
  kort. Een balkon van 8 m2 levert er drie op.
- Zwaluwstraat 175, 82 m2, WOZ €376.000, label C: staat op 159, achtentwintig te
  kort. Alle inrichtingsmaatregelen samen geven negentien punten, dus die grens
  is daar niet te halen. Dat is ook een antwoord, en een definitief.

**Een valkuil die ik eruit heb gehaald.** De eerste versie koos de grootste
maatregel: bij een tekort van acht punten kwam "energielabel naar A" met achttien
punten eruit, terwijl label C met acht punten precies genoeg is. Een eis die
verder gaat dan nodig kost geld dat niets oplevert. Nu wordt de kleinste
maatregel gekozen die het tekort alleen al dekt, en pas als die niet bestaat
wordt er gestapeld, opnieuw de kleinste eerst.

Het dossier zet die regel erbij, en de brief moet hem noemen in plaats van
alleen te melden dat het pand onder de grens zit. "179 punten, dus gereguleerd"
is een conclusie waar pa niets mee kan; "acht punten te kort, een labelstap naar
C is genoeg" is een opdracht aan een aannemer.

---

## 71. Eén programma voor het gebouw, één per eenheid — 7 oktober 2026

**Mark:** als er een pand van 180 m2 over drie etages komt, moet het systeem dan
niet zeggen: splitsen in drie, en dit zijn de eisen? En dan apart wat aan het
GEBOUW moet gebeuren, zoals isolatie voor het label, en wat per APPARTEMENT.

**Die tweedeling is wezenlijk en zit er nu in.** Het energielabel en de isolatie
zitten aan de schil: dat is één bestek voor één aannemer, en de puntenwinst telt
in elke eenheid mee. De keuken, het sanitair, de buitenruimte en de berging zijn
per eenheid en staan dus zo vaak in de begroting als er eenheden zijn.

Voorbeeld van 180 m2 over drie lagen, WOZ €500.000, label E: elke eenheid van 60
m2 staat op 91 punten. Eén keer aan het gebouw een labelstap naar D levert er
negentien per eenheid op; drie keer per eenheid een balkon, een badkamer met
ligbad en een berging leveren er samen twaalf op.

**En dan komt de eerlijke uitkomst, die ik eerst niet goed afhandelde.** Samen is
dat 122 punten, en de 187 wordt niet gehaald. Bij eenheden van 60 m2 met een WOZ
van €167.000 is de vrije sector gewoon onbereikbaar.

Daarom zegt het programma nu wat die punten dan WEL opbrengen: de maximumhuur
per eenheid gaat van €575,87 naar €788,71, over drie eenheden €639 per maand of
€7.662 per jaar. Dat is het getal waartegen je de verbouwing afweegt.

**Dat is een scherpere conclusie dan hij lijkt.** Bij gesplitste eenheden is 187
punten meestal het verkeerde doel. De opbrengst zit in een zo hoog mogelijk
wettelijk maximum per eenheid, plus de verkoopoptie die kamers niet hebben. De
vrije sector is iets voor een hele woning die groot genoeg is, en dat is precies
het pand dat je NIET moet splitsen als je wilt verhuren.

---

## 72. De bron nagekeken, en een regel die ontbrak — 7 oktober 2026

**Mark:** welke bron gebruiken we voor de huurgrenzen en de vrije sector?

**Nagekeken, en de bedragen kloppen exact.** De tabel in wwso.py staat op
peildatum 1 januari 2026 met als bron bijlage I van het Besluit huurprijzen
woonruimte. De liberalisatiegrens voor zelfstandige woningen is de maximale
huurprijsgrens bij 186 punten, en die is in 2026 €1.228,07 per maand; vanaf 187
punten is het vrije sector. De indexering per 1 januari 2026 was 3,65%.

Steekproef op de tabelwaarden: 110 punten €706,32, 116 punten €747,51, 122
punten €788,71, 183 punten €1.207,46, 193 punten €1.276,12. Alle vijf gelijk aan
de bron. Het gezondheidsrapport meldt het ook als de peildatum verouderd raakt,
want die grenzen worden elk jaar per 1 januari geïndexeerd.

**Maar er ontbrak een regel, en die werkte in ons nadeel.** De cap op de
WOZ-punten zat er wel in: de WOZ mag voor hoogstens een derde meetellen, en
alleen als de woning zonder die begrenzing op 187 of meer zou uitkomen. Wat
ontbrak is wat er daarna gebeurt. Zakt de woning DOOR die cap onder de 187, dan
geldt een waardering van 186 punten, niet het lagere getal dat de cap oplevert.
Dat staat als rekenvoorbeeld in het Besluit: 218 punten ongecapt, 162 na de cap,
en dan telt 186.

Ons model rekende met dat lagere getal en dus met een veel lagere maximumhuur
dan er gevraagd mag worden. Bij 162 punten is dat ongeveer €1.040 tegen
€1.228,07 bij 186: bijna tweehonderd euro per maand verschil, in het nadeel van
de verhuurder.

**Wat opvalt bij het testen:** de cap bijt bij panden met een hoge WOZ en een
beperkte maat, en dat is precies het soort pand in Galgenveld. Een woning van 74
m2 met een WOZ van €575.000 haalt 175 punten met een WOZ-deel van 63; die blijft
gereguleerd. Een pand van 105 m2 met WOZ €410.000 en label A komt op 192 en is
vrij. Het verschil zit niet in de WOZ maar in de verhouding tussen WOZ en
oppervlakte.

---

## 73. Een landelijk ijkpunt voor onze eigen huurmeting — 7 oktober 2026

Het artikel dat Mark stuurde verwijst naar Pararius, en dat is dezelfde bron die
wij zelf uitlezen voor de ring. Daarmee is er voor het eerst een landelijk
getal om onze eigen meting tegen te houden: €20,92 per m2 in de vrije sector
over het derde kwartaal van 2026, oftewel €1.914 per maand voor een doorsnee
woning van ongeveer 91 m2.

**Dat zet onze meting in een verontrustend licht.** In het dossier van Burg.
Hustinxstraat 46 staat "gemeten €12/m2 op 3 panden, gewogen met de referentie
€20/m2 tot €18/m2". Die gemeten €12 ligt 43% onder het landelijke cijfer, en dat
is te veel om alleen aan Nijmegen toe te schrijven.

Drie verklaringen die allemaal kunnen meespelen, en die het getal niet fout
maken maar wel beperkt: het landelijke cijfer gaat over NIEUWE verhuringen in de
VRIJE sector, onze meting bevat ook middenhuur, en sommige van onze
waarnemingen zijn inclusief servicekosten. Bovendien rust de €12 op drie
panden.

Er is nu een controle die onze mediane huur per m2 tegen dat landelijke cijfer
houdt en meldt als het verschil boven een kwart komt, met die drie verklaringen
als diagnose. Getest op beide gevallen: bij een afwijking van 9% blijft het OK,
bij 46% komt de melding.

**Waarom dit meer is dan nieuwsgierigheid.** De weging met de referentie
verbergt nu hoe ver de meting weg ligt: er komt €18 uit, en dat ziet er
betrouwbaar uit. Het verschil tussen €12 en €20,92 bepaalt of een richtprijs
€250.000 of €430.000 is, en dat is geen detail dat in een weging mag verdwijnen.

---

## 74. De ochtendbrief viel weg en niemand merkte het — 8 oktober 2026

**Mark om 11:06:** de brief van vandaag is nog niet binnen, en het liefst
ontvang ik hem rond 7:00. Later: de run mag ook in de nacht draaien, als wij de
brief maar kunnen lezen vanaf 7:00.

**Die tweede zin veranderde de oplossing, en maakte hem eenvoudiger.** Eerst
had ik elke editie twee keer ingepland met een wachter die alleen de run op het
juiste lokale uur doorliet, omdat GitHub cron in UTC rekent en de brief bij de
overgang naar wintertijd een uur opschuift. Als de brief pas om 7:00 gelezen
hoeft te worden, is dat uur verschuiving niet erg en kan die hele constructie
eruit.

**Wat er nu staat:**
- werkdagen een eerste poging om 1:17 UTC, dus 3:17 in Nijmegen in de zomer en
  2:17 in de winter;
- een TWEEDE poging om 3:17 UTC, die alleen draait als er nog geen brief van
  vandaag in de repo staat;
- de weekeditie op zondag om 0:17 UTC, zo vroeg als kan, want die werkt de hele
  pandgeschiedenis bij en kan uren duren.

Alle tijden staan na middernacht UTC, want de run leidt de briefdatum af uit de
UTC-datum van de runner: een cron van 23:17 zou de brief van gisteren opleveren.
Getest op zomer- en wintertijd: de UTC-datum is bij alle drie dezelfde dag, en
de krapste marge tot 7:00 is 103 minuten.

**Die tweede poging is de winst van 's nachts draaien.** Een mislukte eerste
run kostte tot nu toe de hele ochtendbrief, omdat hij om 5:17 begon en er geen
tijd meer was. Nu probeert het systeem het zelf nog eens, en de wachter voorkomt
dat hij dubbel werk doet als de eerste poging wel is gelukt.

**Maar de echte fout is dat de stilte niet opviel.** De mailstap stuurt alleen
iets als het briefbestand bestaat. Faalt er een stap daarvoor, dan is er geen
brief EN geen bericht, en dan ziet een mislukte run eruit als een rustige dag.
Vandaag duurde het tot half twaalf voordat dat opviel, en alleen omdat Mark het
zelf miste.

Twee dingen daartegen. Een mailstap die een kort bericht naar Mark stuurt als er
geen brief uitkwam, met de link naar het logboek; die staat op `always()`, dus
hij gaat ook af als de run halverwege klapt, en alleen bij de LAATSTE poging van
de dag, anders meldt de eerste poging al dat er niets is terwijl de tweede hem
nog gaat maken. En een controle in het gezondheidsrapport die meldt wanneer de
laatste brief is gemaakt: twee dagen stilte is altijd een probleem, een dag niet,
want de weekeditie draait op zondag. Getest op vier gevallen.

**Dit is de derde fout van deze soort in twee dagen**, na het verkeerde
afzenderdomein van Huislijn en de buiten-behandelingstelling die als ruis werd
weggefilterd. Alle drie kwamen aan het licht doordat Mark iets miste, niet
doordat het systeem iets zei. Dat is het patroon om te blijven afdekken: een
fout die zich uit als afwezigheid.

---

## 75. Twee fouten in de brief van 8 oktober — 8 oktober 2026

De handrun leverde een brief op waarin de uitpondroute voor het eerst staat, met
de Nieuwe Markt 90 als voorbeeld: vier eenheden van 40 m2 die samen €1.201.152
doen, €568.652 over na aankoop en kosten koper, en een huur van €2.139 die een
koopsom tot €436.212 draagt. De rekensom is narekenbaar en klopt.

**Fout een: de brief maakt van een splitsingsaanvraag een kamerverhuurverhaal.**
Bij de Berg en Dalseweg 11-11A staat dat een slecht label "bij verkamering de
maximale huur per kamer drukt" en dat wie daar kamers verhuurt eerst het label
moet opkrikken. Maar de aanvraag gaat over vier ZELFSTANDIGE huurwoningen; in
het formulier staat letterlijk dat het aantal huurwoningen van 2 naar 4 gaat.
Kamerverhuur komt er niet in voor.

Daarbij mengt die ene zin twee stelsels: het WWS geldt per zelfstandige woning,
het WWSO per kamer. De opdracht zegt nu dat de aanvraag bepaalt welk stelsel je
bespreekt, en dat de brief geen route mag verzinnen die de aanvraag niet noemt.
Dat is dezelfde zwakte als de drie eerdere regimewissels van deze week.

**Fout twee: een prijswijziging van twee dagen terug als nieuws van vandaag.**
"De grootste verlaging was Palmstraat 40, vijftigduizend euro omlaag naar
€485.000" stond ook al in de brief van 6 oktober. De oorzaak zit in de tabel:
die vergelijkt met de prijs van de eerste keer dat we het pand zagen, dus een
verlaging blijft er weken in staan.

Er staat nu een kolom "Gewijzigd op" met de datum waarop de prijs werkelijk
veranderde, uit de pandgeschiedenis waar elke prijswijziging als gebeurtenis
met datum staat. De opdracht verbiedt het woord verlaging als nieuws zodra die
datum ouder is dan gisteren.

**En wat Mark als gezondheidsrapport stuurde, was de broncode van
gezondheid.py.** Het script zelf draait: in een lege map levert het netjes een
rapport op met elf onderdelen in orde en de rest als fout, zoals het hoort
zonder gegevens. Daar is dus niets stuk; het verkeerde bestand is geplakt.

---

## 76. De controle van gisteren vond de fout van vandaag — 8 oktober 2026

Het rapport staat op 41 in orde, 7 aandachtspunten, nul fouten, en de nieuwe
briefcontrole staat op OK. Maar er staat een regel die er gisteren nog niet kon
staan:

    Bronnen die niets opleveren: funda: 528, pararius: 24, kamernet: 44,
    huislijn: 0; geen enkele waarneming van: huislijn

En bij de attenderingen: `huislijn: 4 mails, 0 objecten`.

**Dat is precies waarvoor die controle is gemaakt.** De domeinfix werkt, de
mails komen binnen, en nu blijkt de parser ze niet te lezen. Zonder die controle
had Huislijn er maanden tussen kunnen zitten als een bron die wel wordt
opgehaald en niets oplevert.

**De oorzaak is te voorspellen.** Ik heb de parser gebouwd op de tekst die Mark
in het gesprek plakte, met de straatnaam en de prijs op aparte regels en de
prijsregel beginnend met "Huur:". In een echte mail gaat HTML door een
tekstomzetting, en dan staan straat en prijs vaak op een regel.

De parser leest nu drie vormen:
- straatnaam en prijs op aparte regels, met of zonder blokhaken;
- straatnaam en prijs op dezelfde regel, ook met "Bekijk deze woning" erachter;
- alleen een kale URL plus een bedrag, waarbij de straatnaam uit de link komt.

Die derde is de betrouwbaarste, want een link overleeft elke tekstomzetting:
`/huurwoning/nederland/gelderland/4433366/maasstraat-nijmegen` geeft
"Maasstraat". Een slug die met "st" begint krijgt de punt terug, anders matcht
"St Agnetenweg" niet met de "St. Annastraat" die al in het aanbod staat.

**Een fout in mijn eerste poging, gevonden door te testen op vier vormen:** het
ruisfilter blokkeerde een regel met "Bekijk deze woning" erin, en in de
waarschijnlijkste vorm zit die tekst juist aan de prijsregel vast. Nu geldt een
regel met een BEDRAG erin nooit als reclame. Getest: alle drie de vormen geven
nu de panden, en een mail met alleen reclame geeft nul.

**En de log zegt het al zonder dat ik hoef te gokken.** De mailstap print bij
nul objecten de eerste vijfendertig regels van die mail naar het logboek. Die
staan dus in de run van vanmorgen, en daarmee is de echte vorm na te kijken in
plaats van te voorspellen.

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
