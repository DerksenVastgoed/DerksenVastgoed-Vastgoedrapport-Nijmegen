#!/usr/bin/env python3
"""
Haalt de oppervlakte en het energielabel op van de hele woningvoorraad in de
zes ringbuurten, niet alleen van wat te koop staat.

Drie fasen, elk met een tijdbudget:

  1. De panden uit de BAG via PDOK, om PDOK's eigen pandsleutel om te zetten
     naar de zestiencijferige BAG-pandidentificatie. Zonder die omzetting
     sluit voorraad.json niet aan op pandgeschiedenis.json.
  2. De verblijfsobjecten uit de BAG via PDOK, in één ronde over een doos om
     Nijmegen, daarna lokaal gezeefd op onze 1.733 postcodes.

     WAAROM PER GEBIED EN NIET PER POSTCODE. Dit heeft op 10 oktober vier
     keer gefaald, elke keer omdat ik een eigenschap van een dienst aannam.
     De BAG-API van het Kadaster weigert een postcode zonder huisnummer. PDOK
     laat alleen geometry en identificatie als filter toe, op alle zes
     collecties, dus een vraag per postcode kan daar niet. Wat wel kan is een
     ronde over een doos, en dat blijkt goedkoper dan beide: 164.634 objecten
     in 120,8 seconden. De postcode staat wel in het antwoord, dus zeven kan
     lokaal.

     Dat maakt deze fase ook eenvoudiger dan hij was. Geen achterstand, geen
     versheid per postcode, geen bewaarde cursor, geen hervatten. Elke ronde
     leest alles opnieuw.
  3. EP-Online per adres, voor de woningen die nog geen label hebben. Dat gaat
     per adres en niet per postcode, dus 15.000 vragen, ongeveer 4,6 uur. Dat
     past niet in één run. Daarom werkt deze fase een achterstand weg: elke
     run een tijdbudget, de oudste eerst, en de stand blijft staan. Bij 45
     minuten per run is de ring in zes runs rond.

WAAROM EEN TIJDBUDGET EN GEEN AANTAL. Ik kan deze code hier niet proeven: de
sleutels zitten in de repo-secrets en deze omgeving mag de BAG en EP-Online
niet benaderen. Een budget in aantallen gokt dus het tempo, en gokt verkeerd
zodra een dienst langzamer is dan gedacht. Een budget in minuten klopt altijd:
het script stopt wanneer de tijd om is, bewaart wat het heeft, en gaat de
volgende run verder. De eerste run vertelt het echte tempo.

WAT ER NIET IN ZIT. Dit script vult alleen voorraad.json. Het verandert niets
aan de brief en niets aan pandgeschiedenis.json. Eerst de gegevens, dan kijken
wat ze waard zijn, dan pas de brief. Andersom levert een mooie regel op basis
van een bestand dat nog nergens over gaat.

LET OP BIJ DE OPPERVLAKTE. Een verblijfsobject kan meer dan één adres hebben,
een hoofdadres met nevenadressen. De oppervlakte die de BAG teruggeeft is dan
die van het hele object en niet van wat achter één huisnummer zit. Dit script
bewaart daarom het adresseerbaarObjectIdentificatie en telt hoe vaak twee
adressen er een delen, zodat die gevallen later apart te behandelen zijn.

Vereist env: BAG_API_KEY voor fase 1, EP_API_KEY voor fase 2.

Gebruik:
  python voorraad_bag.py                          # beide fasen, standaardbudget
  python voorraad_bag.py --bag-minuten 40 --labels-minuten 45
  python voorraad_bag.py --alleen bag             # of: --alleen labels
  python voorraad_bag.py --buurt Bottendaal       # eerst één buurt proeven
"""

import argparse
import datetime as dt
import json
import os
import sys
import time

import requests

INVENTARIS = "buurtinventaris.json"
UIT = "voorraad.json"

# De stand van de laatste ronde, los van de gegevens. Dit bestand wordt altijd
# overschreven, ook als er niets is opgehaald, want juist dan moet de reden
# bewaard blijven. voorraad.json wordt alleen overschreven als er werkelijk
# iets in staat; anders zou een mislukte ronde de voorraad van vorige week
# wissen.
STAND = "voorraad_stand.json"

# Na zoveel aanroepen op rij die allemaal mislukken, stoppen. Gaat de eerste
# tien keer hetzelfde mis, dan gaat de elfde dat ook, en dan is 35 minuten
# doorploeteren verspilde tijd die de fout niet duidelijker maakt. Op 10
# oktober is precies dat gebeurd.
MAX_FOUT_OP_RIJ = 10

# De BAG via PDOK, als OGC API Features. Open data, geen sleutel.
PDOK = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections"
PDOK_BASE = f"{PDOK}/verblijfsobject/items"

# Gemeten op 10 oktober: 200, 500 en 1.000 komen voluit terug, 2.000 wordt op
# 1.000 afgekapt. Duizend is dus het maximum en niet een voorzichtige keuze.
PDOK_LIMIT = 1000

# HET GEBIED, NIET DE POSTCODE. PDOK laat alleen geometry en identificatie als
# filter toe, op alle zes collecties. Postcode staat wel in het antwoord maar is
# niet filterbaar, dus er is geen vraag per postcode mogelijk. Daarom één ronde
# over een doos en daarna lokaal zeven op onze postcodes.
#
# Deze doos is met opzet te groot: hij is een bovengrens om Nijmegen heen, geen
# schatting van de ring. Dat mag, want hij kost niets. Gemeten op 10 oktober:
# 165 pagina's, 164.634 objecten, 120,8 seconden, 1.363 objecten per seconde.
# De hele doos leest in twee minuten uit.
#
# EN HIJ KAPT NIETS AF. De doos om de gevonden treffers was
# 5,83189-5,88500 bij 51,82759-51,85880, aan alle vier de kanten ruim acht
# honderdsten van een graad binnen deze doos. Zou de doos de ring ergens
# raken, dan zouden de postcodes daar leeg blijven, en dat wordt per ronde
# geteld (zie postcodes_leeg in de stand). Een te kleine doos faalt hier dus
# hardop en niet stil.
DOOS = "5.75,51.76,5.98,51.90"

