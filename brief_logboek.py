#!/usr/bin/env python3
"""
Wat lag er vandaag op tafel, en wat is ervan verteld?

Het probleem dat dit oplost: op een drukke dag zijn er meer onderwerpen dan er
in een brief passen. Wat niet gekozen wordt, verdwijnt nu geruisloos, en de
volgende dag weet niemand meer dat het er was.

Wat dit bewust NIET is: een wachtrij. Een onderwerp dat drie dagen wacht, is
vaak alleen nog waar en geen nieuws meer. Zou de brief kiezen op leeftijd in
plaats van op nieuwswaarde, dan opent hij met iets van vorige week terwijl het
nieuws van vandaag eronder ligt. Dat is dezelfde fout die de BAG-wachtrij liet
vastlopen: daar vulden de oudste panden de quota en kwamen de nieuwe nooit aan
de beurt.

Het logboek dient twee doelen:
- bij het schrijven mag de brief iets van eerder oppakken, maar alleen als er
  iets nieuws bij is gekomen, zoals een besluit op een eerdere aanvraag;
- in de weekeditie loop je na wat er is gepasseerd zonder dat het aan bod kwam.

TESTRUNS SCHRIJVEN HIER NIETS. Een handmatige oefenrun mag nooit een onderwerp
markeren als verteld; dan mist de echte brief van de volgende ochtend het.
Dezelfde bescherming als bij de artikelen en de weetjes.
"""
import datetime as dt
import json
import os
import sys

PAD = "brief_logboek.json"
BEWAAR_DAGEN = 60


def _alleen_lezen():
    """Draait dit een testrun? Dan niets wegschrijven."""
    try:
        from diagnose import alleen_lezen
        return alleen_lezen()
    except Exception:
        # Bij twijfel niets wegschrijven: een gemiste regel in het logboek is
        # onschuldig, een onterecht afgestreept onderwerp niet.
        return bool(os.environ.get("TESTRUN"))


def lees(pad=PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f) or {"dagen": []}
    except Exception:
        return {"dagen": []}


def leg_vast(gekozen, overgeslagen, pad=PAD, datum=None):
    """
    De keuze van vandaag vastleggen.

    gekozen is het onderwerp waar de brief mee opent; overgeslagen is een lijst
    met wat er verder lag. Allebei korte omschrijvingen, geen hele teksten.
    """
    if _alleen_lezen():
        print("Testrun: het logboek blijft ongewijzigd", file=sys.stderr)
        return False
    datum = datum or dt.date.today().isoformat()
    boek = lees(pad)
    dagen = [d for d in boek.get("dagen", []) if d.get("datum") != datum]
    dagen.append({"datum": datum, "gekozen": gekozen,
                  "overgeslagen": list(overgeslagen or [])})
    # Oud opruimen: na twee maanden is een niet-behandeld onderwerp geen
    # gemiste kans meer maar geschiedenis.
    grens = (dt.date.today() - dt.timedelta(days=BEWAAR_DAGEN)).isoformat()
    dagen = [d for d in dagen if d.get("datum", "") >= grens]
    try:
        with open(pad, "w", encoding="utf-8") as f:
            json.dump({"dagen": sorted(dagen, key=lambda d: d["datum"])},
                      f, ensure_ascii=False, indent=1)
        return True
    except Exception as e:
        print(f"Logboek niet weggeschreven: {str(e)[:80]}", file=sys.stderr)
        return False


def niet_behandeld(dagen=7, pad=PAD):
    """Wat er de afgelopen dagen lag zonder dat het aan bod kwam."""
    grens = (dt.date.today() - dt.timedelta(days=dagen)).isoformat()
    uit = []
    for dag in lees(pad).get("dagen", []):
        if dag.get("datum", "") < grens:
            continue
        for onderwerp in dag.get("overgeslagen", []):
            uit.append({"datum": dag["datum"], "onderwerp": onderwerp})
    return uit


def tekst_voor_week(dagen=7, pad=PAD):
    """Een blokje voor de weekeditie: wat bleef er liggen."""
    rest = niet_behandeld(dagen, pad)
    if not rest:
        return ""
    regels = ["**Wat deze week bleef liggen.** Deze onderwerpen kwamen voorbij "
              "zonder dat er in een brief iets over is gezegd:"]
    for r in rest[:12]:
        regels.append(f"- {r['datum']}: {r['onderwerp']}")
    return "\n".join(regels)
