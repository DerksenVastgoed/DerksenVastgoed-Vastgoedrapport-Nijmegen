#!/usr/bin/env python3
"""
Een map met gedownloade dossierstukken uitlezen en er maten uit halen.

WAAROM DIT BESTAAT. Het ophalen van de stukken blijft handwerk: de viewer van
de gemeente laat geautomatiseerd ophalen niet toe, en daar werken wij niet
omheen. Maar alles wat daarna komt hoeft Mark niet te doen. Hij zet de
bestanden in een map en deze module leest ze uit: welk pand, welk soort stuk,
en bij een tekening de maten per bouwlaag.

WAT HET UIT EEN MAP HAALT:

  - het adres, uit de tekst van de stukken zelf en niet uit de bestandsnaam,
    want die namen zijn een zootje: "1038-04geb Staringstraat2 260922",
    "260914-BD70-DO-03 nieuw", "verzoekpdf-2026092201714"
  - het zaaknummer, waarmee het dossier aan onze bekendmakingen hangt
  - per stuk wat het is: een besluit, een tekening met plattegronden, of iets
    anders
  - uit de tekeningen: de woonfunctie per bouwlaag, de brandcompartimenten en
    de vluchtroute

WAT ER NOOIT IN DE REPO KOMT. De stukken zelf niet. Op een bouwkundige
tekening rust auteursrecht van de tekenaar, en de gemeente legt ze ter inzage
en niet ter verspreiding. Wat wij eruit meten is onze eigen waarneming en mag
wel; dat is ook het enige dat wij nodig hebben.

WAT HET NIET DOET. Het raadt niet. Een stuk waarvan het adres niet uit de
tekst blijkt, krijgt geen adres, en een tekening zonder leesbare maten levert
geen maten op. Een lege uitkomst is een uitkomst en wordt als zodanig
gemeld, want "wij konden het niet lezen" en "er staat niets" zijn
verschillende dingen.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import besluit as _bes
import plattegrond as _plat

# Een adres in de stukken: straatnaam, huisnummer, en liefst een postcode
# erachter. De postcode maakt het zeker; zonder postcode moet de straatnaam
# minstens twee keer voorkomen, anders is een losse vermelding genoeg om het
# verkeerde pand te kiezen.
RE_ADRES_PC = re.compile(
    r"\b([A-Z][a-zA-Z'\-\.]*(?:straat|weg|laan|plein|singel|kade|dijk|baan|"
    r"pad|hof|dwarsstraat|steeg|markt|gracht|bos)\s*\d+[a-zA-Z]?)\s*,?\s*"
    r"(\d{4}\s?[A-Z]{2})\b")
RE_ADRES = re.compile(
    r"\b([A-Z][a-zA-Z'\-\.]*(?:straat|weg|laan|plein|singel|kade|dijk|baan|"
    r"pad|hof|dwarsstraat|steeg|markt|gracht|bos)\s*\d+[a-zA-Z]?)\b")


def tekst_van(pad):
    """De tekstlaag van een PDF. Zonder uitzondering, een lege string."""
    try:
        r = subprocess.run(["pdftotext", "-layout", "-q", pad, "-"],
                           capture_output=True, timeout=180)
        return (r.stdout or b"").decode("utf-8", "replace")
    except Exception:
        return ""


def bbox_van(pad):
    """Dezelfde PDF met coordinaten, voor de maten per bouwlaag."""
    try:
        r = subprocess.run(["pdftotext", "-bbox-layout", "-q", pad, "-"],
                           capture_output=True, timeout=180)
        return (r.stdout or b"").decode("utf-8", "replace")
    except Exception:
        return ""


def adres_uit(tekst):
    """
    Het adres uit de tekst, of leeg.

    WAAROM NIET UIT DE BESTANDSNAAM. De namen die de gemeente meegeeft zijn
    een zootje: "1038-04geb Staringstraat2 260922-geanonimiseerd.pdf" noemt
    het adres aan elkaar geschreven, "260914-BD70-DO-03 nieuw" noemt het
    helemaal niet, en "verzoekpdf-2026092201714" al helemaal niet. In de
    tekst van het stuk staat het adres wel, netjes, meestal met postcode.

    Met postcode is het zeker. Zonder postcode moet de straatnaam minstens
    twee keer voorkomen: een stuk noemt soms een buurpand of een voorbeeld,
    en dan zou een losse vermelding het verkeerde pand kiezen.
    """
    t = re.sub(r"\s+", " ", tekst or "")
    m = RE_ADRES_PC.search(t)
    if m:
        adres = re.sub(r"\s+", " ", m.group(1)).strip()
        return f"{adres}, {m.group(2).replace(' ', '')}"
    telling = {}
    for m in RE_ADRES.finditer(t):
        a = re.sub(r"\s+", " ", m.group(1)).strip()
        telling[a] = telling.get(a, 0) + 1
    vaak = [a for a, n in telling.items() if n >= 2]
    if len(vaak) == 1:
        return vaak[0]
    return ""


def soort_van(tekst):
    """
    Wat voor stuk dit is, afgeleid uit de inhoud en niet uit de naam.

    De drie soorten die wij uit elkaar moeten houden: een besluit (daar staat
    de uitkomst en de motivering in), een tekening met plattegronden (daar
    staan de maten in), en de rest. De rest gooien wij niet weg, wij noemen
    hem alleen zo.
    """
    t = (tekst or "").lower()
    if ("verleende een omgevingsvergunning" in t
            or "wij besloten over uw aanvraag" in t
            or "u krijgt een omgevingsvergunning" in t):
        return "besluit"
    lagen = [w for w in _plat.LAGEN if w in t]
    ruimtes = [w for w in ("woonkamer", "slaapkamer", "badkamer", "keuken",
                           "overloop", "berging", "entree", "woonfunctie")
               if w in t]
    if lagen and ruimtes:
        return "tekening"
    return "anders"


def lees_bestand(pad):
    """Eén stuk uitlezen. Alles wat niet blijkt, blijft leeg."""
    uit = {"naam": os.path.basename(pad), "bytes": 0, "soort": "",
           "adres": "", "zaaknummer": "", "tekstlaag": False}
    try:
        uit["bytes"] = os.path.getsize(pad)
    except Exception:
        pass
    if not pad.lower().endswith(".pdf"):
        uit["soort"] = "geen pdf"
        return uit
    tekst = tekst_van(pad)
    uit["tekstlaag"] = bool(tekst.strip())
    if not uit["tekstlaag"]:
        # Een scan zonder tekstlaag is geen fout maar een uitkomst: daar
        # moeten wij met het oog naar kijken, en dat hoort te blijken.
        uit["soort"] = "beeld zonder tekstlaag"
        return uit
    uit["soort"] = soort_van(tekst)
    uit["adres"] = adres_uit(tekst)
    velden = _bes.velden_uit(tekst)
    uit["zaaknummer"] = velden["zaaknummer"]
    if uit["soort"] == "besluit":
        for k in ("uitkomst", "uitkomst_reden", "signalen",
                  "besluitdatum", "ontvangen"):
            if velden.get(k):
                uit[k] = velden[k]
    if uit["soort"] == "tekening":
        maten = _plat.maten_uit(tekst)
        uit["compartimenten"] = [c["m2"] for c in maten["compartimenten"]]
        uit["vluchtroute_m2"] = maten["vluchtroute_m2"]
        uit["woonfunctie_totaal_m2"] = maten["woonfunctie_totaal_m2"]
        lagen = []
        for blz in re.split(r"<page ", bbox_van(pad))[1:]:
            for laag in _plat.lagen_uit(_plat.woorden_uit_bbox(blz)):
                if laag["woonfunctie_m2"]:
                    lagen.append(laag)
        uit["lagen"] = lagen
    return uit


def lees_map(map_pad):
    """Alle stukken in een map, gegroepeerd per adres."""
    stukken = []
    for wortel, _mappen, namen in os.walk(map_pad):
        for n in sorted(namen):
            if n.startswith("."):
                continue
            stukken.append(lees_bestand(os.path.join(wortel, n)))
    return stukken


def groepeer(stukken):
    """
    Per adres bij elkaar, met de maten uit de tekeningen erbij.

    Een stuk zonder adres komt onder "onbekend" te staan en wordt niet stil
    weggelaten: een dossier waarvan wij het pand niet kunnen vaststellen is
    iets om te zien, niet om te verbergen.
    """
    per = {}
    for s in stukken:
        sleutel = s.get("adres") or "onbekend"
        d = per.setdefault(sleutel, {"adres": sleutel, "stukken": [],
                                     "zaaknummer": "", "uitkomst": "",
                                     "signalen": "",
                                     "lagen": [], "vluchtroute_m2": None,
                                     "woonfunctie_totaal_m2": None,
                                     "compartimenten": []})
        d["stukken"].append(s)
        if s.get("zaaknummer") and not d["zaaknummer"]:
            d["zaaknummer"] = s["zaaknummer"]
        if s.get("uitkomst") and not d["uitkomst"]:
            d["uitkomst"] = s["uitkomst"]
        if s.get("signalen") and not d.get("signalen"):
            d["signalen"] = s["signalen"]
        for veld in ("vluchtroute_m2", "woonfunctie_totaal_m2"):
            if s.get(veld) and not d[veld]:
                d[veld] = s[veld]
        if s.get("compartimenten") and not d["compartimenten"]:
            d["compartimenten"] = s["compartimenten"]
        for laag in s.get("lagen") or []:
            if laag not in d["lagen"]:
                d["lagen"].append(laag)
    # Een zaaknummer dat onder een adres is gevonden, geldt voor het hele
    # dossier. Een stuk zonder adres dat hetzelfde zaaknummer draagt, hoort
    # daar dus bij en niet onder "onbekend".
    per_zaak = {d["zaaknummer"]: a for a, d in per.items()
                if d["zaaknummer"] and a != "onbekend"}
    if "onbekend" in per and per_zaak:
        blijft = []
        for s in per["onbekend"]["stukken"]:
            doel = per_zaak.get(s.get("zaaknummer") or "")
            if doel:
                per[doel]["stukken"].append(s)
            else:
                blijft.append(s)
        if blijft:
            per["onbekend"]["stukken"] = blijft
        else:
            del per["onbekend"]
    return sorted(per.values(), key=lambda d: d["adres"])


def verhouding(dossier):
    """
    Hoeveel van het vloeroppervlak zelfstandige woning wordt, als er genoeg
    staat om het te berekenen. Anders None, nooit een geschat getal.

    Dit is het getal waar het om begonnen is: ons model rekent met 0,90 over
    het hele pand, en Staringstraat 2 gaf 0,59 inclusief kelder en 0,88 over
    de drie woonlagen.
    """
    totaal = dossier.get("woonfunctie_totaal_m2")
    comp = dossier.get("compartimenten") or []
    if not totaal or not comp:
        return None
    return round(sum(comp) / totaal, 3)


def rapport(dossiers):
    """Een leesbaar blok, zonder iets uit de stukken zelf."""
    r = []
    if not dossiers:
        r.append("De map is leeg of bevat geen leesbare stukken. Dat is iets "
                 "anders dan een dossier zonder maten: er is niets "
                 "aangetroffen.")
        return "\n".join(r) + "\n"
    r.append(f"{len(dossiers)} dossier(s) gelezen.")
    r.append("")
    for d in dossiers:
        r.append(f"### {d['adres']}")
        r.append("")
        soorten = {}
        for s in d["stukken"]:
            soorten[s["soort"]] = soorten.get(s["soort"], 0) + 1
        r.append(f"- {len(d['stukken'])} stuk(ken): "
                 + ", ".join(f"{n}x {k}" for k, n in sorted(soorten.items())))
        if d["zaaknummer"]:
            r.append(f"- zaaknummer {d['zaaknummer']}")
        if d["uitkomst"]:
            r.append(f"- uitkomst: {d['uitkomst']}")
        if d.get("signalen"):
            r.append(f"- let op, deze woorden staan er ook in: "
                     f"{d['signalen']} (meestal standaardtekst, maar zo valt "
                     f"een echte weigering op)")
        if d["lagen"]:
            r.append("")
            r.append("| bouwlaag | woonfunctie |")
            r.append("|---|---:|")
            for laag in d["lagen"]:
                r.append(f"| {laag['laag']} | {laag['woonfunctie_m2']} m2 |")
        if d["compartimenten"]:
            r.append("")
            r.append(f"- brandcompartimenten: "
                     + ", ".join(f"{c} m2" for c in d["compartimenten"]))
        if d["woonfunctie_totaal_m2"]:
            r.append(f"- woonfunctie totaal: {d['woonfunctie_totaal_m2']} m2")
        if d["vluchtroute_m2"]:
            r.append(f"- vluchtroute: {d['vluchtroute_m2']} m2")
        v = verhouding(d)
        if v is not None:
            r.append(f"- **verhouding compartimenten op totaal: {v}** "
                     f"(ons model rekent met 0,9 over het hele pand)")
        r.append("")
    r.append("_Geen enkel stuk staat in de repo: alleen wat wij eruit "
             "hebben gemeten._")
    return "\n".join(r) + "\n"


def proef():
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. HET ADRES KOMT UIT DE TEKST, MET POSTCODE ALS DIE ER IS.
    # Deze zinnen staan zo in de stukken die wij hebben gelezen.
    check("adres met postcode",
          adres_uit("Besluit voor Het verbouwen en uitbreiden tot 6 "
                    "zelfstandige woonruimtes, aan Hatertseweg 338, 6533GP "
                    "Nijmegen"),
          "Hatertseweg 338, 6533GP")
    check("adres met spatie in de postcode",
          adres_uit("aan Staringstraat 2, 6511 PD Nijmegen"),
          "Staringstraat 2, 6511PD")

    # 2. ZONDER POSTCODE MOET DE STRAAT TWEE KEER VOORKOMEN.
    # Een stuk noemt soms een buurpand of een voorbeeld; een losse vermelding
    # is niet genoeg om het pand te kiezen.
    check("twee keer genoemd",
          adres_uit("plan Hatertseweg 338 bouwkundig. Zie ook de doorsnede "
                    "van Hatertseweg 338."),
          "Hatertseweg 338")
    check("een keer genoemd",
          adres_uit("de buren op Hatertseweg 340 hebben bezwaar"), "")
    check("twee verschillende adressen",
          adres_uit("Hatertseweg 338 en Hatertseweg 338 naast "
                    "Biezenstraat 110 en Biezenstraat 110"), "")
    check("geen adres", adres_uit("een stuk zonder adres"), "")

    # 3. HET SOORT KOMT UIT DE INHOUD.
    check("besluit",
          soort_van("Wij besloten over uw aanvraag. U krijgt een "
                    "omgevingsvergunning."), "besluit")
    check("tekening",
          soort_van("begane grond nieuw woonkamer slaapkamer entree"),
          "tekening")
    check("constructieberekening is geen van beide",
          soort_van("berekening van de hoofddraagconstructie, staal S235"),
          "anders")
    # Een gevelaanzicht noemt wel de laag maar geen ruimte: geen tekening met
    # plattegronden, en dus geen maten om uit te lezen.
    check("gevelaanzicht",
          soort_van("voorgevel 1e verdieping 2e verdieping peil"), "anders")

    # 4. STUKKEN ZONDER ADRES KOMEN BIJ HUN DOSSIER VIA HET ZAAKNUMMER.
    stukken = [
        {"naam": "besluit.pdf", "soort": "besluit",
         "adres": "Hatertseweg 338, 6533GP", "zaaknummer": "Z2025-00011358",
         "uitkomst": "verleend"},
        {"naam": "bijlage.pdf", "soort": "anders", "adres": "",
         "zaaknummer": "Z2025-00011358"},
        {"naam": "los.pdf", "soort": "anders", "adres": "", "zaaknummer": ""},
    ]
    g = groepeer(stukken)
    check("aantal dossiers", len(g), 2)
    bij = [d for d in g if d["adres"].startswith("Hatertseweg")]
    check("bijlage bij het dossier", len(bij[0]["stukken"]), 2)
    check("uitkomst overgenomen", bij[0]["uitkomst"], "verleend")
    # Een stuk dat echt nergens bij hoort verdwijnt niet.
    onbekend = [d for d in g if d["adres"] == "onbekend"]
    check("het losse stuk blijft zichtbaar", len(onbekend), 1)

    # 5. DE VERHOUDING WORDT NIET GESCHAT.
    # De getallen hieronder zijn die van Staringstraat 2, door ons gemeten.
    check("verhouding",
          verhouding({"woonfunctie_totaal_m2": 254.12,
                      "compartimenten": [58.31, 58.3, 44.59, 69.89]}), 0.909)
    check("zonder totaal",
          verhouding({"woonfunctie_totaal_m2": None,
                      "compartimenten": [58.31]}), None)
    check("zonder compartimenten",
          verhouding({"woonfunctie_totaal_m2": 254.12,
                      "compartimenten": []}), None)

    # 6. EEN LEGE MAP MELDT ZICHZELF.
    leeg = rapport([])
    if "er is niets aangetroffen" not in leeg:
        fouten.append(f"een lege map meldt zich niet: {leeg[:80]!r}")

    print(f"Proef dossiermap: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="", help="de map met gedownloade stukken")
    ap.add_argument("--uit", default="", help="waar het rapport komt")
    ap.add_argument("--json", default="", help="waar de gemeten velden komen")
    ap.add_argument("--proef", action="store_true")
    args = ap.parse_args()
    if args.proef:
        return proef()
    if not args.map:
        print("Geef --map of --proef.", file=sys.stderr)
        return 1
    if not os.path.isdir(args.map):
        # Een map die er niet is, is iets anders dan een lege map.
        print(f"De map {args.map} bestaat niet.", file=sys.stderr)
        return 1
    dossiers = groepeer(lees_map(args.map))
    tekst = rapport(dossiers)
    print(tekst)
    if args.uit:
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(tekst)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(dossiers, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
