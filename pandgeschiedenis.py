#!/usr/bin/env python3
"""
Geschiedenis per pand: wat er in de loop van de tijd met een adres gebeurt.

Vastgelegd op het BAG-pand en niet op het adres. Bij een splitsing verdwijnt
het oude huisnummer niet, er komen nieuwe bij: 15 wordt 15, 15-A en 15-B. Op
het adres vastgelegd zie je drie losse nieuwe woningen zonder verleden; op het
pand zie je dat 180 m2 in drieen is gegaan.

Wat er per pand wordt bijgehouden:
- te koop gezet, prijs gewijzigd, verkocht (uit verkopen.txt);
- vergunning aangevraagd of verleend (uit het bekendmakingenarchief);
- de BAG: hoeveel woningen het pand telt en hoe groot ze zijn. Verandert dat,
  dan is de splitsing geregistreerd;
- het energielabel per adres. Na een splitsing komen de labels vaak weken of
  maanden later; een wijziging is daarom een eigen gebeurtenis.

De BAG en de labels worden alleen op zondag opgevraagd; die veranderen niet
dagelijks en elke opvraging kost een verzoek.

Gebruik:
  python pandgeschiedenis.py --uit digests/2026-09-27-geschiedenis.md
  python pandgeschiedenis.py --volledig   # ook BAG en labels bijwerken
"""

import argparse
import datetime as dt
import json
import os
import re
import statistics as st
import sys
import time

import pandsleutel as _psl

PAD = "pandgeschiedenis.json"
VERKOPEN = "verkopen.txt"
ARCHIEF = "bekendmakingen_archief.json"
# Hoeveel panden per ronde tegen de BAG en EP-Online worden gehouden. Elke
# controle is een paar opvragingen, dus dit is een afweging tussen snelheid en
# belasting van die diensten. Met de omgevingsvariabele BAG_PER_RONDE tijdelijk
# te verhogen als je een achterstand wilt inlopen.
MAX_BAG_PER_RONDE = int(os.environ.get("BAG_PER_RONDE") or 500)
# Een GitHub-job stopt na zes uur. Bij een grote inhaalronde stoppen we zelf
# eerder en netjes, zodat het werk dat af is bewaard blijft in plaats van
# verloren te gaan bij een afgekapte job.
MINUTEN_BUDGET = int(os.environ.get("BAG_MINUTEN") or 0)
_START = dt.datetime.now()


def _rest_vastleggen(rest):
    """
    Hoeveel panden er nog wachten, zodat de workflow zelf kan doorgaan.

    Een GitHub-job stopt na zes uur. Blijft er werk over, dan start de workflow
    een vervolgronde; dit bestand is het sein daarvoor.
    """
    try:
        with open("bag_rest.json", "w", encoding="utf-8") as f:
            json.dump({"rest": max(0, int(rest)),
                       "datum": dt.date.today().isoformat()}, f)
    except Exception:
        pass


def tijd_op():
    """Of het tijdbudget voor deze ronde op is."""
    if not MINUTEN_BUDGET:
        return False
    return (dt.datetime.now() - _START).total_seconds() > MINUTEN_BUDGET * 60
PAUZE_TUSSEN = 0.2

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass


def sleutel(adres):
    """
    De sleutel van een pand, uit pandsleutel.

    Dit was een eigen regel, een van de veertien in elf bestanden die allemaal
    hetzelfde bedoelden en op drie punten uiteenliepen. Hij blijft hier staan
    omdat andere modules hem importeren, maar hij rekent niet meer zelf.
    """
    return _psl.sleutel(adres)


def lees(pad, standaard):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return standaard


def bewaar(geschiedenis):
    """
    Wegschrijven in de compacte vorm: gedeelde pandgegevens een keer.

    Aubadestraat 12 en 16 zijn hetzelfde BAG-pand met 24 woningen; in de oude
    vorm stond die lijst bij allebei. Bij het inlezen wordt het weer uitgevouwen,
    dus voor elke lezer verandert er niets.
    """
    try:
        from pandlezer import compact
        # HET VERSLAG VAN HET SAMENVOEGEN ERBIJ. Twee adresrecords van
        # hetzelfde pand kunnen elk een deel van de labels hebben; die
        # worden samengevoegd in plaats van overschreven. Een botsing op
        # dezelfde sleutel is iets om te zien, dus hij komt in de log en
        # niet alleen in de teller.
        verslag = {}
        uit = compact(geschiedenis, verslag)
        if verslag.get("sleutels_samengevoegd") or verslag.get(
                "botsende_sleutels"):
            print(f"Compact: {verslag['sleutels_samengevoegd']} sleutels "
                  f"samengevoegd uit tweede adresrecords, "
                  f"{verslag['botsende_sleutels']} botsingen op dezelfde "
                  f"sleutel met een andere waarde", file=sys.stderr)
    except Exception as e:
        print(f"Compact opslaan lukt niet, oude vorm gebruikt: {str(e)[:80]}",
              file=sys.stderr)
        uit = geschiedenis
    with open(PAD, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False, indent=1, sort_keys=True)


BEKENDE_VERKOOPDATUMS = "verkoopdatums.txt"


def bekende_verkoopdatums(pad=BEKENDE_VERKOOPDATUMS):
    """
    Verkoopdatums die wij WETEN, tegenover de datums die wij AFLEIDEN.

    In verkopen.txt is de datum de dag waarop wij een pand als verkocht zagen
    staan. Dat is iets anders dan de dag waarop het verkocht is:
    Groesbeekseweg 118 stond bij ons op 28 september omdat wij hem toen in een
    geplakte lijst zagen, terwijl Funda 21 september geeft. Zeven dagen.

    Staat een adres in dit bestand, dan is de datum bekend en vervangt hij het
    venster EN de datum van de gebeurtenis: de verkoopregel komt op 21
    september te staan en de regel op onze kijkdag gaat eruit. Staat het er
    niet in, dan blijft het venster, want een vaag maar eerlijk antwoord is
    beter dan een scherp antwoord dat niet klopt.
    """
    uit = {}
    try:
        with open(pad, encoding="utf-8") as f:
            regels = f.read().splitlines()
    except Exception:
        return uit
    for regel in regels:
        kaal = regel.strip()
        if not kaal or kaal.startswith("#"):
            continue
        velden = [v.strip() for v in kaal.split("|")]
        if len(velden) < 2:
            continue
        adres, datum = velden[0], velden[1]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum or ""):
            # Een regel zonder bruikbare datum wordt overgeslagen en niet
            # half ingelezen: een adres met een lege datum zou het venster
            # vervangen door niets.
            continue
        uit[adres.lower()] = {"datum": datum,
                              "bron": velden[2] if len(velden) > 2 else ""}
    return uit


def voeg_toe(pand, datum, soort, tekst, bron, eenmalig_per_dag=()):
    """
    Een gebeurtenis toevoegen als die er nog niet staat.

    EENMALIG_PER_DAG: soorten waarvan er per pand en per dag maar een kan
    bestaan. Voor die soorten vervangt een nieuwe tekst de oude in plaats van
    ernaast te komen staan.

    Waarom dat nodig is: het ontdubbelen kijkt naar de tekst, dus zodra wij de
    formulering van een gebeurtenis verbeteren, komt die als tweede regel naast
    de oude te staan. Op 13 oktober gold dat voor dertien verkopen waarvan de
    tekst "verkoopdatum onbekend; uit een geplakte lijst" werd vervangen door
    het venster waarin de verkoop moet hebben gelegen. Zonder deze uitzondering
    had elk van die panden twee verkoopregels met dezelfde datum gekregen, en
    las het dossier als twee verkopen.
    """
    for g in pand["gebeurtenissen"]:
        if g["datum"] == datum and g["soort"] == soort and g["tekst"] == tekst:
            return False
    if soort in eenmalig_per_dag:
        for g in pand["gebeurtenissen"]:
            if g["datum"] == datum and g["soort"] == soort:
                g["tekst"], g["bron"] = tekst, bron
                return False
    pand["gebeurtenissen"].append({"datum": datum, "soort": soort,
                                   "tekst": tekst, "bron": bron})
    pand["gebeurtenissen"].sort(key=lambda g: g["datum"])
    return True


def uit_verkopen(geschiedenis):
    """Te koop, prijswijziging en verkocht, uit de waarnemingen."""
    nieuw = 0
    per_adres = {}
    for regel in lees_regels(VERKOPEN):
        v = [x.strip() for x in regel.split("|")]
        if len(v) < 7 or not v[2].isdigit():
            continue
        adres, plaats, prijs, status, datum = v[0], v[1], int(v[2]), v[3].lower(), v[4]
        # Huuradvertenties horen er wel in: bij een appartement in een complex
        # is "wat werd hier eerder voor gevraagd" het meest directe antwoord op
        # de vraag wat je kunt vragen.
        pass
        per_adres.setdefault(sleutel(adres), []).append(
            {"adres": adres, "plaats": plaats, "prijs": prijs, "status": status,
             "datum": datum, "opp": v[6] or None, "bron": v[5] if len(v) > 5 else ""})

    # De datums die wij weten, eenmaal ingelezen voor alle panden. Het pad gaat
    # expliciet mee: een default-waarde wordt bij het inlezen van de module
    # eenmaal vastgelegd, en dan wijst hij naar het oude bestand ook als de
    # constante daarna verandert. De proef trapte daar als eerste in.
    bekend_per_adres = bekende_verkoopdatums(BEKENDE_VERKOOPDATUMS)

    for sl, rijen in per_adres.items():
        rijen.sort(key=lambda r: r["datum"])
        pand = geschiedenis.setdefault(sl, {"adres": rijen[0]["adres"],
                                            "pand_id": None,
                                            "gebeurtenissen": []})
        pand["adres"] = rijen[-1]["adres"]
        vorige_prijs = None
        gezien_te_koop = False
        # De datum van de vorige waarneming van dit pand. Die geeft bij een
        # verkoop uit een geplakte lijst de ondergrens van het venster waarin
        # de verkoop moet hebben plaatsgevonden.
        vorige_waarneming = None
        for r in rijen:
            if r["status"].startswith(("te koop", "nieuw")):
                if not gezien_te_koop:
                    nieuw += voeg_toe(pand, r["datum"], "te koop",
                                      f"te koop voor €{r['prijs']:,}".replace(",", ".")
                                      + (f", {r['opp']} m2" if r["opp"] else ""),
                                      "aanbod")
                    gezien_te_koop = True
                elif (vorige_prijs and r["prijs"] != vorige_prijs
                      and "plak" not in (r.get("bron") or "")):
                    richting = "verlaagd" if r["prijs"] < vorige_prijs else "verhoogd"
                    nieuw += voeg_toe(pand, r["datum"], "prijswijziging",
                                      f"prijs {richting} van "
                                      + f"€{vorige_prijs:,}".replace(",", ".")
                                      + " naar " + f"€{r['prijs']:,}".replace(",", "."),
                                      "aanbod")
                vorige_prijs = r["prijs"]
            elif r["status"].startswith("te huur"):
                soort = ("kamer te huur" if "kamer" in r["status"]
                         else "te huur aangeboden")
                nieuw += voeg_toe(pand, r["datum"], "verhuur",
                                  f"{soort} voor €{r['prijs']:,}".replace(",", ".")
                                  + " per maand"
                                  + (f", {r['opp']} m2" if r["opp"] else "")
                                  + (" (inclusief servicekosten)"
                                     if "incl" in (r.get("bron") or "") else ""),
                                  r.get("bron") or "aanbod")
            elif r["status"] == "verkocht":
                # Funda toont de laatste vraagprijs, niet de koopsom; die staat
                # alleen bij het Kadaster. Zo noemen we het dus ook.
                # Uit een geplakte lijst kennen we de verkoopdatum niet. De
                # datum van de gebeurtenis is dan de dag dat WIJ het zagen.
                #
                # WAT HIER FOUT GING. De tekst zei alleen "verkoopdatum
                # onbekend; uit een geplakte lijst", en de gebeurtenis droeg de
                # plakdatum met de markering "nieuw". Op 13 oktober opende de
                # brief aan pa daarmee zo: "Vandaag staan er vijf panden als
                # verkocht gemarkeerd ... Maar het aantal op een dag zegt wel
                # iets: er wordt flink verkocht." Vijf verkopen op een dag was
                # geen marktbeweging maar onze eigen boekhouding: die vijf
                # panden stonden drie tot zes weken op Funda als verkocht.
                #
                # Een ondergrens hebben we wel, en die is hard: de vorige keer
                # dat wij dit pand zagen stond het nog niet als verkocht. Dus
                # noemen we het venster in plaats van niets, en zeggen we er
                # bij dat de datum onze waarneming is.
                zonder_datum = "plak" in (r.get("bron") or "")
                # EEN DATUM DIE WIJ WETEN GAAT VOOR EEN VENSTER DAT WIJ
                # AFLEIDEN. Zie bekende_verkoopdatums().
                _bekend = bekend_per_adres.get((r.get("adres") or "").lower())
                # EN DAN VERVALT ONZE EIGEN KIJKDAG HELEMAAL. Mark, 14 oktober:
                # "Wanneer de exacte datum bekend is kan de 28 sept toch gewoon
                # komen te vervallen?" Ja. Eerst zette ik de echte datum alleen
                # in de TEKST en bleef de gebeurtenis op 2026-09-28 staan met
                # bron "aanbod". Dan klopt de zin, maar blijft het pand buiten
                # de bezitsduur- en prijsgroeiparen, want verkoopdatum_bekend()
                # kijkt naar die bron. Een datum die in de tekst staat maar
                # niet in het veld is geen datum die wij gebruiken.
                datum_gebeurtenis = r["datum"]
                bron_gebeurtenis = "aanbod"
                if _bekend:
                    # In de zin alleen WAAR hij vandaan komt, in het bronveld
                    # de hele herkomst. Anders luidt de regel in de brief
                    # "volgens Funda, verkoopdatum op de advertentie, gezien
                    # door Mark op 14-10-2026", en dat is boekhouding midden in
                    # een verhaal over een pand.
                    _kort = (_bekend.get("bron") or "").split(",")[0].strip()
                    wanneer = (f" (verkocht op {_bekend['datum']}"
                               + (f", volgens {_kort}" if _kort else "")
                               + ")")
                    datum_gebeurtenis = _bekend["datum"]
                    bron_gebeurtenis = (_bekend.get("bron")
                                        or BEKENDE_VERKOOPDATUMS)
                elif zonder_datum and vorige_waarneming and vorige_waarneming < r["datum"]:
                    wanneer = (f" (verkocht tussen {vorige_waarneming} en "
                               f"{r['datum']}; {r['datum']} is de dag dat wij "
                               f"het zagen, niet de verkoopdatum)")
                elif zonder_datum:
                    wanneer = (f" (verkoopdatum onbekend; {r['datum']} is de "
                               f"dag dat wij het in een geplakte lijst zagen)")
                else:
                    wanneer = ""
                if datum_gebeurtenis != r["datum"]:
                    # De verkoopregel die DEZE waarneming eerder opleverde
                    # stond op onze kijkdag. Die vervalt nu, anders leest het
                    # dossier als twee verkopen: een op 21 en een op 28
                    # september. Alleen de gebeurtenis van deze waarneming
                    # (zelfde dag, soort verkocht, bron "aanbod") gaat eruit.
                    # Een echte eerdere verkoop van hetzelfde pand staat op een
                    # andere dag en blijft dus staan.
                    for _oud in [g for g in pand["gebeurtenissen"]
                                 if g["datum"] == r["datum"]
                                 and g["soort"] == "verkocht"
                                 and g.get("bron") == "aanbod"]:
                        pand["gebeurtenissen"].remove(_oud)
                nieuw += voeg_toe(pand, datum_gebeurtenis, "verkocht",
                                  "verkocht, laatste vraagprijs "
                                  + f"€{r['prijs']:,}".replace(",", ".")
                                  + (f", {r['opp']} m2" if r["opp"] else "")
                                  + wanneer,
                                  bron_gebeurtenis,
                                  eenmalig_per_dag=("verkocht",))
            elif r["status"].startswith(("onder bod", "onder optie",
                                         "onder voorbehoud",
                                         "verkocht onder voorbehoud",
                                         "in onderhandeling")):
                # Funda vat drie stadia samen als "in onderhandeling": onder
                # bod, onder optie en verkocht onder voorbehoud. Dat zijn geen
                # synoniemen. Onder bod is nog onderhandelen en kan makkelijk
                # afketsen; verkocht onder voorbehoud is vrijwel een deal met
                # alleen de financiering of de bouwkundige keuring nog open.
                # Daarom een gezamenlijke soort voor de meting, met het stadium
                # in de tekst zodat het verschil niet verdwijnt.
                stadium = r["status"].strip().lower()
                if stadium.startswith("in onderhandeling"):
                    stadium = "in onderhandeling, stadium onbekend"
                nieuw += voeg_toe(pand, r["datum"], "in onderhandeling",
                                  f"{stadium}, vraagprijs "
                                  + f"€{r['prijs']:,}".replace(",", ".")
                                  + (f", {r['opp']} m2" if r["opp"] else ""),
                                  "aanbod")
            # Aan het eind van elke waarneming, zodat de volgende regel weet
            # wanneer wij dit pand voor het laatst zagen.
            if r["datum"]:
                vorige_waarneming = r["datum"]
    return nieuw


