# Gezondheidsrapport 2026-09-21

10 in orde, 3 aandachtspunten, 1 fouten.

## FOUT
- **Bouwkostenindex**: bouwkosten_index.json ontbreekt of is leeg
  Geen kolom voor de totale bouwkosten. Het CBS gaf deze kolommen: ID, Componenten, Perioden, InputprijsindexBouwkosten_1, OntwikkelingTOVEenJaarEerder_2

## LET OP
- **Huurdata**: 2 huurwaarnemingen, waarvan 2 Pararius en 0 Kamernet; 2 in de laatste week
  Er wordt gemeten, maar het aantal is nog te klein voor een betrouwbare mediaan per grootteklasse en buurt.
- **Eigen bouwkosten**: geen eigen bouwkosten ingevuld
  De verbouwkosten zijn aannames van het script. Vul in bouwkosten_eigen.txt wat verhuurklaar maken en verduurzaming per m2 kosten; uit het hoofd is al beter dan de aanname.
- **Buurtcijfers CBS**: 6 buurten; ontbreekt: inkomen, vermogen, leeftijd, afstand_trein
  inkomen: het veld bestaat wel, maar de waarde is -99997. Bij het CBS betekent een lege of negatieve waarde meestal dat het cijfer voor dit jaar nog niet gepubliceerd is.
vermogen: het veld bestaat wel, maar de waarde is -99997. Bij het CBS betekent een lege of negatieve waarde meestal dat het cijfer voor dit jaar nog niet gepubliceerd is.
leeftijd: niet gevonden onder de verwachte namen. Velden die erop lijken: jaar, perc_bouwjaar_afgelopen_10_jaar, perc_bouwjaar_meer_dan_10_jaar_geleden, percentage_bouwjaarklasse_tot_2000, percentage_bouwjaarklasse_vanaf_2000, percentage_personen_0_tot_15_jaar, percentage_personen_15_tot_25_jaar, percentage_personen_25_tot_45_jaar.
afstand_trein: niet gevonden onder de verwachte namen. Velden die erop lijken: afstand_tot_begraafplaats, afstand_tot_bos, afstand_tot_dagrcreatief_terrein, afstand_tot_open_droog_natuur_terrein, afstand_tot_open_nat_natuurli

## OK
- **Aanbod**: 59 koopobjecten, 6 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,53% (2026-09-18), opslag bij 70% financiering 1,97 procentpunt
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 63 panden gerouteerd
- **Bekendmakingen-archief**: 317 adressen, 445 publicaties
- **Regelgevingsmonitor**: 3 verordeningen, 3 wetten
- **Geheugen en trend**: 62 panden onthouden, prijstrend over 9 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