# Statussen waarbij het object niet bestaat. De collectie bevat ook historie:
# het eerste object dat PDOK op 10 oktober teruggaf had status "Verblijfsobject
# ingetrokken". Zonder deze zeef zou de voorraad gesloopte en nooit gebouwde
# woningen meetellen, en elk aantal dat de brief eruit haalt zou te hoog zijn
# zonder dat er iets faalt.
NIET_BESTAAND = ("ingetrokken", "niet gerealiseerd", "ten onrechte opgevoerd")

BAG_API_KEY = os.environ.get("BAG_API_KEY", "")
BAG_BASE = "https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2"
BAG_HEADERS = {"X-Api-Key": BAG_API_KEY,
               "Accept": "application/hal+json",
               "Accept-Crs": "epsg:28992"}

EP_API_KEY = os.environ.get("EP_API_KEY", "")
EP_BASE = "https://public.ep-online.nl/api/v5/PandEnergielabel"
EP_HEADERS = {"Authorization": EP_API_KEY, "Accept": "application/json"}

# Hetzelfde tempo als marktprijzen_bag.py aanhoudt. Niet sneller: beide
# diensten zijn gratis en een blokkade kost meer dan de winst.
TEMPO = 1.1

# Tussen twee pagina's bij PDOK. De verkenning deed op 10 oktober 165 pagina's
# achter elkaar zonder pauze en zonder één 429, dus 1,1 seconde is hier niet
# nodig en zou een ronde van twee minuten naar vijf brengen. Een kwart seconde
# houdt het netjes en kost veertig seconden per ronde.
TEMPO_PDOK = 0.25

# NIET MEER IN GEBRUIK VOOR FASE 1. Toen er per postcode werd gevraagd was
# versheid per postcode nodig om 1.733 vragen over meer runs te verdelen. Een
# hele ronde kost nu twee minuten, dus elke ronde leest alles opnieuw en er is
# geen achterstand om bij te houden.

# Een adres waarvan EP-Online geen label kende, na een jaar nog eens vragen.
# Een label wordt geregistreerd bij een verkoop of een verbouwing, dus "niet
# bekend" is een momentopname en geen eigenschap van het pand.
LABEL_OPNIEUW_DAGEN = 365


def _lees(pad, standaard):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return standaard


