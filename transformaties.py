#!/usr/bin/env python3
"""
Woningen die in een bestaand pand worden gemaakt, als bron en niet als telling.

WAT DIT OPLOST. De pijplijnstap meldde 2.168 woningen onderweg naar de ring,
met een tabel per buurt en de drukste straten erbij. Op 12 oktober bleek wat
daar onder zat: 697 van die 2.168 zitten in een pand dat AL IN GEBRUIK is en
van voor 2021, dus het zijn nieuwe woningen in bestaande voorraad. En die 697
liggen niet verspreid maar in 113 panden, waarvan:

  191 woningen  pand uit 1955  Grote Markt 4A-1
   44 woningen  pand uit 1897  van Slichtenhorststraat 85
   35 woningen  pand uit 1881  Smetiusstraat 1B-1
   25 woningen  pand uit 1951  Plein 1944 151A-1
   25 woningen  pand uit 1881  Weurtseweg 3
   21 woningen  pand uit 1880  Eerste Walstraat 2A-1

De mediane oppervlakte is 50 m2 met een kwart onder 41 en een kwart boven 63,
en maar 45 van de 697 zijn kleiner dan 30 m2. Het zijn dus zelfstandige
appartementen en geen kamers.

WAAROM DAT EEN FOUT IN DE BRIEF WAS. "Stadscentrum, 446 onderweg" is een
getal dat verbergt dat er 191 in een gebouw zitten. Erger: van die 113 panden
kenden wij er 47 uit het bekendmakingenarchief en 66 niet. De vijf projecten
na Grote Markt, samen 150 woningen in panden uit 1880, 1881, 1897 en 1951,
hadden nul records en nul gebeurtenissen bij ons. Onze hele nieuwsketen hangt
aan publicaties: een bekendmaking komt binnen, wordt een gebeurtenis bij een
pand, en komt in de brief. De BAG vertelt over deze projecten zonder dat er
een publicatie langskwam, en dat signaal ging in een aggregaat.

Deze module maakt er een bron van. Een pand dat al in gebruik is en waarin de
BAG woningen heeft gevormd, krijgt een record en een gebeurtenis, langs
dezelfde weg als een bekendmaking. Daarna werkt de rest van de brief er
gewoon mee.

WAT HET NIET WEET. De BAG kent geen opleverdatum en geen vergunningnummer,
dus de gebeurtenis draagt de datum waarop WIJ het zagen en zegt dat ook. Hij
zegt niet wanneer er is verbouwd. En of het om splitsing, optoppen of een
hele transformatie gaat, staat nergens in de BAG: dat volgt uit het aantal en
de oppervlakte, en dat laat deze module aan de lezer.
"""
import argparse
import datetime as dt
import json
import re
import statistics as stat
import sys

import pandlezer as _pl
import pandsleutel as _psl

VOORRAAD = "voorraad.json"
GESCHIEDENIS = "pandgeschiedenis.json"

# WAAR HET VERSLAG VAN DE RONDE BLIJFT. De stap in de workflow staat achter
# een "|| echo", zoals alle blokstappen, en het verslag gaat naar stderr.
# Maar de log van een run is van buiten niet te lezen, dus een mislukte
# schrijfronde zou nergens opvallen: geen gebeurtenissen, geen melding, en
# een brief die er normaal uitziet. Dat is precies de fout van 10 oktober.
# Daarom komt de stand in een bestand dat de workflow terugcommit, en leest
# het gezondheidsrapport hem. Zelfde vorm als voorraad_stand.json.
STAND = "transformaties_stand.json"

# HOE OUD EEN PAND MOET ZIJN OM BESTAANDE VOORRAAD TE HETEN. Vijf jaar is een
# keuze en geen definitie van het CBS, en hij staat hier als getal zodat hij
# te veranderen is zonder de tekst te herschrijven. De reden voor een marge:
# een pand dat vorig jaar is opgeleverd en waarvan de laatste woningen nog
# niet in gebruik zijn gemeld, is nieuwbouw en geen transformatie. Gemeten op
# 12 oktober: van de 697 panden valt er geen enkele binnen die vijf jaar, dus
# de grens doet vandaag niets. Hij staat er voor de dag dat dat verandert.
JAREN_MARGE = 5

# De pandstatus die "het gebouw staat er al" betekent.
IN_GEBRUIK = ("Pand in gebruik", "Pand in gebruik (niet ingemeten)")

# HOEVEEL GEBEURTENISSEN EEN RONDE MAG MAKEN. Bij de eerste run zijn er 66
# panden die wij nog niet kennen. Die allemaal op een dag in de brief laten
# komen zou de brief zijn, en dan verdrinkt het nieuws van die dag. Grootste
# eerst, de rest de volgende dag; na een paar dagen is de achterstand weg en
# is dit getal nooit meer bindend. Zelfde vorm als MAX_BAG_PER_RONDE in
# pandgeschiedenis.py.
MAX_PER_RONDE = 25

# Het veld waarin staat met welk aantal dit pand al is gemeld. Zie verwerk().
GEMELD = "transformatie_gemeld"


