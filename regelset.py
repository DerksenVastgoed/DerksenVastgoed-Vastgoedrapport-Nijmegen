#!/usr/bin/env python3
"""
De regels die op een pand van toepassing zijn, uit een gegevensbestand.

WAAROM DIT BESTAAT. De doorrekening per pand toetst al vier regels: de
WOZ-grens van €278.000 waaronder een omzettingsvergunning altijd wordt
geweigerd, de opkoopbeschermingsgrens van €396.000, de kamerverhuurtoets en de
splitsingstoets. Dat werkt precies zoals het hoort: een pand komt langs, de
regels worden erop getoetst, en wat afvalt staat in het dossier.

Maar die vier staan als code in marktprijzen_bag.py. Een regel die de gemeente
vandaag publiceert kan daar niet in komen zonder dat iemand Python schrijft.
Daardoor kwam de beleidsregel over wonen op de eerste bouwlaag wel in de brief
terecht als nieuws, maar nooit bij een pand waarop hij van toepassing is, en
over een half jaar is hij vergeten terwijl hij dan nog geldt.

Dit bestand maakt van die regelset gegevens. Een regel in regelset.txt loopt
mee in de doorrekening van elk pand, vandaag en over een half jaar.

WAT DIT MET OPZET NIET IS. Geen taal om voorwaarden in te programmeren. De
voorwaarden zijn een vaste, kleine set vergelijkingen op velden die we van een
pand kennen. Dat is minder krachtig en dat is de bedoeling: een bestand dat
door iemand met de hand wordt bijgewerkt mag de run niet kunnen laten
omvallen, en een voorwaarde die niemand kan nalezen is geen voorwaarde. Wat
niet in deze set past, hoort als code met een eigen toets.

DE VOORWAARDE KOMT NIET UIT DE PUBLICATIETEKST. "Achterin het pand, niet
zichtbaar van de straat, hoogstens 30% van de eerste bouwlaag" is geen veld in
een register. Iemand moet die regel één keer omzetten in iets toetsbaars, en
dat is precies de plek waar een taalmodel fouten maakt die niemand meer ziet.
Dus: het opschrijven is handwerk, het toepassen gaat automatisch.

Gebruik:
  python regelset.py                 # welke regels er in het bestand staan
  python regelset.py --zelftest
"""

import argparse
import os
import re
import sys

PAD = "regelset.txt"

# De velden waarop een regel mag toetsen, met hoe ze gelezen worden. Alles wat
# hier niet in staat, is in regelset.txt een fout en geen stille overslag.
GETALVELDEN = ("oppervlakte_min", "oppervlakte_max", "woz_min", "woz_max",
               "prijs_min", "prijs_max", "eenheden_min", "eenheden_max")
LIJSTVELDEN = ("buurt", "functie", "label", "straten")
TEKSTVELDEN = ("naam", "bron", "sinds", "gevolg", "let_op", "monument")
TOEGESTAAN = set(GETALVELDEN) | set(LIJSTVELDEN) | set(TEKSTVELDEN)
VERPLICHT = ("naam", "gevolg")


def _lijst(waarde):
    return [d.strip().lower() for d in (waarde or "").split(",") if d.strip()]


# Schrijfwijzen van een straatnaam die naast elkaar bestaan. De advertenties
# schrijven "St. Annastraat", de BAG schrijft "Sint Annastraat", en
# plintgebied.txt wordt door beide gelezen: door plintregel.py tegen de
# BAG-voorraad en door dit bestand tegen het advertentieadres. Eén lijst met
# twee lezers die tegengestelde eisen stellen, dus hier alles naar één vorm.
AFKORTING = (("sint ", "st"), ("st. ", "st"), ("st ", "st"),
             ("professor ", "prof"), ("prof. ", "prof"),
             ("burgemeester ", "burg"), ("burg. ", "burg"),
             ("doctor ", "dr"), ("dr. ", "dr"),
             ("van der ", "vd"), ("van de ", "vd"))


def _straatsleutel(naam):
    """Eén vorm per straat, los van de schrijfwijze."""
    a = (naam or "").lower().strip()
    for lang, kort in AFKORTING:
        if a.startswith(lang):
            a = kort + a[len(lang):]
            break
    return "".join(a.replace(".", " ").split())


