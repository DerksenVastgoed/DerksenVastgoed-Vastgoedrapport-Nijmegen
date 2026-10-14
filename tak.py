"""
Loopt deze tak achter op main, op een bestand dat beide hebben veranderd?

WAAROM DIT BESTAAT. Drie keer in twee dagen ging werk verloren of botste het,
alle drie op dezelfde manier: ik werkte door op een tak die van main was
afgesplitst voordat er iets op main veranderde, en duwde er daarna nog een
commit in.

  13 oktober 17:28  PR met bijlagen.py gemerged.
  13 oktober 17:38  einde_reactietermijn naar diezelfde tak gepusht. Die
                    commit kwam nooit op main en de veldenronde liep een dag
                    met een functie die er niet was. De ronde meldde groen.
  13 oktober 16:21  hetzelfde met het tijdbudget van bijlagen.py.
  14 oktober        PR 96 en PR 95 veranderden beide vergunningsmaten.json.
                    Met de hand gezien, niet door een controle.

Wat alle drie gemeen hebben: niet de tak is het probleem maar de OVERLAP. Een
tak die een bestand aanraakt dat main sinds het afsplitsen ook heeft veranderd,
gaat botsen of werk overschrijven. Een tak die andere bestanden aanraakt mag
eeuwig achterlopen.

NIET GEKEKEN EN NIETS GEVONDEN ZIJN TWEE DINGEN. In een checkout met
--depth=1 bestaat origin/main niet als vergelijkingspunt. Dan zegt deze module
dat hij niet kan kijken, met exitcode 2, en nooit dat het goed is.
"""

import os
import subprocess
import sys


def git(*args, werkmap=None):
    """Een git-opdracht, met de uitvoer als tekst. Faalt stil met None."""
    try:
        r = subprocess.run(["git"] + list(args), capture_output=True,
                           text=True, cwd=werkmap, timeout=60)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def splitspunt(tak, hoofd, werkmap=None):
    """De laatste commit die tak en hoofd samen hebben."""
    return git("merge-base", tak, hoofd, werkmap=werkmap)


def veranderd(van, tot, werkmap=None):
    """De bestanden die tussen twee commits zijn veranderd."""
    uit = git("diff", "--name-only", f"{van}..{tot}", werkmap=werkmap)
    if uit is None:
        return None
    return {r for r in uit.splitlines() if r.strip()}


def botst(tak, hoofd, werkmap=None):
    """
    Welke bestanden botsen er echt, gemeten en niet geschat.

    Twee takken die hetzelfde bestand aanraken botsen vaak NIET: git voegt
    blokken die ver uit elkaar liggen gewoon samen. PR 96 en PR 97 raakten
    beide eisen.txt aan en mergeden schoon. "Dit gaat botsen" zou dus een
    schatting zijn, en git kan het antwoord geven: merge-tree doet de merge in
    het geheugen, zonder de werkmap aan te raken.

    Geeft None als het niet gemeten kon worden, een lege lijst bij een schone
    merge, en anders de botsende bestanden.
    """
    try:
        r = subprocess.run(["git", "merge-tree", "--write-tree",
                            "--name-only", hoofd, tak],
                           capture_output=True, text=True, cwd=werkmap,
                           timeout=60)
    except Exception:
        return None
    if r.returncode == 0:
        return []
    if r.returncode != 1:
        # 2 of hoger is geen botsing maar een fout, bijvoorbeeld een git die
        # --write-tree niet kent. Dan hebben wij niet gemeten.
        return None
    # De uitvoer bestaat uit twee delen, gescheiden door een lege regel: eerst
    # de boom-hash met daaronder de botsende bestanden, daarna de uitleg van
    # git zelf ("Auto-merging ...", "CONFLICT (content): ..."). Alleen lege
    # regels wegfilteren levert die uitleg als bestandsnaam op; de proef
    # betrapte dat meteen.
    eerste = (r.stdout or "").split("\n\n")[0]
    regels = [x.strip() for x in eerste.splitlines() if x.strip()]
    return regels[1:]


