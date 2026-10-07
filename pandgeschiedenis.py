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
    return re.sub(r"[^a-z0-9]", "", (adres or "").lower())


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
        uit = compact(geschiedenis)
    except Exception as e:
        print(f"Compact opslaan lukt niet, oude vorm gebruikt: {str(e)[:80]}",
              file=sys.stderr)
        uit = geschiedenis
    with open(PAD, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False, indent=1, sort_keys=True)


def voeg_toe(pand, datum, soort, tekst, bron):
    """Een gebeurtenis toevoegen als die er nog niet staat."""
    for g in pand["gebeurtenissen"]:
        if g["datum"] == datum and g["soort"] == soort and g["tekst"] == tekst:
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

    for sl, rijen in per_adres.items():
        rijen.sort(key=lambda r: r["datum"])
        pand = geschiedenis.setdefault(sl, {"adres": rijen[0]["adres"],
                                            "pand_id": None,
                                            "gebeurtenissen": []})
        pand["adres"] = rijen[-1]["adres"]
        vorige_prijs = None
        gezien_te_koop = False
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
                # Uit een geplakte lijst kennen we de verkoopdatum niet; dan
                # zetten we er geen datum bij in de tekst, zodat niemand er een
                # tijdlijn op bouwt.
                zonder_datum = "plak" in (r.get("bron") or "")
                nieuw += voeg_toe(pand, r["datum"], "verkocht",
                                  "verkocht, laatste vraagprijs "
                                  + f"€{r['prijs']:,}".replace(",", ".")
                                  + (f", {r['opp']} m2" if r["opp"] else "")
                                  + (" (verkoopdatum onbekend; uit een geplakte "
                                     "lijst)" if zonder_datum else ""),
                                  "aanbod")
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
        # De sleutel komt uit het archief zelf, niet uit de titel. Anders levert
        # "aan de Dominicanenstraat 30" de sleutel "dedominicanenstraat30" op en
        # matcht een pand niet met zijn eigen bekendmakingen. Een huisnummer met
        # een letter hoort bij het pand van het kale nummer.
        basis = re.sub(r"(?<=\d)[a-z]{1,2}$", "", k)
        if basis in geschiedenis:
            continue
        # De weergave in lijn brengen met de sleutel: staat er "de" voor de
        # straat terwijl de sleutel dat niet heeft, dan hoort het er niet bij.
        if sleutel(adres) != basis and sleutel(adres).startswith("de"):
            adres = re.sub(r"^de\s+", "", adres)
        geschiedenis.setdefault(basis, {"adres": adres, "pand_id": None,
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
        if not pand_id:
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
            pand_id = bag.get("pand")
            pand["pand_id"] = pand_id
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
        nu = sorted((e.get("adres"), e.get("oppervlakte")) for e in eenheden)
        eerder = pand.get("bag_eenheden")
        if eerder is None:
            pand["bag_eenheden"] = nu
            continue
        if [tuple(x) for x in eerder] != nu:
            oud_n, nieuw_n = len(eerder), len(nu)
            maten = ", ".join(str(o) for _a, o in nu if o)
            if nieuw_n != oud_n:
                tekst = (f"de BAG telt nu {nieuw_n} woningen in dit pand, was "
                         f"{oud_n}: {maten} m2")
            else:
                tekst = f"de oppervlaktes in de BAG zijn gewijzigd: {maten} m2"
            nieuw += voeg_toe(pand, vandaag, "bag", tekst,
                              "Basisregistratie Adressen en Gebouwen")
            pand["bag_eenheden"] = nu
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


def bij_labels(geschiedenis, alleen=None):
    """
    Het energielabel per adres in het pand; na een splitsing volgt dat later.

    Alleen voor de panden die deze ronde ook tegen de BAG zijn gehouden. Zonder
    die grens liep deze stap langs alle gevolgde panden, wat bij duizend panden
    al duizenden opvragingen betekent en na de archiefbackfill onhoudbaar wordt.
    """
    try:
        from marktprijzen_bag import (bag_adres_uitgebreid, ep_energielabel,
                                      BAG_API_KEY, EP_API_KEY)
    except Exception as e:
        leg_vast("geschiedenis", f"Labelfuncties niet te laden: {str(e)[:120]}")
        return 0
    if not BAG_API_KEY:
        # Twee waarden terug, want de aanroeper pakt er twee uit. Met een enkele
        # nul liep de hele stap vast zodra de sleutel ontbrak, en dat is precies
        # het moment waarop je een nette melding wilt in plaats van een crash.
        print("Geen BAG_API_KEY; de BAG-ronde wordt overgeslagen", file=sys.stderr)
        return 0, []
    # Hier hardop over zijn: zonder deze sleutel komt er geen enkel label
    # binnen, en dat bleef eerder onzichtbaar omdat elke fout werd ingeslikt.
    if not EP_API_KEY:
        leg_vast("geschiedenis", "Geen EP_API_KEY: energielabels worden "
                                 "overgeslagen. Staat het secret in de repo en "
                                 "geeft de workflow hem als EP_API_KEY door?")
        print("Geen EP_API_KEY; energielabels overgeslagen", file=sys.stderr)
        return 0
    nieuw, vandaag = 0, dt.date.today().isoformat()
    eerste = gewijzigd = 0
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
        for adres in adressen:
            m = re.match(r"^(.+?)\s+(\d+)\s*([A-Za-z]?)[-\s]*(\w*)$", adres or "")
            if not m:
                continue
            try:
                info = bag_adres_uitgebreid(m.group(1), m.group(2), m.group(3),
                                            m.group(4), "Nijmegen") or {}
                ep = ep_energielabel(info.get("vbo"), info.get("postcode"),
                                     m.group(2), m.group(3), m.group(4)) or {}
            except Exception:
                continue
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
                if was:
                    tekst = f"energielabel van {adres} is nu {label}, was {was}"
                    gewijzigd += 1
                else:
                    # Voor het eerst opgehaald: dat is geen wijziging aan het
                    # pand maar een aanvulling van onze gegevens.
                    tekst = (f"energielabel van {adres} is {label}, "
                             f"geregistreerd {datum}")
                    eerste += 1
                nieuw += voeg_toe(pand, datum, "energielabel", tekst,
                                  "EP-Online")
                labels[adres] = label
        if labels:
            pand["labels"] = labels
        # Onthouden voor de andere adressen in hetzelfde BAG-pand.
        if pid:
            per_pand_id[pid] = labels
        time.sleep(PAUZE_TUSSEN)
    print(f"Labels: {len(doel)} panden nagekeken; {eerste} woningen voor het "
          f"eerst een label, {gewijzigd} werkelijk gewijzigd"
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
        pand = geschiedenis.setdefault(sleutel(adres), {
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
                    if g.get("soort") == "verkocht" and g.get("datum")]
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
                      "hoogstens_dagen": dagen})
    rijen.sort(key=lambda r: r["verkocht_gezien"], reverse=True)
    uit = {"aantal": len(rijen), "panden": rijen[:20]}
    if rijen:
        waarden = sorted(r["hoogstens_dagen"] for r in rijen)
        uit["mediaan_hoogstens_dagen"] = waarden[len(waarden) // 2]
    return uit


def _dagen_tussen(van, tot):
    try:
        return (dt.date.fromisoformat(tot[:10])
                - dt.date.fromisoformat(van[:10])).days
    except Exception:
        return None


def doorlooptijden(geschiedenis):
    """
    Wat de reeks per pand oplevert zodra er meer dan een gebeurtenis in staat.

    Drie dingen die nergens op te zoeken zijn: hoe lang een pand te koop stond,
    hoeveel jaar er tussen twee verkopen zat, en hoe de prijs van datzelfde pand
    zich heeft ontwikkeld.
    """
    verkoop_duur, bezit_duur, prijsgroei = [], [], []
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
        datums = [v["datum"] for v in verkocht]
        for eerst, later in zip(datums, datums[1:]):
            try:
                jaren = (dt.date.fromisoformat(later)
                         - dt.date.fromisoformat(eerst)).days / 365.25
            except ValueError:
                continue
            if 0.2 < jaren < 60:
                bezit_duur.append(round(jaren, 1))
        bedragen = []
        for v in verkocht:
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
           "prijsgroei_aantal": len(prijsgroei)}
    if verkoop_duur:
        uit["verkooptijd_mediaan_dagen"] = int(st.median(verkoop_duur))
    if bezit_duur:
        uit["bezitsduur_mediaan_jaar"] = st.median(bezit_duur)
    if prijsgroei:
        uit["prijsgroei_mediaan_pct"] = round(
            st.median([p["per_jaar"] for p in prijsgroei]), 1)
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
            "makelaar": (details.get(sleutel(pand.get("adres") or "")) or {}
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
            merk = " **nieuw**" if g in vers else ""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    ap.add_argument("--volledig", action="store_true",
                    help="ook de BAG en de energielabels bijwerken")
    args = ap.parse_args()
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
    main()