def lees_regels(pad):
    if not os.path.exists(pad):
        return []
    with open(pad, encoding="utf-8") as f:
        return [r.strip() for r in f if r.strip()]


def uit_archief(geschiedenis):
    """
    Vergunningen en meldingen, ook op adressen die nooit te koop stonden.

    Eerder werden alleen panden uit het aanbod gevolgd, en dan mist een pand
    waar de eigenaar iets aanvraagt zonder het ooit te koop te zetten. Dat is
    juist het soort pand waar een verhaal in zit. Alle panden volgen hoeft niet:
    een pand zonder gebeurtenis heeft geen geschiedenis, en de signalen komen
    vanzelf binnen.
    """
    archief = lees(ARCHIEF, {})
    if not archief:
        return 0
    nieuw = 0

    # Eerst de adressen uit het archief zelf als pand opnemen
    try:
        from bekendmakingen_archief import adres_uit_titel
    except Exception:
        adres_uit_titel = None
    for k, items in archief.items():
        if k in geschiedenis:
            continue
        adres = None
        for t in items:
            uit = adres_uit_titel(t.get("titel") or "") if adres_uit_titel else None
            if uit:
                adres = f"{uit[0]} {uit[1]}"
                break
        if not adres:
            continue
        # DE SLEUTEL KOMT UIT HET ADRES EN NIET UIT HET ARCHIEF.
        #
        # Hier stond het omgekeerde, met de reden dat een pand anders niet
        # matcht met zijn eigen bekendmakingen: het archief sleutelt op de
        # straatnaam uit de titel, en "aan de Dominicanenstraat 30" levert
        # daar "dedominicanenstraat30" op. Dat klopte voor het matchen en
        # ging mis bij het aanmaken. De controle hieronder keek namelijk maar
        # naar één vorm, dus een pand dat al onder "dominicanenstraat30"
        # stond kreeg een tweede record onder de de-vorm.
        #
        # Dat heeft 56 panden in dit bestand dubbel gezet en 4 in
        # kamerverhuur_objecten.json: 1.777 records voor 1.721 panden. In de
        # helft die een lezer met de schone sleutel niet vindt, zaten 60
        # gebeurtenissen. Bij Professor Molkenboerstraat 18 was dat de
        # onttrekking van 2018 en de melding brandveilig gebruik van 2025,
        # dus voor de kamerverhuurtoets het verschil tussen onttrokken en
        # schoon.
        #
        # pandsleutel.zoek() kijkt naar alle vormen waaronder het pand kan
        # staan, dus het matchen blijft werken, en aanmaken gebeurt onder de
        # canonieke sleutel. Het lidwoord verdwijnt daarmee ook uit de
        # weergave, dus de reparatie van een regel verder is niet meer nodig.
        kaal = re.sub(r"(?<=\d)[a-z]{1,2}$", "", k)
        bestaand, _rec = _psl.zoek(geschiedenis, adres)
        if bestaand or kaal in geschiedenis:
            continue
        # HET LIDWOORD GAAT UIT DE SLEUTEL EN NIET UIT DE WEERGAVE. Hier
        # stond eerst een regel die "de" ook uit het adres haalde. Dat is
        # fout: bij De Geerkamp, De Kluijskamp en De Ruyterstraat hoort het
        # lidwoord bij de straatnaam, en die zouden dan "Geerkamp 1652" gaan
        # heten in de brief. Uit een titel als "aan de Grotestraat 7" valt
        # niet te zien welk van de twee het is, dus blijft staan wat de bron
        # schreef. In de sleutel maakt het niets uit, want varianten() kent
        # beide vormen.
        geschiedenis.setdefault(_psl.sleutel(adres),
                                {"adres": adres, "pand_id": None,
                                 "gebeurtenissen": []})

    for sl, pand in list(geschiedenis.items()):
        m = re.match(r"^(.+?)\s+(\d+)", pand["adres"])
        if not m:
            continue
        basis = re.sub(r"[^a-z0-9]", "", m.group(1).lower()) + m.group(2)
        for k, items in archief.items():
            # Ook de nummers met een letter, want na een splitsing komt 15-A erbij
            if not (k == basis or (k.startswith(basis)
                                   and re.fullmatch(r"[a-z]{1,2}", k[len(basis):]))):
                continue
            for t in items:
                titel = (t.get("titel") or "")[:160]
                nieuw += voeg_toe(pand, (t.get("datum") or "")[:10], "bekendmaking",
                                  titel, "officiele bekendmakingen")
    return nieuw


def uit_kamerverhuur(geschiedenis):
    """
    De bekende kamerverhuurpanden als pand opnemen.

    Daar gebeurt per definitie iets: een vergunning of een melding. Ze volgen
    kost niets extra, want de gebeurtenissen komen uit bestanden die we al
    hebben.
    """
    register = lees("kamerverhuur_objecten.json", {})
    nieuw = 0
    for sl, r in register.items():
        adres = r.get("adres")
        if not adres or sl in geschiedenis:
            continue
        pand = geschiedenis.setdefault(sl, {"adres": adres, "pand_id": None,
                                            "gebeurtenissen": []})
        for b in r.get("bronnen", []):
            jaar = b.get("jaar")
            if jaar:
                nieuw += voeg_toe(pand, f"{jaar}-01-01", "kamerverhuur",
                                  f"{b.get('soort', 'kamerverhuur')} bekend "
                                  f"(jaar bij benadering)", b.get("bron", "register"))
    return nieuw


def _doelen(e):
    """
    Het gebruiksdoel als lijst, in welke vorm de BAG hem ook teruggeeft.

    adressenuitgebreid geeft "gebruiksdoelen" als lijst. In de voorraadtak
    bleek hetzelfde begrip bij een ander endpoint een string te zijn waar een
    lijst werd verwacht, en dat leverde op 10 oktober twee keer een lege
    uitkomst op zonder dat er iets faalde. Op een string werkt "woonfunctie"
    in d bij toeval vaak goed, en bij "bijeenkomstfunctie" niet. Daarom hier
    een keer omzetten in plaats van erop hopen.
    """
    d = e.get("gebruiksdoelen")
    if d is None:
        d = e.get("gebruiksdoel")
    if isinstance(d, str):
        return [x.strip() for x in d.replace(";", ",").split(",") if x.strip()]
    return list(d or [])


def tel_en_meld(eenheden, eerder, eerder_woon):
    """
    Uit de BAG-objecten van een pand: twee tellingen en de melding, of None.

    WONINGEN APART VAN DE REST. bag_eenheden_in_pand() geeft elk adresseerbaar
    object in het pand terug, mét gebruiksdoel, en dat gebruiksdoel werd
    weggegooid. Daarna heette elk object een "woning", dus een garage of
    berging met een eigen adres werd als woning geteld en gemeld.

    Dat is niet onschuldig. splitsing_voltooid.py vergelijkt dit aantal met
    het aantal dat de vergunning noemt, en de vergunning telt zelfstandige
    woonruimtes. Twee verschillende definities naast elkaar leggen levert een
    verschil op dat er niet is. Bij Hatertseweg 338 noemde het besluit 6
    zelfstandige woonruimtes en telde dit 7 objecten: 20, 147, 46, 24, 19, 23
    en 19 m2, waarvan twee op huisnummer 338 zelf en de rest op 338A tot en
    met 338E. De zondagsbrief van 11 oktober maakte dat verschil van 1 tot
    haar hoofdthema.

    Wat het gebruiksdoel van die zeven objecten is, staat hier niet: dat veld
    werd juist weggegooid, en zonder BAG-sleutel is het van buiten een run
    niet op te vragen. Deze functie leest het veld en telt wat er staat; de
    eerstvolgende ronde over dit pand zegt het.

    DIT STOND IN DE LUS EN STAAT ER NU BUITEN. Niet om de lus korter te maken,
    maar omdat de vier meldvormen hieronder alleen te beproeven zijn als er
    geen BAG-sleutel aan te pas komt. In de lus zijn ze met de hand nagekeken
    en dat is niet te herhalen.

    Geeft (nu, nu_woon, melding). melding is None als er niets te melden is.
    """
    nu = sorted((e.get("adres"), e.get("oppervlakte")) for e in eenheden)
    woon = [e for e in eenheden if "woonfunctie" in _doelen(e)]
    anders = [e for e in eenheden if "woonfunctie" not in _doelen(e)]
    nu_woon = sorted((e.get("adres"), e.get("oppervlakte")) for e in woon)
    if eerder is None or [tuple(x) for x in eerder] == nu:
        return nu, nu_woon, None

    maten = ", ".join(str(o) for _a, o in nu_woon if o)
    # Geen maten betekent geen woningen, of geen oppervlakte geregistreerd.
    # Dan hoort er geen ": m2" in de tekst te staan.
    staart = f": {maten} m2" if maten else ""
    extra = (f"; daarnaast "
             + (f"{len(anders)} andere objecten" if len(anders) != 1
                else "1 ander object")
             + " met een eigen adres") if anders else ""
    # DE VERGELIJKING OP DEZELFDE GRONDSLAG. Het veld bag_woningen is op 11
    # oktober toegevoegd, dus voor panden die eerder zijn opgehaald bestaat er
    # nog geen woningtelling van vroeger. Dan is "was N" niet te zeggen zonder
    # appels met peren te vergelijken, en zwijgt deze regel over het aantal in
    # plaats van een getal te noemen dat op een andere grondslag rust. De ronde
    # erna is het wel te zeggen. De vergelijking zelf blijft op bag_eenheden
    # staan, zodat deze toevoeging geen enkele valse wijziging meldt op de
    # 1.777 panden die al gevolgd worden.
    if eerder_woon is None:
        return nu, nu_woon, (f"de BAG telt nu {len(nu_woon)} woningen in dit "
                             f"pand{staart}{extra}")
    if len(nu_woon) != len(eerder_woon):
        return nu, nu_woon, (f"de BAG telt nu {len(nu_woon)} woningen in dit "
                             f"pand, was {len(eerder_woon)}{staart}{extra}")
    if [tuple(x) for x in eerder_woon] != nu_woon:
        return nu, nu_woon, (f"de oppervlaktes in de BAG zijn gewijzigd"
                             f"{staart or ' maar niet geregistreerd'}{extra}")
    # Alleen de niet-woningen zijn veranderd. Dat is geen splitsing en hoort
    # niet als woningtelling te klinken.
    return nu, nu_woon, (f"de BAG kent nu {len(anders)} object"
                         f"{'en' if len(anders) != 1 else ''} zonder "
                         f"woonfunctie in dit pand; het aantal woningen bleef "
                         f"{len(nu_woon)}")


VOORRAAD_PAD = "voorraad.json"


