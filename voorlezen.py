#!/usr/bin/env python3
"""
Het verhaal van de brief als geluidsbestand, met een knop bovenaan de mail.

WAAROM. 20 oktober 2026, Mark: een knop in de mail waarmee de brief wordt
voorgelezen. Een mail kan geen speler bevatten (geen scripts, meestal geen
audio), dus de knop is een link naar een MP3 op GitHub Pages, waar de kaarten
ook staan. Pages geeft hem als audio/mpeg, zodat hij in de browser speelt in
plaats van als download binnenkomt.

DE STEM. Piper (open source, draait op de runner, geen sleutel). De stemmen
komen van huggingface.co/rhasspy/piper-voices; robots.txt wordt eerst
nagekeken (stadsbeeld.mag), en daarna staat de stem in de cache van de
workflow. STEM hieronder kiest welke; `--monsters` maakt van elke Nederlandse
stem een kort fragment om te kiezen.

WAT ER VOORGELEZEN WORDT. Alleen het verhaal: de tabellen voorgelezen zijn
onverstaanbaar. Links worden hun tekst, "([straatbeeld](...))" valt weg.

UITSPRAAK, GEMETEN MET DE FONEMEN VAN ESPEAK (die Piper gebruikt), 20 oktober
op de zinnen van het verhaal van die dag:
  - "€358.000" werd "euro driehonderdachtenvijftigduizend": goed te volgen,
    maar wij zeggen het bedrag eerst. Wordt "358.000 euro".
  - "374 m2" werd "... em twee". Wordt "vierkante meter".
  - "St. Anna" werd "es tee Anna". Wordt "Sint Anna".
  - Procenten, plus en min, komma's, "CBS" en "WOZ" (letter voor letter)
    las hij zelf goed; daar is niets aan gedaan.

DE NAAM. digests/<datum>-verhaal-<8 tekens van de hash van de tekst>.mp3. Na
een herschrijving (kopie_pa.py) komt er dus een nieuw bestand en wijst de knop
in pa's mail nooit naar de stem van een eerdere versie, ook niet uit een cache.
Oudere MP3's dan BEWAAR_DAGEN gaan uit de werkmap (opruimen); de git-
geschiedenis houdt ze wel, ongeveer een megabyte per dag.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

STEM = "nl_NL-mls-medium"
SPREKER = None          # bij een stem met meer sprekers: welke; None is de eerste
BASIS = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
CACHE = os.path.expanduser("~/.cache/piper-stemmen")
BEWAAR_DAGEN = 14
STILTE_ALINEA = 0.6     # seconden tussen alinea's
KBPS = 32


def tekst(verhaal):
    """Het verhaal als voor te lezen tekst, een alinea per element."""
    t = verhaal or ""
    t = re.sub(r" \(\[straatbeeld\]\([^)]*\)\)", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"^#+\s*", "", t, flags=re.M)
    # Bedragen: het getal eerst, dan "euro".
    t = re.sub(r"€\s?(\d[\d.,]*\d|\d)", r"\1 euro", t)
    t = re.sub(r"(\d)\s?(m2|m²)\b", r"\1 vierkante meter", t)
    t = re.sub(r"(\d)\s?(m3|m³)\b", r"\1 kubieke meter", t)
    t = re.sub(r"\bSt\. ", "Sint ", t)
    alineas = []
    for a in re.split(r"\n\s*\n", t):
        a = " ".join(a.split())
        if not a or re.fullmatch(r"-{3,}|\*{3,}", a):
            continue
        alineas.append(a)
    return alineas


def naam(datum, verhaal):
    h = hashlib.sha256("\n\n".join(tekst(verhaal)).encode("utf-8")).hexdigest()
    return f"{datum}-verhaal-{h[:8]}.mp3"


def _haal(pad_op_server, doel):
    import requests
    import stadsbeeld
    url = BASIS + pad_op_server
    ok, reden = stadsbeeld.mag(url)
    if not ok:
        raise RuntimeError(f"{url}: {reden or 'robots.txt niet nagekeken'}")
    r = requests.get(url, timeout=120,
                     headers={"User-Agent": stadsbeeld.AGENT})
    r.raise_for_status()
    os.makedirs(os.path.dirname(doel), exist_ok=True)
    with open(doel + ".deel", "wb") as f:
        f.write(r.content)
    os.replace(doel + ".deel", doel)


def stemmen():
    """voices.json van piper-voices, uit de cache of opgehaald."""
    pad = os.path.join(CACHE, "voices.json")
    if not os.path.exists(pad):
        _haal("voices.json", pad)
    with open(pad, encoding="utf-8") as f:
        return json.load(f)


def stem_laden(stem=STEM):
    from piper import PiperVoice
    onnx = os.path.join(CACHE, stem + ".onnx")
    if not (os.path.exists(onnx) and os.path.exists(onnx + ".json")):
        info = stemmen()[stem]
        for pad in info["files"]:
            if pad.endswith(".onnx"):
                _haal(pad, onnx)
            elif pad.endswith(".onnx.json"):
                _haal(pad, onnx + ".json")
    return PiperVoice.load(onnx)


def spreek(alineas, uit, stem=STEM, spreker=SPREKER):
    """De alinea's naar een MP3. Geeft de duur in seconden.

    MP3 via lameenc (een wheel met LAME erin) en niet via ffmpeg: ffmpeg staat
    niet op ubuntu-latest. De eerste proef op 20 oktober liep daarop vast, bij
    alle tien stemmen, nadat de stemmen wel waren opgehaald."""
    import lameenc
    from piper import SynthesisConfig
    v = stem_laden(stem)
    cfg = SynthesisConfig(speaker_id=spreker)
    rate = v.config.sample_rate
    pcm = bytearray()
    stil = b"\0\0" * int(rate * STILTE_ALINEA)
    for a in alineas:
        for stuk in v.synthesize(a, syn_config=cfg):
            pcm += stuk.audio_int16_bytes
        pcm += stil
    enc = lameenc.Encoder()
    enc.set_bit_rate(KBPS)
    enc.set_in_sample_rate(rate)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(bytes(pcm)) + enc.flush()
    with open(uit + ".deel", "wb") as f:
        f.write(data)
    os.replace(uit + ".deel", uit)
    return len(pcm) / 2 / rate


def opruimen(datum, map_="digests", dagen=BEWAAR_DAGEN):
    """MP3's ouder dan `dagen` uit de werkmap. Geeft de verwijderde namen."""
    import datetime as dt
    grens = dt.date.fromisoformat(datum) - dt.timedelta(days=dagen)
    weg = []
    for n in sorted(os.listdir(map_)):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-verhaal-[0-9a-f]{8}\.mp3$", n)
        if m and dt.date.fromisoformat(m.group(1)) < grens:
            os.remove(os.path.join(map_, n))
            weg.append(n)
    return weg


