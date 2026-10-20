# Gezondheidsrapport 2026-10-20

61 in orde, 7 aandachtspunten, 0 fouten.

## LET OP
- **Verkopen**: 661 verkopen: 518 geplakt, 143 met de hand; laatste 2026-10-13; de mailstap liet 32 meldingen vallen met dezelfde status en 0 met een andere
  Er komt nog geen verkoop uit de attendering, terwijl er wel 2 mails van funda.nl zijn gelezen. Het filter is dus niet de vraag; kijk naar wat de mailstap met die mails doet.
- **Plintobjecten geteld**: 1288 plintobjecten in heel Stadscentrum, 770 groot genoeg voor de volle 50 m2, 950 onder woningen; dit is heel Stadscentrum en niet alleen het kernwinkelgebied
  Zet de straatnamen van het kaartje in plintgebied.txt en dit wordt de werkelijke telling.
- **Huurdekking**: steekproef van 12 adressen elders: 6 kennen we al (50%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 549, pararius: 40, kamernet: 71, huislijn: 61, 123wonen: 0, rentola: 2; geen post van 123wonen
  Bij 123wonen staat de attendering niet aan of stuurt die partij van een ander domein dan in AFZENDERS staat. Dat was bij Huislijn het geval: die stuurde van huisly.nl. Kijk in de mailbox van wie die post komt.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 94 panden: correctie 0.988 (1% stelselmatig), spreiding ±21.1%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.9% (94), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+111%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-10-20: huislijn: 4 mails, 12 objecten; kamernet: 14 mails, 13 objecten, 1 bewust overgeslagen; pararius: 2 mails, 4 objecten, 4 bewust overgeslagen; regulier: 2 mails, 3 objecten, 2 bewust overgeslagen; de mailboxtelling mislukte ((SINCE 17-Oct-2026): error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED; SINCE 17-Oct-2026: error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED)
  Van funda kwam geen enkele mail. Staat de attendering aan en komt hij in deze mailbox binnen?

## OK
- **Versies**: code uit commit 9b4db91, in één keer uitgecheckt; een halve upload kan hier niet bestaan
- **Geheugen verstuurde brieven**: 26 onderwerpen bekend, 26 in het venster van drie weken, laatste brief 2026-10-19; 16 onderwerpen kwamen in meer dan een brief terug
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-10-19-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Bekende onwaarheden in de brief**: 6 bekende onwaarheden getoetst op 5 teksten, geen ervan komt voor
- **Samenstelling in plaats van markt**: alle buurten bewegen dezelfde kant op, de schrijver kreeg de waarschuwing en de brief zegt het in eigen woorden: 5 van de 6 buurten met een reeks over 4 weken (Hunnerberg en St. Anna nog zonder) gaan dezelfde kant op, omhoog, van -2,3% tot +9,7%, mediaan 5,9%.
- **Verkocht pand nog in het aanbod**: 7 panden hebben een verkoopregel die nieuwer is dan hun te-koopregel; geen van die panden staat nog in de aanbodtabel
- **Omvang van de gegevensbestanden**: bekendmakingen_archief.json: 11896, kamervergunningen.json: 7246, pandgeschiedenis.json: 177196, verkopen.txt: 975, verteld.json: 160, woz.txt: 130
- **Huurdata**: 174 huurwaarnemingen, waarvan 40 Pararius en 71 Kamernet en 61 Huislijn en 2 Rentola, zonder adres maar met oppervlakte; 56 in de laatste week; 9 zonder oppervlakte, die tellen niet mee in de huur per m2; 8 waarschijnlijke dubbelingen tussen platforms samengevoegd
- **Aanbod**: 111 koopobjecten, 3 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,47% (2026-10-19), opslag bij 70% financiering 2,03 procentpunt
- **Bouwkostenindex**: 104 maanden, laatste 2026-08
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 8 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 970 panden in de ring, waarvan 211 alleen via een melding of besluit; meldingen per jaar: 2023: 13, 2024: 1, 2025: 102, 2026: 90
- **Woningprijsindex CBS**: landelijk 2026-08, Gelderland (PV) 2026-K2, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-15
- **Geschiedenis per pand**: 2167 panden gevolgd, 1814 met meer dan een gebeurtenis; 1988 met BAG-gegevens (7588 woningen, 7822 dubbel geteld zonder deze correctie), 1671 met een energielabel, 0 nog nooit nagekeken waarvan 188 na drie pogingen opgegeven; 19776 regels bespaard door gedeelde pandgegevens; 107 wachten nog op de telling van woningen apart van bergingen en garages; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
  Geen enkel pand kwam in aanmerking voor de BAG-controle. Draait de stap wel met --volledig, en hebben de panden een gebeurtenis van het juiste soort?
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 581 verkochte woningen verwerkt
- **Veroudering aanbod**: 82 panden te koop, mediaan 27 dagen geleden voor het laatst bevestigd, oudste 48 dagen
- **Aanbodreeks**: 19 dagen gemeten; 2026-W41: 6 koop, 34 huur, 1 uitpond; 2026-W42: 7 koop, 28 huur; 2026-W43: 2 koop, 9 huur. In beeld: 3 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 47 panden in dertig dagen; mediaan 83 m2; 1 zonder label
- **Groottepremie**: 598 waarnemingen, 11 buurten met eigen ijkpunt; 0-40 m2: 1.425 (58), 40-60 m2: 1.227 (114), 60-80 m2: 1.061 (172), 80-100 m2: 1.0 (90), 100-130 m2: 0.966 (86), 130 m2 en groter: 0.925 (78)
- **Woningen in bestaande panden**: 139 panden met 765 gevormde woningen erin; laatste ronde 0 nieuwe records, 0 gebeurtenissen, 0 wachten op een volgende ronde (stand van 2026-10-20)
- **Geplande startdagen**: 3 crons, samen zondag 1, maandag 2, dinsdag 2, woensdag 2, donderdag 2, vrijdag 2, zaterdag 2
- **Eisen aan de brief**: 111 eisen aan de brief, 105 afgedwongen door een proef, 6 bewust niet: Een pand dat al aan pa is verteld, opent de brief niet opnie; Een stap die zijn werk door git terugstuurt, meldt een mislu; Een proef die niets kan vinden, valt niet om met een KeyErro
- **Voltooide splitsingen**: 0 gerealiseerd; 57 aangekondigd met gevormde objecten, nog niet in gebruik; 1 vergund maar na een jaar nog niets in de BAG; en het tekstblok van vandaag staat er
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 57 dagen (173 panden, bovengrens); mediane bezitsduur 3.3 jaar (15 paren met een echte verkoopdatum, waarvan 3 op een jaar bij benadering); prijsgroei per pand nog niet te meten: 5 paren, minimaal 10 nodig
- **Voorraad van de ring**: 23903 woningen in de ring, 23903 met oppervlakte, 16554 met label; nog 0 adressen te vragen; 521 adressen buiten de ring bewaard omdat er een bekendmaking over ging; 2343 woningen onderweg, geregistreerd maar nog niet gereedgemeld
- **Voet onder de brief**: de voet staat boven de mail en de brief zonder verhaal
- **Feitencontrole van het verhaal**: voor de herstelronde 9 bevinding(en), erna 0
- **Duiding bij beleidsstukken**: geen beleid dat ons raakt vandaag
- **Beleid haalt de mail**: 1 beleidsstukken vandaag, alle 1 buiten ons onderwerp
- **Gepubliceerde regels bij de panden**: 1 regel in regelset.txt: wonen op de eerste bouwlaag binnenstad
- **Sleutels in de workflowstappen**: 8 workflows met 90 scriptstappen; 8 modules vragen samen 12 sleutels, en elke stap die ze aanroept geeft die mee
- **Verkooptijd bovengrens**: 77 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 123 dagen; alleen in onderhandeling: 32 panden, mediaan hoogstens 98 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 54 brieven bewaard, laatste van 2026-10-20 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €18.00/m2 uit 99 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -14%
- **Gemeubileerd**: 16 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 8 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 6 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: 3 nieuwbouwregels apart gehouden; die tellen niet mee in de mediaan per m2, de groottepremie of de aanbodreeks
- **Opnieuw aangeboden**: 28 adressen vaker aangeboden: 10 voor minder, 16 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; krayenhofflaan van €864 naar €713
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW02: index 164.1, 4.5% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 11014 panden in de eigen snapshot, 11014 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-10-20
- **Achtergronddekking**: 39 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 17 brieven vastgelegd, laatste 2026-10-19; 342 onderwerpen bleven liggen
- **Overgeslagen stappen**: geen stap overgeslagen
- **Dekking van onze signalen**: 650 van de 676 panden met een bekendmaking hebben BAG-gegevens (96%)
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 249 panden gerouteerd
- **Bekendmakingen-archief**: 709 adressen, 1291 publicaties
- **Regelgevingsmonitor**: 89 verordeningen, 5 wetten
- **Geheugen en trend**: 130 panden onthouden, prijstrend over 10 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

