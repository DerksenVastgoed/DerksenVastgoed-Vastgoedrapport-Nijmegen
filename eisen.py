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
TOEGESTAAN = VERPLICHT + ("soort", "let op", "deels")

# DRIE STANDEN EN NIET TWEE. Een eis met een proef EN een "let op" dat zegt
# dat hij niet verder te handhaven is, is deels afgedwongen. Die bij de
# afgedwongen eisen tellen overdrijft, en bij de niet-afgedwongen
# onderschat. Dat verschil zichtbaar houden is precies waarvoor dit bestand
# bestaat, dus krijgt het een eigen veld: "deels: ja".


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


WORKFLOWS = (os.path.join(".github", "workflows", "bekendmakingen.yml"),
             os.path.join(".github", "workflows", "voorraad.yml"))
BRIEFWORKFLOW = WORKFLOWS[0]
DAGNAMEN = ("zondag", "maandag", "dinsdag", "woensdag", "donderdag",
            "vrijdag", "zaterdag")


def _crondagen(veld):
    """
    De weekdagen uit het laatste veld van een cron, als verzameling 0 t/m 6.

    Cron kent zondag als 0 en als 7. Een expander die dat niet weet, noemt
    "17 0 * * 7" een zondag die er niet is en laat de zondag ongedekt lijken.
    """
    dagen = set()
    for deel in str(veld).split(","):
        deel, stap = deel.strip(), 1
        if "/" in deel:
            deel, _, s = deel.partition("/")
            try:
                stap = max(1, int(s))
            except ValueError:
                stap = 1
        if deel == "*":
            begin, eind = 0, 6
        elif "-" in deel:
            a, _, b = deel.partition("-")
            try:
                begin, eind = int(a), int(b)
            except ValueError:
                continue
        else:
            try:
                begin = eind = int(deel)
            except ValueError:
                continue
        for d in range(begin, eind + 1, stap):
            dagen.add(0 if d == 7 else d)
    return {d for d in dagen if 0 <= d <= 6}


def _alle_workflows(map_pad=os.path.join(".github", "workflows")):
    """
    Elk workflowbestand, en niet een vaste lijst van twee.

    WAAROM NIET EEN LIJST. commitstap() stond op WORKFLOWS, een tuple met
    bekendmakingen.yml en voorraad.yml. Zo'n lijst moet worden bijgewerkt bij
    elke nieuwe workflow, en dat gebeurt niet: deze controle bestaat juist
    omdat dezelfde fout in controle_sleutels_in_stappen al een keer een nieuwe
    workflow niet dekte. Nu komt de lijst uit de map.
    """
    try:
        return tuple(os.path.join(map_pad, n) for n in sorted(os.listdir(map_pad))
                     if n.endswith((".yml", ".yaml")))
    except Exception:
        return ()


