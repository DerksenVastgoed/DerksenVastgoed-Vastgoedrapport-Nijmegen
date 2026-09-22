#!/usr/bin/env python3
"""
Prijsindex bestaande koopwoningen van het CBS, landelijk en voor Nijmegen.

Waarom: onze eigen ringcijfers zijn de mediaan van vraagprijzen, en die
verschuift ook als er andere panden bijkomen. De CBS-index meet iets anders:
werkelijke verkoopprijzen uit de notaristransacties van het Kadaster,
gecorrigeerd voor het type woning. Naast elkaar gezet laten ze zien of de ring
anders beweegt dan Nederland of Nijmegen, maar een op een vergelijken kan niet.

Twee tabellen:
- 85773NED, landelijk, per maand, circa 22 dagen na de verslagmaand.
- 85792NED, per regio, per kwartaal, circa 22 dagen na het kwartaal.

Kolomnamen en regiocodes worden opgezocht in plaats van aangenomen. Een kolom
met een verandering wordt nooit als indexniveau gebruikt; wat er gekozen is,
staat in de diagnose.

Gebruik:
  python woningprijsindex.py
Schrijft woningprijsindex.json.
"""

import json
import re
import sys

import requests

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass

BASIS = "https://opendata.cbs.nl/ODataApi/OData"
LANDELIJK = "85773NED"
REGIONAAL = "85792NED"
UIT_PAD = "woningprijsindex.json"

# Welke regio we zoeken, in volgorde van voorkeur
REGIO_ZOEK = ("Nijmegen", "Gelderland")


def _haal(url, params=None):
    """Alle rijen van een OData-bron, via de nextLink die het CBS meegeeft."""
    rijen, eerste = [], True
    for _ronde in range(40):
        r = requests.get(url, params=params if eerste else None, timeout=(15, 90))
        r.raise_for_status()
        body = r.json()
        rijen.extend(body.get("value", []))
        url = body.get("odata.nextLink") or body.get("@odata.nextLink")
        eerste = False
        if not url:
            break
    return rijen


def kies_kolommen(sleutels):
    """
    Het indexniveau, en de seizoengecorrigeerde maandontwikkeling als die er is.

    Een kolom met "ontwikkeling", "mutatie" of "verandering" is een percentage
    en geen niveau. Die mag nooit als index worden gebruikt: dan reken je met
    een verandering alsof het een stand is.
    """
    def laag(k):
        return k.lower()
    verandering = ("ontwikkeling", "mutatie", "verandering")
    index = [k for k in sleutels if "prijsindex" in laag(k)
             and not any(v in laag(k) for v in verandering)]
    seizoen = [k for k in sleutels if "seizoen" in laag(k)
               and any(v in laag(k) for v in verandering)]
    return (index[0] if index else None), (seizoen[0] if seizoen else None)


def _pct(nu, toen):
    return round((nu - toen) / toen * 100, 1) if toen else None


def landelijk():
    """De landelijke index per maand, met de ontwikkeling op maand en jaar."""
    try:
        rijen = _haal(f"{BASIS}/{LANDELIJK}/TypedDataSet")
    except Exception as e:
        leg_vast("woningprijzen", f"Landelijke tabel {LANDELIJK} niet op te halen: "
                                  f"{str(e)[:150]}")
        return None
    if not rijen:
        leg_vast("woningprijzen", f"Tabel {LANDELIJK} gaf geen rijen.")
        return None
    kol, seiz = kies_kolommen(list(rijen[0].keys()))
    if not kol:
        leg_vast("woningprijzen", f"Geen indexkolom in {LANDELIJK}. Kolommen: "
                                  f"{', '.join(rijen[0].keys())}")
        return None

    reeks, seizoen = {}, {}
    for r in rijen:
        p = (r.get("Perioden") or "").strip()
        m = re.fullmatch(r"(\d{4})MM(\d{2})", p)
        if not m or r.get(kol) is None:
            continue
        maand = f"{m.group(1)}-{m.group(2)}"
        reeks[maand] = float(r[kol])
        if seiz and r.get(seiz) is not None:
            seizoen[maand] = float(r[seiz])
    if len(reeks) < 13:
        leg_vast("woningprijzen", f"Te weinig maanden in {LANDELIJK}: {len(reeks)}")
        return None

    maanden = sorted(reeks)
    laatste = maanden[-1]
    j, mnd = laatste.split("-")
    jaar_eerder = f"{int(j) - 1}-{mnd}"
    uit = {
        "periode": laatste,
        "index": reeks[laatste],
        "maand_pct": _pct(reeks[laatste], reeks[maanden[-2]]),
        "jaar_pct": _pct(reeks[laatste], reeks.get(jaar_eerder)),
        "kolom": kol,
    }
    if seizoen.get(laatste) is not None:
        uit["maand_pct_seizoen"] = seizoen[laatste]
        uit["kolom_seizoen"] = seiz
    return uit


