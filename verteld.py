#!/usr/bin/env python3
"""
Wat pa al heeft gelezen.

Het probleem dat dit oplost. Op 8 oktober stonden er drie dingen in de brief
die er niet in hadden moeten staan: de prijsverlaging van de Palmstraat 40 voor
de derde dag op rij, twee vergunningen waarover pa al bericht had gehad, en de
Nieuwe Markt 90 als nieuw aanbod terwijl dat pand er al weken in staat.

Dat zijn drie symptomen van een ding. De brief had geen enkele notie van wat er
eerder is verstuurd. Het brieflogboek legt wel vast wat er verteld is, maar
niets las dat ooit terug: het diende alleen de weekeditie, voor het blokje
"wat bleef liggen". De brief kreeg dus elke dag dezelfde gegevens en moest zelf
bedenken wat daarvan nieuw was, en dat kan hij niet weten.

Waarom het met een instructie niet lukte. In de opdracht stond sinds 6 oktober
de regel dat een prijswijziging alleen nieuws is als hij van vandaag of
gisteren is, met de Palmstraat er als voorbeeld bij. Die regel is drie dagen
achter elkaar niet gevolgd. De conclusie daaruit is niet dat de regel beter
moet worden opgeschreven, maar dat een waarschuwing die genegeerd kan worden,
genegeerd wordt. De gegevens moeten het verschil maken, niet de goede wil.

Wat dit bestand doet. Het houdt per onderwerp bij wanneer het voor het eerst en
voor het laatst in een verstuurde brief stond. Een onderwerp is een adres of de
link van een bekendmaking, want dat zijn de twee dingen die een bericht
herkenbaar maken en die in de brieftekst terugkomen. Dat wordt een blok dat
bovenaan de gegevens staat, zodat de brief weet wat pa al weet.

Wat dit bewust NIET doet. Een onderwerp wegfilteren. Een besluit op een
eerdere aanvraag is wel nieuws, ook al ging het over hetzelfde pand, en een
pand dat na drie weken in prijs zakt is dat ook. Het onderscheid tussen "weer
hetzelfde" en "er is iets bij gekomen" kan alleen bij het schrijven worden
gemaakt. Wat hier gebeurt is dat het verschil zichtbaar wordt gemaakt op de
plek waar het nodig is.

TESTRUNS SCHRIJVEN HIER NIETS, net als bij het brieflogboek. Een oefenrun die
zou vastleggen dat iets verteld is, maakt het nieuws van de volgende ochtend
stuk.
"""
import datetime as dt
import json
import os
import re
import sys

PAD = "verteld.json"
BEWAAR_DAGEN = 90
# Hoe lang een onderwerp als "pa kent dit al" geldt. Langer dan drie weken is
# het redelijk om een pand opnieuw te introduceren; dan is het geen herhaling
# meer maar een herinnering.
VENSTER_DAGEN = 21

# Straatnamen in Nijmegen eindigen vrijwel altijd op een van deze woorden. Dit
# is bewust een lijst en geen slimme truc: een regex die elk hoofdletterwoord
# met een getal erachter als adres ziet, pakt ook "Gelderland 5,6" en "BOPA 20".
STRAATEINDEN = (
    "straat", "straatje", "weg", "laan", "laantje", "plein", "singel", "kade",
    "hof", "hofje", "markt", "pad", "dijk", "baan", "steeg", "dwarsstraat",
    "gracht", "park", "veld", "berg", "dal", "daal", "poort", "wal", "brug",
    "ring", "erf", "akker", "kamp", "horst", "beek", "donk", "burg", "huis",
    "stee", "oord", "schans", "haven", "plaats", "dreef", "gang", "hoek",
    "bos", "hout", "straatweg", "weide", "kolk", "sluis",
)
# Tussenwoorden die in een straatnaam voorkomen: Berg EN Dalseweg, VAN
# Welderenstraat, Graaf VAN Roermondstraat.
TUSSENWOORDEN = ("van", "de", "den", "der", "het", "ter", "te", "op", "aan",
                 "en", "'t", "d'", "op den", "in de")