def commitstap(paden=None):
    """
    Of een run die gegevens terugschrijft geen broncode kan veranderen.

    WAT HIER GEBEURDE. voorraad.yml zette bij een geweigerde push HEAD naar de
    remote met "git reset --soft" en committeerde opnieuw. Soft laat de hele
    index van de oude checkout staan, dus die commit schreef de boom van het
    moment waarop de ronde BEGON. De ronde van 13 oktober 07:04 duurde 102
    minuten; in dat uur werden PR 56 en PR 57 gemerged, en zijn commit van
    08:46 draaide beide volledig terug: zes bestanden broncode en drie eisen.

    Het ergste eraan was niet de terugdraai maar de stilte. Alle proeven bleven
    groen, want de eisen die naar die controles verwezen waren met dezelfde
    commit verdwenen. Daarom staat deze toets hier en niet in een proef van een
    van beide workflows: hij moet blijven staan ook als alles eromheen wegvalt.

    Twee dingen per workflow: geen "git reset --soft", en een toets die een
    commit tegenhoudt die .py of .yml aanraakt.
    """
    fouten = []
    paden = paden if paden is not None else _alle_workflows()
    if not paden:
        return ["geen workflowbestand gevonden om de commitstap te toetsen"]
    gekeken = 0
    for pad in paden:
        try:
            with open(pad, encoding="utf-8") as f:
                bron = f.read()
        except Exception as e:
            fouten.append(f"{pad} niet te lezen: {str(e)[:50]}")
            continue
        # ALLEEN WORKFLOWS DIE WERKELIJK COMMITTEN. Een verkenning die niets
        # terugschrijft heeft geen commitstap en dus ook geen vangnet nodig.
        # De uitzondering volgt uit de inhoud van het bestand en niet uit een
        # lijst met namen, want zo'n lijst veroudert.
        if "git commit" not in bron:
            continue
        gekeken += 1
        # Alleen echte shellregels, niet het commentaar dat de fout uitlegt.
        regels = [r.strip() for r in bron.splitlines()
                  if not r.strip().startswith("#")]
        for r in regels:
            if "git reset --soft" in r:
                fouten.append(f"{pad} gebruikt 'git reset --soft'; die schrijft "
                              f"de hele index van de oude checkout terug en "
                              f"draait werk terug dat tijdens de run is "
                              f"gemerged")
                break
        if "geen_broncode" not in bron:
            fouten.append(f"{pad} committeert en heeft geen toets die een "
                          f"commit tegenhoudt die broncode aanraakt")
    if not gekeken:
        fouten.append("geen enkele workflow committeert; dat kan kloppen, "
                      "maar dan toetst deze controle niets")
    return fouten


def leesbaar_kanaal(paden=None):
    """
    Of elke workflow zijn uitkomst ergens neerzet waar wij hem kunnen lezen.

    WAT HIER GEBEURDE. dossiermail.yml draaide op 13 oktober groen: zes
    stappen gelukt, werkmap schoon. Wat er in het dossier zat was alleen naar
    stderr geschreven, en dat komt in het joblogboek van GitHub. Dat logboek
    zit achter productionresultssa8.blob.core.windows.net, dat van buiten de
    runner wordt geweigerd. Ik had dus een verkenning gebouwd waarvan ik de
    uitkomst niet kon lezen: groen en onleesbaar tegelijk.

    Dezelfde fout trof die ochtend de brief. Daar is hij opgelost door de
    staart van het logboek in briefstand.json te zetten. Zo'n oplossing per
    geval houdt niet: de volgende workflow begint weer met stderr. Daarom
    toetst dit de regel in plaats van de twee gevallen.

    WAT GELDT ALS EEN LEESBAAR KANAAL. Iets dat van buiten de runner op te
    vragen is: een commit, een issue, een mail, of een artefact. Het
    joblogboek niet. De lijst komt uit de inhoud van het bestand en niet uit
    een lijst met workflownamen, want zo'n lijst wordt niet bijgewerkt.
    """
    KANALEN = ("git commit", "gh issue", "gh api", "upload-artifact",
               "MAIL_USERNAME", "GITHUB_STEP_SUMMARY")
    fouten = []
    paden = paden if paden is not None else _alle_workflows()
    if not paden:
        return ["geen workflowbestand gevonden om het kanaal te toetsen"]
    for pad in paden:
        try:
            with open(pad, encoding="utf-8") as f:
                bron = f.read()
        except Exception as e:
            fouten.append(f"{pad} niet te lezen: {str(e)[:50]}")
            continue
        # Alleen echte regels, niet het commentaar waarin deze fout wordt
        # uitgelegd; anders maakt de uitleg zelf de toets groen.
        echt = "\n".join(r for r in bron.splitlines()
                         if not r.strip().startswith("#"))
        if not any(k in echt for k in KANALEN):
            fouten.append(f"{pad} zet zijn uitkomst nergens neer waar wij hem "
                          f"kunnen lezen. Alles wat de stappen printen komt "
                          f"in het joblogboek, en dat wordt van buiten de "
                          f"runner geweigerd. Een commit, een issue, een mail "
                          f"of een artefact is wel te lezen.")
    return fouten


