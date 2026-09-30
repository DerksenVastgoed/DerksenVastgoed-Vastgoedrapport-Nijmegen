#!/usr/bin/env python3
"""
Signaleert onderwerpen waarover we nog geen achtergrondstuk hebben.

De achtergrondstukken in bronnen.py leggen uit hoe een regel werkt. Die lijst
is met de hand gemaakt en loopt dus achter op wat er speelt. Dit script kijkt
wat er in het nieuws en de bekendmakingen terugkeert waar wij niets over
zeggen, en verzamelt het bronmateriaal.

WAT HET NIET DOET: zelf het stuk schrijven. Een model dat zijn eigen naslagwerk
maakt over fiscaal of juridisch terrein produceert met evenveel stelligheid iets
wat niet klopt. Het systeem signaleert het gat en levert de bronnen; de tekst
schrijven we zelf.

Gebruik:
  python onderwerpen_signaal.py            # zoek gaten, schrijf een voorstel
  python onderwerpen_signaal.py --dagen 30 # kortere terugblik
"""

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys

VOORSTEL_PAD = "onderwerpen_voorstel.md"
GEZIEN_PAD = "onderwerpen_gezien.json"

# Termen die we voortaan actief volgen in het nieuws. Dit bestand wordt door
# publicaties_vastgoed.py gelezen, dat er zoekopdrachten van maakt.
#
# Zoeken is veilig te automatiseren: een extra zoekopdracht kan geen onjuiste
# bewering opleveren. Het achtergrondstuk dat uitlegt hoe een regel werkt is
# dat niet, en blijft handwerk.
VOLGEN_PAD = "onderwerpen_volgen.json"

# De lijst die jij beheert. Voorstellen landen hier uitgecommentarieerd; haal
# het hekje weg en de term wordt gevolgd. Zo beslist een mens wat relevant is
# en niet een patroon.
KEUZE_PAD = "onderwerpen_volgen.txt"

# Waar dit vak over gaat. Een gevonden term telt alleen mee als hij in dezelfde
# omgeving staat als een van deze woorden. Dat houdt "Besluit standplaatsen
# woonwagens" en "Wet maatschappelijke ondersteuning" buiten de deur zonder dat
# we ze bij naam hoeven te kennen.
EIGEN_VAKGEBIED = {
    "huur", "verhuur", "verhuurder", "huurder", "woning", "woonruimte",
    "wonen", "pand", "vastgoed", "belegger", "belegging", "koopwoning",
    "vergunning", "omzetting", "onttrekking", "splitsen", "splitsing",
    "verkameren", "kamerverhuur", "transformatie", "woningvoorraad",
    "overdrachtsbelasting", "vennootschapsbelasting", "box 3", "btw",
    "hypotheek", "financiering", "rendement", "energielabel", "verduurzaming",
    "monument", "erfgoed", "opkoopbescherming", "puntenstelsel", "wws",
    "huurprijs", "servicekosten", "woningmarkt", "makelaar", "taxatie",
}

# Hoe dicht een vakwoord bij de term moet staan om als context te tellen
CONTEXTVENSTER = 220

# Hoe vaak een term moet terugkeren voordat het een onderwerp is. Onder deze
# grens is het toeval: één artikel over een onderwerp betekent niets.
DREMPEL = 4

# Patronen waarmee regelingen en wetten zich aandienen. Namen van wetgeving
# worden consistent geschreven, dus die zijn betrouwbaar te herkennen.
PATRONEN = [
    r"\bWet\s+(?:op\s+(?:de|het)\s+)?[a-z][\w-]*(?:\s+[a-z][\w-]*){0,2}",
    r"\bBesluit\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,2}",
    r"\bRegeling\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,2}",
    r"\bVerordening\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,2}",
    r"\bbox\s*3\b",
    r"\b[A-Z]{3,6}\s+(?:IV|III|II|I)\b",        # EPBD IV, NTA-achtige codes
    r"\bNTA\s*\d{4}\b",
]

# Woorden die vaak in zo'n patroon meeliften maar geen onderwerp zijn
RUIS = {"wet", "besluit", "regeling", "verordening", "van", "de", "het", "een",
        "voor", "over", "bij", "met", "tot", "aan", "dat", "die", "zijn",
        "wordt", "worden", "is", "en", "of"}

