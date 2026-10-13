#!/usr/bin/env python3
"""
De maten per bouwlaag uit een vergunningstekening lezen.

WAAROM DIT BESTAAT. Ons splitsmodel rekent met VERHUURBAAR_SPLITSING = 0.90:
tien procent verlies aan gedeelde entree en trappenhuis, over het hele pand.
Dat getal is nooit tegen een echte tekening gehouden. Staringstraat 2 zegt
iets anders: 254,12 m2 woonfunctie en 150,7 m2 in zelfstandige woningen, dus
59 procent. Laat je de kelder weg, die volledig naar bergingen en een
fietsenstalling gaat, dan is het 88 procent over de drie woonlagen. Een
pand met een kelder verliest dus veel meer dan tien procent, en een pand
zonder kelder iets meer dan tien. Dat verschil zit nu nergens in.

Een pand is geen regel. Daarom haalt bijlagen.py de tekeningen op bij alle
splitsingspublicaties die wij volgen, en leest deze module daaruit de maten.
Pas met genoeg panden valt er iets te ijken.

WAT ER WEL EN NIET IN DE TEKSTLAAG STAAT. Nagemeten op de bladen van
Staringstraat 2: de ruimtelabels in de plattegrond ("woonkamer 20,9 m2")
staan er als vector in en komen niet mee als tekst. Het overzichtsblad wel,
volledig: de gebruiksoppervlakte per brandcompartiment, het totaal aan
woonfunctie en de extra beschermde vluchtroute. Dat zijn precies de getallen
die wij nodig hebben, dus deze module leest het overzichtsblad en niet de
plattegrond zelf.

WAT DEZE MODULE NIET BEWEERT. Een brandcompartiment is geen woning. Op
Staringstraat 2 zijn er vier compartimenten en drie appartementen: het
vierde is de kelder met de entree. Het aantal compartimenten is dus een
bovengrens voor het aantal woningen en geen telling ervan. Deze module zegt
dat ook zo, want een getal dat iets anders betekent dan het heet, is erger
dan geen getal.
"""

import argparse
import re
import sys

# De vormen zoals ze op een echt blad staan. Niet verzonnen: afgelezen van
# het overzichtsblad van Staringstraat 2, waar "ca." er soms wel en soms niet
# tussen staat en waar de komma het decimaalteken is.
MAAT = r"(\d{1,4}(?:[.,]\d{1,2})?)\s*m2"
RE_COMPARTIMENT = re.compile(r"Brandcompartiment\s*(\d+)[^0-9]{0,30}?" + MAAT,
                             re.I)
RE_VLUCHTROUTE = re.compile(r"vluchtroute[^0-9]{0,30}?" + MAAT, re.I)
RE_WOONFUNCTIE = re.compile(r"WOONFUNCTIE[^0-9]{0,60}?" + MAAT, re.I)

# De laagnamen zoals een tekenaar ze onder een plattegrond zet.
LAGEN = ("kelder", "souterrain", "begane grond", "1e verdieping",
         "2e verdieping", "3e verdieping", "4e verdieping", "zolder")


