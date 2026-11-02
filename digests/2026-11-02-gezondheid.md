# Gezondheidsrapport 2026-11-02

59 in orde, 9 aandachtspunten, 1 fouten.

## FOUT
- **Overgeslagen stappen**: 1 stap(pen) overgeslagen: Marktprijzen
  Deze stappen zijn vandaag mislukt. Wat zij opleveren staat niet in de brief van vandaag. De reden staat in het joblogboek van de run, dat alleen in de browser te openen is.

## LET OP
- **Verkopen**: 661 verkopen: 518 geplakt, 143 met de hand; laatste 2026-10-13; de mailstap liet 19 meldingen vallen met dezelfde status en 0 met een andere
  Er komt nog geen verkoop uit de attendering, terwijl er wel 2 mails van funda.nl zijn gelezen. Het filter is dus niet de vraag; kijk naar wat de mailstap met die mails doet.
- **Veroudering aanbod**: 103 panden te koop, mediaan 34 dagen geleden voor het laatst bevestigd, oudste 61 dagen, 2 langer dan 60 dagen
  Die panden zijn waarschijnlijk al van de markt; ze blijven staan omdat de attendering alleen nieuw aanbod meldt. Een geplakte verkooplijst haalt ze eruit.
- **Woningen in bestaande panden**: 144 panden met 777 gevormde woningen erin; laatste ronde 0 nieuwe records, 0 gebeurtenissen, 0 wachten op een volgende ronde (stand van 2026-11-02); 1 panden met een sleutel die al van een ander pand is
  Die panden krijgen geen record, want een opzoeking mag nooit bij de buren uitkomen. Ze worden dus niet gemeld.
- **Plintobjecten geteld**: 1288 plintobjecten in heel Stadscentrum, 770 groot genoeg voor de volle 50 m2, 950 onder woningen; dit is heel Stadscentrum en niet alleen het kernwinkelgebied
  Zet de straatnamen van het kaartje in plintgebied.txt en dit wordt de werkelijke telling.
