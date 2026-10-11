#!/usr/bin/env python3
"""
De eisen aan de brief lezen, en nameten of ze werkelijk gehandhaafd worden.

WAT DIT OPLOST. De regels waaraan de brief zich houdt stonden verspreid over
33.000 regels docstrings en workflowcommentaar, elk opgeschreven op de dag dat
het misging. Een losse lijst in markdown zou dat niet oplossen: die veroudert
stil, en stil verouderen is precies de fout die we deze week vijf keer hebben
gezien.

Daarom noemt elke eis in eisen.txt de controle die hem handhaaft, en meet dit
bestand na of die controle bestaat, groen staat, en de naam draagt waar de eis
naar verwijst. Wordt zo'n controle weggehaald of omgedoopt, dan is dit rood.

WAT HET NIET DOET. Het toetst niet of een controle werkelijk meet wat de eis
zegt; dat kan geen programma. Een eis zonder proef staat er met "proef: -" en
dat is een eerlijker antwoord dan een verwijzing die niets afdwingt. Het
verschil tussen wat we willen en wat gecontroleerd wordt, hoort zichtbaar te
zijn in plaats van impliciet.
"""
import argparse
import os
import re
import subprocess
import sys

PAD = "eisen.txt"
VERPLICHT = ("eis", "waarom", "proef")
TOEGESTAAN = VERPLICHT + ("soort", "let op")


def lees(pad=PAD):
    """
    De eisen als lijst van dicts, in de volgorde waarin ze in het bestand staan.

    Een waarde loopt door op de volgende regel als die met twee spaties begint;
    dat houdt een eis van twee zinnen leesbaar in het bestand zonder dat hij
    uit elkaar valt. Fouten in de vorm worden niet stil overgeslagen maar
    verzameld in de sleutel "_fouten" van het laatste blok, zodat proef() ze
    kan melden.
    """
    eisen, blok, veld, fouten = [], None, None, []
    try:
        with open(pad, encoding="utf-8") as f:
            regels = f.read().splitlines()
    except Exception as e:
        return ([], [f"{pad} niet te lezen: {str(e)[:60]}"])
    for n, regel in enumerate(regels, 1):
        kaal = regel.strip()
        if kaal.startswith("#") or (not kaal and blok is None):
            continue
        if kaal == "---":
            if blok:
                eisen.append(blok)
            blok, veld = {}, None
            continue
        if blok is None:
            if kaal:
                fouten.append(f"regel {n}: tekst voor het eerste --- blok")
            continue
        if regel.startswith("  ") and veld:
            # Doorloop van de vorige waarde.
            blok[veld] = (blok[veld] + " " + kaal).strip()
            continue
        if not kaal:
            continue
        if ":" not in kaal:
            fouten.append(f"regel {n}: geen veld, en geen doorloop: {kaal[:40]!r}")
            continue
        naam, waarde = kaal.split(":", 1)
        naam, waarde = naam.strip().lower(), waarde.strip()
        if naam not in TOEGESTAAN:
            fouten.append(f"regel {n}: onbekend veld {naam!r}")
            continue
        blok[naam] = waarde
        veld = naam
    if blok:
        eisen.append(blok)
    for i, e in enumerate(eisen, 1):
        for v in VERPLICHT:
            if not e.get(v):
                fouten.append(f"eis {i} mist het veld {v!r}: "
                              f"{(e.get('eis') or '?')[:50]}")
    return (eisen, fouten)


def _modules_met_proef():
    """
    De modules met een proef, uit de bron en niet uit een lijst.

    HET CRITERIUM IS "def proef(" EN GEEN "--proef". Een eerdere versie zocht
    naar de vlag, en dan viel toets_artikel15.py erbuiten: die draait zijn
    proef onvoorwaardelijk als script en heeft dus geen vlag. Daarmee sloeg
    de controle op de exitcode die module stil over, terwijl hij als poort in
    de workflow staat. Een detector met een eigen aanname over hoe een proef
    wordt aangeroepen, mist precies de module die het anders doet.
    """
    uit = []
    for naam in sorted(os.listdir(".")):
        if not naam.endswith(".py"):
            continue
        try:
            with open(naam, encoding="utf-8") as f:
                bron = f.read()
        except Exception:
            continue
        if "def proef(" in bron and "__main__" in bron:
            uit.append(naam[:-3])
    return uit


def _vlag(module):
    """Hoe deze module zijn proef aangeroepen wil hebben."""
    bron = _bron(module) or ""
    return ["--proef"] if '"--proef"' in bron else []


