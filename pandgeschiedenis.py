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
    with open(PAD, "w", encoding="utf-8") as f:
        json.dump(geschiedenis, f, ensure_ascii=False, indent=1, sort_keys=True)


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
            if r["status"].startswith("te koop"):
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


def bij_bag(geschiedenis, alleen_gevolgd=True):
    """
    De BAG opnieuw bevragen: is het aantal woningen in het pand veranderd?

    Alleen voor panden waar iets mee gebeurd is, en hoogstens een vast aantal
    per ronde, want elke opvraging is een verzoek.
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
        soorten = {g["soort"] for g in pand["gebeurtenissen"]}
        if alleen_gevolgd and not (soorten & {"verkocht", "bekendmaking",
                                              "kamerverhuur"}):
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
    doel = set(alleen) if alleen is not None else set(geschiedenis)
    for sl, pand in geschiedenis.items():
        if sl not in doel:
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
                tekst = (f"energielabel van {adres} is nu {label}"
                         + (f", was {was}" if was else ""))
                nieuw += voeg_toe(pand, vandaag, "energielabel", tekst, "EP-Online")
                labels[adres] = label
        if labels:
            pand["labels"] = labels
        time.sleep(PAUZE_TUSSEN)
    print(f"Labels: {len(doel)} panden nagekeken", file=sys.stderr)
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
        })
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
    for pand, vers in sorted(paren, key=lambda p: -len(p[0]["gebeurtenissen"]))[:8]:
        r.append(f"## {pand['adres']}")
        for g in pand["gebeurtenissen"]:
            merk = " **nieuw**" if g in vers else ""
            r.append(f"- {g['datum']}: {g['tekst']} ({g['bron']}){merk}")
        r.append("")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    ap.add_argument("--volledig", action="store_true",
                    help="ook de BAG en de energielabels bijwerken")
    args = ap.parse_args()
    wis("geschiedenis")

    geschiedenis = lees(PAD, {})
    n_v = uit_verkopen(geschiedenis)
    n_a = uit_archief(geschiedenis)
    n_k = uit_kamerverhuur(geschiedenis)
    n_b = n_l = 0
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
          f"{n_b} BAG-wijzigingen, {n_l} labelwijzigingen", file=sys.stderr)
    if args.uit:
        regels = render(geschiedenis)
        if regels:
            os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
            with open(args.uit, "w", encoding="utf-8") as f:
                f.write("\n".join(regels) + "\n")


if __name__ == "__main__":
    main()
