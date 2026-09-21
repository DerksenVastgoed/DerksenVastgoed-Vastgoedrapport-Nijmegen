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
import sys

OK, LET_OP, FOUT = "OK", "LET OP", "FOUT"
VANDAAG = dt.date.today()


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

def controle_huurdata():
    """Het belangrijkste: rust de richtprijs op metingen of op een aanname?"""
    regels = _regels("verkopen.txt")
    huur = [r for r in regels if "te huur" in r.lower()]
    pararius = [r for r in huur if "pararius" in r.lower()]
    kamernet = [r for r in huur if "kamernet" in r.lower()]
    recent = [r for r in huur
              if any(str(VANDAAG - dt.timedelta(days=d)) in r for d in range(8))]
    bewijs = (f"{len(huur)} huurwaarnemingen, waarvan {len(pararius)} Pararius "
              f"en {len(kamernet)} Kamernet; {len(recent)} in de laatste week")
    if not huur:
        return (FOUT, bewijs,
                "Geen enkele huurwaarneming. Elke richtprijs rust op een aanname. "
                "Kijk in stap 14 naar de [pararius]-regels: staat daar "
                "'0 objecten', dan herkent de parser de mail niet.")
    if not recent:
        return (LET_OP, bewijs,
                "Wel huurdata, maar niets nieuws deze week. Komen de Pararius-mails "
                "nog binnen, en worden ze herkend? Zie stap 14.")
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
                "De verbouwkosten worden niet geindexeerd. Zie stap 17.")
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
                "Deze velden worden niet gevonden in de CBS-kaart. In stap 7 staat "
                "welke veldnamen er wel zijn; die moeten in buurten_tabel.py.")
    return (OK, bewijs + ", alle velden gevuld", "")


def controle_vergunningen():
    per_buurt = _json("vergunningen_per_buurt.json") or {}
    lijst = _json("kamervergunningen.json") or {}
    if not lijst:
        return (FOUT, "kamervergunningen.json ontbreekt", "")
    if len(per_buurt) < 3:
        return (LET_OP, f"{len(lijst)} adressen, maar {len(per_buurt)} buurten "
                        f"gekoppeld",
                "De koppeling aan buurten is niet gemaakt; de kolom in de brief "
                "blijft leeg. Zie stap 5.")
    return (OK, f"{len(lijst)} adressen in {len(per_buurt)} buurten", "")


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
    ("Huurdata", controle_huurdata),
    ("Aanbod", controle_aanbod),
    ("Marktrente", controle_rente),
    ("Kapitaalmarkt (ECB)", controle_ecb),
    ("Bouwkostenindex", controle_bouwkosten),
    ("Eigen bouwkosten", controle_eigen_bouwkosten),
    ("Buurtcijfers CBS", controle_buurtcijfers),
    ("Kamervergunningen", controle_vergunningen),
    ("Misdrijfcijfers", controle_misdrijven),
    ("OV-haltes", controle_ov),
    ("Bekendmakingen-archief", controle_archief),
    ("Regelgevingsmonitor", controle_regelgeving),
    ("Geheugen en trend", controle_geheugen),
    ("Terugschrijven", controle_commit),
]


def rapport():
    uitkomsten = []
    for naam, functie in CONTROLES:
        try:
            status, bewijs, diagnose = functie()
        except Exception as e:
            status, bewijs, diagnose = FOUT, "controle zelf faalde", str(e)[:120]
        uitkomsten.append((naam, status, bewijs, diagnose))

    aantal = {s: sum(1 for u in uitkomsten if u[1] == s) for s in (OK, LET_OP, FOUT)}
    r = [f"# Gezondheidsrapport {VANDAAG.isoformat()}", "",
         f"{aantal[OK]} in orde, {aantal[LET_OP]} aandachtspunten, "
         f"{aantal[FOUT]} fouten.", ""]

    # Eerst wat er mis is, dan de rest: daar gaat het om bij het delen
    for status in (FOUT, LET_OP, OK):
        groep = [u for u in uitkomsten if u[1] == status]
        if not groep:
            continue
        r.append(f"## {status}")
        for naam, _s, bewijs, diagnose in groep:
            r.append(f"- **{naam}**: {bewijs}")
            if diagnose:
                r.append(f"  {diagnose}")
        r.append("")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    tekst = rapport()
    print(tekst)
    if args.uit:
        os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(tekst + "\n")


if __name__ == "__main__":
    main()
