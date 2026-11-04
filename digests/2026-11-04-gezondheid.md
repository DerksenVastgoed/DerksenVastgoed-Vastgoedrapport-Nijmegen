# Gezondheidsrapport 2026-11-04

58 in orde, 9 aandachtspunten, 2 fouten.

## FOUT
- **Voorraad van de ring**: 23904 woningen in de ring, 23904 met oppervlakte, 16554 met label; nog 0 adressen te vragen; 535 adressen buiten de ring bewaard omdat er een bekendmaking over ging; 2356 woningen onderweg, geregistreerd maar nog niet gereedgemeld; de ronde over het gebied is niet afgemaakt na 29 pagina's en 17 tegels; 1 fouten in fase bag, laatste: tijdbudget van 600s om na 17 van de 31 tegels; de ronde is niet af; 1517 van de 1517 Nijmeegse postcodes leverden geen enkel object
  Dan is de voorraad te laag voor het deel dat niet gelezen is. Er wordt dan ook niets verwijderd, dus wat er niet meer is blijft staan. De reden staat in voorraad_stand.json onder bag.laatste_fout. Een hele ronde kostte gemeten 248,4 seconden over 22 tegels. Bij een geweigerde sleutel of een rem stopt de fase meteen en gaat hij de volgende run verder. Voorbeelden staan in voorraad_stand.json onder postcodes_leeg_voorbeeld. Liggen ze bij elkaar, dan raakt de doos in voorraad_bag.py een deel van de ring niet en moet DOOS ruimer. Liggen ze verspreid, dan staan er postcodes in de inventaris waar de BAG geen verblijfsobject heeft. In een geslaagde ronde waren het er 2 van de 1.242.
- **Overgeslagen stappen**: 1 stap(pen) overgeslagen: Marktprijzen
  Deze stappen zijn vandaag mislukt. Wat zij opleveren staat niet in de brief van vandaag. De reden staat in het joblogboek van de run, dat alleen in de browser te openen is.

## LET OP
- **Verkopen**: 661 verkopen: 518 geplakt, 143 met de hand; laatste 2026-10-13; de mailstap liet 8 meldingen vallen met dezelfde status en 0 met een andere
  Er komt nog geen verkoop uit de attendering, terwijl er wel 2 mails van funda.nl zijn gelezen. Het filter is dus niet de vraag; kijk naar wat de mailstap met die mails doet.
- **Veroudering aanbod**: 108 panden te koop, mediaan 35 dagen geleden voor het laatst bevestigd, oudste 63 dagen, 5 langer dan 60 dagen
  Die panden zijn waarschijnlijk al van de markt; ze blijven staan omdat de attendering alleen nieuw aanbod meldt. Een geplakte verkooplijst haalt ze eruit.
- **Woningen in bestaande panden**: 144 panden met 777 gevormde woningen erin; laatste ronde 0 nieuwe records, 0 gebeurtenissen, 0 wachten op een volgende ronde (stand van 2026-11-04); 1 panden met een sleutel die al van een ander pand is
  Die panden krijgen geen record, want een opzoeking mag nooit bij de buren uitkomen. Ze worden dus niet gemeld.
- **Plintobjecten geteld**: nog geen aantal: Stadscentrum is pas voor 0% opgehaald (0 van 337 postcodes); onder 90% publiceren we geen aantal, want een halve meting groeit nog
  Zolang dit staat, laat de brief het blok weg. De BAG-fase van voorraad_bag.py vult dit, Stadscentrum staat daarin alfabetisch achteraan.