def maak(datum, map_="digests"):
    """De MP3 bij het verhaal van `datum`. Geeft de bestandsnaam of None."""
    pad = os.path.join(map_, f"{datum}-verhaal.md")
    if not os.path.exists(pad):
        print(f"Geen verhaal voor {datum}; niets voor te lezen", file=sys.stderr)
        return None
    with open(pad, encoding="utf-8") as f:
        verhaal = f.read()
    alineas = tekst(verhaal)
    if not alineas:
        print("Het verhaal is leeg; niets voor te lezen", file=sys.stderr)
        return None
    n = naam(datum, verhaal)
    uit = os.path.join(map_, n)
    if not os.path.exists(uit):
        duur = spreek(alineas, uit)
        print(f"Voorgelezen: {n}, {duur / 60:.1f} minuten, "
              f"{os.path.getsize(uit) / 1e6:.2f} MB, stem {STEM}",
              file=sys.stderr)
    for w in opruimen(datum, map_):
        print(f"Opgeruimd: {w}", file=sys.stderr)
    return n


def bestaande(datum, verhaal, map_="digests"):
    """De naam van de MP3 die bij precies dit verhaal hoort, als hij er is."""
    if not verhaal or not verhaal.strip():
        return None
    n = naam(datum, verhaal)
    return n if os.path.exists(os.path.join(map_, n)) else None


def knop(datum, verhaal, map_="digests", omgeving=None):
    """De html van de knop bovenaan de mail, of een lege string.

    Leeg als er geen MP3 bij precies dit verhaal is, of als de repo prive is
    (dan geeft Pages een 404; zie kaartlink.py). Een knop die niet speelt is
    erger dan geen knop."""
    import kaartlink
    n = bestaande(datum, verhaal, map_)
    if not n or kaartlink.prive(omgeving):
        return ""
    return ('<p><a href="' + kaartlink.url("digests/" + n) + '" style="'
            'display:inline-block;padding:10px 18px;border-radius:6px;'
            'background:#1f4e79;color:#ffffff;text-decoration:none;'
            'font-weight:bold">&#9654; Beluister de brief</a></p>')


