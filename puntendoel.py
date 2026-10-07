#!/usr/bin/env python3
"""
De puntentelling omgedraaid: van schatting naar programma van eisen.

Bij een pand dat we nog niet bezitten kennen we de keuken, het sanitair en de
buitenruimte niet, en daarom geeft het model een ondergrens. Dat is een
beperking zolang je de punten probeert te RADEN. Draai je het om, dan is het
geen beperking meer maar een opdracht: welk puntenaantal willen we halen, en
wat moet de verbouwing dan opleveren?

Dat is bruikbaar op twee momenten. Bij een bod, omdat je dan weet welke
ingrepen in de begroting moeten. En bij de aannemer, omdat de eis dan niet
"een nette keuken" is maar "een aanrecht van minstens twee meter", en dat is
toetsbaar.

De drempels die ertoe doen:
- 187 punten voor een zelfstandige woning: daarboven vervalt de wettelijke
  maximumhuur en mag de vrije sector in.
- elk punt daaronder is geld: de huurtabel loopt in stappen van ongeveer €7
  per punt per maand.

De hefbomen worden niet uit een tabel overgenomen maar gemeten: het script
rekent de telling door met en zonder elke maatregel, zodat de waarde klopt met
het stelsel zoals wwso.py dat implementeert. Verandert dat stelsel, dan
verandert deze uitkomst mee.
"""
import argparse
import sys

try:
    from wwso import wws_punten, WWS_TABEL
except ImportError:
    print("wwso.py niet gevonden", file=sys.stderr)
    raise

# De maatregelen die een eigenaar werkelijk in de hand heeft, met de waarde
# die in de telling wordt ingevuld. De punten die ze opleveren worden
# hieronder gemeten, niet aangenomen.
MAATREGELEN = [
    ("aanrecht van 2 meter",      dict(aanrecht_m=2.0)),
    ("aanrecht van 3 meter",      dict(aanrecht_m=3.0)),
    ("aanrecht van 4 meter",      dict(aanrecht_m=4.0)),
    ("badkamer met ligbad en tweede toilet", dict(sanitair_punten=11)),
    ("badkamer ruim uitgevoerd",  dict(sanitair_punten=14)),
    ("balkon of terras van 8 m2", dict(buiten_m2=8.0)),
    ("balkon of terras van 14 m2", dict(buiten_m2=14.0)),
    ("berging van 7 m2",          dict(overige_m2=7.0)),
]
LABELSTAPPEN = ["G", "F", "E", "D", "C", "B", "A", "A+", "A++"]


def basis(opp, woz, label):
    """De telling zoals het model hem nu maakt: zonder de onbekende rubrieken."""
    return wws_punten(opp, woz, label=label, sanitair_punten=7, buiten_m2=0,
                      overige_m2=0, aanrecht_m=2.0)


def hefbomen(opp, woz, label):
    """Wat elke maatregel werkelijk oplevert, gemeten in plaats van aangenomen."""
    nul = basis(opp, woz, label)["punten"]
    uit = []
    for naam, kenmerk in MAATREGELEN:
        argumenten = dict(sanitair_punten=7, buiten_m2=0, overige_m2=0,
                          aanrecht_m=2.0)
        argumenten.update(kenmerk)
        r = wws_punten(opp, woz, label=label, **argumenten)
        winst = r["punten"] - nul
        if winst > 0:
            uit.append((naam, winst))
    # Labelstappen apart: die zijn cumulatief en kosten het meest.
    if label and label.upper() in LABELSTAPPEN:
        i = LABELSTAPPEN.index(label.upper())
        for doel in LABELSTAPPEN[i + 1:i + 4]:
            r = wws_punten(opp, woz, label=doel, sanitair_punten=7,
                           buiten_m2=0, overige_m2=0, aanrecht_m=2.0)
            winst = r["punten"] - nul
            if winst > 0:
                uit.append((f"energielabel naar {doel}", winst))
    uit.sort(key=lambda x: -x[1])
    return nul, uit


