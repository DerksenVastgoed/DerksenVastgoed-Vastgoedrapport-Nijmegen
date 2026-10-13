#!/usr/bin/env python3
"""
Geplakte Funda-lijst met verkochte woningen verwerken.

Drie dingen tegelijk, uit dezelfde lijst:

1. De verkopen worden waarnemingen. Let op: Funda toont bij een verkocht pand
   de laatste vraagprijs en niet de koopsom; die staat alleen bij het Kadaster.
   Het is dus de vraagprijs waarop het pand van de markt ging, en dat is iets
   anders dan wat er is betaald.
2. Panden die bij ons nog te koop staan maar op Funda verkocht zijn, worden
   gemeld. Vendr stuurt geen bericht als een project verkocht is, dus die
   blijven anders eeuwig in de lijst staan.
3. Elk verkocht adres wordt tegen het bekendmakingenarchief gelegd: is er na
   het plaatsen van de advertentie een vergunning aangevraagd of verleend op
   dat adres? Dat is het spoor van een koper die is gaan verbouwen, splitsen of
   verkameren.

Let op bij punt 3: Funda noemt alleen hoe lang een advertentie er staat, niet
wanneer er is verkocht. De datum die we afleiden is dus het begin van de
advertentie, en een bekendmaking daarna is een aanwijzing en geen bewijs.

Gebruik:
  python funda_verkocht_plak.py --uit digests/2026-09-27-verkocht.md
"""

import argparse
import datetime as dt
import json
import os
import re
import sys


import pandsleutel as _psl
PLAK_PAD = "funda_verkocht_plak.txt"
UIT_PAD = "verkopen.txt"
DETAIL_PAD = "verkocht_details.json"
ARCHIEF_PAD = "bekendmakingen_archief.json"

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass

# Funda kent meer dan "Verkocht": een pand kan onder bod staan of verkocht zijn
# onder voorbehoud. Dat zijn verschillende dingen, en "onder bod" is helemaal
# geen verkoop. We leggen ze apart vast in plaats van ze op een hoop te gooien.
STATUS = {
    "verkocht": "verkocht",
    "verkocht onder voorbehoud": "verkocht onder voorbehoud",
    "onder bod": "onder bod",
    "onder optie": "onder bod",
}
# Nieuwbouw is geen bestaande voorraad: bouwnummers, v.o.n.-prijzen en een
# project in plaats van een adres. Die horen niet in onze reeks.
NIEUWBOUW = re.compile(r"nieuwbouw|bouwnr\.|^project\[", re.I)
PRIJS = re.compile(r"^€\s*([\d.]+)\s*(k\.k\.|v\.o\.n\.)", re.I)
ADRES = re.compile(r"^\[([^\]]+)\]\((https://www\.funda\.nl/detail/koop/[^)]+)\)")
POSTCODE = re.compile(r"^\[(\d{4}\s?[A-Z]{2})\s+(.+?)\]\(")
OPP = re.compile(r"^\*\s*(\d{1,4})\s*m²")
LABEL = re.compile(r"^\*\s*(A\+{0,4}|[B-G])\s*$")
# HOE LANG DE ADVERTENTIE ER AL STAAT, EN WAAROM DIT EEN TABEL IS.
#
# Dit stond als "7 als de eenheid met 'week' begint, anders 30". Dat leest
# alsof het klopt en doet het niet: het meervoud van week is "weken", met een
# e, dus "weken".startswith("week") is onwaar. Elke Funda-regel "Sinds 3
# weken" werd daardoor 90 dagen in plaats van 21, en dat is de meest
# voorkomende vorm op de pagina. Het enkelvoud "week" ging wel goed, dus de
# fout zat precies in het geval dat bijna altijd voorkomt.
#
# Daarom nu een tabel en geen voorvoegseltoets, en de regex wordt eruit
# opgebouwd zodat een eenheid toevoegen niet op twee plekken hoeft. De langste
# vorm staat vooraan, anders pakt de alternatie "week" uit "weken" en "maand"
# uit "maanden" en is het meervoud weer stil weg.
EENHEDEN = {"dag": 1, "dagen": 1, "week": 7, "weken": 7,
            "maand": 30, "maanden": 30, "jaar": 365, "jaren": 365}
