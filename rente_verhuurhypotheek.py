#!/usr/bin/env python3
"""
Rente-blok voor de Nijmegen Vastgoedmonitor.

Haalt het actuele overzicht verhuurhypotheek-tarieven op van financieren.nl/rente,
vergelijkt met de opgeslagen historie, en schrijft een compact markdown-blok:

- Scherpste tarief per LTV (50%, 70%, 80%) met aanbieder en link naar de bron
- Beweging tegenover een week geleden
- Vertaalregel naar Marks acquisitiemodel (17x jaarhuur, LTV 70%)
- Compact als er niets beweegt; uitgebreider bij een beweging >= 10 basispunten

Draait als losse Python-file; historie wordt bewaard in rente_historie.json
in dezelfde map (dus in de repo, zodat GitHub Actions hem meecommit).
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from html.parser import HTMLParser

import requests

# --- CONFIG ---
BRON_URL = "https://financieren.nl/rente/"
HISTORIE_PAD = "rente_historie.json"
DREMPEL_BP = 10  # basispunten; onder deze beweging = compact blok

# Aanbieder-tarievenpagina's: bron van waarheid als je door wilt klikken
AANBIEDER_LINKS = {
    "nibc":     "https://www.nibc.nl/vastgoed-hypotheek/rentes-vastgoed-hypotheek",
    "rnhb":     "https://www.rnhb.nl/actuele-tarieven/",
    "domivest": "https://www.domivest.com/tarieven/",
    "nestr":    "https://nestr.finance/actuele-rente-verhuurhypotheek/",
    "dcmf":     "https://www.dcmf.nl/tarieven/",
    "hyra":     "https://hyrahypotheken.nl/tarieven/",
    "solidbriq":"https://solidbriq.nl/",
}

# Vertaalregel-parameters (Marks vuistregel)
VUISTREGEL_JAARHUUR = 15000   # illustratie: pand met 15k jaarhuur
LTV_STANDAARD = 70            # jullie meest gebruikte LTV
KOOPSOM_VUISTREGEL = 17       # 17x jaarhuur = referentie-bod
# --------------


class TabelParser(HTMLParser):
    """Trekt de eerste <table> uit de HTML als lijst-van-lijsten van tekst."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table" and not self.rows:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            self.current_row.append(" ".join(self.current_cell).strip())

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.strip())


