# Gezondheidsrapport 2026-10-09

45 in orde, 8 aandachtspunten, 0 fouten.

## LET OP
- **Versies**: paklijst van 2026-10-09: 40 gelijk, 1 met andere inhoud, 0 niet aanwezig; andere inhoud dan de paklijst: .github/workflows/bekendmakingen.yml (46069 bytes, 976 regels)
  Upload de ontbrekende bestanden. Blijft een bestand afwijken nadat het is geuploud, dan is de paklijst achter en moet die ververst worden.
- **Verkopen**: 505 verkopen: 505 geplakt; laatste 2026-09-28
  Er komt nog geen enkele verkoop uit de attendering. Controleer of het filter op verkocht daar echt aan staat.
- **Voltooide splitsingen**: 1 gerealiseerd; mediaan 1 dagen van besluit tot registratie (1); 12 vergund maar na een jaar nog niets in de BAG; maar er is geen tekstblok voor vandaag, dus de brief heeft dit niet gezien
  Het bestand digests/<datum>-splitsingen.md ontbreekt of is leeg. Dan maakt splitsing_voltooid.py wel de json maar komt de tekst nergens terecht. Controleer dat de stap 'Voltooide splitsingen uit de BAG' vóór 'Brief samenstellen' staat.
- **Huurdekking**: steekproef van 12 adressen elders: 5 kennen we al (42%)
  We missen het grootste deel van het huuraanbod. Een extra bron erbij weegt dan zwaarder dan welke verfijning van de berekening ook.
- **Bronnen die niets opleveren**: funda: 528, pararius: 28, kamernet: 46, huislijn: 34, 123wonen: 0, rentola: 1; geen enkele waarneming van: 123wonen
  Controleer of het afzenderdomein in AFZENDERS klopt en of de attendering bij die partij aanstaat. Een verkeerd domein levert geen foutmelding op, alleen stilte.
- **Adressen met meerdere maten**: 1 adressen met meerdere woningmaten: st. annastraat 30 (23, 31 m2)
  Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken weggevallen. Zoek het juiste adres op en pas de regel aan, anders delen twee woningen een dossier.
- **WOZ-schatting**: geijkt op 104 panden: correctie 0.988 (1% stelselmatig), spreiding ±19.4%; mediane fout per methode: kenmerken 14.6% (109), prijs 11.3% (104), beste: prijs; kenmerken uit 77 straten en 11 buurten; nakijken: Derde Walstraat 108 (+111%), Havenweg 34 (-67%), Havenweg 70 (-53%)
  De spreiding is nog te groot om op de schatting te varen; blijf de WOZ opzoeken bij panden die ertoe doen.
- **Attenderingen**: laatste ronde 2026-10-09: huislijn: 4 mails, 17 objecten; kamernet: 19 mails, 13 objecten, 6 bewust overgeslagen; pararius: 3 mails, 6 objecten, 1 bewust overgeslagen; regulier: 4 mails, 6 objecten, 1 bewust overgeslagen; rentola: 1 mails, 1 objecten
  Van funda kwam geen enkele mail. Staat de attendering aan en komt hij in deze mailbox binnen?

## OK
- **Geheugen verstuurde brieven**: 9 onderwerpen bekend, 9 in het venster van drie weken, laatste brief 2026-10-09
- **Brief opnieuw geschreven**: de brief van vandaag is opnieuw geschreven en wijkt af van 2026-10-08-verhaal.md
- **Oude verlaging in de brief**: de brief noemt geen prijsverlaging
- **Bekende onwaarheden in de brief**: 4 bekende onwaarheden getoetst, geen ervan staat in de brief
- **Verkocht pand nog in het aanbod**: geen pand dat zowel verkocht is als te koop staat
- **Huurdata**: 109 huurwaarnemingen, waarvan 28 Pararius en 46 Kamernet en 34 Huislijn en 1 Rentola, zonder adres maar met oppervlakte; 63 in de laatste week; 6 zonder oppervlakte, die tellen niet mee in de huur per m2
- **Aanbod**: 102 koopobjecten, 6 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,52% (2026-10-08), opslag bij 70% financiering 1,98 procentpunt
- **Bouwkostenindex**: 104 maanden, laatste 2026-08
- **Eigen bouwkosten**: 5 eigen tarieven ingevuld
- **Buurtcijfers CBS**: 6 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 951 panden in de ring, waarvan 192 alleen via een melding of besluit; meldingen per jaar: 2025: 102, 2026: 85
- **Woningprijsindex CBS**: landelijk 2026-08, Gelderland (PV) 2026-K2, via opendata.cbs.nl
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-10-08
- **Geschiedenis per pand**: 1770 panden gevolgd, 1425 met meer dan een gebeurtenis; 1579 met BAG-gegevens (6338 woningen, 7446 dubbel geteld zonder deze correctie), 1382 met een energielabel, 0 nog nooit nagekeken waarvan 148 na drie pogingen opgegeven; 12221 regels bespaard door gedeelde pandgegevens; nieuwe panden worden elke run opgehaald, het nakijken van de hele voorraad op veranderingen gebeurt in de weekronde; iedereen is minstens een keer nagekeken
  Geen enkel pand kwam in aanmerking voor de BAG-controle. Draait de stap wel met --volledig, en hebben de panden een gebeurtenis van het juiste soort?
