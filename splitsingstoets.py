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


# De bijlagen die bij beide bekeken aanvragen zijn meegestuurd. Wie het
# aanlevert staat erbij, want dat bepaalt wat vooraf klaar kan liggen en wat
# pas na de aankoop kan.
BIJLAGEN = [
    ("Plattegronden, doorsneden en detailtekeningen", "tekenbureau"),
    ("Situatietekening bestaande en nieuwe toestand", "tekenbureau"),
    ("Constructieve berekening", "constructeur, mag worden nagestuurd"),
    ("Toelichting op ontwerp constructie", "constructeur"),
    ("Ruimtetabel met de 55%-toets uit het Bbl", "zelf, met kamermaten"),
    ("Ventilatieberekening per ruimte", "zelf, met kamermaten"),
    ("Spuivoorziening per verblijfsgebied", "zelf, met kamermaten"),
    ("Parkeerberekening", "zelf, nu al"),
    ("Thermische isolatie", "zelf of adviseur, afhankelijk van de ingreep"),
    ("Bruikbaarheid en toegankelijkheid", "tekenbureau"),
    ("Bouwwerkinstallaties", "installateur"),
    ("Kwaliteitsverklaringen en CE-markeringen", "leverancier"),
    ("Bodemonderzoek", "niet nodig bij een interne verbouwing"),
    ("Gegevens over participatie", "zelf, vooraf te regelen"),
]

# Extra bijlagen die er alleen bij komen als er ook bouwkundig wordt
# uitgebreid, en dus een buitenplanse omgevingsplanactiviteit nodig is. Uit het
# verleende dossier van de Biezenstraat 110: eenentwintig bijlagen in totaal.
BIJLAGEN_BOPA = [
    ("Motivering bopa: waarom afwijken en wat de gevolgen zijn",
     "zelf, vaste opzet"),
    ("Gevelaanzichten en doorsneden nieuwe situatie", "tekenbureau"),
    ("Erfafscheidingen met bebouwing", "tekenbureau"),
    ("Berekening waterberging", "adviseur"),
    ("Hemelwater- en vuilwaterafvoer bestaand en nieuw", "tekenbureau"),
    ("Quickscan flora en fauna", "ecoloog"),
    ("Checklist natuurinclusief bouwen met groenmaatregelen",
     "zelf, met een tekening erbij"),
    ("Brandveiligheid", "adviseur, advies Veiligheidsregio volgt"),
    ("Foto's bestaande situatie", "zelf"),
    ("Verkennend bodemonderzoek", "alleen nodig boven 50 m2 of bij een "
     "andere bodemgevoelige functie"),
    ("Onderzoek ontplofbare oorlogsresten", "alleen in verdacht gebied, "
     "verplicht voordat de grond in gaat"),
    ("Risicomatrix bouwveiligheid", "zelf, uiterlijk vier weken voor de start"),
    ("Bouwveiligheidsplan met veiligheidscoordinator",
     "alleen als de risicomatrix twaalf punten of meer scoort"),
    ("Melding start en einde werkzaamheden",
     "zelf, start twee dagen vooraf melden"),
]
# Wat twee verleende bopa-dossiers aan doorlooptijd lieten zien. Geen
# gemiddelde van een reeks, maar twee gemeten gevallen; dat is meer dan we
# eerder hadden.
DOORLOOPTIJD_BOPA = [
    ("Biezenstraat 110, splitsing met aanbouw (bopa)",
     "2025-12-03", "2026-09-29"),
    ("St. Annastraat 456, extra verdieping (bopa, na negatief welstandsadvies)",
     "2025-10-14", "2026-09-24"),
    ("Heydenrijckstraat 40, inpandig splitsen (alleen technisch)",
     "2026-04-15", "2026-09-23"),
]
# Wat het in de praktijk kostte en duurde, uit dat ene verleende dossier.
BIEZENSTRAAT_LEGES = 2218.21
BIEZENSTRAAT_DAGEN = 300          # 3 december 2025 tot 29 september 2026


