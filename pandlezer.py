#!/usr/bin/env python3
"""
De pandgeschiedenis inlezen, in welke vorm hij ook op schijf staat.

Het probleem dat dit oplost: een BAG-pand kan meerdere adressen hebben die wij
apart volgen. Aubadestraat 12 en 16 zijn hetzelfde pand met 24 woningen, en in
de oude vorm stond die lijst van 24 eenheden en 24 labels bij allebei de
adressen. Bij Achter de Wiemelpoort zelfs drie keer. Dat maakt het bestand
groot, de runs traag en het dossier onleesbaar.

De nieuwe vorm bewaart dat een keer, onder "_panden", met het pand-id als
sleutel. Elk adres houdt zijn eigen gebeurtenissen en een verwijzing.

Deze lezer vouwt het weer uit, zodat elk adres in het geheugen gewoon zijn
bag_eenheden en labels heeft. Daardoor hoeft geen enkele lezer van dit bestand
te veranderen: marktprijzen, het aanbodprofiel, de 3D BAG en het
gezondheidsrapport blijven werken zoals ze deden. Een bestand in de oude vorm
wordt net zo goed gelezen, want dan staat alles al per adres.
"""
import json
import sys

GEDEELD = "_panden"

# De velden die bij het GEBOUW horen en niet bij het adres. Ze staan hier als
# constante en niet als lokale rij in compact(), want pandsleutel.samenvoeg()
# moet dezelfde rij kennen: die mag deze velden juist niet tussen twee
# adresrecords verplaatsen. Twee kopieen van deze rij is precies het soort
# duplicatie dat deze module bestaat om te voorkomen.
GEDEELDE_VELDEN = ("bag_eenheden", "bag_woningen", "labels", "bag_gezien")


def laad(pad="pandgeschiedenis.json"):
    """
    Het bestand als een dict van adres naar pandgegevens.

    Gedeelde velden worden per adres ingevuld. De sleutel _panden zelf komt
    niet in het resultaat terug, zodat een lus over de panden geen vreemde
    regel tegenkomt.
    """
    try:
        with open(pad, encoding="utf-8") as f:
            rauw = json.load(f) or {}
    except Exception:
        return {}
    gedeeld = rauw.pop(GEDEELD, None) or {}
    if not gedeeld:
        return rauw
    for pand in rauw.values():
        if not isinstance(pand, dict):
            continue
        bron = gedeeld.get(pand.get("pand_id") or "")
        if not bron:
            continue
        for veld, waarde in bron.items():
            # Wat al bij het adres staat wint: dat is specifieker dan wat bij
            # het pand hoort, en bij een halve migratie mag niets verdwijnen.
            if veld not in pand or not pand.get(veld):
                pand[veld] = waarde
    return rauw


