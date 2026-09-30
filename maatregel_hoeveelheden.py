#!/usr/bin/env python3
"""
Van vierkante meters bouwdeel naar hoeveelheden materiaal.

Waarom dit apart staat van de prijzen: de hoeveelheden volgen uit de opbouw en
zijn te berekenen. De prijzen niet; daarvoor bestaat geen open bron, en een
geschatte prijs per vierkante meter is precies wat we overal uit dit systeem
halen. Vul de prijzen daarom zelf in materiaalprijzen.txt, met je eigen
inkoopprijzen. Dan is de uitkomst een berekening in plaats van een aanname.

De opbouw voor na-isolatie aan de binnenzijde, zoals Mark hem beschrijft:
oude afwerking eraf, houten frame met stijlen hart op hart 60 cm van vloer tot
plafond, isolatie ertussen, OSB erover, gipsplaat daaroverheen, stucwerk als
afwerking.

Let op de koudebrug: de houten stijlen nemen ongeveer een tiende van het
oppervlak in en isoleren minder dan de isolatie ertussen. De Rc van de
constructie ligt daardoor lager dan de Rd van het materiaal. Voor de subsidie
telt de Rd van het isolatiemateriaal, voor het energielabel de Rc van het
geheel; die twee zijn niet hetzelfde.
"""

# Stijlen hart op hart. Bij 60 cm past standaard isolatiemateriaal er klem
# tussen, wat de reden is dat die maat wordt aangehouden.
HOH = 0.60
# Aandeel van het geveloppervlak dat uit hout bestaat bij die maatvoering.
# 38 mm stijl per 600 mm is ruim 6%; met regels boven en onder en rond
# openingen komt dat op ongeveer een tiende.
HOUTAANDEEL = 0.10
# Snijverlies op plaatmateriaal. Platen zijn 2440 bij 1220, dus rond openingen
# en bij afwijkende maten blijft er materiaal over.
SNIJVERLIES_PLAAT = 0.10
SNIJVERLIES_ISOLATIE = 0.05


def frame_hoeveelheden(m2_muur, hoogte=2.6):
    """
    Wat er aan materiaal nodig is voor een binnenwand van dit oppervlak.

    Geeft hoeveelheden met hun eenheid terug, zodat er alleen nog een prijs per
    eenheid bij hoeft. Niets hierin is een prijs of een schatting daarvan.
    """
    if not m2_muur or m2_muur <= 0:
        return None
    breedte = m2_muur / hoogte

    # Verticale stijlen: om de 60 cm, plus een aan het eind van elk vlak.
    stijlen = breedte / HOH + 1
    meters_stijl = stijlen * hoogte
    # Horizontale regels boven en onder.
    meters_regel = breedte * 2
    return {
        "muur_m2": round(m2_muur, 1),
        "hoogte_m": hoogte,
        "stijlen_stuks": round(stijlen, 1),
        "hout_m1": round(meters_stijl + meters_regel, 1),
        "isolatie_m2": round(m2_muur * (1 - HOUTAANDEEL)
                             * (1 + SNIJVERLIES_ISOLATIE), 1),
        "osb_m2": round(m2_muur * (1 + SNIJVERLIES_PLAAT), 1),
        "gipsplaat_m2": round(m2_muur * (1 + SNIJVERLIES_PLAAT), 1),
        "stucwerk_m2": round(m2_muur, 1),
        "sloop_m2": round(m2_muur, 1),
        "houtaandeel": HOUTAANDEEL,
        "let_op": ("de houten stijlen nemen ongeveer "
                   f"{int(HOUTAANDEEL * 100)}% van het vlak in en isoleren "
                   "minder; de Rc van de constructie ligt daardoor lager dan "
                   "de Rd van het isolatiemateriaal"),
    }


# Btw-tarieven. Voor een verhuurder van woningen is de btw geen verrekenbare
# post maar gewoon kosten: woningverhuur is vrijgesteld, dus er valt niets terug
# te vragen. Alleen bij een utiliteitspand kan dat wel. Daarom rekent dit
# script standaard met bedragen inclusief btw.
BTW_MATERIAAL = 0.21
# Arbeid aan een woning ouder dan twee jaar valt onder het verlaagde tarief.
BTW_ARBEID_WONING = 0.09
ARBEIDSPOSTEN = ("stucwerk", "stucwerk_plafond", "sloop", "arbeid")