SINDS = re.compile(r"^Sinds\s+(\d+)\s+("
                   + "|".join(sorted(EENHEDEN, key=len, reverse=True))
                   + r")\b", re.I)


def _sleutel(adres):
    """Een van de veertien sleutelfuncties in elf bestanden die allemaal hetzelfde
    bedoelden en op drie punten uiteenliepen: of een titel werd afgekort,
    of een accent wegviel of bleef staan, en of "doctor" meedeed. Op de
    adressen die we volgen gaven twee van die veertien 41 keer een andere
    sleutel. De functie blijft staan omdat de aanroepers hem gebruiken, maar
    hij rekent niet meer zelf."""
    return _psl.sleutel(adres)


# Een korte regel voor handwerk, naast de geplakte pagina:
#   status | prijs | adres | postcode | woonoppervlakte | label
# Bijvoorbeeld: verkocht | 519000 | Fagelstraat 42 | 6524CG | 110 | C
KORT = re.compile(r"^\s*(verkocht onder voorbehoud|verkocht|onder bod|onder optie)"
                  r"\s*\|\s*([\d.]+)\s*\|\s*([^|]+?)\s*\|\s*(\d{4}\s?[A-Z]{2})?"
                  r"\s*\|\s*(\d{1,4})\s*(?:\|\s*([A-G]\+{0,4}))?\s*$", re.I)


def parse_kort(regels):
    """De korte handmatige regels, als die er zijn."""
    uit = []
    for regel in regels:
        m = KORT.match(regel)
        if not m:
            continue
        status, prijs, adres, postcode, opp, label = m.groups()
        uit.append({"prijs": int(prijs.replace(".", "")), "adres": adres.strip(),
                    "plaats": "Nijmegen",
                    "postcode": (postcode or "").replace(" ", "") or None,
                    "opp": [int(opp)], "label": (label or "").upper() or None,
                    "sinds_dagen": None, "url": None,
                    "status": STATUS[status.lower()], "nieuwbouw": False})
    return uit


# De makelaar staat in de geplakte tekst als een link naar zijn eigen pagina.
# Die naam is het enige wat we over de partij achter een pand kunnen weten
# zonder het Kadaster: eigendom is daar betaald en mag niet worden
# herpubliceerd. Wie verkoopt is niet wie bezit, maar een makelaar die
# steeds terugkeert bij vergunde en daarna verkochte panden, zegt genoeg om
# eens te bellen.
RE_MAKELAAR = re.compile(r"\[([^\]]{3,60})\]\(https://www\.funda\.nl/makelaar/")


