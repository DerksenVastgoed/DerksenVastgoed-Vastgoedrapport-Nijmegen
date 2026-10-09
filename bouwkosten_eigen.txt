# Eigen bouwkosten per vierkante meter, uit echte facturen en bonnen.
# Formaat per regel: post | bedrag per m2 | peildatum | toelichting
#
# BEDRAGEN INCLUSIEF BTW. Woningverhuur is vrijgesteld, dus de btw is voor ons
# geen verrekenbare post maar gewoon kosten. Alleen bij een utiliteitspand kan
# de btw worden teruggevraagd. Materiaal 21%, arbeid aan een woning ouder dan
# twee jaar 9%.
#
# Regels met een hekje tellen niet mee.
#
# De tarieven zijn NETTO, dus na aftrek van de SVOH-subsidie. Dat is het bedrag
# waarmee je een aankoop beoordeelt, want die subsidie krijg je hoe dan ook als
# je de maatregelen uitvoert. Bij de Eerste Oude Heselaan was dat €2.537,25 op
# een investering van €16.478,36, oftewel 15%.
#
# Ventilatie hoort bij isoleren en zit daarom in het verduurzamingstarief.
# Luchtdicht maken zonder ventilatie levert vocht en schimmel op, en een
# CO2-gestuurd systeem telt ook mee in de labelberekening. Bij de Eerste Oude
# Heselaan was dat €3.327,50 inclusief btw, een vijfde van de hele ingreep.

binnenwandisolatie | 161 | 2026-02-01 | Eerste Oude Heselaan 88, 38 m2: aanneemsom Noordermeer €5.213,08 inclusief btw (frame, folies, 100 mm PIR met Rd 4,54, arbeid, afvalcontainer) plus €911,26 aan zelf gekocht plaatmateriaal bij Sleiderink; exclusief het hout van Bouwmaat, dat als aanbetaling zonder specificatie is geboekt
vloerisolatie      | 39  | 2025-11-20 | Eerste Oude Heselaan 88, 50,4 m2: Knauf Brio vloerelementen 33 mm met lijm en randisolatiestroken, €1.948,00 inclusief btw
stucwerk           | 22  | 2026-03-11 | Eerste Oude Heselaan 88, V. van Oijen: €20 per m2 wand exclusief, €21,80 inclusief 9% btw; plafond €27,25 inclusief. Twee termijnen samen €3.744,15 inclusief btw over 109 m2 wand en 39 m2 plafond

# Let op bij het gebruik: stucwerk schaalt met het hele woonoppervlak en niet
# met het geisoleerde geveldeel. Hier is 109 m2 wand gestuukt tegenover 38 m2
# voorzetwand.

# LET OP: dit is een noodgreep, geen tarief. Het is een hele verbouwing van een
# woning van 58 m2, teruggerekend naar een bedrag per m2 woonoppervlak, en er
# zit 27% stucwerk in dat met verduurzamen weinig te maken heeft. Elk pand met
# label E of F krijgt hiermee dezelfde kosten, ongeacht wat het werkelijk nodig
# heeft. Zodra de maatregelenketen werkt (bouwjaar naar norm naar oppervlak uit
# de 3D BAG naar prijs per maatregel uit maatregelprijzen.txt) vervalt deze
# regel. Tot die tijd is hij beter dan het kental van de RVO, want hij komt
# tenminste uit een echte factuur.
verduurzaming-f | 240 | 2026-06-05 | Eerste Oude Heselaan 88, 58 m2 volgens de BAG: van label F of E naar A. Investering €16.478,36 inclusief btw min €2.537,25 SVOH-subsidie is €13.941,11 netto. Daarin zitten gevelisolatie aan de binnenzijde over 38 m2, vloerisolatie, stucwerk over 109 m2 wand en 39 m2 plafond, en een Duco ventilatiesysteem met CO2-sensoren. Een sprong naar A is de zwaarste ingreep; voor een kleiner labelverschil is dit tarief te hoog.

verduurzaming-e | 240 | 2026-03-11 | zelfde ingreep als verduurzaming-f; het pand had label F of E en het is niet vast te stellen welke van de twee

# LET OP: de brief leest alleen de posten verduurzaming, verhuurklaar en
# splitsen-eenheid, en rekent die per m2 woonoppervlak. De posten hierboven
# staan per m2 bouwdeel en worden dus nog niet gebruikt in de doorrekening.
#
#
# De toevoeging achter verduurzaming is het HUIDIGE label van het pand, niet het
# label waar je naartoe gaat. Het pand aan de Eerste Oude Heselaan had label F
# of E, dus staat dit bedrag onder verduurzaming-f en verduurzaming-e. Voor een
# pand dat al op C staat is de ingreep kleiner en geldt het kental van de RVO,
# tot we daar ook een eigen factuur van hebben.

# Nog in te vullen, zodra er een factuur van is:
# verhuurklaar     | ... | ... | wat een pand kost om zonder ingreep te kunnen verhuren
# dakisolatie      | ... | ... | per m2 dakvlak
#
# splitsen-eenheid blijft leeg, en dat is geen achterstand. Derksen Vastgoed
# heeft nog nooit een appartement op deze manier gesplitst, dus er is geen
# factuur van en die komt er ook niet vanzelf. Vragen om "de cijfers van Twan"
# heeft dus geen zin; die zijn er al, het zijn de posten hierboven van de
# Eerste Oude Heselaan 88.
#
# Wat deze post wel kan vullen, in volgorde van hardheid:
#  1. Een prijsopgave van een aannemer voor het splitsen van een eigen pand.
#     Dat is ook een hard getal en kost een telefoontje, maar pas als er een
#     splitsing op tafel ligt.
#  2. De vaste posten eromheen, die publiek zijn en geen opgave nodig hebben:
#     leges omgevingsvergunning (bij de Biezenstraat 110 was dat EUR 2.218,21
#     volgens het verleende besluit), inschrijving van de splitsingsakte bij
#     het Kadaster, en een extra aansluiting voor elektra en gas volgens het
#     gepubliceerde tarief van Liander. Dat is een ondergrens per eenheid.
#  3. Het bouwkundige deel, dus een tweede keuken, een tweede badkamer, de
#     brand- en geluidsscheiding en een eigen voordeur. Niemand heeft dat voor
#     ons geprijsd en wij gaan het niet schatten.
#
# Tot 1 of 2 er is, blijft de uitpondsom in de brief een bovengrens: wat er na
# aankoop en kosten koper per eenheid overblijft voor de verbouwing. Dat is een
# berekening en geen aanname, en zo hoort het er ook te staan.
