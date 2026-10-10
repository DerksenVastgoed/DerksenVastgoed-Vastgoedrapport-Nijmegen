#!/usr/bin/env python3
"""
Haalt de oppervlakte en het energielabel op van de hele woningvoorraad in de
zes ringbuurten, niet alleen van wat te koop staat.

Drie fasen, elk met een tijdbudget:

  1. De panden uit de BAG via PDOK, om PDOK's eigen pandsleutel om te zetten
     naar de zestiencijferige BAG-pandidentificatie. Zonder die omzetting
     sluit voorraad.json niet aan op pandgeschiedenis.json.
  2. De verblijfsobjecten uit de BAG via PDOK, in een ronde over een raster
     van tegels om Nijmegen, daarna lokaal gezeefd op onze 1.733 postcodes.

     WAAROM PER GEBIED EN NIET PER POSTCODE. Dit heeft op 10 oktober vier
     keer gefaald, elke keer omdat ik een eigenschap van een dienst aannam.
     De BAG-API van het Kadaster weigert een postcode zonder huisnummer. PDOK
     laat alleen geometry en identificatie als filter toe, op alle zes
     collecties, dus een vraag per postcode kan daar niet. Wat wel kan is een
     ronde over een gebied, en dat blijkt goedkoper dan beide: 164.634
     objecten in 248,4 seconden over 22 tegels. De postcode staat wel in het
     antwoord, dus zeven kan lokaal.

     Dat maakt deze fase ook eenvoudiger dan hij was. Geen achterstand, geen
     versheid per postcode, geen bewaarde cursor, geen hervatten. Elke ronde
     leest alles opnieuw.
  3. EP-Online per adres, voor de woningen die nog geen label hebben. Dat gaat
     per adres en niet per postcode, dus 15.000 vragen, ongeveer 4,6 uur. Dat
     past niet in één run. Daarom werkt deze fase een achterstand weg: elke
     run een tijdbudget, de oudste eerst, en de stand blijft staan. Bij 45
     minuten per run zijn 2.455 adressen, dus de ring is in zeven runs
     rond.

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
een hoofdadres met nevenadressen. De oppervlakte is dan die van het hele
object en niet van wat achter één huisnummer zit. Sinds het ophalen per gebied
gaat is dat geen probleem meer voor de telling: er wordt rechtstreeks naar
verblijfsobjecten gevraagd, dus elk object komt één keer voorbij en de
oppervlakte hoort bij precies dat object. Wie de nevenadressen zelf wil zien,
moet de collectie adres bevragen; die staat hier niet in.

Vereist env: EP_API_KEY voor fase 3. Fase 1 en 2 gaan naar PDOK
en vragen geen sleutel.

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
# 164.634 objecten, in één doos 165 pagina's in 146,7 seconden en in tegels
# 201 pagina's in 248,4 seconden. In tegels duurt het langer omdat elke tegel
# zijn eigen eerste pagina heeft en een gedeelde tegel opnieuw wordt gelezen,
# en dat is de prijs voor een ronde die het haalt (zie doorloop).
#
# EN HIJ KAPT NIETS AF. De doos om de gevonden treffers was
# 5,83189-5,88500 bij 51,82759-51,85880. De marge tot deze doos is west
# 0,082, oost 0,095, zuid 0,068 en noord 0,041 graad; noord is de kleinste en
# dat is nog altijd ruim vier kilometer. Zou de doos de ring ergens raken, dan
# zouden de Nijmeegse postcodes daar leeg blijven, en dat wordt per ronde
# geteld (zie postcodes_leeg_nijmegen in de stand; in de eerste echte ronde
# waren dat 2 van de 1.242). Een te kleine doos faalt hier dus hardop en niet
# stil.
DOOS = "5.75,51.76,5.98,51.90"

# Statussen waarbij het object niet bestaat. De collectie bevat ook historie:
# het eerste object dat PDOK op 10 oktober teruggaf had status "Verblijfsobject
# ingetrokken". Zonder deze zeef zou de voorraad gesloopte en nooit gebouwde
# woningen meetellen, en elk aantal dat de brief eruit haalt zou te hoog zijn
# zonder dat er iets faalt.
NIET_BESTAAND = ("ingetrokken", "niet gerealiseerd", "ten onrechte opgevoerd")

# IN HOEVEEL TEGELS DE DOOS WORDT GEDEELD. Vier bij vier is zestien tegels,
# gemiddeld ruim tienduizend objecten per tegel bij de 164.634 die er in de
# hele doos staan. Dat is ongeveer elf pagina's per tegel, en zo diep
# doorbladeren hield PDOK wel vol. In één doos ging het de tweede keer mis bij
# pagina 123 van 165.
TEGELS = 4

# Een tegel die het alsnog niet haalt wordt in vieren gedeeld. Drie keer delen
# maakt van één tegel maximaal 64 kleintjes, en dan is de vraag zo eenvoudig
# dat de oorzaak ergens anders ligt dan in de omvang.
MAX_DELINGEN = 3

# GEEN BAG-SLEUTEL MEER. De BAG-API van het Kadaster weigert een postcode
# zonder huisnummer, dus die route is vervallen; PDOK vraagt geen sleutel. De
# sleutel stond hier nog en werd nergens gebruikt, en de workflow geeft hem
# nog mee. Dat is niet erg, maar het suggereert een afhankelijkheid die er
# niet is.

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

# GEEN VERSHEID PER POSTCODE MEER. Toen er per postcode werd gevraagd was dat
# nodig om 1.733 vragen over meer runs te verdelen. Een hele ronde kost nu vier
# minuten, dus elke ronde leest alles opnieuw en er is geen achterstand om bij
# te houden. De constante die dat regelde is weg; deze uitleg staat er omdat
# de vraag "waarom wordt een postcode niet overgeslagen" anders terugkomt.

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

    ALLE BUURTEN PER POSTCODE, NIET ÉÉN. Achtentwintig postcodes staan in twee
    buurten. Werd daar de eerste op alfabet gekozen, dan verloor Stadscentrum
    er elke keer een, want die staat alfabetisch laatste van de zes. En
    Stadscentrum is precies de buurt waarover de plintregel in de brief
    rekent, dus dat was een vaste afwijking in één richting: 24 van de 471
    postcodes van Stadscentrum vielen uit de telling, zonder dat er iets
    faalde en zonder dat de dekking erop reageerde. Welke van de twee buurten
    het werkelijk is, is uit een postcode niet te zeggen. Dan is beide
    bewaren eerlijker dan één kiezen.
    """
    d = _lees(INVENTARIS, {})
    per_buurt = d.get("postcodes_per_buurt") or {}
    if not per_buurt:
        print(f"Geen postcodes in {INVENTARIS}; draai eerst "
              f"buurtinventaris.py", file=sys.stderr)
        return {}
    uit = {}
    for buurt, lijst in sorted(per_buurt.items()):
        if buurten and buurt not in buurten:
            continue
        for pc in lijst:
            sleutel = (pc or "").replace(" ", "").upper()
            if sleutel:
                uit.setdefault(sleutel, []).append(buurt)
    dubbel = sum(1 for b in uit.values() if len(b) > 1)
    buiten = sum(1 for pc in uit if not pc.startswith("65"))
    if dubbel:
        print(f"{dubbel} postcodes staan in meer dan één buurt; alle buurten "
              f"worden bewaard", file=sys.stderr)
    if buiten:
        # DIT IS EEN FOUT IN DE INVENTARIS EN NIET HIER. Gemeten op 10
        # oktober: 491 van de 1.733 postcodes liggen niet in Nijmegen, maar in
        # Boskoop, Gorinchem, Dongen, Assen en vier andere plaatsen. Ze kunnen
        # hier geen schade doen, want de doos ligt om Nijmegen en ze matchen
        # dus nooit een object. Maar ze verdoezelden wel het signaal dat de
        # doos moet bewaken, en daarom staan ze apart gemeld.
        print(f"{buiten} van de {len(uit)} postcodes in {INVENTARIS} liggen "
              f"niet in Nijmegen (beginnen niet met 65); dat is een fout in de "
              f"inventaris", file=sys.stderr)
    return {pc: tuple(b) for pc, b in uit.items()}


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