# Werkwoorden en bijwoorden die achter een naam plakken en er niet bij horen.
# Zonder dit telt "Wet vaste huurcontracten wordt geevalueerd" als een andere
# regeling dan "Wet vaste huurcontracten", en haalt geen van beide de drempel.
STAARTWOORDEN = {"wordt", "worden", "werd", "is", "was", "blijft", "blijven",
                 "raakt", "raken", "geldt", "gelden", "mag", "mogen", "moet",
                 "moeten", "kan", "kunnen", "zorgt", "speelt", "opnieuw",
                 "geevalueerd", "gewijzigd", "aangepast", "ingetrokken",
                 "particuliere", "tijdelijke", "voor", "het", "de", "een"}


def _tekstbronnen(dagen):
    """Alle tekst uit de digests en het archief van de laatste periode."""
    grens = dt.date.today() - dt.timedelta(days=dagen)
    stukken = []

    if os.path.isdir("digests"):
        for naam in sorted(os.listdir("digests")):
            m = re.match(r"(\d{4}-\d{2}-\d{2})-", naam)
            if not m:
                continue
            try:
                if dt.date.fromisoformat(m.group(1)) < grens:
                    continue
            except ValueError:
                continue
            try:
                with open(os.path.join("digests", naam), encoding="utf-8") as f:
                    stukken.append(f.read())
            except Exception:
                pass

    # Het bekendmakingen-archief, want daar staan de besluiten met hun titel
    try:
        with open("bekendmakingen_archief.json", encoding="utf-8") as f:
            archief = json.load(f)
        for treffers in archief.values():
            for t in treffers:
                datum = (t.get("datum") or "")[:10]
                try:
                    if datum and dt.date.fromisoformat(datum) < grens:
                        continue
                except ValueError:
                    pass
                stukken.append(t.get("titel", ""))
    except Exception:
        pass

    return "\n".join(stukken)


def _normaliseer(term):
    """Vergelijkbaar maken: kleine letters, enkele spaties."""
    return re.sub(r"\s+", " ", term.strip().lower())


def vind_onderwerpen(tekst):
    """Welke regelingen en begrippen komen hier terug, en hoe vaak?"""
    teller = collections.Counter()
    voorbeelden = {}
    for patroon in PATRONEN:
        for m in re.finditer(patroon, tekst, re.IGNORECASE):
            term = _normaliseer(m.group(0))
            # Achterliggende werkwoorden eraf, zodat dezelfde regeling ook
            # dezelfde naam krijgt en de tellingen bij elkaar opgeteld worden
            delen = term.split()
            while len(delen) > 2 and delen[-1] in STAARTWOORDEN:
                delen.pop()
            term = " ".join(delen)
            woorden = [w for w in delen if w not in RUIS]
            if not woorden:
                continue
            # Staat de term in onze eigen omgeving? Zo niet, dan gaat hij over
            # iets anders en telt hij niet mee.
            start_c = max(0, m.start() - CONTEXTVENSTER)
            omgeving = tekst[start_c:m.end() + CONTEXTVENSTER].lower()
            if not any(w in omgeving for w in EIGEN_VAKGEBIED):
                continue

            teller[term] += 1
            if term not in voorbeelden:
                # De regel eromheen bewaren als context
                start = max(0, m.start() - 90)
                voorbeelden[term] = tekst[start:m.end() + 90].replace("\n", " ")
    return teller, voorbeelden


def bestaande_trefwoorden():
    """Waar hebben we al een achtergrondstuk over?"""
    try:
        from bronnen import ACHTERGROND, ACHTERGROND_TREFWOORDEN
    except Exception:
        return set(), set()
    titels = {_normaliseer(t) for t, _ in ACHTERGROND}
    woorden = set()
    for lijst in ACHTERGROND_TREFWOORDEN.values():
        woorden.update(_normaliseer(w) for w in lijst)
    return titels, woorden