def btw_tarief(post):
    """Welk tarief er bij deze post hoort."""
    return (BTW_ARBEID_WONING if post.lower() in ARBEIDSPOSTEN
            else BTW_MATERIAAL)


def indexeer(bedrag, peildatum):
    """
    Een prijs van toen omrekenen naar nu, met de CBS-bouwkostenindex.

    Bonnen van een half jaar oud zijn geen prijs van vandaag. De index die we
    toch al ophalen zegt hoeveel bouwkosten sindsdien zijn veranderd, dus dat
    hoeft niet te worden geschat. Zonder index of zonder peildatum blijft het
    bedrag staan zoals het is, met de melding dat er niet geindexeerd is.
    """
    if not bedrag or not peildatum:
        return {"bedrag": bedrag, "factor": 1.0, "geindexeerd": False,
                "reden": "geen peildatum bij deze prijs"}
    try:
        from bouwkosten_index import indexfactor
        info = indexfactor(vanaf=peildatum[:7])
    except Exception as e:
        return {"bedrag": bedrag, "factor": 1.0, "geindexeerd": False,
                "reden": f"index niet beschikbaar: {str(e)[:60]}"}
    if not info.get("geindexeerd"):
        return {"bedrag": bedrag, "factor": 1.0, "geindexeerd": False,
                "reden": "geen indexcijfer voor die maand"}
    factor = info["factor"]
    return {"bedrag": round(bedrag * factor, 2), "factor": factor,
            "geindexeerd": True, "vanaf": peildatum,
            "reden": f"CBS-bouwkostenindex, {factor:.3f} sinds {peildatum}"}


def lees_prijzen(pad="materiaalprijzen.txt"):
    """
    Eigen prijzen per eenheid. Formaat per regel: post | prijs | eenheid.

    Zonder dit bestand rekent er niets; dat is met opzet. Een prijs die we niet
    kennen, verzinnen we niet.
    """
    uit = {}
    try:
        with open(pad, encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip()
                if not regel or regel.startswith("#") or "|" not in regel:
                    continue
                delen = [d.strip() for d in regel.split("|")]
                if len(delen) < 2:
                    continue
                try:
                    uit[delen[0].lower()] = {
                        "prijs": float(delen[1].replace(",", ".")),
                        "eenheid": delen[2] if len(delen) > 2 else "",
                        "peildatum": delen[3] if len(delen) > 3 else ""}
                except ValueError:
                    continue
    except Exception:
        pass
    return uit


def kosten(hoeveelheden, prijzen):
    """
    De materiaalkosten, als de prijzen bekend zijn.

    Ontbreekt een post, dan staat die apart in de uitkomst. Beter een zichtbaar
    gat dan een totaal dat volledig lijkt.
    """
    if not hoeveelheden:
        return None
    koppeling = {"hout_m1": "hout", "isolatie_m2": "isolatie",
                 "osb_m2": "osb", "gipsplaat_m2": "gipsplaat",
                 "stucwerk_m2": "stucwerk", "sloop_m2": "sloop"}
    regels, ontbreekt, totaal = [], [], 0.0
    for veld, post in koppeling.items():
        aantal = hoeveelheden.get(veld)
        prijs = prijzen.get(post)
        if not aantal:
            continue
        if not prijs:
            ontbreekt.append(post)
            continue
        # De prijs eerst naar vandaag brengen; een bon van een half jaar oud
        # is geen prijs van nu.
        ix = indexeer(prijs["prijs"], prijs.get("peildatum"))
        tarief = btw_tarief(post)
        prijs_incl = ix["bedrag"] * (1 + tarief)
        bedrag = aantal * prijs_incl
        totaal += bedrag
        regels.append({"post": post, "aantal": aantal,
                       "prijs": prijs["prijs"], "prijs_nu": ix["bedrag"],
                       "btw": tarief, "prijs_incl": round(prijs_incl, 2),
                       "geindexeerd": ix["geindexeerd"],
                       "index": ix.get("reden", ""),
                       "bedrag": round(bedrag, 2)})
    return {"regels": regels, "totaal": round(totaal, 2),
            "inclusief_btw": True,
            "ontbrekende_posten": ontbreekt,
            "volledig": not ontbreekt,
            "per_m2": (round(totaal / hoeveelheden["muur_m2"], 2)
                       if hoeveelheden.get("muur_m2") else None)}
