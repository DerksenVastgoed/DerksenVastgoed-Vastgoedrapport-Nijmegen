#!/usr/bin/env python3
"""
Het energielabel uit EP-Online, uit één plek.

WAT HIER MISGING. De aanroep van EP-Online stond drie keer in de repo, en de
derde kopie was stuk. marktprijzen_bag.py en bekendmakingen_nijmegen.py
vragen eerst op verblijfsobject-id en dan pas op postcode, en lezen het label
uit zes mogelijke veldnamen. voorraad_bag.py vroeg alleen op postcode en las
alleen het veld "labelLetter".

Wat dat kostte, gemeten op 10 oktober: van 818 opgevraagde adressen kwamen er
803 terug als "geen label bekend" en 15 als HTTP 400. Nul labels gevonden,
terwijl de pandgeschiedenis er met de werkende aanroep 1.384 kent. Die 803
zijn geen antwoord maar een veldnaam die niet bestond: de API gaf HTTP 200,
de lus vond geen "labelLetter" en gaf een leeg antwoord terug, en de
aanroeper schreef dat op als "dit adres heeft geen label". Een aanname over
een veldnaam die zich voordoet als een feit over de woningvoorraad.

Dat is dezelfde fout als met de pandsleutel, en dezelfde oplossing: één
implementatie, en een proef die hem vasthoudt.

WAT DEZE PROEF WEL EN NIET AANTOONT. De vormen hieronder zijn afgeleid van de
veldnamen die de twee werkende implementaties aankunnen, en niet van een
vastgelegd antwoord van EP-Online; dat staat nergens in de repo. De proef
toetst dus of het lezen klopt, en niet of de API er werkelijk zo uitziet. Zou
EP-Online een zevende veldnaam gebruiken, dan vangt deze proef dat niet. Wat
hij wel vangt: dat een lezer met één veldnaam langs de andere vijf heen
loopt, en dat een privélabel geen "niet bekend" wordt.
"""
import argparse
import os
import re
import sys

BASIS = "https://public.ep-online.nl/api/v5/PandEnergielabel"

# De veldnamen waaronder het label kan staan. _veld() vergelijkt zonder te
# letten op hoofdletters en liggende streepjes, dus dit zijn vormen en geen
# exacte sleutels.
VELD_LABEL = ("Pand_energieklasse", "energieklasse", "labelLetter",
              "Pand_labelletter", "energielabel", "labelletter")
VELD_PRIVE = ("Pand_energielabel_is_prive", "isPrive", "prive")
VELD_DATUM = ("Pand_registratiedatum", "registratiedatum")
VELD_GELDIG = ("Meting_geldig_tot", "geldigTot", "metingGeldigTot")
VELD_KLASSE = ("Pand_gebouwklasse", "gebouwklasse")


def _sleutel():
    return os.environ.get("EP_API_KEY") or ""


def _koppen():
    return {"Authorization": _sleutel(), "Accept": "application/json"}


def eerste(data):
    """
    Het eerste record uit een antwoord, in welke vorm het ook komt.

    De API geeft soms een lijst, soms een enkel object, en soms een object met
    de lijst eronder. Alle drie zijn vormen die de werkende implementaties
    aankunnen, dus alle drie horen hier.
    """
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        for naam in ("results", "data", "items"):
            binnen = data.get(naam)
            if isinstance(binnen, list) and binnen:
                return binnen[0]
        return data
    return None


def veld(rec, namen):
    """
    De eerste gevulde waarde onder een van deze veldnamen.

    Vergelijkt zonder hoofdletters en zonder liggende streepjes, want de API
    schrijft hetzelfde begrip als Pand_energieklasse en als energieklasse.
    """
    if not isinstance(rec, dict):
        return None
    for naam in namen:
        doel = naam.lower().replace("_", "")
        for k, v in rec.items():
            if str(k).lower().replace("_", "") == doel and v not in (None, ""):
                return v
    return None