def al_gedekt(term, titels, trefwoorden):
    """
    Hebben we hier al een achtergrondstuk over?

    De toets moet streng zijn op de overeenkomst en niet op losse woorddelen.
    "Wet vaste huurcontracten" is een ander onderwerp dan de Wet goed
    verhuurderschap, ook al komt het woord huurcontract in allebei voor. Daarom
    eisen we dat de hele term of een volledig trefwoord overeenkomt.
    """
    if term in trefwoorden:
        return True
    for t in titels:
        if term in t or t in term:
            return True
    # Een trefwoord van meerdere woorden dat volledig in de term zit, dekt hem
    for w in trefwoorden:
        if " " in w and w in term:
            return True
    return False


def lees_keuze():
    """
    De termen die jij hebt goedgekeurd, uit onderwerpen_volgen.txt.

    Een regel die met een hekje begint is een voorstel dat je nog niet hebt
    aangenomen. Haal het hekje weg en de term wordt vanaf de volgende run
    gevolgd in het nieuws.
    """
    goedgekeurd, voorgesteld = [], []
    if not os.path.exists(KEUZE_PAD):
        return goedgekeurd, voorgesteld
    try:
        with open(KEUZE_PAD, encoding="utf-8") as f:
            for regel in f:
                regel = regel.rstrip("\n")
                kaal = regel.lstrip("#").strip()
                if not kaal or kaal.startswith("-"):
                    continue
                if regel.lstrip().startswith("#"):
                    voorgesteld.append(kaal.lower())
                else:
                    goedgekeurd.append(kaal.lower())
    except Exception:
        pass
    return goedgekeurd, voorgesteld


def schrijf_keuze(nieuwe_voorstellen):
    """Voorstellen onderaan bijschrijven, zonder te raken aan wat er staat."""
    goedgekeurd, voorgesteld = lees_keuze()
    bekend = set(goedgekeurd) | set(voorgesteld)
    toe_te_voegen = [t for t in nieuwe_voorstellen if t.lower() not in bekend]
    if not toe_te_voegen:
        return 0

    kop = []
    if not os.path.exists(KEUZE_PAD):
        kop = [
            "# Onderwerpen die we volgen in het nieuws.",
            "#",
            "# Een regel zonder hekje wordt gevolgd: er komt een zoekopdracht",
            "# voor, en artikelen erover halen de brief. Een regel met een hekje",
            "# is een voorstel dat het script heeft opgemerkt; haal het hekje weg",
            "# om hem aan te nemen, of laat hem staan om hem te negeren.",
            "#",
            "# Het script voegt alleen onderaan toe en verandert nooit iets aan",
            "# wat er al staat. Jouw keuzes blijven dus staan.",
            "",
        ]
    try:
        with open(KEUZE_PAD, "a", encoding="utf-8") as f:
            if kop:
                f.write("\n".join(kop) + "\n")
            f.write(f"\n# --- voorgesteld op {dt.date.today().isoformat()} ---\n")
            for term in toe_te_voegen:
                f.write(f"# {term}\n")
    except Exception as e:
        print(f"Kon {KEUZE_PAD} niet schrijven: {e}", file=sys.stderr)
        return 0
    return len(toe_te_voegen)


