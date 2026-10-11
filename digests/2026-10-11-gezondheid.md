# Gezondheidsrapport 2026-10-11

53 in orde, 9 aandachtspunten, 0 fouten.

## LET OP
- **Versies**: paklijst van 2026-10-10: 42 gelijk, 6 met andere inhoud, 0 niet aanwezig; andere inhoud dan de paklijst: .github/workflows/bekendmakingen.yml (56165 bytes, 1145 regels), .github/workflows/voorraad.yml (7553 bytes, 179 regels), buurtinventaris.py (20478 bytes, 464 regels), gezondheid.py (158361 bytes, 3326 regels), plintregel.py (24977 bytes, 533 regels), voorraad_bag.py (71315 bytes, 1516 regels)
  Upload de ontbrekende bestanden. Blijft een bestand afwijken nadat het is geuploud, dan is de paklijst achter en moet die ververst worden.
- **Verkopen**: 505 verkopen: 505 geplakt; laatste 2026-09-28
  Er komt nog geen enkele verkoop uit de attendering. Controleer of het filter op verkocht daar echt aan staat.
- **Voorraad van de ring**: 22096 woningen in de ring, 22096 met oppervlakte, 0 met label; nog 21293 adressen te vragen; laatste ronde 818 gevraagd, 0 labels gevonden; 15 fouten in fase labels, laatste: Bachstraat 29A-24: HTTP 400; de objectronde is van 2026-10-10 en niet van vandaag; de pandronde is van 2026-10-10 en niet van vandaag; 491 lege postcodes in de inventaris liggen niet in Nijmegen; 2238 van de 22096 objecten hebben status gevormd en zijn nog niet in gebruik gemeld
  Bij een geweigerde sleutel of een rem stopt de fase meteen en gaat hij de volgende run verder. De stap is overgeslagen of mislukt. De cijfers hieronder zijn dus die van de laatste geslaagde ronde, en de voorraad is zo oud als die datum. De stap is overgeslagen of mislukt. De cijfers hieronder zijn dus die van de laatste geslaagde ronde, en de voorraad is zo oud als die datum. buurtinventaris.py filtert op buurtnaam zonder gemeente erbij, en die buurtnamen bestaan elders ook. Gemeten op 10 oktober: 491 van de 1.733 postcodes, namelijk 2771 Boskoop, 3431 Nieuwegein, 3828 Amersfoort, 4131 Vianen, 4201 Gorinchem, 5103 Dongen, 7001 Doetinchem en 9401 Assen. Altrade en Bottendaal zijn als buurtnaam uniek voor Nijmegen en hebben nul vervuiling; de andere vier hebben het wel. De voorraad zelf kan er niet door vervuilen, want de doos ligt om Nijmegen, maar alles wat verder op de inventaris rekent telt ze mee. Ze worden meegeteld. Die status betekent dat het object in de registratie is gevormd maar niet als in gebruik is gemeld, en dat is in de praktijk vaak een gewone woning waarvan de status nooit is bijgewerkt. Ze eruit halen zou de voorraad ruim een tiende kleiner maken, dus dat hoort niet op een vermoeden te gebeuren. Te zeven is het altijd nog: de status staat per record in voorraad.json.