# Woorden die ervoor kunnen staan zonder bij de naam te horen. Die moeten eraf,
# en wel altijd op dezelfde manier: anders wordt "Bij Berg en Dalseweg 11" een
# andere sleutel dan "Berg en Dalseweg 11", en denkt het geheugen dat het twee
# panden zijn. Een vaste lijst is daarvoor beter dan slim raden.
STOPWOORDEN = (
    "bij", "de", "het", "een", "in", "op", "aan", "naar", "voor", "met",
    "over", "dat", "deze", "dit", "die", "en", "ook", "verder", "nu", "al",
    "als", "zie", "is", "was", "er", "we", "ze", "u", "ik", "want", "maar",
    "dan", "toen", "van", "tot", "zoals", "daar", "hier", "om", "ook",
    "bijvoorbeeld", "namelijk", "vandaag", "gisteren", "sinds", "zowel",
)
# Een straatnaam met huisnummer. De naam mag met een tussenwoord beginnen,
# want "van Welderenstraat 89a" is een adres en begon zonder dat met een
# hoofdletter te eisen op "Welderenstraat".
RE_ADRES = re.compile(
    r"\b((?:(?:" + "|".join(TUSSENWOORDEN) + r")\s+)*"
    r"[A-Z][A-Za-zÀ-ÿ.'\-]*"
    r"(?:\s+(?:" + "|".join(TUSSENWOORDEN) + r")\s+[A-Za-zÀ-ÿ.'\-]+"
    r"|\s+[A-Z][A-Za-zÀ-ÿ.'\-]*)*)"
    r"\s+(\d{1,4}[A-Za-z]?(?:\s*-\s*\d{1,4}[A-Za-z]?)?)\b"
    r"(?![,.]\d)(?!\s*%)")
RE_LINK = re.compile(r"https?://[^\s)\]]+")


def _alleen_lezen():
    """
    Draait dit een testrun? Dan niets wegschrijven.

    Dezelfde drie signalen als in brief_logboek, en om dezelfde reden: bij
    twijfel niet schrijven. Een gemiste regel is onschuldig, een onterecht
    afgestreept onderwerp niet.
    """
    testrun = (os.environ.get("TESTRUN") or "").strip().lower()
    if testrun not in ("", "0", "false"):
        return True
    if (os.environ.get("GEHEUGEN_ALLEEN_LEZEN") or "").strip() == "1":
        return True
    try:
        from diagnose import alleen_lezen
        if alleen_lezen():
            return True
    except Exception:
        pass
    return testrun == ""


def sleutel_adres(adres):
    """Een adres tot een sleutel. 11-11A en 11 11a worden hetzelfde."""
    return re.sub(r"[^a-z0-9]", "", (adres or "").lower())


def lees(pad=PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f) or {"onderwerpen": {}}
    except Exception:
        return {"onderwerpen": {}}


def adressen_uit(tekst):
    """
    De adressen die in deze tekst staan, als {sleutel: zoals geschreven}.

    Niet elk hoofdletterwoord met een getal erachter: de straatnaam moet op een
    bekend straatwoord eindigen. Zonder die eis werd "Gelderland 5,6%" een
    adres, en dan staat er onzin in het geheugen.
    """
    uit = {}
    for m in RE_ADRES.finditer((tekst or "").replace("\n", " ")):
        straat = " ".join(m.group(1).split())
        # Woorden eraf die ervoor stonden zonder bij de naam te horen, altijd
        # op dezelfde manier, want de sleutel moet elke dag hetzelfde zijn.
        delen = straat.split()
        while len(delen) > 1 and delen[0].lower().strip(".,") in STOPWOORDEN:
            delen = delen[1:]
        straat = " ".join(delen)
        if not straat.lower().endswith(STRAATEINDEN):
            continue
        nummer = re.sub(r"\s*-\s*", "-", m.group(2).strip())
        heel = f"{straat} {nummer}"
        uit.setdefault(sleutel_adres(heel), heel)
    return uit


def markeer(brieftekst, datum=None, pad=PAD):
    """
    Vastleggen welke onderwerpen in deze brief stonden.

    Wordt aangeroepen nadat de brief is geschreven, dus met de werkelijke
    tekst. Zo hoeft de brief niet zelf op te geven waar hij over ging; er wordt
    naar gekeken. Dat is grof maar betrouwbaarder dan een opgave.
    """
    if _alleen_lezen():
        print("Testrun: verteld.json blijft ongewijzigd", file=sys.stderr)
        return 0
    datum = datum or dt.date.today().isoformat()
    boek = lees(pad)
    onderwerpen = boek.get("onderwerpen") or {}
    nieuw = 0
    gevonden = dict(adressen_uit(brieftekst))
    for link in RE_LINK.findall(brieftekst or ""):
        if "officielebekendmakingen.nl" in link or "/gmb-" in link:
            gevonden.setdefault(link.rstrip(").,"), link.rstrip(").,"))
    for sleutel, omschrijving in gevonden.items():
        rij = onderwerpen.get(sleutel)
        if rij:
            rij["laatst"] = datum
            rij["keer"] = int(rij.get("keer") or 1) + 1
        else:
            onderwerpen[sleutel] = {"eerst": datum, "laatst": datum,
                                    "keer": 1, "omschrijving": omschrijving}
            nieuw += 1
    grens = (dt.date.today() - dt.timedelta(days=BEWAAR_DAGEN)).isoformat()
    onderwerpen = {k: v for k, v in onderwerpen.items()
                   if (v.get("laatst") or "") >= grens}
    try:
        with open(pad, "w", encoding="utf-8") as f:
            json.dump({"onderwerpen": onderwerpen}, f, ensure_ascii=False,
                      indent=1)
    except Exception as e:  # noqa
        print(f"verteld.json niet weggeschreven: {str(e)[:80]}", file=sys.stderr)
        return 0
    print(f"Verteld: {len(gevonden)} onderwerpen in deze brief, "
          f"{nieuw} voor het eerst", file=sys.stderr)
    return nieuw


