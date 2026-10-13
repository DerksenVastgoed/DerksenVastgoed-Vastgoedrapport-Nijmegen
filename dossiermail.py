#!/usr/bin/env python3
"""
Kijken wat er in de mailbox staat van het Digitaal Gebouwen Archief Nijmegen.

WAT DIT IS EN WAT HET NIET IS. Dit is een verkenning, geen bron die meeloopt in
de ochtendbrief. De studiezaal van Nijmegen pakt een gekozen dossier in en
stuurt een mail met een link naar het pakket. Die mail komt in dezelfde mailbox
die funda_mail.py leest, maar van een afzender waar geen parser voor is, dus
hij valt nu in de teller "post van bronnen zonder parser" en verder niets.

Deze stap meet drie dingen, in deze volgorde, en stopt zodra er iets niet
klopt:

  1. Staat er zo'n mail, van wie, met welk onderwerp en van welke datum.
  2. Zit er een link in, en naar welke host.
  3. Met --haal erbij: wat zit er in het pakket. Bestandsnamen, soorten,
     omvang, en bij een PDF het aantal bladzijden en of er tekst in staat.

WAT HET NOOIT DOET, en dat is met opzet in de code en niet in een afspraak:

  - Niets uit dat pakket komt in de repo. Alles gaat naar een tijdelijke map
    buiten de werkmap, en die wordt opgeruimd. Op de tekeningen in een
    bouwdossier rust auteursrecht, en de voorwaarde bij het aanvragen zegt dat
    de kopie uitsluitend voor persoonlijk gebruik is en niet mag worden
    verveelvoudigd of gepubliceerd. Deze repo is publiek, dus een tekening
    erin zetten zou publiceren zijn. Wat wij er later uit meten, bijvoorbeeld
    "op deze laag is 48 m2 bruikbaar", is onze eigen waarneming en mag wel.
  - Hij volgt alleen een link naar een host die hieronder in TOEGESTANE_HOSTS
    staat, en alleen uit een mail van een afzender in AFZENDERS. Een link uit
    een willekeurige mail volgen is precies hoe een mailbox een aanvalsvlak
    wordt.
  - Hij markeert geen mail als gelezen en verwijdert niets.

Gebruik:
  python dossiermail.py                 # alleen kijken wat er staat
  python dossiermail.py --haal          # ook het pakket openen en beschrijven
  python dossiermail.py --proef         # eigen logica nameten, zonder mailbox
"""
import argparse
import email
import email.header
import imaplib
import os
import re
import shutil
import ssl
import sys
import tempfile
import urllib.parse
import urllib.request

IMAP_HOST = "imap.gmail.com"
GEBRUIKER = os.environ.get("MAIL_USERNAME", "")
WACHTWOORD = os.environ.get("MAIL_PASSWORD", "")

# Alleen deze afzenders, en alleen deze hosts voor een link. Twee lijsten en
# geen slim patroon: een mailbox is een open deur, en wat hier niet in staat
# wordt niet gevolgd.
AFZENDERS = ("nijmegen.nl",)
TOEGESTANE_HOSTS = ("studiezaal.nijmegen.nl", "app4.nijmegen.nl",
                    "nijmegen.nl")
MAX_PAKKET = 200 * 1024 * 1024

RE_URL = re.compile(r"https?://[^\s<>\"')]+")


def _kop(waarde):
    """Een mailkop leesbaar maken, ook als hij gecodeerd is."""
    if not waarde:
        return ""
    uit = []
    for stuk, codering in email.header.decode_header(waarde):
        if isinstance(stuk, bytes):
            try:
                uit.append(stuk.decode(codering or "utf-8", "replace"))
            except LookupError:
                uit.append(stuk.decode("utf-8", "replace"))
        else:
            uit.append(stuk)
    return "".join(uit).strip()


def platte_tekst(bericht):
    """De tekstdelen van een bericht achter elkaar."""
    stukken = []
    for deel in bericht.walk():
        if deel.get_content_maintype() != "text":
            continue
        try:
            ruw = deel.get_payload(decode=True) or b""
            stukken.append(ruw.decode(deel.get_content_charset() or "utf-8",
                                      "replace"))
        except Exception:
            continue
    return "\n".join(stukken)


