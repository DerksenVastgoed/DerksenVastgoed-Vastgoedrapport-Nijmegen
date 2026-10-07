#!/usr/bin/env python3
"""
De rekenstukken voor een splitsingsaanvraag, zelf opgesteld.

Bij een aanvraag om een pand op te delen gaan er vaste bijlagen mee. Drie
daarvan zijn rekenwerk met vaste formules, en die kunnen we zelf maken zodra we
de kamermaten kennen:

1. De ruimtetabel met de toets uit het Besluit bouwwerken leefomgeving (Bbl):
   minstens 55% van de gebruiksoppervlakte moet verblijfsgebied zijn.
2. De ventilatie-eis per ruimte, en de spuivoorziening per verblijfsruimte.
3. De parkeerberekening volgens de Beleidsregels Parkeren 2025, inclusief de
   vrijstelling voor splitsing in het gereguleerde gebied.

De formules zijn overgenomen uit een echte aanvraag, die van de Staringstraat 2
van 22 september 2026, en daarop getest: die komt op 56,6, 48,2 en 79,0 m2 per
appartement met telkens de conclusie dat het voldoet.

Wat we hiermee NIET kunnen: de constructieberekening, de bouwtekeningen en de
situatietekeningen. Daar is een constructeur en een tekenbureau voor nodig. Maar
dit deel hoeft niet meer te wachten tot na de aankoop, en het is ook de toets
die bepaalt of een indeling überhaupt kan.

Gebruik:
  python splitsingstoets.py --in splitsing_staringstraat.txt

Formaat van het invoerbestand, een regel per ruimte:

  # pand: Staringstraat 2, gereguleerd parkeergebied: ja
  # bestaand: 1 woning, nieuw: 3 appartementen, soort: koop
  appartement 1 | hal           | verkeersruimte   | 1.2
  appartement 1 | toilet        | toiletruimte     | 1.1
  appartement 1 | badkamer      | sanitair ruimte  | 3.3
  appartement 1 | keuken        | verblijfsruimte  | 13.7
  appartement 1 | woonkamer     | verblijfsruimte  | 20.9
"""
import argparse
import datetime as dt
import sys

# Uit het Besluit bouwwerken leefomgeving. Het Bbl drukt dit voor een
# woonfunctie niet uit in luchtwisselingen per uur maar in dm3/s per m2
# vloeroppervlakte. Omrekenen kan: 1 dm3/s is 3,6 m3/h.
#
# Nieuwbouwniveau: een verblijfsgebied vraagt 0,9 dm3/s per m2 en een
# verblijfsruimte 0,7, allebei met een minimum van 7 dm3/s per ruimte. Dat
# minimum gold eerder niet in dit script, waardoor een kamer van 5 m2 op 4,5
# uitkwam in plaats van op 7.
#
# Bij verbouw van een bestaand pand geldt het rechtens verkregen niveau: de
# legale kwaliteit mag niet verslechteren, met de eisen voor bestaande bouw als
# ondergrens. Voor een bestaande woonfunctie is dat 0,7 dm3/s per m2 met
# hetzelfde minimum van 7. Daarom staat nieuwbouw hier als zwaarste variant en
# is het te kiezen.
VENTILATIE_GEBIED = 0.9
VENTILATIE_RUIMTE = 0.7
VENTILATIE_MINIMUM = 7.0
VENTILATIE_VAST = {"toiletruimte": 7.0, "sanitair ruimte": 14.0,
                   "badruimte": 14.0, "overige": 14.0}
# Spuivoorziening: voor een verblijfsgebied ten minste 6 dm3/s per m2, voor een
# losse verblijfsruimte 3. De aanvraag rekent dat om naar openingsoppervlak:
# A netto = Qv / (V x 1000) = 6 / (0,1 x 1000) = 0,06 m2 per m2.
SPUI_PER_M2 = 0.06
SPUI_RUIMTE_PER_M2 = 0.03
# Minstens 55% van de gebruiksoppervlakte moet verblijfsgebied zijn
VERBLIJFSGEBIED_AANDEEL = 0.55
# Beleidsregels Parkeren 2025, norm voor koopappartement in de binnenstad
PARKEERNORM = 0.70


