#!/usr/bin/env python3
"""
Hoeveel objecten de beleidsregel over de eerste bouwlaag werkelijk raakt.

DE REGEL. Voor het toevoegen van woonruimte op de begane grond in het
kernwinkelgebied en de ringstraten van de Nijmeegse binnenstad geldt een
vergunningplicht. Een vergunning wordt alleen verleend als de woonruimte in
het achterste, van de straat onzichtbare deel van het pand komt en hoogstens
30% van de eerste bouwlaag beslaat, met een maximum van 50 m2. Bestaande
woningen blijven toegestaan, tenzij de eigenaar het pand naar een andere
functie transformeert.

DE REKENREGEL DIE DAARUIT VOLGT. De opbrengst per pand is min(30% van de
plint, 50). Die twee grenzen kruisen elkaar bij 50 / 0,30 = 166,7 m2. Een
plint onder 167 m2 levert dus minder dan de 50 m2 op, en bij 100 m2 plint is
het 30 m2. Dat is geen schatting maar de regel zelf, doorgerekend.

WAAR DE AANTALLEN VANDAAN KOMEN. voorraad_bag.py haalt de BAG per gebied op en
krijgt elk adres met oppervlakte, gebruiksdoel en pandidentificatie terug. De
adressen zonder woonfunctie werden geteld en weggegooid; sinds 10 oktober
staan ze onder "niet_woningen" in voorraad.json. Dat zijn de winkels, kantoren
en horeca. Er is geen extra vraag aan de BAG voor nodig: het antwoord kwam al
binnen.

DRIE VOORBEHOUDEN, EN ZE STAAN OOK IN DE BRIEF.

1. DE BAG KENT GEEN BOUWLAAG. Er is geen verdiepingsveld. Een winkelfunctie
   zit meestal in de plint, maar de BAG bevestigt dat niet. Daarom tellen we
   apart hoeveel van die objecten in een pand zitten waar ook woonfunctie-
   adressen in staan: een winkel onder woningen is vrijwel zeker de plint. Dat
   is de scherpste aanwijzing die uit een register te halen is, en het is een
   aanwijzing en geen vaststelling.

2. DE GEBIEDSGRENS IS EEN KAARTJE. Kernwinkelgebied en ringstraten staan op
   een kaart in de bijlage van het besluit, niet in een register. Zolang
   plintgebied.txt leeg is rekenen we over heel Stadscentrum, en dat is ruimer
   dan het gebied waar de regel geldt. Het getal is dan een bovengrens. Staan
   er straatnamen in dat bestand, dan rekenen we alleen over die straten en
   staat dat erbij.

3. DE OPPERVLAKTE IS DIE VAN HET HELE OBJECT. Een winkel die ook een kelder of
   een verdieping in gebruik heeft, heeft in de BAG één oppervlakte voor alles
   bij elkaar. De plint is dan kleiner dan het getal, en 30% daarvan dus ook.
   Deze telling is op dat punt optimistisch, en dat is precies de verkeerde
   kant, dus het staat erbij.

Gebruik:
  python plintregel.py              # de regel voor de brief
  python plintregel.py --toon       # met de tien grootste objecten erbij
  python plintregel.py --zelftest   # rekenen op verzonnen cijfers
"""

import argparse
import json
import os
import statistics
import sys

VOORRAAD = "voorraad.json"
GEBIED = "plintgebied.txt"
INVENTARIS = "buurtinventaris.json"

# Het gebied waar de regel over gaat, voor zover wij het kunnen afbakenen.
BUURT = "Stadscentrum"

# Uit de regel: hoogstens dit deel van de eerste bouwlaag, met dit maximum.
DEEL = 0.30
MAXIMUM_M2 = 50

# Onder deze plintmaat is de 30% de bindende grens en niet de 50 m2.
DREMPEL = MAXIMUM_M2 / DEEL  # 166,67

# Gebruiksdoelen die een economische plint kunnen zijn. Een gezondheidszorg-
# of onderwijsfunctie laten we erbuiten: die gaan niet over winkelvloer en de
# regel beschermt winkelvloer.
PLINTDOELEN = ("winkelfunctie", "kantoorfunctie", "bijeenkomstfunctie",
               "logiesfunctie", "industriefunctie")

# Onder dit aantal objecten publiceren we geen aandeel of mediaan. Hetzelfde
# idee als MIN_PAREN in pandgeschiedenis.py: een percentage over een handvol
# objecten is een getal dat nergens over gaat.
MIN_OBJECTEN = 20