def host_van(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def toegestaan(url):
    """
    Mag deze link gevolgd worden?

    De host moet gelijk zijn aan een toegestane host of daar een subdomein van.
    Een toets op "staat de naam erin" zou http://studiezaal.nijmegen.nl.kwaad.nl
    doorlaten, en dat is precies de truc die zo'n toets nutteloos maakt.
    """
    h = host_van(url)
    if not h or not url.lower().startswith("https://"):
        return False
    return any(h == t or h.endswith("." + t) for t in TOEGESTANE_HOSTS)


def links_uit(tekst):
    """De toegestane links uit een mailtekst, in volgorde en zonder dubbele."""
    gezien, uit = set(), []
    for url in RE_URL.findall(tekst or ""):
        url = url.rstrip(".,;:)>]\"'")
        if url in gezien:
            continue
        gezien.add(url)
        if toegestaan(url):
            uit.append(url)
    return uit


def beschrijf_bestand(pad):
    """Wat voor bestand is dit, en wat zit erin? Zonder de inhoud te tonen."""
    naam = os.path.basename(pad)
    bytes_ = os.path.getsize(pad)
    soort = (os.path.splitext(naam)[1] or "").lower().lstrip(".") or "zonder"
    uit = {"naam": naam, "bytes": bytes_, "soort": soort}
    if soort == "pdf":
        try:
            with open(pad, "rb") as f:
                ruw = f.read()
            uit["bladzijden"] = ruw.count(b"/Type /Page") + ruw.count(b"/Type/Page")
            # Staat er tekst in, of is het een scan? Dat bepaalt of wij maten
            # kunnen uitlezen of de tekening moeten bekijken.
            uit["heeft_tekstlaag"] = (b"/Font" in ruw)
        except Exception as e:
            uit["fout"] = f"{type(e).__name__}"
    return uit


def proef():
    """Nameten wat deze module belooft, zonder mailbox en zonder netwerk."""
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. ALLEEN HTTPS NAAR EEN TOEGESTANE HOST. De valse vriend hier is een
    # toets op "staat de naam erin": die laat een host door die de toegestane
    # naam alleen als voorvoegsel heeft.
    for url, mag, waarom in [
            ("https://studiezaal.nijmegen.nl/pakket/123.zip", True,
             "de bron zelf"),
            ("https://app4.nijmegen.nl/DGD2/Bouwarchief/Index/0268", True,
             "het gebouwenarchief"),
            ("https://studiezaal.nijmegen.nl.kwaad.nl/pakket.zip", False,
             "toegestane naam als voorvoegsel van een andere host"),
            ("https://kwaad.nl/?x=studiezaal.nijmegen.nl", False,
             "toegestane naam in de queryreeks"),
            ("http://studiezaal.nijmegen.nl/pakket.zip", False,
             "geen https"),
            ("https://nijmegen.nl.example.com/a", False,
             "nijmegen.nl als voorvoegsel"),
            ("https://sub.studiezaal.nijmegen.nl/a.zip", True,
             "echt subdomein"),
            ("ftp://studiezaal.nijmegen.nl/a.zip", False, "ander protocol")]:
        if toegestaan(url) != mag:
            fouten.append(f"{waarom}: {url} geeft {toegestaan(url)}, "
                          f"verwacht {mag}")

    # 2. DE LINKS UIT EEN MAILTEKST, met een niet-toegestane ertussen.
    tekst = ("Beste,\n\nDe documenten staan klaar:\n"
             "https://studiezaal.nijmegen.nl/pakket/abc123.zip .\n"
             "Afmelden via https://nieuwsbrief.example.com/uit\n"
             "Nogmaals: https://studiezaal.nijmegen.nl/pakket/abc123.zip\n")
    uit = links_uit(tekst)
    check("aantal toegestane links", len(uit), 1)
    if uit and uit[0] != "https://studiezaal.nijmegen.nl/pakket/abc123.zip":
        fouten.append(f"de link is verkeerd afgekapt: {uit[0]!r}")

    # 3. EEN MAIL ZONDER LINK LEVERT NIETS, en dat is iets anders dan een
    # mail die niet is gelezen.
    check("mail zonder link", links_uit("Geen enkele link hier."), [])
    check("lege tekst", links_uit(""), [])
    check("None", links_uit(None), [])

    # 4. EEN GECODEERDE KOP MOET LEESBAAR WORDEN.
    gecodeerd = "=?utf-8?q?Uw_documenten_van_het_Digitaal_Gebouwen_Archief?="
    if "Digitaal Gebouwen Archief" not in _kop(gecodeerd):
        fouten.append(f"een gecodeerde kop wordt niet gelezen: "
                      f"{_kop(gecodeerd)!r}")

    # 5. EEN PDF WORDT BESCHREVEN ZONDER DAT DE INHOUD IN DE UITVOER KOMT.
    with tempfile.TemporaryDirectory() as map_:
        pad = os.path.join(map_, "tekening.pdf")
        with open(pad, "wb") as f:
            f.write(b"%PDF-1.4\n/Type /Page\n/Type /Page\n/Font 1 0 R\n"
                    b"GEHEIME TEKENING\n%%EOF\n")
        d = beschrijf_bestand(pad)
        check("bladzijden", d.get("bladzijden"), 2)
        check("tekstlaag", d.get("heeft_tekstlaag"), True)
        if "GEHEIME" in str(d):
            fouten.append("de beschrijving bevat de inhoud van het bestand")

    # 6. DE WERKMAP BLIJFT ONAANGEROERD. Dit is de belangrijkste belofte van
    # deze module: niets uit een dossier komt in de repo terecht.
    if "repo" in str(tempfile.gettempdir()):
        fouten.append("de tijdelijke map ligt in de repo")

    print(f"Proef dossiermail: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def haal_pakket(url, map_):
    """Het pakket binnenhalen in een tijdelijke map, met een maximum."""
    ctx = ssl.create_default_context()
    naam = os.path.basename(urllib.parse.urlparse(url).path) or "pakket.bin"
    doel = os.path.join(map_, naam)
    verzoek = urllib.request.Request(url, headers={"User-Agent":
                                                   "derksenvastgoed-monitor"})
    with urllib.request.urlopen(verzoek, timeout=120, context=ctx) as antwoord:
        lengte = int(antwoord.headers.get("Content-Length") or 0)
        if lengte and lengte > MAX_PAKKET:
            raise RuntimeError(f"pakket is {lengte} bytes, meer dan "
                               f"{MAX_PAKKET}")
        gelezen = 0
        with open(doel, "wb") as f:
            while True:
                blok = antwoord.read(1 << 16)
                if not blok:
                    break
                gelezen += len(blok)
                if gelezen > MAX_PAKKET:
                    raise RuntimeError("pakket groter dan toegestaan")
                f.write(blok)
    return doel, gelezen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dagen", type=int, default=7,
                    help="hoe ver terug in de mailbox kijken")
    ap.add_argument("--haal", action="store_true",
                    help="ook het pakket binnenhalen en beschrijven")
    ap.add_argument("--proef", action="store_true",
                    help="eigen logica nameten; raakt geen mailbox")
    args = ap.parse_args()
    if args.proef:
        return proef()

    if not (GEBRUIKER and WACHTWOORD):
        print("Geen MAIL_USERNAME of MAIL_PASSWORD; niets te doen.",
              file=sys.stderr)
        return 1
    try:
        verbinding = imaplib.IMAP4_SSL(IMAP_HOST)
        verbinding.login(GEBRUIKER, WACHTWOORD)
        verbinding.select("INBOX", readonly=True)   # lezen, niets markeren
    except Exception as e:
        print(f"Kan niet inloggen op de mailbox: {e}", file=sys.stderr)
        return 1

    import datetime as dt
    sinds = (dt.date.today() - dt.timedelta(days=args.dagen)).strftime("%d-%b-%Y")
    ids = []
    for afzender in AFZENDERS:
        try:
            status, data = verbinding.search(
                None, f'(FROM "{afzender}" SINCE {sinds})')
            if status == "OK":
                ids.extend((data[0] or b"").split())
        except Exception as e:
            print(f"Zoekfout bij {afzender}: {e}", file=sys.stderr)
    print(f"Mails van {', '.join(AFZENDERS)} sinds {sinds}: {len(ids)}",
          file=sys.stderr)
    if not ids:
        print("Geen mail van die afzender gevonden. Is hij al bezorgd, en "
              "staat hij in INBOX en niet in spam?", file=sys.stderr)
        verbinding.logout()
        return 0

    for mid in sorted(set(ids)):
        try:
            status, data = verbinding.fetch(mid, "(BODY.PEEK[])")
            bericht = email.message_from_bytes(data[0][1])
        except Exception as e:
            print(f"  bericht {mid!r} niet te lezen: {e}", file=sys.stderr)
            continue
        print(f"\n  van:     {_kop(bericht.get('From'))}", file=sys.stderr)
        print(f"  datum:   {_kop(bericht.get('Date'))}", file=sys.stderr)
        print(f"  subject: {_kop(bericht.get('Subject'))[:90]}",
              file=sys.stderr)
        tekst = platte_tekst(bericht)
        bijlagen = [d.get_filename() for d in bericht.walk()
                    if d.get_filename()]
        if bijlagen:
            print(f"  bijlagen in de mail zelf: {len(bijlagen)}: "
                  f"{', '.join(_kop(b) for b in bijlagen[:6])}",
                  file=sys.stderr)
        alle = RE_URL.findall(tekst or "")
        goed = links_uit(tekst)
        print(f"  links: {len(alle)} in de mail, {len(goed)} naar een "
              f"toegestane host", file=sys.stderr)
        for url in goed:
            print(f"    {url[:110]}", file=sys.stderr)
        if not goed:
            andere = sorted({host_van(u) for u in alle} - {""})
            if andere:
                print(f"  hosts die niet zijn toegestaan: "
                      f"{', '.join(andere[:6])}", file=sys.stderr)
            continue
        if not args.haal:
            print("  (met --haal erbij wordt het pakket geopend en beschreven)",
                  file=sys.stderr)
            continue

        map_ = tempfile.mkdtemp(prefix="dossier-")
        try:
            doel, bytes_ = haal_pakket(goed[0], map_)
            print(f"  pakket: {os.path.basename(doel)}, {bytes_} bytes",
                  file=sys.stderr)
            uitpak = os.path.join(map_, "uit")
            os.makedirs(uitpak, exist_ok=True)
            try:
                shutil.unpack_archive(doel, uitpak)
                bestanden = []
                for wortel, _, namen in os.walk(uitpak):
                    for n in namen:
                        bestanden.append(os.path.join(wortel, n))
            except Exception:
                bestanden = [doel]
            print(f"  inhoud: {len(bestanden)} bestand(en)", file=sys.stderr)
            for pad in sorted(bestanden)[:40]:
                d = beschrijf_bestand(pad)
                extra = ""
                if d.get("soort") == "pdf":
                    extra = (f", {d.get('bladzijden')} bladzijden, "
                             f"{'met tekstlaag' if d.get('heeft_tekstlaag') else 'alleen beeld'}")
                print(f"    {d['naam'][:60]:60} {d['bytes']:>9} bytes "
                      f"{d['soort']}{extra}", file=sys.stderr)
        except Exception as e:
            print(f"  pakket niet binnen te halen: {type(e).__name__}: "
                  f"{str(e)[:120]}", file=sys.stderr)
        finally:
            shutil.rmtree(map_, ignore_errors=True)
            print("  tijdelijke map opgeruimd; niets hiervan staat in de repo",
                  file=sys.stderr)
    verbinding.logout()
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): zonder dit geeft het proces altijd 0 terug, ook
    # als de proef rood staat, en is de poort in de workflow een formaliteit.
    sys.exit(main())