def parse(tekst):
    """De verkochte woningen uit de geplakte tekst."""
    regels = [r.strip() for r in tekst.split("\n")]
    uit, huidig, sinds_dagen = [], None, None
    for regel in regels:
        s = SINDS.match(regel)
        if s:
            aantal, eenheid = int(s.group(1)), s.group(2).lower()
            sinds_dagen = aantal * EENHEDEN[eenheid]
            continue
        # De statusregel kan er "Verkocht onder voorbehoudNieuwbouwwoning" of
        # "Onder optieNieuwbouwwoning" uitzien: status en soort aan elkaar
        kaal = regel.lower().replace("nieuwbouwwoning", "").strip()
        if kaal in STATUS:
            if huidig:
                uit.append(huidig)
            huidig = {"prijs": None, "adres": None, "plaats": None,
                      "postcode": None, "opp": [], "label": None,
                      "sinds_dagen": sinds_dagen, "url": None,
                      "status": STATUS[kaal],
                      "nieuwbouw": bool(NIEUWBOUW.search(regel))}
            continue
        if not huidig:
            continue
        p = PRIJS.match(regel)
        if p and huidig["prijs"] is None:
            huidig["prijs"] = int(p.group(1).replace(".", ""))
            if p.group(2).lower().startswith("v"):
                huidig["nieuwbouw"] = True   # v.o.n. hoort bij nieuwbouw
            continue
        if NIEUWBOUW.search(regel):
            huidig["nieuwbouw"] = True
            continue
        a = ADRES.match(regel)
        if a and not huidig["adres"]:
            huidig["adres"] = a.group(1).strip()
            huidig["url"] = a.group(2)
            continue
        pc = POSTCODE.match(regel)
        if pc and not huidig["postcode"]:
            huidig["postcode"] = pc.group(1).replace(" ", "")
            huidig["plaats"] = pc.group(2).strip()
            continue
        o = OPP.match(regel)
        if o:
            huidig["opp"].append(int(o.group(1)))
            continue
        lb = LABEL.match(regel)
        if lb and not huidig["label"]:
            huidig["label"] = lb.group(1)
    if huidig:
        uit.append(huidig)
    uit.extend(parse_kort(regels))

    # ONTDUBBELEN: DE LAATSTE EN NIET DE EERSTE.
    #
    # Dit hield de eerste regel per adres en prijs, met als argument dat een
    # geplakte pagina zich vaak herhaalt. Binnen een pagina maakt dat niets
    # uit, want die regels zijn gelijk. Over twee pagina's wel: het bestand is
    # chronologisch en wordt achteraan aangevuld, dus de eerste regel is de
    # OUDSTE waarneming. Daardoor kon een nieuwe lijst de status van een adres
    # dat er al in stond nooit meer bijwerken.
    #
    # Gemeten op 13 oktober: van vijftien woningen die Funda als verkocht gaf,
    # stonden er negen in de lijst van 28 september met een oudere status. Zes
    # bleven daardoor op "onder bod" staan, een op "verkocht onder voorbehoud",
    # en alleen de zes adressen die nog nergens stonden kwamen erdoor. Het
    # plakbestand zei "je mag dezelfde lijst gerust een tweede keer plakken",
    # en dat was waar voor dezelfde lijst en onwaar voor een bijgewerkte.
    #
    # Een dict houdt de plaats van de eerste vermelding en de waarde van de
    # laatste, dus de volgorde blijft stabiel en de waarneming is de nieuwste.
    per_sleutel = {}
    for w in uit:
        if not (w["adres"] and w["prijs"] and w["opp"] and w["plaats"]):
            continue
        if w.get("nieuwbouw"):
            continue
        # Bij een huis staan er twee oppervlaktes: wonen en perceel. De eerste
        # is de woonoppervlakte.
        w["woonopp"] = w["opp"][0]
        w["perceel"] = w["opp"][1] if len(w["opp"]) > 1 else None
        per_sleutel[(_sleutel(w["adres"]), w["prijs"])] = w
    schoon = list(per_sleutel.values())

    # De makelaar hoort bij het pand erboven: in de geplakte pagina staat de
    # link naar zijn pagina onder de gegevens van die woning. We lopen de
    # regels in volgorde langs en houden bij welk pand we net zijn gepasseerd.
    # Dit gebeurt NA het ontdubbelen, zodat de naam bij het record komt dat
    # overleeft en niet bij een record dat zojuist is weggevallen.
    op_adres = {}
    for w in schoon:
        if w.get("adres"):
            op_adres[w["adres"]] = w
    huidig_pand = None
    for regel in regels:
        for adres, w in op_adres.items():
            if f"[{adres}]" in regel:
                huidig_pand = w
                break
        m = RE_MAKELAAR.search(regel)
        if m and huidig_pand is not None and not huidig_pand.get("makelaar"):
            huidig_pand["makelaar"] = m.group(1).strip()
    return schoon


def lees_regels(pad):
    if not os.path.exists(pad):
        return []
    with open(pad, encoding="utf-8") as f:
        return [r.strip() for r in f if r.strip()]


def nog_te_koop(bestaand):
    """
    Adressen die bij ons als te koop staan, volgens hun NIEUWSTE waarneming.

    DE DATUM BESLIST, NIET DE PLAATS IN HET BESTAND. Hier won simpelweg de
    laatste regel. Dat klopte zolang verkopen.txt alleen achteraan werd
    aangevuld met waarnemingen van vandaag. Het klopt niet meer zodra we oude
    mails inhalen: die regels komen ook achteraan, met een datum van weken
    terug, en dan zou een "te koop" van 25 augustus een "verkocht" van 1
    oktober overschrijven. Elke verkoop die we al kenden zou stilletjes
    terugdraaien, en de woning zou weer in het aanbod van de brief staan.

    Een regel zonder datum telt als de oudste. Die zijn met de hand gezet en
    verliezen dus van elke waarneming met een datum. Ze tellen wel mee: de
    eis van vijf velden sloot de 143 met de hand gezette regels hier uit.
    """
    beste = {}
    for n, r in enumerate(bestaand):
        velden = [v.strip() for v in r.split("|")]
        if len(velden) < 4:
            continue
        sl = _sleutel(velden[0])
        # (datum, volgnummer): bij een gelijke of ontbrekende datum beslist de
        # volgorde alsnog, zodat twee waarnemingen van dezelfde dag zich
        # gedragen zoals voorheen.
        rang = ((velden[4] if len(velden) > 4 else ""), n)
        if sl not in beste or rang >= beste[sl][0]:
            beste[sl] = (rang, velden[3].lower())
    return {k for k, (_, status) in beste.items()
            if status.startswith(("te koop", "nieuw"))}


