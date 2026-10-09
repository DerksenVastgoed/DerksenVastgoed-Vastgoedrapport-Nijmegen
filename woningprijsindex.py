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

import datetime as dt
import json
import re
import socket
import sys
import time

import requests

try:
    from diagnose import leg_vast, wis
except Exception:  # noqa
    def leg_vast(*_a):
        pass

    def wis(*_a):
        pass

BASIS = "https://opendata.cbs.nl/ODataApi/OData"
# Tweede ingang: dezelfde tabellen, andere opbouw. De eerste run liep op een
# verbindingsfout naar opendata.cbs.nl; dan proberen we het hier.
BASIS_V4 = "https://datasets.cbs.nl/odata/v1/CBS"
# Derde ingang: het CBS levert de v4-API ook op dit adres.
BASIS_V4_OUD = "https://odata4.cbs.nl/CBS"


def alleen_ipv4():
    """
    Verbindingen over IPv4 dwingen.

    Twee CBS-hosts gaven een verbindingsfout terwijl dataderden.cbs.nl en alle
    andere bronnen wel werkten. Dat patroon hoort bij een host met zowel een
    IPv4- als een IPv6-adres op een machine waar het IPv6-verkeer nergens heen
    kan: de naam wordt gevonden, de verbinding niet opgebouwd. Door alleen naar
    IPv4-adressen te vragen valt die route weg.
    """
    echte = socket.getaddrinfo

    def ipv4(host, port, familie=0, *rest):
        return echte(host, port, socket.AF_INET, *rest)

    socket.getaddrinfo = ipv4
LANDELIJK = "85773NED"
REGIONAAL = "85792NED"
UIT_PAD = "woningprijsindex.json"

# Welke regio we zoeken, in volgorde van voorkeur
REGIO_ZOEK = ("Nijmegen", "Gelderland")


# Welke ingang uiteindelijk antwoordde. Zonder dit weet je na een storing niet
# of de eerste weer werkt of dat de terugval het al weken opvangt.
GEBRUIKT = {"ingang": None}


def _verzoek(url, params=None, pogingen=3):
    """
    Een verzoek aan het CBS, met wachten tussen de pogingen.

    De eerste run liep op een verbindingsfout naar opendata.cbs.nl, niet op een
    foutcode. Dat kan tijdelijk zijn; drie pogingen met oplopende wachttijd
    vangen dat af. Blijft het mislukken, dan staat de host in de diagnose zodat
    duidelijk is dat het niet aan de tabel ligt.
    """
    laatste = None
    for poging in range(1, pogingen + 1):
        try:
            r = requests.get(url, params=params, timeout=(15, 90))
            r.raise_for_status()
            return r
        except Exception as e:
            laatste = e
            if poging < pogingen:
                time.sleep(poging * 5)
    raise laatste


def _haal(url, params=None):
    """Alle rijen van een OData-bron, via de nextLink die het CBS meegeeft."""
    rijen, eerste = [], True
    for _ronde in range(40):
        if eerste and "opendata.cbs.nl" in url:
            GEBRUIKT["ingang"] = "opendata.cbs.nl"
        r = _verzoek(url, params if eerste else None)
        body = r.json()
        rijen.extend(body.get("value", []))
        url = body.get("odata.nextLink") or body.get("@odata.nextLink")
        eerste = False
        if not url:
            break
    return rijen


def _haal_v4(tabel, pad, params=None, basis=None):
    """Rijen uit de v4-API, die met @odata.nextLink doorpagineert."""
    if basis is None:
        try:
            return _haal_v4(tabel, pad, params, BASIS_V4)
        except Exception as e:
            print(f"  v4 op datasets.cbs.nl mislukt ({str(e)[:60]}), nu odata4",
                  file=sys.stderr)
            return _haal_v4(tabel, pad, params, BASIS_V4_OUD)
    GEBRUIKT["ingang"] = basis.split("/")[2]
    url, rijen, eerste = f"{basis}/{tabel}/{pad}", [], True
    for _ronde in range(40):
        r = _verzoek(url, params if eerste else None)
        body = r.json()
        rijen.extend(body.get("value", []))
        url = body.get("@odata.nextLink") or body.get("odata.nextLink")
        eerste = False
        if not url:
            break
    return rijen