# Onder deze dekking publiceren we helemaal geen aantal.
#
# WAAROM DIT ER MOEST KOMEN. De voorraad werd eerst per postcode gevuld met
# een tijdbudget, buurten op alfabet, en Stadscentrum stond achteraan. Na de
# eerste run was Stadscentrum dus maar half gedaan, en zonder deze drempel zou
# de brief zeggen "in heel Stadscentrum staan 60 objecten" terwijl dat de
# stand van een halve meting was. Een losse beoordelaar speelde dat na en zag
# ook dat "onder_woningen" dan stil op 0 blijft staan, omdat de panden met
# woonfunctie nog niet waren opgehaald.
#
# Sinds 10 oktober gaat het ophalen per gebied en is een hele ronde in 146,7
# seconden klaar, dus die geleidelijke opbouw bestaat niet meer. De drempel
# blijft staan voor het geval dat wél kan gebeuren: een ronde die halverwege
# afbreekt. Dat is nu ook wat dekking() meet, want de optelsom van opgehaalde
# postcodes staat na één geslaagde ronde permanent op volledig en zou een
# afgebroken ronde daarna nooit meer opmerken.
MIN_DEKKING = 0.90


def opbrengst(opp):
    """Hoeveel m2 woonruimte deze plint volgens de regel toelaat."""
    if not opp:
        return None
    return min(DEEL * opp, float(MAXIMUM_M2))


def straten_uit_gebied(pad=GEBIED):
    """
    De straatnamen waar de regel geldt, als iemand ze heeft ingevuld.

    Leeg bestand of geen bestand betekent: heel Stadscentrum, en dat staat
    dan als voorbehoud in de regel. Zo werkt dit nu al en wordt het scherper
    zodra de straatnamen van het kaartje erin staan, zonder dat er code bij
    hoeft.
    """
    if not os.path.exists(pad):
        return []
    straten = []
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                regel = regel.split("#")[0].strip()
                if regel:
                    straten.append(regel.lower())
    except Exception as e:
        print(f"Kon {pad} niet lezen: {e}", file=sys.stderr)
    return straten


def _straat(adres):
    """De straatnaam uit 'Broerstraat 12A', zonder huisnummer."""
    deel = (adres or "").rsplit(" ", 1)
    return deel[0].lower() if len(deel) == 2 else (adres or "").lower()


def dekking(voorraad, inventaris=None):
    """
    Hoeveel van de postcodes in het gebied werkelijk zijn opgehaald.

    Geeft (gedaan, totaal) terug. Zonder inventaris is het totaal onbekend en
    komt er (gedaan, 0) uit; dan publiceren we geen aantal, want we weten niet
    wat we missen.
    """
    if inventaris is None:
        try:
            with open(INVENTARIS, encoding="utf-8") as f:
                inventaris = json.load(f)
        except Exception:
            inventaris = {}
    alle = {(pc or "").replace(" ", "").upper()
            for pc in ((inventaris.get("postcodes_per_buurt") or {})
                       .get(BUURT) or [])}
    gedaan = voorraad.get("postcodes") or {}
    uit = sum(1 for pc in alle if pc in gedaan)

    # DE HUIDIGE RONDE WEEGT MEE, NIET ALLEEN DE OPTELSOM. voorraad["postcodes"]
    # werd alleen gevuld en stond na één geslaagde ronde permanent op volledig.
    # Een latere ronde die halverwege afbrak werd daardoor niet meer door deze
    # drempel opgemerkt, en het getal in de brief was dan een mengsel van verse
    # en oude records. Breekt de ronde van vandaag af, dan is de dekking die
    # van die ronde en niet die van de optelsom.
    bag = ((voorraad.get("laatste_ronde") or {}).get("bag") or {})
    if bag.get("ronde_paginas") and not bag.get("ronde_ronde_af"):
        vandaag = bag.get("postcodes_gedaan") or 0
        totaal = bag.get("postcodes_nijmegen") or bag.get("postcodes_totaal") or 0
        if totaal:
            # Dezelfde verhouding, toegepast op dit gebied.
            uit = min(uit, int(len(alle) * vandaag / totaal))
    return uit, len(alle)


