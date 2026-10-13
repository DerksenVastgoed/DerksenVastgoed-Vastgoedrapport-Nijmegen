#!/usr/bin/env python3
"""
Of een link naar een kaartpagina in de brief hoort, en de link zelf.

WAAROM DIT BESTAAT. De drie kaarten staan op GitHub Pages, en Pages werkt
alleen bij een publieke repo. Zodra de repo op prive gaat, geven die drie
links een 404 in een brief die naar pa gaat. Een dode link is erger dan geen
link, want de lezer leert de links over te slaan.

WAAROM GEEN SCHAKELAAR DIE IK OMZET. Een constante die met de hand op False
moet, wordt op het verkeerde moment omgezet of vergeten. De zichtbaarheid van
de repo is bij elke run bekend: GitHub geeft hem mee in het event. De workflow
zet die door als REPO_PRIVE, en deze module leest hem. Zet Mark de repo op
prive, dan verdwijnen de links bij de volgende brief vanzelf.

WAT ALS DE VARIABELE NIET IS GEZET. Dan is de zichtbaarheid onbekend en komt
er geen link. Dat is de voorzichtige kant, want een link die niet opengaat is
het probleem dat we oplossen. Dat die keuze niet stil kan worden gemaakt,
staat in eisen.py: die toetst of de workflow die de brief maakt REPO_PRIVE
werkelijk meegeeft. Zonder die toets zou een vergeten variabele de kaarten
stilletjes uit de brief laten vallen.
"""

import os
import sys

BASIS = "https://derksenvastgoed.github.io/DerksenVastgoed-Vastgoedrapport-Nijmegen/"


def prive(omgeving=None):
    """Of de repo prive staat. Onbekend geldt als prive; zie de kop."""
    o = omgeving if omgeving is not None else os.environ
    waarde = (o.get("REPO_PRIVE") or "").strip().lower()
    if waarde in ("false", "0", "no", "nee"):
        return False
    return True     # "true", leeg, of iets anders dat we niet kennen


def url(pagina):
    """De volledige Pages-url van een kaartpagina."""
    return BASIS + pagina.lstrip("/")


def link(tekst, pagina, omgeving=None):
    """
    Een markdownlink naar een kaartpagina, of een lege string.

    Leeg en niet een link zonder doel: de aanroeper hoort de regel dan
    helemaal weg te laten, zodat er geen losse "Bekijk op de kaart" in de
    brief blijft staan zonder dat er iets te bekijken is.
    """
    if prive(omgeving):
        return ""
    return f"[{tekst}]({url(pagina)})"


def proef():
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. BIJ EEN PUBLIEKE REPO KOMT DE LINK ERIN.
    openbaar = {"REPO_PRIVE": "false"}
    uit = link("Bekijk op de kaart", "top3-kaart.html", openbaar)
    check("publieke repo geeft een link",
          uit, "[Bekijk op de kaart](" + BASIS + "top3-kaart.html)")

    # 2. BIJ EEN PRIVE REPO KOMT ER NIETS. Dit is de hele reden van de module.
    for waarde in ("true", "True", "TRUE"):
        if link("x", "y.html", {"REPO_PRIVE": waarde}) != "":
            fouten.append(f"bij REPO_PRIVE={waarde!r} komt er toch een link")

    # 3. ONBEKEND GELDT ALS PRIVE. Een vergeten variabele mag geen dode link
    # in de brief zetten.
    for omgeving in ({}, {"REPO_PRIVE": ""}, {"REPO_PRIVE": "misschien"}):
        if link("x", "y.html", omgeving) != "":
            fouten.append(f"bij {omgeving!r} komt er toch een link")

    # 4. DE URL KLOPT, OOK MET EEN SCHUINE STREEP VOORAAN.
    check("url", url("kaart-eigendom-ring.html"),
          BASIS + "kaart-eigendom-ring.html")
    check("url met streep", url("/top3-kaart.html"), BASIS + "top3-kaart.html")

    # 5. GEEN ENKELE AANROEPER MAG DE URL ZELF NOG IN ZICH HEBBEN. Anders
    # staat er een tweede plek die de schakelaar niet kent, en dat is precies
    # hoe de ene helft van een regel wel verdwijnt en de andere niet.
    import glob
    for pad in sorted(glob.glob("*.py")):
        if pad in ("kaartlink.py",):
            continue
        try:
            with open(pad, encoding="utf-8") as f:
                bron = f.read()
        except Exception:
            continue
        if "derksenvastgoed.github.io" in bron:
            fouten.append(f"{pad} heeft de Pages-url zelf in zich; die hoort "
                          f"alleen in kaartlink.py te staan, anders kent die "
                          f"plek de schakelaar niet")

    print(f"Proef kaartlink: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    args = ap.parse_args()
    if args.proef:
        return proef()
    print(f"REPO_PRIVE={os.environ.get('REPO_PRIVE')!r}, "
          f"prive={prive()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
