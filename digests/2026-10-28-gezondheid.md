# Gezondheidsrapport 2026-10-28

61 in orde, 8 aandachtspunten, 0 fouten.

## LET OP
- **Verkopen**: 661 verkopen: 518 geplakt, 143 met de hand; laatste 2026-10-13; de mailstap liet 13 meldingen vallen met dezelfde status en 0 met een andere
  Er komt nog geen verkoop uit de attendering, terwijl er wel 1 mails van funda.nl zijn gelezen. Het filter is dus niet de vraag; kijk naar wat de mailstap met die mails doet.
- **Woningen in bestaande panden**: 141 panden met 767 gevormde woningen erin; laatste ronde 1 nieuwe records, 1 gebeurtenissen, 0 wachten op een volgende ronde (stand van 2026-10-28); 1 panden met een sleutel die al van een ander pand is
  Die panden krijgen geen record, want een opzoeking mag nooit bij de buren uitkomen. Ze worden dus niet gemeld.
- **Plintobjecten geteld**: 1288 plintobjecten in heel Stadscentrum, 770 groot genoeg voor de volle 50 m2, 950 onder woningen; dit is heel Stadscentrum en niet alleen het kernwinkelgebied
  Zet de straatnamen van het kaartje in plintgebied.txt en dit wordt de werkelijke telling.