- **Huurdekking**: steekproef van 12 adressen elders: 6 kennen we al (50%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 573, pararius: 50, kamernet: 92, huislijn: 86, 123wonen: 0, rentola: 3; geen post van 123wonen
  Bij 123wonen staat de attendering niet aan of stuurt die partij van een ander domein dan in AFZENDERS staat. Dat was bij Huislijn het geval: die stuurde van huisly.nl. Kijk in de mailbox van wie die post komt.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 94 panden: correctie 0.985 (1% stelselmatig), spreiding ±20.9%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.9% (94), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+111%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-11-02: huislijn: 2 mails, 6 objecten; kamernet: 7 mails, 4 objecten, 3 bewust overgeslagen; pararius: 2 mails, 3 objecten, 1 bewust overgeslagen; regulier: 2 mails, 7 objecten, 1 bewust overgeslagen; vendr: 1 mails, 0 objecten; de mailboxtelling mislukte ((SINCE 30-Oct-2026): error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED; SINCE 30-Oct-2026: error: command SEARCH illegal in state LOGOUT, only allowed in states SELECTED)
  Van vendr komen wel mails binnen maar het script haalt er niets uit; de opmaak is waarschijnlijk veranderd. Voorbeeld: vendr: niets herkend in: Nieuwe projecten op Vendr

## OK
- **Versies**: code uit commit fa3ed24, in één keer uitgecheckt; een halve upload kan hier niet bestaan
- **Geheugen verstuurde brieven**: 45 onderwerpen bekend, 41 in het venster van drie weken, laatste brief 2026-11-02; 23 onderwerpen kwamen in meer dan een brief terug
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-11-01-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Bekende onwaarheden in de brief**: 6 bekende onwaarheden getoetst op 5 teksten, geen ervan komt voor
- **Samenstelling in plaats van markt**: de buurten bewegen niet allemaal dezelfde kant op; geen waarschuwing nodig
- **Verkocht pand nog in het aanbod**: 7 panden zijn na het aanbod verkocht; geen aanbodtabel van vandaag om tegen te toetsen
- **Omvang van de gegevensbestanden**: bekendmakingen_archief.json: 12198, kamervergunningen.json: 7246, pandgeschiedenis.json: 181965, verkopen.txt: 1056, verteld.json: 274, woz.txt: 148
- **Huurdata**: 231 huurwaarnemingen, waarvan 50 Pararius en 92 Kamernet en 86 Huislijn en 3 Rentola, zonder adres maar met oppervlakte; 31 in de laatste week; 10 zonder oppervlakte, die tellen niet mee in de huur per m2; 8 waarschijnlijke dubbelingen tussen platforms samengevoegd
- **Aanbod**: 135 koopobjecten, 7 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,37% (2026-10-29), opslag bij 70% financiering 2,13 procentpunt
- **Bouwkostenindex**: 105 maanden, laatste 2026-09
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 8 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 973 panden in de ring, waarvan 214 alleen via een melding of besluit; meldingen per jaar: 2023: 13, 2024: 1, 2025: 102, 2026: 94
- **Woningprijsindex CBS**: landelijk 2026-09, Gelderland (PV) 2026-K3, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-29
- **Geschiedenis per pand**: 2238 panden gevolgd, 1875 met meer dan een gebeurtenis; 2029 met BAG-gegevens (7668 woningen, 8182 dubbel geteld zonder deze correctie), 1708 met een energielabel, 0 nog nooit nagekeken waarvan 257 na drie pogingen opgegeven; 20748 regels bespaard door gedeelde pandgegevens; 111 wachten nog op de telling van woningen apart van bergingen en garages; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
  Van 1 bekeken panden leverde er geen een pand-id op. Waarschijnlijk komt het adres niet door de BAG-opzoeking, of ontbreekt de sleutel in deze stap.
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 581 verkochte woningen verwerkt
- **Aanbodreeks**: 32 dagen gemeten; 2026-W43: 10 koop, 9 huur, 1 uitpond; 2026-W44: 8 koop, 6 huur; 2026-W45: 0 koop, 0 huur. In beeld: 1 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 41 panden in dertig dagen; mediaan 73 m2; 2 zonder label
- **Groottepremie**: 622 waarnemingen, 11 buurten met eigen ijkpunt; 0-40 m2: 1.414 (59), 40-60 m2: 1.216 (121), 60-80 m2: 1.063 (180), 80-100 m2: 1.0 (95), 100-130 m2: 0.959 (88), 130 m2 en groter: 0.916 (79)
- **Geplande startdagen**: 3 crons, samen zondag 1, maandag 2, dinsdag 2, woensdag 2, donderdag 2, vrijdag 2, zaterdag 2
- **Eisen aan de brief**: 127 eisen aan de brief, 121 afgedwongen door een proef, 6 bewust niet: Een pand dat al aan pa is verteld, opent de brief niet opnie; Een stap die zijn werk door git terugstuurt, meldt een mislu; Een proef die niets kan vinden, valt niet om met een KeyErro
- **Voltooide splitsingen**: 0 gerealiseerd; 1 zonder bekende vergunning; 60 aangekondigd met gevormde objecten, nog niet in gebruik; 1 vergund maar na een jaar nog niets in de BAG; en het tekstblok van vandaag staat er
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 57 dagen (173 panden, bovengrens); mediane bezitsduur 3.3 jaar (15 paren met een echte verkoopdatum, waarvan 3 op een jaar bij benadering); prijsgroei per pand nog niet te meten: 5 paren, minimaal 10 nodig
- **Voorraad van de ring**: 23904 woningen in de ring, 23904 met oppervlakte, 16554 met label; nog 0 adressen te vragen; 535 adressen buiten de ring bewaard omdat er een bekendmaking over ging; 2356 woningen onderweg, geregistreerd maar nog niet gereedgemeld; laatste ronde 4 gevraagd, 2 labels gevonden
- **Voet onder de brief**: de voet staat boven de mail en de brief zonder verhaal
- **Feitencontrole van het verhaal**: voor de herstelronde 6 bevinding(en), erna 0
- **Duiding bij beleidsstukken**: geen beleid dat ons raakt vandaag
- **Beleid haalt de mail**: geen beleidsstuk vandaag gepubliceerd
- **Gepubliceerde regels bij de panden**: 1 regel in regelset.txt: wonen op de eerste bouwlaag binnenstad
- **Sleutels in de workflowstappen**: 9 workflows met 97 scriptstappen; 8 modules vragen samen 12 sleutels, en elke stap die ze aanroept geeft die mee
- **Verkooptijd bovengrens**: 77 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 123 dagen; alleen in onderhandeling: 32 panden, mediaan hoogstens 98 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 67 brieven bewaard, laatste van 2026-11-02 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €17.91/m2 uit 132 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -14%
- **Gemeubileerd**: 20 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 26 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 9 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: 3 nieuwbouwregels apart gehouden; die tellen niet mee in de mediaan per m2, de groottepremie of de aanbodreeks
- **Opnieuw aangeboden**: 43 adressen vaker aangeboden: 15 voor minder, 20 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; weezenhof van €750 naar €490
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW03: index 166.2, 4.3% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 11030 panden in de eigen snapshot, 11030 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-11-02
- **Achtergronddekking**: 39 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 30 brieven vastgelegd, laatste 2026-11-02; 548 onderwerpen bleven liggen
- **Dekking van onze signalen**: 672 van de 700 panden met een bekendmaking hebben BAG-gegevens (96%)
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 298 panden gerouteerd
- **Bekendmakingen-archief**: 732 adressen, 1323 publicaties
- **Veldenronde**: geen publicatie die mislukt (stand van 2026-11-01)
- **Regelgevingsmonitor**: 89 verordeningen, 5 wetten
- **Geheugen en trend**: 151 panden onthouden, prijstrend over 10 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

