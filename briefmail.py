"""
De mail samenstellen: het verhaal bovenaan, de cijfers eronder als bijlage.

WAAROM DIT EEN MODULE IS EN GEEN PYTHON-BLOK IN DE WORKFLOW. Dit is het
laatste punt waar alles langskomt wat pa te zien krijgt, en op 14 oktober ging
het hier mis. De marktprijzenstap mislukte, er kwam geen bijlage, en de regel

    werk = lees(bijlage) or lees(brief)

zette toen de bekendmakingenbrief onder de kop "Bijlage: de cijfers", met
eronder de belofte "het volledige overzicht per buurt". Pa las de
bekendmakingen en de publicaties dus twee keer, een keer onder een kop die
iets anders aankondigde. Mark zag het in zijn eigen kopie en vroeg of dat de
bedoeling was.

In YAML was dat niet na te meten: geen proef kan bij een heredoc. Hier wel.

DE REGEL: wat er niet is, komt er niet, en dan zegt de brief dat.
"""

import argparse
import glob
import os
import sys

STIJL = (
  "body{font:17px/1.75 Georgia,'Times New Roman',serif;color:#1a2830;"
  "max-width:700px;margin:0 auto;padding:28px}"
  "h1{font-size:21px;font-weight:normal;color:#4a5b63;"
  "border-bottom:2px solid #E0A458;padding-bottom:10px;margin-top:40px}"
  "h2{font-size:17px;color:#12242c;margin:32px 0 10px;"
  "border-bottom:1px solid #e3e8ea;padding-bottom:6px}"
  "h3{font-size:16px;color:#12242c;margin:26px 0 8px}"
  "p{margin:0 0 18px}a{color:#4a7a72}"
  "hr{border:0;border-top:2px solid #e3e8ea;margin:48px 0 8px}"
  ".inleiding{color:#4a5b63;font-size:15px}"
  "table{border-collapse:collapse;width:100%;font:14px/1.5 "
  "-apple-system,Segoe UI,sans-serif;margin:0 0 18px}"
  "th{text-align:left;border-bottom:2px solid #12242c;padding:6px 8px}"
  "td{border-bottom:1px solid #e3e8ea;padding:6px 8px;vertical-align:top}"
  "em{color:#4a5b63;font-size:15px}")


