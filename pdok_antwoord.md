Verkenning van de BAG bij PDOK

======================================================================
VRAAG 1. Welke collecties zijn er, en wat is filterbaar?
======================================================================

  collectie: adres   (Adres)
    filterbaar: geometry, identificatie

  collectie: ligplaats   (Ligplaats)
    filterbaar: geometry, identificatie

  collectie: pand   (Pand)
    filterbaar: geometry, identificatie

  collectie: standplaats   (Standplaats)
    filterbaar: geometry, identificatie

  collectie: verblijfsobject   (Verblijfsobject)
    filterbaar: geometry, identificatie

  collectie: woonplaats   (Woonplaats)
    filterbaar: geometry, identificatie

  alle collecties: adres, ligplaats, pand, standplaats, verblijfsobject, woonplaats

======================================================================
VRAAG 2. Hoe ziet een echt verblijfsobject eruit?
======================================================================
  numberMatched: None
  numberReturned: 1
  het hele eerste kenmerk, onbewerkt:
{
  "type": "Feature",
  "properties": {
    "bronhouder_identificatie": "1883",
    "bronhouder_naam": "Sittard-Geleen",
    "documentdatum": "2018-04-04",
    "documentnummer": "correctie",
    "gebruiksdoel": "woonfunctie",
    "geconstateerd": "N",
    "hoofdadres_identificatie": "0000200000057534",
    "hoofdadres_status": "Naamgeving ingetrokken",
    "huisletter": "A",
    "huisnummer": 32,
    "identificatie": "0000010000057469",
    "openbare_ruimte_identificatie": "1883300000001522",
    "openbare_ruimte_naam": "Steenweg",
    "openbare_ruimte_naam_kort": null,
    "openbare_ruimte_status": "Naamgeving uitgegeven",
    "oppervlakte": 72,
    "pand.href": [
      "https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items/4c396a25-0e16-586f-a298-3252f8795942"
    ],
    "postcode": "6131BE",
    "provincie_afkorting": "Li",
    "provincie_naam": "Limburg",
    "rdf_seealso": "http://bag.basisregistraties.overheid.nl/bag/id/verblijfsobject/0000010000057469",
    "status": "Verblijfsobject ingetrokken",
    "toevoeging": null,
    "woonplaats_identificatie": "3512",
    "woonplaats_naam": "Sittard",
    "woonplaats_status": "Woonplaats aangewezen"
  },
  "geometry": {
    "type": "Point",
    "coordinates": [
      5.862878870591695,
      50.99994879976323
    ]
  },
  "id": "80f96ef7-dfa4-5197-b681-cfd92b10757e"
}

  eigenschappen: bronhouder_identificatie, bronhouder_naam, documentdatum, documentnummer, gebruiksdoel, geconstateerd, hoofdadres_identificatie, hoofdadres_status, huisletter, huisnummer, identificatie, openbare_ruimte_identificatie, openbare_ruimte_naam, openbare_ruimte_naam_kort, openbare_ruimte_status, oppervlakte, pand.href, postcode, provincie_afkorting, provincie_naam, rdf_seealso, status, toevoeging, woonplaats_identificatie, woonplaats_naam, woonplaats_status
    postcode: JA  waarde='6131BE'
    oppervlakte: JA  waarde=72
    gebruiksdoel: JA  waarde='woonfunctie'
    huisnummer: JA  waarde=32
    openbare_ruimte_naam: JA  waarde='Steenweg'
    pand: NEE
    identificatie: JA  waarde='0000010000057469'
    status: JA  waarde='Verblijfsobject ingetrokken'

======================================================================
VRAAG 3. Werkt bbox, en hoeveel objecten zitten er in de doos?
======================================================================
  bbox 5.75,51.76,5.98,51.90 werkt.
  numberMatched: None
  numberReturned: 2
    {"postcode": "6551ZE", "openbare_ruimte_naam": "Bonenkampstraat", "huisnummer": 4, "oppervlakte": 144, "gebruiksdoel": "woonfunctie"}
    {"postcode": "6551ZE", "openbare_ruimte_naam": "Bonenkampstraat", "huisnummer": 6, "oppervlakte": 114, "gebruiksdoel": "woonfunctie"}
  volgende-link aanwezig: JA
    https://api.pdok.nl/kadaster/bag/ogc/v2/collections/verblijfsobject/items?bbox=5.75%2C51.76%2C5.98%2C51.90&cursor=Fjol%7C2XCYlA&f=json&limit=2

======================================================================
VRAAG 4. Is de begrenzing van Nijmegen uit de BAG zelf te halen?
======================================================================

  collectie woonplaats binnen de zoekdoos:
    3131: bbox=5.87214,51.86520,5.93304,51.93461 (3775 punten)
    3132: bbox=5.93309,51.85445,6.00205,51.90033 (6046 punten)
    3133: bbox=5.92384,51.89345,5.99845,51.92370 (9259 punten)
    3134: bbox=5.97675,51.87091,6.04628,51.90664 (3985 punten)
    3136: bbox=5.90995,51.87318,5.94693,51.90289 (1433 punten)
    3137: bbox=5.85687,51.87651,5.88011,51.89757 (1075 punten)
    2564: bbox=5.67551,51.77785,5.80095,51.83971 (1151 punten)
    2290: bbox=5.89234,51.79975,5.95114,51.82933 (455 punten)
    2291: bbox=5.87940,51.74103,5.99207,51.81056 (809 punten)
    2292: bbox=5.87907,51.80196,5.91194,51.82389 (357 punten)
    3618: bbox=5.89234,51.79975,5.95714,51.83231 (599 punten)
    2750: bbox=5.77984,51.84088,5.82570,51.87277 (628 punten)
    2802: bbox=5.86447,51.75549,5.90079,51.77863 (253 punten)
    2803: bbox=5.87052,51.74065,5.91528,51.77081 (187 punten)
    1864: bbox=5.78192,51.89369,5.89803,51.95397 (948 punten)
    1866: bbox=5.72415,51.88980,5.77924,51.93661 (698 punten)
    1869: bbox=5.79835,51.87027,5.83779,51.89368 (393 punten)
    1871: bbox=5.74073,51.87569,5.80997,51.90318 (367 punten)
    1872: bbox=5.76214,51.89292,5.83672,51.93300 (539 punten)
    2872: bbox=5.90007,51.81634,5.96290,51.84087 (537 punten)

Klaar.
