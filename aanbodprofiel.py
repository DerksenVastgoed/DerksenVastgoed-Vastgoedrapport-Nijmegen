#!/usr/bin/env python3
"""
Hoe ziet het nieuwe aanbod eruit, en verandert dat?

Niet hoeveel panden erbij komen, maar wat voor panden. Een markt verandert vaak
eerst van samenstelling en pas daarna in aantallen: als er een maand lang
alleen kleine woningen met een slecht label bijkomen, is dat nieuws ook als het
totaal gelijk blijft.

Drie vensters:
- de laatste dertig dagen;
- de dertig dagen daarvoor, om mee te vergelijken;
- een voortschrijdend jaar als ijkpunt, zodat je ziet of een verschil
  uitzonderlijk is of binnen de normale schommeling valt.

Dat laatste is bewust geen venster van dezelfde soort. Over een jaar spelen
seizoen en rente mee, dus het is een referentie en geen vergelijking. En het
is bewust voortschrijdend en niet vanaf 1 januari: zo'n cijfer is in januari
leeg en in december vol, en betekent elke maand iets anders.

Wat erin staat: mediane oppervlakte, mediane prijs per m2, de verdeling over
drie labelgroepen met het aandeel onbekend erbij, en het aandeel panden dat
volgens de BAG in een complex zit.

Het aandeel onbekende labels hoort er altijd bij. Zolang onze labelverzameling
nog groeit, kan een verschuiving in de labelverdeling net zo goed onze eigen
voortgang zijn als een verandering in de markt.
"""
import argparse
import datetime as dt
import json
import statistics as st
import sys

UIT_PAD = "aanbodprofiel.json"
AANBOD_PAD = "verkopen.txt"
GESCHIEDENIS_PAD = "pandgeschiedenis.json"

LABELGROEPEN = (("A en B", ("A", "B")),
                ("C en D", ("C", "D")),
                ("E tot G", ("E", "F", "G")))
MINIMUM_JAAR = 100          # minder waarnemingen: het jaarcijfer niet tonen
MINIMUM_VENSTER = 15        # minder: geen mediaan noemen


def _sleutel(adres):
    return "".join(c for c in (adres or "").lower() if c.isalnum())


def lees_kenmerken(pad=GESCHIEDENIS_PAD):
    """Per adres het label en of het pand meerdere eenheden heeft."""
    try:
        # Via pandlezer: die vouwt gedeelde pandgegevens weer uit per adres,
        # zodat deze functie niets hoeft te weten van de opslagvorm.
        from pandlezer import laad
        g = laad(pad)
    except Exception:
        try:
            with open(pad, encoding="utf-8") as f:
                g = json.load(f)
        except Exception:
            return {}
    if not g:
        return {}
    uit = {}
    for pand in g.values():
        adres = pand.get("adres")
        if not adres:
            continue
        labels = pand.get("labels") or {}
        label = None
        for adr, waarde in labels.items():
            if _sleutel(adr) == _sleutel(adres):
                label = waarde
                break
        if label is None and labels:
            label = sorted(labels.values())[0]
        uit[_sleutel(adres)] = {
            "label": (label or "").upper()[:1] or None,
            "eenheden": len(pand.get("bag_eenheden") or []),
        }
    return uit


def lees_aanbod(pad=AANBOD_PAD):
    """Nieuw aangeboden koopwoningen, met datum, oppervlakte en prijs."""
    uit = []
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 7 or not v[3].lower().startswith("te koop"):
                    continue
                try:
                    prijs, opp = int(v[2]), int(v[6])
                except ValueError:
                    continue
                if not opp:
                    continue
                uit.append({"adres": v[0], "prijs": prijs, "opp": opp,
                            "datum": v[4][:10]})
    except FileNotFoundError:
        return []
    return uit