def _modules_die_importeren(naam, map_pad="."):
    """Welke modules in de map een bepaalde module importeren. Uit de map."""
    uit = []
    try:
        namen = sorted(n for n in os.listdir(map_pad) if n.endswith(".py"))
    except Exception:
        return uit
    for n in namen:
        if n == naam + ".py":
            continue
        try:
            with open(os.path.join(map_pad, n), encoding="utf-8") as f:
                bron = f.read()
        except Exception:
            continue
        if re.search(rf"^\s*(import {naam}\b|from {naam} import)", bron,
                     re.M):
            uit.append(n)
    return uit


def kaartschakelaar():
    """
    Of de workflow die een kaartmodule aanroept ook REPO_PRIVE meegeeft.

    WAT HIER SPEELT. De drie kaarten in de brief staan op GitHub Pages, en
    Pages werkt alleen bij een publieke repo. kaartlink.py laat de link weg
    zodra REPO_PRIVE "true" is, en ook als hij niet is gezet, want een dode
    link in een brief naar pa is erger dan geen link.

    DAAROM DEZE TOETS. Die voorzichtige kant heeft een keerzijde: zet niemand
    de variabele, dan vallen de kaarten stil uit de brief en lijkt dat op een
    bewuste keuze. "Niet gezet" en "op prive gezet" mogen niet hetzelfde
    lezen. Dus toetst dit dat elke workflow die zo'n module aanroept de
    variabele werkelijk meegeeft.

    De lijst modules komt uit de map en niet uit een opsomming hier: wie
    kaartlink gaat importeren, valt er vanzelf onder.
    """
    fouten = []
    modules = _modules_die_importeren("kaartlink")
    if not modules:
        # Geen enkele module gebruikt de schakelaar. Dat kan kloppen, maar dan
        # toetst dit niets en hoort dat te blijken.
        return ["geen enkele module importeert kaartlink; dan staat de "
                "Pages-url weer los in de scripts of is de schakelaar weg"]
    for pad in _alle_workflows():
        try:
            with open(pad, encoding="utf-8") as f:
                bron = f.read()
        except Exception as e:
            fouten.append(f"{pad} niet te lezen: {str(e)[:50]}")
            continue
        roept = [m for m in modules if f"python {m}" in bron or
                 f"python3 {m}" in bron]
        if not roept:
            continue
        if "REPO_PRIVE" not in bron:
            fouten.append(f"{pad} roept {', '.join(roept)} aan en geeft "
                          f"REPO_PRIVE niet mee. Dan vallen de kaartlinks "
                          f"stil uit de brief, ook als de repo publiek is.")
    return fouten


