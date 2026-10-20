#!/usr/bin/env python3
"""
De brief naar pa pas na de nakijkronde.

WAAROM. 20 oktober 2026, Mark: pa moet de brief krijgen nadat hij is
nagekeken, niet ervoor. Tot dan ging de brief om een uur of vijf tegelijk naar
Mark en pa, en keek de nakijkronde (NAKIJKEN.md) hem om 06:46 na, als pa hem
al had. Fouten werden daarna in de code opgelost, maar de brief van die dag
bleef zoals hij was.

HOE HET NU LOOPT.
  1. De briefrun (bekendmakingen.yml) mailt alleen Mark en zet in
     pa_kopie.json of deze brief naar pa mag (geen testrun, geen halve
     update), en in welke modus.
  2. De nakijkronde kijkt hem na en start kopie_pa.yml. Vond hij niets, dan
     zonder correcties: dezelfde mail gaat naar pa. Vond hij wel iets, dan
     met de zinnen en wat de gegevens zeggen: het verhaal wordt met die
     correcties herschreven (herstel), de mail opnieuw samengesteld, en die
     gaat naar pa. Codewijzigingen blijven pull requests die Mark goedkeurt.
  3. Een tweede geplande taak start om 08:52 kopie_pa.yml zonder correcties
     als pa nog niets heeft, zodat een uitgevallen nakijkronde de brief niet
     tegenhoudt.

  python3 kopie_pa.py --klaarzetten --datum D --modus M --testrun 0 --halve 0
  python3 kopie_pa.py --mag --datum D
  python3 kopie_pa.py --herstel --datum D --correcties '[{"zin":..,"waarom":..}]'
  python3 kopie_pa.py --verstuurd --datum D [--gecorrigeerd]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

PAD = "pa_kopie.json"


def lees(pad=PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def schrijf(stand, pad=PAD):
    with open(pad, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)


def klaarzetten(datum, modus, testrun, halve, reden="", pad=PAD):
    """Na de briefrun: mag deze brief naar pa, en waarom niet."""
    oud = lees(pad)
    if testrun:
        # Een testrun verandert de stand van de echte brief niet. Zonder dit
        # zou een handrun "alleen naar mij" de echte brief van die dag op
        # "mag niet" zetten, of een al verstuurde markering wissen.
        return oud
    stand = {"datum": datum, "modus": modus, "mag_naar_pa": not halve,
             "reden": reden if halve else "",
             "verstuurd": None, "gecorrigeerd": None}
    schrijf(stand, pad)
    return stand


def mag(datum, pad=PAD):
    """(ja of nee, reden) voor de kopie naar pa van deze datum."""
    s = lees(pad)
    if s.get("datum") != datum:
        return False, (f"de briefrun van {datum} heeft niets klaargezet "
                       f"(laatste: {s.get('datum') or 'geen'})")
    if not s.get("mag_naar_pa"):
        return False, f"halve update: {s.get('reden') or 'geen reden bewaard'}"
    if s.get("verstuurd"):
        return False, f"al verstuurd om {s['verstuurd']}"
    return True, ""


def markeer_verstuurd(datum, gecorrigeerd, pad=PAD):
    s = lees(pad)
    if s.get("datum") == datum:
        s["verstuurd"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        s["gecorrigeerd"] = bool(gecorrigeerd)
        schrijf(s, pad)
    return s


def romp(verhaal):
    """Het verhaal zonder de kop en zonder het weetje: wat het model schreef,
    zodat de herschrijving niet ook de titel en het weetje teruggeeft."""
    t = re.sub(r"\A# [^\n]*\n+", "", verhaal or "")
    t = re.split(r"\n---\n+\*\*Wist je dat\*\*", t)[0]
    # Ook zonder de links die main() erna zet (besluit en straatbeeld): in de
    # eerste proef kwam "([straatbeeld](...))" er anders twee keer achter.
    t = re.sub(r" \(\[straatbeeld\]\([^)]*\)\)", "", t)
    t = re.sub(r"\[([^\]]+)\]\((?:https?://)[^)]*\)", r"\1", t)
    return t.strip()


def correctiebericht(correcties):
    regels = [f'- "{c.get("zin", "").strip()}": {c.get("waarom", "").strip()}'
              for c in correcties if c.get("zin")]
    return ("Een nakijkronde heeft je brief naast de gegevens gelegd. Deze "
            "zinnen kloppen niet met de gegevens:\n" + "\n".join(regels) +
            "\n\nPas alleen deze zinnen aan, zodat ze kloppen met de "
            "gegevens, of haal ze weg als ze niet te redden zijn. Laat de rest "
            "van de brief zo veel mogelijk staan. Geef de volledige brief "
            "terug, niets eromheen.")


def herstel(datum, correcties, vraag=None):
    """Het verhaal herschrijven met de correcties, en de mail opnieuw
    samenstellen. Geeft True als er een nieuw verhaal is."""
    import brief_verhalend as b
    os.environ["GEHEUGEN_ALLEEN_LEZEN"] = "1"
    pad = os.path.join("digests", f"{datum}-verhaal.md")
    with open(pad, encoding="utf-8") as f:
        eerste = f.read()
    # De eerste versie bewaren: wat Mark om vijf uur kreeg.
    with open(os.path.join("digests", f"{datum}-verhaal-eerste.md"), "w",
              encoding="utf-8") as f:
        f.write(eerste)
    echte = vraag or b._vraag
    stand = {"n": 0}

    def gestuurd(berichten, woorden):
        stand["n"] += 1
        if stand["n"] == 1:
            # De eerste vraag van schrijf_brief: in plaats van een nieuwe
            # brief, de brief van vanochtend met de correcties erachter.
            return echte(berichten + [
                {"role": "assistant", "content": romp(eerste)},
                {"role": "user", "content": correctiebericht(correcties)}],
                woorden)
        return echte(berichten, woorden)

    b._vraag = gestuurd
    oud = sys.argv
    sys.argv = ["brief_verhalend.py", "--datum", datum, "--uit", pad]
    try:
        code = b.main()
    except SystemExit as e:
        code = e.code
    finally:
        sys.argv = oud
    with open(pad, encoding="utf-8") as f:
        nieuw = f.read()
    if code not in (0, None) or not romp(nieuw):
        # Mislukt: de eerste versie terugzetten, dan is er niets half.
        with open(pad, "w", encoding="utf-8") as f:
            f.write(eerste)
        return False
    # De voorleesknop hoort bij de nieuwe tekst: een nieuwe MP3 (de naam volgt
    # de tekst, zie voorlezen.py). Mislukt dat, dan geen knop, wel een brief.
    try:
        import voorlezen
        voorlezen.maak(datum)
    except Exception as e:
        print(f"LET OP: voorlezen na het herschrijven mislukt: {e}",
              file=sys.stderr)
    import briefmail
    modus = lees().get("modus") or "dagelijks"
    return briefmail.bouwen(datum, modus) == 0


def ontvangers_pa(map_=".github/workflows"):
    """Workflows die pa iets kunnen mailen, buiten kopie_pa.yml. Leeg is goed.

    Een regel 'to:' of 'cc:' met MAIL_TO_VERHAAL of CC_VERHAAL telt, en een
    CC_VERHAAL die ergens anders dan op leeg wordt gezet. Zo blijft kopie_pa.yml
    de enige weg naar pa, ook als iemand de cc in de ochtendrun terugzet."""
    fout = []
    for naam in sorted(os.listdir(map_)):
        if not naam.endswith((".yml", ".yaml")) or naam == "kopie_pa.yml":
            continue
        with open(os.path.join(map_, naam), encoding="utf-8") as f:
            for i, r in enumerate(f, 1):
                t = r.strip()
                if t.startswith("#"):
                    continue
                if re.match(r"(to|cc|bcc):", t) and "VERHAAL" in t \
                        and "env.CC_VERHAAL" not in t:
                    fout.append(f"{naam}:{i}: {t}")
                m = re.search(r"CC_VERHAAL=([^\"' ]*)", t)
                if m and m.group(1):
                    fout.append(f"{naam}:{i}: {t}")
    return fout


def test_naar_pa(pad=".github/workflows/kopie_pa.yml"):
    """Stappen in kopie_pa.yml die pa mailen zonder 'env.TEST != '1'' in hun
    voorwaarde. Leeg is goed: een test (alleen_naar_mij) bereikt pa nooit."""
    import yaml
    with open(pad, encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    fout = []
    for job in wf["jobs"].values():
        for st in job["steps"]:
            naar = str((st.get("with") or {}).get("to", ""))
            if "MAIL_TO_VERHAAL" in naar and "env.TEST != '1'" not in str(st.get("if", "")):
                fout.append(st.get("name", "?"))
            if "MAIL_TO_VERHAAL" in naar and "MAIL_TO " in naar + " ":
                fout.append(st.get("name", "?") + " (twee ontvangers in een expressie)")
    return fout


def proef():
    import tempfile
    afw = []
    for r in test_naar_pa():
        afw.append(f"een test van kopie_pa.yml kan pa mailen: {r}")
    for r in ontvangers_pa():
        afw.append(f"pa kan buiten kopie_pa.yml een mail krijgen: {r}")
    with tempfile.TemporaryDirectory() as m:
        p = os.path.join(m, "pa.json")
        klaarzetten("2026-10-21", "dagelijks", False, False, pad=p)
        if mag("2026-10-21", p) != (True, ""):
            afw.append("een complete brief mag niet naar pa")
        if mag("2026-10-22", p)[0]:
            afw.append("een brief van een andere dag mag naar pa")
        # Een testrun laat de stand van de echte brief staan.
        klaarzetten("2026-10-21", "dagelijks", True, True, pad=p)
        if not mag("2026-10-21", p)[0]:
            afw.append("een testrun zet de echte brief op 'mag niet'")
        markeer_verstuurd("2026-10-21", True, pad=p)
        if mag("2026-10-21", p)[0]:
            afw.append("een al verstuurde brief mag nog een keer naar pa")
        klaarzetten("2026-10-22", "dagelijks", False, True,
                    "het verhaal ontbreekt", pad=p)
        ok, reden = mag("2026-10-22", p)
        if ok or "het verhaal ontbreekt" not in reden:
            afw.append(f"een halve update mag naar pa: {reden}")
    v = ("# Vastgoed in Nijmegen, 20 oktober 2026\n\nGoedemorgen pa,\n\nTekst."
         "\n\n---\n\n**Wist je dat** iets?\n")
    lv = ("# T\n\nOp de [Graafseweg 18](https://x/gmb.html) ([straatbeeld]"
          "(https://www.google.com/maps/@?api=1&x=1)) iets.\n")
    if romp(lv) != "Op de Graafseweg 18 iets.":
        afw.append(f"de links blijven in de romp staan: {romp(lv)!r}")
    if romp(v) != "Goedemorgen pa,\n\nTekst.":
        afw.append(f"de romp van het verhaal wordt verkeerd gelezen: {romp(v)!r}")
    c = correctiebericht([{"zin": "zes van de zeven", "waarom": "vijf"}])
    if '"zes van de zeven": vijf' not in c:
        afw.append("de correcties staan niet in het bericht aan de schrijver")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef kopie_pa: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--klaarzetten", action="store_true")
    ap.add_argument("--mag", action="store_true")
    ap.add_argument("--herstel", action="store_true")
    ap.add_argument("--verstuurd", action="store_true")
    ap.add_argument("--datum", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--modus", default="dagelijks")
    ap.add_argument("--testrun", default="0")
    ap.add_argument("--halve", default="0")
    ap.add_argument("--reden", default="")
    ap.add_argument("--correcties", default="")
    ap.add_argument("--gecorrigeerd", action="store_true")
    a = ap.parse_args()
    if a.proef:
        return proef()
    if a.klaarzetten:
        s = klaarzetten(a.datum, a.modus, a.testrun == "1", a.halve == "1",
                        a.reden)
        print(json.dumps(s, ensure_ascii=False))
        return 0
    if a.mag:
        ok, reden = mag(a.datum)
        print("ja" if ok else f"nee: {reden}")
        uit = os.environ.get("GITHUB_OUTPUT")
        if uit:
            with open(uit, "a", encoding="utf-8") as f:
                f.write(f"mag={'ja' if ok else 'nee'}\n")
        return 0
    if a.herstel:
        try:
            correcties = json.loads(a.correcties or "[]")
        except ValueError:
            print("De correcties zijn geen JSON", file=sys.stderr)
            return 1
        if not correcties:
            print("Geen correcties; niets te herstellen", file=sys.stderr)
            return 0
        return 0 if herstel(a.datum, correcties) else 1
    if a.verstuurd:
        print(json.dumps(markeer_verstuurd(a.datum, a.gecorrigeerd),
                         ensure_ascii=False))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