def eerst_gezien_per_adres(bestaand):
    """
    Per adres de oudste datum waarop die regel bij ons in verkopen.txt kwam.

    Dat is geen plaatsingsdatum maar wel een harde ondergrens: op die dag
    stond de advertentie er. Een bekendmaking daarna kan van de koper zijn,
    een bekendmaking ervoor zeker niet.
    """
    uit = {}
    for r in bestaand:
        velden = [v.strip() for v in r.split("|")]
        if len(velden) < 5 or not velden[4]:
            continue
        sl = _sleutel(velden[0])
        if sl not in uit or velden[4] < uit[sl]:
            uit[sl] = velden[4]
    return uit


def vergunningen_na_plaatsing(verkocht, archief, eerst_gezien=None):
    """
    Bekendmakingen op een verkocht adres, na het begin van de advertentie.

    Een aanwijzing dat de koper iets met het pand doet. Geen bewijs: de
    advertentiedatum is een benadering van het verkoopmoment, en een
    bekendmaking kan ook van de vorige eigenaar zijn.

    ZONDER VENSTER GEEN SPOOR. Hier stond "grens = None als we de
    advertentiedatum niet kennen", en dan liet het filter elke bekendmaking
    door die ooit op dat adres is gedaan. In het geplakte bestand van 9
    oktober staat geen enkele "Sinds"-regel, dus gold dat voor alle 575
    verkochte adressen: 14 ervan haalden de brief met de tekst "na het begin
    van de advertentie" terwijl er geen begin bekend was. Twee ervan
    (Graafseweg 47-C en 47-E) hingen aan een vergunning van juni 2025, ruim
    een jaar voor de lijst. Een adres zonder venster wordt nu geteld en niet
    gemeld, en elk spoor zegt waar zijn venster op rust.
    """
    if not archief:
        return ([], {"zonder_venster": 0, "uit_advertentie": 0,
                     "uit_eerst_gezien": 0})
    uit = []
    telling = {"zonder_venster": 0, "uit_advertentie": 0,
               "uit_eerst_gezien": 0}
    vandaag = dt.date.today()
    eerst_gezien = eerst_gezien or {}
    for w in verkocht:
        m = re.match(r"^(.+?)\s+(\d+)", w["adres"])
        if not m:
            continue
        straat, nr = m.group(1), m.group(2)
        sl = re.sub(r"[^a-z0-9]", "", straat.lower()) + nr
        items = archief.get(sl, [])
        if not items:
            continue
        grens, grondslag = None, None
        if w.get("sinds_dagen"):
            grens = (vandaag - dt.timedelta(days=w["sinds_dagen"])).isoformat()
            grondslag = "advertentie"
            telling["uit_advertentie"] += 1
        elif eerst_gezien.get(_sleutel(w["adres"])):
            grens = eerst_gezien[_sleutel(w["adres"])]
            grondslag = "eerst gezien"
            telling["uit_eerst_gezien"] += 1
        else:
            telling["zonder_venster"] += 1
            continue
        na = [t for t in items if (t.get("datum") or "") >= grens]
        if na:
            uit.append({"adres": w["adres"], "prijs": w["prijs"],
                        "vanaf": grens, "grondslag": grondslag,
                        "bekendmakingen": na[:3]})
    return (uit, telling)