def _index_uit_v4(tabel, regio_sleutel=None):
    """
    De indexreeks uit de v4-API, met dezelfde vorm als de v3-rijen.

    In v4 staat elke cel apart, met een code voor wat er gemeten is. Die code
    zoeken we op in plaats van hem aan te nemen: we nemen de maat waarvan de
    titel over de prijsindex gaat en niet over een ontwikkeling.
    """
    maten = _haal_v4(tabel, "MeasureCodes")
    verandering = ("ontwikkeling", "mutatie", "verandering")
    gekozen = None
    for m in maten:
        titel = (m.get("Title") or "").lower()
        if "prijsindex" in titel and not any(v in titel for v in verandering):
            gekozen = m.get("Identifier")
            break
    if not gekozen:
        leg_vast("woningprijzen", f"Geen indexmaat in {tabel} via de v4-API. "
                                  + "; ".join((m.get("Title") or "")[:40]
                                              for m in maten[:8]))
        return [], None
    filters = [f"Measure eq '{gekozen}'"]
    if regio_sleutel:
        filters.append(f"RegioS eq '{regio_sleutel}'")
    rijen = _haal_v4(tabel, "Observations",
                     {"$filter": " and ".join(filters)})
    # Terugvertalen naar de vorm die de rest van dit script verwacht
    uit = [{"Perioden": r.get("Perioden"), "RegioS": r.get("RegioS"),
            "_waarde": r.get("Value")} for r in rijen if r.get("Value") is not None]
    return uit, "_waarde"


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
    kol = seiz = None
    try:
        rijen = _haal(f"{BASIS}/{LANDELIJK}/TypedDataSet")
        if rijen:
            kol, seiz = kies_kolommen(list(rijen[0].keys()))
    except Exception as e:
        print(f"Eerste ingang mislukt ({str(e)[:80]}), nu via de v4-API",
              file=sys.stderr)
        try:
            rijen, kol = _index_uit_v4(LANDELIJK)
        except Exception as e2:
            # Mislukken alle ingangen, dan moet dat in de diagnose komen. Eerder
            # liep deze fout naar buiten en stopte het script, waardoor er niets
            # werd vastgelegd en het rapport alleen "zie de stap" kon melden.
            leg_vast("woningprijzen",
                     f"Alle ingangen mislukt voor {LANDELIJK}. "
                     f"opendata.cbs.nl: {str(e)[:110]}. "
                     f"v4: {str(e2)[:110]}")
            return None
    if not rijen:
        leg_vast("woningprijzen", f"Tabel {LANDELIJK} gaf geen rijen, ook niet via "
                                  f"de v4-API op datasets.cbs.nl.")
        return None
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
        "reeks": {k: reeks[k] for k in maanden[-48:]},
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
    except Exception:
        try:
            opties = _haal_v4(REGIONAAL, "RegioSCodes")
        except Exception as e:
            leg_vast("woningprijzen", f"Regio's van {REGIONAAL} niet op te halen, "
                                      f"ook niet via de v4-API: {str(e)[:120]}")
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
    kol = None
    try:
        rijen = _haal(f"{BASIS}/{REGIONAAL}/TypedDataSet",
                      {"$filter": f"startswith(RegioS,'{sleutel}')"})
    except Exception:
        try:
            rijen = _haal(f"{BASIS}/{REGIONAAL}/TypedDataSet")
        except Exception as e:
            try:
                rijen, kol = _index_uit_v4(REGIONAAL, sleutel)
            except Exception as e2:
                leg_vast("woningprijzen",
                         f"Alle ingangen mislukt voor {REGIONAAL}. "
                         f"opendata.cbs.nl: {str(e)[:110]}. "
                         f"v4: {str(e2)[:110]}")
                return None
    rijen = [r for r in rijen if (r.get("RegioS") or "").strip() == sleutel]
    if not rijen:
        leg_vast("woningprijzen", f"Geen rijen voor {titel} ({sleutel}).")
        return None
    kol = kol or kies_kolommen(list(rijen[0].keys()))[0]
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


MINIMAAL_MAANDEN = 13


def _pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    teller = sum((a - mx) * (b - my) for a, b in zip(x, y))
    noemer = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return round(teller / noemer, 2) if noemer else None


def vergelijk(data, pad="vraagprijzen_ring.json"):
    """
    Onze vraagprijzen naast de CBS-index, met vertraging.

    Een vraagprijs komt eerder dan de transactie die het CBS telt: eerst de
    advertentie, dan het koopcontract, dan de levering bij de notaris. Als er
    een verband is, loopt onze reeks dus voor. Dat is pas te zien met ruim een
    jaar maandcijfers; daarvoor zegt een uitkomst niets en rekenen we niet.
    """
    try:
        with open(pad, encoding="utf-8") as f:
            ring = json.load(f)
    except Exception:
        return {"maanden": 0}
    maanden = sorted(ring)
    uit = {"maanden": len(maanden), "sinds": maanden[0] if maanden else None}
    reeks = ((data.get("landelijk") or {}).get("reeks")) or {}
    if len(maanden) < MINIMAAL_MAANDEN or not reeks:
        return uit

    # Jaar-op-jaar verandering van beide reeksen, zodat seizoen en niveau
    # wegvallen en we alleen de beweging vergelijken
    def jaarmutatie(paren):
        muts = {}
        for maand, waarde in paren.items():
            j, mm = maand.split("-")
            eerder = paren.get(f"{int(j) - 1}-{mm}")
            if eerder:
                muts[maand] = (waarde - eerder) / eerder * 100
        return muts

    ring_mut = jaarmutatie({m: ring[m]["mediaan_m2"] for m in maanden})
    cbs_mut = jaarmutatie(reeks)
    beste = None
    for vertraging in range(0, 7):
        paren = [(ring_mut[m], cbs_mut[vooruit])
                 for m in ring_mut
                 for vooruit in [_plus_maanden(m, vertraging)]
                 if vooruit in cbs_mut]
        if len(paren) >= MINIMAAL_MAANDEN - 1:
            r = _pearson([a for a, _b in paren], [b for _a, b in paren])
            if r is not None and (beste is None or abs(r) > abs(beste["r"])):
                beste = {"vertraging_maanden": vertraging, "r": r,
                         "waarnemingen": len(paren)}
    if beste:
        uit["beste_verband"] = beste
    return uit


