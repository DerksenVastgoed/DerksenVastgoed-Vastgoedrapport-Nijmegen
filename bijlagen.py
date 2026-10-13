#!/usr/bin/env python3
"""
De tekeningen bij een bekendmaking opsporen, zonder studiezaal en met de hand.

WAAROM DIT BESTAAT. Het dossier uit het Digitaal Gebouwen Archief blijft
handwerk: die downloadlink geeft 403 vanaf elk netwerk buiten Marks eigen
computer, zie de kop van dossiermail.py. Maar de tekeningen die wij nodig
hebben zijn er ook langs een andere weg. De gemeente publiceert bij een
aanvraag de stukken mee, geanonimiseerd, als externe bijlage bij de officiele
bekendmaking. Die bekendmakingen halen wij al elke ochtend op.

Dat is de route die zichzelf bijhoudt: geen aanvraag per pand, geen mail,
geen link van drie dagen. Elke aanvraag die langskomt brengt zijn eigen
tekeningen mee.

WAT NOG NIET VASTSTAAT. Hoe die bijlagen in de SRU staan en welke url ze
hebben, weet ik niet, en van buiten een run is het niet te bevragen: de
proxy van de werkomgeving weigert repository.overheid.nl. Daarom probeert
deze module drie vormen in een ronde en meldt van alle drie wat ze opleveren.
Dat scheelt runs, net als bij de drie koppen in dossiermail.py.

TWEE GEVALLEN WAARVAN WIJ HET ANTWOORD AL KENNEN, en daarom bruikbaar als
toets in plaats van als verkenning:

  gmb-2026-463651  Staringstraat 2, verbouwen pand naar 3 appartementen
  gmb-2026-460303  Biezenstraat 110, splitsen woning met garage tot 2 woningen

Van beide staan de stukken op een computer waar wij ze hebben gezien, met
namen als "1038-04geb Staringstraat2 260922-geanonimiseerd.pdf". Vindt deze
module diezelfde namen, dan klopt de route van begin tot eind. Vindt hij er
geen, dan is dat geen "er zijn geen bijlagen" maar "wij kijken verkeerd".

WAT HET NIET DOET. Geen enkel bestand komt in de repo. De stukken gaan naar
een tijdelijke map en die wordt opgeruimd. Op de tekeningen rust auteursrecht
en deze repo is publiek. Wat wij eruit meten, bijvoorbeeld "op deze laag is
45,3 m2 woonfunctie en daarvan 42,8 m2 zelfstandige woning", is onze eigen
waarneming en mag wel.
"""

import argparse
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# EEN IMPLEMENTATIE PER AFSPRAAK. beschrijf_bestand meet van een bestand de
# omvang, de soort, het aantal bladzijden en of er een tekstlaag in zit. Die
# staat al in dossiermail.py en wordt hier geleend in plaats van nagemaakt:
# twee kopieen van dezelfde meting gaan uit elkaar lopen zodra er een wordt
# aangepast.
from dossiermail import beschrijf_bestand

SRU_URL = "https://repository.overheid.nl/sru"
REPO = "https://repository.overheid.nl"
ZOEK = "https://zoek.officielebekendmakingen.nl"

# De hosts waar wij een bijlage vandaan halen. Net als bij dossiermail.py een
# vergelijking op de host zelf en op echte subdomeinen, niet op "staat de naam
# erin": https://repository.overheid.nl.kwaad.nl zou daar doorheen glippen.
TOEGESTANE_HOSTS = ("repository.overheid.nl", "zoek.officielebekendmakingen.nl",
                    "repository.officiele-overheidspublicaties.nl")

MAX_BIJLAGE = 60 * 1024 * 1024
KOP = {"User-Agent": "derksenvastgoed-monitor"}

