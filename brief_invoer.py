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
import os
import sys
import tempfile


def invoer(datum):
    # Niets onthouden: geen weetje afstrepen, geen logboek bijwerken. Zonder
    # dit veranderde weetjes_gezien.json bij de eerste proef.
    os.environ["GEHEUGEN_ALLEEN_LEZEN"] = "1"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datum", required=True)
    a = ap.parse_args()
    tekst = invoer(a.datum)
    if not tekst:
        print("Geen invoer opgebouwd: staan de digests van die dag er?",
              file=sys.stderr)
        return 1
    sys.stdout.write(tekst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