def koppel_objecten(geschiedenis, voorraad_pad=VOORRAAD_PAD):
    """
    Elk adres krijgt zijn verblijfsobject-id en de pand-id's, uit de voorraad.

    WAAROM. De BAG kent een woning als verblijfsobject en een gebouw als pand;
    een adres is alleen een naam. Toch koppelde deze keten op een tekst van
    straat plus huisnummer, en op 14 oktober had geen enkel record hier een
    object-id. Dat ging stil mis: een adres is niet uniek over gemeenten
    (Bachstraat 3 bestaat drie keer), en een energielabel of oppervlakte hoort
    bij het object en niet bij een tekst. De adressleutel is nu alleen de
    voordeur: hier wordt hij een keer omgezet, daarna koppelt alles op id.

    KOST GEEN AANROEP. De voorraad heeft de objecten al, met hun panden.

    DE REGEL BIJ MEER DAN EEN OBJECT OP HETZELFDE ADRES. Alleen Nijmeegse
    objecten tellen (gemeentecode in het id). Daarna wint het object dat
    bestaat boven een gevormd object: dat laatste is een geregistreerde maar
    nog niet gerealiseerde splitsing of transformatie, en wordt apart bewaard
    als vbo_gevormd, want dat is zelf een signaal. Blijven er twee bestaande
    objecten over, dan wordt er niets gekozen en geteld als niet eenduidig.
    Gemeten op 14 oktober over 1.807 adressen: 1.175 een bestaand object,
    83 een bestaand plus een gevormd, 47 alleen een gevormd, 0 niet eenduidig,
    502 niet in de voorraad.

    Een pand-id dat er al stond en niet bij het object hoort, wordt niet
    overschreven maar geteld. Op 14 oktober een keer: Tweede Walstraat 100,
    een transformatie, waar het bestaande object in een ander pand ligt dan
    het pand-id dat de oude opzoeking (eerste pand van het antwoord) koos.
    """
    try:
        from voorraad_bag import GEMEENTECODE
    except Exception:
        GEMEENTECODE = "0268"
    try:
        with open(voorraad_pad, encoding="utf-8") as f:
            v = json.load(f) or {}
    except Exception:
        return {"overgeslagen": "voorraad niet te lezen"}
    per = {}
    for soort in ("adressen", "niet_woningen", "pijplijn"):
        for vid, r in (v.get(soort) or {}).items():
            if not str(vid).startswith(GEMEENTECODE) or not r.get("adres"):
                continue
            per.setdefault(sleutel(r["adres"]), []).append((vid, r))
    tel = {"bestaand": 0, "bestaand_en_gevormd": 0, "alleen_gevormd": 0,
           "niet_eenduidig": 0, "niet_in_voorraad": 0,
           "pand_id_aangevuld": 0, "pand_id_anders": 0}
    for pand in geschiedenis.values():
        if not isinstance(pand, dict) or not pand.get("adres"):
            continue
        kandidaten = per.get(sleutel(pand["adres"])) or []
        gevormd = [x for x in kandidaten
                   if "gevormd" in str(x[1].get("status") or "").lower()]
        bestaand = [x for x in kandidaten if x not in gevormd]
        if len(bestaand) == 1:
            gekozen = bestaand[0]
            tel["bestaand_en_gevormd" if gevormd else "bestaand"] += 1
        elif not bestaand and len(gevormd) == 1:
            gekozen, gevormd = gevormd[0], []
            tel["alleen_gevormd"] += 1
        else:
            tel["niet_eenduidig" if kandidaten else "niet_in_voorraad"] += 1
            continue
        vid, r = gekozen
        panden = [x for x in (r.get("panden") or [r.get("pand")]) if x]
        pand["vbo"] = vid
        pand["vbo_panden"] = panden
        if gevormd:
            pand["vbo_gevormd"] = sorted(x[0] for x in gevormd)
        else:
            pand.pop("vbo_gevormd", None)
        if not pand.get("pand_id") and panden:
            pand["pand_id"] = panden[0]
            tel["pand_id_aangevuld"] += 1
        elif pand.get("pand_id") and panden and pand["pand_id"] not in panden:
            tel["pand_id_anders"] += 1
    print("Objecten: " + ", ".join(f"{k} {n}" for k, n in tel.items()),
          file=sys.stderr)
    return tel


def neem_object_over(pand, bag, vandaag):
    """
    Het object-id uit een BAG-antwoord bij het adres zetten.

    Alleen een Nijmeegs object (gemeentecode in het id), en alleen als er nog
    geen object-id staat: wat koppel_objecten() uit de voorraad haalde, heeft
    dezelfde bron en gaat voor. Het pand-id wordt hier niet aangeraakt.
    """
    try:
        from voorraad_bag import GEMEENTECODE
    except Exception:
        GEMEENTECODE = "0268"
    pand["vbo_gevraagd"] = vandaag
    vid = str((bag or {}).get("adresseerbaarObjectIdentificatie") or "")
    if pand.get("vbo") or not vid.startswith(GEMEENTECODE):
        return False
    pand["vbo"] = vid
    pand["vbo_panden"] = list((bag or {}).get("panden")
                              or [x for x in [(bag or {}).get("pand")] if x])
    return True


def bij_bag(geschiedenis, alleen_gevolgd=True, alleen_nieuwe=False):
    """
    De BAG opnieuw bevragen: is het aantal woningen in het pand veranderd?

    Alleen voor panden waar iets mee gebeurd is, en hoogstens een vast aantal
    per ronde, want elke opvraging is een verzoek.

    Met alleen_nieuwe doet hij uitsluitend panden die nog nooit zijn nagekeken.
    Dat zijn er een handvol per dag, de nieuwe aanbiedingen uit de attendering,
    en die hoeven niet tot zondag te wachten. Het opnieuw nakijken van de hele
    voorraad op veranderingen is iets anders: dat zijn duizenden opvragingen en
    dat hoort wel in de weekronde.
    """
    try:
        from marktprijzen_bag import (bag_adres_uitgebreid, bag_eenheden_in_pand,
                                      split_huisnummer, BAG_API_KEY)
    except Exception as e:
        leg_vast("geschiedenis", f"BAG-functies niet te laden: {str(e)[:120]}")
        # Twee waarden terug, want de aanroeper pakt er twee uit. Met een enkele
        # nul liep de hele stap vast zodra er iets ontbrak, en dat is precies
        # het moment waarop je een nette melding wilt in plaats van een crash.
        return 0, []
    if not BAG_API_KEY:
        # Zonder sleutel geeft elke opvraging een 401. Eenmaal melden is genoeg;
        # honderden mislukte verzoeken vullen alleen het logboek.
        leg_vast("geschiedenis", "Geen BAG_API_KEY in deze stap: de BAG en de "
                                 "energielabels zijn niet bijgewerkt.")
        print("Geen BAG-sleutel; BAG-controle overgeslagen", file=sys.stderr)
        return 0, []
    nieuw, gedaan, deze_ronde = 0, 0, []
    geen_id, bekeken = 0, 0
    vandaag = dt.date.today().isoformat()
    nooit = sum(1 for p in geschiedenis.values() if not p.get("bag_gezien"))
    def volgorde(paar):
        """
        Wie er het eerst aan de beurt is.

        Eerst panden die nog nooit zijn nagekeken. Daarna wat in het aanbod zit
        of verkocht is, en dan de rest, telkens de langst niet bekekene eerst.

        Waarom die eerste groep voorgaat: sinds de 505 geplakte verkopen erin
        zitten, vulden die in hun eentje de quota van 500 per ronde. De panden
        die nog nooit waren nagekeken kwamen daardoor nooit aan de beurt, hoe
        vaak er ook werd gedraaid, en hun aantal liep juist op.
        """
        pand = paar[1]
        soorten = {g["soort"] for g in pand["gebeurtenissen"]}
        if not pand.get("bag_gezien"):
            haast = 0
        elif soorten & {"te koop", "verkocht", "prijswijziging"}:
            haast = 1
        else:
            haast = 2
        return (haast, pand.get("bag_gezien") or "")

    wachtrij = sorted(geschiedenis.items(), key=volgorde)
    for sl, pand in wachtrij:
        if tijd_op():
            print(f"Tijdbudget van {MINUTEN_BUDGET} minuten op na {gedaan} "
                  f"panden; de rest volgt in een vervolgronde", file=sys.stderr)
            _rest_vastleggen(len(wachtrij) - gedaan)
            break
        if gedaan >= MAX_BAG_PER_RONDE:
            _rest_vastleggen(len(wachtrij) - gedaan)
            break
        if alleen_nieuwe and pand.get("bag_gezien"):
            # De wachtrij zet de nooit nagekeken panden vooraan, dus zodra hier
            # een pand met een datum langskomt, zijn we er doorheen.
            break
        soorten = {g["soort"] for g in pand["gebeurtenissen"]}
        if not alleen_nieuwe and alleen_gevolgd and not (
                soorten & {"verkocht", "bekendmaking", "kamerverhuur"}):
            continue
        # Een pand dat geen pand-id oplevert, mag het een paar keer opnieuw
        # proberen en daarna niet meer. Dit blok haalde eerst elke run de
        # markering weg, waardoor dezelfde panden eeuwig terugkwamen, elke
        # ronde de quota vulden en het aantal "nooit nagekeken" opliep in
        # plaats van af. Het was bedoeld als eenmalige reparatie na de
        # bag_dump-fout van 28 september.
        if pand.get("bag_zonder_id") and not pand.get("pand_id"):
            pogingen = int(pand.get("bag_pogingen") or 0)
            if pogingen >= 3:
                continue
            pand["bag_pogingen"] = pogingen + 1
            pand.pop("bag_zonder_id", None)
            pand.pop("bag_gezien", None)
        bekeken += 1
        pand_id = pand.get("pand_id")
        # HET OBJECT-ID OOK, EN NIET ALLEEN HET PAND. Deze opzoeking kreeg
        # het object-id altijd al terug en gooide het weg. Een adres dat
        # koppel_objecten() niet uit de voorraad kon halen (502 op 14
        # oktober, vooral buiten de ring), krijgt het hier, een keer: daarna
        # staat vbo_gevraagd erin, zodat een adres zonder antwoord niet elke
        # ronde een extra aanroep kost.
        if not pand_id or (not pand.get("vbo")
                           and not pand.get("vbo_gevraagd")):
            # bag_dump is een hulpfunctie die de respons print en niets
            # teruggeeft; die stond hier eerst, waardoor geen enkel pand een
            # pand-id kreeg. Dit is de opzoeking die de verrijking ook gebruikt.
            varianten = split_huisnummer(pand["adres"]) or []
            bag = {}
            for straat, huisnr, letter, toev in varianten[:2]:
                bag = bag_adres_uitgebreid(straat, huisnr, letter, toev,
                                           "Nijmegen") or {}
                if bag.get("pand"):
                    break
            if not pand_id:
                pand_id = bag.get("pand")
                pand["pand_id"] = pand_id
            neem_object_over(pand, bag, vandaag)
        if not pand_id:
            # Geen pand-id: dan kunnen we de eenheden niet opvragen. Wel
            # vastleggen dat we het geprobeerd hebben, anders blijven deze
            # panden elke ronde vooraan staan en komt de rest nooit aan de beurt.
            geen_id += 1
            pand["bag_gezien"] = vandaag
            pand["bag_zonder_id"] = vandaag
            gedaan += 1
            continue
        eenheden = bag_eenheden_in_pand(pand_id)
        gedaan += 1
        deze_ronde.append(sl)
        time.sleep(PAUZE_TUSSEN)
        pand["bag_gezien"] = vandaag
        if not eenheden:
            continue
        nu, nu_woon, melding = tel_en_meld(eenheden,
                                           pand.get("bag_eenheden"),
                                           pand.get("bag_woningen"))
        # DE TELLING EEN KEER BIJSCHRIJVEN, OOK ALS ER NIETS VERANDERDE.
        # Zonder dit wordt bag_woningen alleen gevuld bij een pand dat voor het
        # eerst wordt opgehaald of waarvan de eenheden wijzigen. De 1.263
        # panden die al eenheden hebben zouden het veld dus nooit krijgen, en
        # splitsing_voltooid.py vergelijkt daarop. Dat hoofdstuk zou dan
        # blijven melden dat het op een telling wacht die nooit komt: geen
        # foutmelding, geen verkeerd getal, alleen iets dat stilstaat. Het is
        # een inhaalslag van een ronde en daarna staat het er.
        #
        # Het meldt niets, en dat hoort zo: een gebeurtenis hoort bij een
        # waargenomen verandering in het pand, en hier is alleen onze eigen
        # administratie bijgewerkt. tel_en_meld() heeft de melding al bepaald
        # op de oude waarde, dus de tekst zegt nog steeds geen "was N" op een
        # grondslag die er niet was.
        if melding:
            nieuw += voeg_toe(pand, vandaag, "bag", melding,
                              "Basisregistratie Adressen en Gebouwen")
        pand["bag_eenheden"] = nu
        pand["bag_woningen"] = nu_woon
    over = max(nooit - gedaan, 0)
    print(f"BAG: {bekeken} panden bekeken, {gedaan} afgehandeld waarvan "
          f"{geen_id} zonder pand-id, nog {over} nooit gecontroleerd",
          file=sys.stderr)
    if bekeken and not deze_ronde:
        leg_vast("geschiedenis",
                 f"Van {bekeken} bekeken panden leverde er geen een pand-id op. "
                 f"Waarschijnlijk komt het adres niet door de BAG-opzoeking, of "
                 f"ontbreekt de sleutel in deze stap.")
    if not bekeken:
        leg_vast("geschiedenis",
                 "Geen enkel pand kwam in aanmerking voor de BAG-controle. "
                 "Draait de stap wel met --volledig, en hebben de panden een "
                 "gebeurtenis van het juiste soort?")
    return nieuw, deze_ronde