def monsters(uit_map, verhaal_pad):
    """Van elke Nederlandse stem de eerste twee alinea's, om te kiezen."""
    with open(verhaal_pad, encoding="utf-8") as f:
        alineas = tekst(f.read())[:3]
    os.makedirs(uit_map, exist_ok=True)
    regels = []
    for stem, info in sorted(stemmen().items()):
        if not stem.startswith("nl_"):
            continue
        sprekers = info.get("num_speakers", 1)
        try:
            duur = spreek(alineas, os.path.join(uit_map, stem + ".mp3"),
                          stem=stem, spreker=0 if sprekers > 1 else None)
            regels.append(f"{stem}: {duur:.0f} s, {sprekers} spreker(s)")
        except Exception as e:
            regels.append(f"{stem}: MISLUKT {type(e).__name__}: {str(e)[:120]}")
    with open(os.path.join(uit_map, "LEESMIJ.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(regels) + "\n")
    print("\n".join(regels), file=sys.stderr)
    return 0


def proef():
    afw = []
    v = ("# Vastgoed in Nijmegen, 20 oktober 2026\n\nGoedemiddag pa,\n\n"
         "Op de [Graafseweg 18](https://x/gmb.html) ([straatbeeld]"
         "(https://www.google.com/maps/@?api=1&x=1)) naast de woning van "
         "374 m2. Een **WOZ** van €358.000 in St. Anna.\n\n---\n\n"
         "**Wist je dat** iets?\n")
    a = tekst(v)
    verwacht = ["Vastgoed in Nijmegen, 20 oktober 2026", "Goedemiddag pa,",
                "Op de Graafseweg 18 naast de woning van 374 vierkante meter. "
                "Een WOZ van 358.000 euro in Sint Anna.",
                "Wist je dat iets?"]
    if a != verwacht:
        afw.append(f"de voor te lezen tekst klopt niet: {a!r}")
    if naam("2026-10-20", v) != naam("2026-10-20", v.replace("\n\n", "\n\n\n")):
        afw.append("een andere witregel geeft een andere MP3")
    if naam("2026-10-20", v) == naam("2026-10-20", v.replace("374", "375")):
        afw.append("een herschreven verhaal houdt dezelfde MP3-naam")
    with tempfile.TemporaryDirectory() as m:
        for n in ["2026-10-01-verhaal-0123abcd.mp3",
                  "2026-10-10-verhaal-0123abcd.mp3", "2026-10-01-verhaal.md"]:
            open(os.path.join(m, n), "w").close()
        weg = opruimen("2026-10-20", m, 14)
        if weg != ["2026-10-01-verhaal-0123abcd.mp3"]:
            afw.append(f"het opruimen haalt het verkeerde weg: {weg}")
    with tempfile.TemporaryDirectory() as m:
        open(os.path.join(m, naam("2026-10-20", v)), "w").close()
        open_ = {"REPO_PRIVE": "false"}
        k = knop("2026-10-20", v, m, open_)
        if "digests/" + naam("2026-10-20", v) not in k:
            afw.append("de knop wijst niet naar de MP3 van dit verhaal")
        if knop("2026-10-20", v, m, {"REPO_PRIVE": "true"}):
            afw.append("een prive repo krijgt toch een knop")
        if knop("2026-10-20", v.replace("374", "375"), m, open_):
            afw.append("een herschreven verhaal krijgt de knop van de vorige versie")
    for x in afw:
        print("AFWIJKING: " + x, file=sys.stderr)
    print(f"Proef voorlezen: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


def main():
    import datetime as dt
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--datum",
                    default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--monsters", metavar="MAP")
    ap.add_argument("--verhaal", help="voor --monsters: welk verhaal")
    a = ap.parse_args()
    if a.proef:
        return proef()
    if a.monsters:
        return monsters(a.monsters, a.verhaal
                        or os.path.join("digests", f"{a.datum}-verhaal.md"))
    try:
        return 0 if maak(a.datum) else 1
    except Exception as e:
        print(f"LET OP: voorlezen mislukt: {type(e).__name__}: {e}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