def meet(voorraad=None, straten=None, inventaris=None):
    """
    De telling. Geeft een dict met uitsluitend gemeten of afgeleide getallen.

    Geen enkel getal hier is geschat: elk komt uit de BAG of volgt uit de
    rekenregel. Is er niets gemeten, dan staat dat er en komt er geen getal.
    """
    if voorraad is None:
        try:
            with open(VOORRAAD, encoding="utf-8") as f:
                voorraad = json.load(f)
        except Exception:
            return {"meetbaar": False, "reden": f"{VOORRAAD} bestaat nog niet"}
    if straten is None:
        straten = straten_uit_gebied()

    anders = voorraad.get("niet_woningen") or {}
    woningen = voorraad.get("adressen") or {}
    if not anders:
        return {"meetbaar": False,
                "reden": "nog geen niet-woonfunctie in de voorraad; "
                         "fase BAG moet eerst over Stadscentrum heen"}

    gedaan_pc, totaal_pc = dekking(voorraad, inventaris)
    if not totaal_pc:
        return {"meetbaar": False,
                "reden": f"de postcodes van {BUURT} staan niet in "
                         f"{INVENTARIS}, dus de dekking is niet te bepalen"}
    deel_gedaan = gedaan_pc / totaal_pc
    if deel_gedaan < MIN_DEKKING:
        return {"meetbaar": False, "gedaan_pc": gedaan_pc,
                "totaal_pc": totaal_pc,
                "reden": f"{BUURT} is pas voor "
                         f"{round(100 * deel_gedaan)}% opgehaald "
                         f"({gedaan_pc} van {totaal_pc} postcodes); onder "
                         f"{round(100 * MIN_DEKKING)}% publiceren we geen "
                         f"aantal, want een halve meting groeit nog"}

    # Welke panden bevatten woonfunctie-adressen? Dat is de aanwijzing dat een
    # winkel in dat pand de plint onder woningen is.
    panden_met_wonen = {r.get("pand") for r in woningen.values() if r.get("pand")}

    objecten, buiten_gebied, zonder_maat = [], 0, 0
    for r in anders.values():
        # BUURTEN EN NIET BUURT. Achtentwintig postcodes staan in twee
        # buurten, en toen de voorraad er één van koos was dat de eerste op
        # alfabet. Stadscentrum staat alfabetisch laatste van de zes, dus het
        # verloor er elke keer een: 24 van zijn 471 postcodes vielen uit deze
        # telling, in één richting en zonder dat de dekking erop reageerde.
        # Nu bewaart de voorraad alle buurten van een postcode en telt een
        # object mee zodra Stadscentrum erbij staat.
        if BUURT not in (r.get("buurten") or [r.get("buurt")]):
            continue
        if not any(d in PLINTDOELEN for d in (r.get("doelen") or [])):
            continue
        if straten and _straat(r.get("adres")) not in straten:
            buiten_gebied += 1
            continue
        if not r.get("oppervlakte"):
            zonder_maat += 1
            continue
        objecten.append(r)

    if not objecten:
        # Onderscheid maken tussen "er staat niets" en "het filter laat niets
        # door". Met een typefout in plintgebied.txt, bijvoorbeeld een
        # straatnaam met huisnummer erachter, valt alles buiten het gebied en
        # wijst de melding naar de gegevens terwijl het filter de oorzaak is.
        if straten and buiten_gebied:
            return {"meetbaar": False,
                    "reden": f"geen van de {buiten_gebied} plintobjecten in "
                             f"{BUURT} staat in een van de {len(straten)} "
                             f"straten uit {GEBIED}; staat daar een naam "
                             f"verkeerd of met een huisnummer erachter?"}
        return {"meetbaar": False,
                "reden": f"geen plintobjecten gevonden in {BUURT}"}

    maten = [float(r["oppervlakte"]) for r in objecten]
    volle_50 = [m for m in maten if m >= DREMPEL]
    onder_drempel = [m for m in maten if m < DREMPEL]
    onder_wonen = [r for r in objecten
                   if r.get("pand") in panden_met_wonen]

    uit = {
        "meetbaar": True,
        "gebied": (f"{len(straten)} straten uit {GEBIED}" if straten
                   else f"heel {BUURT}"),
        "gebied_is_ruimer": not straten,
        "objecten": len(objecten),
        "zonder_maat": zonder_maat,
        "buiten_gebied": buiten_gebied,
        "volle_50": len(volle_50),
        "onder_drempel": len(onder_drempel),
        "drempel_m2": round(DREMPEL),
        "onder_woningen": len(onder_wonen),
        "mediane_maat": round(statistics.median(maten)),
        "gedaan_pc": gedaan_pc,
        "totaal_pc": totaal_pc,
    }
    if len(onder_drempel) >= MIN_OBJECTEN:
        uit["mediane_opbrengst_onder_drempel"] = round(
            statistics.median(opbrengst(m) for m in onder_drempel))
    uit["te_klein_voor_aandeel"] = len(objecten) < MIN_OBJECTEN
    uit["grootste"] = sorted(objecten, key=lambda r: -float(r["oppervlakte"]))[:10]
    return uit