def _jaar_grens(vandaag=None):
    """Een pand van voor dit jaartal heet bestaande voorraad."""
    return (vandaag or dt.date.today()).year - JAREN_MARGE


def projecten(voorraad, vandaag=None):
    """
    De panden met gevormde woningen erin, grootste eerst.

    Per pand: het aantal, het bouwjaar, de buurten, de adressen en de mediane
    oppervlakte. Alleen panden die al in gebruik zijn en van voor de grens,
    want een gevormde woning in een pand dat vergunning heeft of in bouw is,
    is nieuwbouw en staat al in het pijplijnblok.
    """
    grens = _jaar_grens(vandaag)
    per = {}
    for rec in (voorraad.get("pijplijn") or {}).values():
        if (rec.get("pand_status") or "") not in IN_GEBRUIK:
            continue
        jaar = rec.get("pand_bouwjaar")
        if not jaar or jaar >= grens:
            continue
        pid = rec.get("pand") or ""
        if not pid:
            # Zonder pandidentificatie is er geen project om bij te houden,
            # en een adres als sleutel zou twee panden kunnen samenvoegen.
            continue
        p = per.setdefault(pid, {"pand_id": pid, "bouwjaar": jaar,
                                 "adressen": [], "buurten": [],
                                 "oppervlaktes": []})
        p["adressen"].append(rec.get("adres") or "")
        for b in rec.get("buurten") or []:
            if b not in p["buurten"]:
                p["buurten"].append(b)
        if rec.get("oppervlakte"):
            p["oppervlaktes"].append(rec["oppervlakte"])
        # Het oudste bouwjaar houden als een pand meerdere jaren meegeeft.
        p["bouwjaar"] = min(p["bouwjaar"], jaar)

    uit = []
    for p in per.values():
        p["adressen"] = sorted(set(a for a in p["adressen"] if a))
        p["aantal"] = len(p["adressen"])
        p["adres"] = p["adressen"][0] if p["adressen"] else ""
        p["mediaan_m2"] = (round(stat.median(p["oppervlaktes"]))
                           if p["oppervlaktes"] else None)
        p["met_oppervlakte"] = len(p["oppervlaktes"])
        del p["oppervlaktes"]
        uit.append(p)
    # Grootste eerst, en bij gelijk aantal het oudste pand: dat is het
    # project waar het meeste aan is gebeurd.
    uit.sort(key=lambda p: (-p["aantal"], p["bouwjaar"], p["adres"]))
    return uit


def _record_van(geschiedenis, project):
    """
    Het bestaande record van dit pand, of (None, None).

    OP PAND_ID EERST EN PAS DAARNA OP ADRES. Een pand kan bij ons al staan
    onder een ánder adres dan het eerste gevormde object: Grote Markt 4A-1 is
    hetzelfde gebouw als Grote Markt 4. Zoeken op alleen het adres zou dan een
    tweede record voor hetzelfde pand maken, en dat is precies de fout die op
    11 oktober 1.777 records voor 1.721 panden opleverde.
    """
    pid = project["pand_id"]
    for sleutel, pand in geschiedenis.items():
        if isinstance(pand, dict) and pand.get("pand_id") == pid:
            return (sleutel, pand)
    # Geen record met dit pand-id. Dan nog op elk adres van het project
    # kijken, want een record kan er staan zonder dat het pand-id is gevuld.
    #
    # EN DAN HET PAND-ID VAN WAT WE VINDEN TOETSEN. Dit is een fout die de
    # eigen proef heeft gevangen: zonder deze toets vond de adresopzoeking
    # het record van een ANDER pand dat in onze sleutelvorm hetzelfde adres
    # oplevert, en kwam de gebeurtenis bij de buren te staan. Een opzoeking
    # vindt dit pand, of niets, nooit de buren. Een record zonder pand-id is
    # wel van ons: dat is er een uit het archief waar de BAG nog niet bij is
    # geweest.
    for adres in project["adressen"]:
        sleutel, pand = _psl.zoek_in(GESCHIEDENIS, geschiedenis, adres)
        if pand and (pand.get("pand_id") or pid) == pid:
            return (sleutel, pand)
    return (None, None)


def tekst_gebeurtenis(project, vandaag, eerder=None):
    """
    De gebeurtenis in woorden, met de grondslag erin.

    De BAG kent geen opleverdatum, dus deze tekst zegt wat wij zien en niet
    wanneer er is verbouwd. Dat onderscheid hoort in de tekst zelf te staan:
    een gebeurtenis met de datum van vandaag die klinkt als "vandaag
    verbouwd" is een valse mededeling aan pa.
    """
    n = project["aantal"]
    woning = "woning" if n == 1 else "woningen"
    m2 = (f", mediaan {project['mediaan_m2']} m2"
          if project["mediaan_m2"] else "")
    was = f", waren er {eerder}" if eerder is not None else ""
    return (f"in de BAG staan {n} {woning} als gevormd in dit pand uit "
            f"{project['bouwjaar']}, dat zelf al in gebruik is{m2}{was}. "
            f"Dat is bestaande voorraad waarin woningen worden toegevoegd. "
            f"De BAG kent geen opleverdatum, dus dit is wat er op "
            f"{vandaag} in de registratie staat")