def lees(pad=PAD):
    """
    De regels uit het bestand, plus de fouten die erin staan.

    Geeft (regels, fouten) terug. Een regel met een onbekend veld of zonder
    naam of gevolg komt niet in de lijst maar wel in de fouten, zodat het
    gezondheidsrapport hem meldt. Stil overslaan zou betekenen dat een
    typefout een regel uitschakelt zonder dat iemand het merkt, en dat is de
    fout die dit project het vaakst heeft gemaakt.
    """
    if not os.path.exists(pad):
        return [], []
    regels, fouten, huidig, regelnr_start = [], [], {}, 0

    def afsluiten():
        if not huidig:
            return
        mist = [v for v in VERPLICHT if not huidig.get(v)]
        if mist:
            fouten.append(f"regel bij regelnummer {regelnr_start}: "
                          f"{' en '.join(mist)} ontbreekt")
            huidig.pop("_kapot", None)
        elif huidig.pop("_kapot", False):
            # EEN ONBEKEND VELD MAAKT DE HELE REGEL ONGELDIG, en levert niet
            # alleen een melding op. Een veld dat wij niet kennen was bedoeld
            # als voorwaarde: staat er "buurt" verkeerd gespeld, dan zou de
            # regel zonder die voorwaarde op elk pand in de stad gaan gelden.
            # Een regel die te breed geldt is erger dan een regel die niet
            # geldt, want die eerste zet een onjuiste bewering in het dossier
            # van een pand.
            fouten.append(f"regel '{huidig.get('naam', '?')}' is niet gebruikt: "
                          f"hij bevat een veld dat wij niet kennen, en dan zou "
                          f"hij te breed kunnen gelden")
        else:
            regels.append(dict(huidig))
        huidig.clear()

    try:
        with open(pad, encoding="utf-8") as f:
            for nr, rauw in enumerate(f, 1):
                # COMMENTAAR, EN WAT GEEN COMMENTAAR IS. Een hele regel die met
                # een hekje begint is commentaar. Middenin is een hekje alleen
                # commentaar als er witruimte of het regeleinde achter staat,
                # dus " # noot" wel en "pand #12" niet.
                #
                # Met een onvoorwaardelijke split op "#" verdween het anker uit
                # een bron-URL en werd "geldt voor pand #12 en hoger" afgekapt
                # tot "geldt voor pand". Die halve tekst gaat als feit met bron
                # naar het dossier en dus naar de brief.
                if rauw.lstrip().startswith("#"):
                    continue
                tekst = re.split(r"\s#(?=\s|$)", rauw.rstrip("\n"),
                                 maxsplit=1)[0].rstrip()
                if not tekst.strip():
                    continue
                if tekst.strip() == "---":
                    afsluiten()
                    regelnr_start = nr
                    continue
                if ":" not in tekst:
                    fouten.append(f"regelnummer {nr}: geen dubbele punt in "
                                  f"'{tekst.strip()[:40]}'")
                    continue
                sleutel, waarde = tekst.split(":", 1)
                sleutel = sleutel.strip().lower().replace(" ", "_")
                if sleutel not in TOEGESTAAN:
                    fouten.append(f"regelnummer {nr}: onbekend veld "
                                  f"'{sleutel}', dus deze regel wordt niet "
                                  f"gebruikt")
                    huidig["_kapot"] = True
                    continue
                if sleutel in huidig:
                    # Twee keer hetzelfde veld in één blok overschreef stil. Bij
                    # een lijstveld is dat de natuurlijke fout: iemand denkt een
                    # buurt toe te voegen en krijgt een regel die alleen in de
                    # laatste buurt geldt.
                    fouten.append(f"regelnummer {nr}: '{sleutel}' staat twee "
                                  f"keer in dezelfde regel; zet meerdere "
                                  f"waarden met komma's op één regel")
                    huidig["_kapot"] = True
                    continue
                if not waarde.strip():
                    # Een leeg veld toetste niets, gaf geen fout en werd door de
                    # toets niet als "zonder voorwaarde" gezien, want de sleutel
                    # stond er wel. Dan geldt de regel breder dan bedoeld.
                    fouten.append(f"regelnummer {nr}: '{sleutel}' staat er "
                                  f"zonder waarde")
                    huidig["_kapot"] = True
                    continue
                if sleutel in GETALVELDEN:
                    getal, fout = _getal(waarde)
                    if fout:
                        fouten.append(f"regelnummer {nr}: {fout} bij {sleutel}")
                        huidig["_kapot"] = True
                        continue
                    huidig[sleutel] = getal
                elif sleutel == "monument":
                    if waarde.strip().lower() not in ("ja", "nee"):
                        fouten.append(f"regelnummer {nr}: monument moet ja of "
                                      f"nee zijn, niet '{waarde.strip()}'")
                        huidig["_kapot"] = True
                        continue
                    huidig[sleutel] = waarde.strip().lower()
                else:
                    huidig[sleutel] = waarde.strip()
                if not regelnr_start:
                    regelnr_start = nr
        afsluiten()
    except Exception as e:
        fouten.append(f"{pad} is niet te lezen: {type(e).__name__}")
    return regels, fouten