def programma(opp, woz, label, doel=187):
    """Welke maatregelen samen het doel halen, de goedkoopste eerst in punten."""
    nul, lijst = hefbomen(opp, woz, label)
    tekort = doel - nul
    r = {"nu": nul, "doel": doel, "tekort": max(0, tekort), "hefbomen": lijst}
    if tekort <= 0:
        r["conclusie"] = (f"haalt de {doel} punten al zonder extra maatregelen; "
                          f"de telling staat op {nul}")
        return r
    def groep_van(naam):
        # Niet alle maatregelen zijn te stapelen: van drie aanrechtvarianten
        # telt er een, en van twee badkamervarianten ook.
        return ("aanrecht" if "aanrecht" in naam else
                "badkamer" if "badkamer" in naam else
                "buiten" if ("balkon" in naam or "terras" in naam) else
                "label" if "label" in naam else naam)

    # De KLEINSTE maatregel die het tekort alleen al dekt. Eerder pakte dit de
    # grootste: bij een tekort van acht punten kwam er "energielabel naar A" uit
    # met achttien punten, terwijl label C met acht punten precies genoeg is.
    # Een eis die verder gaat dan nodig kost geld dat niets oplevert.
    genoeg = [(n, p) for n, p in lijst if p >= tekort]
    if genoeg:
        naam, winst = min(genoeg, key=lambda x: x[1])
        gekozen, totaal = [(naam, winst)], winst
    else:
        # Stapelen, de kleinste eerst, tot het tekort gedekt is.
        gekozen, gehad, totaal = [], set(), 0
        for naam, winst in sorted(lijst, key=lambda x: x[1]):
            groep = groep_van(naam)
            if groep in gehad:
                continue
            gehad.add(groep)
            gekozen.append((naam, winst))
            totaal += winst
            if totaal >= tekort:
                break
    r["gekozen"] = gekozen
    r["haalbaar"] = totaal >= tekort
    r["samen"] = totaal
    return r


# De scheiding die er bij een splitsing toe doet. Het energielabel en de
# isolatie zitten aan de SCHIL van het gebouw: die werk je één keer uit en hij
# geldt voor alle eenheden. De keuken, het sanitair, de buitenruimte en de
# berging zijn per eenheid, en die staan dus zo vaak in het bestek als er
# eenheden zijn.
GEBOUWGEBONDEN = ("label", "isolatie", "schil")


def _is_gebouwgebonden(naam):
    return any(w in naam.lower() for w in GEBOUWGEBONDEN)


def programma_gesplitst(opp_totaal, aantal, woz_totaal, label, doel=187):
    """
    Het programma van eisen voor een pand dat in meerdere eenheden gaat.

    Elke eenheid heeft zijn eigen puntentelling, dus in beginsel zijn er net
    zoveel programma's als eenheden. Zijn de eenheden even groot, wat bij een
    opdeling per woonlaag meestal zo is, dan is er één programma dat per
    eenheid geldt, plus één eis aan het gebouw als geheel.

    De WOZ per eenheid kennen we niet; die wordt afgeleid uit de WOZ van het
    pand gedeeld door het aantal. Dat is een aanname en staat als zodanig in
    de uitkomst.
    """
    if not (opp_totaal and aantal and woz_totaal):
        return None
    opp_eenheid = opp_totaal / aantal
    woz_eenheid = int(woz_totaal / aantal)
    r = programma(opp_eenheid, woz_eenheid, label, doel)
    r["opp_per_eenheid"] = round(opp_eenheid, 1)
    r["woz_per_eenheid"] = woz_eenheid
    r["aantal"] = aantal
    r["gebouw"] = [(n, p) for n, p in r.get("gekozen", [])
                   if _is_gebouwgebonden(n)]
    r["per_eenheid"] = [(n, p) for n, p in r.get("gekozen", [])
                        if not _is_gebouwgebonden(n)]
    return r


