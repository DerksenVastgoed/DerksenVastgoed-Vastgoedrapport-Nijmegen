#!/usr/bin/env python3
"""
De brief nagelopen tegen de gegevens die de schrijver kreeg.

WAAROM. 20 oktober 2026 stonden er in een verhaal vijf onjuiste beweringen.
Twee kwamen van de schrijver zelf en stonden nergens in de gegevens: "de
gemeente besluit naar verwachting op 3 december" en "Hatertseweg 320 in
Galgenveld" (het ligt in St. Anna). Een instructie is geen garantie; dus wordt
het nagemeten, en krijgt de schrijver de gevonden zinnen terug in de
herstelronde die brief_verhalend.py al had.

DRIE TOETSEN.
  ongedekt()      elk percentage, bedrag, oppervlak, "per 1.000" en elke datum
                  in de brief moet als getal in de gegevens staan. Gemeten op
                  de drie verhalen van 20 oktober tegen hun eigen gegevens: de
                  enige treffer was "3 december", en die was verzonnen.
  buurtfouten()   staat een adres in een zin met een ringbuurt, dan moet het
                  in die buurt liggen volgens de voorraad. Gemeten op de
                  verhalen van 10 tot en met 20 oktober: twee treffers
                  (Graafseweg 18 "in Galgenveld", ligt in Bottendaal; Hatertseweg
                  320 "in Galgenveld", ligt in St. Anna), beide echte fouten.
  model_controle() een tweede taalmodel, los van de schrijver, krijgt dezelfde
                  gegevens en de brief, en noemt zinnen die er niet mee
                  kloppen. Dat vangt wat de getallen niet zien: "zes nieuwe
                  woningen van 55 tot 374 m2" (374 is het hele adres), "in zes
                  van de zeven buurten" (het waren er vijf).

WAT ER NIET GEBEURT. De controle houdt de brief niet tegen. Wat na de
herstelronde overblijft, staat in controle_brief.json en in het
gezondheidsrapport. Hoe vaak de toetsen bij goed gedrag afgaan, is pas na een
paar weken te zien; tot dan beslist geen toets over wie de brief krijgt.
"""
import json
import re
import sys

MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]
UIT = "controle_brief.json"


def _getal(x):
    x = x.replace("−", "-").replace("+", "").replace(" ", "").rstrip(".,")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", x):
        x = x.replace(".", "")
    x = x.replace(",", ".")
    try:
        return abs(float(x))
    except ValueError:
        return None


def _alle_getallen(tekst):
    uit = set()
    for m in re.finditer(r"[-−+]?\d[\d.,]*", tekst or ""):
        v = _getal(m.group(0))
        if v is not None:
            uit.add(v)
    return uit


def _datums(tekst):
    uit = set()
    for m in re.finditer(r"\b(\d{1,2}) (" + "|".join(MAANDEN) + r")\b",
                         (tekst or "").lower()):
        uit.add((int(m.group(1)), MAANDEN.index(m.group(2)) + 1))
    for m in re.finditer(r"\b20\d\d-(\d\d)-(\d\d)\b", tekst or ""):
        uit.add((int(m.group(2)), int(m.group(1))))
    return uit


def ongedekt(brief, gegevens):
    """[tekst] van elk getal met een eenheid en elke datum in de brief dat
    niet in de gegevens staat. Links tellen niet mee."""
    brief = re.sub(r"\]\([^)]*\)", "]", brief or "")
    getallen, datums = _alle_getallen(gegevens), _datums(gegevens)
    los = []
    for m in re.finditer(r"[-−+]?\d[\d.,]*\s?(?:%|procent|m2|m²|vierkante "
                         r"meter|per 1\.?000)|€\s?\d[\d.,]*", brief):
        g = re.search(r"\d[\d.,]*", m.group(0)).group(0)
        v = _getal(g)
        if v is not None and v not in getallen:
            los.append(m.group(0).strip())
    for dag, maand in sorted(_datums(brief)):
        if (dag, maand) not in datums:
            los.append(f"{dag} {MAANDEN[maand - 1]}")
    return los


def adres_buurt(pad="voorraad.json"):
    """{adres: buurt} voor de adressen in de ring met precies een buurt."""
    try:
        with open(pad, encoding="utf-8") as f:
            v = json.load(f).get("adressen") or {}
    except (OSError, ValueError):
        return {}
    return {r["adres"]: r["buurten"][0] for r in v.values()
            if r.get("herkomst") == "focusbuurt" and r.get("adres")
            and len(r.get("buurten") or []) == 1}


def buurtfouten(brief, adressen, buurten):
    """Zinnen waarin een adres staat met een andere ringbuurt dan de zijne."""
    los = []
    for zin in re.split(r"(?<=[.!?])\s+", brief or ""):
        schoon = re.sub(r"\]\([^)]*\)", "]", zin)
        genoemd = [b for b in buurten
                   if re.search(r"\b" + re.escape(b) + r"\b", schoon)]
        if not genoemd:
            continue
        for adres, buurt in adressen.items():
            if f"[{adres}]" in schoon and buurt not in genoemd:
                los.append((zin.strip()[:300],
                            f"{adres} ligt volgens de voorraad in {buurt}, "
                            f"niet in {', '.join(genoemd)}"))
    return los