def _getal(waarde):
    """
    Een getal uit het bestand, of een reden waarom het er geen is.

    WAAROM DIT EEN EIGEN FUNCTIE IS. Eerst stond hier `replace(".", "")`, om
    "396.000" als duizendscheiding te lezen. Een losse beoordelaar rekende na
    wat dat met een decimaalteken doet: "49.5" werd 495, "167.5" werd 1675 en
    "1.5" werd 15. Een halve vierkante meter in een oppervlaktegrens is heel
    gewoon, en de uitkomst is een grens die tien keer te ruim is, zonder enige
    melding. En float() slikt "nan", waarna elke vergelijking faalt en de regel
    overal geldt.

    Dus: een punt is alleen een duizendscheiding als er precies drie cijfers
    achter staan, de komma is het decimaalteken, en nan en inf zijn een fout.
    """
    tekst = waarde.strip().replace("€", "").replace(" ", "")
    if not tekst:
        return None, "er staat geen waarde"
    # Duizendscheiding: punt met daarachter precies drie cijfers, een of meer
    # keer, en niets anders dan cijfers ervoor.
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tekst):
        tekst = tekst.replace(".", "")
    tekst = tekst.replace(",", ".")
    try:
        getal = float(tekst)
    except ValueError:
        return None, f"'{waarde.strip()}' is geen getal"
    if getal != getal or getal in (float("inf"), float("-inf")):
        return None, f"'{waarde.strip()}' is geen bruikbaar getal"
    if getal < 0:
        return None, f"'{waarde.strip()}' is negatief"
    return getal, ""


def _straten_van(regel):
    """
    De straten waar een regel geldt. Geeft (sleutels, toestand) terug.

    De toestand is "geen" (het veld staat er niet), "lijst" (opsomming in
    regelset.txt), "leeg" (een bestand dat bestaat en na commentaar niets
    overhoudt, wat met opzet "de hele buurt" betekent), "gevuld", of "stuk".

    WAAROM DIE TOESTAND ERBIJ MOET. Eerst gaf deze functie een lege lijst terug
    bij een leeg bestand, bij een ontbrekend bestand en bij een leesfout, en
    past() las een lege lijst als "niet op straat toetsen". Een losse
    beoordelaar rekende na wat dat doet: een regel met straten die naar een
    bestand wijst dat niet bestaat, gold daarmee in de hele stad, zonder fout
    en zonder melding. Een regel die te breed geldt zet een onjuiste bewering
    in het dossier van een pand, en dat is de verkeerde kant om naar toe te
    falen. "Stuk" laat de regel nu afvallen.
    """
    waarde = (regel.get("straten") or "").strip()
    if not waarde:
        return [], "geen"
    if not waarde.lower().endswith(".txt"):
        return [_straatsleutel(s) for s in _lijst(waarde)], "lijst"
    if not os.path.exists(waarde):
        return [], "stuk"
    try:
        uit = []
        with open(waarde, encoding="utf-8") as f:
            for r in f:
                r = r.split("#")[0].strip()
                if r:
                    uit.append(_straatsleutel(r))
    except Exception:
        return [], "stuk"
    return uit, ("gevuld" if uit else "leeg")