RE_AANTAL = re.compile(r"staan (\d+) woning")


def opruimen(geschiedenis):
    """
    De dubbele transformatiegebeurtenissen weghalen, oudste eerst behouden.

    WAAROM DIT ER IS. Tot 13 oktober leunde verwerk() op de datum in de
    tekst, en daardoor kreeg hetzelfde pand elke dag opnieuw dezelfde
    melding. In pandgeschiedenis.json stonden daardoor 25 gebeurtenissen van
    12 oktober en dezelfde 25 van 13 oktober. Alleen de code repareren laat
    die dubbelen staan, en dan leest het dossier van zo'n pand alsof er twee
    keer iets is gebeurd.

    De OUDSTE blijft staan, want die datum is wanneer wij het voor het eerst
    zagen, en dat is wat de gebeurtenis beweert. Het gemelde aantal wordt op
    het record gezet, zodat de volgende ronde dit pand overslaat in plaats
    van het opnieuw te melden.

    Geeft een verslag dat optelt. Klopt de telling niet, dan staat dat erin:
    een opruiming die meer weghaalt dan hij zegt, is erger dan geen opruiming.
    """
    verslag = {"records": 0, "voor": 0, "weg": 0, "na": 0, "gemeld_gezet": 0}
    for pand in geschiedenis.values():
        if not isinstance(pand, dict):
            continue
        geb = pand.get("gebeurtenissen") or []
        tr = [g for g in geb if g.get("soort") == "transformatie"]
        if not tr:
            continue
        verslag["records"] += 1
        verslag["voor"] += len(tr)
        gezien, houden, weg = {}, [], []
        for g in sorted(tr, key=lambda x: x.get("datum") or ""):
            m = RE_AANTAL.search(g.get("tekst") or "")
            aantal = m.group(1) if m else g.get("tekst")
            if aantal in gezien:
                weg.append(g)
            else:
                gezien[aantal] = g
                houden.append(g)
        if weg:
            pand["gebeurtenissen"] = [g for g in geb if g not in weg]
            verslag["weg"] += len(weg)
        verslag["na"] += len(houden)
        # Het laatst gemelde aantal vastleggen.
        laatste = sorted(houden, key=lambda x: x.get("datum") or "")[-1]
        m = RE_AANTAL.search(laatste.get("tekst") or "")
        if m and pand.get(GEMELD) != int(m.group(1)):
            pand[GEMELD] = int(m.group(1))
            verslag["gemeld_gezet"] += 1
    verslag["telt_op"] = (verslag["voor"] - verslag["weg"] == verslag["na"])
    return verslag


def verwerk(geschiedenis, voorraad, vandaag=None, maximaal=MAX_PER_RONDE):
    """
    De projecten als records en gebeurtenissen in de pandgeschiedenis zetten.

    Geeft een verslag met harde aantallen.

    WAT AL GEMELD IS, STAAT IN HET RECORD EN NIET IN DE GEBEURTENIS. Dit is
    de fout van 13 oktober. Eerst leunde deze functie op voeg_toe(), dat
    vergelijkt op datum, soort en tekst. De tekst bevat de datum van vandaag,
    dus op een nieuwe dag was elke melding "nieuw": dezelfde 25 panden kregen
    elke dag opnieuw een gebeurtenis met hetzelfde aantal, en omdat die 25 het
    budget opmaakten kwamen de andere 88 nooit aan de beurt. Precies het
    omgekeerde van waar deze stap voor is. Gemeten: 25 gebeurtenissen op
    12 oktober en dezelfde 25 op 13 oktober, overgeslagen bleef 88 staan.

    En de proef zag het niet, omdat die twee rondes op dezelfde dag deed. Een
    controle die de variatie niet uitvoert die de fout veroorzaakt, meet niets.

    Nu staat het gemelde aantal als veld op het record. Is dat gelijk aan wat
    we nu zien, dan is dit pand klaar en kost het geen budget, zodat de rij
    opschuift. Is het gegroeid, dan is dat nieuws en komt er een gebeurtenis
    met het oude aantal erin.
    """
    vandaag = (vandaag or dt.date.today()).isoformat()
    try:
        from pandgeschiedenis import voeg_toe
    except Exception as e:  # pragma: no cover
        return {"fout": f"pandgeschiedenis niet te importeren: {str(e)[:60]}"}

    verslag = {"projecten": 0, "woningen": 0, "panden_nieuw": 0,
               "panden_bekend": 0, "gebeurtenissen": 0, "overgeslagen": 0,
               "al_gemeld": 0, "sleutel_bezet": 0, "gegroeid": 0}
    lijst = projecten(voorraad, dt.date.fromisoformat(vandaag))
    verslag["projecten"] = len(lijst)
    verslag["woningen"] = sum(p["aantal"] for p in lijst)

    gedaan = 0
    for project in lijst:
        sleutel, pand = _record_van(geschiedenis, project)
        # AL GEMELD MET DIT AANTAL? Dan is dit pand klaar, en het kost geen
        # budget: daardoor schuift de rij op naar de panden die nog niet
        # gemeld zijn.
        if pand is not None and pand.get(GEMELD) == project["aantal"]:
            verslag["al_gemeld"] += 1
            continue
        eerder = (pand or {}).get(GEMELD)
        tekst = tekst_gebeurtenis(project, vandaag, eerder)
        if pand is None:
            if gedaan >= maximaal:
                verslag["overgeslagen"] += 1
                continue
            nieuwe = _psl.sleutel(project["adres"])
            if not nieuwe:
                verslag["overgeslagen"] += 1
                continue
            if nieuwe in geschiedenis:
                # DE SLEUTEL IS AL VAN EEN ANDER PAND. Dat kan: twee panden
                # kunnen hetzelfde adres in onze sleutelvorm opleveren. Dan
                # niets overschrijven, maar het melden. Een opzoeking vindt
                # dit pand of niets, nooit de buren.
                verslag["sleutel_bezet"] += 1
                continue
            pand = {"adres": project["adres"], "gebeurtenissen": [],
                    "pand_id": project["pand_id"]}
            geschiedenis[nieuwe] = pand
            verslag["panden_nieuw"] += 1
        else:
            verslag["panden_bekend"] += 1
            # Een bestaand record zonder pand-id krijgt het erbij, zodat de
            # volgende ronde hem op pand_id vindt in plaats van op adres.
            if not pand.get("pand_id"):
                pand["pand_id"] = project["pand_id"]
            pand.setdefault("gebeurtenissen", [])
            if gedaan >= maximaal:
                verslag["overgeslagen"] += 1
                continue
        if voeg_toe(pand, vandaag, "transformatie", tekst, "BAG"):
            # Het gemelde aantal vastleggen, anders komt dit pand morgen
            # opnieuw aan de beurt met hetzelfde nieuws.
            pand[GEMELD] = project["aantal"]
            verslag["gebeurtenissen"] += 1
            if eerder is not None:
                verslag["gegroeid"] += 1
            gedaan += 1
        else:
            verslag["al_gemeld"] += 1
    return verslag