def getal(s):
    """"58,31" en "58.31" zijn hetzelfde getal. "1.234" is dat niet."""
    s = (s or "").strip()
    if not s:
        return None
    # Een punt met precies drie cijfers erachter is een duizendtalscheiding
    # en geen decimaalteken. Op een tekening komt dat niet voor, maar deze
    # functie leest ook wat anderen schrijven.
    if re.fullmatch(r"\d{1,3}\.\d{3}", s):
        s = s.replace(".", "")
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def maten_uit(tekst):
    """
    De maten van het overzichtsblad. Alles dat ontbreekt blijft None of leeg.

    Nooit een nul voor iets dat niet is gevonden: nul vierkante meter
    vluchtroute en geen opgave van de vluchtroute zijn verschillende dingen,
    en in de brief zouden ze hetzelfde lezen.
    """
    # WITRUIMTE EERST GELIJKTREKKEN. pdftotext -layout houdt de opmaak van
    # het blad aan, dus tussen "WOONFUNCTIE gelegen" en "ca. 254,12 m2" staat
    # een regelafbreking met tientallen spaties. De patronen hieronder laten
    # een beperkt aantal tekens toe tussen het woord en het getal, en zonder
    # dit gelijktrekken viel het totaal daar net buiten: de module gaf keurig
    # vier compartimenten en geen totaal.
    t = re.sub(r"\s+", " ", tekst or "")
    comp = []
    for m in RE_COMPARTIMENT.finditer(t):
        g = getal(m.group(2))
        if g:
            comp.append({"nummer": int(m.group(1)), "m2": g})
    # Hetzelfde compartiment kan twee keer op een blad staan, bijvoorbeeld in
    # de legenda en bij de tekening. Het hoogste nummer is er maar een.
    gezien, net = set(), []
    for c in sorted(comp, key=lambda c: c["nummer"]):
        if c["nummer"] in gezien:
            continue
        gezien.add(c["nummer"])
        net.append(c)

    vlucht = RE_VLUCHTROUTE.search(t)
    woon = [getal(m.group(1)) for m in RE_WOONFUNCTIE.finditer(t)]
    woon = [w for w in woon if w]
    return {
        "compartimenten": net,
        "vluchtroute_m2": getal(vlucht.group(1)) if vlucht else None,
        # Het grootste woonfunctiegetal op het overzichtsblad is het totaal;
        # de kleinere zijn de losse lagen. Dat is geen aanname maar volgt uit
        # wat het woord betekent: het totaal kan niet kleiner zijn dan een
        # laag. Staat er maar een, dan is dat het totaal.
        "woonfunctie_totaal_m2": max(woon) if woon else None,
        "woonfunctie_gevonden": len(woon),
    }


def lagen_uit(woorden):
    """
    De woonfunctie per bouwlaag, uit woorden met coordinaten.

    WAAROM COORDINATEN. Op een blad staan twee plattegronden naast elkaar,
    elk met een eigen laagnaam eronder en een eigen woonfunctiegetal. In
    platte tekst lopen die twee kolommen door elkaar heen, en dan hoort 56,4
    m2 ineens bij de begane grond in plaats van bij de kelder. Met de x-as
    erbij is het eenvoudig: elk getal hoort bij de laagnaam die er het
    dichtst bij staat.

    woorden is een lijst (xMin, yMin, xMax, yMax, tekst).
    """
    if not woorden:
        return []
    # De laagnaam onder een plattegrond staat in een groter lettertype dan de
    # maatvoering. Zonder die eis komen ook de laagnamen uit de legenda mee.
    hoog = [w for w in woorden if (w[3] - w[1]) > 12]
    labels = []
    for i, w in enumerate(hoog):
        woord = w[4].lower()
        vervolg = " ".join(x[4] for x in hoog[i:i + 2]).lower()
        for laag in LAGEN:
            eerste = laag.split()[0]
            if woord == eerste or woord == eerste + ":":
                if " " not in laag or vervolg.startswith(laag):
                    labels.append({"laag": laag, "x": w[0], "y": w[1]})
                break
    if not labels:
        return []
    # HET ONDERSCHRIFT EN NIET HET TITELBLOK. Op blad 3 staat "1e en 2e
    # verdieping" ook in het titelblok rechtsonder, met de twee labels vlak
    # naast elkaar. De onderschriften staan juist ver uit elkaar, want ze
    # horen bij twee tekeningen naast elkaar. De rij met de grootste spreiding
    # over de x-as is dus de goede. Eerst stond hier de middelste y-waarde, en
    # die koos op blad 3 het titelblok.
    rijen = {}
    for lab in labels:
        rijen.setdefault(round(lab["y"] / 25), []).append(lab)
    beste = max(rijen.values(),
                key=lambda rij: (max(l["x"] for l in rij)
                                 - min(l["x"] for l in rij)))
    kolommen = sorted(beste, key=lambda l: l["x"])

    uit = [{"laag": k["laag"], "woonfunctie_m2": None} for k in kolommen]
    for i, w in enumerate(woorden):
        if w[4].lower() not in ("m2", "m²"):
            continue
        omgeving = " ".join(x[4] for x in woorden[max(0, i - 8):i + 1])
        if "woonfunctie" not in omgeving.lower():
            continue
        # HET GETAL DAT ER DIRECT VOOR STAAT, EN NIET HET EERSTE IN HET
        # VENSTER. Eerst zocht deze regel het eerste getal in de omgeving.
        # Bij twee plattegronden naast elkaar valt het getal van de linker
        # kolom ook in dat venster, en dan kreeg de begane grond de 56,4 van
        # de kelder: precies de fout die deze functie moet voorkomen, maar
        # dan een regel later.
        g = None
        for terug in range(i - 1, max(-1, i - 4), -1):
            g = getal(woorden[terug][4])
            if g:
                break
        if not g:
            continue
        j = min(range(len(kolommen)),
                key=lambda k: abs(w[0] - kolommen[k]["x"]))
        if uit[j]["woonfunctie_m2"] is None:
            uit[j]["woonfunctie_m2"] = g
    return uit