def _straat_van(adres):
    """
    De straatnaam uit een advertentieadres.

    Splitsen op de laatste spatie ging mis op de vormen die werkelijk in de
    gegevens staan: "Bijleveldsingel 20 Bb" werd "bijleveldsingel 20", en een
    adres zonder huisnummer als "Berg en Dalseweg" werd "berg en". Splitsen op
    de eerste spatie gevolgd door een cijfer klopt voor beide.
    """
    deel = re.split(r"\s+\d", (adres or "").strip(), maxsplit=1)
    return _straatsleutel(deel[0])


def past(regel, w, buurt=""):
    """
    Geldt deze regel voor dit pand?

    Een voorwaarde die niet in de regel staat, toetst niets. Een voorwaarde die
    er wel staat en waarvan het pand het veld niet heeft, laat de regel
    afvallen: zonder oppervlakte is niet vast te stellen dat een pand boven een
    ondergrens zit, en een regel melden die misschien niet geldt is erger dan
    hem niet melden.
    """
    buurten = _lijst(regel.get("buurt"))
    if buurten and (buurt or "").lower() not in buurten:
        return False

    straten, toestand = _straten_van(regel)
    if toestand == "stuk":
        # Het bestand met straatnamen is er niet of is niet te lezen. Dan weten
        # we het gebied niet, en een regel melden waarvan we het gebied niet
        # kennen is erger dan hem niet melden.
        return False
    if straten and _straat_van(w.get("adres")) not in straten:
        return False
    # toestand "leeg" betekent met opzet "nog niet afgebakend, dus de hele
    # buurt". Dat staat zo in plintgebied.txt beschreven en het aanbod meldt
    # dat voorbehoud.

    functies = _lijst(regel.get("functie"))
    if functies:
        doelen = [str(d).lower() for d in (w.get("gebruiksdoelen") or [])]
        if not doelen or not any(d in functies for d in doelen):
            return False

    labels = _lijst(regel.get("label"))
    if labels:
        # HET LABEL KOMT IN TWEE VORMEN. In pand_dossier() is energielabel het
        # hele antwoord van EP-Online, een dict met een veld "label" en soms
        # "prive". Elders is het de tekst "F (2019)". Mijn eerste opzet deed
        # str() op allebei, waardoor een dict nooit matchte zonder dat er iets
        # faalde. Dat kwam pas uit toen ik de echte pand_dossier() erop zette.
        rauw = w.get("energielabel")
        if isinstance(rauw, dict):
            if rauw.get("prive"):
                return False       # afgeschermd label: niet vast te stellen
            rauw = rauw.get("label")
        label = str(rauw or "").strip().lower()
        # "F (2019)" en "afgeschermd" komen ook voor; alleen de letter telt.
        letter = label.split()[0] if label else ""
        if letter not in labels:
            return False

    mon = (regel.get("monument") or "").strip().lower()
    if mon in ("ja", "nee"):
        if bool(w.get("monument")) != (mon == "ja"):
            return False

    for veld, hoe in (("oppervlakte", "oppervlakte"), ("woz", "woz"),
                      ("prijs", "prijs"), ("eenheden_in_pand", "eenheden")):
        ondergrens = regel.get(f"{hoe}_min")
        bovengrens = regel.get(f"{hoe}_max")
        if ondergrens is None and bovengrens is None:
            continue
        rauw = w.get(veld)
        # eenheden_in_pand is in marktprijzen_bag.py een lijst van eenheden en
        # geen getal. Mijn eerste opzet deed float() op alles en liet de regel
        # daarom altijd afvallen zodra iemand eenheden_min gebruikte, zonder
        # dat er iets faalde. Dat bleek pas toen ik de echte pand_dossier()
        # erop zette met een verzonnen pand.
        if isinstance(rauw, (list, tuple, set, dict)):
            rauw = len(rauw)
        try:
            waarde = float(rauw)
        except (TypeError, ValueError):
            return False
        if ondergrens is not None and waarde < ondergrens:
            return False
        if bovengrens is not None and waarde > bovengrens:
            return False
    return True


def regels_voor(w, buurt="", pad=PAD):
    """De regels die op dit pand van toepassing zijn."""
    regels, _fouten = lees(pad)
    return [r for r in regels if past(r, w, buurt)]