def tekst_gesplitst(opp_totaal, aantal, woz_totaal, label, doel=187):
    r = programma_gesplitst(opp_totaal, aantal, woz_totaal, label, doel)
    if not r:
        return "Onvoldoende gegevens."
    uit = [f"## Programma van eisen bij {aantal} eenheden", "",
           f"_Pand van {opp_totaal} m2 wordt {aantal} eenheden van "
           f"{r['opp_per_eenheid']} m2. WOZ per eenheid geschat op "
           f"€{r['woz_per_eenheid']:,}".replace(",", ".")
           + f" door de WOZ van het pand te delen; dat is een aanname. "
           f"Label nu {label or 'onbekend'}._", ""]
    if not r["tekort"]:
        uit.append(f"Elke eenheid haalt de {doel} punten al: de telling komt "
                   f"op {r['nu']}.")
        return "\n".join(uit)
    uit.append(f"Elke eenheid staat op **{r['nu']} punten** en komt "
               f"**{r['tekort']}** te kort voor de vrije sector.")
    uit.append("")
    if r["gebouw"]:
        uit.append("### Eén keer, aan het gebouw")
        uit.append("")
        for naam, winst in r["gebouw"]:
            uit.append(f"- {naam}: +{winst} punten per eenheid")
        uit.append("")
        uit.append("_Dit is een eis aan de schil en geldt voor alle eenheden "
                   "tegelijk: isolatie, glas, installatie. Eén bestek, één "
                   "aannemer, en de winst telt in elke eenheid._")
        uit.append("")
    if r["per_eenheid"]:
        uit.append(f"### {aantal} keer, per eenheid")
        uit.append("")
        for naam, winst in r["per_eenheid"]:
            uit.append(f"- {naam}: +{winst} punten")
        uit.append("")
        uit.append(f"_Deze eisen staan {aantal} keer in de begroting._")
        uit.append("")
    if r.get("haalbaar"):
        uit.append(f"Samen **+{r['samen']} punten** per eenheid, dus "
                   f"{r['nu'] + r['samen']} in totaal. Elke eenheid haalt de "
                   f"vrije sector.")
    else:
        totaal_na = r["nu"] + r["samen"]
        uit.append(f"Samen +{r['samen']} per eenheid, dus {totaal_na}. "
                   f"Dat haalt de {doel} niet: bij deze maat en WOZ blijven de "
                   f"eenheden gereguleerd.")
        uit.append("")
        # Is de vrije sector onbereikbaar, dan is het doel niet 187 punten maar
        # een zo hoog mogelijk wettelijk maximum. Elk punt is dan geld, en dat
        # is het getal waarop je de verbouwing afweegt.
        nu_huur = WWS_TABEL.get(int(r["nu"]))
        na_huur = WWS_TABEL.get(int(totaal_na))
        if nu_huur and na_huur:
            winst_mnd = (na_huur - nu_huur) * aantal
            uit.append(f"**Dan is 187 punten het verkeerde doel.** Het gaat om "
                       f"een zo hoog mogelijk wettelijk maximum. Per eenheid "
                       f"gaat de maximumhuur van €{nu_huur:.2f} naar "
                       f"€{na_huur:.2f}, dus over {aantal} eenheden "
                       f"€{winst_mnd:,.0f} per maand meer".replace(",", ".")
                       + f" of €{winst_mnd * 12:,.0f} per jaar.".replace(",", ".")
                       + " Daar weeg je de verbouwing tegen af.")
    return "\n".join(uit)


def tekst(opp, woz, label, doel=187):
    r = programma(opp, woz, label, doel)
    uit = [f"## Programma van eisen voor {doel} punten", "",
           f"_Woning van {opp} m2, WOZ €{woz:,}".replace(",", ".")
           + f", label {label or 'onbekend'}._", ""]
    if not r["tekort"]:
        uit.append(r["conclusie"])
        return "\n".join(uit)
    uit.append(f"De telling staat nu op **{r['nu']} punten** met alleen "
               f"oppervlakte, WOZ en label. Er zijn **{r['tekort']} punten** "
               f"nodig om op {doel} te komen.")
    uit.append("")
    uit.append("Wat de verbouwing moet opleveren:")
    uit.append("")
    uit.append("| eis | punten |")
    uit.append("|---|---:|")
    for naam, winst in r.get("gekozen", []):
        uit.append(f"| {naam} | +{winst} |")
    uit.append("")
    if r.get("haalbaar"):
        uit.append(f"Samen **+{r['samen']} punten**, dus "
                   f"{r['nu'] + r['samen']} in totaal. Daarmee is de grens "
                   f"gehaald.")
    else:
        uit.append(f"Samen +{r['samen']} punten, dus {r['nu'] + r['samen']} in "
                   f"totaal. Dat haalt de {doel} NIET: met deze oppervlakte en "
                   f"WOZ is de grens niet te bereiken met inrichtingsmaatregelen "
                   f"alleen.")
    uit.append("")
    uit.append("Alle hefbomen, los gemeten:")
    uit.append("")
    for naam, winst in r["hefbomen"]:
        uit.append(f"- {naam}: +{winst}")
    uit.append("")
    maximum = WWS_TABEL.get(int(r["nu"]))
    if maximum:
        uit.append(f"_Bij {r['nu']} punten is de wettelijke maximumhuur "
                   f"€{maximum:.2f} per maand. Elk punt scheelt ongeveer €7._")
    return "\n".join(uit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opp", type=float, required=True)
    ap.add_argument("--woz", type=int, required=True)
    ap.add_argument("--label", default=None)
    ap.add_argument("--doel", type=int, default=187)
    ap.add_argument("--eenheden", type=int, default=0,
                    help="splits het pand in dit aantal eenheden")
    args = ap.parse_args()
    if args.eenheden > 1:
        print(tekst_gesplitst(args.opp, args.eenheden, args.woz, args.label,
                              args.doel))
    else:
        print(tekst(args.opp, args.woz, args.label, args.doel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