- **Plintobjecten geteld**: 1284 plintobjecten in heel Stadscentrum, 769 groot genoeg voor de volle 50 m2, 989 onder woningen; 336 van 337 postcodes opgehaald, dus dit loopt nog op
- **Huurdekking**: steekproef van 12 adressen elders: 5 kennen we al (42%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 528, pararius: 30, kamernet: 46, huislijn: 37, 123wonen: 0, rentola: 2; geen enkele waarneming van: 123wonen
  Of er van die partij werkelijk post komt, is nog niet gemeten; dat staat in de volgende mailstand. Tot dan: controleer of de attendering aanstaat en of het afzenderdomein in AFZENDERS klopt.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 104 panden: correctie 0.988 (1% stelselmatig), spreiding ±19.7%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.3% (104), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+111%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-10-10: huislijn: 4 mails, 22 objecten; kamernet: 12 mails, 8 objecten, 4 bewust overgeslagen; pararius: 3 mails, 7 objecten, 2 bewust overgeslagen; regulier: 4 mails, 8 objecten, 1 bewust overgeslagen; rentola: 2 mails, 2 objecten, 1 bewust overgeslagen
  Van funda kwam geen enkele mail. Staat de attendering aan en komt hij in deze mailbox binnen?

## OK
- **Geheugen verstuurde brieven**: 9 onderwerpen bekend, 9 in het venster van drie weken, laatste brief 2026-10-09
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-10-10-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Bekende onwaarheden in de brief**: 6 bekende onwaarheden getoetst op 5 teksten, geen ervan komt voor
- **Samenstelling in plaats van markt**: alle buurten bewegen dezelfde kant op, de waarschuwing staat in de bijlage en de brief zegt het in eigen woorden: 5 van de 5 buurten gaan in deze 4 weken dezelfde kant op, omhoog, van +4,1% tot +8,9%, mediaan 6,0%.
- **Verkocht pand nog in het aanbod**: geen pand dat zowel verkocht is als te koop staat
- **Omvang van de gegevensbestanden**: bekendmakingen_archief.json: 4552, kamervergunningen.json: 7246, pandgeschiedenis.json: 115203, verkopen.txt: 894, verteld.json: 58, woz.txt: 122
- **Huurdata**: 115 huurwaarnemingen, waarvan 30 Pararius en 46 Kamernet en 37 Huislijn en 2 Rentola, zonder adres maar met oppervlakte; 54 in de laatste week; 6 zonder oppervlakte, die tellen niet mee in de huur per m2; 1 waarschijnlijke dubbelingen tussen platforms samengevoegd
- **Aanbod**: 102 koopobjecten, 4 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,52% (2026-10-08), opslag bij 70% financiering 1,98 procentpunt
- **Bouwkostenindex**: 104 maanden, laatste 2026-08
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 6 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 951 panden in de ring, waarvan 192 alleen via een melding of besluit; meldingen per jaar: 2025: 102, 2026: 85
- **Woningprijsindex CBS**: landelijk 2026-08, Gelderland (PV) 2026-K2, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-08
- **Geschiedenis per pand**: 1777 panden gevolgd, 1430 met meer dan een gebeurtenis; 1582 met BAG-gegevens (6349 woningen, 7446 dubbel geteld zonder deze correctie), 1384 met een energielabel, 0 nog nooit nagekeken waarvan 191 na drie pogingen opgegeven; 12222 regels bespaard door gedeelde pandgegevens; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 575 verkochte woningen verwerkt
- **Veroudering aanbod**: 74 panden te koop, mediaan 19 dagen geleden voor het laatst bevestigd, oudste 39 dagen
- **Aanbodreeks**: 10 dagen gemeten; 2026-W40: 8 koop, 9 huur, 2 uitpond; 2026-W41: 6 koop, 34 huur, 1 uitpond. In beeld: 3 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 67 panden in dertig dagen; mediaan 89 m2; 0 zonder label
- **Groottepremie**: 576 waarnemingen, 9 buurten met eigen ijkpunt; 0-40 m2: 1.431 (56), 40-60 m2: 1.242 (110), 60-80 m2: 1.068 (168), 80-100 m2: 1.0 (86), 100-130 m2: 0.972 (83), 130 m2 en groter: 0.912 (73)
- **Voltooide splitsingen**: 1 gerealiseerd; mediaan 1 dagen van besluit tot registratie (1); 1 zonder bekende vergunning; 12 vergund maar na een jaar nog niets in de BAG; en het tekstblok van vandaag staat er
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 93 dagen (118 panden, bovengrens); mediane bezitsduur 3.3 jaar (15 paren met een echte verkoopdatum, waarvan 3 op een jaar bij benadering); prijsgroei per pand nog niet te meten: 5 paren, minimaal 10 nodig
- **Voet onder de brief**: de voet staat boven de mail en de brief zonder verhaal
- **Duiding bij beleidsstukken**: geen beleid dat ons raakt vandaag
- **Beleid haalt de mail**: geen beleidsstuk vandaag gepubliceerd
- **Gepubliceerde regels bij de panden**: 1 regel in regelset.txt: wonen op de eerste bouwlaag binnenstad
- **Sleutels in de workflowstappen**: yaml niet beschikbaar, stappen niet te toetsen
- **Verkooptijd bovengrens**: 73 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 129 dagen; alleen in onderhandeling: 37 panden, mediaan hoogstens 88 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 45 brieven bewaard, laatste van 2026-10-11 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €17.35/m2 uit 63 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -17%
- **Gemeubileerd**: 7 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 0 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 6 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: 3 nieuwbouwregels apart gehouden; die tellen niet mee in de mediaan per m2, de groottepremie of de aanbodreeks
- **Opnieuw aangeboden**: 20 adressen vaker aangeboden: 8 voor minder, 12 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; krayenhofflaan van €864 naar €713
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW02: index 164.1, 4.5% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 1259 panden in de eigen snapshot, 1259 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-10-11
- **Achtergronddekking**: 36 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 8 brieven vastgelegd, laatste 2026-10-09; 128 onderwerpen bleven liggen
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 208 panden gerouteerd
- **Bekendmakingen-archief**: 341 adressen, 475 publicaties
- **Regelgevingsmonitor**: 80 verordeningen, 5 wetten
- **Geheugen en trend**: 122 panden onthouden, prijstrend over 9 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