def _deel(doos):
    """Een doos in vier gelijke dozen."""
    x1, y1, x2, y2 = [float(v) for v in doos.split(",")]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return [f"{a:.6f},{b:.6f},{c:.6f},{d:.6f}" for a, b, c, d in
            ((x1, y1, mx, my), (mx, y1, x2, my),
             (x1, my, mx, y2), (mx, my, x2, y2))]


def _raster(doos, n):
    """Een doos in n bij n gelijke dozen, van links naar rechts."""
    x1, y1, x2, y2 = [float(v) for v in doos.split(",")]
    bx, by = (x2 - x1) / n, (y2 - y1) / n
    uit = []
    for i in range(n):
        for j in range(n):
            uit.append(f"{x1 + i * bx:.6f},{y1 + j * by:.6f},"
                       f"{x1 + (i + 1) * bx:.6f},{y1 + (j + 1) * by:.6f}")
    return uit


def _tegel(collectie, doos, per_pagina, stoppen):
    """
    Eén tegel doorbladeren. Geeft (gelukt, paginas, objecten, reden) terug.

    stoppen() zegt of het tijdbudget om is. Werpt niets op: een mislukking
    moet haar reden meenemen, want die bepaalt of de tegel wordt gedeeld.
    """
    url = f"{PDOK}/{collectie}/items"
    params = {"f": "json", "limit": PDOK_LIMIT, "bbox": doos}
    paginas = objecten = 0
    while True:
        if stoppen():
            return False, paginas, objecten, "tijdbudget om"
        body, reden = _pagina(url, params)
        if reden and "netwerk" in reden:
            # Eén herkansing bij een netwerkhapering. Bij een antwoord van de
            # dienst zelf heeft herhalen geen zin; dan is delen het antwoord.
            time.sleep(2)
            body, reden = _pagina(url, params)
        if reden:
            return False, paginas, objecten, reden
        kenmerken = body.get("features")
        if kenmerken is None:
            return (False, paginas, objecten,
                    "geen features in het antwoord; velden: "
                    + ", ".join(sorted(body)[:8]))
        paginas += 1
        objecten += len(kenmerken)
        try:
            per_pagina(kenmerken)
        except Exception as e:
            return False, paginas, objecten, f"verwerken mislukte: {e}"
        volgende = next((l.get("href") or "" for l in (body.get("links") or [])
                         if l.get("rel") == "next"), "")
        if not volgende:
            return True, paginas, objecten, ""
        url, params = volgende, None
        time.sleep(TEMPO_PDOK)


