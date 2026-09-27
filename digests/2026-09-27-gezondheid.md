# Gezondheidsrapport 2026-09-27

13 in orde, 2 aandachtspunten, 2 fouten.

## FOUT
- **Woningprijsindex CBS**: woningprijsindex.json leeg
  Landelijke tabel 85773NED niet op te halen: HTTPSConnectionPool(host='opendata.cbs.nl', port=443): Max retries exceeded with url: /ODataApi/OData/85773NED/TypedDataSet (Caused by NewConnectionEr Regio's van 85792NED niet op te halen: HTTPSConnectionPool(host='opendata.cbs.nl', port=443): Max retries exceeded with url: /ODataApi/OData/85792NED/RegioS (Caused by NewConnectionError("H
- **Regelgevingsmonitor**: controle zelf faalde
  'list' object has no attribute 'get'

## LET OP
- **Huurdata**: 6 huurwaarnemingen, waarvan 6 Pararius en 0 Kamernet; 6 in de laatste week
  Er wordt gemeten, maar het aantal is nog te klein voor een betrouwbare mediaan per grootteklasse en buurt.
- **Eigen bouwkosten**: geen eigen bouwkosten ingevuld
  De verbouwkosten zijn aannames van het script. Vul in bouwkosten_eigen.txt wat verhuurklaar maken en verduurzaming per m2 kosten; uit het hoofd is al beter dan de aanname.

## OK
- **Aanbod**: 77 koopobjecten, 11 in de laatste drie dagen
- **Marktrente**: rente 5.5% bij 70% financiering
- **Kapitaalmarkt (ECB)**: tienjaars AAA-rente 3,57% (2026-09-24), opslag bij 70% financiering 1,93 procentpunt
- **Bouwkostenindex**: 103 maanden, laatste 2026-07
- **Buurtcijfers CBS**: 6 buurten, alle velden gevuld
- **Kamervergunningen**: 766 adressen in 34 buurten
- **Kamerverhuurregister**: 948 panden in de ring, waarvan 189 alleen via een melding of besluit; meldingen per jaar: 2025: 102, 2026: 83
- **Stadsbegroting**: Stadsbegroting 2027, 5 pagina's, opgehaald 2026-09-24
- **Misdrijfcijfers**: 44 buurten
- **OV-haltes**: 333 haltes, 85 panden gerouteerd
- **Bekendmakingen-archief**: 319 adressen, 449 publicaties
- **Geheugen en trend**: 80 panden onthouden, prijstrend over 9 metingen
- **Terugschrijven**: gegevens van de laatste run bewaard