# DE NAAM BEPAALT DE VOLGORDE, DE INHOUD BEPAALT WAT HET IS.
#
# Eerst stond hier een toets op de bestandsnaam die zei of iets een
# plattegrond was. Nagemeten op de 60 namen die wij echt hebben gezien, uit
# zeven dossiers: 16 treffers, waarvan 6 geen plattegrond. "Erfafscheidingen
# aanzichten met bebouwing" kwam binnen omdat "bebouwing" het stuk "geb"
# bevat, en gevelaanzichten, een situatietekening en een muurdetail kwamen
# binnen op "nieuw". Andersom bleven "260928-5907-A1-gewenst" en
# "A1-vergund" buiten, terwijl dat juist de tekeningen van de oude en de
# nieuwe toestand zijn.
#
# Een naam die zo vaak miswijst, hoort geen oordeel te vellen. Hij bepaalt
# alleen welk bestand wij als eerste openen; wat het is, blijkt uit de tekst
# erin. Dat kunnen wij toch al lezen, want de tekeningen hebben een
# tekstlaag.
NAAM_BELOOFT_VEEL = ("plattegrond", "begane", "verdieping", "kelder",
                     "bouwkundig", "gewenst", "vergund", "nieuw", "bestaand")
NAAM_BELOOFT_WEINIG = ("bodemonderzoek", "flora", "fauna", "quickscan",
                       "berekening", "bouwbesluit", "brandveiligheid",
                       "motivering", "rapportage", "folder", "checklist",
                       "checlist", "isolatie", "besluit", "verzoekpdf",
                       "parkeerberekening", "foto", "detailboek", "waterberging")

# Waaraan een plattegrond in zijn eigen tekst te herkennen is: een laagnaam
# en iets dat op een ruimte of een maat lijkt. Een gevelaanzicht noemt wel de
# laag maar geen woonkamer, een bouwbesluittoets noemt wel m2 maar geen laag.
# Beide woorden zijn dus nodig, niet een van de twee.
LAAGWOORDEN = ("begane grond", "verdieping", "kelder", "souterrain", "zolder")
RUIMTEWOORDEN = ("woonkamer", "slaapkamer", "badkamer", "keuken", "overloop",
                 "berging", "hal", "entree", "toilet", "woonfunctie")