def splits_toevoeging(deel):
    """
    Uit "29A-24" komt ("29", "A", "24"), uit "20" komt ("20", "", "").

    Dit stond in drie varianten in de repo, waarvan er een de toevoeging liet
    vallen omdat zijn functie er geen parameter voor had. Bij Bachstraat
    29A-24 gaf dat HTTP 400, vijftien keer per ronde.
    """
    m = re.match(r"^\s*(\d+)\s*(.*)$", str(deel or ""))
    if not m:
        return ("", "", "")
    nr, rest = m.group(1), (m.group(2) or "").strip()
    if not rest:
        return (nr, "", "")
    if "-" in rest:
        letter, _, toev = rest.partition("-")
        return (nr, letter.strip(), toev.strip())
    # Een enkele letter is een huisletter; meer tekens zijn een toevoeging.
    rest = rest.lstrip("- ")
    if len(rest) == 1 and rest.isalpha():
        return (nr, rest, "")
    return (nr, "", rest)


def uit_adres(adres):
    """(huisnummer, huisletter, toevoeging) uit een heel adres."""
    deel = str(adres or "").split()
    if len(deel) < 2:
        return ("", "", "")
    return splits_toevoeging(deel[-1])


def lees(rec):
    """
    Uit een EP-Online-record: het label, of None als er niets in staat.

    Een privélabel is een antwoord en geen leegte: er IS een label, het is
    alleen niet openbaar. Wie dat als "niet bekend" opschrijft, vraagt het
    volgend jaar opnieuw en krijgt hetzelfde.
    """
    if not isinstance(rec, dict) or not rec:
        return None
    prive = veld(rec, VELD_PRIVE)
    if str(prive).lower() in ("1", "true", "ja"):
        return {"label": None, "prive": True, "registratiedatum": "",
                "geldig_tot": "", "gebouwklasse": ""}
    letter = veld(rec, VELD_LABEL)
    if not letter:
        return None
    return {
        "label": str(letter).strip(),
        "prive": False,
        "registratiedatum": str(veld(rec, VELD_DATUM) or "")[:10],
        "geldig_tot": str(veld(rec, VELD_GELDIG) or "")[:10],
        "gebouwklasse": veld(rec, VELD_KLASSE) or "",
    }


# Wat een foutcode betekent. definitief: dit adres gaat het nooit worden, dus
# opschrijven dat het gevraagd is en niet elke ronde opnieuw proberen.
# stoppen: iets is mis met ons, niet met het adres, dus de ronde afbreken.
DEFINITIEF = (400, 404)
STOPPEN = (401, 403, 429)


def energielabel(vbo_id=None, postcode="", huisnr="", letter="", toev="",
                 haler=None):
    """
    Het label van één adres. Geeft (uitkomst, fout, definitief).

    uitkomst is een dict met het label, of {} als er geen label bekend is, of
    None als er niets te zeggen valt. fout is leeg bij een antwoord.
    definitief zegt of dit adres opnieuw vragen zin heeft.

    Eerst op verblijfsobject-id, want dat is exact en dat is de route die
    werkt. Daarna op postcode plus huisnummer. haler is er voor de proef:
    daarmee gaat er geen enkele aanroep de deur uit.
    """
    if haler is None:
        if not _sleutel():
            return (None, "geen EP_API_KEY", False)
        import requests

        def haler(url, params):
            r = requests.get(url, headers=_koppen(), params=params, timeout=20)
            return (r.status_code, (lambda: r.json()))

    pogingen = []
    if vbo_id:
        pogingen.append((f"{BASIS}/AdresseerbaarObject/{vbo_id}", None))
    if postcode and huisnr:
        params = {"postcode": str(postcode).replace(" ", ""),
                  "huisnummer": str(huisnr)}
        if letter:
            params["huisletter"] = letter
        if toev:
            params["huisnummertoevoeging"] = toev
        pogingen.append((f"{BASIS}/Adres", params))
    if not pogingen:
        return (None, "geen vbo-id en geen postcode met huisnummer", True)

    laatste, def_alles = "", True
    for url, params in pogingen:
        try:
            code, json_van = haler(url, params)
        except Exception as e:
            laatste, def_alles = f"netwerk: {str(e)[:60]}", False
            continue
        if code in STOPPEN:
            return (None, f"HTTP {code}", False)
        if code in DEFINITIEF:
            laatste = f"HTTP {code}"
            continue
        if code != 200:
            laatste, def_alles = f"HTTP {code}", False
            continue
        try:
            rec = eerste(json_van())
        except Exception as e:
            laatste, def_alles = f"antwoord onleesbaar: {str(e)[:50]}", False
            continue
        uit = lees(rec)
        if uit is not None:
            return (uit, "", True)
        # HTTP 200 zonder label is een echt antwoord: dit adres heeft er geen.
        return ({}, "", True)
    return (None, laatste or "geen antwoord", def_alles)