def pijp_zonder_vangnet(paden=None):
    """
    Of een stap die iets door een pijp stuurt ook pipefail aanzet.

    WAT HIER GEBEURDE. De veldenronde van 13 oktober meldde "gelukt" terwijl
    python met een traceback stierf. De regel was

        python publicatievelden.py ... 2>&1 | tee "$RUNNER_TEMP/ronde.log"

    en in een pijplijn is de exitcode die van het LAATSTE commando. tee
    slaagt altijd. De stap stond dus groen, er werd niets gecommit, en de
    meldstap ging niet af omdat er formeel geen mislukking was. Drie rondes
    kwijt voordat ik doorhad dat de fout al in de eerste stap zat.

    Dit is geen eigenaardigheid van die ene regel. Elke stap die uitvoer
    door tee, head, tail of grep haalt om hem te bewaren of te filteren,
    verliest de exitcode van wat ervoor stond. Daarom toetst dit alle
    workflows in de map en niet die ene.

    Commentaar telt niet mee: de uitleg van deze fout zou de toets anders
    zelf groen maken.
    """
    # ALLEEN tee, EN NIET head, tail OF grep.
    #
    # Eerst stond hier ook head, tail en grep. Nagemeten op de echte
    # workflows gaf dat twee treffers in de briefworkflow die geen van
    # beide een fout zijn: daar staat "grep -E Versies ... | head -3" om
    # iets te TONEN, en een grep die niets vindt is daar geen mislukking.
    # Met pipefail zou die stap gaan melden bij correct gedrag, en dat is
    # precies het soort valse melding dat de lezer leert het logboek over te
    # slaan.
    #
    # tee is anders: dat is het patroon "voer dit uit en bewaar de uitvoer".
    # Daar is de uitkomst van wat ervoor staat het hele punt, en die mag niet
    # verdwijnen.
    PIJPEN = re.compile(r"\|\s*tee\b")
    fouten = []
    paden = paden if paden is not None else _alle_workflows()
    if not paden:
        return ["geen workflowbestand gevonden om de pijpen te toetsen"]
    for pad in paden:
        try:
            with open(pad, encoding="utf-8") as f:
                bron = f.read()
        except Exception as e:
            fouten.append(f"{pad} niet te lezen: {str(e)[:50]}")
            continue
        for blok in bron.split("\n      - name: ")[1:]:
            naam = blok.split("\n")[0].strip()
            if "run: |" not in blok:
                continue
            run = blok.split("run: |", 1)[1]
            echt = "\n".join(r for r in run.splitlines()
                              if not r.strip().startswith("#"))
            if PIJPEN.search(echt) and "pipefail" not in echt:
                fouten.append(f"{pad}, stap {naam[:48]!r}: stuurt uitvoer "
                              f"door een pijp zonder 'set -o pipefail'. De "
                              f"exitcode is dan die van het laatste commando "
                              f"en een fout ervoor verdwijnt.")
    return fouten