def regel(uit=None):
    """
    Het blok zoals het in de brief komt te staan, of een lege tekst.

    NIETS IN DE BRIEF ALS ER NIETS TE MELDEN IS. De eerste opzet schreef hier
    "Nog niet te meten: voorraad.json bestaat nog niet". Een bestandsnaam in
    een brief aan pa is precies waarom de voorstellenlijst er eerder uit is
    gehaald. De reden gaat nu naar de standaardfoutuitvoer, waar het logboek
    van de run en het gezondheidsrapport hem oppikken, en pa ziet niets.
    """
    if uit is None:
        uit = meet()
    if not uit.get("meetbaar"):
        print(f"Plintregel nog niet te meten: {uit.get('reden', 'onbekend')}",
              file=sys.stderr)
        return ""

    delen = [f"**Hoeveel panden dit raakt.** In {uit['gebied']} staan "
             f"{uit['objecten']} objecten met een winkel-, kantoor-, "
             f"bijeenkomst-, logies- of bedrijfsfunctie en een bekende "
             f"oppervlakte, met een mediane maat van {uit['mediane_maat']} m2."]

    if uit["onder_woningen"]:
        delen.append(f"Daarvan zitten {uit['onder_woningen']} in een pand "
                     f"waar ook woonadressen in staan, en dat is de "
                     f"scherpste aanwijzing dat het werkelijk een plint onder "
                     f"woningen is.")

    if not uit.get("te_klein_voor_aandeel"):
        delen.append(f"De regel laat hoogstens 30% van de eerste bouwlaag toe "
                     f"met een maximum van 50 m2, dus die 50 m2 is pas "
                     f"haalbaar vanaf {uit['drempel_m2']} m2 plint. Dat haalt "
                     f"{uit['volle_50']} van de {uit['objecten']} objecten; "
                     f"bij de andere {uit['onder_drempel']} is de 30% de "
                     f"bindende grens.")
        if uit.get("mediane_opbrengst_onder_drempel"):
            delen.append(f"Voor die groep komt de mediane opbrengst op "
                         f"{uit['mediane_opbrengst_onder_drempel']} m2 "
                         f"woonruimte per pand.")
    else:
        delen.append(f"Dat is te weinig om er een aandeel aan te hangen; de "
                     f"ondergrens staat op {MIN_OBJECTEN} objecten.")

    voorbehoud = ["De BAG kent geen bouwlaag, dus dat een object in de plint "
                  "zit volgt hier uit de functie en niet uit een registratie.",
                  "De oppervlakte is die van het hele object, dus van een "
                  "winkel met een kelder of een verdieping erbij is de plint "
                  "kleiner dan het getal en 30% daarvan ook."]
    if uit["gebied_is_ruimer"]:
        voorbehoud.insert(0, f"Kernwinkelgebied en ringstraten staan op een "
                             f"kaart en niet in een register, dus dit is heel "
                             f"{BUURT} en daarmee een bovengrens. Zet de "
                             f"straatnamen in {GEBIED} en dit wordt de "
                             f"werkelijke telling.")
    if uit["zonder_maat"]:
        voorbehoud.append(f"{uit['zonder_maat']} objecten hebben in de BAG "
                          f"geen oppervlakte en zitten hier niet in.")
    if uit["gedaan_pc"] < uit["totaal_pc"]:
        voorbehoud.append(f"Van de {uit['totaal_pc']} postcodes in {BUURT} "
                          f"zijn er {uit['gedaan_pc']} opgehaald, dus dit "
                          f"aantal kan nog oplopen.")

    return (" ".join(delen) + "\n\n_" + " ".join(voorbehoud) + "_")