def host_van(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def toegestaan(url):
    h = host_van(url)
    if not h or not (url or "").lower().startswith("https://"):
        return False
    return any(h == t or h.endswith("." + t) for t in TOEGESTANE_HOSTS)


def voorrang(naam):
    """
    In welke volgorde wij de bijlagen openen. Geen oordeel, een volgorde.

    0 belooft veel, 1 zegt niets, 2 belooft weinig. Zit een dossier vol, dan
    openen wij de nullen eerst; de tweeen gaan niet overboord, want een naam
    die weinig belooft kan er toch een zijn, en dat hebben wij gezien.

    WAT ER GEBEURT ALS EEN NAAM IN BEIDE LIJSTEN VALT. Dan geeft hij 1, net
    als een naam die niets zegt. Dat is geen compromis maar een meting: van
    de 60 namen die wij echt hebben gezien valt er geen enkele in beide
    lijsten. De volgorde van de twee toetsen maakt dus voor niets uit wat wij
    kennen, en ik heb geprobeerd die volgorde na te meten door hem om te
    draaien: er ging niets rood, want er was niets om rood van te worden.
    Een naam verzinnen waarop het wel uitmaakt en daar de regel op bouwen is
    precies hoe je een toets krijgt die nooit iets vangt. Dus kiest deze
    functie niet: zo'n naam spreekt zichzelf tegen en zegt daarmee niets.
    verken() telt ze, zodat de eerste echte in een issue opduikt en wij de
    regel dan kunnen afleiden uit het geval in plaats van uit een bedenksel.
    """
    n = (naam or "").lower()
    veel = any(w in n for w in NAAM_BELOOFT_VEEL)
    weinig = any(w in n for w in NAAM_BELOOFT_WEINIG)
    if veel and weinig:
        return 1
    if weinig:
        return 2
    if veel:
        return 0
    return 1


def telling_tegenspraak(namen):
    """Hoeveel namen in beide lijsten vallen. Zie voorrang() voor waarom."""
    n = 0
    for naam in namen:
        k = (naam or "").lower()
        if (any(w in k for w in NAAM_BELOOFT_VEEL)
                and any(w in k for w in NAAM_BELOOFT_WEINIG)):
            n += 1
    return n


def is_plattegrond(tekst):
    """Of de tekst in een bestand die van een plattegrond is. Zie de kop."""
    t = (tekst or "").lower()
    return (any(w in t for w in LAAGWOORDEN)
            and any(w in t for w in RUIMTEWOORDEN))


def tekst_van(pad):
    """De tekstlaag van een PDF, of een lege string. Zonder uitzondering."""
    try:
        import subprocess
        r = subprocess.run(["pdftotext", "-layout", "-q", pad, "-"],
                           capture_output=True, timeout=120)
        return (r.stdout or b"").decode("utf-8", "replace")
    except Exception:
        return ""


def kandidaten(gmb):
    """
    De drie vormen waarin de bijlagen kunnen staan, elk met een eigen vraag.

    Welke het is weet ik nog niet, en het is van buiten een run niet te
    bevragen. Daarom alle drie in een ronde, en de samenvatting zegt wat elk
    opleverde. Een vorm die niets geeft is een antwoord en geen storing.
    """
    jaar = gmb.split("-")[1] if gmb.count("-") >= 2 else ""
    return [
        ("html van de publicatie",
         f"{REPO}/frbr/officielepublicaties/gmb/{jaar}/{gmb}/1/html/{gmb}.html"),
        ("metadata van de publicatie",
         f"{REPO}/frbr/officielepublicaties/gmb/{jaar}/{gmb}/1/metadata/metadata.xml"),
        ("zoekpagina", f"{ZOEK}/{gmb}.html"),
    ]


def haal(url, binair=False):
    """Een pagina of bestand ophalen. Geeft (inhoud, fout) terug."""
    if not toegestaan(url):
        return None, "host niet toegestaan"
    try:
        verzoek = urllib.request.Request(url, headers=KOP)
        with urllib.request.urlopen(verzoek, timeout=90) as a:
            ruw = a.read(MAX_BIJLAGE + 1)
        if len(ruw) > MAX_BIJLAGE:
            return None, f"groter dan {MAX_BIJLAGE} bytes"
        return (ruw if binair else ruw.decode("utf-8", "replace")), ""
    except Exception as e:
        code = getattr(e, "code", None)
        # Alleen het soort fout en de code: de tekst bevat de url, en de
        # samenvatting komt in een issue in een publieke repo.
        return None, f"{type(e).__name__}" + (f" {code}" if code else "")


def bijlagen_uit_html(tekst, basis):
    """
    De links naar externe bijlagen uit een publicatiepagina.

    Een bijlage bij een bekendmaking heet exb-<jaar>-<nummer>. De naam die de
    lezer ziet staat in de linktekst, en de bestandsnaam in de url. Beide
    worden meegenomen, want de linktekst zegt vaak waar de tekening over gaat
    en de bestandsnaam niet altijd.
    """
    uit = []
    if not tekst:
        return uit
    for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{0,160})</a>', tekst,
                         re.I):
        href, woorden = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if not re.search(r"(exb-|externebijlagen|\.pdf)", href, re.I):
            continue
        vol = urllib.parse.urljoin(basis, href)
        if not toegestaan(vol):
            continue
        uit.append({"url": vol, "tekst": woorden,
                    "naam": urllib.parse.unquote(
                        os.path.basename(urllib.parse.urlparse(vol).path))})
    # Dubbele links komen voor als dezelfde bijlage twee keer op de pagina
    # staat. De eerste wint; de volgorde van de pagina blijft zo staan.
    gezien, net = set(), []
    for b in uit:
        if b["url"] in gezien:
            continue
        gezien.add(b["url"])
        net.append(b)
    return net