def lees(pad):
    """Het invoerbestand als kop plus ruimten per appartement."""
    kop, ruimten = {}, {}
    try:
        with open(pad, encoding="utf-8") as f:
            regels = f.readlines()
    except FileNotFoundError:
        print(f"{pad} niet gevonden", file=sys.stderr)
        return None, None
    for regel in regels:
        kaal = regel.strip()
        if not kaal:
            continue
        if kaal.startswith("#"):
            # Kopregels met "sleutel: waarde, sleutel: waarde"
            for deel in kaal.lstrip("#").split(","):
                if ":" in deel:
                    k, v = deel.split(":", 1)
                    kop[k.strip().lower()] = v.strip()
            continue
        v = [x.strip() for x in kaal.split("|")]
        if len(v) < 4:
            print(f"Regel overgeslagen: {kaal[:60]}", file=sys.stderr)
            continue
        try:
            opp = float(v[3].replace(",", "."))
        except ValueError:
            print(f"Geen oppervlakte in: {kaal[:60]}", file=sys.stderr)
            continue
        ruimten.setdefault(v[0], []).append(
            {"naam": v[1], "soort": v[2].lower(), "opp": opp})
    return kop, ruimten


def toets(ruimten):
    """Per appartement de gebruiksoppervlakte en de 55%-toets."""
    uit = {}
    for naam, rijen in ruimten.items():
        go = sum(r["opp"] for r in rijen)
        verblijf = sum(r["opp"] for r in rijen
                       if r["soort"].startswith("verblijfs"))
        eis = go * VERBLIJFSGEBIED_AANDEEL
        for r in rijen:
            if r["soort"].startswith("verblijfs"):
                # "verblijfsgebied" krijgt 0,9, een losse "verblijfsruimte"
                # 0,7, en allebei het minimum van 7 dm3/s.
                per_m2 = (VENTILATIE_GEBIED if "gebied" in r["soort"]
                          else VENTILATIE_RUIMTE)
                r["ventilatie"] = round(max(r["opp"] * per_m2,
                                            VENTILATIE_MINIMUM), 2)
                r["ventilatie_m3h"] = round(r["ventilatie"] * 3.6, 1)
                if r["ventilatie"] == VENTILATIE_MINIMUM:
                    r["op_minimum"] = True
                r["spui"] = round(r["opp"] * (SPUI_PER_M2 if "gebied" in r["soort"]
                                              else SPUI_RUIMTE_PER_M2), 2)
            elif r["soort"] in VENTILATIE_VAST:
                r["ventilatie"] = VENTILATIE_VAST[r["soort"]]
                r["ventilatie_m3h"] = round(r["ventilatie"] * 3.6, 1)
            # Een verkeersruimte of meterruimte heeft geen eigen eis.
        uit[naam] = {"go": round(go, 1), "verblijfsgebied": round(verblijf, 1),
                     "eis_55pct": round(eis, 1),
                     "verschil": round(verblijf - eis, 1),
                     "voldoet": verblijf >= eis, "ruimten": rijen}
    return uit


