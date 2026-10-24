#!/usr/bin/env python3
"""
De gegevens die de schrijver van het verhaal kreeg, opnieuw opgebouwd.

WAAROM. De prompt van brief_verhalend.py wordt niet bewaard, en het
joblogboek is van buiten de runner niet te lezen. Om een verstuurde brief na
te lopen moet je weten wat de schrijver zag. Dit script draait main() van
brief_verhalend.py met de digests die in de repo staan, maar in plaats van het
taalmodel aan te roepen vangt het de prompt op en geeft het het verhaal terug
dat er al ligt. Er gaat niets naar de API en er wordt niets overschreven: de
uitvoer van main() gaat naar een tijdelijk bestand.

Gebruikt door de dagelijkse nakijkronde (NAKIJKEN.md). Op 20 oktober 2026 met
de hand zo gedaan; nu een script, zodat het een implementatie is.

  python3 brief_invoer.py --datum 2026-10-20 > /tmp/invoer.txt

Voorbehoud: de gegevensbestanden in de repo kunnen na de briefrun zijn
bijgewerkt (de voorraadronde commit om 03:18 UTC). De digests van die dag
veranderen niet meer, dus het grootste deel van de prompt is gelijk; de
mechanismen uit bronnen.py staan er onderaan bij, zoals de feitencontrole ze
ook krijgt.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile


def modus(datum):
    """
    De modus waarin de brief van die dag geschreven is, of None.

    WAAROM. Op 24 oktober 2026 bouwde dit script voor de weekeditie de
    dagprompt op, want MODUS stond niet in de omgeving van de nakijkronde.
    Daarin stonden het nieuws en de besluiten van die dag gewoon, terwijl de
    schrijver ze door week_terug() nooit kreeg; die fout was alleen te zien
    met MODUS=weekelijks met de hand ervoor.

    WAAR HET VANDAAN KOMT. Niet opnieuw uit de dag van de week: dat besluit de
    workflow (bekendmakingen.yml, met de vrijdagavondregel), en een tweede
    kopie van die regel loopt ervan weg. kopie_pa.py legt de modus van elke
    brief vast in pa_kopie.json, en dat bestand wordt elke dag gecommit. Dus:
    pa_kopie.json als de datum klopt, anders de laatste commit waarin hij die
    datum had.
    """
    def _uit(tekst):
        try:
            d = json.loads(tekst)
        except Exception:
            return None
        return d.get("modus") if d.get("datum") == datum else None

    try:
        with open("pa_kopie.json", encoding="utf-8") as f:
            m = _uit(f.read())
        if m:
            return m
    except OSError:
        pass
    try:
        commits = subprocess.run(
            ["git", "log", "--format=%H", "-n", "60", "--", "pa_kopie.json"],
            capture_output=True, text=True, timeout=30).stdout.split()
    except Exception:
        return None
    for c in commits:
        r = subprocess.run(["git", "show", f"{c}:pa_kopie.json"],
                           capture_output=True, text=True, timeout=30)
        m = _uit(r.stdout) if r.returncode == 0 else None
        if m:
            return m
    return None


def invoer(datum):
    # Niets onthouden: geen weetje afstrepen, geen logboek bijwerken. Zonder
    # dit veranderde weetjes_gezien.json bij de eerste proef.
    os.environ["GEHEUGEN_ALLEEN_LEZEN"] = "1"
    # Een MODUS die de aanroeper zelf zet, gaat voor. Anders die van de brief.
    if not os.environ.get("MODUS"):
        m = modus(datum)
        if m:
            os.environ["MODUS"] = m
            print(f"Modus van de brief van {datum}: {m} (uit pa_kopie.json)",
                  file=sys.stderr)
        else:
            print(f"Modus van de brief van {datum} niet gevonden in "
                  f"pa_kopie.json of zijn geschiedenis; de dagprompt wordt "
                  f"opgebouwd. Zet MODUS als dat niet klopt.", file=sys.stderr)
    import brief_verhalend as b
    import bronnen
    pad = os.path.join("digests", f"{datum}-verhaal.md")
    verhaal = ""
    if os.path.exists(pad):
        with open(pad, encoding="utf-8") as f:
            verhaal = f.read()
    gevangen = []

    def nep(berichten, woorden):
        gevangen.append(berichten[0]["content"])
        return verhaal

    b._vraag = nep
    b.ANTHROPIC_API_KEY = b.ANTHROPIC_API_KEY or "geen-aanroep"
    # De controle na het schrijven roept zelf een taalmodel aan; hier niet.
    try:
        import feitencontrole
        feitencontrole.model_controle = lambda *a, **k: []
    except Exception:
        pass
    oud_argv, oud_cwd_bestand = sys.argv, None
    with tempfile.TemporaryDirectory() as m:
        sys.argv = ["brief_verhalend.py", "--datum", datum,
                    "--uit", os.path.join(m, "verhaal.md")]
        # controle_brief.json niet overschrijven met deze nabootsing.
        bewaard = None
        if os.path.exists("controle_brief.json"):
            with open("controle_brief.json", encoding="utf-8") as f:
                bewaard = f.read()
        try:
            b.main()
        except SystemExit:
            pass
        finally:
            sys.argv = oud_argv
            if bewaard is not None:
                with open("controle_brief.json", "w", encoding="utf-8") as f:
                    f.write(bewaard)
    if not gevangen:
        return ""
    return gevangen[0] + "\n\n" + bronnen.mechanismen()


def proef():
    """
    Op echte brieven: 24 oktober 2026 was de weekeditie, 23 oktober een
    dagbrief (pa_kopie.json in de geschiedenis van main). Een datum zonder
    brief geeft None en niet stil "dagelijks".
    """
    fouten = []
    for datum, verwacht in (("2026-10-24", "weekelijks"),
                            ("2026-10-23", "dagelijks"),
                            ("2026-01-01", None)):
        m = modus(datum)
        if m != verwacht:
            fouten.append(f"de modus van {datum} is {m!r}, verwacht "
                          f"{verwacht!r} (zonder de geschiedenis van "
                          f"pa_kopie.json, bij een ondiepe kloon, is dit niet "
                          f"te meten)")
    print(f"Proef brief_invoer: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datum")
    ap.add_argument("--proef", action="store_true",
                    help="nameten of de modus van een echte brief wordt "
                         "gevonden")
    a = ap.parse_args()
    if a.proef:
        return proef()
    if not a.datum:
        ap.error("--datum is nodig")
    tekst = invoer(a.datum)
    if not tekst:
        print("Geen invoer opgebouwd: staan de digests van die dag er?",
              file=sys.stderr)
        return 1
    sys.stdout.write(tekst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