def zelftest():
    """Rekenen op verzonnen cijfers, zodat de rekenregel toetsbaar is."""
    fout = 0

    # De rekenregel zelf.
    for opp, verwacht in ((100, 30.0), (166, 49.8), (167, 50.0), (500, 50.0),
                          (0, None), (None, None)):
        uit = opbrengst(opp)
        if uit != verwacht:
            print(f"AFWIJKING: opbrengst({opp}) gaf {uit}, verwacht {verwacht}")
            fout += 1
    if round(DREMPEL) != 167:
        print(f"AFWIJKING: drempel is {DREMPEL}, verwacht 167")
        fout += 1

    # Een nagemaakte voorraad: drie plinten in Stadscentrum waarvan twee onder
    # woningen, een winkel in een andere buurt, een object zonder maat en een
    # zorgfunctie die er niet in hoort.
    voorraad = {
        "adressen": {
            "broerstraat12": {"pand": "P1", "buurt": "Stadscentrum"},
            "broerstraat12a": {"pand": "P1", "buurt": "Stadscentrum"},
            "ziekerstraat5": {"pand": "P2", "buurt": "Stadscentrum"},
        },
        "niet_woningen": {
            "broerstraat14": {"adres": "Broerstraat 14", "buurt": "Stadscentrum",
                              "oppervlakte": 210, "doelen": ["winkelfunctie"],
                              "pand": "P1"},
            "ziekerstraat5a": {"adres": "Ziekerstraat 5A", "buurt": "Stadscentrum",
                               "oppervlakte": 100, "doelen": ["winkelfunctie"],
                               "pand": "P2"},
            "molenstraat8": {"adres": "Molenstraat 8", "buurt": "Stadscentrum",
                             "oppervlakte": 90, "doelen": ["kantoorfunctie"],
                             "pand": "P9"},
            "bottelstraat3": {"adres": "Bottelstraat 3", "buurt": "Bottendaal",
                              "oppervlakte": 300, "doelen": ["winkelfunctie"],
                              "pand": "P8"},
            "burchtstraat1": {"adres": "Burchtstraat 1", "buurt": "Stadscentrum",
                              "oppervlakte": None, "doelen": ["winkelfunctie"],
                              "pand": "P7"},
            "hertogstraat2": {"adres": "Hertogstraat 2", "buurt": "Stadscentrum",
                              "oppervlakte": 400,
                              "doelen": ["gezondheidszorgfunctie"], "pand": "P6"},
        },
    }
    # De postcodes van alle objecten staan als opgehaald in de voorraad, en de
    # inventaris noemt precies die postcodes. De dekking is dan 100%.
    voorraad["postcodes"] = {"6511AA": "2026-10-10", "6511AB": "2026-10-10"}
    inv = {"postcodes_per_buurt": {"Stadscentrum": ["6511AA", "6511AB"]}}

    uit = meet(voorraad, straten=[], inventaris=inv)
    verwacht = {"objecten": 3, "volle_50": 1, "onder_drempel": 2,
                "onder_woningen": 2, "zonder_maat": 1, "gebied_is_ruimer": True,
                "te_klein_voor_aandeel": True, "gedaan_pc": 2, "totaal_pc": 2,
                "mediane_maat": 100}
    for k, v in verwacht.items():
        if uit.get(k) != v:
            print(f"AFWIJKING: {k} gaf {uit.get(k)}, verwacht {v}")
            fout += 1

    # EEN POSTCODE IN TWEE BUURTEN. De voorraad bewaart sinds 10 oktober alle
    # buurten van een postcode in het veld buurten. Koos hij er één, dan was
    # dat de eerste op alfabet en verloor Stadscentrum er 24 van zijn 471,
    # altijd in dezelfde richting. Dit toetst dat een object met Stadscentrum
    # erbij meetelt en een object zonder Stadscentrum niet.
    met_buurten = json.loads(json.dumps(voorraad))
    met_buurten["niet_woningen"]["keizer9"] = {
        "adres": "Keizer Karelplein 9", "buurten": ["Benedenstad",
                                                    "Stadscentrum"],
        "oppervlakte": 120, "doelen": ["winkelfunctie"], "pand": "P5"}
    met_buurten["niet_woningen"]["elders1"] = {
        "adres": "Elders 1", "buurten": ["Benedenstad"],
        "oppervlakte": 120, "doelen": ["winkelfunctie"], "pand": "P4"}
    tweede = meet(met_buurten, straten=[], inventaris=inv)
    if tweede.get("objecten") != 4:
        print(f"AFWIJKING: met een postcode in twee buurten hoort het aantal "
              f"4 te zijn, werd {tweede.get('objecten')}")
        fout += 1

    # EEN AFGEBROKEN RONDE MOET DE DEKKING OMLAAG HALEN. De optelsom van
    # opgehaalde postcodes staat na één geslaagde ronde permanent op volledig
    # en zou een afgebroken ronde daarna nooit meer opmerken.
    afgebroken = json.loads(json.dumps(voorraad))
    afgebroken["laatste_ronde"] = {"bag": {
        "ronde_paginas": 40, "ronde_ronde_af": False,
        "postcodes_gedaan": 300, "postcodes_nijmegen": 1242}}
    gestopt = meet(afgebroken, straten=[], inventaris=inv)
    if gestopt.get("meetbaar") is not False:
        print("AFWIJKING: na een afgebroken ronde hoort er geen aantal te "
              "komen, want de voorraad is dan half vers en half oud")
        fout += 1

    # HALVE DEKKING: geen aantal. Dit is de bevinding van de losse beoordelaar:
    # Stadscentrum staat achteraan in de BAG-fase en is na de eerste run maar
    # half gedaan, en dan zou de brief een groeiend getal als stand brengen.
    half = meet(voorraad, straten=[],
                inventaris={"postcodes_per_buurt": {
                    "Stadscentrum": ["6511AA", "6511AB", "6511AC", "6511AD"]}})
    if half.get("meetbaar") is not False:
        print("AFWIJKING: bij halve dekking hoort er geen aantal te komen")
        fout += 1
    elif "50%" not in half.get("reden", ""):
        print(f"AFWIJKING: de reden noemt de dekking niet: {half.get('reden')}")
        fout += 1
    if regel(half) != "":
        print("AFWIJKING: bij halve dekking hoort de brief leeg te blijven")
        fout += 1

    # Zonder inventaris weten we niet wat we missen, dus ook geen aantal.
    blind = meet(voorraad, straten=[], inventaris={})
    if blind.get("meetbaar") is not False:
        print("AFWIJKING: zonder inventaris hoort er geen aantal te komen")
        fout += 1

    # Met een straatlijst erbij valt alles buiten die straten weg. Let op de
    # volgorde: de gebiedstoets gaat voor de maattoets, dus het object zonder
    # oppervlakte in de Burchtstraat telt hier als buiten het gebied en niet
    # als ontbrekende maat. Dat is de bedoeling: een object buiten het gebied
    # hoeft niet als gat in de meting te worden gemeld. Deze toets staat er om
    # die volgorde vast te pinnen.
    smal = meet(voorraad, straten=["broerstraat"], inventaris=inv)
    if smal.get("objecten") != 1 or smal.get("buiten_gebied") != 3:
        print(f"AFWIJKING: met straatlijst {smal.get('objecten')} objecten en "
              f"{smal.get('buiten_gebied')} buiten het gebied, verwacht 1 en 3")
        fout += 1
    if smal.get("zonder_maat") != 0:
        print(f"AFWIJKING: zonder_maat gaf {smal.get('zonder_maat')} in de "
              f"smalle variant, verwacht 0 want gebied gaat voor maat")
        fout += 1
    if smal.get("gebied_is_ruimer"):
        print("AFWIJKING: met een straatlijst is het gebied niet ruimer")
        fout += 1

    # Een straatlijst met een huisnummer erin: dan wijst de melding naar het
    # filter en niet naar de gegevens.
    typefout = meet(voorraad, straten=["broerstraat 12"], inventaris=inv)
    if typefout.get("meetbaar") is not False:
        print("AFWIJKING: met een onbruikbare straatlijst hoort er geen "
              "aantal te komen")
        fout += 1
    elif GEBIED not in typefout.get("reden", ""):
        print(f"AFWIJKING: de reden wijst niet naar {GEBIED}: "
              f"{typefout.get('reden')}")
        fout += 1

    # Zonder voorraad geen getal, geen uitzondering, en geen regel in de brief.
    leeg = meet({}, straten=[], inventaris=inv)
    if leeg.get("meetbaar") is not False:
        print("AFWIJKING: een lege voorraad hoort niet meetbaar te zijn")
        fout += 1
    if regel(leeg) != "":
        print("AFWIJKING: bij een lege voorraad hoort de brief leeg te blijven")
        fout += 1

    print(f"zelftest: {fout} afwijkend")
    return fout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--toon", action="store_true",
                   help="de tien grootste objecten erbij")
    p.add_argument("--zelftest", action="store_true")
    a = p.parse_args()
    if a.zelftest:
        return 1 if zelftest() else 0
    uit = meet()
    print(regel(uit))
    if a.toon and uit.get("grootste"):
        print("\nDe tien grootste:")
        for r in uit["grootste"]:
            print(f"  {r['adres']:34s} {r['oppervlakte']:>5} m2  "
                  f"{round(opbrengst(float(r['oppervlakte'])))} m2 toegestaan  "
                  f"{', '.join(r.get('doelen') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