def voorraad_per_pand(pad=VOORRAAD_PAD):
    """
    De objecten uit de voorraad, per pand-id en dan per adressleutel.

    Een object dat in twee panden ligt, staat onder beide. Alleen Nijmeegse
    objecten (gemeentecode in het id).
    """
    try:
        from voorraad_bag import GEMEENTECODE
    except Exception:
        GEMEENTECODE = "0268"
    try:
        with open(pad, encoding="utf-8") as f:
            v = json.load(f) or {}
    except Exception:
        return {}
    uit = {}
    for soort in ("adressen", "niet_woningen", "pijplijn"):
        for vid, r in (v.get(soort) or {}).items():
            if not str(vid).startswith(GEMEENTECODE) or not r.get("adres"):
                continue
            for pid in (r.get("panden") or [r.get("pand")]):
                if pid:
                    uit.setdefault(pid, {})[sleutel(r["adres"])] = r
    return uit


def label_uit_voorraad(per_pand, pid, adres):
    """
    Het label van dit object volgens de voorraad, als de voorraad het weet.

    Geeft None als de voorraad dit object niet kent of het nog niet aan
    EP-Online heeft gevraagd; dan moet het label elders vandaan komen. Anders
    een dict zoals ep_energielabel() hem geeft, met "label" leeg als EP-Online
    voor dit object geen label kent. Een "geen label" van de kapotte aanroep
    van voor 12 oktober telt niet als antwoord (zie voorraad_bag).
    """
    r = (per_pand.get(pid) or {}).get(sleutel(adres)) if pid else None
    if not r or not r.get("label_gezien"):
        return None
    try:
        from voorraad_bag import _stuk_gevraagd
        if _stuk_gevraagd(r):
            return None
    except Exception:
        pass
    return {"label": r.get("label"), "registratiedatum": r.get("label_datum")}


def bij_labels(geschiedenis, alleen=None, voorraad_pad=VOORRAAD_PAD):
    """
    Het energielabel per adres in het pand; na een splitsing volgt dat later.

    Alleen voor de panden die deze ronde ook tegen de BAG zijn gehouden. Zonder
    die grens liep deze stap langs alle gevolgde panden, wat bij duizend panden
    al duizenden opvragingen betekent en na de archiefbackfill onhoudbaar wordt.

    EERST DE VOORRAAD, PAS DAARNA EP-ONLINE. Deze stap vroeg elk label zelf
    op, naast de labelfase van de voorraad die dat per verblijfsobject al
    doet. Twee verzamelingen van hetzelfde gegeven, en op 14 oktober kwamen
    ze per object 2.445 keer overeen en 1 keer niet (Scheidemakershof 43: D
    hier, C in de voorraad, die het een dag later vroeg). Nu leest deze stap
    het label van het object in de voorraad, gekoppeld op pand-id en adres
    binnen dat pand. Alleen een object dat de voorraad niet kent of nog niet
    vroeg, gaat naar EP-Online: op 14 oktober 1.756 objecten buiten de
    voorraad en 1.523 die hij wel kent maar niet vroeg (pijplijn en
    niet-woningen vraagt de labelfase niet).

    EN DIE ROUTE GEBRUIKT NU HET OBJECT-ID. Hier stond info.get("vbo"), maar
    bag_adres_uitgebreid() geeft dat veld niet terug; het heet daar
    adresseerbaarObjectIdentificatie. De exacte route op object-id is dus
    nooit gebruikt en elke vraag ging op postcode en huisnummer.
    """
    try:
        from marktprijzen_bag import (bag_adres_uitgebreid, ep_energielabel,
                                      BAG_API_KEY, EP_API_KEY)
    except Exception as e:
        leg_vast("geschiedenis", f"Labelfuncties niet te laden: {str(e)[:120]}")
        bag_adres_uitgebreid = ep_energielabel = None
        BAG_API_KEY = EP_API_KEY = ""
    # Zonder sleutels werkt alleen de voorraad. Dat is geen reden om te
    # stoppen, wel om het te zeggen: de objecten buiten de voorraad blijven
    # dan zonder label.
    kan_vragen = bool(BAG_API_KEY and EP_API_KEY and ep_energielabel)
    if not kan_vragen:
        leg_vast("geschiedenis", "Geen BAG_API_KEY of EP_API_KEY: labels "
                                 "alleen uit de voorraad; objecten buiten de "
                                 "voorraad blijven zonder label.")
    per_pand = voorraad_per_pand(voorraad_pad)
    nieuw, vandaag = 0, dt.date.today().isoformat()
    eerste = gewijzigd = gecorrigeerd = uit_voorraad = gevraagd = 0
    doel = set(alleen) if alleen is not None else set(geschiedenis)
    # Een BAG-pand kan meerdere adressen hebben die wij apart volgen:
    # Aubadestraat 12 en 16 zijn hetzelfde pand met 24 eenheden. Zonder deze
    # cache vraagt het script die 24 labels voor elk adres opnieuw op en slaat
    # ze ook twee keer op. Per pand-id een keer ophalen, de rest overnemen.
    per_pand_id, bespaard = {}, 0
    for sl, pand in geschiedenis.items():
        if sl not in doel:
            continue
        pid = pand.get("pand_id")
        if pid and pid in per_pand_id:
            # Zelfde gebouw, al gedaan. Alleen de labels overnemen; de
            # gebeurtenissen staan al bij het eerste adres van dit pand en
            # hoeven niet herhaald te worden.
            klaar = per_pand_id[pid]
            if klaar:
                pand["labels"] = dict(klaar)
                bespaard += len(klaar)
            continue
        adressen = [a for a, _o in (pand.get("bag_eenheden") or [])] or [pand["adres"]]
        labels = dict(pand.get("labels") or {})
        vroeg_iets = False
        for adres in adressen:
            ep = label_uit_voorraad(per_pand, pid, adres)
            bron = "EP-Online, via de voorraad"
            if ep is not None:
                uit_voorraad += 1
            else:
                if not kan_vragen:
                    continue
                m = re.match(r"^(.+?)\s+(\d+)\s*([A-Za-z]?)[-\s]*(\w*)$",
                             adres or "")
                if not m:
                    continue
                try:
                    info = bag_adres_uitgebreid(m.group(1), m.group(2),
                                                m.group(3), m.group(4),
                                                "Nijmegen") or {}
                    ep = ep_energielabel(
                        info.get("adresseerbaarObjectIdentificatie") or None,
                        info.get("postcode"), m.group(2), m.group(3),
                        m.group(4)) or {}
                except Exception:
                    continue
                gevraagd += 1
                vroeg_iets = True
                bron = "EP-Online"
            label = ep.get("label")
            if not label:
                continue
            if labels.get(adres) != label:
                was = labels.get(adres)
                # De datum van het label zelf, niet die van vandaag. Een label
                # uit 2019 dat wij nu pas ophalen is geen gebeurtenis van
                # vandaag; zo stond het wel in de geschiedenis en daarmee
                # leken honderden panden ineens iets gedaan te hebben.
                datum = (ep.get("registratiedatum") or "")[:10]
                try:
                    dt.date.fromisoformat(datum)
                except ValueError:
                    datum = vandaag
                vorige = max((g.get("datum") or "" for g in
                              pand.get("gebeurtenissen") or []
                              if g.get("soort") == "energielabel"
                              and f"van {adres} is" in (g.get("tekst") or "")),
                             default="")
                if was and datum < vorige:
                    # EEN CORRECTIE IS GEEN WIJZIGING. Het label is
                    # geregistreerd voor de dag waarop wij het andere
                    # opschreven, dus het pand is niet veranderd: wij hadden
                    # het verkeerd. Scheidemakershof 43 op 14 oktober: D
                    # opgeschreven op 3 oktober via postcode en huisnummer, C
                    # geregistreerd op 14 juli 2025 volgens het object-id.
                    tekst = (f"energielabel van {adres} is {label}, "
                             f"geregistreerd {datum}; hier stond eerder {was}, "
                             f"dat was onze fout en geen wijziging aan het pand")
                    gecorrigeerd += 1
                elif was:
                    tekst = f"energielabel van {adres} is nu {label}, was {was}"
                    gewijzigd += 1
                else:
                    # Voor het eerst opgehaald: dat is geen wijziging aan het
                    # pand maar een aanvulling van onze gegevens.
                    tekst = (f"energielabel van {adres} is {label}, "
                             f"geregistreerd {datum}")
                    eerste += 1
                nieuw += voeg_toe(pand, datum, "energielabel", tekst, bron)
                labels[adres] = label
        if labels:
            pand["labels"] = labels
        # Onthouden voor de andere adressen in hetzelfde BAG-pand.
        if pid:
            per_pand_id[pid] = labels
        if vroeg_iets:
            time.sleep(PAUZE_TUSSEN)
    print(f"Labels: {len(doel)} panden nagekeken; {uit_voorraad} objecten uit "
          f"de voorraad, {gevraagd} bij EP-Online gevraagd; {eerste} woningen "
          f"voor het eerst een label, {gewijzigd} werkelijk gewijzigd, "
          f"{gecorrigeerd} gecorrigeerd"
          + (f"; {bespaard} opvragingen bespaard doordat adressen hetzelfde "
             f"BAG-pand delen" if bespaard else ""), file=sys.stderr)
    return nieuw


# Welke gebeurtenissen iets zeggen over wat een eigenaar met een pand doet
ROUTE_SOORTEN = ("bekendmaking", "bag", "energielabel", "kamerverhuur", "verhuur")
ROUTE_WOORDEN = ("splits", "omzet", "kamerverhuur", "verbouw", "onttrek",
                 "woningvorming", "brandveilig", "vergunning")


def straat_van(adres):
    m = re.match(r"^(.+?)\s+\d", (adres or "").strip())
    return re.sub(r"[^a-z]", "", m.group(1).lower()) if m else ""


def _route_tekst(pand):
    """Een korte samenvatting van wat er met dit pand is gebeurd."""
    delen = []
    for g in pand["gebeurtenissen"]:
        if g["soort"] == "verkocht":
            delen.append(f"{g['datum'][:7]} verkocht")
        elif g["soort"] == "verhuur":
            delen.append(f"{g['datum'][:7]} {g['tekst'][:60]}")
        elif g["soort"] == "te koop" and delen:
            # Alleen als er al iets gebeurd is: dan is opnieuw te koop het
            # sluitstuk van de route en niet het begin
            delen.append(f"{g['datum'][:7]} weer te koop")
        elif g["soort"] in ROUTE_SOORTEN:
            tekst = g["tekst"].lower()
            if g["soort"] == "bekendmaking" and not any(w in tekst
                                                        for w in ROUTE_WOORDEN):
                continue
            kort = g["tekst"][:70].rstrip()
            delen.append(f"{g['datum'][:7]} {kort}")
    return " -> ".join(delen[-5:])


def precedenten(geschiedenis, adres, maximaal=4):
    """
    Wat vergelijkbare panden in dezelfde straat eerder hebben gedaan.

    Bedoeld voor het moment dat een pand te koop komt: is hier in de straat al
    eerder gesplitst, verkamerd of verbouwd, en wat ging daaraan vooraf? Dat
    zegt iets over wat de gemeente daar toestond en wat een koper er zag.
    """
    straat = straat_van(adres)
    if not straat:
        return []
    zelf = sleutel(adres)
    uit = []
    for sl, pand in geschiedenis.items():
        if sl == zelf or straat_van(pand.get("adres")) != straat:
            continue
        tekst = _route_tekst(pand)
        if not tekst:
            continue
        laatste = max((g["datum"] for g in pand["gebeurtenissen"]), default="")
        uit.append({"adres": pand["adres"], "route": tekst, "laatste": laatste,
                    "aantal": len(pand["gebeurtenissen"])})
    uit.sort(key=lambda x: x["laatste"], reverse=True)
    return uit[:maximaal]


BUURTBEELD_PAD = "buurtbeeld.json"

# Waar een bekendmaking over gaat, en hoe hij afliep
_INGREEP = re.compile(r"splits|omzet|kamerverhuur|woningvorming|onttrek", re.I)
_AANVRAAG = re.compile(r"^aanvraag|ingediend", re.I)
_VERLEEND = re.compile(r"verleend|vergund", re.I)
_GEWEIGERD = re.compile(r"geweigerd|afgewezen", re.I)
_GESTOPT = re.compile(r"buiten behandeling|ingetrokken", re.I)


def buurt_van_pand(pand, cache):
    """De buurt van een pand, via de straatcache. Geen opvraging."""
    m = re.match(r"^(.+?)\s+\d", (pand.get("adres") or "").strip())
    if not m:
        return ""
    straat = m.group(1).strip()
    return cache.get(straat) or cache.get(straat.lower()) or ""


def _verkocht_details(pad="verkocht_details.json"):
    """De gegevens uit de geplakte verkooplijst, waaronder de makelaar."""
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


AFLOOP = {"verleend": "verleend", "geweigerd": "geweigerd",
          "ingetrokken": "ingetrokken",
          "buiten behandeling": "buiten behandeling gesteld"}


def straatprofiel(geschiedenis, straat, aanbod=None):
    """
    Alles wat we van een straat weten, op een rij.

    De straat is het juiste niveau: groot genoeg voor meerdere gevallen, klein
    genoeg om vergelijkbaar te zijn. Geen percentages en geen kansen, maar
    adressen die je kunt natrekken. Een geweigerde aanvraag telt daarbij net zo
    zwaar als een verleende.

    Wat hier niet in kan: misdrijfcijfers, want die gaan niet verder dan
    buurtniveau en zijn op straatniveau herleidbaar tot panden. En de volgorde
    van een verkoop ten opzichte van een besluit, want van geplakte verkopen
    kennen we de datum niet.
    """
    basis = sleutel(straat)
    vergunningen, kamers, verkocht, labels, eenheden = [], [], [], [], 0
    panden = 0
    for pand in geschiedenis.values():
        adres = pand.get("adres") or ""
        if not sleutel(adres).startswith(basis):
            continue
        panden += 1
        eenheden += len(pand.get("bag_eenheden") or [])
        for g in pand["gebeurtenissen"]:
            tekst = (g.get("tekst") or "")
            laag = tekst.lower()
            if g["soort"] == "bekendmaking" and any(
                    w in laag for w in ("splits", "verkamer", "woningvorming",
                                        "omzett", "onttrekk", "appartement")):
                afloop = next((v for k, v in AFLOOP.items() if k in laag), "")
                vergunningen.append({"adres": adres, "datum": g["datum"],
                                     "tekst": tekst[:110], "afloop": afloop})
            elif g["soort"] == "kamerverhuur":
                kamers.append({"adres": adres, "datum": g["datum"],
                               "tekst": tekst[:80]})
            elif g["soort"] == "verkocht":
                verkocht.append({"adres": adres, "tekst": tekst[:90]})
        for adr, label in (pand.get("labels") or {}).items():
            labels.append({"adres": adr, "label": label})

    te_koop = [w for w in (aanbod or [])
               if sleutel(w.get("adres") or "").startswith(basis)
               and (w.get("status") or "").lower().startswith("te koop")]
    return {
        "straat": straat,
        "panden_gevolgd": panden,
        "eenheden_in_bag": eenheden,
        "vergunningen": sorted(vergunningen, key=lambda x: x["datum"],
                               reverse=True),
        "verleend": [v for v in vergunningen if v["afloop"] == "verleend"],
        "geweigerd": [v for v in vergunningen
                      if v["afloop"] in ("geweigerd", "ingetrokken",
                                         "buiten behandeling gesteld")],
        "kamerverhuur": kamers,
        "verkocht": verkocht,
        "te_koop": [{"adres": w.get("adres"), "prijs": w.get("prijs"),
                     "opp": w.get("oppervlakte")} for w in te_koop],
        "labels": labels,
    }


