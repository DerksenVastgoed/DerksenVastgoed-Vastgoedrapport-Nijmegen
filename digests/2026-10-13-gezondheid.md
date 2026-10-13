# Gezondheidsrapport 2026-10-13

54 in orde, 9 aandachtspunten, 2 fouten.

## FOUT
- **Bekende onwaarheden in de brief**: 1 bekende onwaarheid: in de marktanalyse: "Marialaan 56 €444.000 (2026), puntenstelsel ondergrens 140 punten (76 "
  Het woningwaarderingsstelsel kent geen bovengrens aan oppervlakte. Een grote woning krijgt juist veel punten en valt daarmee in de vrije sector, wat voor een verhuurder een voordeel is. De werkelijke reden dat opdelen loont is de gemeten groottepremie, en die staat in de gegevens.
- **Sleutels in de workflowstappen**: 1 stappen missen een sleutel: bekendmakingen.yml: Voltooide splitsingen uit de BAG mist EP_API_KEY voor voorraad_bag.py
  Zo'n stap draait wel en haalt niets op. Zet de sleutel in de env van die stap, zoals de andere stappen doen. Dit ging mis bij de twee voorraadstappen, die daardoor nooit een enkele BAG-aanroep hebben gedaan terwijl ze succes meldden.

## LET OP
- **Versies**: paklijst van 2026-10-10: 27 gelijk, 21 met andere inhoud, 0 niet aanwezig; andere inhoud dan de paklijst: .github/workflows/bekendmakingen.yml (65229 bytes, 1294 regels), .github/workflows/voorraad.yml (16820 bytes, 342 regels), aanbod_reeks.py (5847 bytes, 152 regels), aanbodprofiel.py (8098 bytes, 218 regels), bekendmakingen_archief.py (12003 bytes, 294 regels), bekendmakingen_nijmegen.py (56021 bytes, 1256 regels)
  Upload de ontbrekende bestanden. Blijft een bestand afwijken nadat het is geuploud, dan is de paklijst achter en moet die ververst worden.
- **Verkopen**: 661 verkopen: 518 geplakt, 143 met de hand; laatste 2026-10-13; de mailstap liet 206 meldingen vallen met dezelfde status en 11 met een andere (St. Stephanusstraat -> te huur) (Ijsvogelpassage -> te huur)
  Er komt nog geen verkoop uit de attendering, terwijl er wel 38 mails van funda.nl zijn gelezen. Het filter is dus niet de vraag; kijk naar wat de mailstap met die mails doet.