PLAKPROEF = """\
Sinds 3 weken
Verkocht
€ 539.000 k.k.
[Pontanusstraat 19](https://www.funda.nl/detail/koop/nijmegen/appartement-pontanusstraat-19/44507093/)
[6524 HB Nijmegen](https://www.funda.nl/detail/koop/nijmegen/appartement-pontanusstraat-19/44507093/)

* 135 m²
* 3
* D

[Kolmeijer makelaars Nijmegen](https://www.funda.nl/makelaar/13080-kolmeijer-makelaars-nijmegen/)
Verkocht
€ 275.000 k.k.
[Karrengas 48-F](https://www.funda.nl/detail/koop/nijmegen/appartement-karrengas-48-f/44506179/)
[6511 GS Nijmegen](https://www.funda.nl/detail/koop/nijmegen/appartement-karrengas-48-f/44506179/)

* 40 m²
* 1
* C

[Hestia makelaars & taxateurs](https://www.funda.nl/makelaar/13034-hestia-makelaars-en-taxateurs/)
Sinds 2 dagen
Onder bod
€ 405.000 k.k.
[Schoolstraat 135](https://www.funda.nl/detail/koop/nijmegen/appartement-schoolstraat-135/44574761/)
[6512 JE Nijmegen](https://www.funda.nl/detail/koop/nijmegen/appartement-schoolstraat-135/44574761/)

* 80 m²
* 2
* D

[Houwen Makelaars B.V.](https://www.funda.nl/makelaar/2293-houwen-makelaars-bv/)
"""