def _bron(module):
    try:
        with open(f"{module}.py", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _eindigt_op_sys_exit(bron):
    """
    Geeft de main-regel terug als die NIET op sys.exit staat, anders None.

    Dit is de eis "een proef die rood staat geeft een exitcode die niet 0 is",
    en dit is het deel dat machinaal te zien is: een module die zijn main
    aanroept zonder sys.exit geeft altijd 0 terug, hoe rood de proef ook staat.
    Op 11 oktober was dat bij pandgeschiedenis.py het geval, en dan is de
    poort in de workflow altijd groen.
    """
    m = re.search(r'if __name__ == ["\']__main__["\']:\s*\n((?:[ \t]+.*\n?)+)',
                  bron or "")
    if not m:
        return "geen __main__ blok"
    staart = m.group(1)
    if "sys.exit" in staart:
        return None
    return staart.strip().splitlines()[-1][:60]


def proef(snel=False):
    """
    Nameten of de eisen werkelijk gehandhaafd worden.

    snel=True slaat het draaien van de verwezen proeven over. Dat is er voor
    de poort in de workflow, waar die proeven toch al apart draaien; zonder
    snel duurt dit een paar seconden omdat elke verwezen module opnieuw wordt
    gestart.
    """
    eisen, fouten = lees()
    if not eisen:
        fouten.append("geen enkele eis gelezen")

    met_proef = [e for e in eisen if (e.get("proef") or "-") != "-"]
    zonder = [e for e in eisen if (e.get("proef") or "-") == "-"]

    # Een eis zonder proef moet uitleggen waarom, anders leest "-" als
    # vergeten in plaats van als bewuste keuze.
    for e in zonder:
        if not e.get("let op"):
            fouten.append(f"eis zonder proef en zonder uitleg: "
                          f"{e['eis'][:60]}")

    beschikbaar = set(_modules_met_proef())
    gedraaid = {}
    for e in met_proef:
        verwijzing = e["proef"]
        module, _, label = verwijzing.partition(":")
        module, label = module.strip(), label.strip()
        if module == "eisen":
            # Naar onszelf verwijzen mag: de controles hieronder in dit
            # bestand horen er net zo goed bij.
            continue
        if module not in beschikbaar:
            fouten.append(f"eis verwijst naar {module!r}, maar dat heeft geen "
                          f"--proef: {e['eis'][:50]}")
            continue
        bron = _bron(module)
        if label and label not in (bron or ""):
            fouten.append(f"de controle {label!r} staat niet in {module}.py; "
                          f"omgedoopt of weggehaald? Eis: {e['eis'][:50]}")
        if snel or module in gedraaid:
            continue
        r = subprocess.run([sys.executable, f"{module}.py"] + _vlag(module),
                           capture_output=True, text=True, timeout=600)
        gedraaid[module] = r.returncode
        if r.returncode != 0:
            laatste = (r.stderr or "").strip().splitlines()
            fouten.append(f"{module} --proef staat rood ({r.returncode}): "
                          f"{laatste[-1][:80] if laatste else 'geen uitvoer'}")

    # EISEN DIE DIT BESTAND ZELF HANDHAAFT.
    #
    # Elke module met een --proef moet op sys.exit eindigen. Zonder dat geeft
    # het proces exitcode 0, ook als de proef rood staat, en dan is de poort
    # in de workflow een formaliteit. Dit geldt voor alle modules met een
    # proef en niet alleen voor die waar een eis naar verwijst, want een
    # stille poort is overal even stil.
    for module in sorted(beschikbaar):
        reden = _eindigt_op_sys_exit(_bron(module))
        if reden:
            fouten.append(f"{module}.py heeft een --proef maar eindigt niet op "
                          f"sys.exit: {reden}. De exitcode is dan altijd 0.")

    print(f"Eisen: {len(eisen)} gelezen, {len(met_proef)} met een proef, "
          f"{len(zonder)} bewust zonder, {len(beschikbaar)} modules met een "
          f"proef nagekeken op hun exitcode" + ("" if snel else f", {len(gedraaid)} gedraaid"),
          file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def tekst(pad=PAD):
    """Een blok voor de bijlage: wat we eisen en wat daarvan vastligt."""
    eisen, _f = lees(pad)
    if not eisen:
        return ""
    met = [e for e in eisen if (e.get("proef") or "-") != "-"]
    zonder = [e for e in eisen if (e.get("proef") or "-") == "-"]
    r = ["## Wat de brief moet doen, en wat daarvan vastligt", ""]
    r.append(f"_{len(eisen)} eisen, waarvan {len(met)} worden afgedwongen door "
             f"een proef die bij elke run draait. De overige {len(zonder)} "
             f"staan er met de reden waarom ze niet verder te handhaven zijn; "
             f"dat verschil hoort zichtbaar te zijn in plaats van impliciet._")
    r.append("")
    for soort, kop in (("brief", "Over de brief"),
                       ("gegevens", "Over de gegevens"),
                       ("werking", "Over de werking")):
        groep = [e for e in eisen if (e.get("soort") or "") == soort]
        if not groep:
            continue
        r.append(f"### {kop}")
        r.append("")
        for e in groep:
            vast = (e.get("proef") or "-") != "-"
            r.append(f"- {'**Vastgelegd.**' if vast else '**Niet afgedwongen.**'}"
                     f" {e['eis']}")
        r.append("")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proef", action="store_true",
                    help="Nameten of de eisen gehandhaafd worden.")
    ap.add_argument("--snel", action="store_true",
                    help="Bij --proef: de verwezen proeven niet draaien.")
    ap.add_argument("--tekst", default="",
                    help="Het blok voor de bijlage hierheen schrijven.")
    a = ap.parse_args()
    if a.proef:
        return proef(snel=a.snel)
    if a.tekst:
        blok = tekst()
        if blok:
            with open(a.tekst, "w", encoding="utf-8") as f:
                f.write(blok)
        eisen, _f = lees()
        print(f"Eisen: {len(eisen)} naar {a.tekst}", file=sys.stderr)
        return 0
    print(tekst())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
