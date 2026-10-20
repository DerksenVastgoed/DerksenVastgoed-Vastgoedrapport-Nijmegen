#!/usr/bin/env python3
"""
Eén aanroep naar het taalmodel voor de hele repo.

WAAROM. 20 oktober 2026 ging de brief zonder verhaal uit. brief_verhalend.py
meldde "Brief geschreven: 16000 tokens, 0 woorden" en stop_reason max_tokens.
Claude Sonnet 5 denkt standaard (adaptief, effort "high"), en die denktokens
tellen mee in max_tokens: "max_tokens is a hard cap on total output for the
request, thinking and response text combined" (platform.claude.com, Adaptive
thinking). Het denken at de hele ruimte op en er kwam geen tekst. De code
voegde alleen de tekstblokken samen en zag dus niets, behalve nul woorden.

Dezelfde aanroep stond op zes plekken in vier bestanden, elk met een eigen
max_tokens (3000 tot 16000) en zonder effort. Nu staat hij hier:
  - effort wordt meegegeven (output_config.effort);
  - per aanroep wordt gemeld hoeveel tokens er naar denken gingen;
  - komt er geen tekst terug omdat de limiet op was, dan nog een keer met de
    dubbele ruimte en een stap lagere effort, en dat wordt gemeld;
  - weigert de API het veld output_config (400), dan nog een keer zonder,
    want dan is een brief zonder sturing beter dan geen brief.

Bronnen: platform.claude.com/docs/en/build-with-claude/effort,
.../adaptive-thinking, .../thinking-troubleshooting,
.../models/sonnet-5/whats-new-sonnet-5.
"""
import os
import sys
import time

URL = "https://api.anthropic.com/v1/messages"
LAGER = {"max": "high", "xhigh": "high", "high": "medium", "medium": "low",
         "low": "low"}
MAX_RUIMTE = 64000


class Antwoord:
    def __init__(self, tekst="", stop=None, uit=0, denken=0, blokken=None,
                 fout=None, pogingen=None):
        self.tekst = tekst
        self.stop = stop
        self.uit = uit            # output_tokens, denken inbegrepen
        self.denken = denken      # thinking_tokens, of 0 als niet gemeld
        self.blokken = blokken or []
        self.fout = fout
        self.pogingen = pogingen or []

    def regel(self, label=""):
        woorden = len(self.tekst.split())
        return (f"{label + ': ' if label else ''}{self.uit} tokens, waarvan "
                f"{self.denken} denken, {woorden} woorden, stop {self.stop}"
                + (f", blokken {','.join(self.blokken)}" if not woorden else "")
                + (f"; pogingen: {' | '.join(self.pogingen)}"
                   if len(self.pogingen) > 1 else ""))


def _lees(body):
    blokken = body.get("content") or []
    tekst = "".join(b.get("text", "") for b in blokken
                    if b.get("type", "text") == "text").strip()
    usage = body.get("usage") or {}
    denken = ((usage.get("output_tokens_details") or {}).get("thinking_tokens")
              or 0)
    return Antwoord(tekst, body.get("stop_reason"),
                    usage.get("output_tokens") or 0, denken,
                    [str(b.get("type")) for b in blokken])


def vraag(model, system, berichten, max_tokens, effort="medium",
          timeout=120, label="", post=None, sleutel=None, herhaal_netwerk=1):
    """Stelt de vraag en geeft een Antwoord. Gooit niet; bij een fout staat
    die in .fout en is .tekst leeg."""
    if post is None:
        import requests
        post = requests.post
    sleutel = sleutel if sleutel is not None else \
        os.environ.get("ANTHROPIC_API_KEY", "")
    ruimte, inspanning, met_effort = max_tokens, effort, bool(effort)
    log = []
    antwoord = Antwoord()
    for _ronde in range(4):
        body = {"model": model, "max_tokens": ruimte, "system": system,
                "messages": berichten}
        if met_effort and inspanning:
            body["output_config"] = {"effort": inspanning}
        resp, fout = None, None
        for netwerk in range(herhaal_netwerk):
            try:
                resp = post(URL, headers={"x-api-key": sleutel,
                                          "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"},
                            json=body, timeout=timeout)
                # Overbelast of tijdelijk weg: dat is net als een netwerkfout
                # een reden om het nog eens te proberen.
                if resp.status_code in (429, 500, 502, 503, 529) and \
                        netwerk + 1 < herhaal_netwerk:
                    fout = f"HTTP {resp.status_code}"
                    resp = None
                    time.sleep((netwerk + 1) * 10)
                    continue
                break
            except Exception as e:
                fout = f"{type(e).__name__}: {str(e)[:120]}"
                if netwerk + 1 < herhaal_netwerk:
                    time.sleep((netwerk + 1) * 10)
        if resp is None:
            log.append(f"netwerk: {fout}")
            antwoord = Antwoord(fout=fout, pogingen=log)
            break
        if resp.status_code == 400 and met_effort and \
                ("output_config" in resp.text or "effort" in resp.text):
            log.append("400 op output_config; opnieuw zonder effort")
            met_effort = False
            continue
        if resp.status_code >= 400:
            fout = f"HTTP {resp.status_code}: {resp.text[:200]}"
            log.append(fout)
            antwoord = Antwoord(fout=fout, pogingen=log)
            break
        antwoord = _lees(resp.json())
        log.append(f"max_tokens {ruimte}, effort "
                   f"{inspanning if met_effort else 'standaard'}: "
                   f"{antwoord.uit} tokens, {antwoord.denken} denken, "
                   f"{len(antwoord.tekst.split())} woorden")
        antwoord.pogingen = log
        if antwoord.tekst or antwoord.stop != "max_tokens" or \
                ruimte >= MAX_RUIMTE:
            break
        # Geen tekst omdat de limiet op was: meer ruimte en minder denken.
        ruimte = min(MAX_RUIMTE, ruimte * 2)
        if met_effort:
            inspanning = LAGER.get(inspanning or "high", "low")
    if label:
        regel = (antwoord.regel(label) if not antwoord.fout
                 else f"{label}: mislukt, {antwoord.fout}")
        print(regel, file=sys.stderr)
        # OOK IN DE REPO. Het joblogboek is van buiten de runner niet te
        # lezen; diagnose/ wordt teruggecommit. Zo is na een week te zien
        # hoeveel de brief denkt en of de tweede poging nodig was.
        try:
            if os.path.isdir("diagnose"):
                import datetime as _dt
                with open(os.path.join("diagnose", "taalmodel.txt"), "a",
                          encoding="utf-8") as f:
                    f.write(f"{_dt.date.today().isoformat()} {model} "
                            f"{regel}\n")
        except OSError:
            pass
    return antwoord


