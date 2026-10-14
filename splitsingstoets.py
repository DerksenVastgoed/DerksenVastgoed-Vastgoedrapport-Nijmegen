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
# DE NORM HOORT BIJ DE ZONE EN HET WONINGTYPE, EN STOND HIER ALS EEN GETAL.
#
# Hier stond PARKEERNORM = 0.70 met als uitleg "norm voor koopappartement in
# de binnenstad", en die werd op elk pand toegepast. Van de 20.321 adressen in
# onze voorraad liggen er 14.200 buiten de Binnenstad. Voor een betaalbaar
# huurappartement was 0,70 daar in beide richtingen fout: te hoog in de
# Binnenstad en het Centrumgebied (0,50) en de 1e Schil (0,60), te laag in de
# 2e Schil en Rest bebouwde kom (0,80) en het Buitengebied (1,00).
#
# De tabel staat nu in parkeernormen.txt en de opzoeking in parkeernorm.py.
import parkeernorm as _norm


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
    zone = (kop.get("parkeerzone") or "").strip()
    soort = (kop.get("woningtype") or "").strip()
    gereguleerd = kop.get("gereguleerd parkeergebied", "").lower().startswith("j")
    kaal = {"bestaand": bestaand, "nieuw": aantal_nieuw, "zone": zone,
            "woningtype": soort, "gereguleerd": gereguleerd,
            "norm": None, "onzeker": False, "reden": "", "band": None,
            "eis_oud": None, "eis_nieuw": None, "tekort": None,
            "vrijstelling": False}
    if not zone:
        kaal["reden"] = ("geen parkeerzone opgegeven; die staat per pand in "
                         "voorraad.json onder parkeerzone")
        return kaal
    if not soort:
        # ZONDER WONINGTYPE GEEN GETAL MAAR EEN BANDBREEDTE. In het
        # Centrumgebied loopt de norm van 0,20 voor een studentenwoning tot
        # 1,20 voor een duur koopappartement. Zelf een type kiezen zou de
        # uitkomst bepalen zonder dat iemand die keuze heeft gemaakt.
        kaal["band"] = _norm.bandbreedte(zone)
        kaal["reden"] = ("geen woningtype opgegeven, dus geen enkele norm; "
                         "zie de bandbreedte")
        return kaal
    uit = _norm.norm(zone, soort)
    if uit["norm"] is None:
        kaal["reden"] = uit["reden"]
        kaal["band"] = _norm.bandbreedte(zone)
        return kaal
    if uit["onzeker"]:
        # EEN BESCHADIGDE CEL LEVERT GEEN EIS. Zie parkeernormen.txt.
        kaal["norm"] = uit["norm"]
        kaal["onzeker"] = True
        kaal["reden"] = uit["reden"]
        return kaal
    n = uit["norm"]
    eis_oud = -(-round(n * bestaand, 2) // 1)      # naar boven
    eis_nieuw = -(-round(n * aantal_nieuw, 2) // 1)
    tekort = int(eis_nieuw - eis_oud)
    kaal.update({"norm": n, "eis_oud": int(eis_oud),
                 "eis_nieuw": int(eis_nieuw), "tekort": tekort,
                 "vrijstelling": gereguleerd and tekort > 0})
    return kaal


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
        r.append(f"**Parkeren: geen eis.** Norm {park['norm']} per woning ({park['zone']}, {park['woningtype']}) geeft "
                 f"{park['eis_nieuw']} tegen {park['eis_oud']} nu, dus een "
                 f"tekort van {park['tekort']}. In het gereguleerde "
                 f"parkeergebied geldt bij splitsing geen parkeereis "
                 f"(Beleidsregels Parkeren 2025, bijzonder geval VII): de "
                 f"nieuwe huisnummers krijgen geen parkeervergunning.")
    elif park["tekort"] is None:
        r.append(f"**Parkeren: niet te berekenen.** {park['reden'] or 'geen norm bekend'}.")
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
    # GEEN GETAL ALS ER GEEN NORM IS. Dit blok rekende altijd door, ook als
    # de zone of het type ontbrak, want de norm was een constante. Nu zegt het
    # wat er mist en noemt het de bandbreedte in plaats van een eis.
    if park["norm"] is None or park["onzeker"]:
        r.append(f"**Geen parkeereis berekend**: {park['reden']}.")
        band = park.get("band") or {}
        if band.get("laag") is not None:
            r.append("")
            r.append(f"In zone {park['zone']} loopt de norm van "
                     f"{band['laag']} ({band['laag_type']}) tot "
                     f"{band['hoog']} ({band['hoog_type']}) per woning, over "
                     f"{band['aantal']} woningtypen. Welke geldt, hangt af "
                     f"van het type; zet dat in het invoerbestand onder "
                     f"woningtype.")
        if park["onzeker"]:
            r.append("")
            r.append(f"De tabel geeft hier {park['norm']} per woning, maar "
                     f"die cel is in het brondocument beschadigd. Nakijken in "
                     f"de Beleidsregels parkeren 2025 voordat hiermee wordt "
                     f"gerekend.")
    else:
        r.append(f"Norm {park['norm']} per woning, zone {park['zone']}, type "
                 f"{park['woningtype']}. Bestaand: {park['bestaand']} "
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
    elif park["tekort"] is None:
        # GEEN TEKORT IS NIET NUL. Hier stond elif park["tekort"] > 0, en dat
        # viel om op een tekort dat None is omdat er geen norm bekend is. Dat
        # viel pas op toen deze module zijn eerste proef kreeg. Beter een
        # foutmelding dan een conclusie, maar beter nog deze regel.
        r.append("Of er een tekort is, is hier niet vast te stellen: "
                 + (park["reden"] or "geen norm bekend") + ".")
    elif park["tekort"] > 0:
        r.append(f"Het pand ligt NIET in het gereguleerde parkeergebied, dus "
                 f"de parkeereis geldt wel. Er is een tekort van "
                 f"{park['tekort']} plaats(en) dat moet worden opgelost op "
                 f"eigen terrein of via afkoop. **Dit is hier de kritieke "
                 f"toets.**")
    else:
        r.append("Geen tekort, dus geen parkeerprobleem.")
    return "\n".join(r)


def proef():
    """
    De parkeerberekening nameten, per zone en per woningtype.

    WAAROM DEZE MODULE ER EEN KRIJGT. Hij rekende de parkeereis uit voor een
    aankoopbeslissing en had geen enkele proef. Zolang de norm een constante
    was viel dat nog te overzien; nu hij uit een tabel komt, met zes zones,
    veertien woningtypen en twee beschadigde cellen, niet meer.
    """
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # EEN BETAALBAAR HUURAPPARTEMENT IN DE BINNENSTAD: norm 0,50. Van een naar
    # drie woningen geeft 1 tegen 2, dus een tekort van 1.
    kop = {"bestaand": "1", "parkeerzone": "Binnenstad",
           "woningtype": "huur appartement betaalbaar",
           "gereguleerd parkeergebied": "ja"}
    p1 = parkeren(kop, 3)
    check("norm in de Binnenstad", p1["norm"], 0.50)
    check("eis oud en nieuw", (p1["eis_oud"], p1["eis_nieuw"]), (1, 2))
    check("tekort", p1["tekort"], 1)
    check("vrijstelling in gereguleerd gebied", p1["vrijstelling"], True)

    # DEZELFDE SPLITSING IN DE 2e SCHIL IS EEN ANDER ANTWOORD: norm 0,80.
    # Met de oude constante van 0,70 was dit te laag, en niets liet dat zien.
    p2 = parkeren(dict(kop, **{"parkeerzone": "2e Schil",
                               "gereguleerd parkeergebied": "nee"}), 3)
    check("norm in de 2e Schil", p2["norm"], 0.80)
    check("eis nieuw in de 2e Schil", p2["eis_nieuw"], 3)
    check("geen vrijstelling buiten gereguleerd gebied",
          p2["vrijstelling"], False)
    if p2["tekort"] <= p1["tekort"]:
        fouten.append(f"het tekort in de 2e Schil ({p2['tekort']}) is niet "
                      f"hoger dan in de Binnenstad ({p1['tekort']}), terwijl "
                      f"de norm daar hoger is")

    # ZONDER ZONE GEEN EIS, en de reden wijst naar waar de zone staat.
    p3 = parkeren({"bestaand": "1"}, 3)
    check("zonder zone geen norm", p3["norm"], None)
    check("zonder zone geen tekort", p3["tekort"], None)
    if "voorraad.json" not in p3["reden"]:
        fouten.append(f"zonder zone wijst de reden niet naar de bron: "
                      f"{p3['reden']!r}")

    # ZONDER WONINGTYPE GEEN GETAL MAAR EEN BANDBREEDTE.
    p4 = parkeren({"bestaand": "1", "parkeerzone": "Centrumgebied"}, 3)
    check("zonder type geen norm", p4["norm"], None)
    band = p4.get("band") or {}
    check("de bandbreedte in het Centrumgebied",
          (band.get("laag"), band.get("hoog")), (0.20, 1.20))
    # EN DE REDEN MOET ZEGGEN WAT ER MIST. Zonder deze regel is de aparte tak
    # voor een ontbrekend woningtype niet na te meten: de doorval naar de
    # tabel geeft ook geen norm, maar wel de reden "woningtype '' staat niet
    # in de tabel", en dat is voor de lezer van het rapport een raadsel in
    # plaats van een aanwijzing.
    if "geen woningtype opgegeven" not in p4["reden"]:
        fouten.append(f"zonder woningtype zegt de reden niet dat het type "
                      f"mist: {p4['reden']!r}")

    # EEN BESCHADIGDE CEL LEVERT GEEN EIS, ook al staat er een waarde.
    p5 = parkeren({"bestaand": "1", "parkeerzone": "1e Schil",
                   "woningtype": "koop appartement betaalbaar"}, 3)
    check("een onzekere cel geeft geen tekort", p5["tekort"], None)
    check("de waarde blijft wel zichtbaar", p5["norm"], 1.00)
    check("en heet onzeker", p5["onzeker"], True)

    # DE TEKST MAG GEEN EIS NOEMEN ALS ER GEEN NORM IS. Een rapport dat een
    # getal noemt waar er geen is, is erger dan een rapport dat het weglaat.
    tekst = rapport({"pand": "Proefstraat 1", "parkeerzone": "Centrumgebied"},
                    {"A": {"voldoet": True, "go": 50, "verblijfsgebied": 30,
                           "eis_55pct": 27.5, "verschil": 2.5, "ruimten": []}},
                    p4)
    if "Geen parkeereis berekend" not in tekst:
        fouten.append("het rapport zegt niet dat er geen eis is berekend")
    if "loopt de norm van 0.2" not in tekst:
        fouten.append(f"het rapport noemt de bandbreedte niet")

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef splitsingstoets: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--in", dest="bron", default="")
    ap.add_argument("--uit", default="")
    args = ap.parse_args()
    if args.proef:
        return proef()
    if not args.bron:
        print("Geef --in of --proef mee.", file=sys.stderr)
        return 1
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