def zelftest():
    fout = 0
    import tempfile

    bestand = os.path.join(tempfile.mkdtemp(), "regelset.txt")
    with open(bestand, "w", encoding="utf-8") as f:
        f.write("""# proefbestand
---
naam: Plintregel binnenstad
bron: https://x.invalid/1
sinds: 2026-10-08
buurt: Stadscentrum
functie: winkelfunctie, kantoorfunctie
oppervlakte_min: 167
gevolg: Wonen toevoegen op de begane grond is hier vergunningplichtig.
let op: Bestaande woningen blijven toegestaan tot transformatie.
---
naam: Alleen een label
label: F, G
gevolg: Dit label zakt onder de norm.
---
naam: Alleen een WOZ-bovengrens
woz_max: 396000
gevolg: Hieronder geldt de opkoopbescherming.
---
naam: Kapotte regel
onbekendveld: iets
gevolg: Dit hoort te worden gemeld.
---
naam: Zonder gevolg
buurt: Biezen
---
naam: Getal dat geen getal is
woz_max: driehonderd
gevolg: Ook dit hoort te worden gemeld.
""")
    regels, fouten = lees(bestand)
    # Drie regels blijven over: de plintregel, de labelregel en de WOZ-regel.
    # De regel met een onbekend veld, de regel zonder gevolg en de regel met
    # een onleesbaar getal vallen alle drie af.
    if len(regels) != 3:
        print(f"AFWIJKING: {len(regels)} regels gelezen, verwacht 3: "
              f"{[r.get('naam') for r in regels]}")
        fout += 1
    if len(fouten) != 5:
        print(f"AFWIJKING: {len(fouten)} fouten gemeld, verwacht 5: {fouten}")
        fout += 1
    if any("_kapot" in r for r in regels):
        print("AFWIJKING: de hulpsleutel _kapot hoort niet in een regel te blijven")
        fout += 1

    plint = regels[0]
    if plint.get("let_op") != "Bestaande woningen blijven toegestaan tot transformatie.":
        print(f"AFWIJKING: 'let op' met een spatie wordt niet gelezen: "
              f"{plint.get('let_op')}")
        fout += 1
    if plint.get("oppervlakte_min") != 167.0:
        print(f"AFWIJKING: oppervlakte_min gaf {plint.get('oppervlakte_min')}")
        fout += 1

    # Een winkel van 210 m2 in het Stadscentrum: raakt de plintregel.
    winkel = {"adres": "Broerstraat 14", "oppervlakte": 210,
              "gebruiksdoelen": ["winkelfunctie"]}
    gevallen = (
        (True, winkel, "Stadscentrum", "winkel van 210 m2 in het centrum"),
        (False, winkel, "Bottendaal", "zelfde winkel in een andere buurt"),
        (False, {**winkel, "oppervlakte": 90}, "Stadscentrum",
         "te kleine plint"),
        (False, {**winkel, "gebruiksdoelen": ["woonfunctie"]}, "Stadscentrum",
         "woning en geen winkel"),
        (False, {**winkel, "oppervlakte": None}, "Stadscentrum",
         "oppervlakte onbekend, dus niet vast te stellen"),
        (False, {**winkel, "gebruiksdoelen": []}, "Stadscentrum",
         "geen gebruiksdoel bekend"),
    )
    for verwacht, pand, buurt, wat in gevallen:
        uit = past(plint, pand, buurt)
        if uit != verwacht:
            print(f"AFWIJKING: {wat} gaf {uit}, verwacht {verwacht}")
            fout += 1

    # Een regel met alleen een label toetst niets anders.
    label_regel = regels[1]
    for verwacht, pand, wat in (
            (True, {"adres": "X 1", "energielabel": "F (2019)"}, "label F met jaartal"),
            (True, {"adres": "X 1", "energielabel": "g"}, "label g klein"),
            (False, {"adres": "X 1", "energielabel": "A"}, "label A"),
            (False, {"adres": "X 1", "energielabel": "afgeschermd"}, "afgeschermd"),
            (False, {"adres": "X 1"}, "geen label bekend"),
            # In pand_dossier() is energielabel het hele EP-Online-antwoord.
            (True, {"adres": "X 1", "energielabel": {"label": "F",
                                                     "registratiedatum": "2019-03-01"}},
             "label als dict uit EP-Online"),
            (False, {"adres": "X 1", "energielabel": {"label": "A"}},
             "label A als dict"),
            (False, {"adres": "X 1", "energielabel": {"prive": True, "label": "F"}},
             "afgeschermd label als dict"),
            (False, {"adres": "X 1", "energielabel": {}}, "leeg dict")):
        uit = past(label_regel, pand, "Stadscentrum")
        if uit != verwacht:
            print(f"AFWIJKING: {wat} gaf {uit}, verwacht {verwacht}")
            fout += 1

    # eenheden_in_pand is een lijst en geen getal.
    eenh_regel = {"naam": "x", "gevolg": "y", "eenheden_min": 2.0}
    for verwacht, pand, wat in (
            (True, {"adres": "X 1", "eenheden_in_pand": ["a", "b", "c"]}, "drie eenheden"),
            (False, {"adres": "X 1", "eenheden_in_pand": ["a"]}, "een eenheid"),
            (True, {"adres": "X 1", "eenheden_in_pand": 4}, "als getal gegeven"),
            (False, {"adres": "X 1"}, "onbekend")):
        uit = past(eenh_regel, pand, "Stadscentrum")
        if uit != verwacht:
            print(f"AFWIJKING: {wat} gaf {uit}, verwacht {verwacht}")
            fout += 1

    # Een bovengrens zonder ondergrens.
    woz_regel = regels[2]
    for verwacht, woz, wat in ((True, 300000, "WOZ onder de grens"),
                               (True, 396000, "WOZ precies op de grens"),
                               (False, 500000, "WOZ erboven"),
                               (False, None, "WOZ onbekend")):
        uit = past(woz_regel, {"adres": "X 1", "woz": woz}, "Stadscentrum")
        if uit != verwacht:
            print(f"AFWIJKING: {wat} gaf {uit}, verwacht {verwacht}")
            fout += 1

    # Een straatlijst die naar een leeg bestand wijst, toetst niet op straat.
    leeg = os.path.join(os.path.dirname(bestand), "leeg.txt")
    open(leeg, "w").write("# alleen commentaar\n")
    met_lijst = dict(plint)
    met_lijst["straten"] = leeg
    if not past(met_lijst, winkel, "Stadscentrum"):
        print("AFWIJKING: een lege straatlijst hoort niet op straat te toetsen")
        fout += 1
    with open(leeg, "w", encoding="utf-8") as f:
        f.write("Burchtstraat\n")
    if past(met_lijst, winkel, "Stadscentrum"):
        print("AFWIJKING: Broerstraat hoort buiten een lijst met Burchtstraat "
              "te vallen")
        fout += 1
    with open(leeg, "w", encoding="utf-8") as f:
        f.write("Broerstraat\n")
    if not past(met_lijst, winkel, "Stadscentrum"):
        print("AFWIJKING: Broerstraat hoort binnen een lijst met Broerstraat "
              "te vallen")
        fout += 1

    # DE GEVALLEN DIE EEN LOSSE BEOORDELAAR VOND. Elk hiervan liet een regel
    # breder gelden dan bedoeld, zonder fout en zonder melding.
    hoek = os.path.dirname(bestand)
    def proef(inhoud):
        p = os.path.join(hoek, "p.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(inhoud)
        return lees(p)

    for wat, inhoud in (
            ("leeg veld", "---\nnaam: x\ngevolg: y\nbuurt:\n"),
            ("dubbel veld", "---\nnaam: x\ngevolg: y\nbuurt: A\nbuurt: B\n"),
            ("monument fout", "---\nnaam: x\ngevolg: y\nmonument: true\n"),
            ("nan", "---\nnaam: x\ngevolg: y\nwoz_max: nan\n"),
            ("negatief", "---\nnaam: x\ngevolg: y\nwoz_max: -5\n")):
        r, f3 = proef(inhoud)
        if r or not f3:
            print(f"AFWIJKING: {wat} gaf {len(r)} regels en {len(f3)} fouten, "
                  f"verwacht 0 regels en minstens 1 fout")
            fout += 1

    # Een punt als decimaalteken blijft een decimaalteken.
    r, _ = proef("---\nnaam: x\ngevolg: y\noppervlakte_max: 49.5\n")
    if not r or r[0].get("oppervlakte_max") != 49.5:
        print(f"AFWIJKING: 49.5 werd {r[0].get('oppervlakte_max') if r else None}")
        fout += 1
    r, _ = proef("---\nnaam: x\ngevolg: y\nwoz_max: 396.000\n")
    if not r or r[0].get("woz_max") != 396000.0:
        print(f"AFWIJKING: 396.000 werd {r[0].get('woz_max') if r else None}")
        fout += 1

    # Een hekje midden in een waarde kapt niets meer af.
    r, _ = proef("---\nnaam: x\nbron: https://a.invalid/b.html#d1e123\n"
                 "gevolg: geldt voor pand #12 en hoger\n")
    if not r or not r[0]["bron"].endswith("#d1e123"):
        print(f"AFWIJKING: het anker uit de URL is weg: "
              f"{r[0]['bron'] if r else None}")
        fout += 1
    if not r or r[0]["gevolg"] != "geldt voor pand #12 en hoger":
        print(f"AFWIJKING: het gevolg is afgekapt: "
              f"{r[0]['gevolg'] if r else None}")
        fout += 1

    # Een straatlijst die naar een ontbrekend bestand wijst laat de regel
    # afvallen in plaats van hem in de hele stad te laten gelden.
    stuk = dict(plint)
    stuk["straten"] = os.path.join(hoek, "bestaatniet.txt")
    if past(stuk, winkel, "Stadscentrum"):
        print("AFWIJKING: een ontbrekende straatlijst hoort de regel te laten "
              "afvallen en niet overal te laten gelden")
        fout += 1

    # Straatnamen in twee schrijfwijzen en adresvormen die echt voorkomen.
    for adres, straat, verwacht, wat in (
            ("St. Annastraat 7", "Sint Annastraat", True, "St. tegen Sint"),
            ("Sint Annastraat 7", "St. Annastraat", True, "Sint tegen St."),
            ("Bijleveldsingel 20 Bb", "Bijleveldsingel", True,
             "huisnummer met losse toevoeging"),
            ("van Welderenstraat 121 B", "van Welderenstraat", True,
             "straat met voorvoegsel"),
            ("Berg en Dalseweg", "Berg en Dalseweg", True,
             "meerdelige naam zonder huisnummer"),
            ("Broerstraat 14", "Burchtstraat", False, "andere straat")):
        regel_s = {"naam": "x", "gevolg": "y", "straten": straat}
        uit = past(regel_s, {"adres": adres}, "Stadscentrum")
        if uit != verwacht:
            print(f"AFWIJKING: {wat} ({adres!r} tegen {straat!r}) gaf {uit}, "
                  f"verwacht {verwacht}")
            fout += 1

    # Geen bestand betekent geen regels en geen fouten.
    r, f2 = lees(os.path.join(os.path.dirname(bestand), "bestaatniet.txt"))
    if r or f2:
        print(f"AFWIJKING: een ontbrekend bestand gaf {len(r)} regels en "
              f"{len(f2)} fouten")
        fout += 1

    print(f"zelftest: {fout} afwijkend")
    return fout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zelftest", action="store_true")
    p.add_argument("--pad", default=PAD)
    a = p.parse_args()
    if a.zelftest:
        return 1 if zelftest() else 0
    regels, fouten = lees(a.pad)
    print(f"{len(regels)} {'regel' if len(regels) == 1 else 'regels'} in {a.pad}")
    for r in regels:
        voorwaarden = [f"{k}={v}" for k, v in sorted(r.items())
                       if k not in ("naam", "gevolg", "let_op", "bron", "sinds")]
        print(f"\n  {r['naam']}")
        if r.get("sinds"):
            print(f"    sinds {r['sinds']}")
        print(f"    geldt bij: {', '.join(voorwaarden) or 'elk pand'}")
        print(f"    gevolg: {r['gevolg'][:90]}")
        if r.get("let_op"):
            print(f"    let op: {r['let_op'][:90]}")
    if fouten:
        print(f"\n{len(fouten)} fouten in het bestand:")
        for f2 in fouten:
            print(f"  {f2}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