def compact(geschiedenis, verslag=None):
    """
    De gedeelde velden een keer opslaan in plaats van per adres.

    Alleen velden die bij het gebouw horen en niet bij het adres:
    bag_eenheden, bag_woningen, labels en de datum waarop het pand is
    nagekeken. De gebeurtenissen blijven per adres staan, want een verkoop of
    een vergunning hoort bij een adres en niet bij het hele gebouw.

    BAG_WONINGEN HOORT IN DEZE RIJ. Dat veld is op 11 oktober toegevoegd en
    stond er eerst niet bij, met als gevolg dat het per adres werd bewaard in
    plaats van een keer per pand. Dat is precies wat deze module bestaat om te
    voorkomen: Aubadestraat 12 en 16 zijn hetzelfde pand met 24 woningen, en
    dan staat die lijst van 24 twee keer in het bestand. Over alle panden gaat
    het om 1.777 adressen tegen 1.263 panden.

    EEN WOORDENBOEK WORDT SAMENGEVOEGD EN NIET OVERSCHREVEN. Hier stond "de
    eerste die iets heeft, wint". Voor bag_gezien is dat opgelost met max()
    en voor een lijst is het verdedigbaar, maar labels is een woordenboek van
    adres naar letter, en dan gooit de eerste die wint de labels van de
    andere adressen weg. Gemeten op 12 oktober met twee records van hetzelfde
    pand, een met {A 1: D} en een met {A 3: B, A 5: C}: van de drie labels
    overleefde er een.

    Vandaag staat geen enkel pand in die toestand, want pandgeschiedenis
    schrijft hetzelfde blok naar alle adressen van een pand. Het pad is wel
    te bereiken: zodra een ronde een label vindt op het ene adres van een
    pand en niet op het andere, hangt het van de volgorde in het bestand af
    of dat label het opslaan overleeft. Dat is precies de soort fout die
    deze week vijf keer is langsgekomen, dus hij hoort dicht voordat hij zich
    voordoet en niet erna.

    Panden zonder pand-id blijven staan zoals ze zijn; daar valt niets te
    delen.

    verslag is een dict die, als hij wordt meegegeven, wordt gevuld met wat
    er bij het samenvoegen is gebeurd. Een botsing op dezelfde sleutel met
    een andere waarde is iets om te zien en geen reden om te stoppen: zonder
    datum bij een label is niet te zeggen welke de nieuwste is, dus de eerste
    blijft staan en de botsing wordt geteld.
    """
    gedeeld, uit = {}, {}
    velden = GEDEELDE_VELDEN
    samengevoegd = botsingen = 0
    for sleutel, pand in geschiedenis.items():
        if sleutel == GEDEELD or not isinstance(pand, dict):
            continue
        pid = pand.get("pand_id")
        kopie = dict(pand)
        if pid:
            doel = gedeeld.setdefault(pid, {})
            for veld in velden:
                waarde = kopie.pop(veld, None)
                if not waarde:
                    continue
                staat = doel.get(veld)
                if veld == "bag_gezien":
                    # De laatste datum winnen, anders lijkt een pand ouder dan
                    # het is.
                    doel[veld] = max(staat, waarde) if staat else waarde
                elif isinstance(waarde, dict) and isinstance(staat, dict):
                    for k, v in waarde.items():
                        if k not in staat:
                            staat[k] = v
                            samengevoegd += 1
                        elif staat[k] != v:
                            botsingen += 1
                elif staat is None or not staat:
                    # EEN KOPIE VAN EEN WOORDENBOEK EN NIET DE VERWIJZING.
                    # Anders voegt de lus hierboven straks sleutels toe aan
                    # het blok van het EERSTE adresrecord, en dan verandert
                    # compact() de gegevens die hij alleen zou opslaan.
                    doel[veld] = dict(waarde) if isinstance(waarde, dict) \
                        else waarde
        uit[sleutel] = kopie
    if gedeeld:
        uit[GEDEELD] = gedeeld
    if verslag is not None:
        verslag["sleutels_samengevoegd"] = samengevoegd
        verslag["botsende_sleutels"] = botsingen
    return uit


def tel_besparing(geschiedenis):
    """Hoeveel regels het delen scheelt, voor het gezondheidsrapport."""
    per_adres = som = 0
    gezien = set()
    for sleutel, pand in geschiedenis.items():
        if sleutel == GEDEELD or not isinstance(pand, dict):
            continue
        n = (len(pand.get("bag_eenheden") or [])
             + len(pand.get("bag_woningen") or [])
             + len(pand.get("labels") or {}))
        per_adres += n
        pid = pand.get("pand_id")
        if pid and pid in gezien:
            continue
        if pid:
            gezien.add(pid)
        som += n
    return {"per_adres": per_adres, "gedeeld": som,
            "bespaard": per_adres - som}


