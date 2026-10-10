Verkenning van de PDOK-locatieserver

======================================================================
VRAAG 1. Welke velden heeft een adresrecord?
======================================================================
  het hele eerste record:
{
  "bron": "BAG",
  "woonplaatscode": "3030",
  "type": "adres",
  "woonplaatsnaam": "Nijmegen",
  "wijkcode": "WK026802",
  "huis_nlt": "1",
  "openbareruimtetype": "Weg",
  "buurtnaam": "Bottendaal",
  "gemeentecode": "0268",
  "rdf_seealso": "http://bag.basisregistraties.overheid.nl/bag/id/nummeraanduiding/0268200000002093",
  "weergavenaam": "Arend Noorduijnstraat 1, 6512BK Nijmegen",
  "straatnaam_verkort": "Arend Noorduijnstr",
  "id": "adr-1375ee8faced111853e0b4796d8463a4",
  "gekoppeld_perceel": [
    "NMG00-B-5302"
  ],
  "gemeentenaam": "Nijmegen",
  "buurtcode": "BU02680202",
  "wijknaam": "Nijmegen-Oost",
  "identificatie": "0268010000002314-0268200000002093",
  "openbareruimte_id": "0268300000000859",
  "waterschapsnaam": "Waterschap Rivierenland",
  "provinciecode": "PV25",
  "postcode": "6512BK",
  "provincienaam": "Gelderland",
  "centroide_ll": "POINT(5.85351525 51.84092097)",
  "nummeraanduiding_id": "0268200000002093",
  "waterschapscode": "9",
  "adresseerbaarobject_id": "0268010000002314",
  "huisnummer": 1,
  "provincieafkorting": "GD",
  "centroide_rd": "POINT(187136.056 428140.256)",
  "straatnaam": "Arend Noorduijnstraat",
  "gekoppeld_appartement": [
    "NMG00-B-5316-A-9"
  ],
  "score": 1.0568129
}

  velden: adresseerbaarobject_id, bron, buurtcode, buurtnaam, centroide_ll, centroide_rd, gekoppeld_appartement, gekoppeld_perceel, gemeentecode, gemeentenaam, huis_nlt, huisnummer, id, identificatie, nummeraanduiding_id, openbareruimte_id, openbareruimtetype, postcode, provincieafkorting, provinciecode, provincienaam, rdf_seealso, score, straatnaam, straatnaam_verkort, type, waterschapscode, waterschapsnaam, weergavenaam, wijkcode, wijknaam, woonplaatscode, woonplaatsnaam
    gemeentenaam: JA  waarde='Nijmegen'
    gemeentecode: JA  waarde='0268'
    woonplaatsnaam: JA  waarde='Nijmegen'
    provincienaam: JA  waarde='Gelderland'
    buurtnaam: JA  waarde='Bottendaal'
    wijknaam: JA  waarde='Nijmegen-Oost'
    postcode: JA  waarde='6512BK'

======================================================================
VRAAG 2. Wat doet een filter op gemeente en op woonplaats per buurt?
======================================================================
  buurt            zonder  gemeente  woonplaats  vervuiling
  Altrade            3452      3452        3452           0
  Benedenstad        5098      1911        1911        3187
  Biezen             9443      6083        6083        3360
  Bottendaal         2568      2568        2568           0
  Galgenveld         4287      3494        3494         793
  Stadscentrum      11975      7357        7357        4618
  TOTAAL            36823     24865       24865       11958


======================================================================
VRAAG 4. Welke gemeenten leveren de vervuiling?
======================================================================
  Altrade: MISLUKT: HTTP 400: query parameter 'facet.field' not defined in the specifications
  Benedenstad: MISLUKT: HTTP 400: query parameter 'facet.field' not defined in the specifications
  Biezen: MISLUKT: HTTP 400: query parameter 'facet.field' not defined in the specifications
  Bottendaal: MISLUKT: HTTP 400: query parameter 'facet.field' not defined in the specifications
  Galgenveld: MISLUKT: HTTP 400: query parameter 'facet' not defined in the specifications
  Stadscentrum: MISLUKT: HTTP 400: query parameter 'facet' not defined in the specifications

Klaar.
