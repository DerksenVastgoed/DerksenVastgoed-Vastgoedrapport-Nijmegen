#!/usr/bin/env python3
"""
Haalt de oppervlakte en het energielabel op van de hele woningvoorraad in de
zes ringbuurten, niet alleen van wat te koop staat.

Twee fasen, elk met een tijdbudget, elk hervatbaar:

  1. De BAG per postcode. Eén vraag met een postcode levert alle adressen in
     die postcode mét oppervlakte, gebruiksdoel en pandIdentificatie. De
     inventaris telde 1.743 postcodes in de ring, dus bij het tempo van 1,1
     seconde per vraag dat dit project aanhoudt is dat ongeveer 32 minuten:
     één run.
  2. EP-Online per adres, voor de woningen die nog geen label hebben. Dat gaat
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

# Een postcode opnieuw ophalen heeft weinig zin: oppervlakte en gebruiksdoel
# veranderen alleen bij een verbouwing. Eens per halfjaar is ruim.
VERS_DAGEN = 180

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
    """De werkvoorraad: (postcode, buurt) uit buurtinventaris.json."""
    d = _lees(INVENTARIS, {})
    per_buurt = d.get("postcodes_per_buurt") or {}
    if not per_buurt:
        print(f"Geen postcodes in {INVENTARIS}; draai eerst "
              f"buurtinventaris.py", file=sys.stderr)
        return []
    uit = []
    for buurt, lijst in sorted(per_buurt.items()):
        if buurten and buurt not in buurten:
            continue
        for pc in lijst:
            uit.append((pc, buurt))
    return uit


def anders_aantal(voorraad):
    """Hoeveel niet-woningen er in de voorraad staan."""
    return len(voorraad.get("niet_woningen") or {})


def _is_woning(doelen):
    return any("woonfunctie" == d for d in (doelen or []))


def haal_postcode(pc):
    """
    Alle adressen in één postcode, uit de BAG.

    pageSize 100 omdat een postcode zelden meer adressen heeft; staat er meer,
    dan meldt de BAG dat in de paginering en halen we de rest op.
    """
    rijen, pagina = [], 1
    while pagina <= 5:
        try:
            r = requests.get(f"{BAG_BASE}/adressenuitgebreid",
                             headers=BAG_HEADERS,
                             params={"postcode": pc, "pageSize": 100,
                                     "page": pagina},
                             timeout=(15, 60))
        except Exception as e:
            return None, f"netwerk: {e}"
        if r.status_code == 429:
            return None, "429 te veel vragen"
        if r.status_code in (401, 403):
            return None, f"{r.status_code} sleutel geweigerd"
        if r.status_code == 404:
            return [], ""
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        try:
            blok = r.json().get("_embedded", {}).get("adressen", [])
        except Exception as e:
            return None, f"antwoord onleesbaar: {e}"
        rijen.extend(blok)
        if len(blok) < 100:
            break
        pagina += 1
        time.sleep(TEMPO)
    return rijen, ""


def fase_bag(voorraad, werk, minuten):
    """Fase 1: de BAG per postcode, tot het tijdbudget om is."""
    if not BAG_API_KEY:
        print("Geen BAG_API_KEY; fase BAG overgeslagen", file=sys.stderr)
        return {"overgeslagen": "geen sleutel"}

    vandaag = dt.date.today().isoformat()
    grens = (dt.date.today() - dt.timedelta(days=VERS_DAGEN)).isoformat()
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

    einde = time.time() + minuten * 60
    gedaan_nu = fouten = nieuw = bijgewerkt = woningen = overig = gedeeld = 0
    fout_op_rij = 0
    laatste_fout = ""
    for pc, buurt in werk:
        if time.time() > einde:
            break
        if gedaan.get(pc, "") >= grens:
            continue
        rijen, fout = haal_postcode(pc)
        time.sleep(TEMPO)
        if rijen is None:
            fouten += 1
            fout_op_rij += 1
            laatste_fout = f"{pc}: {fout}"
            # Bij een geweigerde sleutel of een rem heeft doorgaan geen zin.
            if "sleutel" in fout or "429" in fout:
                break
            # En bij tien dezelfde mislukkingen op rij ook niet. Zonder deze
            # grens liep de fase op 10 oktober het volle budget van 35 minuten
            # vol met aanroepen die allemaal faalden.
            if fout_op_rij >= MAX_FOUT_OP_RIJ:
                print(f"{fout_op_rij} mislukkingen op rij, gestopt. "
                      f"Laatste: {laatste_fout}", file=sys.stderr)
                break
            continue
        fout_op_rij = 0
        gedaan[pc] = vandaag
        gedaan_nu += 1
        objecten = {}
        for a in rijen:
            straat = a.get("openbareRuimteNaam", "")
            nr = a.get("huisnummer", "")
            if not straat or not nr:
                continue
            letter = a.get("huisletter") or ""
            toev = a.get("huisnummertoevoeging") or ""
            doelen = a.get("gebruiksdoelen") or []
            if not _is_woning(doelen):
                overig += 1
                anders[adressleutel(straat, nr, letter, toev)] = {
                    "adres": f"{straat} {nr}{letter}{('-' + toev) if toev else ''}",
                    "postcode": pc,
                    "buurt": buurt,
                    "oppervlakte": a.get("oppervlakte"),
                    "doelen": doelen,
                    "pand": (a.get("pandIdentificaties") or [None])[0]
                            or a.get("pandIdentificatie"),
                    "vbo": a.get("adresseerbaarObjectIdentificatie") or "",
                    "status": a.get("adresseerbaarObjectStatus", ""),
                    "bag_gezien": vandaag,
                }
                continue
            woningen += 1
            vbo = a.get("adresseerbaarObjectIdentificatie") or ""
            objecten[vbo] = objecten.get(vbo, 0) + 1
            sleutel = adressleutel(straat, nr, letter, toev)
            oud = adressen.get(sleutel) or {}
            rec = {
                "adres": f"{straat} {nr}{letter}{('-' + toev) if toev else ''}",
                "postcode": pc,
                "buurt": buurt,
                "oppervlakte": a.get("oppervlakte"),
                "doelen": doelen,
                "pand": (a.get("pandIdentificaties") or [None])[0]
                        or a.get("pandIdentificatie"),
                "vbo": vbo,
                "status": a.get("adresseerbaarObjectStatus", ""),
                "bag_gezien": vandaag,
            }
            # Een eerder opgehaald label blijft staan; dat komt uit fase 2.
            for veld in ("label", "label_datum", "label_gezien"):
                if oud.get(veld) is not None:
                    rec[veld] = oud[veld]
            if sleutel in adressen:
                bijgewerkt += 1
            else:
                nieuw += 1
            adressen[sleutel] = rec
        gedeeld += sum(1 for n in objecten.values() if n > 1)

    return {"postcodes_gedaan": gedaan_nu, "postcodes_totaal": len(gedaan),
            "adressen_nieuw": nieuw, "adressen_bijgewerkt": bijgewerkt,
            "woningen_gezien": woningen, "niet_woonfunctie": overig,
            "niet_woningen_bewaard": len(anders),
            "objecten_met_meer_adressen": gedeeld,
            "fouten": fouten, "laatste_fout": laatste_fout}


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uit", default=UIT)
    p.add_argument("--bag-minuten", type=float, default=35)
    p.add_argument("--labels-minuten", type=float, default=45)
    p.add_argument("--alleen", choices=("bag", "labels"))
    p.add_argument("--buurt", action="append")
    args = p.parse_args()

    voorraad = _lees(args.uit, {})
    werk = postcodes_uit_inventaris(args.buurt)
    if not werk and args.alleen != "labels":
        return 1

    uit = {"bijgewerkt": dt.date.today().isoformat()}
    if args.alleen != "labels":
        uit["bag"] = fase_bag(voorraad, werk, args.bag_minuten)
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