def proef():
    """
    Nameten wat deze module over een geplakte lijst beweert.

    Drie dingen die alle drie fout zijn geweest: de omrekening van "Sinds N
    weken", het venster waarbinnen een bekendmaking een spoor van de koper
    mag heten, en de datum waarop we een woning voor het eerst zagen.
    """
    fouten = []

    # 1. DE EENHEDEN. Het meervoud is de meest voorkomende vorm op Funda en
    # was precies de vorm die fout ging.
    for tekst, verwacht in [("Sinds 1 week", 7), ("Sinds 3 weken", 21),
                            ("Sinds 4 weken", 28), ("Sinds 6 weken", 42),
                            ("Sinds 1 maand", 30), ("Sinds 3 maanden", 90),
                            ("Sinds 2 dagen", 2), ("Sinds 1 jaar", 365)]:
        s = SINDS.match(tekst)
        if not s:
            fouten.append(f"{tekst!r} wordt niet herkend")
            continue
        uit = int(s.group(1)) * EENHEDEN[s.group(2).lower()]
        if uit != verwacht:
            fouten.append(f"{tekst!r} geeft {uit} dagen, verwacht {verwacht}")
    # Elke eenheid in de tabel moet ook door de regex komen, anders drijft de
    # een van de ander weg zonder dat iemand het ziet.
    for eenheid in EENHEDEN:
        if not SINDS.match(f"Sinds 2 {eenheid}"):
            fouten.append(f"de eenheid {eenheid!r} staat in de tabel maar komt "
                          f"niet door de regex")

    # 2. DE LIJST ZELF. Adres, prijs, oppervlakte, label, makelaar, status en
    # het aantal dagen, uit de opmaak zoals Funda hem geeft.
    uit = parse(PLAKPROEF)
    if len(uit) != 3:
        fouten.append(f"{len(uit)} woningen uit de proeflijst, verwacht 3")
    else:
        eerste, tweede, derde = uit
        if eerste["adres"] != "Pontanusstraat 19" or eerste["prijs"] != 539000:
            fouten.append(f"eerste woning verkeerd gelezen: "
                          f"{eerste['adres']!r} {eerste['prijs']}")
        if eerste["sinds_dagen"] != 21:
            fouten.append(f"'Sinds 3 weken' werd {eerste['sinds_dagen']} "
                          f"dagen in de lijst, verwacht 21")
        if eerste["woonopp"] != 135 or eerste["label"] != "D":
            fouten.append(f"maat of label verkeerd: {eerste['woonopp']} "
                          f"{eerste['label']!r}")
        if eerste["postcode"] != "6524HB":
            fouten.append(f"postcode verkeerd: {eerste['postcode']!r}")
        if not (eerste.get("makelaar") or "").startswith("Kolmeijer"):
            fouten.append(f"makelaar verkeerd: {eerste.get('makelaar')!r}")
        # De tweede woning heeft geen eigen Sinds-regel. Funda zet die kop
        # een keer boven een groep, dus de waarde hoort door te lopen.
        if tweede["sinds_dagen"] != 21:
            fouten.append(f"de tweede woning kreeg {tweede['sinds_dagen']} "
                          f"dagen; de Sinds-kop hoort door te lopen tot de "
                          f"volgende kop")
        if derde["sinds_dagen"] != 2 or derde["status"] != "onder bod":
            fouten.append(f"de derde woning: {derde['sinds_dagen']} dagen, "
                          f"status {derde['status']!r}; verwacht 2 en "
                          f"'onder bod'")

    # 2b. EEN BIJGEWERKTE LIJST MOET DE OUDE STATUS VERVANGEN. Het bestand
    # wordt achteraan aangevuld, dus de laatste vermelding is de nieuwste.
    ouder = PLAKPROEF.replace("Sinds 3 weken\nVerkocht", "Sinds 9 weken\nOnder bod", 1)
    twee = parse(ouder + PLAKPROEF)
    pont = [w for w in twee if w["adres"] == "Pontanusstraat 19"]
    if len(pont) != 1:
        fouten.append(f"Pontanusstraat 19 komt {len(pont)} keer terug na het "
                      f"ontdubbelen, verwacht 1")
    elif pont[0]["status"] != "verkocht" or pont[0]["sinds_dagen"] != 21:
        fouten.append(f"een bijgewerkte lijst werkt de status niet bij: "
                      f"{pont[0]['status']!r}, {pont[0]['sinds_dagen']} dagen; "
                      f"verwacht 'verkocht' en 21")
    elif not (pont[0].get("makelaar") or "").startswith("Kolmeijer"):
        fouten.append(f"de makelaar hoort bij het record dat overleeft: "
                      f"{pont[0].get('makelaar')!r}")
    if len(twee) != 3:
        fouten.append(f"twee keer dezelfde lijst geeft {len(twee)} woningen, "
                      f"verwacht 3")

    # 3. HET VENSTER. Zonder plaatsingsdatum en zonder eerste waarneming mag
    # er geen spoor worden gemeld, want dan laat het filter alles door.
    archief = {"teststraat1": [{"datum": "2020-01-01", "titel": "oud"},
                               {"datum": dt.date.today().isoformat(),
                                "titel": "vers"}]}
    kaal = [{"adres": "Teststraat 1", "prijs": 1, "sinds_dagen": None}]
    sporen, telling = vergunningen_na_plaatsing(kaal, archief)
    if sporen:
        fouten.append(f"zonder venster werd er toch een spoor gemeld: "
                      f"{sporen[0]['vanaf']!r}")
    if telling["zonder_venster"] != 1:
        fouten.append(f"zonder venster niet geteld: {telling}")

    met = [{"adres": "Teststraat 1", "prijs": 1, "sinds_dagen": 21}]
    sporen, telling = vergunningen_na_plaatsing(met, archief)
    if len(sporen) != 1 or len(sporen[0]["bekendmakingen"]) != 1:
        fouten.append(f"met een venster van 21 dagen hoort alleen de verse "
                      f"bekendmaking mee te komen: {sporen}")
    elif sporen[0]["grondslag"] != "advertentie":
        fouten.append(f"grondslag verkeerd: {sporen[0]['grondslag']!r}")

    # 3b. DE DATUM BESLIST, OOK ALS DE OUDE REGEL ACHTERAAN STAAT. Een
    # inhaalslag van oude mails zet waarnemingen van weken terug achteraan in
    # het bestand. Won daar de plaats in het bestand, dan draaide elke verkoop
    # die we al kenden stilletjes terug naar "te koop".
    oud_achteraan = [
        "Teststraat 1 | Nijmegen | 539000 | verkocht | 2026-10-01 | x | 135 | ",
        "Teststraat 1 | Nijmegen | 539000 | te koop | 2026-08-25 | x | 135 | "]
    for volgorde, naam in ((oud_achteraan, "oud achteraan"),
                           (oud_achteraan[::-1], "oud vooraan")):
        if fvp_te_koop := nog_te_koop(volgorde):
            fouten.append(f"met {naam} heet het adres nog te koop terwijl de "
                          f"nieuwste waarneming verkocht is: {fvp_te_koop}")
    # Een regel zonder datum is met de hand gezet en verliest van elke
    # waarneming met een datum, in welke volgorde hij ook staat.
    zonder_datum = ["Teststraat 1 | Nijmegen | 539000 | te koop",
                    "Teststraat 1 | Nijmegen | 539000 | verkocht | 2026-10-01 "
                    "| x | 135 | "]
    for volgorde, naam in ((zonder_datum, "zonder datum eerst"),
                           (zonder_datum[::-1], "zonder datum laatst")):
        if nog_te_koop(volgorde):
            fouten.append(f"met {naam} wint een regel zonder datum van een "
                          f"gedateerde waarneming")

    regels = ["Teststraat 1 | Nijmegen | 1 | verkocht | 2026-09-01 | x | 50 | ",
              "Teststraat 1 | Nijmegen | 1 | te koop | 2026-08-01 | x | 50 | "]
    gezien = eerst_gezien_per_adres(regels)
    if gezien.get(_sleutel("Teststraat 1")) != "2026-08-01":
        fouten.append(f"de eerste waarneming hoort de oudste datum te zijn, "
                      f"niet de laatste: {gezien}")
    sporen, telling = vergunningen_na_plaatsing(kaal, archief, gezien)
    if len(sporen) != 1 or sporen[0]["grondslag"] != "eerst gezien":
        fouten.append(f"met een eerste waarneming hoort het venster daarop te "
                      f"rusten: {sporen}")
    elif any((t.get("datum") or "") < "2026-08-01"
             for t in sporen[0]["bekendmakingen"]):
        fouten.append(f"een bekendmaking van voor de eerste waarneming kwam "
                      f"toch mee: {sporen[0]['bekendmakingen']}")

    print(f"Proef funda_verkocht_plak: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    ap.add_argument("--proef", action="store_true",
                    help="Alleen nameten, niets wegschrijven.")
    args = ap.parse_args()
    if args.proef:
        return proef()
    wis("verkocht")

    if not os.path.exists(PLAK_PAD):
        print(f"{PLAK_PAD} staat er niet; niets te doen", file=sys.stderr)
        return
    with open(PLAK_PAD, encoding="utf-8") as f:
        verkocht = parse(f.read())
    if not verkocht:
        leg_vast("verkocht", f"Geen verkochte woningen uit {PLAK_PAD} te halen. "
                             f"Is de opmaak van de pagina veranderd?")
        print("Niets gevonden", file=sys.stderr)
        return

    bestaand = lees_regels(UIT_PAD)
    te_koop = nog_te_koop(bestaand)
    kern = set()
    for r in bestaand:
        velden = [v.strip() for v in r.split("|")]
        if len(velden) >= 4:
            kern.add((_sleutel(velden[0]), velden[2], velden[3].lower()))

    datum = dt.date.today().isoformat()
    nieuw, alsnog_verkocht = [], []
    for w in verkocht:
        sl = _sleutel(w["adres"])
        if (sl, str(w["prijs"]), w.get("status") or "verkocht") in kern:
            continue
        nieuw.append(f"{w['adres']} | {w['plaats']} | {w['prijs']} | "
                     f"{w.get('status') or 'verkocht'} | "
                     f"{datum} | funda-verkocht-plak | {w['woonopp']} | "
                     f"{w['postcode'] or ''}")
        if sl in te_koop:
            alsnog_verkocht.append(w)

    if nieuw:
        with open(UIT_PAD, "a", encoding="utf-8") as f:
            f.write("\n".join(nieuw) + "\n")

    # De extra gegevens die niet in verkopen.txt passen
    try:
        with open(DETAIL_PAD, encoding="utf-8") as f:
            details = json.load(f)
    except Exception:
        details = {}
    eerste_regel = eerst_gezien_per_adres(bestaand)
    for w in verkocht:
        sl_det = _sleutel(w["adres"])
        # GEZIEN IS DE EERSTE KEER EN NIET VANDAAG. Hier stond "gezien":
        # datum, en omdat deze stap bij elke run hetzelfde plakbestand
        # opnieuw leest, kregen alle 575 adressen elke dag de datum van die
        # dag. Het veld zag er dus altijd uit als een verse waarneming van
        # een lijst die op 9 oktober voor het laatst is bijgewerkt.
        #
        # DE OUDSTE VAN DRIE EN NIET DE OPGESLAGEN WAARDE. Alleen de vorige
        # waarde overnemen zou de fout bevriezen: die staat voor alle 575
        # adressen op de dag van de laatste run. De regel in verkopen.txt
        # heeft wel een echte datum, dus we nemen de oudste van wat we
        # hebben. Daarmee herstelt het veld zichzelf en kan hij daarna nooit
        # meer vooruit lopen.
        kandidaten = [d for d in ((details.get(sl_det) or {}).get("gezien"),
                                  eerste_regel.get(sl_det), datum) if d]
        details[sl_det] = {
            "adres": w["adres"], "prijs": w["prijs"], "woonopp": w["woonopp"],
            "perceel": w["perceel"], "label": w["label"],
            "sinds_dagen": w["sinds_dagen"], "gezien": min(kandidaten),
            "laatst_gezien": datum, "url": w["url"],
            # Wie het pand verkocht. Niet wie het bezit, maar het enige wat we
            # over de partij erachter weten zonder het Kadaster.
            "makelaar": w.get("makelaar")}
    with open(DETAIL_PAD, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=1, sort_keys=True)

    try:
        with open(ARCHIEF_PAD, encoding="utf-8") as f:
            archief = json.load(f)
    except Exception:
        archief = {}
    sporen, venster = vergunningen_na_plaatsing(
        verkocht, archief, eerst_gezien_per_adres(bestaand))

    print(f"Verkocht: {len(verkocht)} woningen gelezen, {len(nieuw)} nieuw, "
          f"{len(alsnog_verkocht)} stonden bij ons nog te koop, "
          f"{len(sporen)} met een bekendmaking na plaatsing "
          f"({venster['uit_advertentie']} venster uit de advertentie, "
          f"{venster['uit_eerst_gezien']} uit de dag dat wij hem zagen, "
          f"{venster['zonder_venster']} overgeslagen zonder venster)",
          file=sys.stderr)
    for w in alsnog_verkocht:
        print(f"  stond nog te koop: {w['adres']} (€{w['prijs']:,})".replace(",", "."),
              file=sys.stderr)

    if args.uit and (alsnog_verkocht or sporen):
        r = ["# Verkochte woningen", ""]
        if alsnog_verkocht:
            r.append("_Deze panden stonden bij ons nog in het aanbod maar zijn op "
                     "Funda verkocht. Vendr meldt een verkoop niet._")
            for w in alsnog_verkocht:
                r.append(f"- **{w['adres']}**, laatste vraagprijs "
                         + f"€{w['prijs']:,}".replace(",", ".")
                         + f", {w['woonopp']} m2")
            r.append("")
        if sporen:
            r.append("_Bekendmakingen op een verkocht adres, binnen een venster "
                     "dat per adres achter de datum staat. Een aanwijzing dat de "
                     "koper iets met het pand doet, geen bewijs: het venster is "
                     "een benadering, en een bekendmaking kan ook van de vorige "
                     "eigenaar zijn._")
            for s in sporen:
                regels = "; ".join(f"{(t.get('datum') or '')[:10]} "
                                   f"{(t.get('titel') or '')[:90]}"
                                   for t in s["bekendmakingen"])
                # WAAR HET VENSTER OP RUST, IN DE BRIEF ZELF. Anders leest een
                # venster uit "Sinds 3 weken" hetzelfde als een venster uit de
                # dag dat wij de advertentie voor het eerst zagen, en dat zijn
                # twee verschillende beweringen.
                waarop = ("sinds het begin van de advertentie"
                          if s.get("grondslag") == "advertentie"
                          else "sinds de dag dat wij de advertentie zagen")
                r.append(f"- **{s['adres']}** (verkocht, laatste vraagprijs "
                         + f"€{s['prijs']:,}".replace(",", ".")
                         + f", {waarop}, vanaf {s['vanaf']}): {regels}")
        os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write("\n".join(r) + "\n")


if __name__ == "__main__":
    # sys.exit en niet main(): zonder dit geeft het proces altijd 0 terug, ook
    # als de proef rood staat, en is de poort in de workflow een formaliteit.
    sys.exit(main())