def bijlagen_uit_metadata(tekst, basis):
    """Hetzelfde, maar uit de metadata-xml: daar staan de bijlagen als item."""
    uit = []
    if not tekst:
        return uit
    try:
        wortel = ET.fromstring(tekst)
    except Exception:
        # Geen geldige xml is een antwoord: deze vorm bestaat dan niet.
        return uit
    for el in wortel.iter():
        for waarde in list(el.attrib.values()) + ([el.text] if el.text else []):
            if not isinstance(waarde, str):
                continue
            w = waarde.strip()
            if not re.search(r"(exb-|externebijlagen)", w, re.I):
                continue
            vol = urllib.parse.urljoin(basis, w) if not w.startswith("http") else w
            if toegestaan(vol):
                uit.append({"url": vol, "tekst": "",
                            "naam": urllib.parse.unquote(
                                os.path.basename(
                                    urllib.parse.urlparse(vol).path))})
    gezien, net = set(), []
    for b in uit:
        if b["url"] not in gezien:
            gezien.add(b["url"])
            net.append(b)
    return net


def verken(gmb, haal_bestanden=False):
    """Een publicatie langs de drie vormen, en wat elk oplevert."""
    vind = {"gmb": gmb, "vormen": [], "bijlagen": [], "bestanden": []}
    alle = []
    for naam, url in kandidaten(gmb):
        tekst, fout = haal(url)
        if fout:
            vind["vormen"].append({"vorm": naam, "uitkomst": fout, "aantal": 0})
            continue
        gevonden = (bijlagen_uit_metadata(tekst, url) if "metadata" in naam
                    else bijlagen_uit_html(tekst, url))
        vind["vormen"].append({"vorm": naam, "uitkomst": "gelezen",
                               "tekens": len(tekst), "aantal": len(gevonden)})
        alle.extend(gevonden)
    gezien = set()
    for b in alle:
        if b["url"] not in gezien:
            gezien.add(b["url"])
            vind["bijlagen"].append(b)
    # Namen die zichzelf tegenspreken: nul in alles wat wij hebben gezien.
    # Duikt er hier een op, dan hebben wij eindelijk een echt geval om de
    # regel op te bouwen. Zie voorrang().
    vind["tegenspraak"] = telling_tegenspraak(
        [b["naam"] + " " + b["tekst"] for b in vind["bijlagen"]])
    if not haal_bestanden:
        return vind
    map_ = tempfile.mkdtemp(prefix="bijlage-")
    try:
        volgorde = sorted(vind["bijlagen"],
                          key=lambda b: voorrang(b["naam"] + " " + b["tekst"]))
        for b in volgorde[:25]:
            ruw, fout = haal(b["url"], binair=True)
            if fout:
                vind["bestanden"].append({"naam": b["naam"], "fout": fout})
                continue
            pad = os.path.join(map_, re.sub(r"[^\w.-]", "_", b["naam"])[:80]
                               or "bijlage.bin")
            with open(pad, "wb") as f:
                f.write(ruw)
            d = beschrijf_bestand(pad)
            d["tekst"] = b["tekst"][:70]
            d["voorrang"] = voorrang(b["naam"] + " " + b["tekst"])
            # De naam belooft, de inhoud beslist. Beide gaan mee, zodat wij
            # kunnen zien waar de naam miswijst in plaats van het te geloven.
            d["plattegrond"] = (is_plattegrond(tekst_van(pad))
                                if d.get("soort") == "pdf"
                                and d.get("heeft_tekstlaag") else False)
            vind["bestanden"].append(d)
    finally:
        shutil.rmtree(map_, ignore_errors=True)
    return vind