- **Voorraad van de ring**: 20045 woningen in de ring, 20045 met oppervlakte, 8419 met label; nog 6804 adressen te vragen; 2168 woningen onderweg, geregistreerd maar nog niet gereedgemeld; laatste ronde 3457 gevraagd, 2378 labels gevonden; 1 fouten in fase labels, laatste: Professor Terlingenstraat 10: netwerk: ('Connection aborted.', RemoteDisconnected('Remote end close
  Bij een geweigerde sleutel of een rem stopt de fase meteen en gaat hij de volgende run verder.
- **Plintobjecten geteld**: 1288 plintobjecten in heel Stadscentrum, 770 groot genoeg voor de volle 50 m2, 950 onder woningen; dit is heel Stadscentrum en niet alleen het kernwinkelgebied
  Zet de straatnamen van het kaartje in plintgebied.txt en dit wordt de werkelijke telling.
- **Huurdekking**: steekproef van 12 adressen elders: 7 kennen we al (58%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 550, pararius: 34, kamernet: 48, huislijn: 42, 123wonen: 0, rentola: 2; post maar geen waarneming van 123wonen (2 berichten)
  Bij 123wonen komt de post wel binnen maar lezen wij hem niet. Daar is de parser het probleem en niet de aanmelding.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 94 panden: correctie 0.984 (2% stelselmatig), spreiding ±21.1%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.9% (94), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+112%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-10-13: 123wonen: 2 mails, 0 objecten, 2 bewust overgeslagen; business: 1 mails, 0 objecten; huislijn: 13 mails, 47 objecten; kamernet: 93 mails, 51 objecten, 18 bewust overgeslagen; pararius: 27 mails, 37 objecten, 13 bewust overgeslagen; regulier: 37 mails, 86 objecten, 4 bewust overgeslagen; rentola: 4 mails, 2 objecten, 1 bewust overgeslagen; vendr: 4 mails, 0 objecten, 1 bewust overgeslagen
  Van business komen wel mails binnen maar het script haalt er niets uit; de opmaak is waarschijnlijk veranderd. Voorbeeld: business: niets herkend in: Maak een nieuw wachtwoord aan

## OK
- **Geheugen verstuurde brieven**: 15 onderwerpen bekend, 15 in het venster van drie weken, laatste brief 2026-10-13; 7 onderwerpen kwamen in meer dan een brief terug
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-10-12-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Samenstelling in plaats van markt**: alle buurten bewegen dezelfde kant op, de waarschuwing staat in de bijlage en de brief zegt het in eigen woorden: 5 van de 6 buurten gaan in deze 4 weken dezelfde kant op, omhoog, van -2,9% tot +9,9%, mediaan 6,0%.
- **Verkocht pand nog in het aanbod**: 11 panden hebben een verkoopregel die nieuwer is dan hun te-koopregel; geen van die panden staat nog in de aanbodtabel
- **Omvang van de gegevensbestanden**: bekendmakingen_archief.json: 4592, kamervergunningen.json: 7246, pandgeschiedenis.json: 143856, verkopen.txt: 927, verteld.json: 94, woz.txt: 123
- **Huurdata**: 126 huurwaarnemingen, waarvan 34 Pararius en 48 Kamernet en 42 Huislijn en 2 Rentola, zonder adres maar met oppervlakte; 45 in de laatste week; 7 zonder oppervlakte, die tellen niet mee in de huur per m2; 1 waarschijnlijke dubbelingen tussen platforms samengevoegd
- **Aanbod**: 111 koopobjecten, 1 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,51% (2026-10-09), opslag bij 70% financiering 1,99 procentpunt
- **Bouwkostenindex**: 104 maanden, laatste 2026-08
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 6 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 947 panden in de ring, waarvan 188 alleen via een melding of besluit; meldingen per jaar: 2025: 102, 2026: 86
- **Woningprijsindex CBS**: landelijk 2026-08, Gelderland (PV) 2026-K2, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-08
- **Geschiedenis per pand**: 1761 panden gevolgd, 1467 met meer dan een gebeurtenis; 1615 met BAG-gegevens (6719 woningen, 7540 dubbel geteld zonder deze correctie), 1403 met een energielabel, 0 nog nooit nagekeken waarvan 188 na drie pogingen opgegeven; 18937 regels bespaard door gedeelde pandgegevens; 55 wachten nog op de telling van woningen apart van bergingen en garages; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 581 verkochte woningen verwerkt
- **Veroudering aanbod**: 83 panden te koop, mediaan 24 dagen geleden voor het laatst bevestigd, oudste 42 dagen
- **Aanbodreeks**: 12 dagen gemeten; 2026-W40: 8 koop, 9 huur, 2 uitpond; 2026-W41: 6 koop, 34 huur, 1 uitpond; 2026-W42: 1 koop, 3 huur. In beeld: 3 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 57 panden in dertig dagen; mediaan 82 m2; 0 zonder label
- **Groottepremie**: 598 waarnemingen, 9 buurten met eigen ijkpunt; 0-40 m2: 1.44 (57), 40-60 m2: 1.229 (112), 60-80 m2: 1.059 (170), 80-100 m2: 1.0 (91), 100-130 m2: 0.954 (89), 130 m2 en groter: 0.927 (79)
- **Woningen in bestaande panden**: 113 panden met 697 gevormde woningen erin; laatste ronde 15 nieuwe records, 25 gebeurtenissen, 63 wachten op een volgende ronde (stand van 2026-10-13)
- **Geplande startdagen**: 3 crons, samen zondag 1, maandag 2, dinsdag 2, woensdag 2, donderdag 2, vrijdag 2, zaterdag 2
- **Eisen aan de brief**: 34 eisen aan de brief, 29 afgedwongen door een proef, 5 bewust niet: Een pand dat al aan pa is verteld, opent de brief niet opnie; Een stap die zijn werk door git terugstuurt, meldt een mislu; Een proef die niets kan vinden, valt niet om met een KeyErro
- **Voltooide splitsingen**: 2 gerealiseerd; mediaan 3 dagen van besluit tot registratie (2); 14 vergund maar na een jaar nog niets in de BAG; 2 met een ander aantal dan de vergunning noemt; en het tekstblok van vandaag staat er
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 82 dagen (129 panden, bovengrens); mediane bezitsduur 3.3 jaar (15 paren met een echte verkoopdatum, waarvan 3 op een jaar bij benadering); prijsgroei per pand nog niet te meten: 5 paren, minimaal 10 nodig
- **Voet onder de brief**: de voet staat boven de mail en de brief zonder verhaal
- **Duiding bij beleidsstukken**: geen beleid dat ons raakt vandaag
- **Beleid haalt de mail**: geen beleidsstuk vandaag gepubliceerd
- **Gepubliceerde regels bij de panden**: 1 regel in regelset.txt: wonen op de eerste bouwlaag binnenstad
- **Verkooptijd bovengrens**: 80 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 123 dagen; alleen in onderhandeling: 33 panden, mediaan hoogstens 89 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 47 brieven bewaard, laatste van 2026-10-13 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €18.16/m2 uit 72 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -13%
- **Gemeubileerd**: 11 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 1 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 7 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: 3 nieuwbouwregels apart gehouden; die tellen niet mee in de mediaan per m2, de groottepremie of de aanbodreeks
- **Opnieuw aangeboden**: 23 adressen vaker aangeboden: 9 voor minder, 12 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; krayenhofflaan van €864 naar €713
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW02: index 164.1, 4.5% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 1293 panden in de eigen snapshot, 1293 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-10-13
- **Achtergronddekking**: 36 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 11 brieven vastgelegd, laatste 2026-10-13; 193 onderwerpen bleven liggen
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 213 panden gerouteerd
- **Bekendmakingen-archief**: 345 adressen, 479 publicaties
- **Regelgevingsmonitor**: 80 verordeningen, 5 wetten
- **Geheugen en trend**: 122 panden onthouden, prijstrend over 9 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

