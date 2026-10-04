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

GEDEELD = "_panden"


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


def compact(geschiedenis):
    """
    De gedeelde velden een keer opslaan in plaats van per adres.

    Alleen velden die bij het gebouw horen en niet bij het adres:
    bag_eenheden, labels en de datum waarop het pand is nagekeken. De
    gebeurtenissen blijven per adres staan, want een verkoop of een vergunning
    hoort bij een adres en niet bij het hele gebouw.

    Panden zonder pand-id blijven staan zoals ze zijn; daar valt niets te
    delen.
    """
    gedeeld, uit = {}, {}
    velden = ("bag_eenheden", "labels", "bag_gezien")
    for sleutel, pand in geschiedenis.items():
        if sleutel == GEDEELD or not isinstance(pand, dict):
            continue
        pid = pand.get("pand_id")
        kopie = dict(pand)
        if pid:
            doel = gedeeld.setdefault(pid, {})
            for veld in velden:
                waarde = kopie.pop(veld, None)
                if waarde and not doel.get(veld):
                    doel[veld] = waarde
                elif waarde and veld == "bag_gezien":
                    # De laatste datum winnen, anders lijkt een pand ouder dan
                    # het is.
                    doel[veld] = max(doel[veld], waarde)
        uit[sleutel] = kopie
    if gedeeld:
        uit[GEDEELD] = gedeeld
    return uit


def tel_besparing(geschiedenis):
    """Hoeveel regels het delen scheelt, voor het gezondheidsrapport."""
    per_adres = som = 0
    gezien = set()
    for sleutel, pand in geschiedenis.items():
        if sleutel == GEDEELD or not isinstance(pand, dict):
            continue
        n = len(pand.get("bag_eenheden") or []) + len(pand.get("labels") or {})
        per_adres += n
        pid = pand.get("pand_id")
        if pid and pid in gezien:
            continue
        if pid:
            gezien.add(pid)
        som += n
    return {"per_adres": per_adres, "gedeeld": som,
            "bespaard": per_adres - som}
