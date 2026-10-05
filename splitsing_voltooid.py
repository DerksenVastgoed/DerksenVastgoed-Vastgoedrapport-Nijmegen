#!/usr/bin/env python3
"""
Welke panden werkelijk zijn opgedeeld, gezien in de BAG.

Een vergunning zegt dat het mág. De BAG zegt dat het gebeurd ís: zodra het
aantal woningen met een eigen adres in een pand omhoog gaat, zijn de nieuwe
eenheden geregistreerd. Dat is het enige harde bewijs van een voltooide
splitsing dat we hebben, en het komt uit een registratie en niet uit een
advertentie.

Drie dingen vallen daaruit af te leiden:

1. De doorlooptijd van besluit tot registratie. Hoe lang duurt het werkelijk
   voordat een vergund pand ook een opgedeeld pand is? Dat is een getal dat
   nergens te vinden is en dat elke ontwikkelcase nodig heeft.
2. Splitsingen zonder bekende vergunning. Dan hebben we de bekendmaking gemist,
   of het is zonder vergunning gegaan. Allebei interessant.
3. Vergunningen die niet tot een splitsing hebben geleid. Verleend, en daarna
   gebeurt er niets; dat zegt iets over hoe haalbaar zo'n plan in de praktijk is.

Beperking die erbij hoort: het aantal woningen wordt alleen bij een volledige
ronde opnieuw opgehaald, dus wekelijks. Een splitsing is daarmee hooguit een
week na registratie zichtbaar, en een pand dat voor eind september is opgedeeld
zien we helemaal niet, want toen begonnen we pas met meten.
"""
import argparse
import datetime as dt
import json
import re
import sys

UIT_PAD = "splitsingen.json"
# Woorden die op woningvorming wijzen. "Omzetten" staat er bewust niet bij:
# dat is kamerverhuur en dat is iets anders.
SPLITS_WOORDEN = ("splits", "woningvorming", "zelfstandige woningen",
                  "appartementen", "appartementsrechten", "opdelen",
                  "verbouwen van een woning naar", "naar twee woningen",
                  "naar drie woningen")


def _is_splitsing(tekst):
    laag = (tekst or "").lower()
    return any(w in laag for w in SPLITS_WOORDEN)


def _aantallen(tekst):
    """Uit 'de BAG telt nu 3 woningen in dit pand, was 1' komt (1, 3)."""
    m = re.search(r"telt nu (\d+) woningen in dit pand, was (\d+)", tekst or "")
    if not m:
        return None
    return int(m.group(2)), int(m.group(1))


def _dagen(van, tot):
    try:
        return (dt.date.fromisoformat(tot[:10])
                - dt.date.fromisoformat(van[:10])).days
    except Exception:
        return None