- **Huurdekking**: steekproef van 12 adressen elders: 6 kennen we al (50%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 578, pararius: 51, kamernet: 100, huislijn: 86, 123wonen: 0, rentola: 3; geen post van 123wonen
  Bij 123wonen staat de attendering niet aan of stuurt die partij van een ander domein dan in AFZENDERS staat. Dat was bij Huislijn het geval: die stuurde van huisly.nl. Kijk in de mailbox van wie die post komt.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 94 panden: correctie 0.985 (1% stelselmatig), spreiding ±20.9%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.9% (94), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+111%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-11-04: huislijn: 1 mails, 1 objecten; kamernet: 11 mails, 9 objecten, 2 bewust overgeslagen; pararius: 1 mails, 1 objecten; regulier: 2 mails, 5 objecten, 1 bewust overgeslagen; vendr: 1 mails, 0 objecten; de mailboxtelling mislukte ((SINCE 01-Nov-2026): error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED; SINCE 01-Nov-2026: error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED)
  Van vendr komen wel mails binnen maar het script haalt er niets uit; de opmaak is waarschijnlijk veranderd. Voorbeeld: vendr: niets herkend in: Nieuwe projecten op Vendr

## OK
- **Versies**: code uit commit 8986d72, in één keer uitgecheckt; een halve upload kan hier niet bestaan
- **Geheugen verstuurde brieven**: 48 onderwerpen bekend, 38 in het venster van drie weken, laatste brief 2026-11-04; 23 onderwerpen kwamen in meer dan een brief terug
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-11-03-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Bekende onwaarheden in de brief**: 6 bekende onwaarheden getoetst op 5 teksten, geen ervan komt voor
- **Samenstelling in plaats van markt**: de buurten bewegen niet allemaal dezelfde kant op; geen waarschuwing nodig
- **Verkocht pand nog in het aanbod**: 7 panden zijn na het aanbod verkocht; geen aanbodtabel van vandaag om tegen te toetsen
- **Omvang van de gegevensbestanden**: bekendmakingen_archief.json: 12256, kamervergunningen.json: 7246, pandgeschiedenis.json: 182557, verkopen.txt: 1070, verteld.json: 292, woz.txt: 149
- **Huurdata**: 240 huurwaarnemingen, waarvan 51 Pararius en 100 Kamernet en 86 Huislijn en 3 Rentola, zonder adres maar met oppervlakte; 31 in de laatste week; 10 zonder oppervlakte, die tellen niet mee in de huur per m2; 9 waarschijnlijke dubbelingen tussen platforms samengevoegd
- **Aanbod**: 140 koopobjecten, 5 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,33% (2026-11-02), opslag bij 70% financiering 2,17 procentpunt
- **Bouwkostenindex**: 105 maanden, laatste 2026-09
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 8 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 975 panden in de ring, waarvan 216 alleen via een melding of besluit; meldingen per jaar: 2023: 13, 2024: 1, 2025: 102, 2026: 99
- **Woningprijsindex CBS**: landelijk 2026-09, Gelderland (PV) 2026-K3, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-29
- **Geschiedenis per pand**: 2250 panden gevolgd, 1882 met meer dan een gebeurtenis; 2035 met BAG-gegevens (7674 woningen, 8235 dubbel geteld zonder deze correctie), 1714 met een energielabel, 0 nog nooit nagekeken waarvan 257 na drie pogingen opgegeven; 20892 regels bespaard door gedeelde pandgegevens; 111 wachten nog op de telling van woningen apart van bergingen en garages; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 581 verkochte woningen verwerkt
- **Aanbodreeks**: 34 dagen gemeten; 2026-W43: 10 koop, 9 huur, 1 uitpond; 2026-W44: 8 koop, 6 huur; 2026-W45: 5 koop, 0 huur. In beeld: 1 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 43 panden in dertig dagen; mediaan 73 m2; 2 zonder label
- **Groottepremie**: 627 waarnemingen, 11 buurten met eigen ijkpunt; 0-40 m2: 1.42 (60), 40-60 m2: 1.218 (121), 60-80 m2: 1.069 (181), 80-100 m2: 1.0 (98), 100-130 m2: 0.962 (88), 130 m2 en groter: 0.925 (79)
- **Geplande startdagen**: 3 crons, samen zondag 1, maandag 2, dinsdag 2, woensdag 2, donderdag 2, vrijdag 2, zaterdag 2
- **Eisen aan de brief**: 127 eisen aan de brief, 121 afgedwongen door een proef, 6 bewust niet: Een pand dat al aan pa is verteld, opent de brief niet opnie; Een stap die zijn werk door git terugstuurt, meldt een mislu; Een proef die niets kan vinden, valt niet om met een KeyErro
- **Voltooide splitsingen**: 0 gerealiseerd; 1 zonder bekende vergunning; 60 aangekondigd met gevormde objecten, nog niet in gebruik; 1 vergund maar na een jaar nog niets in de BAG; en het tekstblok van vandaag staat er
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 57 dagen (173 panden, bovengrens); mediane bezitsduur 3.3 jaar (15 paren met een echte verkoopdatum, waarvan 3 op een jaar bij benadering); prijsgroei per pand nog niet te meten: 5 paren, minimaal 10 nodig
- **Voet onder de brief**: de voet staat boven de mail en de brief zonder verhaal
- **Feitencontrole van het verhaal**: voor de herstelronde 9 bevinding(en), erna 0
- **Duiding bij beleidsstukken**: geen beleid dat ons raakt vandaag
- **Beleid haalt de mail**: 2 beleidsstukken vandaag, alle 2 buiten ons onderwerp
- **Gepubliceerde regels bij de panden**: 1 regel in regelset.txt: wonen op de eerste bouwlaag binnenstad
- **Sleutels in de workflowstappen**: 9 workflows met 97 scriptstappen; 8 modules vragen samen 12 sleutels, en elke stap die ze aanroept geeft die mee
- **Verkooptijd bovengrens**: 77 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 123 dagen; alleen in onderhandeling: 32 panden, mediaan hoogstens 98 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 69 brieven bewaard, laatste van 2026-11-04 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €17.91/m2 uit 134 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -14%
- **Gemeubileerd**: 20 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 27 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 13 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: 3 nieuwbouwregels apart gehouden; die tellen niet mee in de mediaan per m2, de groottepremie of de aanbodreeks
- **Opnieuw aangeboden**: 44 adressen vaker aangeboden: 17 voor minder, 20 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; berg en dalseweg van €1100 naar €600
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW03: index 166.2, 4.3% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 11030 panden in de eigen snapshot, 11030 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-11-04
- **Achtergronddekking**: 39 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 32 brieven vastgelegd, laatste 2026-11-04; 613 onderwerpen bleven liggen
- **Dekking van onze signalen**: 675 van de 704 panden met een bekendmaking hebben BAG-gegevens (95%)
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 306 panden gerouteerd
- **Bekendmakingen-archief**: 737 adressen, 1329 publicaties
- **Veldenronde**: geen publicatie die mislukt (stand van 2026-11-03)
- **Regelgevingsmonitor**: 89 verordeningen, 5 wetten
- **Geheugen en trend**: 156 panden onthouden, prijstrend over 10 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