def straatprofiel_tekst(profiel):
    """Het profiel als regels voor in het dossier of de brief."""
    if not profiel or not profiel.get("panden_gevolgd"):
        return []
    p = profiel
    r = [f"**{p['straat']}**: {p['panden_gevolgd']} panden gevolgd, "
         f"{p['eenheden_in_bag']} woningen volgens de BAG."]
    if p["vergunningen"]:
        r.append(f"Aanvragen en besluiten over splitsen, verkameren of "
                 f"onttrekken: {len(p['vergunningen'])}, waarvan "
                 f"{len(p['verleend'])} verleend en {len(p['geweigerd'])} "
                 f"geweigerd, ingetrokken of buiten behandeling.")
        for v in p["vergunningen"][:5]:
            r.append(f"- {v['datum']} {v['adres']}: {v['tekst']}")
    else:
        r.append("Geen enkele aanvraag over splitsen of verkameren sinds 2012.")
    if p["kamerverhuur"]:
        r.append(f"Bekend als kamerverhuur: "
                 + ", ".join(k["adres"] for k in p["kamerverhuur"][:6]) + ".")
    if p["verkocht"]:
        r.append(f"Verkocht in onze gegevens: {len(p['verkocht'])} panden "
                 f"({', '.join(v['adres'] for v in p['verkocht'][:6])}). "
                 f"Wanneer er is verkocht weten we niet.")
    if p["te_koop"]:
        r.append("Nu te koop: " + ", ".join(
            f"{w['adres']} €{w['prijs']:,}".replace(",", ".")
            for w in p["te_koop"][:5]) + ".")
    return r


def uit_model(geschiedenis, pad="verkoopdatums_model.json"):
    """
    Oudere plaatsingen en verkopen uit de modelophaler als gebeurtenis.

    Een verkoop uit 2016 is geen ruis maar geschiedenis van dat pand. Daarmee
    wordt zichtbaar waarvoor een woning eerder is aangeboden, hoe lang er tussen
    twee verkopen zat, en hoe de prijs van datzelfde pand zich heeft ontwikkeld.
    Dat laatste is zuiverder dan een buurtmediaan, want alles is gelijk behalve
    de tijd.

    De herkomst gaat mee in de bron, zodat een datum die een model ergens heeft
    gelezen nooit hetzelfde gewicht krijgt als een bekendmaking uit het
    gemeenteblad.
    """
    try:
        with open(pad, encoding="utf-8") as f:
            d = json.load(f) or {}
    except Exception:
        return 0
    nieuw = 0
    for rij in d.values():
        adres = rij.get("adres")
        if not adres:
            continue
        # Eerst zoeken onder alle vormen, dan pas aanmaken onder de canonieke.
        # Een setdefault op één vorm maakt een tweede record zodra dit pand
        # eerder onder een andere spelling is opgeslagen, en dat is precies
        # hoe de 56 dubbele records in dit bestand zijn ontstaan.
        _sl, pand = _psl.zoek(geschiedenis, adres)
        if pand is None:
            pand = geschiedenis.setdefault(_psl.sleutel(adres), {
                "adres": adres, "gebeurtenissen": []})
        pand.setdefault("adres", adres)
        pand.setdefault("gebeurtenissen", [])

        # Nieuwe vorm: een lijst gebeurtenissen per pand, want een woning kan in
        # tien jaar meerdere keren zijn verkocht. De oude vorm met een enkele
        # datum wordt nog gelezen, zodat eerder opgehaalde regels niet verdwijnen.
        rijen = rij.get("gebeurtenissen")
        if not rijen:
            rijen = []
            for veld, soort in (("te_koop_vanaf", "te koop"),
                                ("verkocht_op", "verkocht")):
                if rij.get(veld):
                    rijen.append({"soort": soort, "datum": rij[veld],
                                  "vraagprijs": rij.get("laatste_vraagprijs"),
                                  "bron": rij.get("bron"),
                                  "zeker": rij.get("zeker"),
                                  "eerdere_advertentie": bool(
                                      rij.get("waarschuwing"))})
        for g in rijen:
            if not g.get("datum"):
                continue
            prijs = g.get("vraagprijs")
            bedrag = f", vraagprijs €{prijs:,}".replace(",", ".") if prijs else ""
            merken = []
            if g.get("eerdere_advertentie"):
                merken.append("eerdere advertentie")
            if g.get("jaar_bij_benadering"):
                merken.append("jaar bij benadering")
            if g.get("volgorde_onlogisch"):
                merken.append("volgorde klopt niet met de plaatsing")
            if not merken:
                merken.append(f"zekerheid {g.get('zeker', 'onbekend')}")
            merk = " (" + ", ".join(merken) + ")"
            woord = ("verkocht" if g.get("soort") == "verkocht"
                     else "te koop aangeboden")
            nieuw += voeg_toe(pand, g["datum"], g.get("soort") or "te koop",
                              f"{woord}{bedrag}{merk}",
                              "model: " + str(g.get("bron", ""))[:90])
    return nieuw