def parkeren(kop, aantal_nieuw):
    """
    De parkeerberekening, met de vrijstelling als die geldt.

    De norm is 0,70 per woning in de binnenstad. Bij splitsing in het
    gereguleerde gebied geldt geen parkeereis, omdat de nieuwe huisnummers geen
    parkeervergunning krijgen; dat staat in de Beleidsregels Parkeren 2025 onder
    bijzonder geval VII. Buiten dat gebied geldt de eis wel, en dan is een
    tekort een reëel probleem.
    """
    try:
        bestaand = int("".join(c for c in kop.get("bestaand", "1")
                               if c.isdigit()) or 1)
    except ValueError:
        bestaand = 1
    eis_oud = -(-round(PARKEERNORM * bestaand, 2) // 1)      # naar boven
    eis_nieuw = -(-round(PARKEERNORM * aantal_nieuw, 2) // 1)
    tekort = eis_nieuw - eis_oud
    gereguleerd = kop.get("gereguleerd parkeergebied", "").lower().startswith("j")
    return {"bestaand": bestaand, "nieuw": aantal_nieuw,
            "eis_oud": int(eis_oud), "eis_nieuw": int(eis_nieuw),
            "tekort": int(tekort), "gereguleerd": gereguleerd,
            "vrijstelling": gereguleerd and tekort > 0}


def rapport(kop, resultaat, park):
    r = [f"# Splitsingstoets {kop.get('pand', 'onbekend pand')}", "",
         f"_Opgesteld {dt.date.today().isoformat()} met de formules uit het "
         f"Besluit bouwwerken leefomgeving, op nieuwbouwniveau: 0,9 dm3/s per "
         f"m2 voor een verblijfsgebied, 0,7 voor een verblijfsruimte, met een "
         f"minimum van 7 dm3/s per ruimte. Bij verbouw mag worden teruggevallen "
         f"op het rechtens verkregen niveau, dus dit is de zwaarste variant. "
         f"Dit is rekenwerk, geen constructieberekening en geen bouwtekening._",
         ""]
    for naam, d in resultaat.items():
        r.append(f"## {naam}")
        r.append("")
        r.append("| ruimte | soort | m2 | ventilatie dm3/s | ventilatie m3/h "
                 "| spui m2 |")
        r.append("|---|---|---:|---:|---:|---:|")
        for ruimte in d["ruimten"]:
            vent = ruimte.get("ventilatie", "-")
            if ruimte.get("op_minimum"):
                vent = f"{vent} (minimum)"
            r.append(f"| {ruimte['naam']} | {ruimte['soort']} | "
                     f"{ruimte['opp']:.1f} | {vent} | "
                     f"{ruimte.get('ventilatie_m3h', '-')} | "
                     f"{ruimte.get('spui', '-')} |")
        r.append("")
        r.append(f"Gebruiksoppervlakte: **{d['go']} m2**. Eis van 55% "
                 f"verblijfsgebied: {d['eis_55pct']} m2. Aanwezig: "
                 f"{d['verblijfsgebied']} m2, verschil {d['verschil']:+.1f}. "
                 f"**{'Voldoet' if d['voldoet'] else 'VOLDOET NIET'}**.")
        r.append("")
    r.append("## Parkeerberekening")
    r.append("")
    r.append(f"Norm {PARKEERNORM} per woning. Bestaand: {park['bestaand']} "
             f"woning(en), eis {park['eis_oud']}. Nieuw: {park['nieuw']} "
             f"woningen, eis {park['eis_nieuw']}. Verschil "
             f"{park['tekort']:+d} parkeerplaatsen.")
    r.append("")
    if park["vrijstelling"]:
        r.append("Het pand ligt in het gereguleerde parkeergebied. Volgens de "
                 "Beleidsregels Parkeren 2025, bijzonder geval VII, geldt bij "
                 "splitsing van een bestaande woning geen parkeereis: de nieuwe "
                 "huisnummers krijgen geen parkeervergunning of abonnement, "
                 "waardoor de parkeerdruk niet stijgt. **Beroep op de "
                 "vrijstelling.**")
        r.append("")
        r.append("_Keerzijde om te weten: een bewoner op een nieuw huisnummer "
                 "kan geen parkeervergunning krijgen._")
    elif park["tekort"] > 0:
        r.append(f"Het pand ligt NIET in het gereguleerde parkeergebied, dus "
                 f"de parkeereis geldt wel. Er is een tekort van "
                 f"{park['tekort']} plaats(en) dat moet worden opgelost op "
                 f"eigen terrein of via afkoop. **Dit is hier de kritieke "
                 f"toets.**")
    else:
        r.append("Geen tekort, dus geen parkeerprobleem.")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="bron", required=True)
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    kop, ruimten = lees(args.bron)
    if not ruimten:
        return 1
    resultaat = toets(ruimten)
    park = parkeren(kop, len(resultaat))
    tekst = rapport(kop, resultaat, park)
    if args.uit:
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(tekst)
        print(f"Weggeschreven naar {args.uit}", file=sys.stderr)
    else:
        print(tekst)
    niet_ok = [n for n, d in resultaat.items() if not d["voldoet"]]
    if niet_ok:
        print(f"LET OP: {', '.join(niet_ok)} haalt de 55%-eis niet",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
