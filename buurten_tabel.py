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
OPPERVLAKTE_VELDEN = [
    "gemiddelde_woningoppervlakte", "gemiddeld_woonoppervlak",
    "gemiddelde_oppervlakte_woning", "gemiddeld_oppervlak_woning",
    "woonoppervlakte_gemiddeld", "gemiddelde_gebruiksoppervlakte",
    "gem_woonoppervlakte", "oppervlakte_wonen_gemiddeld",
]


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
    kop = ["", "## Eigendom per buurt in je ring",
           f"_Bron: CBS Wijk- en Buurtkaart {JAAR_NU} via PDOK. "
           f"Trend = verschil met {JAAR_TREND} in procentpunten (koop-aandeel)._", "",
           "| Buurt | Won. | Koop | Corp. | BV/overig | Rest | WOZ | Trend koop |",
           "|---|---:|---:|---:|---:|---:|---:|:--|"]
    for r in rijen:
        kop.append(
            f"| **{r['naam']}** ({r['zijde']}) "
            f"| {r['won'] or '—'} "
            f"| {r['koop'] if r['koop'] is not None else '—'}% "
            f"| {r['corp'] if r['corp'] is not None else '—'}% "
            f"| {r['over'] if r['over'] is not None else '—'}% "
            f"| {r['onb'] if r['onb'] is not None else '—'}% "
            f"| {'€'+format(r['woz']*1000,',').replace(',','.') if r['woz'] else '—'} "
            f"| {r['trend']} |"
        )
    kop += ["",
            f"[Bekijk op de kaart]({KAART_URL})",
            "",
            "_Let op: de 'trend'-kolom vergelijkt binnen dezelfde CBS-definitie (2021 en later). "
            "Langere reeksen zijn onbetrouwbaar door een definitiewijziging in 2021._"]
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
            "koop": koop, "corp": corp, "over": over, "onb": onb,
            "trend": _pijl(koop, koop_toen),
        })

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
                            ("won", "woz", "koop", "corp", "over", "trend", "opp")}
                for r in rijen}
    with open(CBS_PAD, "w", encoding="utf-8") as f:
        _json.dump(gegevens, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Buurtgegevens opgeslagen in {CBS_PAD}", file=sys.stderr)


if __name__ == "__main__":
    main()