def doorloop(collectie, budget, per_pagina):
    """
    Alle kenmerken van een PDOK-collectie in DOOS, tegel voor tegel.

    per_pagina(kenmerken) krijgt elke pagina zodra hij binnen is, zodat een
    ronde die halverwege afbreekt niet alles verliest wat er al was.

    WAAROM IN TEGELS EN NIET IN ÉÉN DOOS. Eerst ging dit in één doos. Dat
    lukte de eerste keer (165 pagina's, 164.634 objecten, 146,7 seconden) en
    de tweede keer niet: PDOK antwoordde op pagina 123 met HTTP 500, "querying
    the features took too long (timeout encountered). Simplify your request
    and try again". Diep doorbladeren in een verzameling van ruim 160.000
    objecten zit dus aan de rand van wat de dienst volhoudt, en of het lukt is
    wisselvallig. Dat is het ergste soort grens: hij valt soms weg en laat dan
    een voorraad achter die voor driekwart klopt.

    "Simplify your request" is letterlijk het antwoord. Een kleinere doos is
    een eenvoudiger vraag, dus de ronde gaat per tegel. En een tegel die het
    alsnog niet haalt wordt in vieren gedeeld en opnieuw geprobeerd, tot
    MAX_DELINGEN diep. Dat stelt zich zelf in op de werkelijke dichtheid: de
    binnenstad is druk en de uiterwaarden zijn leeg, en dat hoef ik dan niet
    te weten.

    WAAROM GEEN CURSOR BEWAARD WORDT. Een hele ronde kost twee tot drie
    minuten. Hervatten over meer runs is dus niet nodig, en een bewaarde
    cursor zou een stand zijn die kan verlopen terwijl niemand merkt dat hij
    verlopen is. Opnieuw beginnen is hier goedkoper dan onthouden.

    Geeft een dict met de stand terug; de fout staat erin en wordt niet
    opgeworpen, want een mislukte ronde moet zijn reden bewaren.
    """
    start = time.time()

    def stoppen():
        return time.time() - start > budget

    wacht = [(t, 0) for t in _raster(DOOS, TEGELS)]
    tegels_totaal = len(wacht)
    paginas = objecten = gedeeld = klaar_tegels = 0
    fout = ""
    while wacht:
        if stoppen():
            fout = (f"tijdbudget van {budget:.0f}s om na {klaar_tegels} van de "
                    f"{tegels_totaal} tegels; de ronde is niet af")
            break
        doos, diepte = wacht.pop()
        gelukt, p, o, reden = _tegel(collectie, doos, per_pagina, stoppen)
        paginas += p
        objecten += o
        if gelukt:
            klaar_tegels += 1
            continue
        if "tijdbudget" in reden:
            fout = (f"tijdbudget van {budget:.0f}s om in tegel {doos} na "
                    f"{klaar_tegels} van de {tegels_totaal} tegels")
            break
        if diepte >= MAX_DELINGEN:
            fout = (f"tegel {doos} bleef mislukken na {diepte} delingen: "
                    f"{reden}")
            break
        # DELEN EN OPNIEUW. De objecten die deze tegel al heeft afgeleverd
        # komen in de kleinere tegels nog een keer voorbij. Dat is geen
        # probleem: fase_bag slaat een object over dat hij deze ronde al zag,
        # dus de tellingen blijven kloppen en het schrijven is onschadelijk.
        gedeeld += 1
        # Vier kinderen erbij, de ouder eraf: netto drie.
        tegels_totaal += 3
        wacht.extend((d, diepte + 1) for d in _deel(doos))
    return {"paginas": paginas, "objecten": objecten,
            "tegels": klaar_tegels, "tegels_gedeeld": gedeeld,
            "tegels_over": len(wacht),
            "seconden": round(time.time() - start, 1),
            "ronde_af": not wacht and not fout, "fout": fout}


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
    ronde over het gebied om Nijmegen kostte gemeten 248,4 seconden voor
    164.634 objecten, dus het alternatief is niet duurder maar goedkoper dan de
    1.733 losse vragen die het ooit zouden zijn geweest.

    Dat verandert ook de aard van de fase. Er is geen achterstand meer, geen
    versheid per postcode en geen hervatten: elke ronde leest alles opnieuw en
    is binnen een paar minuten klaar. Het tijdbudget blijft als noodrem.

    DE SLEUTEL IS HET VERBLIJFSOBJECT EN NIET HET ADRES. Dat was eerst
    adressleutel(), straat plus nummer plus letter plus toevoeging zonder
    scheidingsteken. Daarin botsen huisnummer 1 toevoeging 2 en huisnummer 12
    op dezelfde sleutel, en 1B als huisletter met 1-B als toevoeging ook. De
    eerste echte ronde maakte zichtbaar hoe groot dat is: 22.096 objecten
    kwamen binnen en er bleven 22.003 records over, dus 93 woningen
    overschreven elkaar. Stil, en in de richting die het ergst is. De
    identificatie van het verblijfsobject kan niet botsen.

    EN ER WORDT NU OOK VERWIJDERD. Daarvoor werd alleen toegevoegd en
    overschreven. Een gesloopte woning bleef dan staan met haar oude status, en
    een winkel die woning werd stond in beide lijsten en werd twee keer
    geteld. Het aantal in de brief zou daardoor langzaam te hoog oplopen en
    plausibel blijven. Verwijderen gebeurt alleen na een afgemaakte ronde: een
    halve ronde weet niet wat er niet meer is.

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
           "zonder_pandsleutel": 0, "met_pand": 0, "gevormd": 0,
           "zonder_vbo": 0, "van_soort_gewisseld": 0, "opnieuw_gezien": 0}
    per_postcode = {}
    statussen = {}
    gezien_woning, gezien_anders = set(), set()
    # Elk object dat deze ronde al door verwerk() is gegaan, ook de objecten
    # buiten de ring en de historie, want ook die hebben tellers.
    gezien_alle = set()

    def verwerk(kenmerken):
        for k in kenmerken:
            p = k.get("properties") or {}

            # AL GEZIEN DEZE RONDE? HELEMAAL VOORAAN. Een tegel die pagina's
            # heeft afgeleverd en daarna mislukt wordt in vieren gedeeld en
            # opnieuw gelopen, dus dezelfde objecten komen nog een keer
            # voorbij. Stond deze regel verderop, dan liep alles wat ervoor
            # geteld wordt dubbel op: de statussen, de historie, nog_gevormd
            # en buiten_de_ring. Dat laatste is onschuldig, maar nog_gevormd
            # gedeeld door woningen_gezien is een drempel in het
            # gezondheidsrapport, en dan stond de teller voor en de noemer
            # achter de dedup. Een deling in een drukke tegel zou die drempel
            # dan halen zonder dat er iets aan de hand is.
            ident = str(p.get("identificatie") or "")
            if ident and ident in gezien_alle:
                tel["opnieuw_gezien"] += 1
                continue
            if ident:
                gezien_alle.add(ident)

            pc = (p.get("postcode") or "").replace(" ", "").upper()
            buurten = pcs.get(pc)
            if not buurten:
                tel["buiten_de_ring"] += 1
                continue
            status = p.get("status") or ""
            statussen[status] = statussen.get(status, 0) + 1
            # DE HISTORIE ERUIT. De collectie bevat ook ingetrokken en nooit
            # gerealiseerde objecten. Die meetellen zou elk aantal in de brief
            # te hoog maken zonder dat er iets faalt. Gemeten in de eerste
            # ronde: 1.955 ingetrokken en 427 niet gerealiseerd.
            if not _bestaat(status):
                tel["weg"] += 1
                continue
            if "gevormd" in status.lower():
                tel["gevormd"] += 1
            a = _normaliseer(p)
            straat = a.get("openbareRuimteNaam", "")
            nr = a.get("huisnummer", "")
            if not straat or not nr:
                tel["zonder_adres"] += 1
                continue
            vbo = a.get("adresseerbaarObjectIdentificatie") or ""
            if not vbo:
                # Zonder identificatie is er geen sleutel die niet botst, en
                # dan is weglaten eerlijker dan terugvallen op het adres.
                tel["zonder_vbo"] += 1
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
            if pand:
                tel["met_pand"] += 1
            elif a.get("pandIdentificaties"):
                tel["zonder_pandsleutel"] += 1

            woning = _is_woning(doelen)
            rec = {
                "adres": f"{straat} {nr}{letter}{('-' + toev) if toev else ''}",
                "sleutel": adressleutel(straat, nr, letter, toev),
                "postcode": pc,
                # ALLE BUURTEN EN NIET DE EERSTE OP ALFABET. Achtentwintig
                # postcodes staan in twee buurten. Werd daar de eerste op
                # alfabet gekozen, dan verloor Stadscentrum er elke keer een,
                # want die staat alfabetisch laatste. En Stadscentrum is
                # precies de buurt waarover de plintregel in de brief rekent,
                # dus dat was een vaste afwijking in één richting: 24 van de
                # 471 postcodes van Stadscentrum, zonder dat er iets faalde.
                "buurten": list(buurten),
                "oppervlakte": a.get("oppervlakte"),
                "doelen": doelen,
                "pand": pand,
                "vbo": vbo,
                "status": status,
            }

            # BAG_GEZIEN ALLEEN BIJWERKEN ALS ER WERKELIJK IETS VERANDERDE.
            # Zou hier de datum van vandaag staan, dan verandert elk van de
            # 22.000 records elke ronde en is de dagelijkse wijziging het hele
            # bestand van ruim vijf megabyte. De repo zou dan met megabytes per
            # run groeien terwijl er niets nieuws in staat, en in de
            # geschiedenis zou niet te zien zijn wát er veranderde.
            bestaand = (adressen if woning else anders).get(vbo) or {}
            zelfde = bool(bestaand) and all(bestaand.get(v) == rec[v]
                                            for v in rec)
            rec["bag_gezien"] = (bestaand.get("bag_gezien") or vandaag
                                 if zelfde else vandaag)

            # VAN SOORT GEWISSELD. Een winkel die woning wordt stond eerst in
            # beide lijsten en werd twee keer geteld.
            anderskant = anders if woning else adressen
            if vbo in anderskant:
                del anderskant[vbo]
                tel["van_soort_gewisseld"] += 1

            if not woning:
                tel["overig"] += 1
                anders[vbo] = rec
                gezien_anders.add(vbo)
                continue
            tel["woningen"] += 1
            gezien_woning.add(vbo)
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
            adressen[vbo] = rec

    stand = doorloop("verblijfsobject", minuten * 60, verwerk)

    # WAT ER NIET MEER IS, GAAT ERUIT. Alleen na een afgemaakte ronde, want een
    # halve ronde weet niet wat er niet meer is en zou de helft van de ring
    # weggooien.
    verwijderd = 0
    if stand["ronde_af"]:
        # EN ALLEEN BINNEN DE GEVRAAGDE POSTCODES. Zonder deze voorwaarde
        # wiste "python voorraad_bag.py --buurt Bottendaal" de andere vijf
        # buurten: die objecten komen binnen als buiten_de_ring, staan niet in
        # gezien, en zouden dus verdwijnen. Dat commando staat in de docstring
        # aanbevolen als manier om één buurt te proeven, dus het was een
        # proefdraai die 22.096 woningen op ongeveer 1.700 zette en dat
        # commit, zonder dat er iets faalde.
        for lijst, gezien in ((adressen, gezien_woning),
                              (anders, gezien_anders)):
            for vbo in [v for v, r in lijst.items()
                        if v not in gezien
                        and (r.get("postcode") or "") in pcs]:
                del lijst[vbo]
                verwijderd += 1
        # En de postcodes die niet meer in de zeef zitten, zodat de dekking
        # niet op een postcode blijft staan die er niet meer bij hoort.
        for pc in [x for x in gedaan if x not in pcs]:
            del gedaan[pc]

    # DE LEGE POSTCODES TELLEN, GESPLITST. Dit is de controle op de doos: raakt
    # hij de ring ergens niet, dan blijven de postcodes daar leeg. Maar de
    # eerste echte ronde liet zien dat 491 van de 1.733 postcodes in de
    # inventaris helemaal niet in Nijmegen liggen: 2771 Boskoop, 4201
    # Gorinchem, 5103 Dongen, 9401 Assen en nog vier. Die zouden het signaal
    # over de doos voorgoed verdoezelen. Daarom apart: alleen een lege
    # Nijmeegse postcode zegt iets over de doos.
    leeg = sorted(pc for pc in pcs if pc not in per_postcode)
    leeg_nijmegen = [pc for pc in leeg if pc.startswith("65")]
    uit = {
        "postcodes_gedaan": len(per_postcode),
        "postcodes_totaal": len(pcs),
        "postcodes_nijmegen": sum(1 for pc in pcs if pc.startswith("65")),
        "postcodes_leeg": len(leeg),
        "postcodes_leeg_nijmegen": len(leeg_nijmegen),
        "postcodes_buiten_nijmegen": len(leeg) - len(leeg_nijmegen),
        "postcodes_leeg_voorbeeld": leeg_nijmegen[:12] or leeg[:6],
        "adressen_nieuw": tel["nieuw"],
        "adressen_bijgewerkt": tel["bijgewerkt"],
        "adressen_onveranderd": tel["onveranderd"],
        "adressen_verwijderd": verwijderd,
        "van_soort_gewisseld": tel["van_soort_gewisseld"],
        "woningen_gezien": tel["woningen"],
        "niet_woonfunctie": tel["overig"],
        "niet_woningen_bewaard": len(anders),
        "buiten_de_ring": tel["buiten_de_ring"],
        "historie_overgeslagen": tel["weg"],
        # NOG GEVORMD, NIET IN GEBRUIK. In de eerste ronde 2.238 objecten,
        # ruim een tiende van de voorraad. Die status betekent dat het object
        # in de registratie is gevormd maar nog niet als in gebruik is
        # gemeld. Ze worden meegeteld, want tien procent eruit gooien op een
        # vermoeden is een grotere ingreep dan ze laten staan, en de status
        # staat per record bewaard zodat het later te zeven is. Het getal
        # staat hier zodat de vraag open blijft in plaats van stil beslist.
        "nog_gevormd": tel["gevormd"],
        "zonder_adres": tel["zonder_adres"],
        "zonder_vbo": tel["zonder_vbo"],
        "opnieuw_gezien": tel["opnieuw_gezien"],
        # ALLE OBJECTEN EN NIET ALLEEN DE WONINGEN, want de teller
        # wordt ook voor winkels verhoogd. Heette dit woningen_met_pand, dan
        # deelde het gezondheidsrapport door het verkeerde getal en kwam er
        # een percentage boven honderd uit.
        "objecten_met_pand": tel["met_pand"],
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


def proef_tegels():
    """
    De tegelindeling en het delen nameten, zonder netwerk.

    Dit is de code die op 10 oktober nieuw was omdat PDOK in één doos een
    eigen timeout gaf. Wat hier misgaat is niet te zien aan een foutmelding
    maar aan een gat in de dekking: een tegel die wordt overgeslagen of een
    strook tussen twee tegels waar niemand kijkt.
    """
    global _pagina
    afw = []

    # 1. HET RASTER DEKT DE DOOS PRECIES. Geen gaten en geen overlap.
    tegels = _raster(DOOS, TEGELS)
    if len(tegels) != TEGELS * TEGELS:
        afw.append(f"{len(tegels)} tegels in plaats van {TEGELS ** 2}")
    x1, y1, x2, y2 = [float(v) for v in DOOS.split(",")]
    oppervlak = sum((float(t.split(",")[2]) - float(t.split(",")[0]))
                    * (float(t.split(",")[3]) - float(t.split(",")[1]))
                    for t in tegels)
    if abs(oppervlak - (x2 - x1) * (y2 - y1)) > 1e-9:
        afw.append(f"de tegels dekken {oppervlak} en de doos "
                   f"{(x2 - x1) * (y2 - y1)}; dan zit er een gat of overlap "
                   f"in en vallen er adressen buiten elke tegel")
    hoeken = [[float(v) for v in t.split(",")] for t in tegels]
    if (abs(min(h[0] for h in hoeken) - x1) > 1e-9
            or abs(max(h[2] for h in hoeken) - x2) > 1e-9
            or abs(min(h[1] for h in hoeken) - y1) > 1e-9
            or abs(max(h[3] for h in hoeken) - y2) > 1e-9):
        afw.append("de buitenrand van het raster is niet die van de doos")

    # 2. DELEN DEKT DE OUDERTEGEL PRECIES.
    ouder = "5.0,51.0,6.0,52.0"
    vier = _deel(ouder)
    if len(vier) != 4:
        afw.append(f"_deel gaf {len(vier)} dozen")
    opp4 = sum((float(t.split(",")[2]) - float(t.split(",")[0]))
               * (float(t.split(",")[3]) - float(t.split(",")[1]))
               for t in vier)
    if abs(opp4 - 1.0) > 1e-9:
        afw.append(f"vier delen dekken {opp4} in plaats van 1,0")

    echt_pagina = _pagina
    stuk = {"doos": tegels[5]}

    def nep_pagina(url, params):
        """Elke tegel levert één object, behalve één tegel die PDOK's
        eigen timeout geeft zolang hij zo groot is."""
        doos = (params or {}).get("bbox") or ""
        if doos == stuk["doos"]:
            return {}, ("HTTP 500: Internal Server Error failed to retrieve "
                        "feature collection verblijfsobject: querying the "
                        "features took too long (timeout encountered)")
        return {"features": [{"id": doos, "properties": {}}], "links": []}, ""

    try:
        _pagina = nep_pagina
        gezien = []
        stand = doorloop("verblijfsobject", 30,
                         lambda ks: gezien.extend(ks))
    finally:
        _pagina = echt_pagina

    # 3. EEN MISLUKTE TEGEL WORDT GEDEELD EN DE RONDE KOMT ALSNOG ROND.
    if not stand["ronde_af"]:
        afw.append(f"de ronde kwam niet rond terwijl alleen één tegel "
                   f"haperde: {stand['fout']}")
    if stand["tegels_gedeeld"] != 1:
        afw.append(f"{stand['tegels_gedeeld']} delingen in plaats van 1")
    if stand["tegels"] != TEGELS * TEGELS - 1 + 4:
        afw.append(f"{stand['tegels']} tegels gelukt in plaats van "
                   f"{TEGELS ** 2 + 3}")
    # De vier kleintjes samen moeten precies de mislukte tegel dekken, dus
    # geen enkel adres in die tegel mag ongezien blijven.
    if len(gezien) != TEGELS * TEGELS - 1 + 4:
        afw.append(f"{len(gezien)} objecten gezien in plaats van "
                   f"{TEGELS ** 2 + 3}")

    # 4. EEN TEGEL DIE MISLUKT NA AL PAGINA'S TE HEBBEN AFGELEVERD. Dit is
    # wat op 10 oktober werkelijk gebeurde: pagina 123 van 165, dus ná
    # aflevering. De tegel wordt gedeeld en de al afgeleverde objecten komen
    # in de kleintjes nog een keer voorbij, dus hier hangt aan of de dedup op
    # de juiste plek staat. Stond hij verderop, dan liepen de statussen, de
    # historie en nog_gevormd dubbel op, en nog_gevormd gedeeld door
    # woningen_gezien is een drempel in het gezondheidsrapport.
    laat = {"doos": tegels[5], "pagina": 0}
    # De kinderen van de mislukte tegel leveren hetzelfde object als de ouder
    # al had afgeleverd. Zo gaat het in het echt ook: een kindtegel ligt in de
    # ouder, dus de objecten die de ouder al gaf komen opnieuw voorbij. Stond
    # hier een nieuw object per kind, dan meette deze proef de dedup niet, en
    # dat was de eerste versie ervan.
    kinderen = set(_deel(tegels[5]))

    def nep_laat(url, params):
        doos = (params or {}).get("bbox") or ""
        if doos in kinderen:
            return {"features": [{"id": doos, "properties": {
                "identificatie": "vbo-in-de-stukke-tegel",
                "postcode": "6521AB",
                "status": "Verblijfsobject in gebruik",
                "gebruiksdoel": "woonfunctie", "oppervlakte": 60,
                "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 99,
                "pand.href": []}}], "links": []}, ""
        if doos == laat["doos"]:
            laat["pagina"] += 1
            if laat["pagina"] == 1:
                # Eén object afleveren, met een next-link zodat er een tweede
                # pagina komt.
                return {"features": [{"id": doos, "properties": {
                    "identificatie": "vbo-in-de-stukke-tegel",
                    "postcode": "6521AB", "status": "Verblijfsobject in "
                    "gebruik", "gebruiksdoel": "woonfunctie",
                    "oppervlakte": 60, "openbare_ruimte_naam": "Bottelstraat",
                    "huisnummer": 99, "pand.href": []}}],
                        "links": [{"rel": "next", "href": "verder"}]}, ""
            return {}, ("HTTP 500: querying the features took too long "
                        "(timeout encountered)")
        if url == "verder":
            return {}, "HTTP 500: querying the features took too long"
        return {"features": [{"id": doos, "properties": {
            "identificatie": f"vbo-{doos}", "postcode": "6521AB",
            "status": "Verblijfsobject in gebruik",
            "gebruiksdoel": "woonfunctie", "oppervlakte": 70,
            "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 1,
            "pand.href": []}}], "links": []}, ""

    try:
        _pagina = nep_laat
        voorraad_laat = {}
        uit_laat = fase_bag(voorraad_laat, {"6521AB": ("Bottendaal",)}, 30, {})
    finally:
        _pagina = echt_pagina
    if not uit_laat.get("ronde_ronde_af"):
        afw.append(f"een tegel die laat mislukt bracht de ronde niet rond: "
                   f"{uit_laat.get('laatste_fout')}")
    # De vier kinderen leveren alle vier het object dat de ouder al had
    # afgeleverd, dus dat hoort vier keer als opnieuw_gezien te worden
    # overgeslagen en één keer te zijn geteld.
    if uit_laat.get("opnieuw_gezien") != 4:
        afw.append(f"opnieuw_gezien is {uit_laat.get('opnieuw_gezien')} in "
                   f"plaats van 4; dan meet deze proef de dedup niet of staat "
                   f"de dedup op de verkeerde plek")
    if uit_laat.get("woningen_gezien") != 16:
        afw.append(f"woningen_gezien is {uit_laat.get('woningen_gezien')} in "
                   f"plaats van 16; elk object hoort één keer te tellen, ook "
                   f"na een deling")
    # En de tellers die vóór de dedup stonden mogen ook niet dubbel lopen.
    if (uit_laat.get("statussen") or {}).get(
            "Verblijfsobject in gebruik") != 16:
        afw.append(f"de statustelling is "
                   f"{(uit_laat.get('statussen') or {}).get('Verblijfsobject in gebruik')} "
                   f"in plaats van 16; dan staat de dedup achter de "
                   f"statustelling en loopt die dubbel bij een deling")

    # 5. EEN TEGEL DIE BLIJFT MISLUKKEN STOPT DE RONDE MET EEN REDEN.
    def altijd_stuk(url, params):
        return {}, "HTTP 500: querying the features took too long"

    try:
        _pagina = altijd_stuk
        hard = doorloop("verblijfsobject", 30, lambda ks: None)
    finally:
        _pagina = echt_pagina
    if hard["ronde_af"]:
        afw.append("een tegel die altijd mislukt leverde toch een afgeronde "
                   "ronde op; dan wordt er verwijderd op een halve meting")
    if "delingen" not in (hard["fout"] or ""):
        afw.append(f"de reden noemt het delen niet: {hard['fout']!r}")

    return afw


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

    def nep_panden(collectie, budget, per_pagina):
        per_pagina([
            {"id": "uuid-een", "properties": {
                "identificatie": "0268100000000011"}},
            {"id": "uuid-twee", "properties": {
                "identificatie": "0268100000000022"}},
            # Zonder identificatie: mag de kaart niet vervuilen.
            {"id": "uuid-drie", "properties": {}},
        ])
        return {"paginas": 1, "objecten": 3, "seconden": 0.0,
                "ronde_af": True, "fout": ""}

    doorloop = nep
    try:
        voorraad = {}
        pcs = {"6521AB": ("Bottendaal",),
               "6511AA": ("Benedenstad", "Stadscentrum")}
        kaart = {"uuid-een": "0268100000000011",
                 "uuid-twee": "0268100000000022"}
        uit = fase_bag(voorraad, pcs, 1, kaart)
        # TWEEDE RONDE OP DEZELFDE GEGEVENS. Hieraan hangt of het bestand van
        # ruim vijf megabyte elke dag ongewijzigd blijft of elke dag helemaal
        # verandert. Dat verschil is in de uitkomst niet te zien en alleen
        # hier te meten.
        voorraad_na = json.loads(json.dumps(voorraad))
        tweede = fase_bag(voorraad_na, pcs, 1, kaart)

        # DERDE RONDE WAARIN DINGEN VERDWIJNEN EN VAN SOORT WISSELEN. Hier
        # hangt aan of het aantal in de brief langzaam te hoog oploopt.
        voorraad_weg = json.loads(json.dumps(voorraad))
        korter = [k for k in PROEF_KENMERKEN if k["id"] != "v5"]
        # En de winkel op Broerstraat 3 wordt een woning.
        werd_woning = json.loads(json.dumps(
            [k for k in PROEF_KENMERKEN if k["id"] == "v4"][0]))
        werd_woning["properties"]["gebruiksdoel"] = "woonfunctie"
        korter = [k for k in korter if k["id"] != "v4"] + [werd_woning]

        def nep_korter(collectie, budget, per_pagina):
            per_pagina(korter)
            return {"paginas": 1, "objecten": len(korter), "seconden": 0.0,
                    "ronde_af": True, "fout": ""}

        doorloop = nep_korter
        derde = fase_bag(voorraad_weg, pcs, 1, kaart)

        # VIERDE RONDE DIE HALVERWEGE AFBREEKT: dan mag er niets verdwijnen.
        voorraad_half = json.loads(json.dumps(voorraad))

        def nep_half(collectie, budget, per_pagina):
            per_pagina(korter)
            return {"paginas": 1, "objecten": len(korter), "seconden": 0.0,
                    "ronde_af": False, "fout": "tijdbudget om"}

        doorloop = nep_half
        vierde = fase_bag(voorraad_half, pcs, 1, kaart)

        # En de pandfase zelf, op de vorm die PDOK werkelijk levert.
        doorloop = nep_panden
        pandkaart, pandstand = fase_panden(1)
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
        "objecten_met_pand": 3,        # 1, 4 en 5
        "postcodes_gedaan": 2,
        "postcodes_totaal": 2,
        "postcodes_nijmegen": 2,
        "postcodes_leeg": 0,
        "postcodes_leeg_nijmegen": 0,
        "adressen_nieuw": 3,
        "adressen_verwijderd": 0,
        "van_soort_gewisseld": 0,
        "niet_woningen_bewaard": 1,
    }
    afwijkingen = []
    for veld, moet in verwacht.items():
        if uit.get(veld) != moet:
            afwijkingen.append(f"{veld}: {uit.get(veld)} in plaats van {moet}")

    # DE SLEUTEL IS DE VBO-IDENTIFICATIE. Met de adressleutel botsten in de
    # echte ring 93 van de 22.096 objecten op elkaar.
    if set(adressen) != {"0268010000000001", "0268010000000005",
                         "0268010000000008"}:
        afwijkingen.append(f"adressen zijn niet op vbo gesleuteld: "
                           f"{sorted(adressen)}")
    # En een botsende adressleutel mag geen record meer opslokken.
    bots = [
        {"id": "b1", "properties": {
            "postcode": "6521AB", "status": "Verblijfsobject in gebruik",
            "gebruiksdoel": "woonfunctie", "oppervlakte": 40,
            "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 1,
            "toevoeging": "2", "identificatie": "0268010000000101",
            "pand.href": []}},
        {"id": "b2", "properties": {
            "postcode": "6521AB", "status": "Verblijfsobject in gebruik",
            "gebruiksdoel": "woonfunctie", "oppervlakte": 90,
            "openbare_ruimte_naam": "Bottelstraat", "huisnummer": 12,
            "identificatie": "0268010000000102", "pand.href": []}},
    ]
    if adressleutel("Bottelstraat", 1, "", "2") != adressleutel(
            "Bottelstraat", 12, "", ""):
        afwijkingen.append("de proef op de botsing meet niets, want deze twee "
                           "adressen botsen niet meer")
    bewaar = doorloop

    def nep_bots(collectie, budget, per_pagina):
        per_pagina(bots)
        return {"paginas": 1, "objecten": 2, "seconden": 0.0,
                "ronde_af": True, "fout": ""}

    doorloop = nep_bots
    try:
        vb = {}
        botsuit = fase_bag(vb, {"6521AB": ("Bottendaal",)}, 1, {})
    finally:
        doorloop = bewaar
    if len(vb.get("adressen") or {}) != 2:
        afwijkingen.append(
            f"twee objecten met een botsende adressleutel leverden "
            f"{len(vb.get('adressen') or {})} records in plaats van 2; dan "
            f"slokt de sleutel nog woningen op")
    if botsuit.get("woningen_gezien") != 2:
        afwijkingen.append("de botsproef zag geen twee woningen")

    # De pandsleutel moet de BAG-identificatie zijn en niet PDOK's uuid.
    bottel12 = adressen.get("0268010000000001") or {}
    if bottel12.get("pand") != "0268100000000011":
        afwijkingen.append(f"pand van Bottelstraat 12: "
                           f"{bottel12.get('pand')!r} in plaats van de "
                           f"BAG-identificatie")
    bottel18 = adressen.get("0268010000000008") or {}
    if bottel18.get("pand") != "":
        afwijkingen.append("een onbekend pand moet leeg blijven en geen uuid "
                           f"krijgen, maar werd {bottel18.get('pand')!r}")
    # Gemengd gebruik hoort bij de woningen en niet bij de winkels.
    if "0268010000000005" not in adressen:
        afwijkingen.append("winkelfunctie,woonfunctie werd niet als woning "
                           "gezien; dan is de komma-splitsing stuk")
    if "0268010000000004" not in anders:
        afwijkingen.append("de winkel staat niet onder niet_woningen")
    if "0268010000000006" in adressen:
        afwijkingen.append("een adres buiten de ring is toch bewaard")

    # BEIDE BUURTEN BEWAARD. Koos dit de eerste op alfabet, dan verloor
    # Stadscentrum 24 van zijn 471 postcodes uit de plinttelling.
    winkel = anders.get("0268010000000004") or {}
    if winkel.get("buurten") != ["Benedenstad", "Stadscentrum"]:
        afwijkingen.append(f"een postcode in twee buurten levert "
                           f"{winkel.get('buurten')!r} in plaats van beide")

    # WAT ER NIET MEER IS, MOET ERUIT.
    if derde.get("adressen_verwijderd") != 1:
        afwijkingen.append(
            f"een verdwenen object leverde "
            f"{derde.get('adressen_verwijderd')} verwijderingen in plaats "
            f"van 1; dan loopt het aantal in de brief op")
    if "0268010000000005" in (voorraad_weg.get("adressen") or {}):
        afwijkingen.append("een object dat de BAG niet meer teruggeeft staat "
                           "er nog in")
    if derde.get("van_soort_gewisseld") != 1:
        afwijkingen.append(
            f"een winkel die woning werd gaf "
            f"{derde.get('van_soort_gewisseld')} wisselingen in plaats van 1")
    dubbel = (set(voorraad_weg.get("adressen") or {})
              & set(voorraad_weg.get("niet_woningen") or {}))
    if dubbel:
        afwijkingen.append(f"{len(dubbel)} objecten staan in beide lijsten en "
                           f"worden dus dubbel geteld: {sorted(dubbel)}")

    # EEN HALVE RONDE MAG NIETS WEGGOOIEN.
    if vierde.get("adressen_verwijderd") != 0:
        afwijkingen.append(
            f"een afgebroken ronde verwijderde "
            f"{vierde.get('adressen_verwijderd')} records; dan gooit een "
            f"haperende dienst de halve ring weg")
    if not vierde.get("fouten"):
        afwijkingen.append("een afgebroken ronde meldt geen fout")

    # DE PANDFASE OP DE ECHTE VORM.
    if pandkaart != {"uuid-een": "0268100000000011",
                     "uuid-twee": "0268100000000022"}:
        afwijkingen.append(f"fase_panden gaf {pandkaart!r}")
    if pandstand.get("omzettingen") != 2:
        afwijkingen.append(f"fase_panden meldt "
                           f"{pandstand.get('omzettingen')} omzettingen")
    if pandstand.get("fout"):
        afwijkingen.append(f"fase_panden meldde een fout: {pandstand['fout']}")

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

    afwijkingen.extend(proef_tegels())

    for a in afwijkingen:
        print(f"AFWIJKING: {a}", file=sys.stderr)
    # GEEN AANTAL CONTROLES MEER. Dat getal stond er eerst bij en was fout,
    # en een fout getal in een proefverslag is erger dan geen getal: het wekt
    # vertrouwen dat het niet verdient. Wat de proef dekt staat er wel.
    print(f"Proef: {len(afwijkingen)} afwijkingen. Gedekt: de vorm van het "
          f"antwoord, de komma in gebruiksdoel, de historiezeef, de "
          f"vbo-sleutel en de botsing die hij vervangt, de omzetting van de "
          f"pandsleutel, beide buurten bij een dubbele postcode, verwijderen "
          f"na een afgemaakte ronde, niets verwijderen na een afgebroken "
          f"ronde, wisselen tussen woning en niet-woning, en twee gelijke "
          f"rondes die hetzelfde bestand opleveren, en het raster met "
          f"het delen van een tegel die PDOK niet aankan.", file=sys.stderr)
    return 1 if afwijkingen else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uit", default=UIT)
    # Gemeten op 10 oktober met tegels: de objectronde 248,4 seconden over 201
    # pagina's en 22 tegels, de pandronde 247,0 seconden over 228 pagina's en
    # 19 tegels. Tien minuten is dus ruim twee keer de gemeten duur: genoeg
    # voor een trage dag en voor een paar delingen, en kort genoeg om niet een
    # half uur te blijven hangen als de dienst hapert.
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

    # DE DIAGNOSE VAN DE ANDERE FASE NIET WISSEN. De workflow doet twee aparte
    # aanroepen: eerst --alleen bag, daarna --alleen labels. Begon dit met een
    # lege dict, dan schreef de labelronde een stand zonder de sleutels bag en
    # panden, en waren postcodes_leeg, ronde_af en de hele pandronde weg
    # voordat het gezondheidsrapport ernaar keek. Alle vier de controles die
    # erop staan vuurden dan nooit, en de voorraad kon stil te laag zijn
    # terwijl het rapport OK meldde. Precies de fout die dit standsbestand
    # moest voorkomen, nu in het bestand zelf. Daarom opbouwen op wat er al
    # staat.
    #
    # Elke fase stempelt haar eigen datum, zodat een fase die vandaag niet
    # draaide niet als vers wordt gelezen.
    uit = dict(_lees(STAND, {}).get("ronde") or {})
    uit["bijgewerkt"] = dt.date.today().isoformat()
    if args.alleen != "labels":
        # EERST DE PANDEN, DAN DE OBJECTEN. De omzetting van PDOK's pandsleutel
        # naar de BAG-pandidentificatie moet klaar zijn voordat de objecten
        # worden weggeschreven, anders staat er een sleutel in voorraad.json
        # die nergens op aansluit. Mislukt deze ronde, dan blijft het veld pand
        # leeg en gaat de rest door; de reden staat in de stand.
        panden, uit["panden"] = fase_panden(args.panden_minuten * 60)
        uit["panden"]["datum"] = dt.date.today().isoformat()
        print("Panden: " + json.dumps(uit["panden"], ensure_ascii=False),
              file=sys.stderr)
        uit["bag"] = fase_bag(voorraad, pcs, args.bag_minuten, panden)
        uit["bag"]["datum"] = dt.date.today().isoformat()
        print("BAG: " + json.dumps(uit["bag"], ensure_ascii=False),
              file=sys.stderr)
    if args.alleen != "bag":
        uit["labels"] = fase_labels(voorraad, args.labels_minuten)
        uit["labels"]["datum"] = dt.date.today().isoformat()
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