- **Huurdekking**: steekproef van 12 adressen elders: 6 kennen we al (50%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 561, pararius: 42, kamernet: 87, huislijn: 77, 123wonen: 0, rentola: 3; geen post van 123wonen
  Bij 123wonen staat de attendering niet aan of stuurt die partij van een ander domein dan in AFZENDERS staat. Dat was bij Huislijn het geval: die stuurde van huisly.nl. Kijk in de mailbox van wie die post komt.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 94 panden: correctie 0.985 (1% stelselmatig), spreiding ±20.9%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.9% (94), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+111%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-10-28: huislijn: 3 mails, 9 objecten; kamernet: 12 mails, 8 objecten, 4 bewust overgeslagen; pararius: 1 mails, 1 objecten, 1 bewust overgeslagen; regulier: 1 mails, 2 objecten; de mailboxtelling mislukte ((SINCE 25-Oct-2026): error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED; SINCE 25-Oct-2026: error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED)
  Van funda kwam geen enkele mail. Staat de attendering aan en komt hij in deze mailbox binnen?

## OK
- **Versies**: code uit commit e4a276d, in één keer uitgecheckt; een halve upload kan hier niet bestaan
- **Geheugen verstuurde brieven**: 39 onderwerpen bekend, 39 in het venster van drie weken, laatste brief 2026-10-28; 21 onderwerpen kwamen in meer dan een brief terug
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-10-27-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Bekende onwaarheden in de brief**: 6 bekende onwaarheden getoetst op 5 teksten, geen ervan komt voor
- **Samenstelling in plaats van markt**: de buurten bewegen niet allemaal dezelfde kant op; geen waarschuwing nodig
- **Verkocht pand nog in het aanbod**: 7 panden hebben een verkoopregel die nieuwer is dan hun te-koopregel; geen van die panden staat nog in de aanbodtabel
- **Omvang van de gegevensbestanden**: bekendmakingen_archief.json: 12108, kamervergunningen.json: 7246, pandgeschiedenis.json: 180198, verkopen.txt: 1022, verteld.json: 238, woz.txt: 140
- **Huurdata**: 209 huurwaarnemingen, waarvan 42 Pararius en 87 Kamernet en 77 Huislijn en 3 Rentola, zonder adres maar met oppervlakte; 35 in de laatste week; 10 zonder oppervlakte, die tellen niet mee in de huur per m2; 11 waarschijnlijke dubbelingen tussen platforms samengevoegd
- **Aanbod**: 123 koopobjecten, 2 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,37% (2026-10-26), opslag bij 70% financiering 2,13 procentpunt
- **Bouwkostenindex**: 104 maanden, laatste 2026-08
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 8 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 973 panden in de ring, waarvan 214 alleen via een melding of besluit; meldingen per jaar: 2023: 13, 2024: 1, 2025: 102, 2026: 94
- **Woningprijsindex CBS**: landelijk 2026-09, Gelderland (PV) 2026-K3, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-22
- **Geschiedenis per pand**: 2207 panden gevolgd, 1847 met meer dan een gebeurtenis; 2010 met BAG-gegevens (7632 woningen, 8048 dubbel geteld zonder deze correctie), 1689 met een energielabel, 0 nog nooit nagekeken waarvan 239 na drie pogingen opgegeven; 20418 regels bespaard door gedeelde pandgegevens; 110 wachten nog op de telling van woningen apart van bergingen en garages; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 581 verkochte woningen verwerkt
- **Veroudering aanbod**: 92 panden te koop, mediaan 31 dagen geleden voor het laatst bevestigd, oudste 56 dagen
- **Aanbodreeks**: 27 dagen gemeten; 2026-W42: 7 koop, 28 huur; 2026-W43: 10 koop, 9 huur, 1 uitpond; 2026-W44: 0 koop, 0 huur. In beeld: 2 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 40 panden in dertig dagen; mediaan 74 m2; 1 zonder label
- **Groottepremie**: 610 waarnemingen, 11 buurten met eigen ijkpunt; 0-40 m2: 1.415 (59), 40-60 m2: 1.216 (119), 60-80 m2: 1.059 (175), 80-100 m2: 1.0 (91), 100-130 m2: 0.959 (87), 130 m2 en groter: 0.917 (79)
- **Geplande startdagen**: 3 crons, samen zondag 1, maandag 2, dinsdag 2, woensdag 2, donderdag 2, vrijdag 2, zaterdag 2
- **Eisen aan de brief**: 127 eisen aan de brief, 121 afgedwongen door een proef, 6 bewust niet: Een pand dat al aan pa is verteld, opent de brief niet opnie; Een stap die zijn werk door git terugstuurt, meldt een mislu; Een proef die niets kan vinden, valt niet om met een KeyErro
- **Voltooide splitsingen**: 0 gerealiseerd; 58 aangekondigd met gevormde objecten, nog niet in gebruik; 1 vergund maar na een jaar nog niets in de BAG; en het tekstblok van vandaag staat er
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 57 dagen (173 panden, bovengrens); mediane bezitsduur 3.3 jaar (15 paren met een echte verkoopdatum, waarvan 3 op een jaar bij benadering); prijsgroei per pand nog niet te meten: 5 paren, minimaal 10 nodig
- **Voorraad van de ring**: 23903 woningen in de ring, 23903 met oppervlakte, 16554 met label; nog 0 adressen te vragen; 529 adressen buiten de ring bewaard omdat er een bekendmaking over ging; 2346 woningen onderweg, geregistreerd maar nog niet gereedgemeld
- **Voet onder de brief**: de voet staat boven de mail en de brief zonder verhaal
- **Feitencontrole van het verhaal**: voor de herstelronde 8 bevinding(en), erna 0
- **Duiding bij beleidsstukken**: geen beleid dat ons raakt vandaag
- **Beleid haalt de mail**: geen beleidsstuk vandaag gepubliceerd
- **Gepubliceerde regels bij de panden**: 1 regel in regelset.txt: wonen op de eerste bouwlaag binnenstad
- **Sleutels in de workflowstappen**: 9 workflows met 97 scriptstappen; 8 modules vragen samen 12 sleutels, en elke stap die ze aanroept geeft die mee
- **Verkooptijd bovengrens**: 77 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 123 dagen; alleen in onderhandeling: 32 panden, mediaan hoogstens 98 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 62 brieven bewaard, laatste van 2026-10-28 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €17.91/m2 uit 116 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -14%
- **Gemeubileerd**: 17 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 18 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 6 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: 3 nieuwbouwregels apart gehouden; die tellen niet mee in de mediaan per m2, de groottepremie of de aanbodreeks
- **Opnieuw aangeboden**: 38 adressen vaker aangeboden: 15 voor minder, 17 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; berg en dalseweg van €1100 naar €428
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW03: index 166.2, 4.3% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 11022 panden in de eigen snapshot, 11022 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-10-28
- **Achtergronddekking**: 39 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 25 brieven vastgelegd, laatste 2026-10-28; 454 onderwerpen bleven liggen
- **Overgeslagen stappen**: geen stap overgeslagen
- **Dekking van onze signalen**: 663 van de 691 panden met een bekendmaking hebben BAG-gegevens (95%)
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 276 panden gerouteerd
- **Bekendmakingen-archief**: 723 adressen, 1314 publicaties
- **Veldenronde**: geen publicatie die mislukt (stand van 2026-10-27)
- **Regelgevingsmonitor**: 89 verordeningen, 5 wetten
- **Geheugen en trend**: 140 panden onthouden, prijstrend over 10 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