def lees_volgen():
    try:
        with open(VOLGEN_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def schrijf_volgen(volgen):
    """
    Bewaart de termen die we volgen, met een opruiming.

    Een term die een half jaar niet meer in het nieuws is geweest, houdt op
    relevant te zijn. Anders groeit de lijst met zoekopdrachten eindeloos en
    wordt elke run trager.
    """
    grens = (dt.date.today() - dt.timedelta(days=180)).isoformat()
    opgeschoond = {t: g for t, g in volgen.items()
                   if g.get("laatst", "") >= grens}
    try:
        with open(VOLGEN_PAD, "w", encoding="utf-8") as f:
            json.dump(opgeschoond, f, ensure_ascii=False, indent=1,
                      sort_keys=True)
    except Exception as e:
        print(f"Kon {VOLGEN_PAD} niet schrijven: {e}", file=sys.stderr)
    weg = len(volgen) - len(opgeschoond)
    if weg:
        print(f"  {weg} termen losgelaten: een half jaar niet meer gezien",
              file=sys.stderr)


def lees_gezien():
    try:
        with open(GEZIEN_PAD, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def schrijf_gezien(termen):
    try:
        with open(GEZIEN_PAD, "w", encoding="utf-8") as f:
            json.dump(sorted(termen), f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dagen", type=int, default=90)
    ap.add_argument("--drempel", type=int, default=DREMPEL)
    ap.add_argument("--uit", default=VOORSTEL_PAD)
    args = ap.parse_args()

    tekst = _tekstbronnen(args.dagen)
    if not tekst.strip():
        print("Geen tekst gevonden om te doorzoeken", file=sys.stderr)
        return

    teller, voorbeelden = vind_onderwerpen(tekst)
    titels, trefwoorden = bestaande_trefwoorden()
    eerder_gemeld = lees_gezien()

    gaten = []
    for term, aantal in teller.most_common():
        if aantal < args.drempel:
            continue
        if al_gedekt(term, titels, trefwoorden):
            continue
        gaten.append((term, aantal, voorbeelden.get(term, "")))

    print(f"Doorzocht: {len(tekst.split())} woorden uit de laatste "
          f"{args.dagen} dagen", file=sys.stderr)
    print(f"Herkende regelingen en begrippen: {len(teller)}", file=sys.stderr)
    print(f"Zonder achtergrondstuk: {len(gaten)}", file=sys.stderr)

    if not gaten:
        if os.path.exists(args.uit):
            os.remove(args.uit)
        return

    nieuw = [g for g in gaten if g[0] not in eerder_gemeld]

    r = ["# Onderwerpen zonder achtergrondstuk", "",
         f"_Gevonden in de laatste {args.dagen} dagen aan nieuws en "
         f"bekendmakingen. Deze termen keren terug terwijl er in bronnen.py "
         f"niets over staat. De tekst schrijven we zelf; dit levert alleen het "
         f"signaal en de context._", ""]
    for term, aantal, context in gaten:
        merk = " (nieuw)" if term in {g[0] for g in nieuw} else ""
        r.append(f"## {term}{merk}")
        r.append(f"_{aantal} keer genoemd._")
        if context:
            r.append("")
            r.append(f"> ...{context.strip()}...")
        r.append("")
    r.append("_Om er een achtergrondstuk van te maken: voeg het toe aan "
             "ACHTERGROND in bronnen.py, met trefwoorden in "
             "ACHTERGROND_TREFWOORDEN zodat het aansluit bij het nieuws._")

    with open(args.uit, "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")
    schrijf_gezien({g[0] for g in gaten} | eerder_gemeld)

    # De voorstellen in de keuzelijst zetten. Alleen wat jij aanneemt wordt
    # daadwerkelijk gevolgd; een patroon mag niet zelf bepalen wat relevant is.
    nieuw_voorgesteld = schrijf_keuze([g[0] for g in gaten])
    if nieuw_voorgesteld:
        print(f"  {nieuw_voorgesteld} voorstellen toegevoegd aan {KEUZE_PAD}",
              file=sys.stderr)

    goedgekeurd, voorgesteld = lees_keuze()
    volgen = lees_volgen()
    for term in goedgekeurd:
        bestaand = volgen.get(term, {})
        volgen[term] = {
            "sinds": bestaand.get("sinds", dt.date.today().isoformat()),
            "gezien": max(teller.get(term, 0), bestaand.get("gezien", 0)),
            "laatst": (dt.date.today().isoformat() if teller.get(term)
                       else bestaand.get("laatst", dt.date.today().isoformat())),
        }
    # Termen die je hebt teruggezet naar voorstel, volgen we niet meer
    for term in list(volgen):
        if term not in goedgekeurd:
            del volgen[term]
    schrijf_volgen(volgen)
    print(f"  {len(goedgekeurd)} termen goedgekeurd, {len(voorgesteld)} in "
          f"afwachting", file=sys.stderr)

    print(f"\nVoorstel weggeschreven naar {args.uit}:", file=sys.stderr)
    for term, aantal, _c in gaten[:8]:
        print(f"  {aantal:>3}x  {term}", file=sys.stderr)


if __name__ == "__main__":
    main()