def proef():
    afw = []

    class Resp:
        def __init__(self, status, body=None, tekst=""):
            self.status_code, self._b, self.text = status, body, tekst

        def json(self):
            return self._b

    def nep(antwoorden):
        verzonden = []

        def post(url, headers=None, json=None, timeout=None):
            verzonden.append(json)
            return antwoorden.pop(0)
        return post, verzonden

    # DE FOUT VAN 20 OKTOBER: alleen denken, limiet op, geen tekst. Dan nog
    # een keer met dubbele ruimte en lagere effort, en die tekst komt terug.
    leeg = {"content": [{"type": "thinking", "thinking": ""}],
            "stop_reason": "max_tokens",
            "usage": {"output_tokens": 16000,
                      "output_tokens_details": {"thinking_tokens": 16000}}}
    goed = {"content": [{"type": "thinking", "thinking": ""},
                        {"type": "text", "text": "Een brief van vier woorden."}],
            "stop_reason": "end_turn",
            "usage": {"output_tokens": 9000,
                      "output_tokens_details": {"thinking_tokens": 8000}}}
    post, verzonden = nep([Resp(200, leeg), Resp(200, goed)])
    a = vraag("m", "s", [], 16000, effort="high", post=post, sleutel="x")
    if a.tekst != "Een brief van vier woorden." or len(verzonden) != 2:
        afw.append(f"een antwoord met alleen denken wordt niet opnieuw "
                   f"gevraagd: {a.tekst!r}, {len(verzonden)} aanroepen")
    elif verzonden[1]["max_tokens"] != 32000 or \
            verzonden[1]["output_config"]["effort"] != "medium":
        afw.append(f"de tweede poging krijgt niet meer ruimte en minder "
                   f"denken: {verzonden[1]}")
    if "8000 denken" not in a.regel() and "waarvan 8000 denken" not in \
            a.regel():
        afw.append(f"het aantal denktokens wordt niet gemeld: {a.regel()}")
    # Alleen tekstblokken tellen, ook als een denkblok een tekstveld heeft.
    post, _ = nep([Resp(200, {"content": [
        {"type": "thinking", "thinking": "x", "text": "NIET"},
        {"type": "text", "text": "wel"}], "stop_reason": "end_turn",
        "usage": {"output_tokens": 5}})])
    if vraag("m", "s", [], 100, post=post, sleutel="x").tekst != "wel":
        afw.append("tekst uit een denkblok komt in de brief")
    # Weigert de API output_config, dan zonder.
    post, verzonden = nep([Resp(400, None, '{"error": "output_config: '
                                           'unknown field"}'),
                           Resp(200, goed)])
    a = vraag("m", "s", [], 1000, effort="medium", post=post, sleutel="x")
    if not a.tekst or "output_config" in verzonden[1]:
        afw.append("een 400 op output_config wordt niet zonder herhaald")
    # Overbelast: opnieuw als er pogingen over zijn (zonder te wachten in de
    # proef).
    _slaap = time.sleep
    try:
        time.sleep = lambda s: None
        post, verzonden = nep([Resp(529, None, "overloaded"), Resp(200, goed)])
        a = vraag("m", "s", [], 1000, post=post, sleutel="x",
                  herhaal_netwerk=3)
    finally:
        time.sleep = _slaap
    if not a.tekst or len(verzonden) != 2:
        afw.append("een overbelaste API wordt niet opnieuw geprobeerd")
    # Een andere fout is een fout, zonder herhaling en zonder tekst.
    post, verzonden = nep([Resp(500, None, "overloaded")])
    a = vraag("m", "s", [], 1000, post=post, sleutel="x")
    if a.tekst or not a.fout or len(verzonden) != 1:
        afw.append("een serverfout wordt niet als fout teruggegeven")
    for x in afw:
        print("AFWIJKING: " + x, file=sys.stderr)
    print(f"Proef taalmodel: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


if __name__ == "__main__":
    sys.exit(proef() if "--proef" in sys.argv else 0)
