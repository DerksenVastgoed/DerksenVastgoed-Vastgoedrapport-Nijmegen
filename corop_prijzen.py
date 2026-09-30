#!/usr/bin/env python3
"""
Prijzen en transacties voor het COROP-gebied Arnhem/Nijmegen.

Waarom dit naast de bestaande cijfers staat: de brief zette onze eigen
vraagprijsmedianen tot nu toe af tegen de CBS-index voor heel Gelderland. Daar
zitten Winterswijk en Nijmegen in dezelfde bak. Het COROP-gebied
Arnhem/Nijmegen is een stuk dichterbij, en uit dezelfde tabel komt het aantal
transacties, wat iets zegt over de krapte in de markt.

Landelijk, provincie en COROP blijven alle drie in beeld: wijken ze van elkaar
af, dan is dat verschil zelf het signaal.

Bron: CBS-tabel 85819NED, prijsindex 2020=100 per COROP-gebied, ongeveer 22
dagen na afloop van een kwartaal.
"""
import argparse
import datetime as dt
import json
import sys

TABEL = "85819NED"
UIT_PAD = "corop_prijzen.json"
# Niet de code raden maar opzoeken: CBS hernummert gebieden af en toe, en een
# verkeerde code levert stilletjes de cijfers van een andere regio op.
ZOEK_REGIO = "arnhem/nijmegen"
KWARTALEN = 16


def _cbs():
    """De ophaalfuncties van de woningprijsindex hergebruiken."""
    from woningprijsindex import _haal, BASIS, alleen_ipv4
    alleen_ipv4()
    return _haal, BASIS


def regiocode(haal, basis):
    """
    De code van het COROP-gebied, opgezocht op naam.

    Geeft None terug als het gebied er niet tussen staat; dan schrijven we
    liever niets dan de cijfers van de verkeerde regio.
    """
    rijen = haal(f"{basis}/{TABEL}/RegioS")
    for rij in rijen:
        titel = (rij.get("Title") or "").strip().lower()
        if ZOEK_REGIO in titel.replace(" ", ""):
            return rij.get("Key", "").strip(), rij.get("Title", "").strip()
    for rij in rijen:                      # ruimer: los van de schuine streep
        titel = (rij.get("Title") or "").lower()
        if "arnhem" in titel and "nijmegen" in titel:
            return rij.get("Key", "").strip(), rij.get("Title", "").strip()
    return None, None


def _getal(waarde):
    try:
        return float(waarde)
    except (TypeError, ValueError):
        return None


def kwartaalreeks(rijen):
    """De kwartaalrijen op volgorde, met de velden die we gebruiken."""
    uit = {}
    for rij in rijen:
        periode = (rij.get("Perioden") or "").strip()
        if "KW" not in periode:            # jaar- en maandrijen overslaan
            continue
        uit[periode] = {
            "index": _getal(rij.get("PrijsindexBestaandeKoopwoningen_1")),
            "kwartaal_pct": _getal(rij.get("OntwikkelingTOVVorigePeriode_2")),
            "jaar_pct": _getal(rij.get("OntwikkelingTOVEenJaarEerder_3")),
            "transacties": _getal(rij.get("AantalVerkochteWoningen_4")),
            "transacties_jaar_pct": _getal(
                rij.get("OntwikkelingTOVEenJaarEerder_6")),
            "gemiddelde_prijs": _getal(rij.get("GemiddeldeVerkoopprijs_7")),
        }
    return uit


def samenvatting(reeks, regionaam):
    """Wat de brief nodig heeft: de laatste stand en de richting."""
    if not reeks:
        return None
    laatste = max(reeks)
    r = reeks[laatste]
    return {
        "gebied": regionaam,
        "periode": laatste,
        "index": r["index"],
        "kwartaal_pct": r["kwartaal_pct"],
        "jaar_pct": r["jaar_pct"],
        "transacties": r["transacties"],
        "transacties_jaar_pct": r["transacties_jaar_pct"],
        "gemiddelde_prijs": r["gemiddelde_prijs"],
        "reeks": {k: reeks[k] for k in sorted(reeks)[-KWARTALEN:]},
        "opgehaald": dt.date.today().isoformat(),
        "bron": f"CBS {TABEL}, prijsindex bestaande koopwoningen per COROP",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=UIT_PAD)
    ap.add_argument("--stil", action="store_true")
    args = ap.parse_args()

    try:
        haal, basis = _cbs()
    except Exception as e:
        print(f"CBS-hulpfuncties niet te laden: {str(e)[:120]}", file=sys.stderr)
        return 1

    try:
        code, naam = regiocode(haal, basis)
    except Exception as e:
        print(f"Regiolijst niet op te halen: {str(e)[:120]}", file=sys.stderr)
        return 1
    if not code:
        print(f"COROP-gebied met '{ZOEK_REGIO}' niet gevonden in {TABEL}; "
              f"niets weggeschreven", file=sys.stderr)
        return 1

    try:
        rijen = haal(f"{basis}/{TABEL}/TypedDataSet",
                     {"$filter": f"RegioS eq '{code}'"})
    except Exception as e:
        print(f"Cijfers niet op te halen: {str(e)[:120]}", file=sys.stderr)
        return 1

    stand = samenvatting(kwartaalreeks(rijen), naam)
    if not stand:
        print("Geen kwartaalcijfers gevonden", file=sys.stderr)
        return 1

    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)
    if not args.stil:
        print(f"{naam} {stand['periode']}: index {stand['index']}, "
              f"{stand['jaar_pct']}% op jaarbasis, "
              f"{int(stand['transacties'] or 0)} transacties", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
