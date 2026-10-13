#!/usr/bin/env python3
"""
De velden uit elke bekendmaking vastleggen, zodat de uitkomst meetbaar wordt.

WAAROM DIT BESTAAT. Wij volgen 479 publicaties en bewaren er vier dingen van:
datum, titel, soort en url. De uitkomst staat er niet bij. Van 37 aanvragen
die een besluit kregen noemde de titel er twee "verleend"; de rest heet
gewoon "Besluit voor het splitsen van ...". Zonder die uitkomst kunnen wij
onze eigen inschatting nooit nameten, en dan is er geen lerend effect maar
alleen een mening die zichzelf bevestigt.

De tekst van de publicatie zegt het wel, en die halen wij al op. Deze module
leest hem uit en legt per publicatie vast:

  zaaknummer        Z2025-00011358, in zowel de aanvraag als het besluit, en
                    dus de enige harde koppeling tussen die twee
  uitkomst          verleend, anders, onduidelijk of leeg
  besluitdatum      de dag waarop de gemeente besloot
  ontvangen         de dag waarop zij de aanvraag kreeg
  verwacht_besluit  de dag waarop zij dacht te besluiten
  einde             tot wanneer de stukken ter inzage liggen

Dat laatste komt uit de metadata van de pagina en staat er alleen als er
werkelijk iets ligt. Zie besluit.py voor beide.

WAT DIT NIET DOET. Het haalt geen stukken op. De viewer waar die op staan
laat geautomatiseerd ophalen niet toe, en daar werken wij niet omheen. Deze
module raakt alleen de publicatie zelf, op een site die daar wel voor is.

EENMAAL GEZIEN IS GENOEG. Een publicatie verandert niet meer nadat zij is
gepubliceerd, dus wat eenmaal is vastgelegd wordt niet opnieuw opgehaald.
De eerste ronde haalt de hele achterstand in, daarna zijn het er een paar
per dag.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time

import besluit
import bijlagen

PAD = "publicatie_velden.json"
STAND = "publicatie_velden_stand.json"
VELDEN = ("zaaknummer", "uitkomst", "uitkomst_reden", "besluitdatum",
          "bezwaar_tot", "ontvangen", "verwacht_besluit", "einde")


def lees(pad=PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def nog_te_doen(archief_rijen, bekend):
    """
    Welke publicaties nog niet zijn uitgelezen, nieuwste eerst.

    Nieuwste eerst omdat een recente publicatie de kans heeft dat haar
    stukken nog ter inzage liggen, en omdat een ronde die halverwege stopt
    dan het nuttigste deel af heeft.
    """
    uit = [r for r in archief_rijen if r["gmb"] not in bekend]
    return sorted(uit, key=lambda r: r.get("datum") or "", reverse=True)


def stand_van(velden):
    """Wat er nu ligt, als getallen. Geen schatting, een telling."""
    uitkomsten = {}
    met_zaak = 0
    open_nu = 0
    vandaag = dt.date.today().isoformat()
    for v in velden.values():
        u = v.get("uitkomst") or "geen uitspraak"
        uitkomsten[u] = uitkomsten.get(u, 0) + 1
        if v.get("zaaknummer"):
            met_zaak += 1
        if (v.get("einde") or "") >= vandaag and v.get("einde"):
            open_nu += 1
    return {"vastgelegd": len(velden), "met_zaaknummer": met_zaak,
            "uitkomsten": dict(sorted(uitkomsten.items(),
                                      key=lambda x: -x[1])),
            "nu_ter_inzage": open_nu, "datum": vandaag}


def doorlooptijden(velden):
    """
    De werkelijke doorlooptijd per zaak: van ontvangst tot besluit.

    Niet van publicatiedatum tot publicatiedatum, want dat is wanneer wij het
    zagen en niet wanneer het gebeurde. Het verschil is groot: de gemeente
    publiceert een aanvraag pas dagen nadat zij hem kreeg.
    """
    per = {}
    for gmb, v in velden.items():
        z = v.get("zaaknummer")
        if not z:
            continue
        d = per.setdefault(z, {})
        if v.get("ontvangen"):
            d["ontvangen"] = v["ontvangen"]
        if v.get("besluitdatum"):
            d["besluit"] = v["besluitdatum"]
        if v.get("uitkomst"):
            d["uitkomst"] = v["uitkomst"]
        if v.get("verwacht_besluit"):
            d["verwacht"] = v["verwacht_besluit"]
    uit = []
    for z, d in per.items():
        if not (d.get("ontvangen") and d.get("besluit")):
            continue
        try:
            a = dt.date.fromisoformat(d["ontvangen"])
            b = dt.date.fromisoformat(d["besluit"])
        except ValueError:
            continue
        rij = {"zaaknummer": z, "dagen": (b - a).days,
               "uitkomst": d.get("uitkomst", "")}
        if d.get("verwacht"):
            try:
                rij["dagen_tov_verwacht"] = (
                    b - dt.date.fromisoformat(d["verwacht"])).days
            except ValueError:
                pass
        uit.append(rij)
    return sorted(uit, key=lambda r: r["dagen"])


def ronde(minuten=10, maximaal=0, pad=PAD, tempo=0.4):
    """Een ronde: ophalen wat nog niet bekend is, binnen een tijdbudget."""
    bekend = lees(pad)
    rijen = bijlagen.uit_archief(soorten=None)
    todo = nog_te_doen(rijen, bekend)
    if maximaal:
        todo = todo[:maximaal]
    einde = time.time() + minuten * 60
    gedaan = mislukt = 0
    for r in todo:
        if time.time() > einde:
            print(f"Tijdbudget op na {gedaan} publicaties; "
                  f"{len(todo) - gedaan - mislukt} blijven liggen.",
                  file=sys.stderr)
            break
        _naam, url = bijlagen.kandidaten(r["gmb"])[0]
        broncode, fout = bijlagen.haal(url)
        if fout:
            mislukt += 1
            continue
        import re as _re
        kaal = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", broncode))
        v = besluit.velden_uit(kaal)
        v["einde"] = besluit.einde_reactietermijn(broncode)
        v["pand"] = r.get("pand", "")
        v["datum"] = r.get("datum", "")
        v["gezien"] = dt.date.today().isoformat()
        bekend[r["gmb"]] = v
        gedaan += 1
        time.sleep(tempo)
    return bekend, gedaan, mislukt, len(todo)


def bewaar(velden, pad=PAD, stand_pad=STAND):
    with open(pad, "w", encoding="utf-8") as f:
        json.dump(velden, f, ensure_ascii=False, indent=1, sort_keys=True)
    s = stand_van(velden)
    s["doorlooptijden"] = doorlooptijden(velden)[:400]
    with open(stand_pad, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    return s


def proef():
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. WAT AL BEKEND IS WORDT NIET OPNIEUW OPGEHAALD.
    # Een publicatie verandert niet meer nadat zij is gepubliceerd. Zonder
    # deze regel haalt elke ronde alle 479 opnieuw op, en dan wordt de
    # achterstand nooit ingelopen maar elke dag opnieuw gedaan.
    rijen = [{"gmb": "gmb-2026-3", "datum": "2026-10-03"},
             {"gmb": "gmb-2026-1", "datum": "2026-10-01"},
             {"gmb": "gmb-2026-2", "datum": "2026-10-02"}]
    todo = nog_te_doen(rijen, {"gmb-2026-2": {}})
    check("nog te doen", [r["gmb"] for r in todo],
          ["gmb-2026-3", "gmb-2026-1"])
    check("alles bekend", nog_te_doen(rijen, {r["gmb"]: {} for r in rijen}),
          [])
    check("niets bekend", len(nog_te_doen(rijen, {})), 3)

    # 2. DE STAND IS EEN TELLING EN GEEN SCHATTING.
    velden = {
        "a": {"uitkomst": "verleend", "zaaknummer": "Z1", "einde": "2099-01-01"},
        "b": {"uitkomst": "verleend", "zaaknummer": "Z2", "einde": ""},
        "c": {"uitkomst": "anders", "zaaknummer": "Z3", "einde": "2000-01-01"},
        "d": {"uitkomst": "", "zaaknummer": "", "einde": ""},
    }
    s = stand_van(velden)
    check("vastgelegd", s["vastgelegd"], 4)
    check("met zaaknummer", s["met_zaaknummer"], 3)
    check("uitkomsten", s["uitkomsten"],
          {"verleend": 2, "anders": 1, "geen uitspraak": 1})
    check("nu ter inzage", s["nu_ter_inzage"], 1)
    # Een publicatie zonder uitspraak telt als "geen uitspraak" en niet als
    # verleend. Dat verschil is het hele punt: een aanvraag heeft nog geen
    # uitkomst, en die meetellen maakt onze cijfers mooier dan zij zijn.
    if "verleend" in str(velden["d"]):
        fouten.append("een publicatie zonder uitspraak kreeg er toch een")

    # 3. DE DOORLOOPTIJD LOOPT VAN ONTVANGST TOT BESLUIT.
    # Niet van publicatie tot publicatie: dat is wanneer wij het zagen. Bij
    # Hatertseweg 338 is dat het verschil tussen 2 december 2025 (ontvangen)
    # en 14 september 2026 (besluit), en de publicatiedatums liggen anders.
    tweeluik = {
        "gmb-aanvraag": {"zaaknummer": "Z2025-00011358",
                         "ontvangen": "2025-12-02",
                         "verwacht_besluit": "2026-01-28", "uitkomst": ""},
        "gmb-besluit": {"zaaknummer": "Z2025-00011358",
                        "besluitdatum": "2026-09-14", "uitkomst": "verleend"},
    }
    d = doorlooptijden(tweeluik)
    check("een doorlooptijd", len(d), 1)
    # NIET d[0] ZONDER MEER. Bij het nameten van deze controle brak ik de
    # ontvangstdatum, en toen viel de proef om op een IndexError in plaats
    # van te melden welke controle rood stond: er was geen doorlooptijd meer
    # om in te kijken. Een proef die omvalt zegt niets. Zie de eis daarover.
    eerste = d[0] if d else {}
    check("dagen", eerste.get("dagen"), 286)
    check("uitkomst erbij", eerste.get("uitkomst"), "verleend")
    # Hoeveel later dan de gemeente zelf dacht. Dat is een getal dat zij
    # publiceert en dat wij dus kunnen nameten.
    check("later dan verwacht", eerste.get("dagen_tov_verwacht"), 229)
    # Een zaak met alleen een aanvraag heeft geen doorlooptijd, en dat is
    # iets anders dan een doorlooptijd van nul.
    check("alleen een aanvraag", doorlooptijden(
        {"x": {"zaaknummer": "Z9", "ontvangen": "2026-01-01"}}), [])
    check("zonder zaaknummer", doorlooptijden(
        {"x": {"ontvangen": "2026-01-01", "besluitdatum": "2026-02-01"}}), [])

    # 4. EEN ONTBREKEND BESTAND IS LEEG EN GEEN FOUT.
    check("bestand ontbreekt", lees("bestaat-echt-niet.json"), {})

    print(f"Proef publicatievelden: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--minuten", type=float, default=10)
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args()
    if args.proef:
        return proef()
    velden, gedaan, mislukt, totaal = ronde(minuten=args.minuten,
                                            maximaal=args.max)
    s = bewaar(velden)
    print(f"Opgehaald: {gedaan} van {totaal} nog te doen, {mislukt} mislukt.",
          file=sys.stderr)
    print(f"Vastgelegd: {s['vastgelegd']} publicaties, "
          f"{s['met_zaaknummer']} met zaaknummer, "
          f"{s['nu_ter_inzage']} nu ter inzage.", file=sys.stderr)
    print(f"Uitkomsten: {s['uitkomsten']}", file=sys.stderr)
    d = s.get("doorlooptijden") or []
    if d:
        dagen = sorted(x["dagen"] for x in d)
        print(f"Doorlooptijd over {len(d)} zaken: mediaan "
              f"{dagen[len(dagen) // 2]} dagen, kortste {dagen[0]}, langste "
              f"{dagen[-1]}", file=sys.stderr)
    # NUL OPGEHAALD TERWIJL ER WERK WAS, IS GEEN SUCCES.
    #
    # De eerste echte ronde meldde "gelukt" en committeerde niets, en toen
    # had ik geen enkel aanknopingspunt: de stap stond groen, het joblogboek
    # is van buiten niet te lezen, en de meldstap gaat alleen af bij een
    # mislukking. Een ronde die niets ophaalt terwijl er 479 publicaties
    # wachten, hoort rood te staan, zodat de reden in het issue komt.
    if totaal and not gedaan:
        print(f"GESTOPT: geen enkele van de {totaal} publicaties is "
              f"opgehaald, {mislukt} mislukt. Dat is geen lege uitkomst maar "
              f"een storing.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
