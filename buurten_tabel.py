#!/usr/bin/env python3
"""
Buurten-tabelblok voor de Nijmegen Vastgoedmonitor.

Haalt per buurt (Stadscentrum, Benedenstad, Bottendaal, Galgenveld, Altrade,
Biezen) de eigendomsverdeling op uit de CBS Wijk- en Buurtkaart via PDOK, en
zet er de trend sinds 2021 naast. Schrijft een markdown-tabelblok weg dat
onder de bekendmakingen in de dagelijkse brief kan.

Bron: https://api.pdok.nl/cbs/wijken-en-buurten-{jaar}/ogc/v1/collections/buurten/items
Open data, geen sleutel nodig.
"""

import argparse
import sys
import urllib.parse
import requests

# --- CONFIG ---
CBS_PAD = "buurten_cbs.json"

BUURTEN = [
    ("Stadscentrum",     "oost"),
    ("Benedenstad",      "oost"),
    ("Bottendaal",       "oost"),
    ("Galgenveld",       "oost"),
    ("Altrade",          "oost"),
    ("Biezen",           "west"),
]
GEMEENTE = "Nijmegen"
JAAR_NU = "2024"
JAAR_TREND = "2021"   # zelfde definitie als 2024 = eerlijke vergelijking
PDOK_TMPL = ("https://api.pdok.nl/cbs/wijken-en-buurten-{jaar}"
             "/ogc/v1/collections/buurten/items?f=json&limit=2000"
             "&bbox=5.780,51.800,5.920,51.880")

KAART_URL = "https://derksenvastgoed.github.io/DerksenVastgoed-Vastgoedrapport-Nijmegen/kaart-eigendom-ring.html"
# --------------