def eerder(dagen=VENSTER_DAGEN, pad=PAD):
    """Wat er de afgelopen weken in een verstuurde brief stond."""
    grens = (dt.date.today() - dt.timedelta(days=dagen)).isoformat()
    uit = {}
    for sleutel, rij in (lees(pad).get("onderwerpen") or {}).items():
        if (rij.get("laatst") or "") >= grens:
            uit[sleutel] = rij
    return uit


def _nl(datum):
    maanden = ("januari", "februari", "maart", "april", "mei", "juni", "juli",
               "augustus", "september", "oktober", "november", "december")
    try:
        p = dt.date.fromisoformat(datum)
        return f"{p.day} {maanden[p.month - 1]}"
    except Exception:
        return datum


def tekst(dagen=VENSTER_DAGEN, pad=PAD, maximaal=40):
    """
    Het blok voor de gegevens: wat pa al heeft gelezen.

    Staat bovenaan en niet onderaan. Wat pa al weet bepaalt wat vandaag nieuws
    is, dus het hoort gelezen te worden voordat de rest wordt bekeken.
    """
    rijen = eerder(dagen, pad)
    if not rijen:
        return ("Er is nog geen eerdere brief vastgelegd. Alles wat vandaag in "
                "de gegevens staat, is voor pa nieuw.")
    op_datum = sorted(rijen.values(), key=lambda r: r.get("laatst") or "",
                      reverse=True)
    r = ["Dit is al in een eerdere brief aan pa verteld. Breng niets hiervan "
         "opnieuw als nieuws, als vondst of als nieuw aanbod. Je mag een "
         "onderwerp hieronder alleen aanhalen wanneer er vandaag een feit bij "
         "is gekomen dat er eerder niet was, bijvoorbeeld een besluit op een "
         "aanvraag die eerder is gemeld of een prijs die sinds gisteren is "
         "veranderd. Noem dan het nieuwe feit en niet opnieuw het hele "
         "verhaal, en schrijf erbij dat het een vervolg is.", ""]
    for rij in op_datum[:maximaal]:
        omschrijving = rij.get("omschrijving") or "?"
        if omschrijving.startswith("http"):
            omschrijving = f"de bekendmaking op {omschrijving}"
        keer = int(rij.get("keer") or 1)
        regel = f"- {omschrijving}: laatst gemeld op {_nl(rij.get('laatst'))}"
        if rij.get("eerst") and rij["eerst"] != rij.get("laatst"):
            regel += f", voor het eerst op {_nl(rij['eerst'])}"
        if keer > 1:
            regel += f", in totaal {keer} brieven"
        r.append(regel)
    if len(op_datum) > maximaal:
        r.append(f"- en nog {len(op_datum) - maximaal} eerdere onderwerpen")
    return "\n".join(r)


def waarschuwing(brontekst, dagen=VENSTER_DAGEN, pad=PAD):
    """
    Een gerichte waarschuwing bij een brontekst, met de adressen erin genoemd.

    Een algemene regel bovenaan de opdracht is drie dagen achter elkaar
    genegeerd. Een waarschuwing die de adressen noemt die in DEZE tekst staan
    en al gemeld zijn, staat er niet los van maar middenin, en is daardoor
    moeilijker over te slaan.
    """
    rijen = eerder(dagen, pad)
    if not rijen or not brontekst:
        return ""
    raak = []
    for sleutel, zoals in adressen_uit(brontekst).items():
        rij = rijen.get(sleutel)
        if rij:
            raak.append(f"{zoals} (gemeld op {_nl(rij.get('laatst'))})")
    if not raak:
        return ""
    return ("LET OP, HIERONDER STAAT AL GEMELD NIEUWS. Deze adressen zijn al "
            "in een eerdere brief aan pa behandeld: " + "; ".join(raak[:12])
            + ". Breng ze niet opnieuw als nieuws. Is er vandaag een nieuw "
              "feit bij, noem dan alleen dat feit en zeg dat het een vervolg "
              "is op wat eerder is gemeld.\n\n")


def main():
    """Handig om te zien wat er in het geheugen staat."""
    rijen = eerder()
    print(f"{len(rijen)} onderwerpen in het venster van {VENSTER_DAGEN} dagen")
    print()
    print(tekst())
    return 0


if __name__ == "__main__":
    sys.exit(main())