def startdagen(pad=BRIEFWORKFLOW):
    """
    Voor welke weekdagen de briefworkflow een geplande start heeft.

    Levert (per_dag, crons, fout): per_dag is een dict 0 t/m 6 met het aantal
    crons dat op die dag vuurt, crons het aantal gelezen cronregels, en fout
    een reden als het bestand niet te lezen was.

    WAAROM DIT HIER STAAT EN NIET IN HET GEZONDHEIDSRAPPORT. Een ontbrekende
    dag hoort de poort tegen te houden en niet alleen in de bijlage te staan.
    Zaterdag stond niet in de cron en niet in de geplande taak die de run van
    buitenaf start; de brief van 3 en 10 oktober bestond dus alleen omdat er
    iemand keek. Dat was aan niets te zien, want de digests-map had voor elke
    dag een brief.

    WAT DIT NIET MEET. Niet of de brief op tijd komt. De cron van GitHub vuurt
    op deze repo uren te laat, en de start die hem wel op tijd brengt komt van
    een geplande taak buiten de repo, die dit programma niet kan zien. Dit
    meet de terugval die in de repo zelf vastligt.
    """
    per_dag = {d: 0 for d in range(7)}
    try:
        with open(pad, encoding="utf-8") as f:
            regels = f.read().splitlines()
    except Exception as e:
        return (per_dag, 0, f"{pad} niet te lezen: {str(e)[:60]}")
    crons = 0
    for regel in regels:
        kaal = regel.strip()
        if not kaal.startswith("- cron:"):
            continue
        # EERST HET COMMENTAAR, DAN DE AANHALINGSTEKENS. Andersom haalt strip
        # alleen het aanhalingsteken aan de voorkant weg, want achteraan staat
        # het commentaar; dan blijft het laatste veld '1-6"' en leest geen
        # enkele dag. De controle meldde zo zeven ongedekte dagen terwijl er
        # drie crons stonden.
        waarde = kaal.split(":", 1)[1].split("#", 1)[0].strip()
        velden = waarde.strip('"').strip("'").strip().split()
        if len(velden) != 5:
            continue
        crons += 1
        for d in _crondagen(velden[4]):
            per_dag[d] += 1
    return (per_dag, crons, "")


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

    heeft = [e for e in eisen if (e.get("proef") or "-") != "-"]
    deels = [e for e in heeft if (e.get("deels") or "").lower() == "ja"]
    met_proef = [e for e in heeft if e not in deels]
    zonder = [e for e in eisen if (e.get("proef") or "-") == "-"]
    # Een eis die als deels is gemarkeerd moet zeggen waarom, net als een eis
    # zonder proef. Anders leest "deels" als een slag om de arm.
    for e in deels:
        if not e.get("let op"):
            fouten.append(f"eis met deels: ja maar zonder uitleg: "
                          f"{e['eis'][:60]}")

    # Een eis zonder proef moet uitleggen waarom, anders leest "-" als
    # vergeten in plaats van als bewuste keuze.
    for e in zonder:
        if not e.get("let op"):
            fouten.append(f"eis zonder proef en zonder uitleg: "
                          f"{e['eis'][:60]}")

    beschikbaar = set(_modules_met_proef())
    gedraaid = {}
    for e in heeft:
        # EEN EIS MAG OP MEER DAN EEN PLEK WORDEN AFGEDWONGEN, gescheiden
        # door een puntkomma. Dat is er omdat de eis over het leesbare kanaal
        # op twee plaatsen bleek te gelden: in de brief en in een verkenning.
        # Een tweede veld ernaast zou hetzelfde ding twee namen geven, en dan
        # kijkt de controle maar naar een van de twee.
        for verwijzing in e["proef"].split(";"):
            module, _, label = verwijzing.partition(":")
            module, label = module.strip(), label.strip()
            if not module:
                continue
            if module == "eisen":
                # Naar onszelf verwijzen mag, maar het label moet dan wel in
                # dit bestand staan: anders verdwijnt een controle hier
                # zonder dat de eis het merkt.
                if label and label not in (_bron("eisen") or ""):
                    fouten.append(f"de controle {label!r} staat niet in "
                                  f"eisen.py: {e['eis'][:50]}")
                continue
            if module not in beschikbaar:
                fouten.append(f"eis verwijst naar {module!r}, maar dat heeft "
                              f"geen --proef: {e['eis'][:50]}")
                continue
            bron = _bron(module)
            if label and label not in (bron or ""):
                fouten.append(f"de controle {label!r} staat niet in "
                              f"{module}.py; omgedoopt of weggehaald? Eis: "
                              f"{e['eis'][:50]}")
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
    # elke proef eindigt op sys.exit.
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

    # Een run die gegevens terugschrijft mag geen broncode veranderen. Zie
    # commitstap() voor wat dat op 13 oktober kostte.
    fouten.extend(commitstap())

    # Elke workflow moet zijn uitkomst neerzetten waar wij hem kunnen lezen.
    # Zie leesbaar_kanaal() voor de verkenning die groen en onleesbaar
    # tegelijk was.
    fouten.extend(leesbaar_kanaal())

    # Een kaartlink die stil wegvalt leest als een keuze. Zie
    # kaartschakelaar().
    fouten.extend(kaartschakelaar())

    # COMMENTAAR MAG DE TOETS NIET GROEN MAKEN. Het blok hieronder noemt
    # pipefail wel in de uitleg en zet het niet aan. Zonder dit geval zou
    # een stap die de fout keurig uitlegt en hem laat staan, erdoorheen
    # glippen, en dat is precies hoe de uitleg van een fout die fout
    # verbergt.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _m:
        _p = os.path.join(_m, "nep.yml")
        with open(_p, "w", encoding="utf-8") as _f:
            _f.write("jobs:\n  x:\n    steps:\n"
                     "      - name: Zonder vangnet\n"
                     "        run: |\n"
                     "          # hier hoort set -o pipefail te staan\n"
                     "          python iets.py 2>&1 | tee /tmp/log\n")
        _r = pijp_zonder_vangnet([_p])
        if len(_r) != 1:
            fouten.append(f"een stap die pipefail alleen in commentaar noemt "
                          f"wordt niet gemeld: {_r}")
        _p2 = os.path.join(_m, "goed.yml")
        with open(_p2, "w", encoding="utf-8") as _f:
            _f.write("jobs:\n  x:\n    steps:\n"
                     "      - name: Met vangnet\n"
                     "        run: |\n"
                     "          set -o pipefail\n"
                     "          python iets.py 2>&1 | tee /tmp/log\n")
        if pijp_zonder_vangnet([_p2]):
            fouten.append("een stap met pipefail wordt ten onrechte gemeld")
        _p3 = os.path.join(_m, "tonen.yml")
        with open(_p3, "w", encoding="utf-8") as _f:
            _f.write("jobs:\n  x:\n    steps:\n"
                     "      - name: Iets tonen\n"
                     "        run: |\n"
                     "          grep -E Versies rapport.md | head -3\n")
        if pijp_zonder_vangnet([_p3]):
            fouten.append("een grep die iets toont wordt ten onrechte "
                          "gemeld; een grep zonder treffer is daar geen fout")

    # Een stap die zijn uitvoer door een pijp stuurt, verliest de exitcode
    # van wat ervoor stond. Zie pijp_zonder_vangnet() voor wat dat kostte.
    fouten.extend(pijp_zonder_vangnet())

    # Elke dag van de week moet een geplande start van de brief hebben. Een
    # dag zonder cron heeft geen terugval, en dat valt pas op als niemand
    # kijkt. Zie startdagen() voor wat dit wel en niet meet.
    per_dag, crons, fout = startdagen()
    if fout:
        fouten.append(f"de startdagen niet na te meten: {fout}")
    elif not crons:
        fouten.append(f"geen enkele cron in {BRIEFWORKFLOW}; dan hangt de "
                      f"brief volledig aan de geplande taak buiten de repo")
    else:
        kaal = [DAGNAMEN[d] for d in range(7) if not per_dag[d]]
        if kaal:
            fouten.append(f"zonder geplande start: {', '.join(kaal)}. Op die "
                          f"dag komt de brief alleen als iemand hem met de "
                          f"hand start.")

    print(f"Eisen: {len(eisen)} gelezen, {len(met_proef)} afgedwongen, "
          f"{len(deels)} deels, {len(zonder)} bewust zonder, "
          f"{len(beschikbaar)} modules met een proef nagekeken op hun "
          f"exitcode" + ("" if snel else f", {len(gedraaid)} gedraaid"),
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
    heeft = [e for e in eisen if (e.get("proef") or "-") != "-"]
    deelt = [e for e in heeft if (e.get("deels") or "").lower() == "ja"]
    met = [e for e in heeft if e not in deelt]
    zonder = [e for e in eisen if (e.get("proef") or "-") == "-"]
    r = ["## Wat de brief moet doen, en wat daarvan vastligt", ""]
    r.append(f"_{len(eisen)} eisen. {len(met)} worden volledig afgedwongen "
             f"door een proef die bij elke run draait, {len(deelt)} deels, en "
             f"{len(zonder)} niet. Die laatste twee groepen staan er met de "
             f"reden waarom ze niet verder te handhaven zijn; dat verschil "
             f"hoort zichtbaar te zijn in plaats van impliciet._")
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
            if (e.get("proef") or "-") == "-":
                kop = "**Niet afgedwongen.**"
            elif (e.get("deels") or "").lower() == "ja":
                kop = "**Deels vastgelegd.**"
            else:
                kop = "**Vastgelegd.**"
            r.append(f"- {kop} {e['eis']}")
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
