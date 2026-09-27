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
import sys

PAD = "pandgeschiedenis.json"
VERKOPEN = "verkopen.txt"
ARCHIEF = "bekendmakingen_archief.json"
MAX_BAG_PER_RONDE = 60

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
        if status.startswith("te huur"):
            continue
        per_adres.setdefault(sleutel(adres), []).append(
            {"adres": adres, "plaats": plaats, "prijs": prijs, "status": status,
             "datum": datum, "opp": v[6] or None})

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
                elif vorige_prijs and r["prijs"] != vorige_prijs:
                    richting = "verlaagd" if r["prijs"] < vorige_prijs else "verhoogd"
                    nieuw += voeg_toe(pand, r["datum"], "prijswijziging",
                                      f"prijs {richting} van "
                                      + f"€{vorige_prijs:,}".replace(",", ".")
                                      + " naar " + f"€{r['prijs']:,}".replace(",", "."),
                                      "aanbod")
                vorige_prijs = r["prijs"]
            elif r["status"] == "verkocht":
                # Funda toont de laatste vraagprijs, niet de koopsom; die staat
                # alleen bij het Kadaster. Zo noemen we het dus ook.
                nieuw += voeg_toe(pand, r["datum"], "verkocht",
                                  "verkocht, laatste vraagprijs "
                                  + f"€{r['prijs']:,}".replace(",", ".")
                                  + (f", {r['opp']} m2" if r["opp"] else ""),
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
        from marktprijzen_bag import bag_dump, bag_eenheden_in_pand, BAG_API_KEY
    except Exception as e:
        leg_vast("geschiedenis", f"BAG-functies niet te laden: {str(e)[:120]}")
        return 0
    if not BAG_API_KEY:
        # Zonder sleutel geeft elke opvraging een 401. Eenmaal melden is genoeg;
        # honderden mislukte verzoeken vullen alleen het logboek.
        leg_vast("geschiedenis", "Geen BAG_API_KEY in deze stap: de BAG en de "
                                 "energielabels zijn niet bijgewerkt.")
        print("Geen BAG-sleutel; BAG-controle overgeslagen", file=sys.stderr)
        return 0
    nieuw, gedaan = 0, 0
    vandaag = dt.date.today().isoformat()
    for sl, pand in sorted(geschiedenis.items(),
                           key=lambda x: x[1].get("bag_gezien") or ""):
        if gedaan >= MAX_BAG_PER_RONDE:
            break
        soorten = {g["soort"] for g in pand["gebeurtenissen"]}
        if alleen_gevolgd and not (soorten & {"verkocht", "bekendmaking",
                                              "kamerverhuur"}):
            continue
        pand_id = pand.get("pand_id")
        if not pand_id:
            bag = bag_dump(pand["adres"]) or {}
            pand_id = bag.get("pand")
            pand["pand_id"] = pand_id
        if not pand_id:
            continue
        eenheden = bag_eenheden_in_pand(pand_id)
        gedaan += 1
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
    return nieuw


def bij_labels(geschiedenis):
    """Het energielabel per adres in het pand; na een splitsing volgt dat later."""
    try:
        from marktprijzen_bag import (bag_adres_uitgebreid, ep_energielabel,
                                      BAG_API_KEY)
    except Exception as e:
        leg_vast("geschiedenis", f"Labelfuncties niet te laden: {str(e)[:120]}")
        return 0
    if not BAG_API_KEY:
        return 0
    nieuw, vandaag = 0, dt.date.today().isoformat()
    for sl, pand in geschiedenis.items():
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
    return nieuw


# Welke gebeurtenissen iets zeggen over wat een eigenaar met een pand doet
ROUTE_SOORTEN = ("bekendmaking", "bag", "energielabel", "kamerverhuur")
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
        n_b = bij_bag(geschiedenis)
        n_l = bij_labels(geschiedenis)
    bewaar(geschiedenis)

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