- **Handmatige lijsten**: verkooplijst van Funda: aanwezig; kamerlijst van Kamernet: niet nodig, komt uit de mail; 575 verkochte woningen verwerkt
- **Veroudering aanbod**: 74 panden te koop, mediaan 17 dagen geleden voor het laatst bevestigd, oudste 37 dagen
- **Aanbodreeks**: 8 dagen gemeten; 2026-W40: 8 koop, 9 huur, 2 uitpond; 2026-W41: 6 koop, 28 huur, 1 uitpond. In beeld: 3 nieuw aangeboden panden die bij ons als kamerverhuur bekend staan
- **Profiel nieuw aanbod**: 67 panden in dertig dagen; mediaan 89 m2; 0 zonder label
- **Groottepremie**: 576 waarnemingen, 9 buurten met eigen ijkpunt; 0-40 m2: 1.431 (56), 40-60 m2: 1.242 (110), 60-80 m2: 1.068 (168), 80-100 m2: 1.0 (86), 100-130 m2: 0.972 (83), 130 m2 en groter: 0.912 (73)
- **Verkoopdatums**: 96 panden met een indicatie: 6 met een verkoopdatum, 17 met een plaatsingsdatum, 4 met hoge zekerheid, 0 met een waarschuwing dat het om een andere advertentie gaat; indicaties met bronvermelding, geen Kadastercijfers
- **Doorlooptijden**: mediane verkooptijd 93 dagen (118 panden); mediane bezitsduur 0.8 jaar (65); onbetrouwbaar zolang de geplakte verkopen de plakdatum dragen; prijsgroei per pand 4.8% per jaar (26)
- **Verkooptijd bovengrens**: 73 panden van te koop naar onder bod of verkocht gezien; mediaan hoogstens 129 dagen; alleen in onderhandeling: 37 panden, mediaan hoogstens 88 dagen. Dat is de scherpste maat, want daar legt de koper zich vast. Een bovengrens uit twee eigen waarnemingen, geen schatting: de werkelijke tijd is korter of gelijk
- **Brieven verstuurd**: 43 brieven bewaard, laatste van 2026-10-09 (vandaag)
- **Huur tegen het landelijke cijfer**: onze mediaan €17.91/m2 uit 58 waarnemingen tegen landelijk €20.92/m2 (2026-Q3): -14%
- **Gemeubileerd**: 6 gemeubileerde advertenties apart bewaard; de opslag wordt binnen hetzelfde huurregime vergeleken, want een hoge huur komt eerder door de vrije sector dan door het meubilair
- **WOZ-bestand**: 114 bruikbare regels, 0 nog in te vullen, 8 opgezocht zonder dat het loket een waarde geeft; 6 panden in het aanbod nog zonder WOZ
- **WOZ zonder pand**: 2 landen via de letterroute als overgenomen waarde: Daalseweg 56a, van Welderenstraat 89a; 2 horen bij geen pand in het aanbod en zijn bewaard voor later: Koningshofje 3, St. Annastraat 165
  De letterroute vult een pand aan met de waarde van hetzelfde nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet mee in de doorrekening maar niet in de ijking, want het kunnen twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen meting, zoek dan het adres op zoals het in het aanbod staat.
- **Nieuwbouw apart**: geen nieuwbouwprojecten in het aanbodbestand
- **Opnieuw aangeboden**: 19 adressen vaker aangeboden: 8 voor minder, 11 voor meer; lager bij: van welderenstraat van €705 naar €670; hertogplein van €1995 naar €1520; krayenhofflaan van €864 naar €713
- **VvE-bijdragen**: 2 panden met een VvE-bijdrage, mediaan €275.15 per maand
- **COROP Arnhem/Nijmegen**: Arnhem/Nijmegen (CR) 2026KW02: index 164.1, 4.5% op jaarbasis, 0 transacties
- **3D BAG eigen snapshot**: 1256 panden in de eigen snapshot, 1256 met een buitenmuuroppervlak, 0 zonder gegevens bij de bron; bijgewerkt 2026-10-09
- **Achtergronddekking**: 36 achtergrondstukken voor 13 soorten bekendmakingen; elk soort heeft een stuk
- **Nieuwe onderwerpen**: geen nieuwe onderwerpen voorgesteld
- **Logboek van de brief**: 8 brieven vastgelegd, laatste 2026-10-09; 128 onderwerpen bleven liggen
- **Jaarlijkse grenzen**: huurprijstabel 2026-01-01 (grens vrije sector €1228.07); overdrachtsbelasting 8.0% plus 2.0% bijkomende kosten; SVOH-bedragen 2026-01-01 (gevelisolatie €40.50 per m2)
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 201 panden gerouteerd
- **Bekendmakingen-archief**: 341 adressen, 475 publicaties
- **Regelgevingsmonitor**: 80 verordeningen, 5 wetten
- **Geheugen en trend**: 122 panden onthouden, prijstrend over 9 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