def _get(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def _pct(v):
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if 0 <= n <= 100 else None


def _veld(p, namen):
    for n in namen:
        for k in (n, n.upper(), n.lower()):
            if k in p and p[k] not in (None, ""):
                return p[k]
    return None


def _eigendom(p):
    """Geeft koop, corp, over en 'rest' als % van ALLE woningen; som is 100."""
    koop = _pct(_veld(p, ["percentage_koopwoningen"]))
    corpH = _pct(_veld(p, ["perc_huurwoningen_in_bezit_woningcorporaties"]))
    overH = _pct(_veld(p, ["perc_huurwoningen_in_bezit_overige_verhuurders"]))
    if koop is None:
        return None, None, None, None
    huur = 100 - koop
    corp = round(huur * corpH / 100) if corpH is not None else None
    over = round(huur * overH / 100) if overH is not None else None
    bekend = round(koop) + (corp or 0) + (over or 0)
    rest = max(0, 100 - bekend)
    return round(koop), corp, over, rest


def _buurt_props(feats, naam):
    for f in feats:
        p = f.get("properties", {})
        for k in ("buurtnaam", "BUURTNAAM", "bu_naam", "BU_NAAM", "naam"):
            v = p.get(k)
            if v and str(v).strip().lower() == naam.lower() and str(p.get("gemeentenaam", GEMEENTE)).lower() == GEMEENTE.lower():
                return p
    return None


def _woningen(p):
    v = _veld(p, ["aantal_woningen", "woningvoorraad"])
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _woz(p):
    v = _veld(p, ["gemiddelde_woningwaarde", "gemiddelde_woz_waarde_woning"])
    try:
        return int(v) if v is not None and int(v) > 0 else None
    except (TypeError, ValueError):
        return None


# Mogelijke namen voor de gemiddelde woningoppervlakte. Of het CBS dit per buurt
# levert weten we niet zeker; vindt het script niets, dan logt het alle velden.
# Inkomen per buurt. Het CBS levert dit met ongeveer twee jaar vertraging en
# onderdrukt het bij kleine buurten, dus een lege waarde is normaal.
INKOMEN_VELDEN = [
    "gemiddeld_inkomen_per_inwoner",
    "gemiddeld_gestandaardiseerd_inkomen_van_huishoudens",
    "gemiddeld_inkomen_inwoner", "gem_inkomen_per_inwoner",
    "inkomen_per_inwoner",
]
INKOMEN_ONTVANGER_VELDEN = [
    "gemiddeld_inkomen_per_inkomensontvanger", "gem_inkomen_per_inkomensontvanger",
    "inkomen_per_inkomensontvanger",
]
# Het CBS heeft "laag inkomen" en "sociaal minimum" vervangen door een nieuwe
# armoededefinitie, ontwikkeld met Nibud en SCP. Beide reeksen staan erin,
# zodat het werkt met de oude en de nieuwe tabel.
LAAG_INKOMEN_VELDEN = [
    "percentage_huishoudens_met_een_laag_inkomen", "perc_huishoudens_laag_inkomen",
    "percentage_laag_inkomen", "perc_laag_inkomen",
    "percentage_huishoudens_onder_de_armoedegrens", "percentage_armoede",
    "perc_huishoudens_armoede", "percentage_huishoudens_in_armoede",
]

# Mediaan vermogen per buurt: het saldo van bezittingen en schulden. Dit is een
# gemeten cijfer, niet afgeleid uit leeftijd of inkomen. Bij weinig huishoudens
# onderdrukt het CBS de waarde.
VERMOGEN_VELDEN = [
    # De naam die het CBS werkelijk gebruikt, afgekort en al
    "mediaan_vermogen_van_particuliere_huish",
    "mediaan_vermogen_particuliere_huishoudens", "mediaan_vermogen",
    "med_vermogen_part_huish", "mediaan_vermogen_part_huishoudens",
    "mediaan_vermogen_van_particuliere_huishoudens",
]
MINIMUM_VELDEN = [
    "percentage_huishoudens_onder_of_rond_sociaal_minimum",
    "perc_huishoudens_onder_of_rond_sociaal_minimum",
    "percentage_onder_of_rond_sociaal_minimum",
]

# Huishoudenssamenstelling. Het aandeel alleenwonenden voorspelt de vraag naar
# kleine eenheden, en dat is waar de huur per m2 het hoogst ligt.
HUISHOUDENS_VELDEN = ["aantal_huishoudens", "aantal_particuliere_huishoudens"]
EENPERSOONS_VELDEN = [
    "percentage_eenpersoonshuishoudens", "perc_eenpersoonshuishoudens",
    "percentage_eenpersoons_huishoudens",
]
ZONDER_KINDEREN_VELDEN = [
    "percentage_huishoudens_zonder_kinderen", "perc_huishoudens_zonder_kinderen",
]
MET_KINDEREN_VELDEN = [
    "percentage_huishoudens_met_kinderen", "perc_huishoudens_met_kinderen",
]
GROOTTE_VELDEN = [
    "gemiddelde_huishoudsgrootte", "gemiddelde_huishoudensgrootte",
    "gem_huishoudensgrootte", "gemiddelde_huishoudens_grootte",
]

OPPERVLAKTE_VELDEN = [
    "gemiddelde_woningoppervlakte", "gemiddeld_woonoppervlak",
    "gemiddelde_oppervlakte_woning", "gemiddeld_oppervlak_woning",
    "woonoppervlakte_gemiddeld", "gemiddelde_gebruiksoppervlakte",
    "gem_woonoppervlakte", "oppervlakte_wonen_gemiddeld",
]


def _getal(p, namen, minimum=None, maximum=None):
    """Haalt een getal op en controleert of het binnen een zinnig bereik valt."""
    v = _veld(p, namen)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if minimum is not None and v < minimum:
        return None
    if maximum is not None and v > maximum:
        return None
    return round(v)


def _oppervlakte(p):
    v = _veld(p, OPPERVLAKTE_VELDEN)
    try:
        v = float(v)
        return round(v) if 15 <= v <= 400 else None
    except (TypeError, ValueError):
        return None


def _pijl(nu, toen):
    if nu is None or toen is None:
        return "—"
    d = nu - toen
    if d >= 3:
        return f"▲ +{d}"
    if d <= -3:
        return f"▼ {d}"
    return "▬ ±0" if abs(d) < 1 else f"▬ {d:+d}"


def render(rijen: list) -> str:
    """
    De trendkolom is vervallen: de CBS-kaart van 2021 is niet meer op te halen,
    en het aanbod vergelijken we tegenwoordig tegen de actuele markt.
    """
    kop = ["", "## Eigendom per buurt in je ring",
           f"_Bron: CBS Wijk- en Buurtkaart {JAAR_NU} via PDOK._", "",
           "| Buurt | Won. | Koop | Corp. | BV/overig | Rest | WOZ | Meergezins | Voor 2000 | Studenten |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rijen:
        kop.append(
            f"| **{r['naam']}** ({r['zijde']}) "
            f"| {r['won'] or '—'} "
            f"| {r['koop'] if r['koop'] is not None else '—'}% "
            f"| {r['corp'] if r['corp'] is not None else '—'}% "
            f"| {r['over'] if r['over'] is not None else '—'}% "
            f"| {r['onb'] if r['onb'] is not None else '—'}% "
            f"| {'€'+format(r['woz']*1000,',').replace(',','.') if r['woz'] else '—'} "
            f"| {str(r.get('meergezins'))+'%' if r.get('meergezins') is not None else '—'} "
            f"| {str(r.get('voor2000'))+'%' if r.get('voor2000') is not None else '—'} "
            f"| {r.get('studenten') or '—'} |"
        )
    kop += ["",
            f"[Bekijk op de kaart]({KAART_URL})",
            "",
            "_Meergezins is het aandeel appartementen in de voorraad, een indicatie of "
            "splitsen hier gebruikelijk is. Voor 2000 is het aandeel oudere voorraad, "
            "wat samenhangt met de renovatie- en labelopgave. Studenten is het aantal "
            "hbo- en wo-studenten dat in de buurt woont._"]
    return "\n".join(kop)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="buurten_tabel.md")
    args = ap.parse_args()

    try:
        nu = _get(PDOK_TMPL.format(jaar=JAAR_NU))
    except Exception as e:  # noqa
        print(f"CBS {JAAR_NU} ophalen mislukt: {e}", file=sys.stderr); sys.exit(1)
    try:
        toen = _get(PDOK_TMPL.format(jaar=JAAR_TREND))
    except Exception as e:  # noqa
        print(f"CBS {JAAR_TREND} ophalen mislukt ({e}); trend uitgeschakeld.", file=sys.stderr)
        toen = {"features": []}

    feats_nu = nu.get("features", [])
    feats_toen = toen.get("features", [])

    rijen = []
    for naam, zijde in BUURTEN:
        p_nu = _buurt_props(feats_nu, naam)
        if not p_nu:
            print(f"Waarschuwing: buurt {naam} niet gevonden in {JAAR_NU}", file=sys.stderr)
            continue
        koop, corp, over, onb = _eigendom(p_nu)
        p_toen = _buurt_props(feats_toen, naam)
        koop_toen = _eigendom(p_toen)[0] if p_toen else None
        rijen.append({
            "naam": naam, "zijde": zijde,
            "won": _woningen(p_nu), "woz": _woz(p_nu),
            "opp": _oppervlakte(p_nu),
            # Kenmerken die raken aan splitsen, renoveren en kamerverhuur
            "meergezins": _getal(p_nu, ["percentage_meergezinswoning"], 0, 100),
            "voor2000": _getal(p_nu, ["percentage_bouwjaarklasse_tot_2000"], 0, 100),
            "studenten": (_getal(p_nu, ["aantal_studenten_wo"], 0) or 0)
                         + (_getal(p_nu, ["aantal_studenten_hbo"], 0) or 0),
            "inwoners": _getal(p_nu, ["aantal_inwoners"], 0),
            "nietwoningen": _getal(p_nu, ["aantal_niet_woningvoorraad"], 0),
            # Huishoudens: wie woont er alleen en wie met hoeveel
            "huishoudens": _getal(p_nu, HUISHOUDENS_VELDEN, 0),
            "eenpersoons": _getal(p_nu, EENPERSOONS_VELDEN, 0, 100),
            "zonder_kinderen": _getal(p_nu, ZONDER_KINDEREN_VELDEN, 0, 100),
            "met_kinderen": _getal(p_nu, MET_KINDEREN_VELDEN, 0, 100),
            "huishoudgrootte": _getal(p_nu, GROOTTE_VELDEN, 1, 6),
            # Inkomen zegt wat de buurt kan dragen aan huur
            # Ondergrens 1 in plaats van 0: het CBS zet -99999997 bij ontbrekend
            "inkomen": _getal(p_nu, INKOMEN_VELDEN, 1, 500),
            "inkomen_ontvanger": _getal(p_nu, INKOMEN_ONTVANGER_VELDEN, 0, 500),
            "laag_inkomen": _getal(p_nu, LAAG_INKOMEN_VELDEN, 0, 100),
            "vermogen": _getal(p_nu, VERMOGEN_VELDEN, -400, 5000),
            "sociaal_minimum": _getal(p_nu, MINIMUM_VELDEN, 0, 100),
            "bedrijven": _getal(p_nu, ["aantal_bedrijfsvestigingen"], 0),
            "leegstand": _getal(p_nu, ["percentage_leegstand_woningen"], 0, 100),
            "koop": koop, "corp": corp, "over": over, "onb": onb,
            "trend": _pijl(koop, koop_toen),
        })

    # Stadstotalen: alles wat in de opgehaalde set als Nijmegen geregistreerd staat.
    # Zo kun je de ring afzetten tegen de stad als geheel.
    stad = {"woningen": 0, "nietwoningen": 0, "inwoners": 0,
            "studenten": 0, "bedrijven": 0, "buurten": 0}
    for f in feats_nu:
        p = f.get("properties", {}) or {}
        if str(p.get("gemeentenaam", "")).lower() != GEMEENTE.lower():
            continue
        stad["buurten"] += 1
        stad["woningen"] += _getal(p, ["woningvoorraad", "aantal_woningen"], 0) or 0
        stad["nietwoningen"] += _getal(p, ["aantal_niet_woningvoorraad"], 0) or 0
        stad["inwoners"] += _getal(p, ["aantal_inwoners"], 0) or 0
        stad["studenten"] += ((_getal(p, ["aantal_studenten_wo"], 0) or 0)
                              + (_getal(p, ["aantal_studenten_hbo"], 0) or 0))
        stad["bedrijven"] += _getal(p, ["aantal_bedrijfsvestigingen"], 0) or 0
    print(f"Stadstotalen over {stad['buurten']} buurten: "
          f"{stad['woningen']} woningen, {stad['inwoners']} inwoners, "
          f"{stad['studenten']} studenten", file=sys.stderr)

    if rijen and not any(r.get("vermogen") for r in rijen):
        eerste_v = _buurt_props(feats_nu, BUURTEN[0][0]) or {}
        vermogensachtig = sorted(k for k in eerste_v
                                 if "vermogen" in k.lower() or "armoede" in k.lower())
        print("Geen vermogensgegevens gevonden in de CBS-buurtkaart.", file=sys.stderr)
        print(f"  Velden die op vermogen of armoede lijken: "
              f"{vermogensachtig or 'geen'}", file=sys.stderr)

    if rijen and not any(r.get("eenpersoons") for r in rijen):
        eerste_h = _buurt_props(feats_nu, BUURTEN[0][0]) or {}
        huishoudachtig = sorted(k for k in eerste_h if "huishoud" in k.lower())
        print("Geen huishoudensgegevens gevonden in de CBS-buurtkaart.",
              file=sys.stderr)
        print(f"  Velden die op huishoudens lijken: {huishoudachtig or 'geen'}",
              file=sys.stderr)

    if rijen and not any(r.get("inkomen") or r.get("laag_inkomen") for r in rijen):
        eerste_i = _buurt_props(feats_nu, BUURTEN[0][0]) or {}
        inkomensachtig = sorted(k for k in eerste_i
                                if "inkom" in k.lower() or "minimum" in k.lower()
                                or "welvaart" in k.lower())
        print("Geen inkomensgegevens gevonden in de CBS-buurtkaart.", file=sys.stderr)
        print(f"  Velden die op inkomen lijken: {inkomensachtig or 'geen'}",
              file=sys.stderr)

    if rijen and not any(r.get("opp") for r in rijen):
        eerste = _buurt_props(feats_nu, BUURTEN[0][0]) or {}
        print("Geen gemiddelde woningoppervlakte gevonden in de CBS-gegevens.",
              file=sys.stderr)
        print(f"Beschikbare velden: {sorted(eerste.keys())}", file=sys.stderr)

    md = render(rijen)
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\nTabel opgeslagen in {args.uit}", file=sys.stderr)

    # Ook als los gegevensbestand wegschrijven. Het marktprijzen-script toont
    # deze cijfers per buurt, maar alleen bij buurten waar aanbod in staat.
    import json as _json
    gegevens = {r["naam"]: {k: r.get(k) for k in
                            ("won", "woz", "koop", "corp", "over", "trend", "opp",
                             "meergezins", "voor2000", "studenten", "leegstand",
                             "inwoners", "nietwoningen", "bedrijven",
                             "inkomen", "inkomen_ontvanger", "laag_inkomen",
                             "sociaal_minimum", "vermogen", "huishoudens", "eenpersoons",
                             "zonder_kinderen", "met_kinderen", "huishoudgrootte")}
                for r in rijen}
    gegevens["_nijmegen"] = stad
    with open(CBS_PAD, "w", encoding="utf-8") as f:
        _json.dump(gegevens, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Buurtgegevens opgeslagen in {CBS_PAD}", file=sys.stderr)


if __name__ == "__main__":
    main()