def lees(pad):
    try:
        with open(pad, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def werkstuk(datum, modus, map="digests"):
    """
    Welk stuk er als bijlage onder het verhaal hoort, en of het er is.

    Doordeweeks de tabelversie, want dan gaat het om de cijfers. Op zondag de
    volledige werkbrief, want daar staan de investeringscases, de
    referentietabellen, de beleggingslijst en de regelgevingsmonitor in; die
    tabelversie kent die onderdelen niet.

    GEEN VERVANGER. Is het stuk er niet, dan komt er niets voor in de plaats.
    """
    naam = "bijlage" if modus == "dagelijks" else "brief"
    pad = os.path.join(map, f"{datum}-{naam}.md")
    inhoud = lees(pad)
    return {"pad": pad, "naam": naam, "inhoud": inhoud,
            "ontbreekt": "" if inhoud else naam}


def delen_van(datum, map="digests"):
    """De digestonderdelen die op dit moment bestaan en niet leeg zijn."""
    uit = set()
    for pad in glob.glob(os.path.join(map, f"{datum}-*.md")):
        try:
            if os.path.getsize(pad) <= 0:
                continue
        except OSError:
            continue
        uit.add(os.path.basename(pad)[len(datum) + 1:-3])
    return uit


def wat_er_mist(datum, modus, map="digests", bewaren=True):
    """
    Welke onderdelen deze brief mist die de vorige brief wel had.

    NIET DE LIJST MET OVERGESLAGEN STAPPEN. Monumenten, haltes en de
    bouwkostenindex verversen achtergrondgegevens en staan nooit in de brief.
    Die opnoemen zou een melding zijn die afgaat zonder dat de lezer iets
    mist, en dat is erger dan geen melding. Dus meten we het aan de brief
    zelf: welke onderdelen had de vorige brief in DEZELFDE modus, die deze
    niet heeft. De modus hoort erbij omdat de zondagse werkbrief onderdelen
    kent die de doordeweekse niet heeft.

    OP HETZELFDE MOMENT IN DE RUN GEMETEN. Het gezondheidsrapport wordt pas na
    deze stap geschreven. "Wat staat er nu" vergelijken met "wat stond er aan
    het eind van de vorige run" zou dus elke dag melden dat gezondheid.md
    ontbreekt: een melding die op goed gedrag afgaat. Daarom legt deze functie
    vast wat zij op dit punt ziet, en vergelijkt zij met wat de vorige run op
    precies dit punt zag.

    Geen eerdere brief in deze modus betekent: niet gemeten. Dan is de uitkomst
    leeg EN zegt gemeten False, want niet gekeken en niets gevonden mogen niet
    hetzelfde woord krijgen.
    """
    nu = sorted(delen_van(datum, map))
    if bewaren:
        with open(os.path.join(map, f"{datum}-delen.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write(modus + "\n" + "\n".join(nu) + "\n")
    for pad in sorted(glob.glob(os.path.join(map, "*-delen.txt")),
                      reverse=True):
        eerder = os.path.basename(pad)[:10]
        if eerder >= datum:
            continue
        regels = [r.strip() for r in lees(pad).splitlines() if r.strip()]
        if regels and regels[0] == modus:
            return {"gemeten": True, "vorige": eerder,
                    "kwijt": sorted(set(regels[1:]) - set(nu))}
    return {"gemeten": False, "vorige": "", "kwijt": []}


def samenstellen(verhaal, werk, weggevallen=(), voet=""):
    """De html van de mail, uit de stukken die er werkelijk zijn."""
    import markdown

    delen = []
    if voet:
        delen.append(voet)
    if verhaal:
        delen.append(markdown.markdown(verhaal, extensions=["extra"]))
        if weggevallen:
            delen.append('<p class="inleiding">Niet in deze brief: '
                         + ", ".join(weggevallen)
                         + ". Die onderdelen zijn vandaag niet opgeleverd.</p>")
        if werk:
            delen.append('<hr><h1 id="bijlage">Bijlage: de cijfers</h1>'
                         '<p class="inleiding">Het volledige overzicht per '
                         'buurt, met de panden die nu worden aangeboden, de '
                         'doorrekening en de gemeentelijke berichten.</p>')
    if werk:
        delen.append(markdown.markdown(werk, extensions=["extra", "tables"]))
    if not delen or (voet and len(delen) == 1):
        return ""
    return ("<!DOCTYPE html><html lang=nl><head><meta charset=utf-8>"
            f"<style>{STIJL}</style></head><body>"
            + "".join(delen) + "</body></html>")


def meld(regel):
    print(regel, file=sys.stderr)


def naar_omgeving(sleutel, waarde):
    """Een vlag doorgeven aan de volgende stap in de workflow."""
    pad = os.environ.get("GITHUB_ENV")
    if not pad:
        return False
    try:
        with open(pad, "a", encoding="utf-8") as fh:
            fh.write(f"{sleutel}={waarde}\n")
        return True
    except Exception:
        return False


def bouwen(datum, modus, map="digests"):
    verhaal = lees(os.path.join(map, f"{datum}-verhaal.md"))
    stuk = werkstuk(datum, modus, map)
    if stuk["ontbreekt"]:
        meld(f"LET OP: {stuk['pad']} ontbreekt. De bijlage gaat niet mee en "
             f"er komt geen ander stuk voor in de plaats.")
        # De volgende stap haalt hierop de kopie naar pa eraf. Een brief
        # waaruit een heel onderdeel is weggevallen is een halve update.
        naar_omgeving("ONVOLLEDIG", stuk["ontbreekt"])
    # GEEN VERHAAL IS EEN HALVE UPDATE. 20 oktober 2026: het schrijven
    # leverde 0 woorden op (zie taalmodel.py), en de mail ging met alleen de
    # tabellen naar beiden, als gewone brief. Het verhaal is voor pa het
    # belangrijkste deel; zonder verhaal gaat de kopie eraf en zegt het
    # onderwerp waarom.
    if not verhaal.strip():
        meld("LET OP: er is geen verhaal voor vandaag. De kopie naar pa gaat "
             "eraf.")
        naar_omgeving("ONVOLLEDIG", "het verhaal")
    stand = wat_er_mist(datum, modus, map)
    if stand["gemeten"]:
        meld(f"Vergeleken met {stand['vorige']} ({modus}): "
             f"{len(stand['kwijt'])} deel/delen kwijt: "
             f"{', '.join(stand['kwijt']) or 'geen'}")
    else:
        meld(f"Geen eerdere brief in modus {modus} om tegen te meten; over "
             f"weggevallen delen zegt deze brief dus niets.")
    weggevallen = list(stand["kwijt"])
    if stuk["ontbreekt"] and stuk["ontbreekt"] not in weggevallen:
        weggevallen.append(stuk["ontbreekt"])

    # De voet die zegt wat deze brief is, bovenaan en niet onderaan: een
    # waarschuwing achteraf is geen waarschuwing. Hier en niet in de
    # brieftekst, want dit is het laatste punt waar alles langskomt wat de
    # ontvanger te zien krijgt en de schrijvende stap kan er niet omheen.
    #
    # Lukt het niet, dan gaat de brief niet naar pa. Dat is de hele reden dat
    # deze voet bestaat, dus een stille uitzondering mag hier niet tot een
    # gewone verzending leiden.
    voet = ""
    try:
        import briefvoet
        voet = briefvoet.html()
    except Exception as e:
        meld(f"LET OP: de briefvoet ontbreekt in de mail: {e}")
        naar_omgeving("GEEN_VOET", "1")

    html = samenstellen(verhaal, stuk["inhoud"], weggevallen, voet)
    if not html:
        meld("Geen verhaal en geen bijlage: er is geen mail samengesteld.")
        return 1
    uit = os.path.join(map, f"{datum}-mail.html")
    with open(uit, "w", encoding="utf-8") as f:
        f.write(html)
    meld(f"Mail samengesteld: verhaal {len(verhaal.split())} woorden, "
         f"bijlage {len(stuk['inhoud'].split())} woorden")
    return 0


def proef():
    fouten = []
    import tempfile

    # DE FOUT VAN 20 OKTOBER. Geen verhaal, wel een bijlage: de mail mag er
    # komen, maar als halve update, zonder kopie naar pa.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as m:
        omg = os.path.join(m, "env")
        open(omg, "w").close()
        oud = os.environ.get("GITHUB_ENV")
        os.environ["GITHUB_ENV"] = omg
        try:
            with open(os.path.join(m, "2026-10-20-bijlage.md"), "w",
                      encoding="utf-8") as f:
                f.write("# Bijlage\n\nDe cijfers.\n")
            bouwen("2026-10-20", "dagelijks", m)
            vlaggen = open(omg, encoding="utf-8").read()
        finally:
            if oud is None:
                os.environ.pop("GITHUB_ENV", None)
            else:
                os.environ["GITHUB_ENV"] = oud
        if "ONVOLLEDIG=het verhaal" not in vlaggen:
            fouten.append("een brief zonder verhaal gaat als gewone brief naar "
                          "beiden")

    def schrijf(m, naam, tekst="inhoud\n"):
        with open(os.path.join(m, naam), "w", encoding="utf-8") as f:
            f.write(tekst)

    # DE FOUT VAN 14 OKTOBER. Geen bijlage, en dan mag de bekendmakingenbrief
    # daar NIET voor in de plaats komen.
    with tempfile.TemporaryDirectory() as m:
        schrijf(m, "2026-10-14-verhaal.md", "# Vastgoed\n\nEen verhaal.\n")
        schrijf(m, "2026-10-14-brief.md", "# Bekendmakingen\n\nKernsignalen.\n")
        stuk = werkstuk("2026-10-14", "dagelijks", m)
        if stuk["inhoud"]:
            fouten.append("zonder bijlage wordt de bekendmakingenbrief toch "
                          "als bijlage gebruikt; dan staat die twee keer in "
                          "de mail, de tweede keer onder een kop die iets "
                          "anders belooft")
        if stuk["ontbreekt"] != "bijlage":
            fouten.append(f"een ontbrekende bijlage wordt niet gemeld: "
                          f"{stuk['ontbreekt']!r}")
        # En de kop hoort dan ook niet in de html te staan.
        html = samenstellen("<p>verhaal</p>", stuk["inhoud"], ["bijlage"])
        if "Bijlage: de cijfers" in html:
            fouten.append("de kop 'Bijlage: de cijfers' staat in de mail "
                          "terwijl er geen bijlage is")
        if "Niet in deze brief: bijlage" not in html:
            fouten.append("de mail zegt niet dat de bijlage ontbreekt")

        # Op zondag is de werkbrief juist WEL het stuk onder het verhaal.
        stuk = werkstuk("2026-10-14", "weekelijks", m)
        if "Bekendmakingen" not in stuk["inhoud"] or stuk["ontbreekt"]:
            fouten.append(f"in de weekeditie hoort de werkbrief de bijlage te "
                          f"zijn: {stuk['ontbreekt']!r}")

    # WAT ER MIST, GEMETEN TEGEN DE VORIGE BRIEF IN DEZELFDE MODUS.
    with tempfile.TemporaryDirectory() as m:
        # Eerst een dag zonder voorganger: dan is er niets gemeten.
        schrijf(m, "2026-10-12-verhaal.md")
        schrijf(m, "2026-10-12-bijlage.md")
        schrijf(m, "2026-10-12-marktprijzen.md")
        stand = wat_er_mist("2026-10-12", "dagelijks", m)
        if stand["gemeten"] or stand["kwijt"]:
            fouten.append(f"zonder eerdere brief wordt toch een uitspraak "
                          f"gedaan: {stand}")
        # De dag erna mist de marktprijzen.
        schrijf(m, "2026-10-13-verhaal.md")
        schrijf(m, "2026-10-13-bijlage.md")
        stand = wat_er_mist("2026-10-13", "dagelijks", m)
        if not stand["gemeten"]:
            fouten.append("met een voorganger wordt er toch niet gemeten")
        elif stand["kwijt"] != ["marktprijzen"]:
            fouten.append(f"het weggevallen deel wordt niet gezien: "
                          f"{stand['kwijt']}")
        # Een leeg bestand telt niet als deel: dat is het geval waarin een
        # stap wel iets aanmaakt maar niets schrijft.
        schrijf(m, "2026-10-14-verhaal.md")
        schrijf(m, "2026-10-14-bijlage.md")
        schrijf(m, "2026-10-14-marktprijzen.md", "")
        stand = wat_er_mist("2026-10-14", "dagelijks", m)
        if "marktprijzen" in delen_van("2026-10-14", m):
            fouten.append("een leeg digestbestand telt als opgeleverd deel")
    # DE WEEKEDITIE MAG DE MAANDAG NIET VERSTOREN. Dit is de lastige kant: de
    # zondagse werkbrief heeft onderdelen die doordeweeks nooit bestaan, en op
    # maandag is zondag de MEEST RECENTE voorganger. Vergelijkt de meting
    # zonder op de modus te letten, dan meldt hij elke maandag dat de
    # beleggingslijst is weggevallen. Zolang de weekeditie in deze proef niet
    # de meest recente voorganger was, bleef die breuk stil.
    with tempfile.TemporaryDirectory() as m:
        schrijf(m, "2026-10-16-verhaal.md")
        schrijf(m, "2026-10-16-bijlage.md")
        schrijf(m, "2026-10-16-marktprijzen.md")
        wat_er_mist("2026-10-16", "dagelijks", m)
        # Zondag: de werkbrief, met onderdelen die doordeweeks niet bestaan.
        schrijf(m, "2026-10-18-verhaal.md")
        schrijf(m, "2026-10-18-brief.md")
        schrijf(m, "2026-10-18-beleggingslijst.md")
        schrijf(m, "2026-10-18-marktprijzen.md")
        wat_er_mist("2026-10-18", "weekelijks", m)
        # Maandag: alles compleet, dus er hoort niets gemeld te worden.
        schrijf(m, "2026-10-19-verhaal.md")
        schrijf(m, "2026-10-19-bijlage.md")
        schrijf(m, "2026-10-19-marktprijzen.md")
        stand = wat_er_mist("2026-10-19", "dagelijks", m)
        if stand["vorige"] != "2026-10-16":
            fouten.append(f"op maandag wordt tegen de zondagse werkbrief "
                          f"gemeten in plaats van tegen de vorige doordeweekse "
                          f"dag: {stand['vorige']!r}")
        if stand["kwijt"]:
            fouten.append(f"op maandag wordt gemeld dat er onderdelen "
                          f"ontbreken terwijl de brief compleet is: "
                          f"{stand['kwijt']}")

    # EEN MAIL ZONDER IETS ERIN IS GEEN MAIL. Alleen de voet mag er niet voor
    # zorgen dat er toch een bericht uitgaat.
    if samenstellen("", "", [], "<p>voet</p>") != "":
        fouten.append("met alleen een voet en geen inhoud wordt er toch een "
                      "mail samengesteld")
    if not samenstellen("<p>verhaal</p>", "", [], "<p>voet</p>"):
        fouten.append("een brief met alleen een verhaal wordt niet "
                      "samengesteld")

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--datum", default=os.environ.get("DATUM", ""))
    ap.add_argument("--modus", default=os.environ.get("MODUS", "dagelijks"))
    ap.add_argument("--map", default="digests")
    args = ap.parse_args()
    if args.proef:
        return proef()
    if not args.datum:
        meld("Geen datum meegegeven.")
        return 1
    return bouwen(args.datum, args.modus, args.map)


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
