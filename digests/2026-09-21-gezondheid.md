# Gezondheidsrapport 2026-09-21

9 in orde, 4 aandachtspunten, 1 fouten.

## FOUT
- **Bouwkostenindex**: bouwkosten_index.json ontbreekt of is leeg
  De verbouwkosten worden niet geindexeerd. Zie stap 17.

## LET OP
- **Huurdata**: 2 huurwaarnemingen, waarvan 2 Pararius en 0 Kamernet; 2 in de laatste week
  Er wordt gemeten, maar het aantal is nog te klein voor een betrouwbare mediaan per grootteklasse en buurt.
- **Eigen bouwkosten**: geen eigen bouwkosten ingevuld
  De verbouwkosten zijn aannames van het script. Vul in bouwkosten_eigen.txt wat verhuurklaar maken en verduurzaming per m2 kosten; uit het hoofd is al beter dan de aanname.
- **Buurtcijfers CBS**: 6 buurten; ontbreekt: inkomen, vermogen, leeftijd, afstand_trein
  Deze velden worden niet gevonden in de CBS-kaart. In stap 7 staat welke veldnamen er wel zijn; die moeten in buurten_tabel.py.
- **Kamervergunningen**: 766 adressen, maar 0 buurten gekoppeld
  De koppeling aan buurten is niet gemaakt; de kolom in de brief blijft leeg. Zie stap 5.

## OK
- **Aanbod**: 59 koopobjecten, 6 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,53% (2026-09-18), opslag bij 70% financiering 1,97 procentpunt
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 63 panden gerouteerd
- **Bekendmakingen-archief**: 317 adressen, 445 publicaties
- **Regelgevingsmonitor**: 3 verordeningen, 3 wetten
- **Geheugen en trend**: 62 panden onthouden, prijstrend over 9 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