def regio():
    """De index voor Nijmegen per kwartaal, of anders Gelderland."""
    try:
        opties = _haal(f"{BASIS}/{REGIONAAL}/RegioS")
    except Exception as e:
        leg_vast("woningprijzen", f"Regio's van {REGIONAAL} niet op te halen: "
                                  f"{str(e)[:150]}")
        return None
    titels = [((o.get("Key") or "").strip(), (o.get("Title") or "").strip())
              for o in opties]
    gekozen = None
    for zoek in REGIO_ZOEK:
        for sleutel, titel in titels:
            if titel.lower().startswith(zoek.lower()):
                gekozen = (sleutel, titel)
                break
        if gekozen:
            break
    if not gekozen:
        leg_vast("woningprijzen", f"Geen Nijmegen of Gelderland in {REGIONAAL}. "
                                  f"Voorbeelden: "
                                  + "; ".join(t for _k, t in titels[:12]))
        return None
    sleutel, titel = gekozen

    # Eerst met een filter; lukt dat niet, dan alles ophalen en zelf filteren
    try:
        rijen = _haal(f"{BASIS}/{REGIONAAL}/TypedDataSet",
                      {"$filter": f"startswith(RegioS,'{sleutel}')"})
    except Exception:
        try:
            rijen = _haal(f"{BASIS}/{REGIONAAL}/TypedDataSet")
        except Exception as e:
            leg_vast("woningprijzen", f"Regionale tabel niet op te halen: "
                                      f"{str(e)[:150]}")
            return None
    rijen = [r for r in rijen if (r.get("RegioS") or "").strip() == sleutel]
    if not rijen:
        leg_vast("woningprijzen", f"Geen rijen voor {titel} ({sleutel}).")
        return None
    kol, _s = kies_kolommen(list(rijen[0].keys()))
    if not kol:
        leg_vast("woningprijzen", f"Geen indexkolom in {REGIONAAL}. Kolommen: "
                                  f"{', '.join(rijen[0].keys())}")
        return None

    reeks = {}
    for r in rijen:
        p = (r.get("Perioden") or "").strip()
        m = re.fullmatch(r"(\d{4})KW0?(\d)", p)
        if m and r.get(kol) is not None:
            reeks[f"{m.group(1)}-K{m.group(2)}"] = float(r[kol])
    if len(reeks) < 5:
        leg_vast("woningprijzen", f"Te weinig kwartalen voor {titel}: {len(reeks)}")
        return None
    kwartalen = sorted(reeks)
    laatste = kwartalen[-1]
    j, k = laatste.split("-K")
    jaar_eerder = f"{int(j) - 1}-K{k}"
    return {"naam": titel, "periode": laatste, "index": reeks[laatste],
            "kwartaal_pct": _pct(reeks[laatste], reeks[kwartalen[-2]]),
            "jaar_pct": _pct(reeks[laatste], reeks.get(jaar_eerder)),
            "kolom": kol}


def omschrijf(data):
    """Tekst voor de brief, met de kanttekening over wat het meet."""
    if not data:
        return ""
    delen = []
    l = data.get("landelijk")
    if l:
        maand = l.get("maand_pct_seizoen", l.get("maand_pct"))
        soort = ("seizoengecorrigeerd" if "maand_pct_seizoen" in l
                 else "niet seizoengecorrigeerd")
        delen.append(f"Landelijk, {l['periode']}: "
                     + f"{maand:+.1f}".replace(".", ",")
                     + f"% op een maand ({soort}), "
                     + f"{l['jaar_pct']:+.1f}".replace(".", ",")
                     + "% op een jaar")
    r = data.get("regio")
    if r:
        delen.append(f"{r['naam']}, {r['periode']}: "
                     + f"{r['kwartaal_pct']:+.1f}".replace(".", ",")
                     + "% op een kwartaal, "
                     + f"{r['jaar_pct']:+.1f}".replace(".", ",")
                     + "% op een jaar")
    if not delen:
        return ""
    return ("Prijsindex bestaande koopwoningen van CBS en Kadaster, uit "
            "werkelijke verkoopprijzen en gecorrigeerd voor het type woning. "
            + ". ".join(delen) + ". Dit is een andere maat dan onze ringcijfers, "
            "die de mediaan van vraagprijzen zijn en ook verschuiven door welke "
            "panden er bijkomen. Naast elkaar zetten mag, een op een vergelijken "
            "niet. Bron: CBS, tabellen 85773NED en 85792NED.")


def main():
    wis("woningprijzen")
    data = {"landelijk": landelijk(), "regio": regio()}
    with open(UIT_PAD, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(omschrijf(data) or "Geen woningprijsindex opgehaald", file=sys.stderr)
    for deel in ("landelijk", "regio"):
        if data.get(deel):
            print(f"  {deel}: kolom {data[deel].get('kolom')}", file=sys.stderr)


if __name__ == "__main__":
    main()