def profiel(panden, kenmerken, vanaf, tot):
    """Het profiel van wat er in dit venster bijkwam."""
    binnen = [p for p in panden if vanaf <= p["datum"] < tot]
    if not binnen:
        return None
    opp = [p["opp"] for p in binnen]
    ppm2 = [p["prijs"] / p["opp"] for p in binnen if p["opp"]]
    labels, complexen, bekend = {}, 0, 0
    for p in binnen:
        k = kenmerken.get(_sleutel(p["adres"])) or {}
        if k.get("eenheden", 0) >= 4:
            complexen += 1
        letter = k.get("label")
        if not letter:
            continue
        bekend += 1
        for naam, letters in LABELGROEPEN:
            if letter in letters:
                labels[naam] = labels.get(naam, 0) + 1
                break
    return {
        "aantal": len(binnen),
        "mediane_opp": round(st.median(opp)) if len(opp) >= MINIMUM_VENSTER else None,
        "mediane_ppm2": round(st.median(ppm2)) if len(ppm2) >= MINIMUM_VENSTER else None,
        "labels": labels,
        "label_bekend": bekend,
        "label_onbekend": len(binnen) - bekend,
        "in_complex": complexen,
        "vanaf": vanaf, "tot": tot,
    }


def maak(vandaag=None):
    """De drie vensters naast elkaar."""
    vandaag = vandaag or dt.date.today()
    panden = lees_aanbod()
    if not panden:
        return None
    kenmerken = lees_kenmerken()
    d = lambda n: (vandaag - dt.timedelta(days=n)).isoformat()
    morgen = (vandaag + dt.timedelta(days=1)).isoformat()
    uit = {
        "gemaakt": vandaag.isoformat(),
        "nu": profiel(panden, kenmerken, d(30), morgen),
        "vorige": profiel(panden, kenmerken, d(60), d(30)),
        "jaar": profiel(panden, kenmerken, d(365), morgen),
    }
    if uit["jaar"] and uit["jaar"]["aantal"] < MINIMUM_JAAR:
        uit["jaar_te_klein"] = True
    return uit


def tekst(p):
    """Het profiel als regels voor de weekeditie."""
    if not p or not p.get("nu"):
        return []
    nu, vorige, jaar = p["nu"], p.get("vorige"), p.get("jaar")
    r = [f"**Wat er de laatste dertig dagen bijkwam.** {nu['aantal']} panden "
         f"nieuw te koop"
         + (f", tegen {vorige['aantal']} in de dertig dagen daarvoor."
            if vorige else ".")]
    if nu["mediane_opp"]:
        regel = f"Mediane oppervlakte {nu['mediane_opp']} m2"
        if vorige and vorige["mediane_opp"]:
            regel += f", was {vorige['mediane_opp']} m2"
        if jaar and jaar["mediane_opp"] and not p.get("jaar_te_klein"):
            regel += f"; over het jaar {jaar['mediane_opp']} m2"
        r.append(regel + ".")
    if nu["mediane_ppm2"]:
        regel = f"Mediane vraagprijs €{nu['mediane_ppm2']:,} per m2".replace(",", ".")
        if vorige and vorige["mediane_ppm2"]:
            regel += f", was €{vorige['mediane_ppm2']:,}".replace(",", ".")
        r.append(regel + ".")
    if nu["labels"]:
        delen = ", ".join(f"{n}: {a}" for n, a in nu["labels"].items())
        r.append(f"Energielabels: {delen}; van {nu['label_onbekend']} van de "
                 f"{nu['aantal']} panden kennen we het label niet, dus een "
                 f"verschuiving hierin kan ook onze eigen voortgang zijn.")
    r.append(f"{nu['in_complex']} van de {nu['aantal']} panden zitten volgens "
             f"de BAG in een complex van vier woningen of meer.")
    if p.get("jaar_te_klein"):
        r.append(f"Het jaarcijfer blijft buiten beschouwing: nog maar "
                 f"{jaar['aantal']} waarnemingen, en onder de "
                 f"{MINIMUM_JAAR} zegt een gemiddelde niets.")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=UIT_PAD)
    args = ap.parse_args()
    p = maak()
    if not p:
        print("Geen aanbod gevonden om een profiel van te maken", file=sys.stderr)
        return 0
    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    for regel in tekst(p):
        print("  " + regel, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