def _schrijf(pad, data):
    try:
        with open(pad, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        return True
    except Exception as e:
        print(f"Kon {pad} niet schrijven: {e}", file=sys.stderr)
        return False


def adressleutel(straat, nr, letter, toev):
    """Eén sleutel per adres, zonder hoofdletters en zonder spaties."""
    deel = f"{straat}{nr}{letter or ''}{toev or ''}"
    return "".join(deel.lower().split())


def postcodes_uit_inventaris(buurten=None):
    """
    De zeef: {postcode: buurt} uit buurtinventaris.json.

    Een dict en geen lijst, want er wordt niet meer per postcode gevraagd maar
    per gebied, en daarna wordt elk object in de doos hierin opgezocht.

    Achtentwintig postcodes staan in twee buurten. De eerste op alfabet wint,
    zodat dezelfde postcode niet per ronde van buurt wisselt, en het aantal
    wordt gemeld zodat die willekeur zichtbaar is in plaats van verborgen.
    """
    d = _lees(INVENTARIS, {})
    per_buurt = d.get("postcodes_per_buurt") or {}
    if not per_buurt:
        print(f"Geen postcodes in {INVENTARIS}; draai eerst "
              f"buurtinventaris.py", file=sys.stderr)
        return {}
    uit, dubbel = {}, 0
    for buurt, lijst in sorted(per_buurt.items()):
        if buurten and buurt not in buurten:
            continue
        for pc in lijst:
            sleutel = (pc or "").replace(" ", "").upper()
            if not sleutel:
                continue
            if sleutel in uit:
                dubbel += 1
                continue
            uit[sleutel] = buurt
    if dubbel:
        print(f"{dubbel} postcodes staan in meer dan één buurt; de eerste op "
              f"alfabet is gebruikt", file=sys.stderr)
    return uit


def anders_aantal(voorraad):
    """Hoeveel niet-woningen er in de voorraad staan."""
    return len(voorraad.get("niet_woningen") or {})


def _is_woning(doelen):
    return any("woonfunctie" == d for d in (doelen or []))


def _queryables():
    """
    Welke velden PDOK wel als filter toestaat.

    Alleen bedoeld voor de foutmelding. De dienst zegt bij een geweigerd filter
    welk veld niet mag, maar niet welke wel mogen, en die lijst staat op een
    eigen pagina. In een try, want een mislukking hier mag de eigenlijke
    foutmelding niet opeten.
    """
    try:
        r = requests.get(PDOK_BASE.replace("/items", "/queryables"),
                         params={"f": "json"}, timeout=(10, 30))
        if r.status_code != 200:
            return f"queryables gaf HTTP {r.status_code}"
        eigenschappen = (r.json() or {}).get("properties") or {}
        return ", ".join(sorted(eigenschappen)) or "geen velden gemeld"
    except Exception as e:
        return f"queryables niet op te halen ({type(e).__name__})"


def _bestaat(status):
    """Of de status van een object zegt dat het er werkelijk staat."""
    s = (status or "").lower()
    return not any(w in s for w in NIET_BESTAAND)


def _pand_uuids(p):
    """De panden van een verblijfsobject, uit het veld pand.href.

    PDOK zet het pand niet als identificatie in het antwoord maar als lijst
    met URL's naar zijn eigen kenmerk: pand.href is
    ["https://.../collections/pand/items/4c396a25-0e16-586f-a298-..."]. Het
    laatste stuk van die URL is PDOK's eigen sleutel voor dat pand, niet de
    zestiencijferige BAG-pandidentificatie. Die wordt in fase_panden()
    opgezocht; lukt dat niet, dan blijft het veld pand leeg in plaats van dat
    er een getal in staat dat op een pandidentificatie lijkt maar het niet is.
    """
    hrefs = p.get("pand.href") or p.get("pand") or []
    if isinstance(hrefs, str):
        hrefs = [hrefs]
    uit = []
    for h in hrefs:
        deel = str(h).rstrip("/").rsplit("/", 1)[-1]
        if deel:
            uit.append(deel)
    return uit


def _normaliseer(p):
    """
    Een PDOK-verblijfsobject in de vorm die de rest van deze module verwacht.

    WAAROM DIT ER IS. Fase 1 haalde eerst bij de BAG-API van het Kadaster alle
    adressen in een postcode op. Dat kan niet: die dienst antwoordt met
    "Minimale combinatie van parameters moet worden opgegeven", want op
    adressenuitgebreid moet er minstens een huisnummer bij de postcode. Per
    adres zou 34.946 aanroepen zijn, bijna elf uur.

    PDOK biedt dezelfde registratie als OGC API Features, en daar staat het
    verblijfsobject met oppervlakte, gebruiksdoel, postcode, straat en pand in
    één collectie. Open data, geen sleutel nodig.

    De veldnamen verschillen alleen. Die omzetting staat hier en niet in
    fase_bag(), zodat de rest van de module niet weet uit welke dienst de
    gegevens komen en een volgende wisseling één functie kost.

    Let op het enkelvoud: PDOK geeft gebruiksdoel als één tekst, de BAG-API gaf
    gebruiksdoelen als lijst. _is_woning() verwacht een lijst, dus dat wordt
    hier een lijst. Was dat niet gebeurd, dan had geen enkel adres een
    woonfunctie gehad en was de voorraad leeg gebleven zonder dat er iets
    faalde, precies zoals vandaag al twee keer is gebeurd.
    """
    doel = p.get("gebruiksdoel")
    doelen = ([d.strip() for d in doel.split(",") if d.strip()]
              if isinstance(doel, str) else list(doel or []))
    return {
        "openbareRuimteNaam": p.get("openbare_ruimte_naam") or "",
        "huisnummer": p.get("huisnummer") or "",
        "huisletter": p.get("huisletter") or "",
        "huisnummertoevoeging": p.get("toevoeging") or "",
        "gebruiksdoelen": doelen,
        "oppervlakte": p.get("oppervlakte"),
        "pandIdentificaties": _pand_uuids(p),
        "adresseerbaarObjectIdentificatie": p.get("identificatie") or "",
        "adresseerbaarObjectStatus": p.get("status") or "",
        "postcode": (p.get("postcode") or "").replace(" ", "").upper(),
    }


def doorloop(collectie, budget, per_pagina):
    """
    Alle kenmerken van een PDOK-collectie in DOOS, pagina voor pagina.

    per_pagina(kenmerken) krijgt elke pagina zodra hij binnen is, zodat een
    ronde die halverwege afbreekt niet alles verliest wat er al was.

    WAAROM GEEN CURSOR BEWAARD WORDT. Een hele ronde over de doos kostte op 10
    oktober 120,8 seconden. Hervatten over meer runs is dus niet nodig, en een
    bewaarde cursor zou een stand zijn die kan verlopen terwijl niemand merkt
    dat hij verlopen is. Opnieuw beginnen is hier goedkoper dan onthouden.

    Geeft een dict met de stand terug; de fout staat erin en wordt niet
    opgeworpen, want een mislukte ronde moet zijn reden bewaren.
    """
    start = time.time()
    url = f"{PDOK}/{collectie}/items"
    params = {"f": "json", "limit": PDOK_LIMIT, "bbox": DOOS}
    paginas = objecten = 0
    fout = ""
    klaar = False
    while True:
        if time.time() - start > budget:
            fout = (f"tijdbudget van {budget:.0f}s om na {paginas} pagina's; "
                    f"de ronde is niet af")
            break
        body, reden = _pagina(url, params)
        if reden:
            fout = f"pagina {paginas + 1}: {reden}"
            break
        kenmerken = body.get("features")
        if kenmerken is None:
            fout = ("geen features in het antwoord; velden: "
                    + ", ".join(sorted(body)[:8]))
            break
        paginas += 1
        objecten += len(kenmerken)
        try:
            per_pagina(kenmerken)
        except Exception as e:
            fout = f"verwerken van pagina {paginas} mislukte: {e}"
            break
        volgende = next((l.get("href") or "" for l in (body.get("links") or [])
                         if l.get("rel") == "next"), "")
        if not volgende:
            klaar = True
            break
        url, params = volgende, None
        time.sleep(TEMPO_PDOK)
    return {"paginas": paginas, "objecten": objecten,
            "seconden": round(time.time() - start, 1),
            "ronde_af": klaar, "fout": fout}


def _pagina(url, params):
    """Eén pagina ophalen. Geeft (body, fout) terug, werpt niets op."""
    try:
        r = requests.get(url, params=params or {}, timeout=(15, 90))
    except Exception as e:
        return {}, f"netwerk: {type(e).__name__}: {e}"
    if r.status_code == 429:
        return {}, "429 te veel vragen"
    if r.status_code != 200:
        # HET ANTWOORD ERBIJ, want de dienst zet er zelf in wat er mis is. Bij
        # de BAG-API kwam er tien keer "HTTP 400" uit en dat vertelde alleen
        # dat de vraag werd geweigerd, niet waarom.
        reden = ""
        try:
            body = r.json()
            reden = " ".join(str(body.get(k, "")) for k in
                             ("title", "detail", "code", "description")).strip()
            for inval in (body.get("invalidParams") or []):
                reden += (f" | {inval.get('name', '?')}: "
                          f"{inval.get('reason', '?')}")
        except Exception:
            reden = r.text[:200]
        # GAAT HET OVER HET FILTER, VRAAG DAN WELKE VELDEN WEL MOGEN. PDOK
        # antwoordde op 10 oktober: "property 'postcode' cannot be used in CQL
        # filter, is not a queryable property". Dat zegt wat er niet mag en
        # niet wat er wel mag, en die lijst staat op een eigen pagina van
        # dezelfde dienst.
        if "queryable" in reden.lower() or "cql" in reden.lower():
            reden += " | WEL FILTERBAAR: " + _queryables()
        return {}, f"HTTP {r.status_code}: {reden[:600]}"
    try:
        return r.json(), ""
    except Exception as e:
        return {}, f"antwoord onleesbaar: {e}"


def fase_panden(budget):
    """
    De omzetting van PDOK's pandsleutel naar de BAG-pandidentificatie.

    WAAROM DIT NODIG IS. Een verblijfsobject verwijst naar zijn pand met een
    URL naar PDOK's eigen kenmerk, niet met de zestiencijferige
    BAG-pandidentificatie. Zonder deze omzetting staat er in voorraad.json een
    sleutel die nergens op aansluit: pandgeschiedenis.json en marktprijzen_bag
    werken met de BAG-identificatie, en een join daarop zou nul treffers geven
    zonder dat er iets faalt. Precies de fout die dit project steeds inhaalt.

    De pandcollectie heeft dezelfde doos en hetzelfde tempo, dus dit kost een
    tweede ronde van ongeveer twee minuten.

    AANNAME DIE HIER WORDT GETOETST EN NIET GELOOFD. Bij het verblijfsobject is
    de kenmerksleutel "id" een uuid en staat de BAG-identificatie in
    properties. Of dat bij panden ook zo is, is niet gemeten. Komt de omzetting
    leeg terug, dan meldt de stand dat en blijft het veld pand leeg; de rest
    van de ronde gaat gewoon door.
    """
    kaart = {}

    def per_pagina(kenmerken):
        for k in kenmerken:
            sleutel = k.get("id") or ""
            bag = ((k.get("properties") or {}).get("identificatie") or "")
            if sleutel and bag:
                kaart[str(sleutel)] = str(bag)

    stand = doorloop("pand", budget, per_pagina)
    stand["omzettingen"] = len(kaart)
    if not kaart and not stand["fout"]:
        stand["fout"] = ("geen enkele omzetting; de pandcollectie levert geen "
                         "id met identificatie zoals verwacht")
    return kaart, stand


def fase_bag(voorraad, pcs, minuten, panden=None):
    """
    Fase 1: alle verblijfsobjecten in de doos, daarna zeven op onze postcodes.

    WAAROM NIET MEER PER POSTCODE. PDOK laat postcode niet als filter toe, op
    geen van de zes collecties. Een vraag per postcode kan dus niet. Maar een
    ronde over de hele doos om Nijmegen kost 120,8 seconden voor 164.634
    objecten, dus het alternatief is niet duurder maar goedkoper dan de 1.733
    losse vragen die het ooit zouden zijn geweest.

    Dat verandert ook de aard van de fase. Er is geen achterstand meer, geen
    versheid per postcode en geen hervatten: elke ronde leest alles opnieuw en
    is binnen een paar minuten klaar. Het tijdbudget blijft als noodrem.

    Geen sleutel nodig: PDOK is open data onder Public Domain Mark.
    """
    vandaag = dt.date.today().isoformat()
    gedaan = voorraad.setdefault("postcodes", {})
    adressen = voorraad.setdefault("adressen", {})
    # WAAROM DIT APART STAAT. Een adres zonder woonfunctie werd geteld en
    # daarna weggegooid, terwijl de BAG hem in hetzelfde antwoord meestuurt.
    # Winkels, kantoren en horeca in de plint zijn precies de verzameling die
    # de beleidsregel over de eerste bouwlaag raakt, en ze bewaren kost geen
    # enkele extra vraag. Ze staan onder een eigen sleutel en niet bij
    # "adressen", zodat fase 2 en alles wat later de woningvoorraad leest niet
    # ineens winkels meekrijgt. "adressen" blijft dus de woningvoorraad.
    anders = voorraad.setdefault("niet_woningen", {})
    panden = panden or {}

    tel = {"nieuw": 0, "bijgewerkt": 0, "onveranderd": 0, "woningen": 0,
           "overig": 0, "buiten_de_ring": 0, "weg": 0, "zonder_adres": 0,
           "zonder_pandsleutel": 0}
    per_postcode = {}
    statussen = {}
    objecten = {}

    def verwerk(kenmerken):
        for k in kenmerken:
            p = k.get("properties") or {}
            pc = (p.get("postcode") or "").replace(" ", "").upper()
            buurt = pcs.get(pc)
            if not buurt:
                tel["buiten_de_ring"] += 1
                continue
            status = p.get("status") or ""
            statussen[status] = statussen.get(status, 0) + 1
            # DE HISTORIE ERUIT. De collectie bevat ook ingetrokken en nooit
            # gerealiseerde objecten. Die meetellen zou elk aantal in de brief
            # te hoog maken zonder dat er iets faalt.
            if not _bestaat(status):
                tel["weg"] += 1
                continue
            a = _normaliseer(p)
            straat = a.get("openbareRuimteNaam", "")
            nr = a.get("huisnummer", "")
            if not straat or not nr:
                tel["zonder_adres"] += 1
                continue
            letter = a.get("huisletter") or ""
            toev = a.get("huisnummertoevoeging") or ""
            doelen = a.get("gebruiksdoelen") or []
            per_postcode[pc] = per_postcode.get(pc, 0) + 1
            gedaan[pc] = vandaag

            # PDOK's pandsleutel omzetten naar de BAG-identificatie. Lukt dat
            # niet, dan blijft pand leeg: liever geen sleutel dan een sleutel
            # die op een pandidentificatie lijkt en nergens op aansluit.
            pand = ""
            for sleutel in a.get("pandIdentificaties") or []:
                pand = panden.get(sleutel) or ""
                if pand:
                    break
            if not pand and (a.get("pandIdentificaties") or []):
                tel["zonder_pandsleutel"] += 1

            rec = {
                "adres": f"{straat} {nr}{letter}{('-' + toev) if toev else ''}",
                "postcode": pc,
                "buurt": buurt,
                "oppervlakte": a.get("oppervlakte"),
                "doelen": doelen,
                "pand": pand,
                "vbo": a.get("adresseerbaarObjectIdentificatie") or "",
                "status": status,
            }
            sleutel = adressleutel(straat, nr, letter, toev)

            # BAG_GEZIEN ALLEEN BIJWERKEN ALS ER WERKELIJK IETS VERANDERDE.
            # Zou hier de datum van vandaag staan, dan verandert elk van de
            # 26.561 records elke ronde en is de dagelijkse wijziging het hele
            # bestand van ruim zes megabyte. De repo zou dan met megabytes per
            # run groeien terwijl er niets nieuws in staat, en in de
            # geschiedenis zou niet te zien zijn wát er veranderde. Nu is de
            # wijziging per ronde precies dat wat de BAG anders meldt.
            bestaand = (adressen.get(sleutel) if _is_woning(doelen)
                        else anders.get(sleutel)) or {}
            zelfde = all(bestaand.get(v) == rec[v] for v in rec)
            rec["bag_gezien"] = (bestaand.get("bag_gezien") or vandaag
                                 if zelfde else vandaag)
            if not _is_woning(doelen):
                tel["overig"] += 1
                anders[sleutel] = rec
                continue
            tel["woningen"] += 1
            vbo = rec["vbo"]
            objecten[vbo] = objecten.get(vbo, 0) + 1
            # Een eerder opgehaald label blijft staan; dat komt uit fase 2.
            for veld in ("label", "label_datum", "label_gezien"):
                if bestaand.get(veld) is not None:
                    rec[veld] = bestaand[veld]
            if not bestaand:
                tel["nieuw"] += 1
            elif zelfde:
                tel["onveranderd"] += 1
            else:
                tel["bijgewerkt"] += 1
            adressen[sleutel] = rec

    stand = doorloop("verblijfsobject", minuten * 60, verwerk)

    # DE LEGE POSTCODES TELLEN. Dit is de controle op de doos. Raakt de doos de
    # ring ergens niet, dan blijven de postcodes daar leeg en staat dat hier.
    # Een te kleine doos faalt daarmee hardop in plaats van stil adressen te
    # missen, en dat is precies het soort fout dat dit project steeds inhaalt.
    leeg = sorted(pc for pc in pcs if pc not in per_postcode)
    uit = {
        "postcodes_gedaan": len(per_postcode),
        "postcodes_totaal": len(pcs),
        "postcodes_leeg": len(leeg),
        "postcodes_leeg_voorbeeld": leeg[:12],
        "adressen_nieuw": tel["nieuw"],
        "adressen_bijgewerkt": tel["bijgewerkt"],
        "adressen_onveranderd": tel["onveranderd"],
        "woningen_gezien": tel["woningen"],
        "niet_woonfunctie": tel["overig"],
        "niet_woningen_bewaard": len(anders),
        "objecten_met_meer_adressen": sum(1 for n in objecten.values()
                                          if n > 1),
        "buiten_de_ring": tel["buiten_de_ring"],
        "historie_overgeslagen": tel["weg"],
        "zonder_adres": tel["zonder_adres"],
        "zonder_pandsleutel": tel["zonder_pandsleutel"],
        "statussen": dict(sorted(statussen.items(), key=lambda x: -x[1])[:8]),
        "fouten": 1 if stand["fout"] else 0,
        "laatste_fout": stand["fout"],
    }
    uit.update({f"ronde_{k}": v for k, v in stand.items() if k != "fout"})
    return uit


def haal_label(rec):
    """Het energielabel van één adres, uit EP-Online."""
    pc = (rec.get("postcode") or "").replace(" ", "")
    adres = rec.get("adres") or ""
    deel = adres.split()
    if not pc or len(deel) < 2:
        return None, "geen postcode of huisnummer"
    nr = "".join(c for c in deel[-1] if c.isdigit())
    if not nr:
        return None, "huisnummer niet te lezen"
    params = {"postcode": pc, "huisnummer": nr}
    rest = deel[-1][len(nr):]
    if rest:
        if "-" in rest:
            letter, toev = rest.split("-", 1)
            if letter:
                params["huisletter"] = letter
            if toev:
                params["huisnummertoevoeging"] = toev
        else:
            params["huisletter"] = rest
    try:
        r = requests.get(f"{EP_BASE}/Adres", headers=EP_HEADERS,
                         params=params, timeout=20)
    except Exception as e:
        return None, f"netwerk: {e}"
    if r.status_code in (401, 403):
        return None, f"{r.status_code} sleutel geweigerd"
    if r.status_code == 429:
        return None, "429 te veel vragen"
    if r.status_code == 404:
        return {}, ""          # geen label bekend: dat is een antwoord
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    try:
        data = r.json()
    except Exception as e:
        return None, f"antwoord onleesbaar: {e}"
    rijen = data if isinstance(data, list) else [data]
    for rij in rijen:
        if isinstance(rij, dict) and rij.get("labelLetter"):
            return {"label": rij.get("labelLetter"),
                    "datum": (rij.get("registratiedatum")
                              or rij.get("geldigTot") or "")[:10]}, ""
    return {}, ""


def fase_labels(voorraad, minuten):
    """Fase 2: EP-Online voor de woningen zonder label, tot de tijd om is."""
    if not EP_API_KEY:
        print("Geen EP_API_KEY; fase labels overgeslagen", file=sys.stderr)
        return {"overgeslagen": "geen sleutel"}

    vandaag = dt.date.today().isoformat()
    adressen = voorraad.setdefault("adressen", {})

    # Welke adressen nog aan de beurt zijn. Nooit gevraagd gaat voor. Daarna
    # de adressen waar EP-Online geen label van kende en waar dat lang genoeg
    # geleden is: een label wordt pas geregistreerd bij een verkoop of een
    # verbouwing, dus een adres dat vandaag geen label heeft kan er volgend
    # jaar wel een hebben. Zonder die hernieuwing zou één antwoord "niet
    # bekend" een blinde vlek worden die nooit meer dichtgaat.
    opnieuw = (dt.date.today() - dt.timedelta(days=LABEL_OPNIEUW_DAGEN)
               ).isoformat()
    nooit, verlopen = [], []
    for s, r in adressen.items():
        if r.get("label"):
            continue
        gezien = r.get("label_gezien")
        if not gezien:
            nooit.append(s)
        elif gezien < opnieuw:
            verlopen.append(s)
    nog = (sorted(nooit, key=lambda s: adressen[s].get("adres", ""))
           + sorted(verlopen, key=lambda s: adressen[s].get("label_gezien", "")))

    einde = time.time() + minuten * 60
    gevraagd = met_label = zonder = fouten = 0
    laatste_fout = ""
    for sleutel in nog:
        if time.time() > einde:
            break
        rec = adressen[sleutel]
        uit, fout = haal_label(rec)
        time.sleep(TEMPO)
        gevraagd += 1
        if uit is None:
            fouten += 1
            laatste_fout = f"{rec.get('adres')}: {fout}"
            if "sleutel" in fout or "429" in fout:
                break
            continue
        rec["label_gezien"] = vandaag
        if uit.get("label"):
            rec["label"] = uit["label"]
            rec["label_datum"] = uit.get("datum") or ""
            met_label += 1
        else:
            zonder += 1

    resterend = sum(1 for r in adressen.values()
                    if not r.get("label") and not r.get("label_gezien"))
    return {"gevraagd": gevraagd, "label_gevonden": met_label,
            "geen_label_bekend": zonder, "nog_nooit_gevraagd": resterend,
            "opnieuw_aan_de_beurt": len(verlopen),
            "fouten": fouten, "laatste_fout": laatste_fout}


# De kenmerken hieronder zijn overgenomen uit wat PDOK op 10 oktober
# werkelijk teruggaf, inclusief het veld pand.href, het enkelvoudige
# gebruiksdoel met komma's erin en de statussen uit de historie. Verzonnen
# vormen hebben vandaag twee keer een stille fout opgeleverd: gebruiksdoelen
# bleek een lijst waar een string stond, en energielabel een dict waar een
# tekst stond. Daarom hier de echte vorm.
PROEF_KENMERKEN = [
    # 1. Gewone woning in onze postcode, pand bekend in de kaart.
    {"id": "v1", "properties": {
        "postcode": "6521AB", "status": "Verblijfsobject in gebruik",
        "gebruiksdoel": "woonfunctie", "oppervlakte": 72,
        "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 12,
        "huisletter": None, "toevoeging": None, "identificatie": "0268010000000001",
        "pand.href": ["https://api.pdok.nl/kadaster/bag/ogc/v2/collections/"
                      "pand/items/uuid-een"]}},
    # 2. Ingetrokken object in onze postcode: historie, moet eruit.
    {"id": "v2", "properties": {
        "postcode": "6521AB", "status": "Verblijfsobject ingetrokken",
        "gebruiksdoel": "woonfunctie", "oppervlakte": 65,
        "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 14,
        "identificatie": "0268010000000002", "pand.href": []}},
    # 3. Nooit gebouwd: ook historie.
    {"id": "v3", "properties": {
        "postcode": "6521AB", "status": "Niet gerealiseerd verblijfsobject",
        "gebruiksdoel": "woonfunctie", "oppervlakte": 80,
        "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 16,
        "identificatie": "0268010000000003", "pand.href": []}},
    # 4. Winkel in de plint: geen woning, wel bewaren.
    {"id": "v4", "properties": {
        "postcode": "6511AA", "status": "Verblijfsobject in gebruik",
        "gebruiksdoel": "winkelfunctie", "oppervlakte": 180,
        "openbare_ruimte_naam": "Broerstraat", "huisnummer": 3,
        "identificatie": "0268010000000004",
        "pand.href": ["https://api.pdok.nl/kadaster/bag/ogc/v2/collections/"
                      "pand/items/uuid-twee"]}},
    # 5. Gemengd gebruik: de komma's zijn echt, dit moet een woning zijn.
    {"id": "v5", "properties": {
        "postcode": "6511AA", "status": "Verblijfsobject in gebruik",
        "gebruiksdoel": "winkelfunctie,woonfunctie", "oppervlakte": 140,
        "openbare_ruimte_naam": "Broerstraat", "huisnummer": 5,
        "identificatie": "0268010000000005",
        "pand.href": ["https://api.pdok.nl/kadaster/bag/ogc/v2/collections/"
                      "pand/items/uuid-twee"]}},
    # 6. Buiten de ring: moet geteld maar niet bewaard worden.
    {"id": "v6", "properties": {
        "postcode": "6551ZE", "status": "Verblijfsobject in gebruik",
        "gebruiksdoel": "woonfunctie", "oppervlakte": 144,
        "openbare_ruimte_naam": "Bonenkampstraat", "huisnummer": 4,
        "identificatie": "0268010000000006", "pand.href": []}},
    # 7. Geen huisnummer: niet te sleutelen.
    {"id": "v7", "properties": {
        "postcode": "6521AB", "status": "Verblijfsobject in gebruik",
        "gebruiksdoel": "woonfunctie", "oppervlakte": 50,
        "openbare_ruimte_naam": "Bottelstraat", "huisnummer": None,
        "identificatie": "0268010000000007", "pand.href": []}},
    # 8. Pand niet in de kaart: pand blijft leeg en wordt geteld.
    {"id": "v8", "properties": {
        "postcode": "6521AB", "status": "Verblijfsobject in gebruik",
        "gebruiksdoel": "woonfunctie", "oppervlakte": 90,
        "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 18,
        "identificatie": "0268010000000008",
        "pand.href": ["https://api.pdok.nl/kadaster/bag/ogc/v2/collections/"
                      "pand/items/uuid-onbekend"]}},
]


def proef():
    """
    De zeef nameten op de echte vorm van een PDOK-antwoord, zonder netwerk.

    Wat hier wordt getoetst is precies wat vandaag vier keer stil misging: dat
    een aanname over de vorm van een veld een lege voorraad oplevert zonder
    dat er iets faalt.
    """
    global doorloop
    echt = doorloop

    def nep(collectie, budget, per_pagina):
        per_pagina(PROEF_KENMERKEN)
        return {"paginas": 1, "objecten": len(PROEF_KENMERKEN),
                "seconden": 0.0, "ronde_af": True, "fout": ""}

    doorloop = nep
    try:
        voorraad = {}
        pcs = {"6521AB": "Bottendaal", "6511AA": "Stadscentrum"}
        kaart = {"uuid-een": "0268100000000011",
                 "uuid-twee": "0268100000000022"}
        uit = fase_bag(voorraad, pcs, 1, kaart)
        # TWEEDE RONDE OP DEZELFDE GEGEVENS. Hieraan hangt of het bestand van
        # ruim zes megabyte elke dag ongewijzigd blijft of elke dag helemaal
        # verandert. Dat verschil is in de uitkomst niet te zien en alleen
        # hier te meten.
        voorraad_na = json.loads(json.dumps(voorraad))
        tweede = fase_bag(voorraad_na, pcs, 1, kaart)
    finally:
        doorloop = echt

    adressen = voorraad.get("adressen") or {}
    anders = voorraad.get("niet_woningen") or {}
    verwacht = {
        "woningen_gezien": 3,          # 1, 5 en 8
        "niet_woonfunctie": 1,         # 4
        "historie_overgeslagen": 2,    # 2 en 3
        "buiten_de_ring": 1,           # 6
        "zonder_adres": 1,             # 7
        "zonder_pandsleutel": 1,       # 8
        "postcodes_gedaan": 2,
        "postcodes_totaal": 2,
        "postcodes_leeg": 0,
        "adressen_nieuw": 3,
        "niet_woningen_bewaard": 1,
    }
    afwijkingen = []
    for veld, moet in verwacht.items():
        if uit.get(veld) != moet:
            afwijkingen.append(f"{veld}: {uit.get(veld)} in plaats van {moet}")

    # De pandsleutel moet de BAG-identificatie zijn en niet PDOK's uuid.
    bottel12 = adressen.get("bottelstraat12") or {}
    if bottel12.get("pand") != "0268100000000011":
        afwijkingen.append(f"pand van Bottelstraat 12: "
                           f"{bottel12.get('pand')!r} in plaats van de "
                           f"BAG-identificatie")
    bottel18 = adressen.get("bottelstraat18") or {}
    if bottel18.get("pand") != "":
        afwijkingen.append("een onbekend pand moet leeg blijven en geen uuid "
                           f"krijgen, maar werd {bottel18.get('pand')!r}")
    # Gemengd gebruik hoort bij de woningen en niet bij de winkels.
    if "broerstraat5" not in adressen:
        afwijkingen.append("winkelfunctie,woonfunctie werd niet als woning "
                           "gezien; dan is de komma-splitsing stuk")
    if "broerstraat3" not in anders:
        afwijkingen.append("de winkel staat niet onder niet_woningen")
    if "bonenkampstraat4" in adressen:
        afwijkingen.append("een adres buiten de ring is toch bewaard")

    for status, moet in (("Verblijfsobject in gebruik", True),
                         ("Verblijfsobject buiten gebruik", True),
                         ("Verbouwing verblijfsobject", True),
                         ("Verblijfsobject ingetrokken", False),
                         ("Niet gerealiseerd verblijfsobject", False),
                         ("Verblijfsobject ten onrechte opgevoerd", False)):
        if _bestaat(status) != moet:
            afwijkingen.append(f"_bestaat({status!r}) gaf "
                               f"{_bestaat(status)}")

    if _pand_uuids({"pand.href": ["https://x/items/abc"]}) != ["abc"]:
        afwijkingen.append("pand.href wordt niet goed uitgelezen")
    if _pand_uuids({}) != []:
        afwijkingen.append("een object zonder pand moet een lege lijst geven")

    # De tweede ronde op dezelfde gegevens mag niets veranderen.
    if tweede.get("adressen_onveranderd") != 3:
        afwijkingen.append(
            f"tweede ronde meldt {tweede.get('adressen_onveranderd')} "
            f"onveranderd in plaats van 3; dan verandert het hele bestand "
            f"elke ronde")
    if tweede.get("adressen_nieuw") or tweede.get("adressen_bijgewerkt"):
        afwijkingen.append(
            f"tweede ronde meldt {tweede.get('adressen_nieuw')} nieuw en "
            f"{tweede.get('adressen_bijgewerkt')} bijgewerkt, terwijl er "
            f"niets veranderd is")
    if json.dumps(voorraad, sort_keys=True) != json.dumps(voorraad_na,
                                                          sort_keys=True):
        afwijkingen.append("twee rondes op dezelfde gegevens leveren een "
                           "ander bestand op; dan groeit de repo per run "
                           "met het hele bestand")

    for a in afwijkingen:
        print(f"AFWIJKING: {a}", file=sys.stderr)
    print(f"Proef: {len(afwijkingen)} afwijkingen, "
          f"{len(verwacht) + 13} controles.", file=sys.stderr)
    return 1 if afwijkingen else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uit", default=UIT)
    # Een ronde over de doos kostte gemeten 120,8 seconden. Tien minuten is
    # dus vijf keer de gemeten duur, ruim genoeg voor een trage dag en kort
    # genoeg om niet een half uur te blijven hangen als de dienst hapert.
    p.add_argument("--bag-minuten", type=float, default=10)
    p.add_argument("--panden-minuten", type=float, default=10)
    p.add_argument("--labels-minuten", type=float, default=45)
    p.add_argument("--alleen", choices=("bag", "labels"))
    p.add_argument("--buurt", action="append")
    p.add_argument("--proef", action="store_true",
                   help="de zeef nameten zonder netwerk")
    args = p.parse_args()

    if args.proef:
        return proef()

    voorraad = _lees(args.uit, {})
    pcs = postcodes_uit_inventaris(args.buurt)
    if not pcs and args.alleen != "labels":
        return 1

    uit = {"bijgewerkt": dt.date.today().isoformat()}
    if args.alleen != "labels":
        # EERST DE PANDEN, DAN DE OBJECTEN. De omzetting van PDOK's pandsleutel
        # naar de BAG-pandidentificatie moet klaar zijn voordat de objecten
        # worden weggeschreven, anders staat er een sleutel in voorraad.json
        # die nergens op aansluit. Mislukt deze ronde, dan blijft het veld pand
        # leeg en gaat de rest door; de reden staat in de stand.
        panden, uit["panden"] = fase_panden(args.panden_minuten * 60)
        print("Panden: " + json.dumps(uit["panden"], ensure_ascii=False),
              file=sys.stderr)
        uit["bag"] = fase_bag(voorraad, pcs, args.bag_minuten, panden)
        print("BAG: " + json.dumps(uit["bag"], ensure_ascii=False),
              file=sys.stderr)
    if args.alleen != "bag":
        uit["labels"] = fase_labels(voorraad, args.labels_minuten)
        print("Labels: " + json.dumps(uit["labels"], ensure_ascii=False),
              file=sys.stderr)

    adressen = voorraad.get("adressen") or {}
    met_opp = sum(1 for r in adressen.values() if r.get("oppervlakte"))
    met_label = sum(1 for r in adressen.values() if r.get("label"))
    uit["stand"] = {
        "woningen": len(adressen),
        "met_oppervlakte": met_opp,
        "met_label": met_label,
        "postcodes_gedaan": len(voorraad.get("postcodes") or {}),
    }
    voorraad["laatste_ronde"] = uit

    # DE DIAGNOSE ALTIJD WEGSCHRIJVEN, OOK ALS ER NIETS IS OPGEHAALD. Op 10
    # oktober liep de BAG-fase 35 minuten met een geldige sleutel en kwam er
    # niets uit. Het gezondheidsrapport kon alleen melden "voorraad nog leeg",
    # want deze functie gaf exitcode 1 en schreef niets, dus de teller met
    # fouten en de laatste foutmelding gingen mee de prullenbak in. Daarmee was
    # niet te zien of de BAG de vraag weigerde, of hij wel antwoordde maar niets
    # als woning werd herkend, of dat er echt niets stond.
    #
    # Dat is dezelfde fout als de rest: de melding die vertelt wat er mis is,
    # verdwijnt juist wanneer er iets mis is. Daarom een eigen standsbestand
    # dat altijd wordt overschreven, los van de gegevens.
    _schrijf(STAND, {"datum": dt.date.today().isoformat(), "ronde": uit})

    if not adressen and not anders_aantal(voorraad):
        print("Geen enkel adres opgehaald; bestand niet overschreven. "
              f"Zie {STAND} voor de fouten.", file=sys.stderr)
        return 1
    if not adressen:
        # Wel niet-woningen, geen woningen. Dat kan betekenen dat het veld
        # gebruiksdoelen anders heet of anders is opgebouwd dan _is_woning()
        # aanneemt, en dan is het zonde om die records weg te gooien.
        print(f"Geen woningen maar wel {anders_aantal(voorraad)} andere "
              f"adressen opgehaald; wel bewaard.", file=sys.stderr)
    if not _schrijf(args.uit, voorraad):
        return 1

    s = uit["stand"]
    print(f"\nStand: {s['woningen']} woningen, {s['met_oppervlakte']} met "
          f"oppervlakte, {s['met_label']} met label, "
          f"{s['postcodes_gedaan']} postcodes nagekeken.", file=sys.stderr)
    print(f"Weggeschreven naar {args.uit}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