def samenvatting(bevindingen, vandaag=None):
    """
    Wat de verkenning opleverde, als markdown, zonder iets uit de stukken.

    Alleen bestandsnamen zoals de gemeente ze publiceert, omvang, soort,
    bladzijden en of er een tekstlaag in zit. Dat is metadata en niet het werk
    waarop auteursrecht rust, en het is het enige dat nodig is om te weten of
    deze route bruikbaar is.
    """
    import datetime as _dt
    nu = (vandaag or _dt.datetime.now(_dt.timezone.utc)).strftime(
        "%Y-%m-%d %H:%M UTC")
    r = [f"## Bijlagen bij bekendmakingen verkend op {nu}", ""]
    if not bevindingen:
        r.append("Geen enkele publicatie onderzocht. Dat is iets anders dan "
                 "een publicatie zonder bijlagen: er is niet gekeken.")
        return "\n".join(r) + "\n"
    for b in bevindingen:
        r.append(f"### {b['gmb']}")
        r.append("")
        for v in b.get("vormen", []):
            extra = (f", {v.get('tekens', 0)} tekens" if v.get("tekens")
                     else "")
            r.append(f"- {v['vorm']}: {v['uitkomst']}{extra}, "
                     f"{v.get('aantal', 0)} bijlage(n)")
        bij = b.get("bijlagen") or []
        r.append(f"- samen {len(bij)} unieke bijlage(n)")
        if b.get("tegenspraak"):
            r.append(f"- **{b['tegenspraak']} naam/namen spreken zichzelf "
                     f"tegen** (beloven veel en weinig tegelijk). Dat was "
                     f"nog nooit voorgekomen; hier is eindelijk een echt "
                     f"geval om de regel op te bouwen.")
        if bij and not b.get("bestanden"):
            r.append("")
            for x in bij[:25]:
                r.append(f"  - `{x['naam'][:70]}`"
                         + (f" . {x['tekst'][:60]}" if x["tekst"] else ""))
        if b.get("bestanden"):
            r.append("")
            r.append("| bestand | bytes | soort | bladzijden | tekstlaag | "
                     "plattegrond |")
            r.append("|---|---:|---|---:|---|---|")
            for d in b["bestanden"][:25]:
                if d.get("fout"):
                    r.append(f"| {d['naam'][:46]} | | niet gelukt: "
                             f"{d['fout']} | | | |")
                    continue
                r.append(f"| {d['naam'][:46]} | {d['bytes']} | {d['soort']} | "
                         f"{d.get('bladzijden', '')} | "
                         f"{'ja' if d.get('heeft_tekstlaag') else 'nee' if d.get('soort') == 'pdf' else ''} | "
                         f"{'ja' if d.get('plattegrond') else ''} |")
            pdfs = [d for d in b["bestanden"] if d.get("soort") == "pdf"]
            met = [d for d in pdfs if d.get("heeft_tekstlaag")]
            plat = [d for d in b["bestanden"] if d.get("plattegrond")]
            if pdfs:
                r.append("")
                r.append(f"Van {len(pdfs)} PDF's hebben {len(met)} een "
                         f"tekstlaag; {len(plat)} lijken op een plattegrond. "
                         f"Met een tekstlaag zijn de maten uit te lezen "
                         f"zonder de tekening te bekijken.")
        r.append("")
    r.append("_Geen enkel bestand staat in de repo: alles is in een "
             "tijdelijke map geopend en opgeruimd._")
    return "\n".join(r) + "\n"