def al_gemerged(tak, hoofd="origin/main", werkmap=None):
    """
    Is de PR van deze tak al gemerged, terwijl er nog commits op staan?

    Dit is het incident van 13 oktober 17:38 in zijn precieze vorm. De PR
    mergede om 17:28; om 17:38 duwde ik er nog een commit in. Die commit kwam
    nooit op main en de veldenronde liep een dag met een functie die er niet
    was. Niets stond rood: er was geen botsing en geen foutmelding, het werk
    was er alleen niet.

    Hoe je dat ziet: is de tak gemerged, dan is het splitspunt met main de
    toenmalige top van de tak, en die staat in main als TWEEDE ouder van een
    merge-commit. Het gewone geval, een tak die nooit gemerged is, heeft als
    splitspunt een commit uit de geschiedenis van main zelf, en die is nooit
    de tweede ouder van een merge.
    """
    basis = splitspunt(tak, hoofd, werkmap=werkmap)
    if not basis:
        return None
    uit = git("log", "--merges", "--format=%H %P", hoofd, werkmap=werkmap)
    if uit is None:
        return None
    for regel in uit.splitlines():
        delen = regel.split()
        if basis in delen[2:]:
            return True
    return False


def tak_loopt_achter(tak="HEAD", hoofd="origin/main", werkmap=None):
    """
    Wat deze tak en main sinds het afsplitsen beide hebben aangeraakt.

    Geeft altijd een woordenboek terug met kan_kijken erin. Is dat False, dan
    staat in reden waarom, en zegt deze module niets over de toestand.
    """
    leeg = {"kan_kijken": False, "reden": "", "splitspunt": "",
            "gedeeld": [], "op_tak": [], "op_hoofd": []}
    if git("rev-parse", "--git-dir", werkmap=werkmap) is None:
        return dict(leeg, reden="geen git-repository")
    if git("rev-parse", "--verify", "--quiet", hoofd, werkmap=werkmap) is None:
        # Dit is het geval bij een checkout met --depth=1: main bestaat dan
        # niet als vergelijkingspunt. Geen melding, maar ook geen groen.
        return dict(leeg, reden=f"{hoofd} is hier niet bekend")
    if git("rev-parse", "--verify", "--quiet", tak, werkmap=werkmap) is None:
        # Een tak die nog niet gepusht is bestaat niet als origin/<naam>, en
        # dan gaf merge-base "geen gemeenschappelijke commit" terug. Dat klopt
        # letterlijk maar wijst de verkeerde kant op.
        return dict(leeg, reden=f"{tak} is hier niet bekend")
    basis = splitspunt(tak, hoofd, werkmap=werkmap)
    if not basis:
        return dict(leeg, reden=f"geen gemeenschappelijke commit met {hoofd}")
    op_tak = veranderd(basis, tak, werkmap=werkmap)
    op_hoofd = veranderd(basis, hoofd, werkmap=werkmap)
    if op_tak is None or op_hoofd is None:
        return dict(leeg, reden="de vergelijking zelf mislukte")
    return {"kan_kijken": True, "reden": "", "splitspunt": basis,
            "gedeeld": sorted(op_tak & op_hoofd),
            "op_tak": sorted(op_tak), "op_hoofd": sorted(op_hoofd),
            "botst": botst(tak, hoofd, werkmap=werkmap),
            "al_gemerged": al_gemerged(tak, hoofd, werkmap=werkmap),
            "nog_niet_op_hoofd": len((git("rev-list", f"{hoofd}..{tak}",
                                          werkmap=werkmap) or "").split())}


