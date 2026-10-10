#!/usr/bin/env python3
"""
Gezondheidsrapport van de vastgoedbrief.

Draait als laatste stap en kijkt per onderdeel wat er werkelijk is opgeleverd.
Niet wat de log belooft, maar wat er in de bestanden staat: een script kan
netjes "gelukt" melden en toch niets hebben weggeschreven.

Het rapport is bedoeld om te kopiëren en te delen. Per onderdeel staat de
status, het bewijs en bij een probleem de vermoedelijke oorzaak en waar je
moet kijken.

Gebruik:
  python gezondheid.py --uit digests/2026-09-21-gezondheid.md
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

OK, LET_OP, FOUT = "OK", "LET OP", "FOUT"

# De scripts schrijven bij een probleem hun eigen diagnose weg in deze map.
# Het rapport neemt die over, zodat de oorzaak in het rapport staat en je niet
# in de logs hoeft te zoeken.
DIAGNOSE_MAP = "diagnose"


def diagnose(onderdeel):
    """
    De diagnose die een script zelf heeft achtergelaten, als die er is.

    Dubbele regels eruit: een script dat twee keer draait of twee keer
    hetzelfde vaststelt, hoort het maar een keer te zeggen.
    """
    pad = os.path.join(DIAGNOSE_MAP, f"{onderdeel}.txt")
    try:
        with open(pad, encoding="utf-8") as f:
            regels = [r.strip() for r in f if r.strip()]
    except Exception:
        return ""
    uniek = []
    for r in regels:
        if r not in uniek:
            uniek.append(r)
    return " ".join(uniek)


def automatische_keuzes():
    """Alle keuzes die een script zelf heeft gemaakt, uit alle diagnoses."""
    uit = []
    if not os.path.isdir(DIAGNOSE_MAP):
        return uit
    for naam in sorted(os.listdir(DIAGNOSE_MAP)):
        try:
            with open(os.path.join(DIAGNOSE_MAP, naam), encoding="utf-8") as f:
                for regel in f:
                    regel = regel.strip()
                    if regel.startswith("AUTOMATISCH") and regel not in uit:
                        uit.append(regel.replace("AUTOMATISCH: ", ""))
        except Exception:
            continue
    return uit


def _kort(tekst, maximum=240):
    """Een diagnose inkorten tot iets wat in een bericht past."""
    if len(tekst) <= maximum:
        return tekst
    return tekst[:maximum].rsplit(" ", 1)[0] + " (...)"
VANDAAG = dt.date.today()


def _geschiedenis(pad="pandgeschiedenis.json"):
    """De pandgeschiedenis, uitgevouwen uit de compacte vorm."""
    try:
        from pandlezer import laad
        return laad(pad)
    except Exception:
        return _json(pad) or {}


def _json(pad):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _leeftijd_dagen(pad):
    """Hoeveel dagen geleden is dit bestand bijgewerkt?"""
    try:
        return (VANDAAG - dt.date.fromtimestamp(os.path.getmtime(pad))).days
    except Exception:
        return None


def _regels(pad):
    try:
        with open(pad, encoding="utf-8") as f:
            return [r for r in f if r.strip() and not r.startswith("#")]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# De controles. Elk geeft (status, bewijs, diagnose) terug.
# ---------------------------------------------------------------------------

def controle_huur_ijkpunt():
    """
    Onze gemeten huur per m2 tegen het landelijke cijfer van Pararius.

    Pararius meldde voor het derde kwartaal van 2026 €20,92 per m2 in de vrije
    sector. Wij lezen Pararius zelf uit voor de ring, dus een groot verschil
    zegt iets: of onze steekproef is niet representatief, of hij bevat
    middenhuur en servicekosten die daar niet in zitten. Het is geen fout, maar
    het hoort zichtbaar te zijn in plaats van verstopt in een weging.
    """
    try:
        from marktprijzen_bag import LANDELIJK_HUUR_M2, LANDELIJK_HUUR_PEILDATUM
    except Exception:
        return (OK, "geen landelijk ijkpunt beschikbaar", "")
    waarden = []
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                if regel.startswith("#"):
                    continue
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 7 or not v[3].lower().startswith("te huur"):
                    continue
                if "kamer" in v[3].lower():
                    continue
                try:
                    prijs, opp = float(v[2]), float(v[6])
                except (ValueError, IndexError):
                    continue
                if opp >= 20 and prijs >= 300:
                    waarden.append(prijs / opp)
    except Exception:
        return (OK, "geen aanbodbestand om te toetsen", "")
    if len(waarden) < 3:
        return (OK, f"te weinig huurwaarnemingen met oppervlakte "
                f"({len(waarden)}) om tegen het landelijke cijfer van "
                f"€{LANDELIJK_HUUR_M2}/m2 te houden", "")
    waarden.sort()
    eigen = waarden[len(waarden) // 2]
    afw = round((eigen / LANDELIJK_HUUR_M2 - 1) * 100)
    bewijs = (f"onze mediaan €{eigen:.2f}/m2 uit {len(waarden)} waarnemingen "
              f"tegen landelijk €{LANDELIJK_HUUR_M2}/m2 "
              f"({LANDELIJK_HUUR_PEILDATUM}): {afw:+d}%")
    if abs(afw) > 25:
        return (LET_OP, bewijs,
                "Een verschil van meer dan een kwart vraagt uitleg. Het "
                "landelijke cijfer gaat over nieuwe verhuringen in de vrije "
                "sector; onze meting bevat ook middenhuur en soms "
                "servicekosten. Controleer of de steekproef niet uit vooral "
                "kleine of juist grote woningen bestaat.")
    return (OK, bewijs, "")


def controle_brieven():
    """
    Wanneer is er voor het laatst een brief gemaakt?

    Op 8 oktober viel de ochtendbrief weg en bleef dat tot half twaalf
    onopgemerkt: de mailstap stuurt alleen iets als het briefbestand bestaat,
    dus een mislukte run leverde geen brief EN geen melding op. Het ontbreken
    van post ziet eruit als een rustige dag.

    De weekeditie draait op zondag, dus op maandag mag de jongste brief van
    gisteren zijn. Twee dagen stilte is altijd een probleem.
    """
    datums = []
    try:
        for naam in os.listdir("digests"):
            if naam.endswith("-brief.md") and len(naam) >= 10:
                try:
                    datums.append(dt.date.fromisoformat(naam[:10]))
                except ValueError:
                    continue
    except FileNotFoundError:
        return (OK, "geen digestmap in deze run", "")
    if not datums:
        return (LET_OP, "geen enkele brief in de digestmap",
                "Dit is de eerste run, of de map is leeg gelopen.")
    laatste = max(datums)
    dagen = (VANDAAG - laatste).days
    bewijs = (f"{len(datums)} brieven bewaard, laatste van {laatste} "
              f"({'vandaag' if not dagen else f'{dagen} dagen terug'})")
    if dagen >= 2:
        return (LET_OP, bewijs,
                "Er is minstens een werkdag geen brief gemaakt. Kijk in het "
                "logboek van de geplande run welke stap rood werd; de mailstap "
                "stuurt niets als het briefbestand ontbreekt.")
    return (OK, bewijs, "")


def controle_afzenders():
    """
    Of elke bron waarvan we mails verwachten ook werkelijk iets oplevert.

    Huislijn stond met een verkeerd domein in de lijst, "huisly.nl" in plaats
    van "huislijn.nl". De mails stonden daardoor ongelezen in de mailbox en de
    woningen kwamen nergens terecht. Dat was alleen te zien doordat Mark het
    opmerkte, en dat is precies het soort fout dat een controle hoort te doen.
    """
    bronnen_verwacht = ("funda", "pararius", "kamernet", "huislijn",
                        "123wonen", "rentola")
    gezien = {}
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                if regel.startswith("#"):
                    continue
                v = [x.strip().lower() for x in regel.split("|")]
                if len(v) > 5 and v[5]:
                    for b in bronnen_verwacht:
                        if b in v[5]:
                            gezien[b] = gezien.get(b, 0) + 1
    except Exception:
        return (OK, "geen aanbodbestand om te toetsen", "")
    stil = [b for b in bronnen_verwacht if not gezien.get(b)]
    bewijs = ", ".join(f"{b}: {gezien.get(b, 0)}" for b in bronnen_verwacht)
    if stil:
        return (LET_OP, bewijs + f"; geen enkele waarneming van: "
                + ", ".join(stil),
                "Controleer of het afzenderdomein in AFZENDERS klopt en of de "
                "attendering bij die partij aanstaat. Een verkeerd domein "
                "levert geen foutmelding op, alleen stilte.")
    return (OK, bewijs, "")


def controle_huurdata():
    """Het belangrijkste: rust de richtprijs op metingen of op een aanname?"""
    regels = _regels("verkopen.txt")
    huur = [r for r in regels if "te huur" in r.lower()]
    pararius = [r for r in huur if "pararius" in r.lower()]
    kamernet = [r for r in huur if "kamernet" in r.lower()]
    recent = [r for r in huur
              if any(str(VANDAAG - dt.timedelta(days=d)) in r for d in range(8))]
    huislijn = [r for r in huur if "huislijn" in r.lower()]
    wonen123 = [r for r in huur if "123wonen" in r.lower()]
    rentola = [r for r in huur if "rentola" in r.lower()]
    # Waarnemingen zonder oppervlakte: bruikbaar om te zien wat er te huur
    # staat, niet om een prijs per vierkante meter uit te rekenen. Huislijn
    # geeft alleen een straatnaam en een huurprijs, dus die vallen hieronder.
    zonder_m2 = 0
    for r in huur:
        v = [x.strip() for x in r.split("|")]
        if len(v) < 7 or not v[6]:
            zonder_m2 += 1
    # Waarnemingen waarvan het adres of de oppervlakte met de hand is
    # aangevuld, gemarkeerd met "+hand" achter de bron. Huislijn geeft geen
    # huisnummer, dus elke waarneming daar is onvolledig; herkent Mark een pand
    # van de foto, dan is de oppervlakte uit de BAG hard MITS het adres klopt.
    # Dat voorbehoud hoort zichtbaar te zijn, net als de tilde bij een
    # overgenomen WOZ-waarde.
    met_hand = [r for r in huur if "+hand" in r.lower()]
    # Huislijn levert zelf geen oppervlakte; die wordt van de advertentiepagina
    # gehaald. Zijn er Huislijn-waarnemingen en heeft GEEN ervan een
    # oppervlakte, dan lukt dat ophalen niet, en dan vallen ze allemaal buiten
    # de huur per m2 zonder dat iets dat zegt.
    # Dit geldt voor elke bron waarvan de oppervlakte van de advertentiepagina
    # komt. 123Wonen is de tweede: de mail noemt daar zelfs de straat niet.
    stille_bron = None
    for naam in ("huislijn", "123wonen"):
        rijen = [r for r in huur if naam in r.lower()]
        if not rijen:
            continue
        met_m2 = 0
        for r in rijen:
            v = [x.strip() for x in r.split("|")]
            if len(v) > 6 and v[6]:
                met_m2 += 1
        if not met_m2:
            stille_bron = (naam, len(rijen))
            break
    bewijs = (f"{len(huur)} huurwaarnemingen, waarvan {len(pararius)} Pararius "
              f"en {len(kamernet)} Kamernet"
              + (f" en {len(huislijn)} Huislijn" if huislijn else "")
              + (f" en {len(wonen123)} 123Wonen" if wonen123 else "")
              + (f" en {len(rentola)} Rentola, zonder adres maar met "
                 f"oppervlakte" if rentola else "")
              + f"; {len(recent)} in de laatste week"
              + (f"; {zonder_m2} zonder oppervlakte, die tellen niet mee in de "
                 f"huur per m2" if zonder_m2 else "")
              + (f"; {len(met_hand)} met een handmatig aangevuld adres, die "
                 f"tellen wel mee maar rusten op een herkenning"
                 if met_hand else "")
              + (f"; {(_json('huur_dubbel.json') or {}).get('samengevoegd')} "
                 f"waarschijnlijke dubbelingen tussen platforms samengevoegd"
                 if (_json("huur_dubbel.json") or {}).get("samengevoegd")
                 else ""))
    if not huur:
        return (FOUT, bewijs,
                "Geen enkele huurwaarneming. Elke richtprijs rust op een aanname. "
                "Kijk in stap 14 naar de [pararius]-regels: staat daar "
                "'0 objecten', dan herkent de parser de mail niet.")
    if not recent:
        return (LET_OP, bewijs,
                "Wel huurdata, maar niets nieuws deze week. Komen de Pararius-mails "
                "nog binnen, en worden ze herkend? Zie stap 14.")
    if stille_bron:
        naam, aantal = stille_bron
        return (LET_OP, bewijs + f"; geen van de {aantal} "
                f"{naam}-waarnemingen heeft een oppervlakte",
                f"De oppervlakte van een {naam}-pand komt van de "
                "advertentiepagina, niet uit de mail. Lukt dat ophalen niet, "
                "dan tellen die waarnemingen nergens mee. Zoek in het logboek "
                "van de mailstap op 'kenmerken niet op te halen'.")
    if len(huur) < 30:
        return (LET_OP, bewijs,
                "Er wordt gemeten, maar het aantal is nog te klein voor een "
                "betrouwbare mediaan per grootteklasse en buurt.")
    return (OK, bewijs, "")


def controle_aanbod():
    regels = _regels("verkopen.txt")
    koop = [r for r in regels if "te koop" in r.lower() or "belegging" in r.lower()]
    recent = [r for r in koop
              if any(str(VANDAAG - dt.timedelta(days=d)) in r for d in range(4))]
    bewijs = f"{len(koop)} koopobjecten, {len(recent)} in de laatste drie dagen"
    if not koop:
        return (FOUT, bewijs, "Het aanbodbestand is leeg. Zie stap 14.")
    if not recent:
        return (LET_OP, bewijs,
                "Geen nieuw aanbod in drie dagen. Kan kloppen in een stille week, "
                "maar controleer of de Funda-mails binnenkomen.")
    return (OK, bewijs, "")


def controle_rente():
    d = _json("rente_actueel.json") or {}
    leeftijd = _leeftijd_dagen("rente_actueel.json")
    rente = d.get("rente") or d.get("ltv70")
    if not rente:
        return (FOUT, "geen rente in rente_actueel.json",
                "De rentestap leverde niets op. Zie stap 8; financieren.nl kan van "
                "opmaak zijn veranderd.")
    if leeftijd is not None and leeftijd > 3:
        return (LET_OP, f"rente {rente}%, bestand {leeftijd} dagen oud",
                "De rente is niet vernieuwd. Zie stap 8.")
    return (OK, f"rente {rente}% bij 70% financiering", "")


def controle_ecb():
    d = _json("rente_actueel.json") or {}
    markt = d.get("kapitaalmarkt")
    if markt is None:
        return (FOUT, "geen kapitaalmarktrente vastgelegd",
                "De ECB gaf geen antwoord. Zie stap 8, de regel 'ECB-rente'. Staat "
                "er 'mislukt op alle manieren', dan blokkeert de ECB verzoeken "
                "vanaf GitHub en helpt een andere vraagvorm niet.")
    rente = d.get("ltv70") or d.get("rente")
    opslag = (f", opslag bij 70% financiering {rente - markt:.2f}".replace(".", ",")
              + " procentpunt") if rente else ""
    return (OK, f"tienjaars AAA-rente " + f"{markt:.2f}".replace(".", ",")
            + f"% ({d.get('kapitaalmarkt_datum', '')}){opslag}", "")


def controle_bouwkosten():
    d = _json("bouwkosten_index.json") or {}
    if not d:
        return (FOUT, "bouwkosten_index.json ontbreekt of is leeg",
                diagnose("bouwkosten")
                or "De verbouwkosten worden niet geindexeerd. Zie stap 17.")
    laatste = max(d)
    return (OK, f"{len(d)} maanden, laatste {laatste}", "")


def controle_eigen_bouwkosten():
    eigen = [r for r in _regels("bouwkosten_eigen.txt") if "|" in r]
    if not eigen:
        return (LET_OP, "geen eigen bouwkosten ingevuld",
                "De verbouwkosten zijn aannames van het script. Vul in "
                "bouwkosten_eigen.txt wat verhuurklaar maken en verduurzaming per "
                "m2 kosten; uit het hoofd is al beter dan de aanname.")
    return (OK, f"{len(eigen)} eigen tarieven ingevuld", "")


def controle_buurtcijfers():
    d = _json("buurten_cbs.json") or {}
    buurten = [b for b in d if not str(b).startswith("_")]
    if not buurten:
        return (FOUT, "buurten_cbs.json leeg", "Zie stap 7.")
    eerste = d[buurten[0]] if buurten else {}
    ontbreekt = [v for v in ("inkomen", "vermogen", "eenpersoons", "leeftijd",
                             "afstand_trein")
                 if eerste.get(v) is None]
    bewijs = f"{len(buurten)} buurten"
    if ontbreekt:
        return (LET_OP, bewijs + f"; ontbreekt: {', '.join(ontbreekt)}",
                diagnose("buurtcijfers")
                or "Deze velden worden niet gevonden in de CBS-kaart. In stap 7 "
                   "staat welke veldnamen er wel zijn.")
    return (OK, bewijs + ", alle velden gevuld", "")


def controle_vergunningen():
    per_buurt = _json("vergunningen_per_buurt.json") or {}
    lijst = _json("kamervergunningen.json") or {}
    if not lijst:
        return (FOUT, "kamervergunningen.json ontbreekt", "")
    if len(per_buurt) < 3:
        return (LET_OP, f"{len(lijst)} adressen, maar {len(per_buurt)} buurten "
                        f"gekoppeld",
                diagnose("vergunningen")
                or "De koppeling aan buurten is niet gemaakt; de kolom in de brief "
                   "blijft leeg. Zie stap 5.")
    return (OK, f"{len(lijst)} adressen in {len(per_buurt)} buurten", "")


def controle_kamerverhuur():
    """Het register van kamerverhuurpanden, en hoe ver de meldingen teruggaan."""
    d = _json("kamerverhuur_per_buurt.json") or {}
    per = d.get("per_buurt") or {}
    if not per:
        return (FOUT, "kamerverhuur_per_buurt.json ontbreekt of is leeg",
                diagnose("kamerverhuur") or "Zie de stap Kamerverhuurregister.")
    totaal = sum(v.get("totaal", 0) for v in per.values())
    via_melding = sum(v.get("alleen_melding_of_besluit", 0) for v in per.values())
    jaren = d.get("meldingen_per_jaar") or {}
    jaartekst = (", ".join(f"{j}: {n}" for j, n in jaren.items())
                 if jaren else "geen meldingen")
    bewijs = (f"{totaal} panden in de ring, waarvan {via_melding} alleen via een "
              f"melding of besluit; meldingen per jaar: {jaartekst}")
    if not jaren:
        return (LET_OP, bewijs, diagnose("kamerverhuur") or
                "Geen meldingen in het archief; het register rust dan alleen op de "
                "vergunningenlijst.")
    return (OK, bewijs, "")


def controle_woningprijzen():
    d = _json("woningprijsindex.json") or {}
    l, r = d.get("landelijk"), d.get("regio")
    if not l and not r:
        return (FOUT, "woningprijsindex.json leeg; daarmee valt ook de "
                "WOZ-schatting weg voor elk pand zonder eigen WOZ-waarde",
                (diagnose("woningprijzen") or "Zie de stap Woningprijsindex "
                 "CBS.") + " Sinds 9 oktober overschrijft een mislukte "
                "ophaalronde een goede reeks niet meer; staat dit er toch, "
                "dan was er ook geen eerdere reeks.")
    delen = []
    # Een reeks die is blijven staan omdat het ophalen vandaag mislukte. Beter
    # dan niets, maar het hoort zichtbaar te zijn: de reeks veroudert.
    if d.get("laatste_poging_mislukt"):
        leeftijd = None
        try:
            leeftijd = (VANDAAG - dt.date.fromisoformat(
                d.get("opgehaald") or "")).days
        except Exception:
            pass
        return (LET_OP,
                f"de reeks van {d.get('opgehaald', 'onbekende datum')} is "
                f"bewaard; het ophalen mislukte voor het laatst op "
                f"{d['laatste_poging_mislukt']}"
                + (f", de reeks is {leeftijd} dagen oud" if leeftijd else ""),
                "De WOZ-schatting blijft werken met de bewaarde reeks, dus dit "
                "is geen storing met gevolgen. Blijft het meer dan een paar "
                "dagen mislukken, kijk dan in het logboek van de stap "
                "Woningprijsindex CBS: het CBS wijzigt soms kolomnamen.")
    if l:
        delen.append(f"landelijk {l['periode']}")
    if r:
        delen.append(f"{r['naam']} {r['periode']}")
    if d.get("ingang"):
        delen.append(f"via {d['ingang']}")
    v = d.get("vergelijking") or {}
    if v.get("beste_verband"):
        b = v["beste_verband"]
        delen.append(f"eigen reeks {v['maanden']} maanden, sterkste samenhang bij "
                     f"{b['vertraging_maanden']} maanden vooruit ({b['r']})")
    elif v.get("maanden"):
        delen.append(f"eigen reeks {v['maanden']} maanden sinds {v['sinds']}, "
                     f"vergelijking start bij 13")
    if not r:
        return (LET_OP, ", ".join(delen) + "; geen regio",
                diagnose("woningprijzen") or "Nijmegen niet gevonden in de regiotabel.")
    return (OK, ", ".join(delen), "")


def controle_begroting():
    d = _json("begroting_nijmegen.json") or {}
    if not d.get("paginas"):
        return (LET_OP, "nog geen begroting opgehaald",
                diagnose("begroting") or "Draait de stap Stadsbegroting al?")
    return (OK, f"Stadsbegroting {d.get('jaar')}, {len(d['paginas'])} pagina's, "
                f"opgehaald {d.get('opgehaald')}", "")


def controle_geschiedenis():
    """Hoeveel panden we volgen, en hoeveel er nog nooit zijn nagekeken."""
    d = _geschiedenis()
    if not d:
        return (LET_OP, "nog geen geschiedenis opgebouwd",
                diagnose("geschiedenis") or "Draait de stap Geschiedenis per pand?")
    met_verhaal = sum(1 for p in d.values()
                      if len(p.get("gebeurtenissen") or []) > 1)
    nooit = sum(1 for p in d.values() if not p.get("bag_gezien"))
    opgegeven = sum(1 for p in d.values()
                    if int(p.get("bag_pogingen") or 0) >= 3)
    zonder_id = sum(1 for p in d.values() if p.get("bag_zonder_id"))
    # Wat er werkelijk is opgehaald: de eenheden uit de BAG en de labels uit
    # EP-Online. Dat was tot nu toe alleen af te leiden uit een aftreksom.
    met_bag = sum(1 for p in d.values() if p.get("bag_eenheden"))
    met_label = sum(1 for p in d.values() if p.get("labels"))
    # Per pand-id tellen en niet per sleutel. Hetzelfde pand staat soms onder
    # meerdere adressen in het bestand, elk met de volledige lijst eenheden;
    # optellen over sleutels telde die woningen dan dubbel. Achter de Carmel 28
    # en 32 zijn hetzelfde gebouw met acht eenheden, en die werden zestien.
    per_pand, zonder_id = {}, 0
    for p in d.values():
        eenh = p.get("bag_eenheden") or []
        pid = p.get("pand_id")
        if pid:
            per_pand[pid] = max(per_pand.get(pid, 0), len(eenh))
        else:
            zonder_id += len(eenh)
    eenheden = sum(per_pand.values()) + zonder_id
    dubbel = sum(len(p.get("bag_eenheden") or []) for p in d.values()) - eenheden
    # Het getal uit het script zelf, niet een eigen kopie: die liepen uiteen
    # toen de standaard van 200 naar 500 ging.
    try:
        from pandgeschiedenis import MAX_BAG_PER_RONDE as per_ronde
    except Exception:
        per_ronde = int(os.environ.get("BAG_PER_RONDE") or 500)
    # Labels groeien alleen tijdens een volledige ronde; dat staat erbij zodat
    # een stilstaand getal niet als storing wordt gelezen.
    # Hoeveel het delen van pandgegevens scheelt, zodat de verbouwing
    # meetbaar is in plaats van aangenomen.
    try:
        from pandlezer import tel_besparing
        bes = tel_besparing(d)
    except Exception:
        bes = {}
    bewijs = (f"{len(d)} panden gevolgd, {met_verhaal} met meer dan een "
              f"gebeurtenis; {met_bag} met BAG-gegevens ({eenheden} woningen"
              + (f", {dubbel} dubbel geteld zonder deze correctie" if dubbel else "")
              + "), "
              f"{met_label} met een energielabel, {nooit} nog nooit nagekeken"
              + (f", {zonder_id} zonder pand-id in de BAG" if zonder_id else "")
              + (f" waarvan {opgegeven} na drie pogingen opgegeven"
                 if opgegeven else "")
              + (f"; {bes['bespaard']} regels bespaard door gedeelde "
                 f"pandgegevens" if bes.get("bespaard") else "")
              + ("; nieuwe panden worden elke run opgehaald, het nakijken van "
                 "de hele voorraad op veranderingen gebeurt in de weekronde"
                 if met_label < met_bag else ""))
    # Een handvol panden dat vandaag of gisteren uit de attendering kwam, is
    # geen achterstand: de BAG en het label worden opgehaald bij de eerste
    # volledige ronde, dus uiterlijk zondag. Dat op LET OP zetten maakt een
    # melding van iets wat precies volgens plan verloopt.
    if nooit > per_ronde // 10:
        runs = -(-nooit // per_ronde)
        oorzaak = (f"Bij {per_ronde} panden per ronde zijn dat nog {runs} "
                   f"run(s). Elke handmatige start werkt er een ronde af.")
        return (LET_OP, bewijs, diagnose("geschiedenis") or oorzaak)
    if nooit:
        return (OK, bewijs + "; die paar zijn net binnengekomen en worden bij "
                "de eerste volledige ronde opgehaald",
                diagnose("geschiedenis") or "")
    return (OK, bewijs + "; iedereen is minstens een keer nagekeken",
            diagnose("geschiedenis") or "")


def controle_mailbronnen():
    """Welke attenderingen er binnenkomen, en of er iets uit te halen valt."""
    d = _json("mail_status.json") or {}
    bronnen = d.get("bronnen") or {}
    if d.get("opmerking"):
        return (LET_OP, f"mailstap van {d.get('datum', '?')}: {d['opmerking']}",
                "De mailstap kwam niet bij de mailbox; zonder die stap komt er "
                "geen aanbod binnen.")
    if not bronnen:
        return (LET_OP, f"mailstap van {d.get('datum', '?')}: geen enkele mail "
                        f"van een van de bronnen",
                "Komen de attenderingen in deze mailbox binnen, en staan ze in "
                "de inbox en niet in een map?")
    delen, stil, stom = [], [], []
    for bron, t in sorted(bronnen.items()):
        stuk = (f"{bron}: {t.get('mails', 0)} mails, "
                f"{t.get('objecten', 0)} objecten")
        if t.get("overgeslagen"):
            stuk += f", {t['overgeslagen']} bewust overgeslagen"
        delen.append(stuk)
        if not t.get("mails"):
            stil.append(bron)
        elif not t.get("objecten") and not t.get("overgeslagen"):
            # Alleen alarm slaan als er niets uitkwam en er ook niets bewust is
            # overgeslagen. Een mail met alleen een gemeubileerde woning levert
            # terecht nul objecten op; dat is geen parserfout.
            stom.append(bron)
    for verwacht in ("kamernet", "pararius", "funda"):
        if verwacht not in bronnen:
            stil.append(verwacht)
    bewijs = f"laatste ronde {d.get('datum', '?')}: " + "; ".join(delen)
    # Post van platforms waar nog geen parser voor is. Zo wordt een aanmelding
    # zichtbaar in plaats van dat die mails ongemerkt blijven liggen.
    kandidaten = d.get("kandidaten") or {}
    if kandidaten:
        bewijs += ("; zonder parser: "
                   + ", ".join(f"{b} ({n})" for b, n in sorted(kandidaten.items())))
    if stom:
        voorbeelden = []
        for bron in stom:
            for r in (bronnen[bron].get("redenen") or [])[:2]:
                voorbeelden.append(f"{bron}: {r}")
        staart = (" Voorbeeld: " + "; ".join(voorbeelden)) if voorbeelden else ""
        return (LET_OP, bewijs,
                f"Van {', '.join(stom)} komen wel mails binnen maar het script "
                f"haalt er niets uit; de opmaak is waarschijnlijk veranderd."
                + staart)
    if stil:
        return (LET_OP, bewijs,
                f"Van {', '.join(sorted(set(stil)))} kwam geen enkele mail. "
                f"Staat de attendering aan en komt hij in deze mailbox binnen?")
    return (OK, bewijs, "")


def controle_versies():
    """
    Draait deze run op de bestanden die bij de laatste oplevering horen?

    Staat bovenaan in het rapport, zodat een geplakt rapport meteen laat zien
    welke code er draaide. Anders moet dat uit een andere stap in het logboek
    komen en is het bij het overnemen zo verdwenen.
    """
    try:
        import paklijst as _v
        controleer = getattr(_v, "controleer", None)
        if controleer is None:
            # Een oudere versies.py zonder die functie. Met de details erbij,
            # anders moet je op mijn woord geloven dat het bestand anders is.
            pad = getattr(_v, "__file__", "?")
            try:
                grootte = os.path.getsize(pad)
                gewijzigd = dt.datetime.fromtimestamp(
                    os.path.getmtime(pad)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                grootte, gewijzigd = "?", "?"
            heeft = ", ".join(sorted(
                n for n in dir(_v) if not n.startswith("_") and callable(
                    getattr(_v, n, None)))) or "geen functies"
            return (LET_OP,
                    f"de paklijst.py in de repo mist de functie controleer "
                    f"({grootte} bytes, gewijzigd {gewijzigd}); hij kent: "
                    f"{heeft}",
                    "Upload paklijst.py opnieuw; let op dat je het script "
                    "pakt en niet versies.json.")
        uit = controleer()
    except Exception as e:
        return (LET_OP, "versiecontrole niet uit te voeren", str(e)[:120])
    if uit is None:
        return (LET_OP, "geen paklijst gevonden",
                "versies.json hoort mee in dezelfde upload als de bestanden.")
    gemaakt = (_json("versies.json") or {}).get("gemaakt", "?")
    bewijs = (f"paklijst van {gemaakt}: {len(uit['gelijk'])} gelijk, "
              f"{len(uit['afwijkend'])} met andere inhoud, "
              f"{len(uit['ontbrekend'])} niet aanwezig")
    if uit["afwijkend"] or uit["ontbrekend"]:
        # Afwijkend en ontbrekend zijn twee verschillende dingen, en bij
        # afwijkend hoort de datum van het bestand in de repo: is dat nieuwer
        # dan de paklijst, dan is de paklijst oud en niet het bestand.
        # Geen bestandsdatum erbij: in een workflow krijgt elk bestand de tijd
        # van het uitchecken, dus ze staan allemaal op dezelfde minuut en zegt
        # die datum niets over wanneer de inhoud is geschreven. Dat was gisteren
        # een verkeerde aanname van mij.
        delen = []
        if uit["afwijkend"]:
            delen.append("andere inhoud dan de paklijst: "
                         + ", ".join(uit["afwijkend"][:6]))
        if uit["ontbrekend"]:
            delen.append("niet in de repo: " + ", ".join(uit["ontbrekend"][:6]))
        return (LET_OP, bewijs + "; " + "; ".join(delen),
                "Upload de ontbrekende bestanden. Blijft een bestand afwijken "
                "nadat het is geuploud, dan is de paklijst achter en moet die "
                "ververst worden.")
    if uit["onbekend"]:
        bewijs += f", {len(uit['onbekend'])} niet in de paklijst"
    return (OK, bewijs, "")


def controle_peildata():
    """
    Bedragen en grenzen die elk jaar opnieuw worden vastgesteld.

    De huurprijstabel wordt per 1 januari geindexeerd, en daarmee verschuift de
    grens tussen middenhuur en vrije sector. Hetzelfde geldt voor de WOZ-grenzen
    in de huisvestingsverordening en voor de overdrachtsbelasting. Staat hier
    een ouder jaar dan het huidige, dan rekent het script met verouderde
    grenzen zonder dat iemand dat merkt.
    """
    dit_jaar = dt.date.today().year
    regels, verouderd = [], []
    try:
        from wwso import TABEL_PEILDATUM, TABEL_BRON, WWS_TABEL
        jaar = int(TABEL_PEILDATUM[:4])
        regels.append(f"huurprijstabel {TABEL_PEILDATUM} (grens vrije sector "
                      f"€{WWS_TABEL.get(186, 0):.2f})")
        if jaar < dit_jaar:
            verouderd.append(f"de huurprijstabel is van {jaar}; de nieuwe staat "
                             f"in {TABEL_BRON}")
    except Exception as e:
        return (LET_OP, "huurprijstabel niet te lezen", str(e)[:120])

    try:
        from marktprijzen_bag import (OVERDRACHTSBELASTING_PCT,
                                      BIJKOMENDE_KOSTEN_PCT)
        regels.append(f"overdrachtsbelasting {OVERDRACHTSBELASTING_PCT}% plus "
                      f"{BIJKOMENDE_KOSTEN_PCT}% bijkomende kosten")
    except Exception:
        pass

    try:
        from subsidie_svoh import PEILDATUM as SVOH_PEIL, PER_M2
        jaar = int(SVOH_PEIL[:4])
        regels.append(f"SVOH-bedragen {SVOH_PEIL} (gevelisolatie "
                      f"€{PER_M2['gevelisolatie'][1]:.2f} per m2)")
        if jaar < dit_jaar:
            verouderd.append(f"de SVOH-bedragen zijn van {jaar}; ze worden "
                             f"jaarlijks opnieuw vastgesteld door de RVO.")
    except Exception:
        pass

    try:
        from marktprijzen_bag import WOZ_GRENS_OMZETTING, WOZ_GRENS_WEIGERING
        regels.append(f"WOZ-grenzen €{WOZ_GRENS_OMZETTING:,} en "
                      f"€{WOZ_GRENS_WEIGERING:,}".replace(",", "."))
    except Exception:
        pass

    if verouderd:
        return (LET_OP, "; ".join(regels),
                " ".join(verouderd) + " Werk de tabel bij en zet de nieuwe "
                "peildatum erbij.")
    return (OK, "; ".join(regels), "")


def controle_bag3d():
    """De eigen snapshot van hoogtes en oppervlakken per pand."""
    d = _json("bag3d.json") or {}
    panden = d.get("panden") or {}
    if not panden:
        return (LET_OP, "nog geen 3D BAG-gegevens opgehaald",
                "Zonder hoogte en buitenmuuroppervlak is er geen basis voor de "
                "bouwkosten per pand. Zie de stap in het logboek.")
    met = sum(1 for p in panden.values() if p.get("b3_opp_buitenmuur"))
    leeg = sum(1 for p in panden.values() if p.get("leeg"))
    opgegeven = sum(1 for p in panden.values()
                    if int(p.get("pogingen") or 0) >= 3)
    bewijs = (f"{len(panden)} panden in de eigen snapshot, {met} met een "
              f"buitenmuuroppervlak, {leeg} zonder gegevens bij de bron"
              + (f", {opgegeven} na drie pogingen opgegeven" if opgegeven else "")
              + f"; bijgewerkt {d.get('bijgewerkt', '?')}")
    if met < len(panden) * 0.5:
        return (LET_OP, bewijs,
                "Van minder dan de helft kwamen bruikbare waarden; controleer "
                "of de opzet van de bron is veranderd.")
    return (OK, bewijs, "")


def controle_corop():
    """De kwartaalcijfers voor het eigen COROP-gebied."""
    d = _json("corop_prijzen.json") or {}
    if not d.get("periode"):
        return (LET_OP, "geen COROP-cijfers opgehaald",
                "Zonder deze tabel vergelijkt de brief onze buurtcijfers met "
                "heel Gelderland; dat is te grof. Zie de stap in het logboek.")
    oud = ""
    try:
        jaar, kw = d["periode"][:4], d["periode"][-1]
        maanden = (dt.date.today().year - int(jaar)) * 12 + \
                  (dt.date.today().month - int(kw) * 3)
        if maanden > 6:
            oud = (f" De cijfers zijn van {d['periode']}; het CBS publiceert "
                   f"ongeveer 22 dagen na afloop van een kwartaal.")
    except Exception:
        pass
    bewijs = (f"{d.get('gebied')} {d['periode']}: index {d.get('index')}, "
              f"{d.get('jaar_pct')}% op jaarbasis, "
              f"{int(d.get('transacties') or 0)} transacties")
    return ((LET_OP, bewijs, oud.strip()) if oud else (OK, bewijs, ""))


def controle_wozschatting():
    """Hoe betrouwbaar is de eigen WOZ-schatting inmiddels?"""
    d = _json("woz_kalibratie.json") or {}
    aantal = d.get("aantal") or 0
    if aantal < 8:
        # Eerst kijken of de oorzaak elders ligt. De schatting herleidt de
        # vraagprijs met de landelijke prijsindex naar de waardepeildatum;
        # zonder die index is er voor geen enkel pand een schatting en valt de
        # ijking naar nul, hoeveel WOZ-waarden er ook zijn ingevoerd. Op 9
        # oktober stond dat als twee losse meldingen in het rapport, en ik heb
        # er een uur in de verkeerde richting naar gezocht.
        index = _json("woningprijsindex.json") or {}
        if not (index.get("landelijk") or index.get("regio")):
            woz_regels = 0
            try:
                with open("woz.txt", encoding="utf-8") as f:
                    woz_regels = sum(
                        1 for r in f
                        if not r.lstrip().startswith("#")
                        and len(r.split("|")) > 1
                        and any(c.isdigit() for c in r.split("|")[1]))
            except Exception:
                pass
            return (FOUT, f"geijkt op {aantal} panden, maar de oorzaak is de "
                    f"woningprijsindex: die is leeg, en zonder die reeks is er "
                    f"voor geen enkel pand een WOZ-schatting"
                    + (f". De {woz_regels} ingevoerde WOZ-waarden zijn er nog"
                       if woz_regels else ""),
                    "Dit is geen WOZ-probleem. De schatting herleidt de "
                    "vraagprijs met de landelijke prijsindex naar de "
                    "waardepeildatum; zonder index geen factor en dus geen "
                    "schatting. Kijk bij 'Woningprijsindex CBS' en in het "
                    "logboek van die stap.")
        return (LET_OP, f"geijkt op {aantal} panden, te weinig om iets te zeggen",
                "Voer WOZ-waarden in bij grensgevallen; vanaf acht panden begint "
                "de schatting zichzelf te corrigeren.")
    vgl = d.get("vergelijking") or {}
    delen = []
    # Alle methoden tonen die er zijn, met het aantal erbij. De lijst was
    # beperkt tot twee vaste namen, waardoor "prijsindex" wegviel en er maar
    # een methode in de regel stond. Juist de vergelijking is interessant: als
    # meer waarnemingen de spreiding niet verkleinen, moet een betere methode
    # het doen.
    for naam, v in sorted(vgl.items()):
        if isinstance(v, dict) and v.get("mediane_fout") is not None:
            delen.append(f"{naam} {v['mediane_fout'] * 100:.1f}% "
                         f"({v.get('aantal', 0)})")
    if not delen:
        # Hardop zeggen dat hij ontbreekt. Zonder deze regel lijkt het alsof de
        # vergelijking er gewoon niet toe doet, terwijl hij juist bepaalt of
        # een betere methode of meer waarnemingen de weg vooruit is.
        delen.append("geen vergelijking tussen methoden beschikbaar")
    else:
        # Erbij zetten welke methode wint, anders moet iedereen twee
        # percentages vergelijken om de conclusie te trekken.
        beste = min(((n, v["mediane_fout"]) for n, v in vgl.items()
                     if isinstance(v, dict) and v.get("mediane_fout") is not None),
                    key=lambda p: p[1], default=None)
        if beste:
            delen.append(f"beste: {beste[0]}")
    afwijking = abs(1 - (d.get("correctie") or 1)) * 100
    spreiding = (d.get("spreiding") or 0) * 100
    kb = d.get("kenmerken_beschikbaar") or {}
    bewijs = (f"geijkt op {aantal} panden: correctie {d.get('correctie'):.3f} "
              f"({afwijking:.0f}% stelselmatig), spreiding ±{spreiding:.1f}%"
              + (f"; mediane fout per methode: {', '.join(delen)}" if delen else "")
              + (f"; kenmerken uit {kb.get('straten', 0)} straten en "
                 f"{kb.get('buurten', 0)} buurten" if kb else ""))
    # Panden die ver van de mediaan liggen apart noemen. Die kunnen een
    # tikfout in de handmatige invoer zijn, en zo'n fout valt nergens op: de
    # spreiding gebruikt percentielen en de correctie is een mediaan.
    uit = d.get("uitschieters") or []
    if uit:
        bewijs += ("; nakijken: " + ", ".join(
            f"{u['adres']} ({u['afwijking_pct']:+d}%"
            + (", telt niet mee" if u.get("telt_niet_mee") else "") + ")"
            for u in uit[:3]))
    niet_mee = d.get("niet_meegeteld") or 0
    if niet_mee:
        bewijs += (f"; {niet_mee} waarde(n) buiten beschouwing gelaten als "
                   f"vermoedelijke tikfout")
    if spreiding > 7:
        return (LET_OP, bewijs,
                "De spreiding is nog te groot om op de schatting te varen; blijf "
                "de WOZ opzoeken bij panden die ertoe doen.")
    return (OK, bewijs + "; nauwkeurig genoeg om alleen grensgevallen op te "
            "zoeken", "")


def controle_logboek():
    """
    Houdt de brief bij wat er is verteld en wat niet?

    Ook een controle op de testrun-bescherming: komen er meer regels bij dan er
    echte brieven zijn, dan schrijft een oefenrun mee en loopt de echte brief
    straks nieuws mis.
    """
    d = _json("brief_logboek.json") or {}
    dagen = d.get("dagen") or []
    if not dagen:
        return (LET_OP, "nog geen logboek van behandelde onderwerpen",
                "Vanaf de eerste echte brief wordt hier bijgehouden wat er is "
                "verteld en wat bleef liggen. Een testrun schrijft hier niets.")
    laatste = max(x.get("datum", "") for x in dagen)
    blijven_liggen = sum(len(x.get("overgeslagen") or []) for x in dagen)
    return (OK, f"{len(dagen)} brieven vastgelegd, laatste {laatste}; "
            f"{blijven_liggen} onderwerpen bleven liggen", "")


def _groot_dus_geen_punten(brief):
    """
    De bewering dat het puntenstelsel niet opgaat omdat het pand groot is.

    Deze fout is deze week drie keer in drie formuleringen langsgekomen: "te
    groot om als één huishouden door te rekenen", "te groot voor het
    puntenstelsel" en op 9 oktober "met 158 vierkante meter wordt het pand niet
    als één huishouden doorgerekend in het puntenstelsel; die telling zegt hier
    dus weinig". Een patroon per formulering loopt altijd een formulering
    achter, dus wordt hier op de drie bestanddelen getoetst in plaats van op de
    woorden: een maat, het puntenstelsel, en een afwijzing. Staan die drie in
    één zin, dan is het deze fout.

    De losse zin "een kamerpand wordt niet als één huishouden doorgerekend" is
    wel waar, want onzelfstandige verhuur gaat per kamer. Daarom moet de maat
    erbij staan: de onwaarheid zit in het verband tussen de grootte en de
    telling, niet in de telling zelf.
    """
    maat = re.compile(r"te groot|groter dan|\d{2,4}\s*(?:m2|m²|vierkante meter)",
                      re.I)
    # "telling" hoort er bij: de bron schreef "een telling voor een
    # zelfstandige woning zegt hier weinig", zonder het woord puntenstelsel.
    stelsel = re.compile(r"puntenstelsel|woningwaarderingsstelsel|wwso?\b"
                         r"|puntentelling|punten\b|\btelling", re.I)
    afwijzing = re.compile(
        r"te groot"
        r"|zegt[^.]{0,30}(?:weinig|niets)"
        r"|niet van toepassing"
        r"|gaat (?:hier )?niet op"
        r"|telt[^.]{0,30}niet mee"
        r"|niet mee(?:geteld|gerekend)"
        r"|niet (?:als|per)[^.]{0,25}(?:huishouden|woning)[^.]{0,25}"
        r"(?:doorgerekend|gerekend|geteld)"
        r"|niet doorgerekend"
        r"|valt[^.]{0,20}buiten", re.I)
    # Niet op de puntkomma splitsen: de bewering liep juist over de puntkomma
    # heen, met de maat ervoor en de afwijzing erna.
    for zin in re.split(r"(?<=[.!?])\s+", brief):
        if maat.search(zin) and stelsel.search(zin) and afwijzing.search(zin):
            return zin.strip()
    return ""


def _snelle_route(brief):
    """
    De bewering dat een splitsingsroute snel is, op grond van de registratie.

    Op 9 oktober stond in de brief: "van besluit naar registratie zat hier maar
    één dag. Dat is het eerste bewijs dat deze route in de praktijk ook snel
    kan lopen." Die ene dag is echt, maar het is de laatste stap. Bij datzelfde
    pand, de Biezenstraat 110, zaten er 241 dagen tussen de gepubliceerde
    aanvraag en het gepubliceerde besluit, en 300 dagen volgens het dossier
    zelf. De route duurde dus acht tot tien maanden en alleen het afstempelen
    duurde een dag.

    Dit is dezelfde fout als de bezitsduur van 0,8 jaar: een administratieve
    datum wordt gelezen als een gebeurtenis in de werkelijkheid. Hij wordt hier
    over twee zinnen gezocht, want de bewering en het bewijs stonden niet in
    dezelfde zin. Noemt de brief de aanvraag erbij, dan is het verhaal compleet
    en slaat deze toets niet aan.
    """
    gap = re.compile(r"besluit", re.IGNORECASE)
    reg = re.compile(r"registratie|geregistreerd|\bBAG\b", re.IGNORECASE)
    snel = re.compile(r"\bsnel|\bvlot|korte doorlooptijd|in (?:een|één) dag"
                      r"|binnen (?:een|één) dag", re.IGNORECASE)
    kort = re.compile(r"\b(?:maar|slechts)?\s?(?:een|één|1|2|twee|3|drie)\s"
                      r"dag(?:en)?\b", re.IGNORECASE)
    volledig = re.compile(r"aanvraag|ingediend", re.IGNORECASE)
    zinnen = re.split(r"(?<=[.!?])\s+", brief)
    for i in range(len(zinnen)):
        venster = " ".join(zinnen[i:i + 2])
        if (gap.search(venster) and reg.search(venster)
                and snel.search(venster) and kort.search(venster)
                and not volledig.search(venster)):
            return venster.strip()
    return ""


# Beweringen die deze week in een brief stonden en die onwaar zijn. Elke regel
# is een patroon plus de reden. Een patroon mag ook een functie zijn die de
# gevonden tekst teruggeeft, voor een fout die in te veel formuleringen
# voorkomt om in één reguliere expressie te vatten. Dit is een lijst die
# groeit, en dat is het punt: een regel in de opdracht kan genegeerd worden,
# een toets op de verstuurde tekst niet. Vier keer is deze week geprobeerd een
# fout met een instructie te verhelpen en vier keer stond hij er de volgende
# dag weer.
VERZONNEN = (
    (_groot_dus_geen_punten,
     "Het woningwaarderingsstelsel kent geen bovengrens aan oppervlakte. Een "
     "grote woning krijgt juist veel punten en valt daarmee in de vrije "
     "sector, wat voor een verhuurder een voordeel is. De werkelijke reden dat "
     "opdelen loont is de gemeten groottepremie, en die staat in de gegevens."),
    (r"verkocht[,;:\s]+voor\s*€|verkoopprijs (?:was|is|bedroeg)"
     r"|ging(?: toen)? voor\s*€|opgebracht van\s*€"
     r"|verkocht[,;:\s]+voor\s*\d",
     "Wij kennen geen koopsommen; die staan alleen bij het Kadaster. Funda "
     "toont de laatste vraagprijs. Schrijf 'laatste vraagprijs €X'."),
    (r"aanvraag.{0,60}laat zien dat.{0,40}(?:werkt|kan|mag|mogelijk is)",
     "Een aanvraag om te legaliseren laat zien dat er zonder vergunning is "
     "gesplitst en dat de eigenaar dat rechtgetrokken wil hebben. Of het mag, "
     "blijkt pas uit het besluit; tot die tijd loopt de eigenaar het risico "
     "dat hij moet terugbouwen."),
    (r"het pand (?:is|heeft|meet) \d{2,4} m2 en heeft energielabel",
     "Oppervlakte en energielabel horen bij een adres en niet bij een pand. "
     "Staat er bij de gegevens 'op dit adres, niet van het hele pand', neem "
     "dat voorbehoud dan over."),
    (_snelle_route,
     "De tijd tussen een besluit en de BAG-registratie is de laatste stap en "
     "niet de doorlooptijd van de route. Die begint bij de aanvraag. Bij de "
     "Biezenstraat 110 was het verschil 1 dag, terwijl er 241 dagen tussen de "
     "gepubliceerde aanvraag en het besluit zaten en 300 dagen volgens het "
     "dossier. Noem de aanvraagdatum erbij; die staat per pand in het blok "
     "over de splitsingen die de BAG inmiddels telt."),
)


# De gegevensbestanden waarvan het aantal regels alleen mag groeien, met hoeveel
# procent krimp nog aanvaardbaar is. Deze bestanden bouwen jarenlang op uit
# handwerk en uit dagelijkse metingen; ze worden nooit kleiner behalve door een
# ongeluk. De versiecontrole ziet dit niet, want die slaat gegevensbestanden
# bewust over: die veranderen elke dag en zouden anders elke dag klagen.
OMVANG_PAD = "bestandsomvang.json"
OMVANG_LETTEN_OP = {
    "woz.txt": 10,
    "verkopen.txt": 5,
    "pandgeschiedenis.json": 5,
    "bekendmakingen_archief.json": 2,
    "kamervergunningen.json": 2,
    "verteld.json": 0,
}


def _omvang_nu():
    uit = {}
    for naam in OMVANG_LETTEN_OP:
        try:
            with open(naam, encoding="utf-8") as f:
                uit[naam] = sum(1 for r in f if r.strip()
                                and not r.lstrip().startswith("#"))
        except Exception:
            continue
    return uit


def controle_bestandsomvang():
    """
    Is een gegevensbestand plotseling veel kleiner geworden?

    Op 9 oktober stond er een verouderde woz.txt met zeven waarden in de map
    waaruit Mark de bestanden uploadt. Met "alle bestanden toevoegen" ging die
    over de 104 waarden die hij met de hand had opgezocht. Het rapport meldde
    niets: de versiecontrole slaat gegevensbestanden bewust over, en de
    WOZ-controle zag zeven leesbare regels en noemde dat OK. Alleen de ijking
    die van 104 naar 0 panden viel verraadde het.

    Deze controle houdt per bestand het aantal regels bij en vergelijkt met de
    vorige run. Krimp boven de drempel is FOUT, want deze bestanden groeien
    alleen: ze komen uit handwerk en uit dagelijkse metingen.
    """
    nu = _omvang_nu()
    vorige = _json(OMVANG_PAD) or {}
    gedaald = []
    for naam, aantal in nu.items():
        was = (vorige.get("bestanden") or {}).get(naam)
        if not was or aantal >= was:
            continue
        krimp = (was - aantal) / was * 100
        if krimp > OMVANG_LETTEN_OP[naam]:
            gedaald.append(f"{naam}: van {was} naar {aantal} regels "
                           f"({krimp:.0f}% minder)")
    # De stand van nu bewaren, ook als er iets fout is: anders blijft de melding
    # eeuwig staan nadat het is opgelost.
    try:
        with open(OMVANG_PAD, "w", encoding="utf-8") as f:
            json.dump({"datum": str(VANDAAG), "bestanden": nu}, f,
                      ensure_ascii=False, indent=1)
    except Exception:
        pass
    bewijs = ", ".join(f"{n}: {a}" for n, a in sorted(nu.items()))
    if not vorige:
        return (OK, bewijs + " (eerste meting, nog niets om mee te "
                "vergelijken)", "")
    if gedaald:
        return (FOUT, "; ".join(gedaald),
                "Deze bestanden groeien alleen. Een plotselinge krimp betekent "
                "dat er een oude versie over een nieuwe is gezet, bijvoorbeeld "
                "door alle bestanden uit een map te uploaden. Haal het bestand "
                "terug met 'git log -- <bestand>' en 'git checkout <commit> -- "
                "<bestand>'; elke run commit deze bestanden, dus de goede "
                "versie staat in de geschiedenis.")
    return (OK, bewijs, "")


def controle_verkocht_nog_in_aanbod():
    """
    Staat een pand dat verkocht is nog in de aanbodtabel?

    Op 9 oktober stond de St. Annastraat 165-B in dezelfde brief twee keer: in
    het verhaal als verkocht, en in de bijlage als te koop met elf dagen in de
    markt. Het bestand bevatte ook echt twee regels voor dat adres, een
    te-koopregel uit de attendering en een verkochtregel uit de geplakte lijst,
    en die kwamen in verschillende groepen terecht omdat de BAG-opzoeking bij
    de een lukte en bij de ander niet.

    Deze controle kijkt naar de uitkomst en niet naar de groepering. Heeft een
    adres een verkochtregel die nieuwer is dan zijn nieuwste te-koopregel, dan
    hoort het niet meer in de aanbodtabel van vandaag te staan.
    """
    nieuwste = {}
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                if regel.startswith("#"):
                    continue
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 5 or not v[0]:
                    continue
                status, datum = v[3].lower(), v[4]
                soort = ("verkocht" if "verkocht" in status
                         else "tekoop" if status.startswith(("te koop", "nieuw"))
                         else None)
                if not soort:
                    continue
                # Dezelfde sleutel als het model, met de afkortingen erin.
                # Met alleen letters en cijfers zou deze controle precies het
                # geval missen waarvoor hij is gemaakt: "Sint Annastraat" naast
                # "St. Annastraat".
                sleutel = _wozsleutel(v[0])
                rij = nieuwste.setdefault(sleutel, {"adres": v[0]})
                if datum > rij.get(soort, ""):
                    rij[soort] = datum
    except Exception:
        return (OK, "geen aanbodbestand om te toetsen", "")
    verkocht = [r for r in nieuwste.values()
                if r.get("verkocht") and r.get("tekoop")
                and r["verkocht"] > r["tekoop"]]
    if not verkocht:
        return (OK, "geen pand dat zowel verkocht is als te koop staat", "")

    # En dan: staat zo'n pand nog in de aanbodtabel van vandaag?
    try:
        pad = os.path.join("digests", f"{VANDAAG}-marktprijzen.md")
        with open(pad, encoding="utf-8") as f:
            aanbod = f.read().lower()
    except Exception:
        return (OK, f"{len(verkocht)} panden zijn na het aanbod verkocht; geen "
                f"aanbodtabel van vandaag om tegen te toetsen", "")
    fout = [r["adres"] for r in verkocht if r["adres"].lower() in aanbod]
    bewijs = (f"{len(verkocht)} panden hebben een verkoopregel die nieuwer is "
              f"dan hun te-koopregel")
    if not fout:
        return (OK, bewijs + "; geen van die panden staat nog in de "
                "aanbodtabel", "")
    return (FOUT, bewijs + f"; {len(fout)} staan nog in de aanbodtabel van "
            f"vandaag: " + ", ".join(fout[:4]),
            "Dan spreekt de brief zichzelf tegen: in het verhaal verkocht, in "
            "de bijlage te koop. De oorzaak zit in de groepering per pand in "
            "marktprijzen_bag.py; twee regels voor hetzelfde adres horen in "
            "dezelfde groep, ook als de BAG-opzoeking bij maar een van de twee "
            "lukte.")


# Welke opgeleverde teksten op bekende onwaarheden worden getoetst. Alleen
# teksten die wij zelf uit onze eigen gegevens schrijven. De publicaties en de
# bekendmakingen staan er bewust niet bij: daarin staat tekst van anderen, en
# "verkocht voor €X" in een nieuwsbericht is geen fout van ons.
EIGEN_TEKSTEN = (("-verhaal.md", "de brief"),
                 ("-marktprijzen.md", "de marktanalyse"),
                 ("-bijlage.md", "de bijlage"),
                 ("-dossiers.md", "de dossiers"))


def controle_verzonnen_beweringen():
    """
    Staan er beweringen in onze eigen teksten die we al eens fout bevonden?

    Een lijst van bekende onwaarheden, getoetst op de opgeleverde tekst. Dat is
    de enige plek waar het zeker werkt: de gegevens kunnen kloppen en de
    opdracht kan de regel bevatten, en toch staat het er. Deze week gebeurde
    dat met de bovengrens die het puntenstelsel niet heeft, met vraagprijzen
    die als koopsom werden gepresenteerd, en met een aanvraag die als bewijs
    van haalbaarheid werd gelezen.

    Niet alleen de brief wordt getoetst maar ook de teksten die de brief
    voeden, en dat is de les van 9 oktober. De bewering over het puntenstelsel
    bleek niet verzonnen in de brief: wws_indicatie() in marktprijzen_bag.py
    schreef hem in de marktanalyse en de brief nam hem braaf over. Drie dagen
    heb ik regels en patronen op de brief gezet terwijl de zin een niveau
    hoger werd gemaakt. Wie alleen de laatste tekst toetst, ziet de bron niet.
    """
    teksten = []
    try:
        bestanden = os.listdir("digests")
    except Exception:
        return (OK, "geen teksten om te toetsen", "")
    for achtervoegsel, wat in EIGEN_TEKSTEN:
        namen = sorted(n for n in bestanden if n.endswith(achtervoegsel))
        if not namen:
            continue
        try:
            with open(os.path.join("digests", namen[-1]), encoding="utf-8") as f:
                teksten.append((wat, " ".join(f.read().split())))
        except Exception:
            continue
    if not teksten:
        return (OK, "geen teksten om te toetsen", "")
    raak = []
    for patroon, waarom in VERZONNEN:
        for wat, tekst in teksten:
            if callable(patroon):
                gevonden = patroon(tekst)
            else:
                m = re.search(patroon, tekst, re.IGNORECASE)
                gevonden = m.group(0) if m else ""
            if gevonden:
                raak.append((wat, gevonden[:70], waarom))
                break        # eerste vindplaats is genoeg; die is de bron
    if not raak:
        return (OK, f"{len(VERZONNEN)} bekende onwaarheden getoetst op "
                f"{len(teksten)} teksten, geen ervan komt voor", "")
    return (FOUT,
            (f"{len(raak)} bekende onwaarheden" if len(raak) > 1
             else "1 bekende onwaarheid")
            + ": " + "; ".join(f'in {w}: "{z}"' for w, z, _ in raak),
            " ".join(r[2] for r in raak))


def controle_samenstelling():
    """
    Bewegen alle buurten dezelfde kant op, staat de waarschuwing dan in de brief?

    Op 9 oktober stonden vijf van de vijf buurten met een cijfer op +4,1% tot
    +7,8% in vier weken. Dat is op jaarbasis meer dan een verdubbeling, dus is
    het onze steekproef en niet de markt. De brief trok de omgekeerde
    conclusie: de ring koelt niet af. De waarschuwing die dat moet voorkomen
    was er wel, hij werd die ochtend gemaakt en daarna weggegooid, want de
    dagelijkse editie bouwt de regellijst erna opnieuw op.

    Dit is dezelfde fout als met het splitsingenblok: iets wordt gemaakt en
    bereikt de brief niet. De code toont dat niet, want de functie werkt. Deze
    controle toetst daarom de opgeleverde tekst, en gebruikt dezelfde functie
    die de waarschuwing maakt om te bepalen of hij er had moeten staan.

    TWEE SOORTEN TEKST, TWEE SOORTEN TOETS. De bijlage en de marktanalyse
    worden door ons gegenereerd; daar hoort de waarschuwing woordelijk in te
    staan. De brief wordt geschreven en hoort de dingen in eigen woorden te
    zeggen. Op 9 oktober stond er: "alle vijf de gemeten buurten dezelfde kant
    op, van +4,1% tot +7,8%. Dat is onze steekproef die verandert, niet de
    markt, dus die zet ik er niet tegenover." Dat is precies goed, en toch
    meldde deze controle een FOUT, want hij zocht de hoofdletters van het
    bronblok. Een controle die goed gedrag afstraft leert je het rapport
    negeren, dus kijkt hij in de brief nu naar de inhoud: noemt de brief de
    beweging, dan moet het voorbehoud er in welke woorden ook bij staan.
    """
    try:
        from marktprijzen_bag import samenstellingseffect
        with open("prijstrend.json", encoding="utf-8") as f:
            historie = json.load(f)
    except Exception as e:
        return (OK, f"niet te toetsen ({type(e).__name__})", "")
    melding = samenstellingseffect(historie)
    if not melding:
        return (OK, "de buurten bewegen niet allemaal dezelfde kant op; "
                "geen waarschuwing nodig", "")
    beweging = melding.split("**")[-1].split(" Dat is")[0].strip()[:160]

    def laatste(achtervoegsel):
        try:
            namen = sorted(n for n in os.listdir("digests")
                           if n.endswith(achtervoegsel))
            if not namen:
                return None
            with open(os.path.join("digests", namen[-1]), encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    # De gegenereerde teksten: woordelijk, want die schrijven wij.
    mist = []
    for achtervoegsel, wat in (("-bijlage.md", "de bijlage"),
                               ("-marktprijzen.md", "de marktanalyse")):
        tekst = laatste(achtervoegsel)
        if tekst is not None and "GEEN MARKTBEWEGING" not in tekst:
            mist.append(wat)

    # De brief: alleen streng als hij de beweging zelf noemt.
    brief = laatste("-verhaal.md") or ""
    noemt = bool(re.search(r"\ballemaal dezelfde kant|dezelfde kant op"
                           r"|alle (?:vijf|zes|vier)\b", brief, re.IGNORECASE))
    voorbehoud = bool(re.search(r"steekproef|samenstelling|GEEN MARKTBEWEGING"
                                r"|andere panden in de meting",
                                brief, re.IGNORECASE))
    if noemt and not voorbehoud:
        mist.append("de brief, die de beweging wel noemt maar zonder "
                    "voorbehoud")

    if not mist:
        hoe = ("de brief zegt het in eigen woorden" if voorbehoud
               else "de brief laat het erbuiten")
        return (OK, f"alle buurten bewegen dezelfde kant op, de waarschuwing "
                f"staat in de bijlage en {hoe}: {beweging}", "")
    return (FOUT,
            "alle buurten bewegen dezelfde kant op, maar de waarschuwing staat "
            f"niet in {' en '.join(mist)}: {beweging}",
            "Zonder dat voorbehoud leest pa de buurtcijfers als een "
            "marktbeweging, en dat zijn ze niet: er komen andere panden in de "
            "meting. De waarschuwing wordt gemaakt in samenstellingseffect() "
            "en moet vlak voor de return worden ingevoegd, anders gooit de "
            "opbouw van de dagelijkse editie hem weg.")


def controle_oude_verlaging():
    """
    Noemt de brief een prijsverlaging die niet van vandaag of gisteren is?

    Dit is een controle op de uitkomst en niet op de code, en dat is met
    opzet. De verlaging van de Palmstraat 40 van 6 oktober stond op 6, 7, 8 en
    9 oktober in de brief. Drie keer is er iets aan gedaan: een regel in de
    opdracht, een kolom met de datum, en het splitsen van de tabel in nieuws en
    achtergrond. Elke keer bleek er een plek te zijn die ik niet had gezien;
    de laatste was de samenvattingsregel "Grootste verlaging", met een eigen
    berekening zonder datum.

    Een controle op de brieftekst is immuun voor dat probleem. Hoeveel plekken
    er ook zijn die een prijswijziging kunnen melden, als er een oude verlaging
    in de brief staat, valt hij hier door de mand.
    """
    try:
        namen = sorted(n for n in os.listdir("digests")
                       if n.endswith("-verhaal.md"))
    except Exception:
        return (OK, "geen brief om te toetsen", "")
    if not namen:
        return (OK, "geen brief om te toetsen", "")
    try:
        with open(os.path.join("digests", namen[-1]), encoding="utf-8") as f:
            brief = " ".join(f.read().split())
    except Exception:
        return (OK, "brief niet te lezen", "")
    if not any(w in brief.lower() for w in
               ("omlaag", "verlaging", "verlaagd", "zakte", "gezakt")):
        return (OK, "de brief noemt geen prijsverlaging", "")

    # De datums van prijswijzigingen uit de pandgeschiedenis, net als het model
    # die gebruikt.
    datums = {}
    try:
        from pandlezer import laad
        for pand in (laad("pandgeschiedenis.json") or {}).values():
            if not isinstance(pand, dict):
                continue
            rij = [g["datum"] for g in (pand.get("gebeurtenissen") or [])
                   if g.get("soort") == "prijswijziging" and g.get("datum")]
            if rij:
                sleutel = "".join(c for c in (pand.get("adres") or "").lower()
                                  if c.isalnum())
                datums[sleutel] = max(rij)
    except Exception:
        return (OK, "geen pandgeschiedenis om tegen te toetsen", "")
    if not datums:
        return (OK, "nog geen prijswijzigingen in de pandgeschiedenis", "")

    try:
        import verteld
        adressen = verteld.adressen_uit(brief)
    except Exception:
        return (OK, "adressen niet uit de brief te halen", "")

    oud_genoemd = []
    for sleutel, zoals in adressen.items():
        op = datums.get(sleutel)
        if not op:
            continue
        try:
            dagen = (VANDAAG - dt.date.fromisoformat(op)).days
        except Exception:
            continue
        if dagen <= 1:
            continue
        # Staat dit adres in de buurt van het woord verlaging of omlaag?
        plek = brief.lower().find(zoals.lower())
        if plek == -1:
            continue
        omgeving = brief.lower()[max(0, plek - 200):plek + 200]
        if any(w in omgeving for w in ("omlaag", "verlaging", "verlaagd",
                                       "zakte", "gezakt")):
            oud_genoemd.append(f"{zoals} (gewijzigd op {op}, {dagen} dagen "
                               f"terug)")
    if oud_genoemd:
        return (FOUT, "de brief noemt een prijsverlaging die niet van vandaag "
                "of gisteren is: " + "; ".join(oud_genoemd[:4]),
                "Een oude verlaging hoort bij de achtergrond en niet bij het "
                "nieuws. Zoek in marktprijzen_bag.py naar elke plek die een "
                "prijswijziging meldt; er is er vermoedelijk een die niet op "
                "datum filtert.")
    return (OK, "elke genoemde prijsverlaging is van vandaag of gisteren", "")


def controle_briefherhaling():
    """
    Is de brief van vandaag werkelijk opnieuw geschreven?

    Op 8 oktober ging 's avonds dezelfde brief uit als die ochtend, woord voor
    woord, met de vier fouten die al waren gemeld. De oorzaak: brief_verhalend
    schreef bij mislukken geen bestand en gaf toch exitcode nul, en de workflow
    zag het verhaalbestand van de eerdere run van die dag staan en meldde
    "Brief gemaakt". Mislukken zag eruit als slagen.

    Twee dingen worden getoetst. De workflow legt vast of het bestand door deze
    run is geschreven. En los daarvan vergelijken we de brief van vandaag met de
    vorige: zijn ze letterlijk gelijk, dan is er iets fout, wat de oorzaak ook
    is. Dat tweede is de vangnetcontrole, want die werkt ook als de eerste om
    een onvoorziene reden niets zegt.
    """
    stand = _json("briefstand.json") or {}
    if stand.get("datum") == str(VANDAAG) and not stand.get("opnieuw_geschreven"):
        return (FOUT, f"de brief van {stand['datum']} is niet opnieuw "
                f"geschreven: {stand.get('reden') or 'onbekende reden'}",
                "Er is een oude brief verstuurd of klaargezet. Zoek in het "
                "logboek van de stap 'Verhalende brief maken' waarom het "
                "schrijven mislukte.")
    try:
        namen = sorted(n for n in os.listdir("digests")
                       if n.endswith("-verhaal.md"))
    except Exception:
        return (OK, "geen briefmap om te vergelijken", "")
    if len(namen) < 2:
        return (OK, f"{len(namen)} brieven, te weinig om te vergelijken", "")

    def inhoud(naam):
        try:
            with open(os.path.join("digests", naam), encoding="utf-8") as f:
                return " ".join(f.read().split())
        except Exception:
            return ""

    laatste, vorige = inhoud(namen[-1]), inhoud(namen[-2])
    if laatste and laatste == vorige:
        return (FOUT, f"{namen[-1]} is woord voor woord gelijk aan "
                f"{namen[-2]}",
                "Twee identieke brieven op rij betekent dat het schrijven is "
                "mislukt en een oude brief is hergebruikt. Zoek in het logboek "
                "van de stap 'Verhalende brief maken' op 'NIET opnieuw "
                "geschreven'.")
    if stand.get("datum") == str(VANDAAG):
        return (OK, f"de brief van vandaag is opnieuw geschreven en wijkt af "
                f"van {namen[-2]}", "")
    return (OK, f"{len(namen)} brieven, de laatste twee verschillen", "")


def controle_verteld():
    """
    Weet de brief wat pa al heeft gelezen?

    Dit is de controle op de reparatie van 8 oktober. Die dag stonden er drie
    dingen in de brief die pa al had gehad: een prijsverlaging van twee dagen
    eerder, twee vergunningen en een pand dat al weken te koop stond. De
    oorzaak was dat niets bijhield wat er eerder was verstuurd.

    Het geheugen wordt alleen door een echte brief bijgewerkt, nooit door een
    testrun. Groeit het dus niet terwijl er wel brieven uitgaan, dan is de
    herhaling terug zonder dat iemand het ziet, en dat is precies het soort
    stille uitval waar dit rapport voor bestaat.
    """
    d = _json("verteld.json") or {}
    onderwerpen = d.get("onderwerpen") or {}
    if not onderwerpen:
        return (LET_OP, "nog geen geheugen van verstuurde brieven",
                "Vanaf de eerste echte brief komt hier per pand en per "
                "bekendmaking te staan wanneer het is gemeld. Een testrun "
                "schrijft hier niets, dus na alleen handruns is dit leeg. "
                "Blijft het leeg na een geplande ochtendrun, kijk dan in het "
                "logboek van de briefstap naar 'Verteld:'.")
    laatst = max((r.get("laatst") or "") for r in onderwerpen.values())
    leeftijd = None
    try:
        leeftijd = (VANDAAG - dt.date.fromisoformat(laatst)).days
    except Exception:
        pass
    binnen = sum(1 for r in onderwerpen.values()
                 if (r.get("laatst") or "") >= str(VANDAAG - dt.timedelta(days=21)))
    herhaald = sum(1 for r in onderwerpen.values() if int(r.get("keer") or 1) > 1)
    bewijs = (f"{len(onderwerpen)} onderwerpen bekend, {binnen} in het venster "
              f"van drie weken, laatste brief {laatst}")
    if herhaald:
        bewijs += (f"; {herhaald} onderwerpen kwamen in meer dan een brief "
                   f"terug")
    if leeftijd is not None and leeftijd > 3:
        return (LET_OP, bewijs,
                f"De laatste echte brief is {leeftijd} dagen geleden "
                f"vastgelegd. Gaan er wel brieven uit, dan wordt dit geheugen "
                f"niet bijgewerkt en komt de herhaling terug. Zoek in het "
                f"logboek van de briefstap op 'Verteld:'.")
    return (OK, bewijs, "")


def controle_nieuwe_onderwerpen():
    """
    Onderwerpen die in het nieuws terugkomen en waar nog geen stuk over is.

    De signaalstap vindt ze en schrijft ze in een bestand; zonder deze controle
    blijft dat bestand liggen en gebeurt er niets mee. Dit is de schakel tussen
    "het script ziet een nieuw onderwerp" en "er komt een achtergrondstuk".
    """
    # De voorstellen staan als kopregel: "## term" of "## term (nieuw)". De
    # regels eronder zijn tellingen en citaten, geen onderwerpen; die haalde ik
    # eerst ook binnen, waardoor het rapport "_88 keer genoemd._" als onderwerp
    # toonde.
    voorstellen = []
    try:
        with open("onderwerpen_voorstel.md", encoding="utf-8") as f:
            for regel in f:
                regel = regel.rstrip()
                if not regel.startswith("## "):
                    continue
                term = regel[3:].replace("(nieuw)", "").strip()
                if term and len(term) < 80:
                    voorstellen.append(term)
    except Exception:
        pass
    gevolgd = _json("onderwerpen_volgen.json") or {}
    # Heeft de signaalstap ooit iets weggeschreven? Zo niet, dan draait hij
    # niet, en dan is "geen nieuwe onderwerpen" geen geruststelling maar een
    # stille fout. Dit is dezelfde soort melding als bij de mailstap: een nul
    # kan betekenen dat er niets was, of dat er niets gekeken is.
    sporen = [p for p in ("onderwerpen_voorstel.md", "onderwerpen_volgen.json",
                          "onderwerpen_gezien.json")
              if os.path.exists(p)]
    if not sporen:
        return (LET_OP, "de signaalstap heeft nog nooit iets weggeschreven",
                "Die stap draaide alleen in de weekeditie en is daardoor bij "
                "elke dagelijkse run overgeslagen. Hij loopt nu ook bij een "
                "handmatige start mee.")
    if not voorstellen and not gevolgd:
        return (OK, "geen nieuwe onderwerpen voorgesteld", "")
    bewijs = (f"{len(voorstellen)} voorgestelde onderwerpen, "
              f"{len(gevolgd)} gevolgd")
    if voorstellen:
        return (LET_OP, bewijs + ": " + "; ".join(voorstellen[:4]),
                "Deze komen terug in het nieuws en hebben nog geen "
                "achtergrondstuk. Bespreek ze, dan kan er een stuk met bronnen "
                "bij; het script schrijft die niet zelf, want juridische tekst "
                "zonder gecontroleerde bron is precies wat we niet willen.")
    return (OK, bewijs, "")


def controle_achtergronddekking():
    """
    Heeft elk soort bekendmaking een achtergrondstuk dat de inhoud uitlegt?

    Een melding constateren is iets anders dan uitleggen wat er dan van je
    gevraagd wordt. Komt er een soort voorbij waarvoor geen stuk klaarligt, dan
    blijft het bij de constatering.
    """
    try:
        from bekendmakingen_archief import SIGNAALWOORDEN
        from bronnen import ACHTERGROND, ACHTERGROND_TREFWOORDEN
    except Exception as e:
        return (LET_OP, "kon de onderwerpen niet vergelijken", str(e)[:120])
    alle_trefwoorden = " ".join(
        " ".join(v) for v in ACHTERGROND_TREFWOORDEN.values()).lower()
    titels = " ".join(t for t, _ in ACHTERGROND).lower()
    zonder = []
    for soort, woorden in SIGNAALWOORDEN.items():
        raak = any(w.lower()[:8] in alle_trefwoorden or w.lower()[:8] in titels
                   for w in [soort] + list(woorden))
        if not raak:
            zonder.append(soort)
    bewijs = (f"{len(ACHTERGROND)} achtergrondstukken voor "
              f"{len(SIGNAALWOORDEN)} soorten bekendmakingen")
    if zonder:
        return (LET_OP, bewijs + f"; geen stuk voor: {', '.join(sorted(zonder))}",
                "Bij die soorten blijft het bij constateren dat er iets is "
                "gemeld, zonder uit te leggen wat de regel inhoudt.")
    return (OK, bewijs + "; elk soort heeft een stuk", "")


def controle_vve():
    """Van hoeveel appartementen in een complex kennen we de VvE-bijdrage?"""
    try:
        from marktprijzen_bag import lees_vve_kosten
        tabel = lees_vve_kosten()
    except Exception as e:
        return (LET_OP, "VvE-bestand niet te lezen", str(e)[:120])
    if not tabel:
        return (LET_OP, "geen enkele VvE-bijdrage ingevoerd",
                "Appartementen in een complex worden nu doorgerekend alsof er "
                "geen VvE is; de richtprijs valt daardoor te hoog uit. Zet de "
                "maandbijdrage in vve_kosten.txt, een regel per adres.")
    bedragen = sorted(tabel.values())
    return (OK, f"{len(tabel)} panden met een VvE-bijdrage, mediaan "
            f"€{bedragen[len(bedragen)//2]:.2f} per maand", "")


def controle_opnieuw_aangeboden():
    """
    Woningen die vaker te huur zijn aangeboden, en tegen welke prijs.

    We horen nooit wanneer een woning verhuurd is. Maar komt hetzelfde adres
    later terug voor minder geld, dan is dat het bewijs dat de eerste vraagprijs
    niet werd betaald. Komt hij terug voor meer, dan is het een normale mutatie
    in een krappe markt. Dat onderscheid is het enige signaal dat we hebben
    over wat er werkelijk wordt betaald.
    """
    per_adres = {}
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 6 or not v[3].lower().startswith("te huur"):
                    continue
                try:
                    prijs = int(v[2])
                except ValueError:
                    continue
                per_adres.setdefault(v[0].lower(), []).append((v[4], prijs))
    except Exception:
        return (LET_OP, "huuraanbod niet te lezen", "Staat verkopen.txt er wel?")
    herhaald = {a: sorted(p) for a, p in per_adres.items() if len(p) > 1}
    if not herhaald:
        return (OK, "geen enkel adres twee keer aangeboden", "")
    omlaag, omhoog = [], []
    for adres, reeks in herhaald.items():
        eerst, laatst = reeks[0][1], reeks[-1][1]
        if laatst < eerst * 0.97:
            omlaag.append(f"{adres} van €{eerst} naar €{laatst}")
        elif laatst > eerst * 1.03:
            omhoog.append(adres)
    bewijs = (f"{len(herhaald)} adressen vaker aangeboden: {len(omlaag)} voor "
              f"minder, {len(omhoog)} voor meer")
    if omlaag:
        return (OK, bewijs + "; lager bij: " + "; ".join(omlaag[:3]),
                "")
    return (OK, bewijs, "")


def controle_wozbestand():
    """Of elke regel in het WOZ-bestand te lezen is."""
    goed = slecht = open_regels = benaderingen = zonder_woz = 0
    voorbeelden = []
    # "geen" in het bedragveld betekent: opgezocht, het loket geeft niets. Dat
    # is geen openstaand werk en ook geen fout, maar een eigen toestand. Werd
    # dat bij "nog in te vullen" geteld, dan leek er meer werk open te staan
    # dan er is, en dat is precies het getal waarop Mark afgaat.
    geen_markering = ("geen", "-", "--", "nvt", "n.v.t", "nvt.",
                      "niet beschikbaar", "onbekend", "x")
    try:
        with open("woz.txt", encoding="utf-8") as f:
            for nummer, regel in enumerate(f, 1):
                kaal = regel.split("#", 1)[0].strip()
                if not kaal:
                    continue
                delen = [d.strip() for d in kaal.split("|")]
                if len(delen) < 2 or not delen[0]:
                    slecht += 1
                    if len(voorbeelden) < 3:
                        voorbeelden.append(f"regel {nummer}")
                    continue
                if delen[1].lstrip().startswith(("~", "ca", "±")):
                    benaderingen += 1
                cijfers = "".join(c for c in delen[1] if c.isdigit())
                if delen[1].strip().lower().rstrip(".") in [
                        m.rstrip(".") for m in geen_markering]:
                    zonder_woz += 1
                elif not cijfers:
                    # Leeg bedrag is geen fout: dat is een regel die nog moet
                    # worden ingevuld.
                    open_regels += 1
                elif int(cijfers) < 10000:
                    slecht += 1
                    if len(voorbeelden) < 3:
                        voorbeelden.append(f"regel {nummer}: {delen[0]}")
                else:
                    goed += 1
    except FileNotFoundError:
        return (OK, "geen WOZ-bestand", "")
    # Hoeveel panden uit het aanbod nog geen WOZ hebben. Staat dat op nul,
    # dan vult de werklijst niet aan omdat er niets te kiezen valt, en niet
    # omdat er iets stuk is.
    te_doen = 0
    try:
        bekend = set()
        with open("woz.txt", encoding="utf-8") as f2:
            for r in f2:
                k = r.split("#", 1)[0].split("|", 1)[0].strip().lower()
                if k:
                    bekend.add("".join(c for c in k if c.isalnum()))
        with open("verkopen.txt", encoding="utf-8") as f2:
            for r in f2:
                if r.startswith("#"):
                    continue
                v = [x.strip() for x in r.split("|")]
                if len(v) < 4 or not v[3].lower().startswith(("te koop", "nieuw")):
                    continue
                if "".join(c for c in v[0].lower() if c.isalnum()) not in bekend:
                    te_doen += 1
    except Exception:
        te_doen = -1
    bewijs = f"{goed} bruikbare regels, {open_regels} nog in te vullen"
    if zonder_woz:
        bewijs += (f", {zonder_woz} opgezocht zonder dat het loket een waarde "
                   f"geeft")
    if te_doen == 0:
        bewijs += ("; geen nieuwe kandidaten, elk pand in het aanbod heeft al "
                   "een WOZ of staat al op de lijst")
    elif te_doen > 0:
        bewijs += f"; {te_doen} panden in het aanbod nog zonder WOZ"
    if benaderingen:
        bewijs += (f", {benaderingen} overgenomen van een ander pand (die "
                   f"tellen niet mee in de ijking)")
    if slecht:
        return (LET_OP, bewijs + f", {slecht} niet te lezen: "
                + ", ".join(voorbeelden),
                "Formaat per regel: adres | bedrag | jaar. Staat er tekst in "
                "het bedragveld, zet die dan achter een # aan het eind van de "
                "regel; dan blijft hij leesbaar en gaat de notitie niet "
                "verloren.")
    return (OK, bewijs, "")


def _wozsleutel(adres):
    """
    Dezelfde sleutel als het model gebruikt.

    Dit stond hier eerder anders: de controle vergeleek met een simpele
    sleutel zonder de afkortingen, terwijl het model "sint" en "st." gelijk
    maakt. Een controle die een andere sleutel gebruikt dan het ding dat hij
    controleert, meldt verschillen die er niet zijn. Precies dat is hier
    gebeurd.
    """
    a = (adres or "").lower()
    a = a.replace("professor ", "prof").replace("prof. ", "prof")
    a = a.replace("burgemeester ", "burg").replace("burg. ", "burg")
    a = a.replace("sint ", "st").replace("st. ", "st")
    return re.sub(r"[^a-z0-9]", "", a)


def controle_woz_zonder_pand():
    """
    WOZ-regels waarvan het adres bij geen enkel pand hoort dat wij volgen.

    Drie uitkomsten, en alleen de laatste is werk:

    1. Het adres hoort bij een pand. Goed.
    2. Het adres heeft een letter en zonder die letter is er wel een pand.
       Dan landt de waarde sinds 8 oktober via de letterroute in woz_van, als
       overgenomen waarde die niet in de ijking meedoet. Geen werk meer, maar
       wel iets om te melden, want die route hoort zichtbaar te zijn.
    3. Er is helemaal geen pand met dat adres. Dan is het een waarde die we
       bewaren voor later; dat is geen fout. Zo'n pand kan uit het aanbod zijn
       verdwenen nadat het werd opgezocht.
    """
    adressen = set()
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                if regel.startswith("#"):
                    continue
                naam = regel.split("|", 1)[0].strip()
                if naam:
                    adressen.add(_wozsleutel(naam))
    except Exception:
        return (OK, "geen aanbodbestand om tegen te toetsen", "")
    via_letter, bewaard = [], []
    try:
        with open("woz.txt", encoding="utf-8") as f:
            for regel in f:
                kaal = regel.split("#", 1)[0].strip()
                if not kaal or kaal.startswith("#"):
                    continue
                delen = [d.strip() for d in kaal.split("|")]
                if len(delen) < 2 or not delen[0]:
                    continue
                if not any(c.isdigit() for c in delen[1]):
                    continue
                sleutel = _wozsleutel(delen[0])
                if sleutel in adressen:
                    continue
                zonder = re.sub(r"[a-z]+$", "", sleutel)
                if (zonder and zonder != sleutel and zonder[-1].isdigit()
                        and zonder in adressen):
                    via_letter.append(delen[0])
                else:
                    bewaard.append(delen[0])
    except FileNotFoundError:
        return (OK, "geen WOZ-bestand", "")
    delen_bewijs = []
    if via_letter:
        delen_bewijs.append(f"{len(via_letter)} landen via de letterroute "
                            f"als overgenomen waarde: "
                            f"{', '.join(via_letter[:4])}")
    if bewaard:
        delen_bewijs.append(f"{len(bewaard)} horen bij geen pand in het "
                            f"aanbod en zijn bewaard voor later: "
                            f"{', '.join(bewaard[:4])}")
    if not delen_bewijs:
        return (OK, "elke ingevulde WOZ hoort bij een pand dat we volgen", "")
    return (OK, "; ".join(delen_bewijs),
            "De letterroute vult een pand aan met de waarde van hetzelfde "
            "nummer met een letter, bijvoorbeeld 56-A bij 56. Die waarde doet "
            "mee in de doorrekening maar niet in de ijking, want het kunnen "
            "twee woningen in hetzelfde gebouw zijn. Wil je hem als eigen "
            "meting, zoek dan het adres op zoals het in het aanbod staat.")


def controle_nieuwbouw():
    """
    Nieuwbouwprojecten die apart worden gehouden.

    Een prijs vrij op naam is niet vergelijkbaar met kosten koper, en een
    bouwnummer is geen bestaande woning. Zeven stadswoningen van een project
    tegen €733.000 voor 153 m2 zouden de mediaan per m2 en de groottepremie
    verschuiven zonder dat er iets in de bestaande voorraad is gebeurd.
    """
    aantal = 0
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                if regel.startswith("#"):
                    continue
                v = [x.strip() for x in regel.split("|")]
                if len(v) > 3 and v[3].lower().startswith("project"):
                    aantal += 1
    except Exception:
        return (OK, "geen aanbodbestand om te tellen", "")
    if not aantal:
        return (OK, "geen nieuwbouwprojecten in het aanbodbestand", "")
    return (OK, f"{aantal} nieuwbouwregels apart gehouden; die tellen niet mee "
            f"in de mediaan per m2, de groottepremie of de aanbodreeks", "")


def controle_adressen_met_meerdere_maten():
    """
    Adressen waaronder meerdere woningen schuilgaan.

    Bij de St. Annastraat 30 staan een woning van 31 m2 en een van 23 m2 onder
    hetzelfde adres, allebei uit de geplakte lijst. Het huisnummer-achtervoegsel
    is bij het plakken verloren gegaan, en dat valt niet terug te rekenen: de
    oppervlakte is het enige dat ze onderscheidt. Zulke adressen delen een
    dossier en een geschiedenis, en dat vertekent elke doorrekening op dat pand.
    """
    per_adres = {}
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                if regel.startswith("#"):
                    continue
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 7 or not v[6]:
                    continue
                # Alleen koopregels met een huisnummer. De huurwaarnemingen van
                # Pararius en Kamernet dragen alleen een straatnaam, en dan zijn
                # twee verschillende maten juist normaal: dat zijn twee woningen
                # in dezelfde straat. Zonder deze regel meldde de controle
                # "graafseweg (13, 20, 21, 22 m2)" als probleem.
                if "huur" in v[3].lower():
                    continue
                if not any(c.isdigit() for c in v[0]):
                    continue
                try:
                    opp = int(v[6])
                except ValueError:
                    continue
                per_adres.setdefault(v[0].lower(), set()).add(opp)
    except Exception:
        return (OK, "geen aanbodbestand om te toetsen", "")
    # Meer dan tien procent verschil: dan is het geen meetverschil maar een
    # andere woning.
    verdacht = {a: sorted(m) for a, m in per_adres.items()
                if len(m) > 1 and max(m) > min(m) * 1.10}
    if not verdacht:
        return (OK, "geen adres met twee verschillende woningmaten", "")
    namen = ", ".join(f"{a} ({', '.join(str(x) for x in m)} m2)"
                      for a, m in sorted(verdacht.items())[:3])
    return (LET_OP, f"{len(verdacht)} adressen met meerdere woningmaten: {namen}",
            "Waarschijnlijk is het huisnummer-achtervoegsel bij het plakken "
            "weggevallen. Zoek het juiste adres op en pas de regel aan, anders "
            "delen twee woningen een dossier.")


def controle_gemeubileerd():
    """Gemeubileerde advertenties: apart bewaard, niet in de mediaan."""
    aantal = 0
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) > 3 and "gemeubileerd" in v[3].lower():
                    aantal += 1
    except Exception:
        return (OK, "geen huurbestand om te tellen", "")
    if not aantal:
        return (OK, "nog geen gemeubileerde advertenties bewaard", "")
    return (OK, f"{aantal} gemeubileerde advertenties apart bewaard; de opslag "
            f"wordt binnen hetzelfde huurregime vergeleken, want een hoge huur "
            f"komt eerder door de vrije sector dan door het meubilair", "")


def controle_huurdekking():
    """Hoeveel van het huuraanbod elders we zelf al zien."""
    try:
        from huur_dekking import lees_elders, lees_eigen, sleutel
        elders = lees_elders()
    except Exception as e:
        return (LET_OP, "dekkingscontrole niet uit te voeren", str(e)[:100])
    if not elders:
        return (OK, "geen steekproef geplakt in huur_elders.txt", "")
    per_sleutel, straten = lees_eigen()
    raak = sum(1 for a in elders
               if a["sleutel"] in per_sleutel or sleutel(a["straat"]) in straten)
    deel = raak / len(elders) * 100
    bewijs = (f"steekproef van {len(elders)} adressen elders: {raak} kennen we "
              f"al ({deel:.0f}%)")
    if deel < 60:
        return (LET_OP, bewijs,
                "We missen het grootste deel van het huuraanbod. Een extra "
                "bron erbij weegt dan zwaarder dan welke verfijning van de "
                "berekening ook.")
    return (OK, bewijs, "")


def controle_aanbodreeks():
    """De instroom van nieuw aanbod, en het uitpondsignaal."""
    reeks = _json("aanbod_reeks.json") or {}
    if len(reeks) < 2:
        return (LET_OP, f"{len(reeks)} dagen in de reeks",
                "Een golf is pas te zien na een paar weken meten. Deze reeks "
                "begint nu te lopen.")
    try:
        from aanbod_reeks import samenvatting
        weken = samenvatting(reeks)
    except Exception as e:
        return (LET_OP, "reeks niet samen te vatten", str(e)[:100])
    delen = [f"{w}: {d['nieuw_te_koop']} koop, {d['nieuw_te_huur']} huur"
             + (f", {d['uitpond']} uitpond" if d.get("uitpond") else "")
             for w, d in sorted(weken.items())]
    uitpond = sum(d.get("uitpond", 0) for d in weken.values())
    bewijs = f"{len(reeks)} dagen gemeten; " + "; ".join(delen[-3:])
    if uitpond:
        return (OK, bewijs + f". In beeld: {uitpond} nieuw aangeboden panden "
                f"die bij ons als kamerverhuur bekend staan", "")
    return (OK, bewijs, "")


def controle_verkooptijd():
    """De bovengrens op de verkooptijd, uit onze eigen waarnemingen."""
    d = _json("verkooptijd.json") or {}
    if not d.get("aantal"):
        return (OK, "nog geen pand dat wij eerst te koop en daarna in "
                "onderhandeling of verkocht "
                "zagen; dat begint te lopen nu de verkochtmeldingen binnenkomen",
                "")
    deel = (f"{d['aantal']} panden van te koop naar onder bod of verkocht "
            f"gezien; mediaan hoogstens {d.get('mediaan_hoogstens_dagen')} "
            f"dagen")
    if d.get("aantal_in_onderhandeling"):
        deel += (f"; alleen in onderhandeling: "
                 f"{d['aantal_in_onderhandeling']} panden, mediaan hoogstens "
                 f"{d['mediaan_tot_onderhandeling']} dagen. Dat is de scherpste "
                 f"maat, want daar legt de koper zich vast")
    return (OK, deel + ". Een bovengrens uit twee eigen waarnemingen, geen "
            "schatting: de werkelijke tijd is korter of gelijk", "")


def controle_briefvoet():
    """
    Staat er in de verstuurde mail dat de brief machinewerk is?

    De brief spreekt in de eerste persoon, dus de ontvanger leest een analyse
    van zijn zoon. In oktober stonden er vijf beweringen in die onwaar waren.
    De voet verandert daar niets aan; hij verandert hoe de brief wordt gelezen,
    en dat is de enige maatregel die ook werkt tegen de fouten die we nog niet
    kennen. Daarom is het niet genoeg dat de regel bestaat: hij moet in de mail
    staan die eruit gaat. Dat is precies het soort "gemaakt maar niet
    opgeleverd" dat deze week zes keer voorkwam.

    DE VALKUIL DIE EEN LOSSE BEOORDELAAR HIER VOND. De eerste opzet las het
    nieuwste bestand dat op -mail.html eindigt. Dat is niet hetzelfde als de
    mail van vandaag: mislukt de samenvoegstap, dan staat die van gisteren er
    nog en meldt de toets OK over een mail die niemand heeft gekregen, terwijl
    de werkelijke verzending via brief.html liep. Daarom kijkt hij nu naar de
    datum van vandaag en naar beide verzendpaden.
    """
    try:
        from briefvoet import TOETSTEKST
    except Exception as e:
        return (FOUT, f"briefvoet.py is niet te lezen ({type(e).__name__})",
                "Zonder dat bestand gaat de brief zonder voet de deur uit.")
    vandaag = dt.date.today().isoformat()
    # Beide paden waarlangs er werkelijk een brief wordt verstuurd. mail.html
    # is het gewone pad; brief.html is het pad "Mail versturen zonder verhaal".
    paden = [(f"digests/{vandaag}-mail.html", "de mail"),
             (f"digests/{vandaag}-brief.html", "de brief zonder verhaal")]
    gevonden = [(pad, wat) for pad, wat in paden if os.path.exists(pad)]
    if not gevonden:
        return (OK, "geen brief van vandaag om te toetsen", "")
    mist = []
    for pad, wat in gevonden:
        try:
            with open(pad, encoding="utf-8") as f:
                if TOETSTEKST not in f.read():
                    mist.append(wat)
        except Exception as e:
            mist.append(f"{wat} ({type(e).__name__})")
    if not mist:
        return (OK, "de voet staat boven "
                + " en ".join(w for _, w in gevonden), "")
    return (FOUT, "de voet staat NIET in " + " en ".join(mist),
            "Die tekst gaat dan uit zonder dat er in staat dat de tekst door "
            "een taalmodel is geschreven. De stap 'Brief en bijlage "
            "samenvoegen tot een HTML' zet GEEN_VOET=1 als het invoegen "
            "mislukt, en dan gaat de kopie naar pa er vanzelf af; staat die "
            "melding er niet, dan is er iets anders aan de hand.")


def controle_voorraad():
    """
    Hoe ver de voorraad van de hele ring is gevuld.

    Dit telt niet de panden die te koop staan maar de woningvoorraad zelf, met
    oppervlakte en energielabel. De labels gaan per adres bij EP-Online, dus
    dat is een achterstand die per run een stuk opschuift; deze regel maakt
    zichtbaar of dat werkelijk gebeurt. Blijft het aantal twee runs lang
    gelijk, dan loopt de stap ergens op vast.
    """
    d = _json("voorraad.json") or {}
    adressen = d.get("adressen") or {}
    if not adressen:
        inv = _json("buurtinventaris.json") or {}
        postcodes = (inv.get("totaal") or {}).get("postcodes")
        if not postcodes:
            return (OK, "voorraad nog niet opgehaald en nog geen postcodes om "
                    "het mee te doen", "")
        return (LET_OP, f"voorraad nog leeg terwijl er {postcodes} postcodes "
                f"klaarstaan",
                "De stap 'Oppervlakte en gebruiksdoel van de hele voorraad' "
                "draait in de weekeditie en bij een handmatige start. Levert "
                "hij niets op, kijk dan of BAG_API_KEY nog geldig is.")
    met_opp = sum(1 for r in adressen.values() if r.get("oppervlakte"))
    met_label = sum(1 for r in adressen.values() if r.get("label"))
    nog = sum(1 for r in adressen.values()
              if not r.get("label") and not r.get("label_gezien"))
    ronde = d.get("laatste_ronde") or {}
    labels = ronde.get("labels") or {}
    bewijs = (f"{len(adressen)} woningen in de ring, {met_opp} met "
              f"oppervlakte, {met_label} met label; nog {nog} adressen te "
              f"vragen")
    if labels.get("gevraagd"):
        bewijs += (f"; laatste ronde {labels['gevraagd']} gevraagd, "
                   f"{labels.get('label_gevonden', 0)} labels gevonden")
    for fase in ("bag", "labels"):
        fouten = (ronde.get(fase) or {}).get("fouten") or 0
        if fouten:
            laatste = (ronde.get(fase) or {}).get("laatste_fout") or ""
            return (LET_OP, bewijs + f"; {fouten} fouten in fase {fase}"
                    + (f", laatste: {laatste}" if laatste else ""),
                    "Bij een geweigerde sleutel of een 429 stopt de fase "
                    "meteen en gaat hij de volgende run verder.")
    return (OK, bewijs, "")


def controle_doorlooptijden():
    """Wat de reeks per pand oplevert: verkooptijd, bezitsduur, prijsgroei."""
    d = _json("doorlooptijden.json") or {}
    if not d or not d.get("verkooptijd_aantal"):
        return (LET_OP, "nog geen doorlooptijden te berekenen",
                "Hiervoor zijn per pand twee gebeurtenissen nodig; dat groeit "
                "met elke ronde verkoopdatums.")
    minimum = d.get("minimum_paren", 10)
    delen = []
    if d.get("verkooptijd_mediaan_dagen"):
        delen.append(f"mediane verkooptijd {d['verkooptijd_mediaan_dagen']} "
                     f"dagen ({d['verkooptijd_aantal']} panden, bovengrens)")

    # Bezitsduur en prijsgroei rusten op twee verkopen van hetzelfde pand, en
    # dus op echte verkoopdatums. De 505 geplakte verkopen hebben die niet: hun
    # datum is de dag dat de lijst werd geplakt. Zolang die meededen stond hier
    # een mediane bezitsduur van 0,8 jaar, en dat is geen bezitsduur maar de
    # tijd tot onze eigen plakronde. Nu alleen echte datums meetellen, meldt
    # dit wat er werkelijk te meten is, en niets zodra dat te weinig is.
    aantal_b = d.get("bezitsduur_aantal", 0)
    if d.get("bezitsduur_mediaan_jaar"):
        bij_benadering = d.get("bezitsduur_bij_benadering", 0)
        delen.append(f"mediane bezitsduur {d['bezitsduur_mediaan_jaar']} jaar "
                     f"({aantal_b} paren met een echte verkoopdatum"
                     + (f", waarvan {bij_benadering} op een jaar bij "
                        f"benadering" if bij_benadering else "") + ")")
    else:
        delen.append(f"bezitsduur nog niet te meten: {aantal_b} paren met een "
                     f"echte verkoopdatum, minimaal {minimum} nodig")

    aantal_p = d.get("prijsgroei_aantal", 0)
    if d.get("prijsgroei_mediaan_pct"):
        delen.append(f"prijsgroei per pand {d['prijsgroei_mediaan_pct']}% per "
                     f"jaar ({aantal_p} paren, vraagprijzen en geen koopsommen)")
    else:
        delen.append(f"prijsgroei per pand nog niet te meten: {aantal_p} paren, "
                     f"minimaal {minimum} nodig")
    return (OK, "; ".join(delen), "")


def controle_verkoopdatums():
    """Hoeveel panden een indicatie van hun verkoopdatum hebben."""
    d = _json("verkoopdatums_model.json") or {}
    if not d:
        return (OK, "geen verkoopdatums opgehaald; die stap staat uit omdat "
                "het webzoeken per pand te duur was, en wordt vanuit de chat "
                "aangevuld", "")
    hoog = sum(1 for p in d.values() if p.get("zeker") == "hoog")
    verdacht = sum(1 for p in d.values() if p.get("waarschuwing"))
    met_verkoop = sum(1 for p in d.values() if p.get("verkocht_op"))
    met_aanbod = sum(1 for p in d.values() if p.get("te_koop_vanaf"))
    bewijs = (f"{len(d)} panden met een indicatie: {met_verkoop} met een "
              f"verkoopdatum, {met_aanbod} met een plaatsingsdatum, {hoog} met "
              f"hoge zekerheid, {verdacht} met een waarschuwing dat het om een "
              f"andere advertentie gaat; indicaties met bronvermelding, geen "
              f"Kadastercijfers")
    if verdacht > len(d) * 0.3:
        return (LET_OP, bewijs,
                "Meer dan een derde wijkt af van onze eigen vraagprijs; het "
                "model vindt dan oude advertenties.")
    return (OK, bewijs, "")


def controle_splitsingen():
    """Panden waarvan de BAG laat zien dat ze werkelijk zijn opgedeeld."""
    d = _json("splitsingen.json") or {}
    ger = d.get("gerealiseerd") or []
    zonder = d.get("zonder_bekende_vergunning") or []
    vergund = d.get("vergund_maar_niets_gebeurd") or []
    if not (ger or zonder or vergund):
        return (OK, "nog geen voltooide splitsing gezien; het aantal woningen "
                "per pand wordt pas sinds eind september gemeten", "")
    delen = [f"{len(ger)} gerealiseerd"]
    if d.get("mediaan_dagen_besluit_tot_bag"):
        delen.append(f"mediaan {d['mediaan_dagen_besluit_tot_bag']} dagen van "
                     f"besluit tot registratie ({d.get('aantal_looptijden')})")
    if zonder:
        delen.append(f"{len(zonder)} zonder bekende vergunning")
    if vergund:
        delen.append(f"{len(vergund)} vergund maar na een jaar nog niets in "
                     f"de BAG")
    # En komt het ook in een brief terecht? Het blok werd elke dag gemaakt en
    # door niets gelezen, omdat de stap die het schreef na de stap liep die het
    # moest opnemen. Dat is tien dagen onzichtbaar geweest: het bestand bestond,
    # het rapport meldde het, en in geen enkele brief stond het. Een bron die
    # niets oplevert moet zichzelf melden, ook als het bestand er is.
    if ger or zonder:
        pad = os.path.join("digests", f"{VANDAAG}-splitsingen.md")
        try:
            leeg = os.path.getsize(pad) < 20
        except Exception:
            leeg = True
        if leeg:
            return (LET_OP, "; ".join(delen) + "; maar er is geen tekstblok "
                    f"voor vandaag, dus de brief heeft dit niet gezien",
                    "Het bestand digests/<datum>-splitsingen.md ontbreekt of is "
                    "leeg. Dan maakt splitsing_voltooid.py wel de json maar "
                    "komt de tekst nergens terecht. Controleer dat de stap "
                    "'Voltooide splitsingen uit de BAG' vóór 'Brief "
                    "samenstellen' staat.")
        delen.append("en het tekstblok van vandaag staat er")
    return (OK, "; ".join(delen), "")


def controle_grootte_premie():
    """De gemeten premie van kleine eenheden, de basis van elke splitsingscase."""
    d = _json("grootte_premie.json") or {}
    klassen = d.get("klassen") or {}
    if not klassen:
        return (LET_OP, "nog geen groottepremie gemeten",
                "Deze rekent elke run opnieuw uit wat er bekend is.")
    met_getal = {n: r for n, r in klassen.items() if r.get("premie")}
    if len(met_getal) < 3:
        return (LET_OP,
                f"{d.get('waarnemingen', 0)} waarnemingen, maar maar "
                f"{len(met_getal)} grootteklassen met genoeg panden",
                "Met minder dan drie klassen is er geen curve.")
    delen = ", ".join(f"{n}: {r['premie']} ({r['aantal']})"
                      for n, r in met_getal.items())
    return (OK, f"{d.get('waarnemingen', 0)} waarnemingen, "
            f"{d.get('buurten_met_ijkpunt', 0)} buurten met eigen ijkpunt; "
            f"{delen}", "")


def controle_aanbodprofiel():
    """Het profiel van het nieuwe aanbod, voor de weekeditie."""
    p = _json("aanbodprofiel.json") or {}
    nu = p.get("nu")
    if not nu:
        return (LET_OP, "nog geen profiel van het nieuwe aanbod",
                "Dit vult zich met elke dag dat er aanbod bijkomt.")
    delen = [f"{nu['aantal']} panden in dertig dagen"]
    if nu.get("mediane_opp"):
        delen.append(f"mediaan {nu['mediane_opp']} m2")
    if nu.get("label_onbekend") is not None:
        delen.append(f"{nu['label_onbekend']} zonder label")
    bewijs = "; ".join(delen)
    if nu.get("label_onbekend", 0) > nu.get("aantal", 1) * 0.5:
        return (LET_OP, bewijs,
                "Van meer dan de helft kennen we het label niet; een "
                "labelverdeling zegt dan nog weinig.")
    return (OK, bewijs, "")


def controle_veroudering():
    """
    Hoe oud is het aanbod dat we tonen?

    Een pand blijft in de tabellen staan tot iets anders bewijst dat het weg
    is. De attenderingen melden alleen nieuw en gewijzigd aanbod, dus een pand
    dat stilletjes verkocht wordt, blijft staan. Dit telt hoe groot die groep
    is, zodat de brief niet ongemerkt met verouderd aanbod rekent.
    """
    vandaag = dt.date.today()
    laatst = {}
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 5 or not v[3].lower().startswith(("te koop", "nieuw")):
                    continue
                sleutel = v[0].lower()
                laatst[sleutel] = max(laatst.get(sleutel, ""), v[4])
    except Exception:
        return (LET_OP, "aanbod niet te lezen", "Staat verkopen.txt er wel?")
    if not laatst:
        return (LET_OP, "geen aanbod in het bestand", "")
    ouderdom = []
    for datum in laatst.values():
        try:
            ouderdom.append((vandaag - dt.date.fromisoformat(datum)).days)
        except Exception:
            continue
    ouderdom.sort()
    oud = sum(1 for d in ouderdom if d > 60)
    bewijs = (f"{len(ouderdom)} panden te koop, mediaan {ouderdom[len(ouderdom)//2]} "
              f"dagen geleden voor het laatst bevestigd, oudste {ouderdom[-1]} dagen")
    if oud:
        return (LET_OP, bewijs + f", {oud} langer dan 60 dagen",
                "Die panden zijn waarschijnlijk al van de markt; ze blijven "
                "staan omdat de attendering alleen nieuw aanbod meldt. Een "
                "geplakte verkooplijst haalt ze eruit.")
    return (OK, bewijs, "")


def controle_verkopen():
    """
    Hoe de verkopen binnenkomen: via de mail of met de hand geplakt.

    Belangrijk om te weten of de attendering de verkopen meeneemt sinds Mark
    dat filter aanzette. Zo ja, dan hoeft er niets meer geplakt te worden.
    """
    per_bron, laatste = {}, ""
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 6 or not v[3].lower().startswith("verkocht"):
                    continue
                bron = "geplakt" if "plak" in v[5] else "uit de mail"
                per_bron[bron] = per_bron.get(bron, 0) + 1
                laatste = max(laatste, v[4])
    except Exception:
        return (LET_OP, "verkopen niet te lezen", "Staat verkopen.txt er wel?")
    if not per_bron:
        return (LET_OP, "nog geen verkopen in de reeks",
                "Zet in de Funda-attendering het filter op verkocht en onder "
                "bod; dan komen ze vanzelf binnen. Werkt dat niet, dan blijft "
                "plakken over.")
    delen = ", ".join(f"{n} {b}" for b, n in sorted(per_bron.items()))
    uit_mail = per_bron.get("uit de mail", 0)
    bewijs = f"{sum(per_bron.values())} verkopen: {delen}; laatste {laatste}"
    if not uit_mail:
        return (LET_OP, bewijs,
                "Er komt nog geen enkele verkoop uit de attendering. Controleer "
                "of het filter op verkocht daar echt aan staat.")
    return (OK, bewijs, "")


def controle_plakbestanden():
    """De lijsten die Mark met de hand aanlevert: verkopen en Kamernet."""
    uit = []
    for pad, wat in (("funda_verkocht_plak.txt", "verkooplijst van Funda"),
                     ("kamernet_plak.txt", "kamerlijst van Kamernet")):
        if os.path.exists(pad) and os.path.getsize(pad) > 200:
            uit.append(f"{wat}: aanwezig")
        else:
            uit.append(f"{wat}: ontbreekt")
    verkocht = _json("verkocht_details.json") or {}
    if verkocht:
        uit.append(f"{len(verkocht)} verkochte woningen verwerkt")
    # Komt een bron via de mail binnen, dan is het plakbestand overbodig.
    mail = (_json("mail_status.json") or {}).get("bronnen") or {}
    if (mail.get("kamernet") or {}).get("objecten"):
        uit[1] = "kamerlijst van Kamernet: niet nodig, komt uit de mail"
    if all(("aanwezig" in x or "niet nodig" in x) for x in uit[:2]):
        return (OK, "; ".join(uit), "")
    return (LET_OP, "; ".join(uit),
            "Plak de tekst van de pagina in dat bestand en commit het; het "
            "script verwerkt hem bij de volgende run.")


def controle_misdrijven():
    d = _json("misdrijven_per_buurt.json") or {}
    if not d:
        return (FOUT, "geen misdrijfcijfers", "Zie stap 6.")
    return (OK, f"{len(d)} buurten", "")


def controle_ov():
    haltes = _json("ov_haltes.json") or []
    afstanden = _json("ov_afstand_cache.json") or {}
    if not haltes:
        return (FOUT, "geen haltebestand",
                "Zie stap 16. Verwijder ov_haltes.json om opnieuw op te halen.")
    if len(haltes) < 50:
        return (LET_OP, f"{len(haltes)} haltes",
                "Verdacht weinig voor de ring; controleer het zoekgebied in "
                "ov_haltes.py.")
    geschat = sum(1 for a in afstanden.values()
                  if isinstance(a, dict) and a.get("geschat"))
    bewijs = f"{len(haltes)} haltes, {len(afstanden)} panden gerouteerd"
    if afstanden and geschat == len(afstanden):
        return (LET_OP, bewijs + ", alle afstanden geschat",
                "De routering via OSRM lukt niet; alle afstanden zijn de rechte "
                "lijn maal 1,35.")
    return (OK, bewijs, "")


def controle_archief():
    d = _json("bekendmakingen_archief.json") or {}
    leeftijd = _leeftijd_dagen("bekendmakingen_archief.json")
    if not d:
        return (FOUT, "archief leeg", "Zie stap 13.")
    publ = sum(len(v) for v in d.values() if isinstance(v, list))
    bewijs = f"{len(d)} adressen, {publ} publicaties"
    if leeftijd is not None and leeftijd > 3:
        return (LET_OP, bewijs + f", {leeftijd} dagen niet bijgewerkt",
                "Zie stap 13.")
    return (OK, bewijs, "")


def controle_regelgeving():
    d = _json("regelgeving_status.json")
    if d is None:
        return (LET_OP, "nog geen regelgevingsstatus",
                "De monitor draait op zondag. Na de eerste zondag hoort hier een "
                "aantal regelingen te staan.")
    # Sleutels die met een liggend streepje beginnen zijn geen regeling maar
    # administratie van het script zelf, zoals de lijst met zoektermen.
    d = {k: v for k, v in d.items()
         if not str(k).startswith("_") and isinstance(v, dict)}
    gemeente = sum(1 for g in d.values() if g.get("bron") == "gemeente")
    landelijk = sum(1 for g in d.values() if g.get("bron") == "landelijk")
    bewijs = f"{gemeente} verordeningen, {landelijk} wetten"
    if not gemeente:
        return (LET_OP, bewijs,
                "Geen gemeentelijke verordeningen gevonden via CVDR. Zie stap 9 op "
                "zondag; de zoekopdracht op 'Nijmegen' levert mogelijk niets op.")
    return (OK, bewijs, "")


def controle_geheugen():
    gezien = _json("brief_gezien.json") or {}
    trend = _json("prijstrend.json") or {}
    if not gezien:
        return (FOUT, "brief_gezien.json leeg",
                "Zonder geheugen wordt elk pand elke dag als nieuw behandeld.")
    weken = max((len(v) for v in trend.values() if isinstance(v, dict)), default=0)
    bewijs = f"{len(gezien)} panden onthouden, prijstrend over {weken} metingen"
    if weken < 4:
        return (LET_OP, bewijs,
                "De prijstrend is nog te kort voor een vergelijking over vier "
                "weken. Dat lost zich vanzelf op.")
    return (OK, bewijs, "")


def controle_commit():
    """Werd er de vorige keer iets teruggeschreven?"""
    leeftijd = _leeftijd_dagen("brief_gezien.json")
    if leeftijd is None:
        return (FOUT, "brief_gezien.json ontbreekt", "")
    if leeftijd > 2:
        return (FOUT, f"gegevens {leeftijd} dagen niet bijgewerkt",
                "Het terugcommitten lukt vermoedelijk niet. Zie de stap "
                "'Digests + gegevensbestanden terugcommitten'.")
    return (OK, "gegevens van de laatste run bewaard", "")


CONTROLES = [
    ("Versies", controle_versies),
    ("Geheugen verstuurde brieven", controle_verteld),
    ("Brief opnieuw geschreven", controle_briefherhaling),
    ("Oude verlaging in de brief", controle_oude_verlaging),
    ("Bekende onwaarheden in de brief", controle_verzonnen_beweringen),
    ("Samenstelling in plaats van markt", controle_samenstelling),
    ("Verkocht pand nog in het aanbod", controle_verkocht_nog_in_aanbod),
    ("Omvang van de gegevensbestanden", controle_bestandsomvang),
    ("Huurdata", controle_huurdata),
    ("Aanbod", controle_aanbod),
    ("Marktrente", controle_rente),
    ("Kapitaalmarkt (ECB)", controle_ecb),
    ("Bouwkostenindex", controle_bouwkosten),
    ("Eigen bouwkosten", controle_eigen_bouwkosten),
    ("Buurtcijfers CBS", controle_buurtcijfers),
    ("Kamervergunningen", controle_vergunningen),
    ("Kamerverhuurregister", controle_kamerverhuur),
    ("Woningprijsindex CBS", controle_woningprijzen),
    ("Stadsbegroting", controle_begroting),
    ("Geschiedenis per pand", controle_geschiedenis),
    ("Handmatige lijsten", controle_plakbestanden),
    ("Verkopen", controle_verkopen),
    ("Veroudering aanbod", controle_veroudering),
    ("Aanbodreeks", controle_aanbodreeks),
    ("Profiel nieuw aanbod", controle_aanbodprofiel),
    ("Groottepremie", controle_grootte_premie),
    ("Voltooide splitsingen", controle_splitsingen),
    ("Verkoopdatums", controle_verkoopdatums),
    ("Doorlooptijden", controle_doorlooptijden),
    ("Voorraad van de ring", controle_voorraad),
    ("Voet onder de brief", controle_briefvoet),
    ("Verkooptijd bovengrens", controle_verkooptijd),
    ("Huurdekking", controle_huurdekking),
    ("Bronnen die niets opleveren", controle_afzenders),
    ("Brieven verstuurd", controle_brieven),
    ("Huur tegen het landelijke cijfer", controle_huur_ijkpunt),
    ("Gemeubileerd", controle_gemeubileerd),
    ("Adressen met meerdere maten", controle_adressen_met_meerdere_maten),
    ("WOZ-bestand", controle_wozbestand),
    ("WOZ zonder pand", controle_woz_zonder_pand),
    ("Nieuwbouw apart", controle_nieuwbouw),
    ("Opnieuw aangeboden", controle_opnieuw_aangeboden),
    ("VvE-bijdragen", controle_vve),
    ("WOZ-schatting", controle_wozschatting),
    ("COROP Arnhem/Nijmegen", controle_corop),
    ("3D BAG eigen snapshot", controle_bag3d),
    ("Achtergronddekking", controle_achtergronddekking),
    ("Nieuwe onderwerpen", controle_nieuwe_onderwerpen),
    ("Logboek van de brief", controle_logboek),
    ("Jaarlijkse grenzen", controle_peildata),
    ("Attenderingen", controle_mailbronnen),
    ("Misdrijfcijfers", controle_misdrijven),
    ("OV-haltes", controle_ov),
    ("Bekendmakingen-archief", controle_archief),
    ("Regelgevingsmonitor", controle_regelgeving),
    ("Geheugen en trend", controle_geheugen),
    ("Terugschrijven", controle_commit),
]


VORIGE_PAD = "gezondheid_vorige.json"


def _vorige_stand():
    """Welke controles er vorige keer waren en hoe ze stonden."""
    return _json(VORIGE_PAD) or {}


def _bewaar_stand(uitkomsten):
    """De stand van nu bewaren, zodat de volgende run kan vergelijken."""
    try:
        with open(VORIGE_PAD, "w", encoding="utf-8") as f:
            json.dump({"datum": VANDAAG.isoformat(),
                       "controles": {n: s for n, s, _b, _d in uitkomsten}},
                      f, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception:
        pass


def _verschillen(uitkomsten, vorige):
    """
    Wat er is veranderd sinds de vorige run.

    Dit is de kern van een korter rapport: je hoeft niet elke regel te lezen,
    alleen wat anders is dan gisteren. En het vangt het gevaarlijke geval af
    dat een controle helemaal verdwijnt, zoals de 3D BAG-controle die er
    vanmiddag uitviel omdat een bestand niet was geuploud.
    """
    oud = (vorige or {}).get("controles") or {}
    nu = {n: s for n, s, _b, _d in uitkomsten}
    regels = []
    for naam, status in nu.items():
        if naam not in oud:
            regels.append(f"nieuw: {naam} ({status})")
        elif oud[naam] != status:
            regels.append(f"{naam}: van {oud[naam]} naar {status}")
    for naam in oud:
        if naam not in nu:
            regels.append(f"WEG: de controle {naam} draait niet meer")
    return regels


def _kerncijfers():
    """
    De cijfers die groeien, in een regel.

    Niet elk onderdeel hoeft in het korte blok, maar een teller die oploopt wel:
    daaraan zie je of de voorraad zich vult of dat er iets stilstaat. Een getal
    dat niet beweegt is deze week vaker een signaal gebleken dan een melding
    die oplichtte.
    """
    uit = []
    g = _geschiedenis()
    if g:
        met_bag = sum(1 for p in g.values() if p.get("bag_eenheden"))
        met_label = sum(1 for p in g.values() if p.get("labels"))
        nooit = sum(1 for p in g.values() if not p.get("bag_gezien"))
        uit.append(f"{len(g)} panden, {met_bag} met BAG, {met_label} met label, "
                   f"{nooit} nog niet nagekeken")
    b3 = (_json("bag3d.json") or {}).get("panden") or {}
    if b3:
        met = sum(1 for p in b3.values() if p.get("b3_opp_buitenmuur"))
        uit.append(f"3D BAG: {met} van {len(b3)}")
    try:
        # Op velden tellen en niet op tekst in de regel. Met "| verkocht" in de
        # hele regel telde hij ook adressen en toelichtingen mee waar dat woord
        # in voorkomt; dat gaf 648 waar de controle erboven 505 zei, en twee
        # tellers op hetzelfde bestand horen hetzelfde getal te geven.
        huur = koop = voorbehoud = 0
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 5:
                    continue
                status = v[3].lower()
                if status.startswith("te huur"):
                    huur += 1
                elif status.startswith("verkocht onder voorbehoud"):
                    voorbehoud += 1
                elif status.startswith("verkocht"):
                    koop += 1
        uit.append(f"{huur} huurwaarnemingen, {koop} verkopen"
                   + (f" en {voorbehoud} onder voorbehoud" if voorbehoud else ""))
    except Exception:
        pass
    woz = (_json("woz_kalibratie.json") or {}).get("aantal")
    if woz:
        # Ook tonen hoeveel er nog open staan, want dat is de stapel die Mark
        # zelf moet invullen.
        open_regels = 0
        try:
            with open("woz.txt", encoding="utf-8") as f:
                for regel in f:
                    delen = [d.strip() for d in regel.split("|")]
                    if (len(delen) > 1 and delen[0]
                            and not delen[0].startswith("#") and not delen[1]):
                        open_regels += 1
        except Exception:
            pass
        uit.append(f"{woz} panden met eigen WOZ"
                   + (f", {open_regels} nog in te vullen" if open_regels else ""))
    return uit


def rapport(kort=False, bewaren=False):
    uitkomsten = []
    for naam, functie in CONTROLES:
        try:
            status, bewijs, diagnose = functie()
        except Exception as e:
            status, bewijs, diagnose = FOUT, "controle zelf faalde", str(e)[:120]
        uitkomsten.append((naam, status, bewijs, diagnose))

    aantal = {s: sum(1 for u in uitkomsten if u[1] == s) for s in (OK, LET_OP, FOUT)}
    # Pas bewaren als het korte rapport al is gemaakt, anders vergelijkt de
    # volgende regel de stand met zichzelf en is er nooit een verschil.
    if bewaren:
        _bewaar_stand(uitkomsten)

    if kort:
        # Dit blok wordt in de chat geplakt en daar door Claude gelezen, niet
        # door Mark. De adviesregels kunnen er dus uit: wat "505 geplakt, 0 uit
        # de mail" betekent en wat eraan te doen valt, hoeft er niet bij te
        # staan. Dat halveert wat er vanaf een telefoon gekopieerd moet worden.
        # De uitleg blijft in het volledige rapport in het digestbestand, voor
        # als iemand het zonder context moet kunnen lezen.
        r = [f"GEZONDHEID {VANDAAG.isoformat()}: {aantal[OK]} ok, "
             f"{aantal[LET_OP]} let op, {aantal[FOUT]} fout"]
        for status in (FOUT, LET_OP):
            for naam, s_, bewijs, _diag in uitkomsten:
                if s_ != status:
                    continue
                r.append(f"[{status}] {naam}: {bewijs}")
        # De onderdelen die goed gaan niet meer uitschrijven: dat is de helft
        # van het rapport en je leest het toch niet. Wel het aantal, en wat er
        # is veranderd sinds de vorige run, want daar zit het nieuws.
        goed = [naam for naam, s_, _b, _d in uitkomsten if s_ == OK]
        vorige = _vorige_stand()
        verschil = _verschillen(uitkomsten, vorige) if vorige else []
        r.append(f"[OK] {len(goed)} onderdelen, ongewijzigd; het volledige "
                 f"rapport staat in het digestbestand")
        # De tellers die ergens naartoe groeien blijven wel zichtbaar, ook als
        # ze op OK staan. Anders zie je niet meer dat de voorraad zich vult, en
        # dat is juist wat je week na week wilt volgen.
        kern = _kerncijfers()
        if kern:
            r.append("Stand: " + "; ".join(kern))
        if not vorige:
            # Eerste run met deze vergelijking: dan is alles nieuw en zegt dat
            # niets. Vanaf de volgende run staat hier wat er werkelijk wijzigde.
            r.append("Eerste run met deze vergelijking; vanaf morgen staat hier "
                     "alleen nog wat er is veranderd.")
        elif verschil:
            r.append("")
            r.append(f"VERANDERD sinds {vorige.get('datum', 'de vorige run')}:")
            for regel in verschil:
                r.append(f"  {regel}")
        elif vorige:
            r.append(f"Niets veranderd sinds {vorige.get('datum')}.")

        # Automatische keuzes altijd tonen, ook als het onderdeel groen is.
        # Juist dan: een automatisch gekozen veld dat verkeerd is, geeft geen
        # fout maar een plausibel verkeerd getal.
        for regel in automatische_keuzes():
            r.append(f"[CONTROLEER] {regel}")
        return "\n".join(r)

    r = [f"# Gezondheidsrapport {VANDAAG.isoformat()}", "",
         f"{aantal[OK]} in orde, {aantal[LET_OP]} aandachtspunten, "
         f"{aantal[FOUT]} fouten.", ""]

    # Eerst wat er mis is, dan de rest: daar gaat het om bij het delen
    for status in (FOUT, LET_OP, OK):
        groep = [u for u in uitkomsten if u[1] == status]
        if not groep:
            continue
        r.append(f"## {status}")
        for naam, _s, bewijs, diag in groep:
            r.append(f"- **{naam}**: {bewijs}")
            if diag:
                r.append(f"  {diag}")
        r.append("")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    args = ap.parse_args()

    # In de log de korte versie, om te kopieren en te delen. In het bestand de
    # volledige versie, voor als je alle details wilt nalezen.
    print("=" * 60)
    print("KOPIEER VANAF HIER")
    print("=" * 60)
    print(rapport(kort=True))
    print("=" * 60)
    print("TOT HIER")
    print("=" * 60)
    if args.uit:
        os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(rapport(kort=False, bewaren=True) + "\n")
        print(f"\nVolledig rapport met alle details: {args.uit}")


if __name__ == "__main__":
    main()