def proef():
    """Nameten wat deze module belooft, zonder netwerk."""
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # 1. DE HOSTCONTROLE KIJKT NAAR DE HOST EN NIET NAAR DE NAAM.
    gevallen = [
        ("https://repository.overheid.nl/frbr/x.html", True),
        ("https://zoek.officielebekendmakingen.nl/gmb-2026-1.html", True),
        ("https://repository.officiele-overheidspublicaties.nl/exb.pdf", True),
        ("https://repository.overheid.nl.kwaad.nl/exb.pdf", False),
        ("https://kwaad.nl/?x=repository.overheid.nl", False),
        ("http://repository.overheid.nl/x.html", False),
        ("https://overheid.nl/x.html", False),
        ("", False),
    ]
    for url, verwacht in gevallen:
        if toegestaan(url) != verwacht:
            fouten.append(f"toegestaan({url!r}) geeft {toegestaan(url)}, "
                          f"verwacht {verwacht}")

    # 2. DE DRIE VORMEN STAAN ER ALLE DRIE, met het jaar uit het nummer.
    k = kandidaten("gmb-2026-463651")
    check("aantal vormen", len(k), 3)
    if not any("/2026/" in u for _n, u in k):
        fouten.append(f"het jaar komt niet uit het nummer: {k}")

    # 3. BIJLAGEN UIT HTML, en niets anders dan bijlagen.
    html = ('<a href="/frbr/.../exb-2026-99/1/bijlage/'
            '1038-04geb%20Staringstraat2%20260922-geanonimiseerd.pdf">'
            'Bouwkundige tekening nieuw</a>'
            '<a href="https://kwaad.nl/exb-2026-1.pdf">kwaadaardig</a>'
            '<a href="/over-deze-site.html">Over deze site</a>')
    uit = bijlagen_uit_html(html, "https://repository.overheid.nl/frbr/x.html")
    check("aantal bijlagen uit html", len(uit), 1)
    if uit:
        check("naam ontkomt aan %20", uit[0]["naam"],
              "1038-04geb Staringstraat2 260922-geanonimiseerd.pdf")
        check("linktekst", uit[0]["tekst"], "Bouwkundige tekening nieuw")

    # 4. DE NAAM BEPAALT DE VOLGORDE EN VELT GEEN OORDEEL.
    # Alle namen hieronder zijn namen die wij echt hebben gezien, uit zeven
    # dossiers. Een patroon bouwen tegen een naam die niemand schrijft, vangt
    # niets.
    for naam in ("Plattegronden - Nieuwe situatie - Kelder en BG-Vloer.pdf",
                 "260914-BD70-DO-03 nieuw-geanonimiseerd.pdf",
                 "260928-5907-A1-vergund-geanonimiseerd.pdf"):
        check(f"voorrang {naam[:28]}", voorrang(naam), 0)
    for naam in ("Quickscan flora en fauna Biezenstraat 110.pdf",
                 "checlist-natuurinclusief-bouwen-geanonimiseerd.pdf",
                 "verzoekpdf-2026092201714-geanonimiseerd.pdf",
                 "1038-Parkeerberekening 260921-geanonimiseerd.pdf"):
        check(f"voorrang {naam[:28]}", voorrang(naam), 2)
    # Een naam die niets belooft hoort in het midden te vallen en niet
    # achteraan: "A3 (L)-trappenhuis" zegt niets, maar is wel een tekening.
    check("voorrang trappenhuis",
          voorrang("260928-5907-A3 (L)-trappenhuis-geanonimiseerd.pdf"), 1)
    # Een naam die zichzelf tegenspreekt zegt niets en krijgt daarom 1. Dit
    # is het enige geval hier dat niet van een echt bestand komt: van de 60
    # namen die wij hebben gezien valt er geen in beide lijsten. Daarom kiest
    # de functie niet en telt verken() ze, zodat de eerste echte opduikt.
    check("voorrang tegenspraak",
          voorrang("Berekening plattegronden-geanonimiseerd.pdf"), 1)
    if telling_tegenspraak(["Berekening plattegronden.pdf", "nieuw.pdf"]) != 1:
        fouten.append("een naam die zichzelf tegenspreekt wordt niet geteld")

    # 5. DE INHOUD BESLIST WAT HET IS.
    # De twee gevallen hieronder zijn afgelezen van twee echte stukken bij de
    # aanvraag voor Staringstraat 2: het blad met de plattegronden en het blad
    # met de bouwkundige details. Op het eerste staan laagnamen en
    # ruimtenamen, op het tweede geen van beide. Een gevelaanzicht noemt wel
    # de laag en geen ruimte; daarom moeten het er twee zijn en niet een.
    if not is_plattegrond("begane grond nieuw  woonkamer 20.9 m2  "
                          "slaapkamer 16.4 m2  entree"):
        fouten.append("een blad met laagnamen en ruimtenamen geldt niet als "
                      "plattegrond")
    for tekst, waarom in (
            ("detail dakrand houtvezelisolatie dampremmende laag", "details"),
            ("voorgevel achtergevel 1e verdieping 2e verdieping peil",
             "een gevelaanzicht noemt wel de laag maar geen ruimte"),
            ("gebruiksoppervlakte 58,31 m2 brandcompartiment",
             "een bouwbesluittoets noemt wel maten maar geen laag"),
            ("", "leeg")):
        if is_plattegrond(tekst):
            fouten.append(f"ten onrechte een plattegrond ({waarom})")

    # 5. GEEN GELDIGE XML IS EEN ANTWOORD EN GEEN VAL.
    check("rommel in plaats van xml", bijlagen_uit_metadata("<nietafgesloten",
                                                            REPO), [])
    check("lege metadata", bijlagen_uit_metadata("", REPO), [])

    # 6. DE SAMENVATTING IS LEESBAAR EN VERRAADT NIETS.
    leeg = samenvatting([])
    if "er is niet gekeken" not in leeg:
        fouten.append(f"een lege verkenning zegt niet dat er niet is gekeken: "
                      f"{leeg[:90]!r}")
    vol = samenvatting([{
        "gmb": "gmb-2026-463651",
        "vormen": [{"vorm": "html van de publicatie", "uitkomst": "gelezen",
                    "tekens": 12000, "aantal": 6},
                   {"vorm": "metadata van de publicatie",
                    "uitkomst": "HTTPError 404", "aantal": 0}],
        "bijlagen": [{"url": "https://repository.overheid.nl/x.pdf",
                      "naam": "1038-04geb Staringstraat2.pdf", "tekst": ""}],
        "bestanden": [{"naam": "1038-04geb Staringstraat2.pdf", "bytes": 3049275,
                       "soort": "pdf", "bladzijden": 6,
                       "heeft_tekstlaag": True, "plattegrond": True}]}])
    for nodig in ("gmb-2026-463651", "1038-04geb", "HTTPError 404",
                  "hebben 1 een tekstlaag"):
        if nodig not in vol:
            fouten.append(f"de samenvatting noemt {nodig!r} niet")
    # Een mislukte vorm moet erin blijven staan. Zonder dat leest een
    # samenvatting met een lege tabel als "deze publicatie heeft geen
    # bijlagen", terwijl er misschien verkeerd is gekeken.
    if "404" not in vol:
        fouten.append("een vorm die niets opleverde valt uit de samenvatting")

    print(f"Proef bijlagen: {len(fouten)} fouten", file=sys.stderr)
    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    return 1 if fouten else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gmb", default="gmb-2026-463651,gmb-2026-460303",
                    help="publicatienummers, door komma's gescheiden")
    ap.add_argument("--haal", action="store_true",
                    help="de bijlagen ook binnenhalen en beschrijven")
    ap.add_argument("--proef", action="store_true")
    ap.add_argument("--samenvatting", default="",
                    help="pad waar de bevinding als markdown komt; zonder dit "
                         "staat de uitkomst alleen in het joblogboek, en dat "
                         "is van buiten de runner niet te lezen")
    args = ap.parse_args()
    if args.proef:
        return proef()

    bevindingen = []
    try:
        for gmb in [g.strip() for g in args.gmb.split(",") if g.strip()]:
            print(f"\n== {gmb} ==", file=sys.stderr)
            v = verken(gmb, haal_bestanden=args.haal)
            for vorm in v["vormen"]:
                print(f"  {vorm['vorm']}: {vorm['uitkomst']}, "
                      f"{vorm.get('aantal', 0)} bijlagen", file=sys.stderr)
            for d in v.get("bestanden", []):
                print(f"    {d.get('naam', '?')[:60]:60} "
                      f"{d.get('bytes', '')} {d.get('soort', d.get('fout', ''))}",
                      file=sys.stderr)
            bevindingen.append(v)
    finally:
        # Ook bij een fout halverwege hoort er te staan wat wel is gevonden.
        if args.samenvatting:
            with open(args.samenvatting, "w", encoding="utf-8") as f:
                f.write(samenvatting(bevindingen))
    return 0


if __name__ == "__main__":
    # sys.exit en niet main(): anders is de exitcode altijd 0 en is de poort
    # in de workflow een formaliteit.
    sys.exit(main())