def woorden_uit_bbox(xml):
    """De woorden met hun coordinaten uit de uitvoer van pdftotext -bbox."""
    return [(float(a), float(b), float(c), float(d), e) for a, b, c, d, e in
            re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" '
                       r'xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',
                       xml or "")]


def proef():
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. DE MATEN VAN EEN ECHT OVERZICHTSBLAD.
    # De regels hieronder staan zo op het overzichtsblad van de aanvraag voor
    # Staringstraat 2. De getallen zijn onze eigen waarneming; de tekening
    # zelf staat nergens in deze repo.
    blad = ("extra beschermde vluchtroute GO ca.15,72 m2 "
            "WOONFUNCTIE gelegen in een woongebouw ca. 254,12 m2 "
            "Brandcompartiment 1, GO ca. 58,31 m2 "
            "Brandcompartiment 2, GO ca. 58,30 m2 "
            "Brandcompartiment 3, GO ca. 44,59 m2 "
            "Brandcompartiment 4, GO ca. 69,89 m2 ")
    m = maten_uit(blad)
    check("aantal compartimenten", len(m["compartimenten"]), 4)
    check("maten", [c["m2"] for c in m["compartimenten"]],
          [58.31, 58.3, 44.59, 69.89])
    check("vluchtroute", m["vluchtroute_m2"], 15.72)
    check("woonfunctie totaal", m["woonfunctie_totaal_m2"], 254.12)

    # 1b. ZOALS HET BLAD HET WERKELIJK AFLEVERT, met de opmaak erin.
    # pdftotext -layout houdt de kolommen van het blad aan, dus tussen
    # "WOONFUNCTIE gelegen" en het getal staat een regelafbreking met een
    # sliert spaties. Zonder de witruimte gelijk te trekken gaf deze module
    # keurig vier compartimenten en geen totaal, en dat las als "dit blad
    # vermeldt geen totaal".
    opgemaakt = ("            extra beschermde vluchtroute GO ca.15,72 m2\n"
                 "\n\n"
                 "            WOONFUNCTIE gelegen\n"
                 "            in een woongebouw                ca. 254,12 m2\n"
                 "\n"
                 "            Brandcompartiment 1, GO ca. 58,31 m2\n")
    mo = maten_uit(opgemaakt)
    check("totaal door de opmaak heen", mo["woonfunctie_totaal_m2"], 254.12)
    check("vluchtroute door de opmaak heen", mo["vluchtroute_m2"], 15.72)
    check("compartiment door de opmaak heen",
          [c["m2"] for c in mo["compartimenten"]], [58.31])

    # 2. HETZELFDE COMPARTIMENT TWEE KEER TELT EEN KEER.
    check("dubbel compartiment",
          len(maten_uit(blad + "Brandcompartiment 1, GO ca. 58,31 m2")
              ["compartimenten"]), 4)

    # 3. WAT ONTBREEKT IS None EN GEEN NUL. Nul vierkante meter vluchtroute
    # en geen opgave zijn verschillende dingen, en in de brief zouden ze
    # hetzelfde lezen.
    leeg = maten_uit("een blad zonder enige maat")
    check("geen vluchtroute", leeg["vluchtroute_m2"], None)
    check("geen woonfunctie", leeg["woonfunctie_totaal_m2"], None)
    check("geen compartimenten", leeg["compartimenten"], [])
    check("leegte", maten_uit(""), maten_uit(None))

    # 4. KOMMA EN PUNT ZIJN HETZELFDE DECIMAALTEKEN.
    check("komma", getal("58,31"), 58.31)
    check("punt", getal("58.31"), 58.31)
    check("duizendtal", getal("1.234"), 1234.0)
    check("rommel", getal("ca."), None)
    check("niets", getal(""), None)

    # 5. TWEE PLATTEGRONDEN NAAST ELKAAR KRIJGEN ELK HUN EIGEN GETAL.
    # Dit is de fout waar het om gaat: in platte tekst loopt de linker kolom
    # door de rechter heen en krijgt de begane grond het getal van de kelder.
    # De coordinaten hieronder zijn die van blad 2 van Staringstraat 2.
    woorden = [
        (127.1, 665.1, 180.0, 684.2, "kelder"),
        (722.5, 669.0, 790.0, 687.7, "begane"),
        (795.0, 669.0, 850.0, 687.0, "grond"),
        (120.0, 560.0, 160.0, 570.0, "WOONFUNCTIE"),
        (120.0, 568.0, 160.0, 578.0, "56.4"),
        (164.2, 568.8, 180.0, 578.0, "m2"),
        (715.0, 560.0, 755.0, 570.0, "WOONFUNCTIE"),
        (715.0, 568.0, 755.0, 578.0, "69.4"),
        (759.6, 569.1, 775.0, 578.0, "m2"),
    ]
    lagen = lagen_uit(woorden)
    check("twee lagen", [(l["laag"], l["woonfunctie_m2"]) for l in lagen],
          [("kelder", 56.4), ("begane grond", 69.4)])

    # 6. HET ONDERSCHRIFT WINT VAN HET TITELBLOK.
    # Op blad 3 staat "1e en 2e verdieping" ook rechtsonder in het titelblok,
    # met de labels vlak naast elkaar. Eerst koos deze functie op de middelste
    # y-waarde, en dan won het titelblok en bleven beide lagen leeg.
    met_titelblok = [
        (127.8, 668.7, 170.0, 685.6, "1e"),
        (175.0, 668.7, 250.0, 685.0, "verdieping"),
        (722.2, 667.7, 760.0, 685.9, "2e"),
        (765.0, 667.7, 840.0, 685.0, "verdieping"),
        (491.4, 794.0, 510.0, 810.9, "1e"),
        (531.0, 793.0, 550.0, 811.2, "2e"),
        (575.0, 793.0, 650.0, 811.0, "verdieping"),
        (120.0, 560.0, 160.0, 570.0, "WOONFUNCTIE"),
        (120.0, 568.0, 160.0, 578.0, "55.9"),
        (164.2, 568.8, 180.0, 578.0, "m2"),
        (715.0, 560.0, 755.0, 570.0, "WOONFUNCTIE"),
        (715.0, 568.0, 755.0, 578.0, "45.3"),
        (759.6, 569.1, 775.0, 578.0, "m2"),
    ]
    lagen2 = lagen_uit(met_titelblok)
    check("onderschrift wint",
          [(l["laag"], l["woonfunctie_m2"]) for l in lagen2],
          [("1e verdieping", 55.9), ("2e verdieping", 45.3)])

    # 7. ZONDER LAAGNAAM GEEN LAGEN, en dat is geen fout maar een uitkomst.
    check("blad zonder laagnaam", lagen_uit(
        [(10.0, 10.0, 20.0, 30.0, "doorsnede")]), [])
    check("geen woorden", lagen_uit([]), [])

    print(f"Proef plattegrond: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--pdf", default="", help="een tekening om te meten")
    args = ap.parse_args()
    if args.proef:
        return proef()
    if not args.pdf:
        print("Geef --pdf of --proef.", file=sys.stderr)
        return 1
    import subprocess
    plat = subprocess.run(["pdftotext", "-layout", "-q", args.pdf, "-"],
                          capture_output=True).stdout.decode("utf-8", "replace")
    bbox = subprocess.run(["pdftotext", "-bbox-layout", "-q", args.pdf, "-"],
                          capture_output=True).stdout.decode("utf-8", "replace")
    m = maten_uit(plat)
    print(f"compartimenten: {[c['m2'] for c in m['compartimenten']]}",
          file=sys.stderr)
    print(f"vluchtroute: {m['vluchtroute_m2']}", file=sys.stderr)
    print(f"woonfunctie totaal: {m['woonfunctie_totaal_m2']}", file=sys.stderr)
    for blz in re.split(r"<page ", bbox)[1:]:
        lagen = lagen_uit(woorden_uit_bbox(blz))
        if lagen:
            print(f"  lagen: {[(l['laag'], l['woonfunctie_m2']) for l in lagen]}",
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