def proef():
    """De vormen nameten zonder één aanroep te doen."""
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # Alle zes veldnamen waaronder het label kan staan. Dit is de fout die
    # voorraad_bag maakte: hij las er een.
    for naam in VELD_LABEL:
        uit = lees({naam: "C"})
        check(f"veld {naam}", (uit or {}).get("label"), "C")
    # Dezelfde meting met een vaste naam, want eisen.txt verwijst hiernaar en
    # een naam die met een f-string wordt gemaakt staat niet letterlijk in de
    # bron. De eisenproef ving dat zelf op toen ik het verkeerd deed.
    check("alle zes veldnamen gelezen",
          sum(1 for n in VELD_LABEL if (lees({n: "C"}) or {}).get("label")),
          len(VELD_LABEL))
    check("hoofdletters en streepjes doen niet mee",
          (lees({"pandenergieklasse": "A++"}) or {}).get("label"), "A++")
    check("leeg veld telt niet", lees({"energieklasse": ""}), None)
    check("leeg record", lees({}), None)
    check("geen dict", lees(None), None)

    # Een privélabel is een antwoord en geen leegte.
    p = lees({"Pand_energielabel_is_prive": True, "Pand_energieklasse": "B"})
    check("prive geeft geen letter", (p or {}).get("label"), None)
    check("prive zegt dat het prive is", (p or {}).get("prive"), True)
    check("prive als 1", (lees({"isPrive": 1}) or {}).get("prive"), True)
    check("niet prive", (lees({"prive": False, "energieklasse": "D"}) or {}
                         ).get("prive"), False)

    # De drie antwoordvormen.
    check("lijst", (lees(eerste([{"energieklasse": "E"}])) or {}).get("label"),
          "E")
    check("enkel object",
          (lees(eerste({"energieklasse": "F"})) or {}).get("label"), "F")
    check("lijst onder results",
          (lees(eerste({"results": [{"energieklasse": "G"}]})) or {}
           ).get("label"), "G")
    check("lege lijst", eerste([]), None)
    check("datum afgekapt op tien tekens",
          (lees({"energieklasse": "A", "registratiedatum":
                 "2025-03-04T00:00:00"}) or {}).get("registratiedatum"),
          "2025-03-04")

    # Het huisnummer uit een adres. "29A-24" gaf vijftien keer HTTP 400 omdat
    # een van de drie kopieen de toevoeging liet vallen.
    check("gewoon nummer", splits_toevoeging("20"), ("20", "", ""))
    check("huisletter", splits_toevoeging("29A"), ("29", "A", ""))
    check("letter en toevoeging", splits_toevoeging("29A-24"),
          ("29", "A", "24"))
    check("alleen toevoeging", splits_toevoeging("29-24"), ("29", "", "24"))
    check("toevoeging van meer tekens", splits_toevoeging("12BIS"),
          ("12", "", "BIS"))
    check("niets", splits_toevoeging(""), ("", "", ""))
    check("uit een heel adres", uit_adres("Bachstraat 29A-24"),
          ("29", "A", "24"))
    check("adres zonder nummer", uit_adres("Hertogstraat"), ("", "", ""))

    # De route: eerst het vbo-id, en de postcode alleen als dat niets geeft.
    gevraagd = []

    def nep(code_per_url, lichaam=None):
        def haler(url, params):
            gevraagd.append(url.rsplit("/", 2)[-2] if "AdresseerbaarObject"
                            in url else "Adres")
            code = code_per_url.get("vbo" if "AdresseerbaarObject" in url
                                    else "adres", 200)
            return (code, lambda: (lichaam or {}))
        return haler

    gevraagd.clear()
    uit, fout, definitief = energielabel(
        vbo_id="0268010000000056", postcode="6524LR", huisnr="20",
        haler=nep({"vbo": 200}, {"energieklasse": "C"}))
    check("vbo eerst gevraagd", gevraagd, ["AdresseerbaarObject"])
    check("label uit de vbo-route", (uit or {}).get("label"), "C")
    check("geen fout", fout, "")

    gevraagd.clear()
    uit, fout, definitief = energielabel(
        vbo_id="0268010000000056", postcode="6524LR", huisnr="20",
        haler=nep({"vbo": 404, "adres": 200}, {"labelLetter": "D"}))
    check("na 404 ook de adresroute", gevraagd,
          ["AdresseerbaarObject", "Adres"])
    check("label uit de adresroute", (uit or {}).get("label"), "D")

    # HTTP 200 zonder label is een antwoord: dit adres heeft er geen.
    uit, fout, definitief = energielabel(
        vbo_id="X", haler=nep({"vbo": 200}, {"iets": "anders"}))
    check("200 zonder label geeft een leeg antwoord", uit, {})
    check("en dat is definitief", definitief, True)

    # 400 en 404 op alle routes: definitief, dus niet elke ronde opnieuw.
    uit, fout, definitief = energielabel(
        vbo_id="X", postcode="6524LR", huisnr="29", letter="A", toev="24",
        haler=nep({"vbo": 404, "adres": 400}))
    check("400 geeft geen uitkomst", uit, None)
    check("400 is definitief", definitief, True)
    check("400 noemt de code", fout, "HTTP 400")

    # 429 en een geweigerde sleutel zijn van ons en niet van het adres.
    for code in STOPPEN:
        uit, fout, definitief = energielabel(
            vbo_id="X", haler=nep({"vbo": code}))
        check(f"{code} stopt", (uit, definitief), (None, False))
    uit, fout, definitief = energielabel(vbo_id="X", haler=nep({"vbo": 500}))
    check("500 is niet definitief", definitief, False)

    def valt_om(url, params):
        raise OSError("verbinding weg")
    uit, fout, definitief = energielabel(vbo_id="X", haler=valt_om)
    check("netwerkfout is niet definitief", definitief, False)
    check("netwerkfout noemt zich", fout.startswith("netwerk:"), True)

    uit, fout, definitief = energielabel(haler=nep({}))
    check("zonder vbo en zonder postcode", (uit, definitief), (None, True))

    # En de drie aanroepers moeten deze module gebruiken en niet hun eigen
    # kopie. Dat is de eis "een conventie bestaat een keer in code", en voor
    # EP-Online was die kopie het verschil tussen 1.384 labels en nul.
    for pad, naam in (("marktprijzen_bag.py", "ep_energielabel"),
                      ("bekendmakingen_nijmegen.py", "ep_energielabel"),
                      ("voorraad_bag.py", "haal_label")):
        try:
            with open(pad, encoding="utf-8") as f:
                bron = f.read()
        except Exception as e:
            fouten.append(f"{pad} niet te lezen: {str(e)[:40]}")
            continue
        if "eponline" not in bron:
            fouten.append(f"{pad} gebruikt eponline niet; {naam}() heeft dan "
                          f"een eigen kopie van de aanroep")
        if "labelLetter" in bron and "eponline" not in bron:
            fouten.append(f"{pad} leest labelLetter zelf")

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten. Gedekt: de zes veldnamen, het "
          f"privelabel, de drie antwoordvormen, het huisnummer met letter en "
          f"toevoeging, de route vbo-eerst, en welke foutcodes definitief "
          f"zijn. Geen enkele aanroep.", file=sys.stderr)
    return 1 if fouten else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proef", action="store_true",
                    help="De vormen nameten zonder aanroep.")
    ap.add_argument("--adres", default="",
                    help="Eén adres opvragen, met EP_API_KEY in de omgeving.")
    ap.add_argument("--postcode", default="")
    ap.add_argument("--vbo", default="")
    a = ap.parse_args()
    if a.proef:
        sys.exit(proef())
    if a.adres or a.vbo:
        nr, letter, toev = uit_adres(a.adres) if a.adres else ("", "", "")
        print(energielabel(a.vbo or None, a.postcode, nr, letter, toev))
    sys.exit(0)
