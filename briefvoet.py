#!/usr/bin/env python3
"""
De regel boven de brief die zegt wat de brief is.

WAAROM DIT BESTAAT. De brief spreekt in de eerste persoon: "Goedenavond pa",
"ik schreef je eerder al over", "ik let de komende week vooral op". De
ontvanger leest dus een analyse van zijn zoon. In werkelijkheid wordt de tekst
door een taalmodel geschreven, en daar hebben in oktober 2026 vijf beweringen
in gestaan die onwaar waren: drie keer een bovengrens aan oppervlakte in het
puntenstelsel die niet bestaat, een bezitsduur die een plakdatum bleek te
meten, en een splitsingsroute die snel zou zijn omdat de registratie één dag na
het besluit kwam, terwijl er 241 dagen tussen aanvraag en besluit zaten.

Al die fouten zijn later gevonden en er staat nu een toets op. Maar die toetsen
dekken alleen wat al eens is misgegaan, en elk nieuw onderwerp brengt nieuwe
manieren om fout te zitten. De lezer heeft geen enkele manier om een gemeten
getal van een verzonnen getal te onderscheiden, en geen reden om te twijfelen
aan iets dat zijn zoon schrijft.

Deze regel verandert niets aan die fouten. Hij verandert hoe de brief wordt
gelezen: van "mijn zoon zegt dit" naar "dit is machinewerk en ik vraag het na".
Dat is de enige maatregel die ook werkt tegen de fouten die we nog niet kennen.

BOVEN DE BRIEF EN NIET ERONDER. De eerste opzet zette hem onderaan, na de hele
brief en de hele bijlage. Een losse beoordelaar wees erop dat dat het doel
ondergraaft: de lezer komt er dan aan toe nadat hij alles al heeft gelezen en
geloofd. Een waarschuwing achteraf is geen waarschuwing.

Eén tekst op één plek, gebruikt door de mail en door de losse HTML. Twee
kopieën gaan uit elkaar lopen, en dan staat er in de ene mail iets anders dan
in de andere.
"""

# Waar het gezondheidsrapport op toetst of de voet werkelijk in de mail staat.
# Dit is met opzet een hele zinsnede en geen kort kopje: "Over deze brief" zijn
# drie gewone woorden die het taalmodel zelf ook kan schrijven, en dan zou de
# toets slagen terwijl de voet ontbreekt.
TOETSTEKST = "door een taalmodel geschreven en niet door Mark"

KOP = "Over deze brief"

# Let op bij het aanpassen: html() splitst op de eerste punt na de kop, dus de
# kop hoort te eindigen op ".** ". De toets in gezondheid.py zoekt TOETSTEKST,
# dus die zinsnede moet erin blijven staan.
TEKST = (
    f"**{KOP}.** Deze brief wordt op werkdagen en op zondag automatisch "
    "samengesteld uit openbare registers en eigen waarnemingen. De tekst is "
    f"{TOETSTEKST}. Daar zitten fouten in: een getal kan verkeerd staan en een "
    "regel kan verkeerd zijn weergegeven, en dat is de afgelopen weken ook "
    "gebeurd. Sommige cijfers zijn gemeten en andere zijn aannames, en dat "
    "staat er niet overal bij. Neem dus geen besluit op grond van deze brief "
    "zonder het bij Mark na te vragen."
)


def markdown():
    """De voet als markdown, met een streep eronder."""
    return "_" + TEKST.replace("**", "") + "_\n\n---\n\n"


def html():
    """De voet als HTML, voor de mail die wordt verstuurd."""
    kop, rest = TEKST.split(".**", 1)
    return ('<p style="font:14px/1.6 -apple-system,Segoe UI,sans-serif;'
            'color:#4a5b63;background:#f7f9fa;border-left:3px solid #E0A458;'
            'padding:12px 14px;margin:0 0 28px">'
            f'<strong>{kop.replace("**", "")}.</strong>{rest}</p>')


if __name__ == "__main__":
    print(markdown())
    print(html())
    # Een kapotte kop levert geen voet op, en dat moet hier blijken en niet in
    # een stille uitzondering tijdens een run.
    assert TOETSTEKST in TEKST, "TOETSTEKST staat niet in TEKST"
    assert TOETSTEKST in html(), "TOETSTEKST staat niet in de HTML"
    assert TOETSTEKST in markdown(), "TOETSTEKST staat niet in de markdown"
    print("toetsen geslaagd")