def zoek(geschiedenis):
    """
    Per pand: is het aantal woningen omhooggegaan, en was er een vergunning?

    De vergunning mag van voor de registratie zijn; een besluit dat erna komt
    hoort niet bij deze splitsing en telt dus niet mee.
    """
    gerealiseerd, zonder_vergunning, vergund_niets = [], [], []
    for pand in geschiedenis.values():
        if not isinstance(pand, dict):
            continue
        gebeurtenissen = sorted(pand.get("gebeurtenissen") or [],
                                key=lambda g: g.get("datum") or "")
        groei = [(g["datum"], _aantallen(g.get("tekst")))
                 for g in gebeurtenissen if g.get("soort") == "bag"]
        groei = [(d, a) for d, a in groei if a and a[1] > a[0]]
        besluiten = [g for g in gebeurtenissen
                     if g.get("soort") in ("bekendmaking", "kamerverhuur")
                     and _is_splitsing(g.get("tekst"))
                     and "besluit" in (g.get("tekst") or "").lower()]
        aanvragen = [g for g in gebeurtenissen
                     if g.get("soort") == "bekendmaking"
                     and _is_splitsing(g.get("tekst"))
                     and "aanvraag" in (g.get("tekst") or "").lower()]

        if groei:
            datum, (van, naar) = groei[-1]
            eerder = [b for b in besluiten if b["datum"] <= datum]
            rij = {"adres": pand.get("adres"), "datum": datum,
                   "van": van, "naar": naar}
            if eerder:
                rij["besluit"] = eerder[-1]["datum"]
                rij["dagen_na_besluit"] = _dagen(eerder[-1]["datum"], datum)
                rij["tekst"] = eerder[-1].get("tekst", "")[:160]
                gerealiseerd.append(rij)
            else:
                # Geen besluit gevonden voor de registratie. Dat betekent niet
                # dat er geen vergunning was: wij zien alleen wat is
                # gepubliceerd, en pas sinds 2012.
                rij["aanvraag"] = aanvragen[-1]["datum"] if aanvragen else None
                zonder_vergunning.append(rij)
        elif besluiten:
            # Vergund, maar in de BAG is er niets veranderd. Interessant zodra
            # het lang genoeg geleden is; daaronder is het gewoon nog in
            # uitvoering.
            laatste = besluiten[-1]
            dagen = _dagen(laatste["datum"], dt.date.today().isoformat())
            if dagen and dagen > 365:
                vergund_niets.append({
                    "adres": pand.get("adres"), "besluit": laatste["datum"],
                    "dagen": dagen, "tekst": laatste.get("tekst", "")[:160]})

    for rij in (gerealiseerd, zonder_vergunning, vergund_niets):
        rij.sort(key=lambda r: r.get("datum") or r.get("besluit") or "",
                 reverse=True)
    uit = {"gerealiseerd": gerealiseerd,
           "zonder_bekende_vergunning": zonder_vergunning,
           "vergund_maar_niets_gebeurd": vergund_niets}
    looptijden = [r["dagen_na_besluit"] for r in gerealiseerd
                  if r.get("dagen_na_besluit") is not None
                  and 0 <= r["dagen_na_besluit"] < 3000]
    if looptijden:
        looptijden.sort()
        uit["mediaan_dagen_besluit_tot_bag"] = looptijden[len(looptijden) // 2]
        uit["aantal_looptijden"] = len(looptijden)
    return uit


def tekst(uit):
    """Een blok voor de bijlage. Alleen wat er werkelijk is, geen kopjes leeg."""
    r = []
    ger = uit.get("gerealiseerd") or []
    if ger:
        r.append("## Splitsingen die de BAG inmiddels telt")
        r.append("")
        r.append("_Een vergunning zegt dat het mag; de BAG zegt dat het is "
                 "gebeurd. Zodra het aantal woningen met een eigen adres omhoog "
                 "gaat, staan de nieuwe eenheden geregistreerd._")
        r.append("")
        for rij in ger[:8]:
            deel = (f"- **{rij['adres']}**: van {rij['van']} naar "
                    f"{rij['naar']} woningen, gezien op {rij['datum']}")
            if rij.get("dagen_na_besluit") is not None:
                deel += (f", {rij['dagen_na_besluit']} dagen na het besluit van "
                         f"{rij['besluit']}")
            r.append(deel + ".")
        if uit.get("mediaan_dagen_besluit_tot_bag"):
            r.append("")
            r.append(f"_Mediane tijd tussen besluit en registratie: "
                     f"{uit['mediaan_dagen_besluit_tot_bag']} dagen, gemeten op "
                     f"{uit['aantal_looptijden']} panden._")
        r.append("")
    zon = uit.get("zonder_bekende_vergunning") or []
    if zon:
        r.append("## Opgedeeld zonder dat wij een vergunning kennen")
        r.append("")
        r.append("_Dat bewijst niets: we zien alleen wat is gepubliceerd, en "
                 "pas sinds 2012. Het is wel een aanwijzing dat er een route is "
                 "die wij missen._")
        r.append("")
        for rij in zon[:5]:
            r.append(f"- **{rij['adres']}**: van {rij['van']} naar "
                     f"{rij['naar']} woningen, gezien op {rij['datum']}.")
        r.append("")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=UIT_PAD)
    ap.add_argument("--tekst", default="")
    args = ap.parse_args()
    try:
        from pandlezer import laad
        geschiedenis = laad("pandgeschiedenis.json")
    except Exception as e:
        print(f"Geschiedenis niet te lezen: {str(e)[:80]}", file=sys.stderr)
        return 0
    uit = zoek(geschiedenis)
    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False, indent=1)
    if args.tekst:
        blok = tekst(uit)
        if blok:
            with open(args.tekst, "w", encoding="utf-8") as f:
                f.write(blok)
    print(f"Splitsingen: {len(uit['gerealiseerd'])} gerealiseerd, "
          f"{len(uit['zonder_bekende_vergunning'])} zonder bekende vergunning, "
          f"{len(uit['vergund_maar_niets_gebeurd'])} vergund zonder resultaat",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