CONTROLE_PROFIEL = (
    "Je controleert een brief tegen de gegevens waaruit hij is geschreven. "
    "Je schrijft niets nieuws. Noem alleen zinnen die iets beweren wat NIET "
    "in de gegevens staat, of wat er anders staat: een verkeerd getal, een "
    "getal bij het verkeerde ding, een telling die niet klopt, een adres in "
    "de verkeerde buurt, een besluit dat als verleend wordt gebracht terwijl "
    "alleen de titel bekend is, een eigen conclusie die als feit staat. Een "
    "mening of een afweging is geen fout. Antwoord met ALLEEN een JSON-array "
    'van {"zin": "<de zin letterlijk>", "waarom": "<wat de gegevens zeggen>"}. '
    "Is er niets, antwoord dan []. Nederlands.")


def model_controle(brief, gegevens, model, vraag=None):
    """[(zin, waarom)] van een tweede taalmodel, of None als dat mislukte."""
    if vraag is None:
        import taalmodel
        vraag = taalmodel.vraag
    a = vraag(model, CONTROLE_PROFIEL,
              [{"role": "user", "content":
                f"GEGEVENS:\n\n{gegevens}\n\nBRIEF:\n\n{brief}"}],
              8000, effort="medium", timeout=(30, 300), label="Controle")
    if getattr(a, "fout", None) or not getattr(a, "tekst", ""):
        return None
    tekst = a.tekst.strip()
    if tekst.startswith("```"):
        tekst = tekst.split("```")[1]
        if tekst.startswith("json"):
            tekst = tekst[4:]
    try:
        rijen = json.loads(tekst.strip())
    except ValueError:
        return None
    return [(str(r.get("zin", "")).strip(), str(r.get("waarom", "")).strip())
            for r in rijen if isinstance(r, dict) and r.get("zin")]


def bevindingen(brief, gegevens, adressen, buurten, model=None, vraag=None):
    """Alle bevindingen als [(zin of getal, waarom, toets)]."""
    zinnen = re.split(r"(?<=[.!?])\s+", re.sub(r"\]\([^)]*\)", "]",
                                                brief or ""))
    uit = []
    for g in ongedekt(brief, gegevens):
        # De hele zin, zodat de schrijver weet waar het staat.
        zin = next((z.strip() for z in zinnen if g in z), g)
        uit.append((zin[:300], f"'{g}' staat niet in de gegevens", "getal"))
    uit += [(z, w, "buurt") for z, w in buurtfouten(brief, adressen, buurten)]
    if model:
        m = model_controle(brief, gegevens, model, vraag)
        if m is None:
            uit.append(("", "de controle door het tweede taalmodel mislukte",
                        "niet gedaan"))
        else:
            uit += [(z, w, "model") for z, w in m]
    return uit


def bewaar(datum, voor, na):
    with open(UIT, "w", encoding="utf-8") as f:
        json.dump({"datum": datum,
                   "voor_herstel": [list(x) for x in voor],
                   "na_herstel": [list(x) for x in na]}, f,
                  ensure_ascii=False, indent=1)


def proef():
    afw = []
    gegevens = ("Besluit van 2026-10-19 voor 6, aan Graafseweg 18. "
                "Hatertseweg 320, 184 m2, label C. Gelderland 5,6% jaar. "
                "Woninginbraak 1,6 per 1.000. WOZ €396.000.")
    # Het verzonnen "3 december" (20 oktober) wordt gevonden, wat er wel
    # staat niet.
    brief = ("De gemeente besluit naar verwachting op 3 december. Het besluit "
             "is van 19 oktober, 184 m2, Gelderland +5,6%, inbraak 1,6 per "
             "1000, onder €396.000.")
    los = ongedekt(brief, gegevens)
    if los != ["3 december"]:
        afw.append(f"de getallen en datums worden verkeerd getoetst: {los}")
    # Een link telt niet als getal in de brief.
    if ongedekt("[Graafseweg 18](https://x/gmb-2026-485967.html)", gegevens):
        afw.append("het nummer in een link telt als getal in de brief")
    adressen = {"Hatertseweg 320": "St. Anna", "Graafseweg 18": "Bottendaal"}
    buurten = ["Galgenveld", "St. Anna", "Bottendaal"]
    fout = ("In Galgenveld ligt er een vergelijkbare aanvraag: [Hatertseweg 320]"
            "(https://x) wil naar meerdere woonruimtes.")
    goed = "In St. Anna ligt [Hatertseweg 320](https://x)."
    if len(buurtfouten(fout, adressen, buurten)) != 1 or \
            buurtfouten(goed, adressen, buurten):
        afw.append("een adres in de verkeerde buurt wordt niet of te vaak "
                   "gevonden")

    class A:
        def __init__(self, tekst="", fout=None):
            self.tekst, self.fout = tekst, fout
    m = model_controle("x", "y", "m", vraag=lambda *a, **k: A(
        '[{"zin": "zes van de zeven", "waarom": "vijf"}]'))
    if m != [("zes van de zeven", "vijf")]:
        afw.append(f"het antwoord van de controle wordt verkeerd gelezen: {m}")
    if model_controle("x", "y", "m", vraag=lambda *a, **k: A(fout="500")) \
            is not None:
        afw.append("een mislukte controle leest als 'niets gevonden'")
    b = bevindingen("x", "y", {}, [], model="m",
                    vraag=lambda *a, **k: A(fout="500"))
    if not any(t == "niet gedaan" for _z, _w, t in b):
        afw.append("een mislukte controle staat niet in de bevindingen")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef feitencontrole: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


if __name__ == "__main__":
    sys.exit(proef() if "--proef" in sys.argv else 0)