def haal_tabel() -> list:
    r = requests.get(BRON_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    p = TabelParser()
    p.feed(r.text)
    if not p.rows or len(p.rows) < 2:
        raise RuntimeError("Geen tarieventabel gevonden op financieren.nl/rente")
    return p.rows


def _pct(cel: str):
    """Trekt bv. 5,50% of 5.50% uit een cel; None als er niks staat."""
    m = re.search(r"(\d+[.,]\d+)\s*%", cel)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def parse(rijen: list) -> list:
    """Zet ruwe tabel om in [{aanbieder, ltv50, ltv70, ltv80}]."""
    kop = [c.lower() for c in rijen[0]]
    idx = {}
    for i, c in enumerate(kop):
        if "aanbieder" in c:
            idx["naam"] = i
        elif "50%" in c or "50 %" in c:
            idx["ltv50"] = i
        elif "70%" in c or "70 %" in c:
            idx["ltv70"] = i
        elif "80%" in c or "80 %" in c:
            idx["ltv80"] = i
    if "naam" not in idx:
        raise RuntimeError(f"Kolommen niet herkend: {kop}")
    uit = []
    for r in rijen[1:]:
        if len(r) <= max(idx.values()):
            continue
        uit.append({
            "aanbieder": r[idx["naam"]].strip(),
            "ltv50": _pct(r[idx["ltv50"]]) if "ltv50" in idx else None,
            "ltv70": _pct(r[idx["ltv70"]]) if "ltv70" in idx else None,
            "ltv80": _pct(r[idx["ltv80"]]) if "ltv80" in idx else None,
        })
    return [x for x in uit if x["aanbieder"]]


def scherpste(rijen, ltv_key) -> tuple:
    """Retourneert (aanbieder, rente) van de laagste beschikbare rente in kolom."""
    kandidaten = [(x["aanbieder"], x[ltv_key]) for x in rijen if x[ltv_key] is not None]
    if not kandidaten:
        return (None, None)
    kandidaten.sort(key=lambda x: x[1])
    return kandidaten[0]


def aanbieder_link(naam: str) -> str:
    if not naam:
        return ""
    sleutel = re.sub(r"[^a-z]", "", naam.lower())
    for k, url in AANBIEDER_LINKS.items():
        if k in sleutel:
            return url
    return ""


def lees_historie() -> dict:
    if not os.path.exists(HISTORIE_PAD):
        return {}
    try:
        with open(HISTORIE_PAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa
        return {}


def schrijf_historie(hist: dict):
    with open(HISTORIE_PAD, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)


def week_geleden(hist: dict, ltv_key: str):
    """Rente van 5 tot 9 werkdagen geleden voor deze LTV, of None."""
    vandaag = dt.date.today()
    for offset in range(5, 10):
        datum = (vandaag - dt.timedelta(days=offset)).isoformat()
        if datum in hist and hist[datum].get(ltv_key) is not None:
            return hist[datum][ltv_key], datum
    return None, None


def _bp(a: float, b: float) -> int:
    return round((a - b) * 100)


def _pijl(delta_bp: int) -> str:
    if delta_bp >= DREMPEL_BP:
        return f"▲ +{delta_bp} bp"
    if delta_bp <= -DREMPEL_BP:
        return f"▼ {delta_bp} bp"
    return f"▬ {delta_bp:+d} bp"


def _nl(getal):
    """Nederlands geformatteerd getal, bv 15000 -> '15.000'."""
    return f"{getal:,}".replace(",", ".")


def vertaal_bod(rente_pct: float) -> str:
    """MSRE-lens: wat betekent deze rente voor een representatief pand in Marks segment.
    Referentie-scenario: pand €1,5M waarde, €1M lening, €67.500 kale huur/jaar."""
    waarde = 1_500_000
    lening = 1_000_000
    kale_huur = 67_500
    ltv = lening / waarde * 100  # 66,7%
    rentelast = lening * rente_pct / 100
    icr = kale_huur / rentelast if rentelast > 0 else 0
    opex_pct = 25  # realistisch voor vooroorlogs bezit
    netto_huur = kale_huur * (1 - opex_pct / 100)
    cashflow = netto_huur - rentelast
    equity = waarde - lening
    equity_rendement = cashflow / equity * 100 if equity > 0 else 0

    return (
        f"**Wat betekent {rente_pct:.2f}% voor een typisch pand?** "
        f"Neem een representatief pand van €{_nl(waarde)} met €{_nl(lening)} hypotheek "
        f"(LTV {ltv:.0f}%) en €{_nl(kale_huur)} kale huur per jaar. "
        f"Rentelast: **€{_nl(round(rentelast))}/jaar**. "
        f"Huur dekt rente {icr:.2f}× (banken willen minimaal 1,25×; je zit {'krap' if icr < 1.3 else 'ruim'}). "
        f"Na 25% opex (onderhoud, leegstand, beheer) resteert €{_nl(round(netto_huur))} netto huur. "
        f"Netto cashflow: **€{_nl(round(cashflow))}/jaar** op €{_nl(equity)} equity = "
        f"{equity_rendement:.1f}% direct rendement."
        + (f"\n\n_{'⚠️ Cashflow is negatief bij deze rente' if cashflow < 0 else 'Cashflow blijft positief maar mager'}. "
           f"Rendement in dit segment moet komen uit mutatie-events: renovatie, huurverhoging bij nieuwe huurder, splitsen naar meerdere units. "
           f"Elke 0,25% rentestijging kost €{_nl(round(lening * 0.0025))} extra rentelast per jaar._")
    )


def render(scherpsten: dict, wijzigingen: dict, alles: list, modus="weekelijks") -> str:
    vandaag = dt.date.today().strftime("%d-%m-%Y")
    grote_beweging = any(abs(v["delta_bp"]) >= DREMPEL_BP for v in wijzigingen.values() if v)

    # Doordeweeks alleen melden als er iets is gebeurd. Staat de rente stil,
    # dan hoort hij thuis in de zondagsbrief en niet elke ochtend opnieuw.
    if modus == "dagelijks" and not grote_beweging:
        return ""

    r = ["", "## Rente verhuurhypotheek"]

    # Rustige dag: een regel, geen tabel. De volledige analyse verschijnt zodra er iets beweegt.
    if not grote_beweging:
        delen = []
        for label, key in [("50%", "ltv50"), ("70%", "ltv70"), ("80%", "ltv80")]:
            _, rente = scherpsten.get(key, (None, None))
            if rente is not None:
                delen.append(f"{rente:.2f}% bij {label} LTV")
        _, r70 = scherpsten.get("ltv70", (None, None))
        regel = "Onveranderd deze week: " + ", ".join(delen) + "."
        if r70 is not None:
            regel += (f" Op een lening van €1.000.000 is dat "
                      f"€{_nl(round(1_000_000 * r70 / 100))} rentelast per jaar.")
        r.append(regel)
        r.append(f"_Bron: [financieren.nl/rente]({BRON_URL}), {vandaag}._")
        r.append("")
        return "\n".join(r)

    # Er is beweging: volledige tabel en analyse
    r.append(f"_Bron: [financieren.nl/rente]({BRON_URL}), {vandaag}. Scherpste tarief per LTV._")
    r.append("")
    r.append("| LTV | Rente | Aanbieder | Beweging | Bron |")
    r.append("|---|---:|---|:--|:--|")
    for label, key in [("50%", "ltv50"), ("70%", "ltv70"), ("80%", "ltv80")]:
        naam, rente = scherpsten.get(key, (None, None))
        if rente is None:
            r.append(f"| {label} | — | — | — | — |")
            continue
        w = wijzigingen.get(key)
        pijl = _pijl(w["delta_bp"]) if w else "geen historie"
        link = aanbieder_link(naam)
        link_md = f"[bron]({link})" if link else "—"
        r.append(f"| {label} | **{rente:.2f}%** | {naam} | {pijl} | {link_md} |")

    r.append("")
    _, r70 = scherpsten.get("ltv70", (None, None))
    if r70 is not None:
        r.append(vertaal_bod(r70))
    r.append("")

    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modus", choices=["dagelijks", "weekelijks"], default="weekelijks")
    ap.add_argument("--uit", default="rente_digest.md")
    args = ap.parse_args()

    try:
        rijen = haal_tabel()
        data = parse(rijen)
    except Exception as e:  # noqa
        print(f"Ophalen mislukt: {e}", file=sys.stderr)
        sys.exit(1)

    scherpsten = {k: scherpste(data, k) for k in ("ltv50", "ltv70", "ltv80")}

    hist = lees_historie()
    vandaag_iso = dt.date.today().isoformat()
    hist[vandaag_iso] = {k: v[1] for k, v in scherpsten.items() if v[1] is not None}

    wijzigingen = {}
    for k in ("ltv50", "ltv70", "ltv80"):
        _, nu = scherpsten[k]
        toen, toen_datum = week_geleden(hist, k)
        if nu is not None and toen is not None:
            wijzigingen[k] = {"delta_bp": _bp(nu, toen), "vergeleken": toen_datum}
        else:
            wijzigingen[k] = None

    md = render(scherpsten, wijzigingen, data, modus=args.modus)
    print(md)
    with open(args.uit, "w", encoding="utf-8") as f:
        f.write(md)
    schrijf_historie(hist)
    print(f"\nRente-digest opgeslagen in {args.uit}", file=sys.stderr)


if __name__ == "__main__":
    main()