def melding(stand, tak="HEAD", hoofd="origin/main"):
    """Een regel die zegt wat er aan de hand is, of dat er niets te zien is."""
    if not stand["kan_kijken"]:
        return f"Niet gekeken: {stand['reden']}."
    # De zwaarste eerst: werk dat nergens meer heen gaat. Dit is het incident
    # van 17:38, en het is iets anders dan een botsing.
    if stand.get("al_gemerged") and stand.get("nog_niet_op_hoofd"):
        return (f"LET OP: de PR van deze tak is al gemerged en er "
                f"{'staat' if stand['nog_niet_op_hoofd'] == 1 else 'staan'} "
                f"nog {stand['nog_niet_op_hoofd']} commit(s) op die niet op "
                f"{hoofd} staan. Dat werk komt er nooit vanzelf op. Haal het "
                f"met cherry-pick naar een nieuwe tak.")
    if stand.get("botst"):
        return ("LET OP: deze tak botst met " + hoofd + " op "
                + ", ".join(stand["botst"]) + ". Eerst main erin halen.")
    if not stand["op_hoofd"]:
        return f"{hoofd} is sinds het afsplitsen niet veranderd."
    if not stand["gedeeld"]:
        return (f"{hoofd} veranderde {len(stand['op_hoofd'])} bestand(en) "
                f"sinds het afsplitsen, geen daarvan op deze tak.")
    # Overlap zonder botsing is geen alarm maar wel iets om te weten: git
    # voegt het samen en de uitkomst heeft niemand nagekeken. Of er gebotst
    # zou worden is hierboven al gemeten; is dat niet gelukt, dan zeggen we
    # dat, in plaats van "merget schoon" te beweren.
    kop = f"Deze tak en {hoofd} veranderden beide " + ", ".join(stand["gedeeld"])
    if stand.get("botst") is None:
        return kop + ". Of dat botst is hier niet gemeten."
    return kop + (". Git merget dat schoon, maar de samengevoegde uitkomst "
                  "heeft niemand nagekeken.")