def _plus_maanden(maand, n):
    j, mm = (int(x) for x in maand.split("-"))
    mm += n
    j += (mm - 1) // 12
    mm = (mm - 1) % 12 + 1
    return f"{j}-{mm:02d}"


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
    v = data.get("vergelijking") or {}
    if v.get("beste_verband"):
        b = v["beste_verband"]
        delen.append(f"Onze vraagprijzen en de CBS-index bewegen het meest samen "
                     f"als je onze reeks {b['vertraging_maanden']} maanden "
                     f"vooruitlegt (samenhang {b['r']} over {b['waarnemingen']} "
                     f"maanden). Dat is een samenhang tussen twee reeksen, geen "
                     f"bewijs dat de een de ander voorspelt")
    elif v.get("maanden"):
        delen.append(f"Onze eigen maandreeks vraagprijzen loopt sinds "
                     f"{v['sinds']} en telt {v['maanden']} maanden; een verband "
                     f"met vertraging is pas te berekenen vanaf "
                     f"{MINIMAAL_MAANDEN} maanden")
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
    def veilig(functie, naam):
        try:
            return functie()
        except Exception as e:
            leg_vast("woningprijzen", f"{naam} brak af: {type(e).__name__}: "
                                      f"{str(e)[:160]}")
            print(f"{naam} brak af: {e}", file=sys.stderr)
            return None

    data = {"landelijk": veilig(landelijk, "Landelijke reeks"),
            "regio": veilig(regio, "Regionale reeks"),
            "ingang": GEBRUIKT["ingang"]}
    data["vergelijking"] = vergelijk(data)
    data["opgehaald"] = dt.date.today().isoformat()

    # Een mislukte ophaalronde mag goede gegevens niet overschrijven.
    #
    # Dit ging op 9 oktober mis en de gevolgen reikten verder dan deze reeks.
    # Het CBS leverde die run niets, het bestand werd leeggeschreven, en daarmee
    # viel de hele WOZ-schatting om: die herleidt de vraagprijs met deze index
    # naar de waardepeildatum. Zonder factor geeft woz_schatting None, dus voor
    # elk pand zonder handmatig ingevoerde WOZ was er geen schatting meer, en de
    # ijking viel van 104 panden naar nul. In het rapport stonden dat als twee
    # losse meldingen, zonder dat iets zei dat het een oorzaak was.
    #
    # Hetzelfde principe als bij de brief: een mislukte run hoort geen goede
    # uitkomst door niets te vervangen.
    if not (data.get("landelijk") or data.get("regio")):
        try:
            with open(UIT_PAD, encoding="utf-8") as f:
                oud_bestand = json.load(f) or {}
        except Exception:
            oud_bestand = {}
        if oud_bestand.get("landelijk") or oud_bestand.get("regio"):
            oud_bestand["laatste_poging_mislukt"] = dt.date.today().isoformat()
            with open(UIT_PAD, "w", encoding="utf-8") as f:
                json.dump(oud_bestand, f, ensure_ascii=False, indent=1)
            print("LET OP: het CBS leverde nu niets. Het bestaande bestand van "
                  f"{oud_bestand.get('opgehaald', 'onbekende datum')} blijft "
                  "staan; de WOZ-schatting blijft dus werken met die reeks.",
                  file=sys.stderr)
            return 0
        print("LET OP: het CBS leverde niets en er is ook geen eerdere reeks. "
              "Daarmee valt de WOZ-schatting voor elk pand zonder eigen "
              "WOZ-waarde weg.", file=sys.stderr)

    with open(UIT_PAD, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(omschrijf(data) or "Geen woningprijsindex opgehaald", file=sys.stderr)
    for deel in ("landelijk", "regio"):
        if data.get(deel):
            print(f"  {deel}: kolom {data[deel].get('kolom')}", file=sys.stderr)


if __name__ == "__main__":
    main()