def tekst(voorraad, geschiedenis=None, vandaag=None, hoeveel=12):
    """
    Het blok voor de brief: de projecten, grootste eerst.

    WAT HIER ANDERS IS DAN IN HET PIJPLIJNBLOK. Dat blok telt per buurt en
    per straat. Dit blok telt per PAND, want daar zit de concentratie: 191
    van de 446 in Stadscentrum zitten in een gebouw. Een gemiddelde per buurt
    verbergt dat, en dan leest de brief als een gelijkmatige stroom terwijl
    het een paar projecten zijn.
    """
    lijst = projecten(voorraad, vandaag)
    if not lijst:
        return ""
    totaal = sum(p["aantal"] for p in lijst)
    grens = _jaar_grens(vandaag)
    r = ["## Woningen die in bestaande panden worden gemaakt", ""]
    onbekend = None
    if isinstance(geschiedenis, dict):
        onbekend = sum(1 for p in lijst if _record_van(geschiedenis, p)[1] is None)
    r.append(f"_{totaal} woningen staan in de BAG als gevormd in een pand dat "
             f"zelf al in gebruik is en van voor {grens}. Dat is bestaande "
             f"voorraad waarin woningen worden toegevoegd, en het staat los "
             f"van de nieuwbouw in het pijplijnblok. Ze liggen in "
             f"{len(lijst)} panden."
             + (f" Van die panden kenden wij {onbekend} nog niet uit de "
                f"bekendmakingen." if onbekend else "")
             + " De BAG kent geen opleverdatum, dus hier staat niet wanneer "
               "ze klaar zijn._")
    r.append("")
    r.append("| pand | woningen | bouwjaar | mediaan m2 | buurt |")
    r.append("|---|---:|---:|---:|---|")
    for p in lijst[:hoeveel]:
        m2 = p["mediaan_m2"] if p["mediaan_m2"] else "onbekend"
        r.append(f"| {p['adres']} | {p['aantal']} | {p['bouwjaar']} | {m2} | "
                 f"{', '.join(p['buurten']) or 'onbekend'} |")
    r.append("")
    if len(lijst) > hoeveel:
        rest = sum(p["aantal"] for p in lijst[hoeveel:])
        r.append(f"De overige {len(lijst) - hoeveel} panden hebben samen "
                 f"{rest} woningen.")
        r.append("")
    # DE OPPERVLAKTE ZEGT OF HET KAMERS OF APPARTEMENTEN ZIJN, en dat is het
    # verschil tussen verkamering en appartementisering. Zonder dit getal
    # leest "woningen toegevoegd" als allebei.
    alle = [p["mediaan_m2"] for p in lijst if p["mediaan_m2"]]
    if alle:
        klein = sum(1 for p in lijst if p["mediaan_m2"] and p["mediaan_m2"] < 30)
        r.append(f"_De mediaan van de mediane oppervlakte per pand is "
                 f"{round(stat.median(alle))} m2. Bij {klein} van de "
                 f"{len(alle)} panden ligt die mediaan onder 30 m2; daar gaat "
                 f"het waarschijnlijk om kamers en niet om zelfstandige "
                 f"woningen. Wat het juridisch is, zegt de BAG niet._")
        r.append("")
    return "\n".join(r)