def proef():
    fouten = []

    # DE PROEF BOUWT DE ECHTE SITUATIE, GEEN NAGEMAAKTE TEKST. Een controle op
    # git-gedrag die op zelfbedachte uitvoer rust, meet mijn aanname over git
    # en niet git. Dus: een echte repo, een echte afsplitsing, een echte merge.
    import tempfile
    with tempfile.TemporaryDirectory() as m:
        def g(*a):
            return git(*a, werkmap=m)

        g("init", "-q", "-b", "main")
        g("config", "user.email", "proef@example.com")
        g("config", "user.name", "proef")
        for naam in ("gedeeld.txt", "eigen.txt", "elders.txt"):
            with open(os.path.join(m, naam), "w") as f:
                f.write("begin\n")
        g("add", "-A")
        g("commit", "-q", "-m", "begin")
        # origin/main nabouwen zonder netwerk: een gewone ref mag ook zo heten.
        g("update-ref", "refs/remotes/origin/main", "main")

        g("checkout", "-q", "-b", "tak")
        with open(os.path.join(m, "gedeeld.txt"), "w") as f:
            f.write("tak\n")
        with open(os.path.join(m, "eigen.txt"), "w") as f:
            f.write("tak\n")
        g("commit", "-qam", "werk op de tak")

        # Nog niets op main: dan is er niets te melden.
        stand = tak_loopt_achter("tak", "origin/main", werkmap=m)
        if not stand["kan_kijken"]:
            fouten.append(f"de proefrepo wordt niet gelezen: {stand['reden']}")
        elif stand["gedeeld"]:
            fouten.append(f"main is niet veranderd en toch wordt "
                          f"{stand['gedeeld']} als overlap gemeld; een melding "
                          f"die op goed gedrag afgaat is erger dan geen")

        # Nu main vooruit, op een ander bestand. Nog steeds niets te melden.
        g("checkout", "-q", "main")
        with open(os.path.join(m, "elders.txt"), "w") as f:
            f.write("main\n")
        g("commit", "-qam", "werk op main, ander bestand")
        g("update-ref", "refs/remotes/origin/main", "main")
        stand = tak_loopt_achter("tak", "origin/main", werkmap=m)
        if stand["gedeeld"]:
            fouten.append(f"main raakte een ander bestand aan en toch heet "
                          f"{stand['gedeeld']} overlap")
        if stand["op_hoofd"] != ["elders.txt"]:
            fouten.append(f"de verandering op main wordt niet gezien: "
                          f"{stand['op_hoofd']}")
        # EEN SCHONE MERGE IS EEN LEGE LIJST EN GEEN None. Met None erbij zou
        # "gemeten en niets gevonden" hetzelfde woord krijgen als "niet
        # gemeten", en dat is precies het onderscheid waar deze module om
        # draait. De breuk die None teruggaf bij exitcode 0 bleef zonder deze
        # regel stil.
        if botst("tak", "origin/main", werkmap=m) != []:
            fouten.append(f"een schone merge wordt niet als schoon gemeten: "
                          f"{botst('tak', 'origin/main', werkmap=m)!r}")

        # En nu de echte situatie van 13 oktober: main verandert het bestand
        # waar de tak ook in zit.
        with open(os.path.join(m, "gedeeld.txt"), "w") as f:
            f.write("main\n")
        g("commit", "-qam", "werk op main, zelfde bestand")
        g("update-ref", "refs/remotes/origin/main", "main")
        stand = tak_loopt_achter("tak", "origin/main", werkmap=m)
        if stand["gedeeld"] != ["gedeeld.txt"]:
            fouten.append(f"een bestand dat beide kanten veranderden wordt "
                          f"niet als overlap gemeld: {stand['gedeeld']}")
        elif "gedeeld.txt" not in melding(stand):
            fouten.append(f"de melding noemt het bestand niet: "
                          f"{melding(stand)}")
        # eigen.txt is alleen op de tak veranderd en hoort er niet bij: anders
        # staat de melding bij elke tak aan en kijkt niemand er meer naar.
        if "eigen.txt" in stand["gedeeld"]:
            fouten.append("een bestand dat alleen de tak veranderde heet ook "
                          "overlap")
        # Beide kanten schreven een andere regel in hetzelfde kleine bestand:
        # dit botst echt, en dat moet gemeten zijn en niet geschat.
        if botst("tak", "origin/main", werkmap=m) != ["gedeeld.txt"]:
            fouten.append(f"de botsing wordt niet gemeten: "
                          f"{botst('tak', 'origin/main', werkmap=m)}")

    # DE VORM VAN 13 OKTOBER 17:38: de PR is gemerged en er komt nog een
    # commit bij. Geen botsing, geen foutmelding, het werk is er alleen niet.
    with tempfile.TemporaryDirectory() as m:
        def g2(*a):
            return git(*a, werkmap=m)

        g2("init", "-q", "-b", "main")
        g2("config", "user.email", "proef@example.com")
        g2("config", "user.name", "proef")
        with open(os.path.join(m, "a.txt"), "w") as f:
            f.write("begin\n")
        g2("add", "-A")
        g2("commit", "-q", "-m", "begin")
        g2("checkout", "-q", "-b", "tak")
        with open(os.path.join(m, "a.txt"), "w") as f:
            f.write("werk\n")
        g2("commit", "-qam", "werk dat in de PR zat")
        # De PR wordt gemerged: een merge-commit op main met de tak als
        # tweede ouder. Niet --ff, want dan is er geen merge-commit.
        g2("checkout", "-q", "main")
        g2("merge", "-q", "--no-ff", "-m", "Merge pull request", "tak")
        g2("update-ref", "refs/remotes/origin/main", "main")
        # Zolang er niets bijkomt is er niets aan de hand.
        stand = tak_loopt_achter("tak", "origin/main", werkmap=m)
        if "al gemerged" in melding(stand):
            fouten.append(f"een gemergede tak zonder losse commits wordt "
                           "gemeld; een melding die op goed gedrag afgaat is "
                           "erger dan geen: " + melding(stand))
        # En nu de commit van 17:38.
        g2("checkout", "-q", "tak")
        with open(os.path.join(m, "b.txt"), "w") as f:
            f.write("na de merge\n")
        g2("add", "-A")
        g2("commit", "-qm", "de commit van 17:38")
        stand = tak_loopt_achter("tak", "origin/main", werkmap=m)
        if not stand.get("al_gemerged"):
            fouten.append("een tak waarvan de PR gemerged is wordt niet als "
                          "gemerged gezien")
        # EN EEN TAK DIE NOOIT GEMERGED IS MAG NIET ZO HETEN. Het splitspunt
        # van zo'n tak is een gewone commit uit main, en die is heel vaak de
        # EERSTE ouder van een merge-commit, want main mergede ondertussen een
        # andere PR. Wie de eerste ouder meerekent, meldt dus elke tak. Die
        # breuk bleef stil tot deze tak in de proef stond.
        g2("checkout", "-q", "-b", "andere", "main")
        with open(os.path.join(m, "c.txt"), "w") as f:
            f.write("andere PR\n")
        g2("add", "-A")
        g2("commit", "-qm", "werk in een andere PR")
        g2("checkout", "-q", "main")
        g2("merge", "-q", "--no-ff", "-m", "Merge pull request", "andere")
        g2("update-ref", "refs/remotes/origin/main", "main")
        g2("checkout", "-q", "-b", "verse", "main~1")
        with open(os.path.join(m, "d.txt"), "w") as f:
            f.write("verse tak\n")
        g2("add", "-A")
        g2("commit", "-qm", "werk op een verse tak")
        if al_gemerged("verse", "origin/main", werkmap=m):
            fouten.append("een tak die nooit gemerged is heet toch gemerged; "
                          "dan staat de melding bij elke tak aan")
        if stand.get("nog_niet_op_hoofd") != 1:
            fouten.append(f"het aantal commits buiten main is "
                          f"{stand.get('nog_niet_op_hoofd')} en niet 1")
        if "al gemerged" not in melding(stand):
            fouten.append(f"de commit na de merge wordt niet gemeld: "
                          f"{melding(stand)}")

    # NIET GEKEKEN KRIJGT EEN EIGEN ANTWOORD. Zonder dit zou een repo zonder
    # origin/main als "niets aan de hand" doorgaan, en dat is precies de vorm
    # waarin de drie incidenten zich voordeden: stil groen.
    with tempfile.TemporaryDirectory() as m:
        git("init", "-q", "-b", "main", werkmap=m)
        git("config", "user.email", "proef@example.com", werkmap=m)
        git("config", "user.name", "proef", werkmap=m)
        with open(os.path.join(m, "a.txt"), "w") as f:
            f.write("a\n")
        git("add", "-A", werkmap=m)
        git("commit", "-q", "-m", "begin", werkmap=m)
        stand = tak_loopt_achter("HEAD", "origin/main", werkmap=m)
        if stand["kan_kijken"]:
            fouten.append("zonder origin/main doet deze module alsof hij "
                          "gekeken heeft")
        if not stand["reden"]:
            fouten.append("niet kunnen kijken gaat zonder reden voorbij")
        if "Niet gekeken" not in melding(stand):
            fouten.append(f"de melding verzwijgt dat er niet gekeken is: "
                          f"{melding(stand)}")
        # En een tak die niet bestaat krijgt zijn eigen reden en niet die van
        # een ontbrekend splitspunt.
        stand = tak_loopt_achter("bestaat-niet", "main", werkmap=m)
        if stand["kan_kijken"] or "bestaat-niet" not in stand["reden"]:
            fouten.append(f"een tak die niet bestaat wordt verkeerd gemeld: "
                          f"{stand['reden']!r}")

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten", file=sys.stderr)
    return 1 if fouten else 0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--tak", default="HEAD")
    ap.add_argument("--hoofd", default="origin/main")
    args = ap.parse_args()
    if args.proef:
        return proef()
    stand = tak_loopt_achter(args.tak, args.hoofd)
    print(melding(stand, args.tak, args.hoofd), file=sys.stderr)
    if not stand["kan_kijken"]:
        return 2
    return 1 if stand["gedeeld"] else 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