def voorbereiding(adres, aantal_nu, aantal_na, gereguleerd=True):
    """
    Wat er klaar kan liggen voordat er een pand is gekocht.

    Voor een pand dat we nog niet bezitten kennen we geen kamermaten, dus de
    ruimtetabel en de ventilatieberekening kunnen nog niet. De
    parkeerberekening wel, want die heeft alleen het aantal woningen voor en na
    nodig. En de lijst met bijlagen is bekend uit twee echte aanvragen, dus die
    kan er altijd bij: dan is vooraf duidelijk wie wat moet leveren en wat pas
    na de aankoop kan.
    """
    park = parkeren({"bestaand": str(aantal_nu),
                     "gereguleerd parkeergebied": "ja" if gereguleerd else "nee"},
                    aantal_na)
    r = [f"### Voorbereiding splitsingsaanvraag {adres}", "",
         f"_Van {aantal_nu} naar {aantal_na} woningen. Dit blok zegt wat er nu "
         f"al klaar kan liggen en wat pas kan als de kamermaten bekend zijn._",
         ""]
    if park["vrijstelling"]:
        r.append(f"**Parkeren: geen eis.** Norm {PARKEERNORM} per woning geeft "
                 f"{park['eis_nieuw']} tegen {park['eis_oud']} nu, dus een "
                 f"tekort van {park['tekort']}. In het gereguleerde "
                 f"parkeergebied geldt bij splitsing geen parkeereis "
                 f"(Beleidsregels Parkeren 2025, bijzonder geval VII): de "
                 f"nieuwe huisnummers krijgen geen parkeervergunning.")
    elif park["tekort"] > 0:
        r.append(f"**Parkeren: tekort van {park['tekort']} plaats(en)** en geen "
                 f"vrijstelling, want dit pand ligt buiten het gereguleerde "
                 f"gebied. Dit is hier de kritieke toets.")
    else:
        r.append("**Parkeren: geen tekort.**")
    r.append("")
    r.append("| bijlage | wie levert |")
    r.append("|---|---|")
    for naam, wie in BIJLAGEN:
        r.append(f"| {naam} | {wie} |")
    r.append("")
    r.append("_Komt er ook bouwkundig iets bij, bijvoorbeeld een aanbouw die "
             "buiten het omgevingsplan valt, dan is het een buitenplanse "
             "omgevingsplanactiviteit en komen deze bijlagen erbij:_")
    r.append("")
    r.append("| extra bijlage bij een bopa | wie levert |")
    r.append("|---|---|")
    for naam, wie in BIJLAGEN_BOPA:
        r.append(f"| {naam} | {wie} |")
    r.append("")
    r.append(f"**Doorlooptijd uit {len(DOORLOOPTIJD_BOPA)} verleende "
             f"dossiers:**")
    r.append("")
    for naam, van, tot in DOORLOOPTIJD_BOPA:
        try:
            dagen = (dt.date.fromisoformat(tot)
                     - dt.date.fromisoformat(van)).days
            r.append(f"- {naam}: {van} tot {tot}, {dagen} dagen "
                     f"({dagen // 30} maanden)")
        except ValueError:
            continue
    r.append("")
    r.append("_Het verschil tussen die drie zit in de buitenkant. Blijft de "
             "voorgevel ongemoeid en gebeurt alles inpandig, in een bestemming "
             "waar meerdere woningen zijn toegestaan, dan is de activiteit "
             "bouwen onder het omgevingsplan vergunningsvrij en blijft alleen "
             "de technische toets over: bij de Heydenrijckstraat drie stukken, "
             "een voorschrift en vijf maanden. Komt er een aanbouw of een "
             "dakopbouw bij, dan is het een bopa met twintig bijlagen, de "
             "welstandscommissie en ongeveer een jaar._")
    r.append("")
    r.append("_Bij de St. Annastraat kwam daar een negatief welstandsadvies "
             "tussen: op 11 juni 2026 afgewezen, na aanpassing van de "
             "dakaansluiting, de leien en de kozijnen op 10 september positief. "
             "Reken bij een ingreep die het aanzicht verandert op zo'n extra "
             "ronde van ongeveer een kwartaal._")
    r.append("")
    r.append(f"_Uit het verleende dossier van de Biezenstraat 110: aanvraag 3 "
             f"december 2025, vergunning 29 september 2026, dus ongeveer "
             f"{BIEZENSTRAAT_DAGEN} dagen, met leges van "
             f"€{BIEZENSTRAAT_LEGES:,.2f}".replace(",", ".") + " en "
             "eenentwintig bijlagen. Reken op groenmaatregelen als voorschrift "
             "en op zes weken bezwaartermijn waarin beginnen op eigen risico "
             "is._")
    r.append("")
    r.append("_Nog nodig voor de eigen berekeningen: een plattegrond met de "
             "kamermaten per ruimte. Die is er bij een bezichtiging in een half "
             "uur, en dan geeft splitsingstoets.py de ruimtetabel, de "
             "ventilatie en de spuivoorziening._")
    return "\n".join(r)


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