def verkooptijd_bovengrens(geschiedenis):
    """
    Hoe lang een pand maximaal te koop stond, uit twee eigen waarnemingen.

    De exacte verkoopdatum kennen we niet: Funda publiceert die niet en de
    "sinds zoveel weken" op de site loopt gelijk met de advertentie en niet met
    de verkoop. Maar twee eigen waarnemingen geven wel een harde bovengrens:
    zagen we een pand op 11 september te koop en is het op 6 oktober verkocht,
    dan stond het hoogstens 25 dagen te koop.

    Dat is geen schatting maar een feit, en het is de maat die we de hele week
    misten. De werkelijke verkooptijd is korter of gelijk; nooit langer.
    """
    rijen = []
    for pand in geschiedenis.values():
        if not isinstance(pand, dict):
            continue
        gebeurtenissen = sorted((pand.get("gebeurtenissen") or []),
                                key=lambda g: g.get("datum") or "")
        tekoop = [g["datum"] for g in gebeurtenissen
                  if g.get("soort") == "te koop" and g.get("datum")]
        verkocht = [g for g in gebeurtenissen
                    if g.get("soort") in ("verkocht", "in onderhandeling")
                    and g.get("datum")]
        if not (tekoop and verkocht):
            continue
        laatste = verkocht[-1]
        # De eerste keer dat we het pand te koop zagen vóór deze verkoop.
        eerder = [d for d in tekoop if d <= laatste["datum"]]
        if not eerder:
            continue
        dagen = _dagen_tussen(eerder[0], laatste["datum"])
        if dagen is None or dagen < 0 or dagen > 1500:
            continue
        rijen.append({"adres": pand.get("adres"),
                      "eerst_gezien": eerder[0],
                      "verkocht_gezien": laatste["datum"],
                      "soort": laatste.get("soort"),
                      "hoogstens_dagen": dagen})
    rijen.sort(key=lambda r: r["verkocht_gezien"], reverse=True)
    uit = {"aantal": len(rijen), "panden": rijen[:20]}
    if rijen:
        waarden = sorted(r["hoogstens_dagen"] for r in rijen)
        uit["mediaan_hoogstens_dagen"] = waarden[len(waarden) // 2]
    # Onder bod apart, want dat is het moment dat een koper zich vastlegt en
    # dus de scherpste maat voor hoe snel de markt loopt.
    bod = sorted(r["hoogstens_dagen"] for r in rijen
                 if r.get("soort") == "in onderhandeling")
    if bod:
        uit["aantal_in_onderhandeling"] = len(bod)
        uit["mediaan_tot_onderhandeling"] = bod[len(bod) // 2]
    return uit


def _dagen_tussen(van, tot):
    try:
        return (dt.date.fromisoformat(tot[:10])
                - dt.date.fromisoformat(van[:10])).days
    except Exception:
        return None


# Onder dit aantal paren publiceren we geen mediaan. Vijf waarnemingen leveren
# wel een getal op, maar niet een getal waar een besluit op mag rusten, en in de
# brief is het verschil tussen die twee niet te zien.
MIN_PAREN = 10


def verkoopdatum_bekend(g):
    """
    Is de datum van deze verkocht-gebeurtenis een echte verkoopdatum?

    Bij 505 van de verkocht-gebeurtenissen is dat niet zo. Die komen uit de
    geplakte Funda-lijst, die alleen meldt DAT een pand verkocht is en niet
    wanneer. De datum is dan de dag waarop wij de lijst plakten, en de tekst
    zegt dat ook: "verkoopdatum onbekend; uit een geplakte lijst".

    Dat die datum toch als verkoopdatum werd gebruikt, leverde een mediane
    bezitsduur van 0,8 jaar op. Dat is geen bezitsduur maar de tijd tussen een
    oudere echte verkoop en de dag dat wij de lijst plakten: 505 gebeurtenissen
    dragen alle dezelfde datum 2026-09-28. Met alleen echte verkoopdatums komen
    er 15 paren uit met een mediaan van 3,3 jaar.
    """
    # De bron "aanbod" betekent: deze datum is onze kijkdag. Staat het adres in
    # verkoopdatums.txt, dan draagt de gebeurtenis de echte datum en de echte
    # bron, en komt hij hier dus wel door. Zie bekende_verkoopdatums().
    if g.get("bron") == "aanbod":
        return False
    # Drie formuleringen, alle drie "wij weten de verkoopdatum niet". De eerste
    # is de oude tekst, de tweede de huidige zonder venster, de derde met
    # venster. De bron "aanbod" vangt ze vandaag alle drie al af; dit staat er
    # zodat een gebeurtenis met een andere bron maar dezelfde tekst niet alsnog
    # als echte verkoopdatum wordt meegerekend.
    tekst = g.get("tekst") or ""
    return not any(w in tekst for w in ("verkoopdatum onbekend",
                                        "niet de verkoopdatum",
                                        "verkocht tussen"))


def _bij_benadering(datum):
    """
    Een datum op 1 januari is in deze reeks een jaar bij benadering.

    Zo staan ze in de bronnen die we met de hand hebben nagezocht: bekend is
    het jaar, niet de dag. Dat mag meetellen, maar dan wel met de kanttekening
    dat er een jaar speling in zit.
    """
    return (datum or "")[4:] == "-01-01"


def doorlooptijden(geschiedenis):
    """
    Wat de reeks per pand oplevert zodra er meer dan een gebeurtenis in staat.

    Drie dingen die nergens op te zoeken zijn: hoe lang een pand te koop stond,
    hoeveel jaar er tussen twee verkopen zat, en hoe de prijs van datzelfde pand
    zich heeft ontwikkeld.

    De bezitsduur en de prijsgroei rusten op twee verkopen van hetzelfde pand,
    en daarvoor zijn echte verkoopdatums nodig. Zie verkoopdatum_bekend().
    De verkooptijd is anders: die loopt van onze eigen eerste waarneming "te
    koop" tot de dag dat het pand als verkocht in beeld kwam, en is daarmee een
    bovengrens. Dat staat zo in het gezondheidsrapport en blijft zo.
    """
    verkoop_duur, bezit_duur, prijsgroei = [], [], []
    bezit_benadering = []
    for pand in geschiedenis.values():
        tekoop = sorted(g["datum"] for g in pand["gebeurtenissen"]
                        if g["soort"] == "te koop")
        verkocht = sorted((g for g in pand["gebeurtenissen"]
                           if g["soort"] == "verkocht"),
                          key=lambda g: g["datum"])
        for v in verkocht:
            eerder = [t for t in tekoop if t < v["datum"]]
            if eerder:
                try:
                    dagen = (dt.date.fromisoformat(v["datum"])
                             - dt.date.fromisoformat(eerder[-1])).days
                except ValueError:
                    continue
                if 0 < dagen < 1500:
                    verkoop_duur.append(dagen)
        # Alleen verkopen met een echte verkoopdatum. Een datum uit de geplakte
        # lijst is de dag dat wij plakten en niet de dag van de verkoop.
        met_datum = [v for v in verkocht if verkoopdatum_bekend(v)]
        datums = [v["datum"] for v in met_datum]
        for eerst, later in zip(datums, datums[1:]):
            try:
                jaren = (dt.date.fromisoformat(later)
                         - dt.date.fromisoformat(eerst)).days / 365.25
            except ValueError:
                continue
            if 0.2 < jaren < 60:
                bezit_duur.append(round(jaren, 1))
                if _bij_benadering(eerst) or _bij_benadering(later):
                    bezit_benadering.append(round(jaren, 1))
        bedragen = []
        for v in met_datum:
            m = re.search(r"€([\d.]+)", v["tekst"])
            if m:
                try:
                    bedragen.append((v["datum"],
                                     int(m.group(1).replace(".", ""))))
                except ValueError:
                    continue
        for (d1, p1), (d2, p2) in zip(bedragen, bedragen[1:]):
            try:
                jaren = (dt.date.fromisoformat(d2)
                         - dt.date.fromisoformat(d1)).days / 365.25
            except ValueError:
                continue
            if jaren > 0.5 and p1:
                prijsgroei.append({"adres": pand.get("adres"),
                                   "van": d1, "tot": d2,
                                   "per_jaar": round(
                                       ((p2 / p1) ** (1 / jaren) - 1) * 100, 1)})
    uit = {"verkooptijd_aantal": len(verkoop_duur),
           "bezitsduur_aantal": len(bezit_duur),
           "bezitsduur_bij_benadering": len(bezit_benadering),
           "prijsgroei_aantal": len(prijsgroei),
           "minimum_paren": MIN_PAREN}
    if verkoop_duur:
        uit["verkooptijd_mediaan_dagen"] = int(st.median(verkoop_duur))
    # Een mediaan pas vanaf MIN_PAREN paren. Daaronder wel het aantal melden,
    # want dat groeit met elke ronde verkoopdatums, maar geen getal dat in de
    # brief kan belanden als was het een marktcijfer.
    if len(bezit_duur) >= MIN_PAREN:
        uit["bezitsduur_mediaan_jaar"] = st.median(bezit_duur)
    if len(prijsgroei) >= MIN_PAREN:
        uit["prijsgroei_mediaan_pct"] = round(
            st.median([p["per_jaar"] for p in prijsgroei]), 1)
    if prijsgroei:
        uit["voorbeelden"] = sorted(prijsgroei,
                                    key=lambda p: p["tot"], reverse=True)[:5]
    return uit


def vergund_en_verkocht(geschiedenis):
    """
    Panden met een besluit over splitsen of verkameren die inmiddels verkocht
    zijn.

    Dit is het patroon waar de brief van 1 oktober toevallig op stuitte: wie
    zo'n vergunning krijgt, verkoopt het pand vervolgens door. Toevallig
    opmerken is geen methode, dus hier wordt het geteld.

    Let op de formulering: "en inmiddels verkocht", niet "daarna verkocht". Van
    de geplakte verkopen kennen we de datum niet, dus de volgorde is niet vast
    te stellen. Dat verschil is het verschil tussen een waarneming en een
    verhaal.
    """
    details = _verkocht_details()
    uit = []
    for pand in geschiedenis.values():
        soorten = {g["soort"] for g in pand["gebeurtenissen"]}
        if "verkocht" not in soorten:
            continue
        besluiten = [g for g in pand["gebeurtenissen"]
                     if g["soort"] == "bekendmaking"
                     and "besluit" in (g.get("tekst") or "").lower()
                     and any(w in (g.get("tekst") or "").lower()
                             for w in ("splits", "verkamer", "appartement",
                                       "omzett", "woningvorming"))]
        if not besluiten:
            continue
        verkoop = [g for g in pand["gebeurtenissen"] if g["soort"] == "verkocht"]
        uit.append({
            "adres": pand.get("adres"),
            "besluit": besluiten[-1]["tekst"][:120],
            "besluit_datum": besluiten[-1]["datum"],
            "verkoop": verkoop[-1]["tekst"][:80] if verkoop else "",
            # Via zoek_in, want verkocht_details.json is door een andere
            # module gesleuteld en die spelde "Mariënburg" anders dan deze.
            "makelaar": (_psl.zoek_in("verkocht_details.json", details,
                                      pand.get("adres") or "")[1] or {}
                         ).get("makelaar"),
        })
    # Wie keert er terug? Een makelaar die vaker opduikt bij vergunde en daarna
    # verkochte panden, is de partij om te bellen. Eigendom kunnen we niet zien,
    # dit wel.
    tellen = {}
    for p in uit:
        if p.get("makelaar"):
            tellen[p["makelaar"]] = tellen.get(p["makelaar"], 0) + 1
    for p in uit:
        p["makelaar_aantal"] = tellen.get(p.get("makelaar"), 0)
    return sorted(uit, key=lambda x: x["besluit_datum"], reverse=True)


def buurtbeeld(geschiedenis, cache=None, vanaf=2012):
    """
    Per buurt en per jaar: hoeveel aanvragen om te splitsen of te verkameren, en
    hoe ze afliepen.

    Dit is de stroom in plaats van de voorraad. De buurtcijfers van het CBS
    veranderen een keer per jaar; dit verandert elke week, en het zegt iets wat
    je nergens anders ziet: of de gemeente in die buurt meewerkt.

    Wat het niet is: een volledig beeld. We zien alleen wat gepubliceerd is en
    wat onze zoekwoorden vangen. Een laag aantal bewijst dus niets.
    """
    cache = cache if cache is not None else lees("straat_buurt_cache.json", {})
    per_buurt = {}
    for sl, pand in geschiedenis.items():
        buurt = buurt_van_pand(pand, cache)
        if not buurt:
            continue
        b = per_buurt.setdefault(buurt, {"jaren": {}, "doorlooptijden": [],
                                         "na_verkoop": 0})
        aanvraag_op = None
        verkocht_op = None
        for g in sorted(pand["gebeurtenissen"], key=lambda x: x["datum"]):
            datum, tekst = g["datum"][:10], g["tekst"]
            if g["soort"] == "verkocht":
                verkocht_op = datum
                continue
            if g["soort"] != "bekendmaking" or not _INGREEP.search(tekst):
                continue
            jaar = datum[:4]
            if not jaar.isdigit() or int(jaar) < vanaf:
                continue
            tel = b["jaren"].setdefault(jaar, {"aanvragen": 0, "verleend": 0,
                                               "geweigerd": 0, "gestopt": 0})
            if _GESTOPT.search(tekst):
                tel["gestopt"] += 1
            elif _GEWEIGERD.search(tekst):
                tel["geweigerd"] += 1
            elif _VERLEEND.search(tekst):
                tel["verleend"] += 1
                if aanvraag_op:
                    dagen = (dt.date.fromisoformat(datum)
                             - dt.date.fromisoformat(aanvraag_op)).days
                    if 0 <= dagen <= 730:
                        b["doorlooptijden"].append(dagen)
                    aanvraag_op = None
            elif _AANVRAAG.search(tekst):
                tel["aanvragen"] += 1
                aanvraag_op = datum
            # Gekocht en daarna een ingreep aangevraagd: de route die we volgen
            if verkocht_op and datum > verkocht_op:
                b["na_verkoop"] += 1
                verkocht_op = None
    return per_buurt


def buurtbeeld_tekst(per_buurt, buurt, jaren=4):
    """De regels voor een buurt, met de laatste jaren apart en de rest opgeteld."""
    b = per_buurt.get(buurt)
    if not b or not b["jaren"]:
        return []
    alle = sorted(b["jaren"])
    recent_j = alle[-jaren:]
    ouder = [j for j in alle if j not in recent_j]
    regels = []
    for j in recent_j:
        t = b["jaren"][j]
        delen = [f"{t['aanvragen']} aanvragen"] if t["aanvragen"] else []
        for sleutel, woord in (("verleend", "verleend"), ("geweigerd", "geweigerd"),
                               ("gestopt", "buiten behandeling of ingetrokken")):
            if t[sleutel]:
                delen.append(f"{t[sleutel]} {woord}")
        if delen:
            regels.append(f"{j}: " + ", ".join(delen))
    if ouder:
        som = sum(b["jaren"][j]["aanvragen"] for j in ouder)
        regels.append(f"{ouder[0]} tot en met {ouder[-1]}: {som} aanvragen")
    uit = [f"splitsen en verkameren in {buurt}, uit de gepubliceerde "
           f"bekendmakingen: " + "; ".join(regels)]
    if b["doorlooptijden"]:
        mediaan = int(st.median(b["doorlooptijden"]))
        uit.append(f"doorlooptijd van aanvraag tot verleende vergunning in "
                   f"{buurt}: mediaan {mediaan} dagen over "
                   f"{len(b['doorlooptijden'])} gevallen")
    if b["na_verkoop"]:
        uit.append(f"{b['na_verkoop']} keer werd er in {buurt} na een verkoop een "
                   f"ingreep aangevraagd op hetzelfde adres")
    uit.append("deze tellingen zien alleen wat gepubliceerd is; een laag aantal "
               "bewijst niet dat er weinig gebeurt")
    return uit


def recent(geschiedenis, dagen=7):
    """De panden met een gebeurtenis in de afgelopen dagen, met hun hele verleden."""
    grens = (dt.date.today() - dt.timedelta(days=dagen)).isoformat()
    uit = []
    for sl, pand in geschiedenis.items():
        vers = [g for g in pand["gebeurtenissen"] if g["datum"] >= grens
                and g["soort"] in ("verkocht", "bekendmaking", "bag", "energielabel",
                                   "prijswijziging")]
        if vers and len(pand["gebeurtenissen"]) > 1:
            uit.append((pand, vers))
    return uit


def render(geschiedenis, dagen=7):
    paren = recent(geschiedenis, dagen)
    if not paren:
        return []
    r = ["# Wat er met eerdere panden gebeurde", "",
         "_Per pand de gebeurtenissen op volgorde. Vastgelegd op het BAG-pand, "
         "dus een splitsing en de nieuwe huisnummers horen bij dezelfde "
         "geschiedenis._", ""]
    # Op aantal gebeurtenissen sorteren levert complexen bovenaan, en die
    # hebben er honderden. Daarom tellen labelregels niet mee in die volgorde:
    # een pand met twintig vergunningen is interessanter dan een flat met
    # honderdtwintig labels.
    def gewicht(paar):
        return -sum(1 for g in paar[0]["gebeurtenissen"]
                    if g["soort"] != "energielabel")

    for pand, vers in sorted(paren, key=gewicht)[:8]:
        r.append(f"## {pand['adres']}")
        labels = [g for g in pand["gebeurtenissen"] if g["soort"] == "energielabel"]
        rest = [g for g in pand["gebeurtenissen"] if g["soort"] != "energielabel"]
        for g in rest:
            # "NIEUW IN ONS DOSSIER" EN NIET "NIEUW". Deze markering betekent
            # dat de gebeurtenis in deze ronde is vastgelegd, niet dat ze
            # vandaag is gebeurd. Als "**nieuw**" las de briefschrijver het als
            # nieuws van vandaag, en opende de brief van 13 oktober met vijf
            # verkopen die al drie tot zes weken oud waren.
            merk = " **nieuw in ons dossier**" if g in vers else ""
            r.append(f"- {g['datum']}: {g['tekst']} ({g['bron']}){merk}")
        # Labels samenvatten in plaats van uitschrijven. Een flat met
        # honderdtwintig woningen leverde honderdtwintig regels op en maakte
        # het dossier onleesbaar; de verdeling zegt hetzelfde in een regel.
        if labels:
            verdeling = {}
            for g in labels:
                m = re.search(r"is (?:nu )?([A-G]\+*)", g["tekst"])
                if m:
                    verdeling[m.group(1)] = verdeling.get(m.group(1), 0) + 1
            laatste = max(g["datum"] for g in labels)
            samen = ", ".join(f"{k}: {v}" for k, v in
                              sorted(verdeling.items(), key=lambda p: -p[1])[:6])
            r.append(f"- {laatste}: energielabels van {len(labels)} woningen in "
                     f"dit pand ({samen or 'niet uit te lezen'}) (EP-Online)")
        r.append("")
    return r


def proef():
    """
    De vier meldvormen nameten op echte objectvormen, zonder BAG-sleutel.

    Deze kwamen uit een lus die alleen met een sleutel en een run van drie uur
    te bekijken was, dus zijn ze met de hand nagekeken en nooit opnieuw. De
    objectvorm hieronder is die van bag_eenheden_in_pand(): adres,
    oppervlakte, gebruiksdoelen en status.
    """
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    def obj(adres, opp, doel="woonfunctie"):
        return {"adres": adres, "oppervlakte": opp,
                "gebruiksdoelen": [doel] if doel else [],
                "status": "Verblijfsobject in gebruik"}

    # De zeven objecten van Hatertseweg 338, met het object van 20 m2 als
    # niet-woning. Welk object dat in de BAG werkelijk is, weten we hier niet;
    # dit meet alleen of de telling en de tekst doen wat ze moeten doen.
    hatert = [obj("Hatertseweg 338", 20, "overige gebruiksfunctie"),
              obj("Hatertseweg 338", 147), obj("Hatertseweg 338A", 46),
              obj("Hatertseweg 338B", 24), obj("Hatertseweg 338C", 19),
              obj("Hatertseweg 338D", 23), obj("Hatertseweg 338E", 19)]

    # 1. Een pand dat voor het eerst wordt opgehaald meldt niets, maar vult
    #    wel beide tellingen.
    nu, nu_woon, melding = tel_en_meld(hatert, None, None)
    check("eerste keer geen melding", melding, None)
    check("eerste keer eenheden", len(nu), 7)
    check("eerste keer woningen", len(nu_woon), 6)

    # 2. Niets veranderd: geen melding. Dit is de inhaalslag van de 1.263
    #    panden die al eenheden hebben; de lus schrijft nu_woon dan weg zonder
    #    iets te melden.
    nu2, nu_woon2, melding = tel_en_meld(hatert, [list(x) for x in nu], None)
    check("ongewijzigd geen melding", melding, None)
    check("ongewijzigd wel een woningtelling", len(nu_woon2), 6)

    # 3. Gewijzigd en nog geen woningtelling van vroeger: geen "was".
    _n, _w, melding = tel_en_meld(hatert, [["Hatertseweg 338", 167]], None)
    check("zonder vroeger geen was", "was" in (melding or ""), False)
    check("zonder vroeger telt zes",
          melding, "de BAG telt nu 6 woningen in dit pand: 147, 46, 24, 19, "
                   "23, 19 m2; daarnaast 1 ander object met een eigen adres")

    # 4. Gewijzigd met een woningtelling van vroeger: wel "was".
    _n, _w, melding = tel_en_meld(hatert, [["Hatertseweg 338", 167]],
                                  [["Hatertseweg 338", 167]])
    check("met vroeger zegt was zes tegen een",
          melding, "de BAG telt nu 6 woningen in dit pand, was 1: 147, 46, "
                   "24, 19, 23, 19 m2; daarnaast 1 ander object met een "
                   "eigen adres")

    # 5. Even veel woningen, andere oppervlaktes.
    anders = [obj("Hatertseweg 338", 150)]
    _n, _w, melding = tel_en_meld(anders, [["Hatertseweg 338", 147]],
                                  [["Hatertseweg 338", 147]])
    check("alleen maten", melding,
          "de oppervlaktes in de BAG zijn gewijzigd: 150 m2")

    # 6. Alleen een niet-woning erbij: dat is geen splitsing en mag niet als
    #    woningtelling klinken.
    met_berging = [obj("Hatertseweg 338", 147),
                   obj("Hatertseweg 338F", 8, "overige gebruiksfunctie")]
    _n, _w, melding = tel_en_meld(met_berging, [["Hatertseweg 338", 147]],
                                  [["Hatertseweg 338", 147]])
    check("alleen niet-woning", melding,
          "de BAG kent nu 1 object zonder woonfunctie in dit pand; het aantal "
          "woningen bleef 1")

    # 7. Het gebruiksdoel als string in plaats van als lijst.
    check("doel als string",
          _doelen({"gebruiksdoelen": "woonfunctie,bijeenkomstfunctie"}),
          ["woonfunctie", "bijeenkomstfunctie"])
    check("doel enkelvoud veld",
          _doelen({"gebruiksdoel": ["woonfunctie"]}), ["woonfunctie"])
    check("doel leeg", _doelen({}), [])
    als_string = [{"adres": "Hatertseweg 338", "oppervlakte": 147,
                   "gebruiksdoelen": "woonfunctie"}]
    _n, w, _m = tel_en_meld(als_string, None, None)
    check("string telt als woning", len(w), 1)

    # 8. Geen enkele woning: geen kale ": m2" in de tekst.
    geen = [obj("Hatertseweg 338F", 8, "overige gebruiksfunctie")]
    _n, w, melding = tel_en_meld(geen, [["Hatertseweg 338", 147]], None)
    check("nul woningen telling", len(w), 0)
    check("nul woningen tekst", melding,
          "de BAG telt nu 0 woningen in dit pand; daarnaast 1 ander object "
          "met een eigen adres")

    # 9. De tekst van 3 en 4 moet door de lezer van splitsing_voltooid heen
    #    komen, want die twee bestanden praten hier met elkaar.
    try:
        from splitsing_voltooid import _aantallen
        _n, _w, m4 = tel_en_meld(hatert, [["Hatertseweg 338", 167]],
                                 [["Hatertseweg 338", 167]])
        check("splitsing_voltooid leest de melding", _aantallen(m4), (1, 6))
        _n, _w, m3 = tel_en_meld(hatert, [["Hatertseweg 338", 167]], None)
        check("zonder was leest hij niets", _aantallen(m3), None)
    except ImportError:
        fouten.append("splitsing_voltooid niet te importeren")

    # 10. uit_archief() MAG OP DE ECHTE DATA NIETS AANMAKEN.
    #
    # Dit is de controle die de 56 dubbele records had gevangen. Die stap nam
    # de sleutel uit het bekendmakingenarchief over, lidwoord en al, en keek
    # bij het aanmaken maar naar één vorm. Elk pand dat al onder de schone
    # sleutel stond kreeg zo een tweede record, en de helft van de
    # geschiedenis belandde in de helft die niemand opzoekt.
    #
    # Op een bestand dat al bij is, hoort deze stap niets toe te voegen: alle
    # adressen uit het archief staan er dan in en alle bekendmakingen zijn
    # gekoppeld. Voegt hij wel iets toe, dan is er of een nieuw adres in het
    # archief (dan is dit geen fout maar nieuws, en dan hoort dit getal in de
    # run te staan en niet in de proef), of er is een sleutel uit elkaar
    # gelopen. Daarom geen harde nul maar een grens: een paar nieuwe adressen
    # is normaal, tientallen betekent dat het sleutelen stuk is.
    #
    # Het kost geen aanroep: het archief en de geschiedenis staan in de repo.
    try:
        from pandlezer import laad as _laad
        g = _laad("pandgeschiedenis.json")
        if g:
            voor = len(g)
            uit_archief(g)
            erbij = len(g) - voor
            if erbij > 10:
                fouten.append(
                    f"uit_archief() maakt {erbij} nieuwe records aan op de "
                    f"bestaande geschiedenis; dat zijn er te veel om nieuwe "
                    f"adressen te zijn en wijst op sleutels die uiteenlopen")
            else:
                print(f"  uit_archief() op de echte data: {erbij} nieuwe "
                      f"records", file=sys.stderr)
            # En wat hij aanmaakt, moet onder de canonieke sleutel staan.
            scheef = [k for k, p in g.items()
                      if isinstance(p, dict) and p.get("adres")
                      and k != _psl.sleutel(p["adres"])]
            if scheef:
                fouten.append(
                    f"{len(scheef)} records staan niet onder hun canonieke "
                    f"sleutel, bijvoorbeeld {scheef[0]!r}")
    except Exception as e:
        fouten.append(f"uit_archief() niet na te meten: {type(e).__name__} {e}")

    # HET VENSTER BIJ EEN VERKOOP UIT EEN GEPLAKTE LIJST.
    #
    # De datum van zo'n gebeurtenis is de dag dat wij het zagen. Stond er
    # alleen "verkoopdatum onbekend" bij, dan las de briefschrijver de datum
    # als de dag van de verkoop: de brief van 13 oktober opende met vijf
    # verkopen die al drie tot zes weken oud waren, en noemde dat een signaal.
    # De ondergrens van het venster is hard: de vorige keer dat wij het pand
    # zagen stond het nog niet als verkocht.
    pad = "/tmp/pandgeschiedenis_proef_verkopen.txt"
    eerder = globals().get("VERKOPEN")
    try:
        with open(pad, "w", encoding="utf-8") as f:
            f.write("Teststraat 1 | Nijmegen | 419000 | te koop | 2026-09-11 "
                    "| funda-mail | 77 | 6521EC\n")
            f.write("Teststraat 1 | Nijmegen | 419000 | onder bod | 2026-09-28 "
                    "| funda-verkocht-plak | 77 | 6521EC\n")
            f.write("Teststraat 1 | Nijmegen | 419000 | verkocht | 2026-10-13 "
                    "| funda-verkocht-plak | 77 | 6521EC\n")
            f.write("Kortstraat 2 | Nijmegen | 300000 | verkocht | 2026-10-13 "
                    "| funda-verkocht-plak | 60 | 6511AA\n")
        globals()["VERKOPEN"] = pad
        g = {}
        uit_verkopen(g)
        for adres, moet, mag_niet in (
                ("Teststraat 1", "verkocht tussen 2026-09-28 en 2026-10-13",
                 None),
                ("Kortstraat 2", "verkoopdatum onbekend", None)):
            sl = _psl.sleutel(adres)
            verkopen = [x for x in (g.get(sl) or {}).get("gebeurtenissen", [])
                        if x["soort"] == "verkocht"]
            if not verkopen:
                fouten.append(f"{adres}: geen verkocht-gebeurtenis gemaakt")
                continue
            if len(verkopen) != 1:
                fouten.append(f"{adres}: {len(verkopen)} verkoopregels op "
                              f"dezelfde dag, verwacht 1")
            tekst = verkopen[-1]["tekst"]
            if moet not in tekst:
                fouten.append(f"{adres}: de tekst noemt {moet!r} niet: "
                              f"{tekst!r}")
            if "dag dat wij het" not in tekst:
                fouten.append(f"{adres}: de tekst zegt niet dat de datum onze "
                              f"waarneming is: {tekst!r}")
        # EEN VERBETERDE TEKST MAG DE OUDE VERVANGEN EN NIET VERDUBBELEN.
        #
        # Dit is het geval dat werkelijk optreedt, en het is niet hetzelfde als
        # tweemaal draaien: bij gelijke tekst ontdubbelt voeg_toe toch al. Het
        # gaat mis zodra de formulering verandert. Op 13 oktober stonden er
        # dertien verkopen in het dossier met de oude tekst "verkoopdatum
        # onbekend; uit een geplakte lijst", en de nieuwe ronde schrijft het
        # venster. Zonder eenmalig_per_dag krijgt elk van die panden twee
        # verkoopregels met dezelfde datum, en leest het dossier als twee
        # verkopen van hetzelfde pand op een dag.
        oud = {_psl.sleutel("Teststraat 1"): {
            "adres": "Teststraat 1", "pand_id": None,
            "gebeurtenissen": [{
                "datum": "2026-10-13", "soort": "verkocht",
                "tekst": "verkocht, laatste vraagprijs €419.000, 77 m2 "
                         "(verkoopdatum onbekend; uit een geplakte lijst)",
                "bron": "aanbod"}]}}
        uit_verkopen(oud)
        verkopen = [x for x in oud[_psl.sleutel("Teststraat 1")]["gebeurtenissen"]
                    if x["soort"] == "verkocht"]
        if len(verkopen) != 1:
            fouten.append(f"een verbeterde tekst komt naast de oude te staan: "
                          f"{len(verkopen)} verkoopregels op dezelfde dag, "
                          f"verwacht 1")
        elif "verkocht tussen" not in verkopen[0]["tekst"]:
            fouten.append(f"de oude tekst is niet vervangen: "
                          f"{verkopen[0]['tekst']!r}")
    except Exception as e:
        fouten.append(f"het venster niet na te meten: {type(e).__name__} {e}")
    finally:
        if eerder is not None:
            globals()["VERKOPEN"] = eerder
        try:
            os.remove(pad)
        except OSError:
            pass

    # EN DE SCHRIJFINSTRUCTIE MOET HET VERBOD DRAGEN. Het blok mag het venster
    # nog zo netjes noemen; zolang brief_verhalend.py niet verbiedt om het
    # AANTAL gebeurtenissen van een dag als signaal te gebruiken, kan de brief
    # er weer mee openen. Dat deed hij, binnen de letter van de oude regel.
    try:
        with open("brief_verhalend.py", encoding="utf-8") as f:
            instructie = f.read()
    except Exception as e:
        fouten.append(f"brief_verhalend.py niet te lezen: {str(e)[:40]}")
        instructie = ""
    for nodig in ("ONZE BOEKHOUDING IS GEEN NIEUWS",
                  "nooit een signaal", "nieuw in ons dossier"):
        if instructie and nodig not in instructie:
            fouten.append(f"brief_verhalend.py noemt {nodig!r} niet; dan mag "
                          f"de brief het aantal van een dag weer als signaal "
                          f"gebruiken")

    # EEN DATUM DIE WIJ WETEN GAAT VOOR EEN VENSTER DAT WIJ AFLEIDEN.
    #
    # Groesbeekseweg 118 stond bij ons op 28 september, want toen zagen wij
    # hem in een geplakte lijst. Funda geeft 21 september. Zeven dagen, en het
    # venster zou dat verschil verbergen achter "verkocht tussen ... en ...".
    import tempfile as _tf
    import os as _os
    with _tf.TemporaryDirectory() as _m:
        _p = _os.path.join(_m, "vd.txt")
        with open(_p, "w", encoding="utf-8") as _f:
            _f.write("# commentaar wordt overgeslagen\n"
                     "\n"
                     "Groesbeekseweg 118 | 2026-09-21 | Funda\n"
                     "Zonder Datum 1 | | Funda\n"
                     "Rommel 2 | binnenkort | Funda\n"
                     "Kale Regel 3 | 2026-01-02\n")
        _d = bekende_verkoopdatums(_p)
        if sorted(_d) != ["groesbeekseweg 118", "kale regel 3"]:
            fouten.append(f"de bekende verkoopdatums zijn verkeerd gelezen: "
                          f"{sorted(_d)}")
        if "zonder datum 1" in _d or "rommel 2" in _d:
            fouten.append("een regel zonder bruikbare datum wordt toch "
                          "ingelezen, en vervangt dan het venster door niets")
        if _d.get("groesbeekseweg 118", {}).get("bron") != "Funda":
            fouten.append("de bron bij een bekende verkoopdatum gaat "
                          "verloren; dan is over een jaar niet na te gaan "
                          "waarop hij rust")
    if bekende_verkoopdatums("bestaat-echt-niet.txt") != {}:
        fouten.append("een ontbrekend bestand met verkoopdatums geeft geen "
                      "lege uitkomst")

    # EN DE KIJKDAG VERVALT OOK ECHT. Een datum die alleen in de tekst staat is
    # geen datum die wij gebruiken: de gebeurtenis moet hem dragen, de oude
    # regel op onze kijkdag moet weg, en verkoopdatum_bekend() moet hem
    # meerekenen. Twee panden in deze proef: een met een bekende datum en een
    # zonder, zodat het venster niet stilletjes verdwijnt voor de rest.
    with _tf.TemporaryDirectory() as _m:
        _vk = _os.path.join(_m, "verkopen.txt")
        with open(_vk, "w", encoding="utf-8") as _f:
            _f.write("Proefstraat 1 | Nijmegen | 400000 | te koop | "
                     "2026-06-01 | model | 100\n"
                     "Proefstraat 1 | Nijmegen | 400000 | verkocht | "
                     "2026-09-28 | geplakte lijst | 100\n"
                     "Proefstraat 2 | Nijmegen | 300000 | te koop | "
                     "2026-06-01 | model | 80\n"
                     "Proefstraat 2 | Nijmegen | 300000 | verkocht | "
                     "2026-09-28 | geplakte lijst | 80\n")
        _vd = _os.path.join(_m, "vd.txt")
        with open(_vd, "w", encoding="utf-8") as _f:
            _f.write("Proefstraat 1 | 2026-09-21 | Funda\n")
        _oud_vk, _oud_vd = VERKOPEN, BEKENDE_VERKOOPDATUMS
        # De geschiedenis begint NIET leeg. In pandgeschiedenis.json staat de
        # verkoopregel op onze kijkdag er al, want die schreven wij voordat de
        # echte datum bekend was. Een proef die vanaf niets begint ziet dat
        # nooit: dan komt de nieuwe regel op 21 september en is er niets om op
        # te ruimen. Daarom zetten we de oude regel er eerst in, precies zoals
        # hij er vandaag staat.
        _g = {"proefstraat1": {
            "adres": "Proefstraat 1", "pand_id": None,
            "gebeurtenissen": [
                {"datum": "2026-09-28", "soort": "verkocht",
                 "tekst": "verkocht, laatste vraagprijs €400.000, 100 m2 "
                          "(verkoopdatum onbekend; 2026-09-28 is de dag dat "
                          "wij het in een geplakte lijst zagen)",
                 "bron": "aanbod"}]}}
        try:
            globals()["VERKOPEN"] = _vk
            globals()["BEKENDE_VERKOOPDATUMS"] = _vd
            # Twee rondes: de tweede mag niets verdubbelen.
            uit_verkopen(_g)
            uit_verkopen(_g)
        finally:
            globals()["VERKOPEN"] = _oud_vk
            globals()["BEKENDE_VERKOOPDATUMS"] = _oud_vd
        _met = [g for g in _g.get("proefstraat1", {}).get("gebeurtenissen", [])
                if g["soort"] == "verkocht"]
        _zonder = [g for g in _g.get("proefstraat2", {}).get("gebeurtenissen", [])
                   if g["soort"] == "verkocht"]
        if len(_met) != 1:
            fouten.append(f"een bekende verkoopdatum levert {len(_met)} "
                          f"verkoopregels op in plaats van 1; dan leest het "
                          f"dossier als twee verkopen")
        elif _met[0]["datum"] != "2026-09-21":
            fouten.append(f"de verkoopgebeurtenis staat op "
                          f"{_met[0]['datum']} en niet op de bekende datum "
                          f"2026-09-21; onze kijkdag vervalt dus niet")
        elif not verkoopdatum_bekend(_met[0]):
            fouten.append("een verkoop met een bekende datum wordt niet als "
                          "echte verkoopdatum meegerekend; dan blijft het "
                          "pand buiten de bezitsduur- en prijsgroeiparen")
        if len(_zonder) != 1 or _zonder[0]["datum"] != "2026-09-28":
            fouten.append(f"zonder bekende datum hoort de kijkdag te blijven "
                          f"staan, maar er staat {_zonder}")
        elif verkoopdatum_bekend(_zonder[0]):
            fouten.append("een verkoop zonder bekende datum wordt toch als "
                          "echte verkoopdatum meegerekend")

    # HET ADRES WORDT EEN OBJECT-ID. Echte records uit de voorraad van 14
    # oktober: Albardastraat 34 heeft een bestaand en een gevormd object,
    # Bachstraat 3 staat er drie keer in drie gemeenten.
    import tempfile
    with tempfile.TemporaryDirectory() as _d:
        _vp = os.path.join(_d, "v.json")
        with open(_vp, "w", encoding="utf-8") as _f:
            json.dump({"adressen": {
                "0268010000000735": {"adres": "Albardastraat 34",
                                     "status": "Verblijfsobject in gebruik",
                                     "pand": "0268100000018066"},
                "0241010000000134": {"adres": "Bachstraat 3",
                                     "status": "Verblijfsobject in gebruik",
                                     "pand": "0241100000012822"},
                "0268010000055748": {"adres": "Bachstraat 3",
                                     "status": "Verblijfsobject in gebruik",
                                     "pand": "0268100000001964"},
                "0944010000206628": {"adres": "Bachstraat 3",
                                     "status": "Verblijfsobject in gebruik",
                                     "pand": "0944100000202931"}},
                "pijplijn": {
                "0268010000112652": {"adres": "Albardastraat 34",
                                     "status": "Verblijfsobject gevormd",
                                     "pand": "0268100000018066"}}}, _f)
        _g = {"albardastraat34": {"adres": "Albardastraat 34", "pand_id": None,
                                  "gebeurtenissen": []},
              "bachstraat3": {"adres": "Bachstraat 3",
                              "pand_id": "0268100000001964",
                              "gebeurtenissen": []},
              "nergens1": {"adres": "Nergensstraat 1", "pand_id": None,
                           "gebeurtenissen": []}}
        _t = koppel_objecten(_g, _vp)
    check("het bestaande object wint van het gevormde",
          _g["albardastraat34"].get("vbo"), "0268010000000735")
    check("het gevormde object blijft zichtbaar",
          _g["albardastraat34"].get("vbo_gevormd"), ["0268010000112652"])
    check("een ontbrekend pand-id wordt aangevuld uit het object",
          _g["albardastraat34"].get("pand_id"), "0268100000018066")
    check("een naamgenoot in een andere gemeente telt niet mee",
          _g["bachstraat3"].get("vbo"), "0268010000055748")
    check("een adres buiten de voorraad krijgt geen geraden id",
          _g["nergens1"].get("vbo"), None)
    check("de telling klopt met wat er gebeurde",
          (_t.get("bestaand"), _t.get("bestaand_en_gevormd"),
           _t.get("niet_in_voorraad")), (1, 1, 1))

    # HET LABEL KOMT UIT DE VOORRAAD, EN ALLEEN WAT DIE NIET WEET GAAT NAAR
    # EP-ONLINE, OP OBJECT-ID. Een pand met drie objecten: A 1 kent de
    # voorraad met label, A 3 kent hij niet, en A 5 kreeg "geen label" van
    # de kapotte aanroep van 10 oktober. Alleen A 3 en A 5 horen gevraagd te
    # worden, en dan met het object-id uit de BAG.
    import marktprijzen_bag as _mb
    _bewaar = (_mb.bag_adres_uitgebreid, _mb.ep_energielabel,
               _mb.BAG_API_KEY, _mb.EP_API_KEY, globals()["PAUZE_TUSSEN"])
    _gevraagd = []

    def _nep_bag(straat, nr, letter, toev, plaats):
        return {"adresseerbaarObjectIdentificatie": f"02680100000{nr:0>5}",
                "postcode": "6500AA", "pand": "0268100000077777"}

    def _nep_ep(vbo, postcode, nr, letter, toev):
        _gevraagd.append(vbo)
        return {"label": "B", "registratiedatum": "2024-01-01"}

    with tempfile.TemporaryDirectory() as _d:
        _vp = os.path.join(_d, "v.json")
        with open(_vp, "w", encoding="utf-8") as _f:
            json.dump({"adressen": {
                "0268010000000001": {"adres": "Proefhof 1", "label": "C",
                                     "label_datum": "2023-05-05",
                                     "label_gezien": "2026-10-13",
                                     "pand": "0268100000077777"},
                "0268010000000005": {"adres": "Proefhof 5",
                                     "label_gezien": "2026-10-10",
                                     "pand": "0268100000077777"}}}, _f)
        _g = {"proefhof1": {"adres": "Proefhof 1",
                            "pand_id": "0268100000077777",
                            "bag_eenheden": [["Proefhof 1", 60],
                                             ["Proefhof 3", 60],
                                             ["Proefhof 5", 60]],
                            # Eerder verkeerd opgeschreven als D, op een dag
                            # na de registratie van het echte label C.
                            "labels": {"Proefhof 1": "D"},
                            "gebeurtenissen": [{
                                "datum": "2026-10-03", "soort": "energielabel",
                                "tekst": "energielabel van Proefhof 1 is nu D",
                                "bron": "EP-Online"}]}}
        try:
            _mb.bag_adres_uitgebreid, _mb.ep_energielabel = _nep_bag, _nep_ep
            _mb.BAG_API_KEY = _mb.EP_API_KEY = "proef"
            globals()["PAUZE_TUSSEN"] = 0
            bij_labels(_g, voorraad_pad=_vp)
        finally:
            (_mb.bag_adres_uitgebreid, _mb.ep_energielabel, _mb.BAG_API_KEY,
             _mb.EP_API_KEY, globals()["PAUZE_TUSSEN"]) = _bewaar
    _lab = _g["proefhof1"].get("labels") or {}
    check("het label uit de voorraad wordt gebruikt", _lab.get("Proefhof 1"),
          "C")
    _corr = [x for x in _g["proefhof1"]["gebeurtenissen"]
             if "Proefhof 1 is C" in (x.get("tekst") or "")
             or "Proefhof 1 is nu C" in (x.get("tekst") or "")]
    check("een correctie van onze fout heet geen wijziging aan het pand",
          bool(_corr) and "onze fout" in _corr[0]["tekst"], True)
    check("alleen wat de voorraad niet weet gaat naar EP-Online",
          len(_gevraagd), 2)
    check("EP-Online wordt op object-id gevraagd en niet op postcode",
          all(_gevraagd), True)

    # HET OBJECT-ID UIT HET BAG-ANTWOORD WORDT BEWAARD, alleen een Nijmeegs,
    # en wat de voorraad al gaf blijft staan.
    _a = {"adres": "Proefhof 9"}
    neem_object_over(_a, {"adresseerbaarObjectIdentificatie": "0268010000000009",
                          "panden": ["0268100000000009"]}, "2026-10-14")
    check("het object-id uit de BAG wordt bewaard", _a.get("vbo"),
          "0268010000000009")
    _b = {"adres": "Bachstraat 3"}
    neem_object_over(_b, {"adresseerbaarObjectIdentificatie":
                          "0241010000000134"}, "2026-10-14")
    check("een object uit een andere gemeente wordt niet bewaard",
          (_b.get("vbo"), _b.get("vbo_gevraagd")), (None, "2026-10-14"))
    _c = {"adres": "Proefhof 9", "vbo": "0268010000000001"}
    neem_object_over(_c, {"adresseerbaarObjectIdentificatie":
                          "0268010000000009"}, "2026-10-14")
    check("een object-id uit de voorraad wordt niet overschreven",
          _c.get("vbo"), "0268010000000001")

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    ap.add_argument("--volledig", action="store_true",
                    help="ook de BAG en de energielabels bijwerken")
    ap.add_argument("--proef", action="store_true",
                    help="De meldvormen nameten zonder iets op te halen.")
    args = ap.parse_args()
    if args.proef:
        return proef()
    wis("geschiedenis")

    try:
        from pandlezer import laad
        geschiedenis = laad(PAD)
    except Exception:
        geschiedenis = lees(PAD, {})
    n_v = uit_verkopen(geschiedenis)
    n_m = uit_model(geschiedenis)
    n_a = uit_archief(geschiedenis)
    n_k = uit_kamerverhuur(geschiedenis)
    # Voor de BAG-ronde: wat de voorraad al weet, hoeft niet gevraagd.
    koppel_objecten(geschiedenis)
    n_b = n_l = 0
    if not args.volledig:
        # Nieuwe panden meteen ophalen, ook bij een korte run. Dat zijn de
        # aanbiedingen die vandaag binnenkwamen: een handvol, en zonder dit
        # staan ze tot zondag zonder oppervlakte, bouwjaar en label in de
        # dossiers. Het hele bestand nakijken op veranderingen blijft wel aan
        # de weekronde voorbehouden.
        n_b, ronde = bij_bag(geschiedenis, alleen_gevolgd=False,
                             alleen_nieuwe=True)
        if ronde:
            n_l = bij_labels(geschiedenis, ronde)
    if args.volledig:
        # alleen_gevolgd=False: bij een volledige ronde doen ook de panden mee
        # waarvan we alleen aanbod kennen en geen bekendmaking. Zonder dit
        # werden die overgeslagen voordat ze geteld werden, en bleef het aantal
        # "nog nooit nagekeken" eeuwig op hetzelfde getal staan.
        n_b, ronde = bij_bag(geschiedenis, alleen_gevolgd=False)
        n_l = bij_labels(geschiedenis, ronde)
    bewaar(geschiedenis)
    # Het patroon vergund-en-verkocht apart wegschrijven, zodat de brief het
    # kan noemen zonder het zelf uit de lijsten te hoeven vissen.
    # Wat de reeks per pand oplevert: verkooptijd, bezitsduur, prijsgroei.
    try:
        with open("doorlooptijden.json", "w", encoding="utf-8") as f:
            json.dump(doorlooptijden(geschiedenis), f, ensure_ascii=False,
                      indent=1)
    except Exception:
        pass
    # De bovengrens op de verkooptijd, uit onze eigen waarnemingen.
    try:
        with open("verkooptijd.json", "w", encoding="utf-8") as f:
            json.dump(verkooptijd_bovengrens(geschiedenis), f,
                      ensure_ascii=False, indent=1)
    except Exception:
        pass

    patroon = vergund_en_verkocht(geschiedenis)
    try:
        with open("vergund_verkocht.json", "w", encoding="utf-8") as f:
            json.dump({"datum": dt.date.today().isoformat(),
                       "panden": patroon}, f, ensure_ascii=False, indent=1)
        if patroon:
            print(f"Vergund en inmiddels verkocht: {len(patroon)} panden",
                  file=sys.stderr)
    except Exception:
        pass

    beeld = buurtbeeld(geschiedenis)
    with open(BUURTBEELD_PAD, "w", encoding="utf-8") as f:
        json.dump(beeld, f, ensure_ascii=False, indent=1, sort_keys=True)

    met_verhaal = sum(1 for p in geschiedenis.values()
                      if len(p["gebeurtenissen"]) > 1)
    print(f"Geschiedenis: {len(geschiedenis)} panden gevolgd, waarvan "
          f"{met_verhaal} met meer dan een gebeurtenis; nieuw: {n_v} uit het "
          f"aanbod, {n_a} bekendmakingen, {n_k} uit het kamerverhuurregister, "
          f"{n_b} BAG-wijzigingen, {n_l} labels erbij of gewijzigd",
          file=sys.stderr)
    if args.uit:
        regels = render(geschiedenis)
        if regels:
            os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
            with open(args.uit, "w", encoding="utf-8") as f:
                f.write("\n".join(regels) + "\n")


if __name__ == "__main__":
    # sys.exit en niet main(): zonder dit geeft het proces exitcode 0, ook als
    # de proef rood staat. Dan is de poort in de workflow altijd groen en
    # controleert hij in de praktijk niets. Dat was deze week al twee keer de
    # vorm van een fout: een stap die slaagt terwijl er niets gebeurde.
    sys.exit(main() or 0)