def proef():
    """
    Nameten op verzonnen gegevens, en daarna op de echte voorraad.

    Wat hier wordt gemeten is niet of de aantallen kloppen maar of de
    afbakening klopt: nieuwbouw hoort hier NIET bij, een pand zonder
    identificatie ook niet, en een pand dat wij al kennen hoort geen tweede
    record te krijgen. Dat laatste is de fout die 1.777 records voor 1.721
    panden opleverde.
    """
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    nu = dt.date(2026, 10, 12)
    voorraad = {"pijplijn": {
        # Drie woningen in een pand uit 1881 dat al in gebruik is: dit is het
        # geval waar het om gaat.
        "v1": {"adres": "Oudestraat 1", "pand": "P1", "pand_status":
               "Pand in gebruik", "pand_bouwjaar": 1881, "oppervlakte": 48,
               "buurten": ["Benedenstad"]},
        "v2": {"adres": "Oudestraat 1A", "pand": "P1", "pand_status":
               "Pand in gebruik", "pand_bouwjaar": 1881, "oppervlakte": 52,
               "buurten": ["Benedenstad"]},
        "v3": {"adres": "Oudestraat 1B", "pand": "P1", "pand_status":
               "Pand in gebruik", "pand_bouwjaar": 1881, "oppervlakte": 60,
               "buurten": ["Benedenstad"]},
        # Nieuwbouw: pand met vergunning. Hoort hier niet bij.
        "v4": {"adres": "Nieuwstraat 1", "pand": "P2", "pand_status":
               "Bouwvergunning verleend", "pand_bouwjaar": 2026,
               "oppervlakte": 70, "buurten": ["Biezen"]},
        # Pand dat in gebruik is maar van dit jaar: de staart van de
        # nieuwbouw, en dus geen transformatie.
        "v5": {"adres": "Verstraat 1", "pand": "P3", "pand_status":
               "Pand in gebruik", "pand_bouwjaar": 2026, "oppervlakte": 70,
               "buurten": ["Biezen"]},
        # Zonder pandidentificatie valt er geen project bij te houden.
        "v6": {"adres": "Losstraat 1", "pand": "", "pand_status":
               "Pand in gebruik", "pand_bouwjaar": 1900, "oppervlakte": 40,
               "buurten": ["Biezen"]},
        # Een enkele woning in een oud pand: hoort er wel bij, want een
        # toegevoegde woning is het signaal, ook als het er een is.
        "v7": {"adres": "Kleinstraat 2", "pand": "P4", "pand_status":
               "Pand in gebruik", "pand_bouwjaar": 1935, "oppervlakte": 25,
               "buurten": ["Bottendaal"]},
    }}

    lijst = projecten(voorraad, nu)
    check("alleen bestaande panden met een pand-id",
          [p["pand_id"] for p in lijst], ["P1", "P4"])
    check("grootste eerst", lijst[0]["aantal"], 3)
    check("de adressen van het project", lijst[0]["adressen"],
          ["Oudestraat 1", "Oudestraat 1A", "Oudestraat 1B"])
    check("de mediane oppervlakte", lijst[0]["mediaan_m2"], 52)
    check("een enkele woning telt mee", lijst[1]["aantal"], 1)

    # EEN PAND DAT WIJ AL KENNEN KRIJGT GEEN TWEEDE RECORD, ook niet als het
    # bij ons onder een ander adres staat dan het eerste gevormde object.
    geschiedenis = {
        "oudestraat1": {"adres": "Oudestraat 1", "pand_id": "P1",
                        "gebeurtenissen": []},
    }
    verslag = verwerk(geschiedenis, voorraad, nu)
    check("geen fout", verslag.get("fout"), None)
    check("twee projecten gezien", verslag["projecten"], 2)
    check("vier woningen", verslag["woningen"], 4)
    check("een pand kenden wij al", verslag["panden_bekend"], 1)
    check("en een is nieuw", verslag["panden_nieuw"], 1)
    check("twee gebeurtenissen", verslag["gebeurtenissen"], 2)
    check("het bestaande record is niet verdubbeld",
          sum(1 for p in geschiedenis.values()
              if p.get("pand_id") == "P1"), 1)
    check("het nieuwe record staat onder zijn canonieke sleutel",
          "kleinstraat2" in geschiedenis, True)

    # DE GEBEURTENIS ZEGT WAT WIJ ZIEN EN NIET WANNEER ER IS VERBOUWD.
    g = geschiedenis["oudestraat1"]["gebeurtenissen"][0]
    check("de datum is van vandaag", g["datum"], "2026-10-12")
    check("de bron is de BAG", g["bron"], "BAG")
    check("de tekst noemt het aantal", "3 woningen" in g["tekst"], True)
    check("de tekst noemt het bouwjaar", "1881" in g["tekst"], True)
    check("de tekst zegt dat er geen opleverdatum is",
          "geen opleverdatum" in g["tekst"], True)

    # TWEE KEER DRAAIEN MAG GEEN TWEEDE MELDING GEVEN. Anders staat er elke
    # dag hetzelfde pand in de brief.
    tweede = verwerk(geschiedenis, voorraad, nu)
    check("tweede ronde maakt geen gebeurtenis", tweede["gebeurtenissen"], 0)
    check("tweede ronde ziet ze als al gemeld", tweede["al_gemeld"], 2)
    check("en maakt geen records", tweede["panden_nieuw"], 0)

    # EN OP EEN NIEUWE DAG OOK NIET. DIT IS DE CONTROLE DIE ONTBRAK. De
    # proef deed twee rondes op dezelfde dag, en voeg_toe() vergelijkt op
    # datum, soort en tekst, dus op dezelfde dag was het dubbel en op een
    # nieuwe dag niet. Daardoor kregen dezelfde 25 panden elke dag opnieuw
    # een gebeurtenis en kwamen de andere 88 nooit aan de beurt.
    morgen = nu + dt.timedelta(days=1)
    derde = verwerk(geschiedenis, voorraad, morgen)
    check("op een nieuwe dag komt er geen tweede melding",
          derde["gebeurtenissen"], 0)
    check("en ze staan als al gemeld", derde["al_gemeld"], 2)

    # EN HET BUDGET SCHUIFT OP. Dit is het gevolg dat het ergste was: de
    # grootste panden stonden vooraan, maakten elke dag het budget op, en de
    # rest kwam nooit. Acht panden, drie per ronde: de tweede ronde hoort de
    # VOLGENDE drie te doen en niet dezelfde.
    veel2 = {"pijplijn": {}}
    for i in range(8):
        veel2["pijplijn"][f"q{i}"] = {
            "adres": f"Rijstraat {i + 1}", "pand": f"Q{i}",
            "pand_status": "Pand in gebruik", "pand_bouwjaar": 1900,
            # Aflopend, zodat de volgorde vastligt en de rij meetbaar is.
            "oppervlakte": 40, "buurten": ["Biezen"]}
    gesch2 = {}
    r1 = verwerk(gesch2, veel2, nu, maximaal=3)
    gemeld1 = sorted(p["adres"] for p in gesch2.values()
                     if p.get("transformatie_gemeld"))
    r2 = verwerk(gesch2, veel2, nu + dt.timedelta(days=1), maximaal=3)
    gemeld2 = sorted(p["adres"] for p in gesch2.values()
                     if p.get("transformatie_gemeld"))
    check("eerste ronde meldt drie", r1["gebeurtenissen"], 3)
    check("tweede ronde meldt de volgende drie", r2["gebeurtenissen"], 3)
    check("en samen zijn het zes verschillende panden", len(gemeld2), 6)
    check("de eerste drie zitten er nog bij",
          all(a in gemeld2 for a in gemeld1), True)
    check("en er wachten nog twee", r2["overgeslagen"], 2)

    # GROEIT HET AANTAL, DAN IS HET WEL NIEUWS.
    voorraad["pijplijn"]["v8"] = {
        "adres": "Oudestraat 1C", "pand": "P1", "pand_status":
        "Pand in gebruik", "pand_bouwjaar": 1881, "oppervlakte": 55,
        "buurten": ["Benedenstad"]}
    derde = verwerk(geschiedenis, voorraad, nu)
    check("een vierde woning is wel nieuws", derde["gebeurtenissen"], 1)
    check("en de tekst noemt vier",
          "4 woningen" in geschiedenis["oudestraat1"]["gebeurtenissen"][-1]["tekst"],
          True)

    # DE OPRUIMING VAN DE DUBBELEN DIE ER AL STAAN.
    dubbel = {"a": {"adres": "Dubbelstraat 1", "pand_id": "D1",
                    "gebeurtenissen": [
                        {"datum": "2026-10-12", "soort": "transformatie",
                         "tekst": "in de BAG staan 21 woningen als gevormd",
                         "bron": "BAG"},
                        {"datum": "2026-10-13", "soort": "transformatie",
                         "tekst": "in de BAG staan 21 woningen als gevormd",
                         "bron": "BAG"},
                        {"datum": "2026-10-13", "soort": "bekendmaking",
                         "tekst": "iets anders", "bron": "gemeente"},
                    ]}}
    v_op = opruimen(dubbel)
    check("de opruiming telt op", v_op["telt_op"], True)
    check("een van de twee gaat weg", v_op["weg"], 1)
    over = [g["datum"] for g in dubbel["a"]["gebeurtenissen"]
            if g["soort"] == "transformatie"]
    check("de oudste blijft staan", over, ["2026-10-12"])
    check("de andere soort blijft onaangeroerd",
          sum(1 for g in dubbel["a"]["gebeurtenissen"]
              if g["soort"] == "bekendmaking"), 1)
    check("en het gemelde aantal is vastgelegd",
          dubbel["a"].get("transformatie_gemeld"), 21)
    # EEN GEGROEID AANTAL IS GEEN DUBBELE: die twee blijven beide staan.
    gegroeid = {"a": {"adres": "Groeistraat 1", "pand_id": "G1",
                      "gebeurtenissen": [
                          {"datum": "2026-10-12", "soort": "transformatie",
                           "tekst": "in de BAG staan 21 woningen als gevormd",
                           "bron": "BAG"},
                          {"datum": "2026-10-20", "soort": "transformatie",
                           "tekst": "in de BAG staan 24 woningen als gevormd",
                           "bron": "BAG"},
                      ]}}
    v_g = opruimen(gegroeid)
    check("een groei blijft staan", v_g["weg"], 0)
    check("en het laatste aantal wordt vastgelegd",
          gegroeid["a"].get("transformatie_gemeld"), 24)

    # DE BEZETTE SLEUTEL. Een nieuw pand waarvan de sleutel al van een ander
    # pand is, wordt niet overschreven maar gemeld.
    bezet = {"kleinstraat2": {"adres": "Kleinstraat 2", "pand_id": "ANDER",
                              "gebeurtenissen": []}}
    v_bezet = {"pijplijn": {"x": dict(voorraad["pijplijn"]["v7"],
                                      pand="P9")}}
    verslag_b = verwerk(bezet, v_bezet, nu)
    check("een bezette sleutel wordt niet overschreven",
          bezet["kleinstraat2"]["pand_id"], "ANDER")
    check("en hij wordt gemeld", verslag_b["sleutel_bezet"], 1)

    # HET MAXIMUM PER RONDE. Bij de eerste run zijn er 66 onbekende panden;
    # die allemaal op een dag melden zou de brief zijn.
    veel = {"pijplijn": {}}
    for i in range(8):
        veel["pijplijn"][f"m{i}"] = {
            "adres": f"Maxstraat {i + 1}", "pand": f"M{i}",
            "pand_status": "Pand in gebruik", "pand_bouwjaar": 1900,
            "oppervlakte": 45, "buurten": ["Biezen"]}
    leeg = {}
    verslag_m = verwerk(leeg, veel, nu, maximaal=3)
    check("niet meer dan het maximum", verslag_m["gebeurtenissen"], 3)
    check("de rest wordt overgeslagen en geteld",
          verslag_m["overgeslagen"], 5)
    check("en er komen niet meer records dan meldingen",
          verslag_m["panden_nieuw"], 3)

    # HET BLOK.
    blok = tekst(voorraad, geschiedenis, nu)
    check("het blok noemt het grootste pand eerst",
          blok.index("Oudestraat 1") < blok.index("Kleinstraat 2"), True)
    check("het blok noemt de mediane oppervlakte", "mediaan" in blok, True)
    check("het blok zegt dat er geen opleverdatum is",
          "geen opleverdatum" in blok, True)
    check("zonder projecten geen blok", tekst({"pijplijn": {}}, {}, nu), "")

    # HET VOORBEHOUD UIT HET BLOK MOET OOK IN DE SCHRIJFINSTRUCTIE STAAN.
    # Dit is de eis "de brief spreekt zichzelf niet tegen", en op 11 oktober
    # ging het daar mis: een voorbehoud stond in het blok en het omgekeerde
    # in de openingsalinea. Hier is het voorbehoud dat de BAG geen
    # opleverdatum kent. Staat dat niet in brief_verhalend.py, dan kan het
    # verhaal schrijven dat er vandaag is opgeleverd, en dat is onjuist.
    blok_voorbehoud = "geen opleverdatum"
    if blok_voorbehoud not in blok:
        fouten.append(f"het blok noemt {blok_voorbehoud!r} niet; dan is er "
                      f"niets om de schrijfinstructie aan te binden")
    try:
        with open("brief_verhalend.py", encoding="utf-8") as f:
            instructie = f.read()
    except Exception as e:
        fouten.append(f"brief_verhalend.py niet te lezen: {str(e)[:40]}")
        instructie = ""
    if instructie and blok_voorbehoud not in instructie:
        fouten.append(f"brief_verhalend.py noemt {blok_voorbehoud!r} niet, "
                      f"terwijl het blok dat wel doet; dan kan het verhaal "
                      f"schrijven dat er vandaag is opgeleverd")
    # En de drempel waarboven zo'n pand de brief mag openen. Zonder drempel
    # gaat de brief vijf ochtenden over hetzelfde soort nieuws.
    if instructie and "tien of meer toegevoegde woningen" not in instructie:
        fouten.append("brief_verhalend.py noemt geen drempel waarboven een "
                      "pand de brief mag openen; met 113 panden opent de "
                      "brief dan dagen achter elkaar hierover")

    # EN DAN OP DE ECHTE VOORRAAD, zonder iets te schrijven. Hier wordt niet
    # getoetst hoeveel het zijn maar dat het draait en dat de afbakening
    # dezelfde uitkomst geeft als de meting van 12 oktober: alle projecten
    # zitten in panden van voor de grens.
    try:
        with open(VOORRAAD, encoding="utf-8") as f:
            echt = json.load(f)
    except Exception:
        echt = None
    if echt:
        lijst = projecten(echt)
        grens = _jaar_grens()
        te_nieuw = [p for p in lijst if p["bouwjaar"] >= grens]
        if te_nieuw:
            fouten.append(f"{len(te_nieuw)} projecten in een pand van "
                          f"{grens} of later; die horen bij de nieuwbouw")
        zonder = [p for p in lijst if not p["pand_id"]]
        if zonder:
            fouten.append(f"{len(zonder)} projecten zonder pand-id")
        if lijst:
            print(f"Echte voorraad: {len(lijst)} panden, "
                  f"{sum(p['aantal'] for p in lijst)} woningen, grootste "
                  f"{lijst[0]['aantal']} in {lijst[0]['adres']} uit "
                  f"{lijst[0]['bouwjaar']}", file=sys.stderr)

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten. Gedekt: de afbakening (nieuwbouw en "
          f"een pand zonder identificatie vallen erbuiten), een pand dat wij "
          f"al kennen krijgt geen tweede record, een bezette sleutel wordt "
          f"niet overschreven, twee keer draaien geeft een melding en een "
          f"groter aantal wel, het maximum per ronde, het blok, en dat het "
          f"voorbehoud uit het blok ook in de schrijfinstructie staat, dat "
          f"een tweede ronde OP EEN NIEUWE DAG niets meldt en de rij "
          f"opschuift, en de opruiming van de dubbelen die er al staan. "
          f"Plus de "
          f"echte voorraad, zonder te schrijven.", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proef", action="store_true",
                    help="De afbakening en het schrijven nameten.")
    ap.add_argument("--uit", default="",
                    help="Het blok voor de brief hierheen schrijven.")
    ap.add_argument("--droog", action="store_true",
                    help="Wel tellen, niets naar de pandgeschiedenis.")
    ap.add_argument("--maximaal", type=int, default=MAX_PER_RONDE,
                    help=f"Gebeurtenissen per ronde. Standaard {MAX_PER_RONDE}.")
    a = ap.parse_args()
    if a.proef:
        return proef()

    try:
        with open(VOORRAAD, encoding="utf-8") as f:
            voorraad = json.load(f)
    except Exception as e:
        print(f"{VOORRAAD} niet te lezen: {str(e)[:60]}", file=sys.stderr)
        return 1

    geschiedenis = _pl.laad(GESCHIEDENIS)
    if not geschiedenis:
        print(f"{GESCHIEDENIS} is leeg of niet te lezen; niets geschreven",
              file=sys.stderr)
        return 1

    if a.uit:
        blok = tekst(voorraad, geschiedenis)
        with open(a.uit, "w", encoding="utf-8") as f:
            f.write(blok)
        print(f"Blok van {len(blok)} tekens naar {a.uit}", file=sys.stderr)

    # EERST OPRUIMEN. Zie opruimen(): tot 13 oktober kreeg hetzelfde pand
    # elke dag opnieuw dezelfde melding. Klopt de telling van die opruiming
    # niet, dan wordt er niets geschreven: een opruiming die meer weghaalt
    # dan hij zegt, is erger dan geen opruiming.
    schoon = opruimen(geschiedenis)
    if not schoon["telt_op"]:
        print(f"FOUT de opruiming telt niet op: {json.dumps(schoon)}; "
              f"niets geschreven", file=sys.stderr)
        return 1
    if schoon["weg"] or schoon["gemeld_gezet"]:
        print("Opruiming: " + json.dumps(schoon, ensure_ascii=False),
              file=sys.stderr)

    verslag = verwerk(geschiedenis, voorraad, maximaal=a.maximaal)
    verslag["opgeruimd"] = schoon["weg"]
    if verslag.get("fout"):
        print(f"FOUT {verslag['fout']}", file=sys.stderr)
        return 1
    print("Transformaties: " + json.dumps(verslag, ensure_ascii=False),
          file=sys.stderr)
    # DE STAND NAAR SCHIJF, OOK ALS ER NIETS VERANDERDE. Een stand die alleen
    # wordt geschreven als er iets gebeurde, is niet te onderscheiden van een
    # stap die niet heeft gedraaid.
    try:
        # DROOG STAAT ERIN. Een droge run telt wat er ZOU gebeuren, en een
        # stand die 25 gebeurtenissen meldt terwijl er niets is geschreven,
        # is dezelfde valse mededeling als een stille mislukking.
        with open(STAND, "w", encoding="utf-8") as f:
            json.dump({"datum": dt.date.today().isoformat(),
                       "droog": bool(a.droog), "ronde": verslag}, f,
                      ensure_ascii=False, indent=1, sort_keys=True)
    except Exception as e:
        print(f"Stand niet weg te schrijven: {str(e)[:60]}", file=sys.stderr)
    if a.droog:
        print("Droog: niets weggeschreven", file=sys.stderr)
        return 0
    if (verslag["gebeurtenissen"] or verslag["panden_nieuw"]
            or schoon["weg"] or schoon["gemeld_gezet"]):
        from pandgeschiedenis import bewaar
        bewaar(geschiedenis)
        print(f"Pandgeschiedenis bijgewerkt: {verslag['panden_nieuw']} "
              f"records erbij, {verslag['gebeurtenissen']} gebeurtenissen",
              file=sys.stderr)
    else:
        print("Niets veranderd, niets weggeschreven", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