def proef():
    """
    Het delen en uitvouwen nameten, zonder één bestand te hoeven hebben.

    WAAROM DEZE MODULE EEN PROEF KRIJGT. Hij had er geen, en hij is het
    smalste punt van het hele bestand: elk pandgegeven gaat door compact()
    naar schijf en door laad() terug. Een fout hier is een fout in alles wat
    de pandgeschiedenis leest, en hij zou nergens anders rood worden.
    """
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # HEEN EN TERUG. Twee adressen van hetzelfde pand, en na het uitvouwen
    # hoort elk adres het gedeelde veld gewoon te hebben.
    heen = {
        "a1": {"adres": "A 1", "pand_id": "P", "bag_woningen": ["x", "y"],
               "bag_gezien": "2026-10-01", "labels": {"A 1": "D"}},
        "a3": {"adres": "A 3", "pand_id": "P", "bag_woningen": ["x", "y"],
               "bag_gezien": "2026-10-09", "labels": {"A 1": "D"}},
    }
    kort = compact(heen)
    check("het gedeelde veld staat een keer", "bag_woningen" in kort["a1"],
          False)
    check("en wel onder het pand",
          kort["_panden"]["P"]["bag_woningen"], ["x", "y"])
    check("de laatste datum wint", kort["_panden"]["P"]["bag_gezien"],
          "2026-10-09")

    # TWEE VERSCHILLENDE WOORDENBOEKEN VAN HETZELFDE PAND. Dit is de fout
    # die op 12 oktober is gemeten: met "de eerste die iets heeft, wint"
    # overleefde een van de drie labels, en welke hing af van de volgorde in
    # het bestand.
    twee = {
        "a1": {"adres": "A 1", "pand_id": "P", "labels": {"A 1": "D"}},
        "a3": {"adres": "A 3", "pand_id": "P",
               "labels": {"A 3": "B", "A 5": "C"}},
    }
    verslag = {}
    kort2 = compact(twee, verslag)
    check("alle drie de labels overleven",
          kort2["_panden"]["P"]["labels"],
          {"A 1": "D", "A 3": "B", "A 5": "C"})
    check("het samenvoegen wordt geteld", verslag["sleutels_samengevoegd"], 2)
    check("en er is geen botsing", verslag["botsende_sleutels"], 0)
    # EN COMPACT VERANDERT ZIJN EIGEN INVOER NIET. Zonder de kopie in
    # compact() zouden de sleutels van a3 in het blok van a1 belanden, en dan
    # wijzigt een functie die alleen zou opslaan de gegevens zelf.
    check("de invoer blijft zoals hij was", twee["a1"]["labels"], {"A 1": "D"})

    # EEN BOTSING OP DEZELFDE SLEUTEL IS IETS OM TE ZIEN EN GEEN REDEN OM TE
    # STOPPEN: zonder datum bij een label is niet te zeggen welke de nieuwste
    # is, dus de eerste blijft staan en het wordt geteld.
    bots = {
        "a1": {"adres": "A 1", "pand_id": "P", "labels": {"A 1": "D"}},
        "a3": {"adres": "A 3", "pand_id": "P", "labels": {"A 1": "B"}},
    }
    verslag2 = {}
    kort3 = compact(bots, verslag2)
    check("bij een botsing blijft de eerste staan",
          kort3["_panden"]["P"]["labels"], {"A 1": "D"})
    check("en de botsing wordt geteld", verslag2["botsende_sleutels"], 1)

    # HET UITVOUWEN. Wat bij het adres staat wint, want dat is specifieker,
    # en bij een halve migratie mag niets verdwijnen.
    import json as _json
    import os as _os
    import tempfile
    with tempfile.TemporaryDirectory() as map_:
        pad = _os.path.join(map_, "p.json")
        with open(pad, "w", encoding="utf-8") as f:
            _json.dump(kort, f)
        terug = laad(pad)
        check("na het uitvouwen heeft elk adres het veld",
              [terug["a1"].get("bag_woningen"), terug["a3"].get("bag_woningen")],
              [["x", "y"], ["x", "y"]])
        check("_panden komt niet als pand terug", "_panden" in terug, False)

        # EEN BESTAND IN DE OUDE VORM, zonder _panden, hoort gewoon gelezen
        # te worden. Anders breekt een terugrol.
        oud = _os.path.join(map_, "oud.json")
        with open(oud, "w", encoding="utf-8") as f:
            _json.dump({"a1": {"adres": "A 1", "labels": {"A 1": "D"}}}, f)
        check("de oude vorm wordt gelezen",
              laad(oud)["a1"]["labels"], {"A 1": "D"})
        check("een bestand dat niet bestaat geeft niets",
              laad(_os.path.join(map_, "weg.json")), {})

    # Een pand zonder pand-id valt niets te delen.
    los = {"z": {"adres": "Z 1", "labels": {"Z 1": "A"}}}
    check("zonder pand-id blijft het bij het adres",
          compact(los)["z"].get("labels"), {"Z 1": "A"})
    check("en er komt geen leeg _panden bij", "_panden" in compact(los), False)

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten. Gedekt: het delen heen en terug, de "
          f"laatste datum die wint, twee verschillende woordenboeken van "
          f"hetzelfde pand die worden samengevoegd in plaats van "
          f"overschreven, de botsing die wordt geteld, dat compact zijn eigen "
          f"invoer niet verandert, de oude bestandsvorm en een pand zonder "
          f"pand-id.", file=sys.stderr)
    return 1 if fouten else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proef", action="store_true",
                    help="Het delen en uitvouwen nameten.")
    a = ap.parse_args()
    sys.exit(proef() if a.proef else 0)
