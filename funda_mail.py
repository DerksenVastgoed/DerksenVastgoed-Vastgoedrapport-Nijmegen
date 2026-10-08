#!/usr/bin/env python3
"""
Leest de attenderingsmails van Funda en funda in business uit de eigen mailbox
en zet nieuwe objecten onderaan verkopen.txt.

Dit is geen scraping: Funda stuurt deze berichten zelf toe op basis van een
opgeslagen zoekopdracht. Het script leest de eigen post, meer niet.

Vereist:
  - IMAP aangezet in Gmail (Instellingen, Doorsturen en POP/IMAP)
  - MAIL_USERNAME en MAIL_PASSWORD (app-wachtwoord) als omgevingsvariabelen

Gebruik:
  python funda_mail.py                    # verwerkt ongelezen Funda-mails
  python funda_mail.py --proef            # toont wat het zou toevoegen, schrijft niets
  python funda_mail.py --dagen 30         # kijkt verder terug dan alleen ongelezen
"""

import argparse
import datetime as dt
import json
import email
import imaplib
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.header import decode_header

IMAP_HOST = "imap.gmail.com"
VERKOPEN_PAD = "verkopen.txt"
AFZENDERS = ["funda.nl", "funda.com", "pararius.nl", "pararius.com",
             "kamernet.nl", "vendr.nl",
             # Huislijn stuurt vanaf server@huislijn.nl. Hier stond eerst
             # alleen "huisly.nl", een ander domein, waardoor die mails nooit
             # werden opgehaald: ze stonden ongelezen in de mailbox en de
             # woningen kwamen niet in het bestand. Beide domeinen blijven
             # staan; Huisly is een andere dienst.
             "huislijn.nl", "huisly.nl",
             # 123Wonen stuurt een attendering waarin alleen de prijs staat en
             # "Nijmegen ()" als plaats: geen straat, geen oppervlakte. Alles
             # staat achter de link, inclusief het huisnummer. Deze afzender
             # stond nergens, ook niet bij de kandidaten, dus de mails waren
             # volledig onzichtbaar.
             "123wonen.nl"]

# Platforms waarvan we nog geen parser hebben, maar waar Mark zich wel bij kan
# hebben aangemeld. We lezen ze niet uit; we tellen alleen of er post van komt.
# Zo wordt een aanmelding zichtbaar in het rapport in plaats van dat de mails
# ongemerkt in de mailbox blijven liggen.
KANDIDATEN = ["huurwoningen.nl", "rentola.nl", "huurflits.nl", "hestiva.nl",
              "rebogroep.nl", "huislijn.nl", "ikwilhuren.nu", "nmgwonen.nl",
              "vastgoednederland.nl", "level2makelaars.nl", "vgmdestijl.nl",
              "expatrentalsholland.com", "hansjanssen.nl",
              "nextmovemakelaars.nl", "funda.nl"]

# De datum van de mail die nu wordt gelezen. De parsers stempelden elke
# waarneming met vandaag; bij het inhalen van oude mails zouden alle
# advertenties dan dezelfde dag krijgen en lijkt de markt in een dag ontstaan.
_DATUM_VAN_MAIL = None


def waarnemingsdatum():
    """De datum van de mail die nu gelezen wordt, anders vandaag."""
    return _DATUM_VAN_MAIL or dt.date.today().isoformat()


def datum_van_mail(bericht):
    """De verzenddatum uit de mailkop, als jjjj-mm-dd."""
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(bericht.get("Date"))
        return d.date().isoformat()
    except Exception:
        return None


GEBRUIKER = os.environ.get("MAIL_USERNAME", "")
WACHTWOORD = os.environ.get("MAIL_PASSWORD", "")

# Zelfde patronen als de browser-verzamelaar
RE_ADRES_KOMMA = re.compile(
    r"^\s*([A-Za-zÀ-ÿ.'\-\s]+?\s+\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\s*,\s*"
    r"([A-Za-zÀ-ÿ\-' ]+?)\s*$")
RE_POSTCODE = re.compile(
    r"^\s*(\d{4}\s?[A-Z]{2})\s+([A-Za-zÀ-ÿ\-' ]+?)\s*(?:\([^)]*\))?\s*$")
# Alleen een straatnaam, zonder huisnummer. Pararius doet dit bij huuraanbod.
RE_STRAAT_ALLEEN = re.compile(r"^\s*([A-Za-zÀ-ÿ.'\- ]{3,40})\s*$")
# '112 m² · 3 kamers · ...' of '112 m2'
RE_OPPERVLAKTE = re.compile(r"(\d{2,4})\s*m[²2]\b")
RE_ADRES = re.compile(r"^\s*([A-Za-zÀ-ÿ.'\-\s]+?\s+\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\s*$")
RE_PRIJS = re.compile(r"([\d][\d.]{2,})")


def strip_html(tekst):
    """
    Maakt van een HTML-mail leesbare regels. De href van een link naar een
    objectpagina wordt als aparte regel bewaard, zodat we later per pand de
    oorspronkelijke advertentie kunnen meegeven.
    """
    tekst = re.sub(r"(?is)<(script|style).*?</\1>", " ", tekst)
    # Objectlinks markeren voordat de tags verdwijnen. Alleen Funda-links
    # werden bewaard, waardoor bij Huislijn elke URL verdween. Juist daar zit
    # de straatnaam in de link (/huurwoning/.../maasstraat-nijmegen), en dat is
    # het enige dat een tekstomzetting altijd overleeft. Een link naar een
    # objectpagina van Huislijn blijft nu ook staan.
    tekst = re.sub(
        r'(?is)<a[^>]+href=["\']('
        r'[^"\']*funda[^"\']*/(?:koop|huur|detail|object)[^"\']*'
        r'|[^"\']*huislijn\.nl/huurwoning/[^"\']*'
        r'|[^"\']*123wonen[^"\']*'
        r')["\'][^>]*>',
        lambda m: f"\n__LINK__{m.group(1)}\n", tekst)
    tekst = re.sub(r"(?i)<br\s*/?>", "\n", tekst)
    tekst = re.sub(r"(?i)</(p|div|tr|td|h\d|li)>", "\n", tekst)
    tekst = re.sub(r"<[^>]+>", " ", tekst)
    vervang = {"&nbsp;": " ", "&amp;": "&", "&euro;": "€", "&#8364;": "€",
               "&quot;": '"', "&#39;": "'", "&lt;": "<", "&gt;": ">"}
    for k, v in vervang.items():
        tekst = tekst.replace(k, v)
    regels = [re.sub(r"[ \t]+", " ", r).strip() for r in tekst.split("\n")]
    return [r for r in regels if r]


def haal_tekst(bericht):
    """Haalt de leesbare regels uit een e-mailbericht."""
    delen_html, delen_plat = [], []
    if bericht.is_multipart():
        for deel in bericht.walk():
            soort = deel.get_content_type()
            if soort not in ("text/plain", "text/html"):
                continue
            try:
                inhoud = deel.get_payload(decode=True)
                if inhoud is None:
                    continue
                tekens = deel.get_content_charset() or "utf-8"
                tekst = inhoud.decode(tekens, errors="replace")
            except Exception:
                continue
            (delen_html if soort == "text/html" else delen_plat).append(tekst)
    else:
        try:
            inhoud = bericht.get_payload(decode=True) or b""
            tekst = inhoud.decode(bericht.get_content_charset() or "utf-8",
                                  errors="replace")
        except Exception:
            tekst = ""
        if "<html" in tekst.lower() or "<td" in tekst.lower():
            delen_html.append(tekst)
        else:
            delen_plat.append(tekst)

    if delen_html:
        return strip_html("\n".join(delen_html))
    regels = []
    for t in delen_plat:
        regels.extend([r.strip() for r in t.split("\n") if r.strip()])
    return regels


def parse_objecten(regels, basis_status):
    """
    Haalt objecten uit de regels van een attenderingsmail.
    Twee vormen:
      'Waalkade 60, Nijmegen'  gevolgd door  '€ 495.000 k.k.'
      'Vondelstraat 26'  '6512 BG Nijmegen'  '€ 545.000 k.k.'
    """
    gevonden, gezien, overgeslagen = [], set(), []

    for i, regel in enumerate(regels):
        if regel.startswith("__LINK__"):
            continue
        adres = plaats = None
        adres_idx = i

        postcode_gevonden = ""
        komma = RE_ADRES_KOMMA.match(regel)
        if komma:
            adres, plaats = komma.group(1).strip(), komma.group(2).strip()
        else:
            pc = RE_POSTCODE.match(regel)
            if not pc:
                continue
            plaats = pc.group(2).strip()
            postcode_gevonden = pc.group(1).replace(" ", "")
            for j in range(i - 1, max(-1, i - 5), -1):
                a = RE_ADRES.match(regels[j])
                if a:
                    adres, adres_idx = a.group(1).strip(), j
                    break
            # Pararius toont bij huuraanbod alleen de straatnaam. Dan pakken we
            # de regel direct boven de postcode, mits die op een straat lijkt.
            if not adres and i > 0:
                st_alleen = RE_STRAAT_ALLEEN.match(regels[i - 1])
                if st_alleen and not any(
                        w in regels[i - 1].lower()
                        for w in ("zoekopdracht", "woningen", "pararius", "bekijk",
                                  "nieuwe", "jouw", "team", "groet", "kamernet")):
                    adres, adres_idx = st_alleen.group(1).strip(), i - 1
            if not adres:
                continue

        # Alleen Nijmegen en directe omgeving
        if plaats.lower() not in ("nijmegen", "lent", "nijmegen-oost", "nijmegen-west"):
            continue

        prijs = None
        soort = None   # 'koop', 'maand' of 'pm2jr'
        for p in range(i + 1, min(len(regels), i + 8)):
            laag = regels[p].lower()
            if "aanvraag" in laag or "n.o.t.k" in laag:
                break
            pm = RE_PRIJS.search(regels[p])
            if not pm:
                continue
            ruw = pm.group(1).replace(".", "")
            if not ruw.isdigit():
                continue
            bedrag = int(ruw)

            # Huur per m2 per jaar, komt voor bij bedrijfsruimte
            if re.search(r"/\s*m.?\s*/\s*jaar|per\s*m.?\s*per\s*jaar", laag):
                if 20 <= bedrag <= 2000:
                    prijs, soort = bedrag, "pm2jr"
                    break
                continue

            # Maandhuur
            if re.search(r"per\s*maand|p/?m\b|/\s*mnd|per\s*mnd", laag):
                if 300 <= bedrag <= 25000:
                    prijs, soort = bedrag, "maand"
                    break
                continue

            # Koopsom: minimaal vijf cijfers en een duizendtalscheiding
            if "." in pm.group(1) and len(ruw) >= 5:
                prijs, soort = bedrag, "koop"
                break

        if not prijs:
            overgeslagen.append(f"{adres} (geen prijs gevonden)")
            continue

        # De status hangt af van wat voor prijs we vonden
        if soort == "maand":
            status = "te huur"
        elif soort == "pm2jr":
            status = "te huur pm2"
        else:
            status = basis_status

        sleutel = (adres.lower(), prijs)
        if sleutel in gezien:
            continue
        gezien.add(sleutel)

        # Bron-URL zoeken vlak boven of onder het adres
        bron = ""
        for j in range(max(0, adres_idx - 4), min(len(regels), i + 4)):
            if regels[j].startswith("__LINK__"):
                bron = regels[j][len("__LINK__"):].split("?")[0].strip()
                break

        # Oppervlakte staat vaak in de advertentieregel zelf. Bij een adres zonder
        # huisnummer is dat de enige bron, want de BAG kan er dan niets mee.
        opp = ""
        for p in range(adres_idx, min(len(regels), i + 8)):
            om = RE_OPPERVLAKTE.search(regels[p])
            if om and 10 <= int(om.group(1)) <= 2000:
                opp = om.group(1)
                break

        vandaag = waarnemingsdatum()
        regel_uit = f"{adres} | {plaats} | {prijs} | {status} | {vandaag}"
        regel_uit += f" | {bron}" if bron else " | "
        regel_uit += f" | {opp}" if opp else " | "
        regel_uit += f" | {postcode_gevonden}" if postcode_gevonden else " | "
        gevonden.append(regel_uit.rstrip(" |") if regel_uit.endswith(" | ") else regel_uit)

    return gevonden, overgeslagen




# Kamernet zet elk object over meerdere regels, zonder postcode:
#   Lange Hezelstraat,
#   Nijmegen
#   25 m2
#   kaal
#   Kamer
#   Vanaf 1 Sep 2026
#   € 550
#   /maand incl.
RE_KN_STRAAT = re.compile(r"^\s*([A-Za-zÀ-ÿ.'\-\d ]{3,45}),\s*$")
RE_KN_PLAATS = re.compile(r"^\s*([A-Za-zÀ-ÿ\-' ]{3,30})\s*$")
RE_KN_OPP = re.compile(r"^\s*(\d{1,4})\s*m[²2]\s*$")
RE_KN_SOORT = re.compile(r"^\s*(Kamer|Appartement|Studio|Woonhuis|Anti-kraak)\s*$", re.I)
RE_KN_PRIJS = re.compile(r"^\s*€\s*([\d.]+)\s*$")

KN_PLAATSEN = ("nijmegen", "lent")


def parse_kamernet(regels, basis_status="te huur kamer"):
    """
    Leest een Kamernet-overzicht. Kamers krijgen 'te huur kamer', zelfstandige
    eenheden zoals appartement en studio krijgen gewoon 'te huur'.
    """
    gevonden, gezien, overgeslagen = [], set(), []
    vandaag = waarnemingsdatum()

    for i, regel in enumerate(regels):
        st_m = RE_KN_STRAAT.match(regel)
        if not st_m or i + 1 >= len(regels):
            continue
        pl_m = RE_KN_PLAATS.match(regels[i + 1])
        if not pl_m:
            continue
        straat, plaats = st_m.group(1).strip(), pl_m.group(1).strip()
        if plaats.lower() not in KN_PLAATSEN:
            continue

        opp = soort = prijs = None
        inclusief = False
        for j in range(i + 2, min(len(regels), i + 12)):
            if opp is None:
                om = RE_KN_OPP.match(regels[j])
                if om:
                    opp = int(om.group(1))
                    continue
            if soort is None:
                sm = RE_KN_SOORT.match(regels[j])
                if sm:
                    soort = sm.group(1).lower()
                    continue
            pm = RE_KN_PRIJS.match(regels[j])
            if pm:
                prijs = int(pm.group(1).replace(".", ""))
                if j + 1 < len(regels) and "incl" in regels[j + 1].lower():
                    inclusief = True
                break

        if not (opp and soort and prijs):
            overgeslagen.append(f"{straat} (onvolledig)")
            continue

        status = "te huur kamer" if soort == "kamer" else "te huur"
        sleutel = (straat.lower(), prijs, opp)
        if sleutel in gezien:
            continue
        gezien.add(sleutel)

        # 'incl.' betekent inclusief servicekosten; dat vermelden we in de bron,
        # zodat later duidelijk is dat dit geen kale huur is.
        bron = "kamernet-incl" if inclusief else "kamernet"
        gevonden.append(f"{straat} | {plaats} | {prijs} | {status} | {vandaag} "
                        f"| {bron} | {opp} | ")
    return gevonden, overgeslagen




# Kamernet stuurt ook losse attenderingen, met labels in plaats van een lijst:
#   Locatie: Graafseweg, Nijmegen
#   Oppervlakte: 21 m2
#   Prijs: € 852 incl. g/w/e
# Die vorm herkende de overzichtsparser niet, waardoor tien mails per dag
# ongebruikt bleven.
RE_KN_LOCATIE = re.compile(r"^\s*Locatie:\s*(.+?)\s*,\s*([A-Za-zÀ-ÿ\-' ]+)\s*$", re.I)
RE_KN_OPP = re.compile(r"^\s*Oppervlakte:\s*(\d{1,4})\s*m", re.I)
RE_KN_PRIJS = re.compile(r"^\s*Prijs:\s*€\s*([\d.]+)", re.I)
# Waaraan we zien dat het geen kamer is. Op hele woorden, want "studentenhuis"
# bevat "huis" en dat maakte van een kamer een zelfstandige woning.
RE_ZELFSTANDIG = re.compile(r"\b(appartement|studio|woonhuis|eengezinswoning)\b", re.I)
RE_KAMER = re.compile(r"\bkamer\b", re.I)


def parse_kamernet_attendering(regels, vandaag=None):
    """
    Een losse Kamernet-mail met een enkele woonruimte.

    Er staat geen huisnummer in, alleen de straat; dat is hetzelfde als bij het
    huuraanbod van Pararius en daar kan de rest van het script mee omgaan.
    """
    vandaag = vandaag or waarnemingsdatum()
    straat = plaats = None
    opp = prijs = None
    inclusief = False
    soort_tekst = " ".join(regels).lower()
    for regel in regels:
        m = RE_KN_LOCATIE.match(regel)
        if m and not straat:
            straat, plaats = m.group(1).strip(), m.group(2).strip()
            continue
        m = RE_KN_OPP.match(regel)
        if m and not opp:
            opp = int(m.group(1))
            continue
        m = RE_KN_PRIJS.match(regel)
        if m and not prijs:
            prijs = int(m.group(1).replace(".", ""))
            inclusief = "incl" in regel.lower()
    if not (straat and plaats and prijs and opp):
        return [], []
    # Onmogelijke bedragen tegenhouden bij de bron. Een advertentie van €5 per
    # maand is een typefout of een plaatsaanduiding, en zo'n waarneming hoort
    # niet in het bestand te belanden, ook niet als de mediaan hem later toch
    # negeert. Ondergrens per maand en per m2, want allebei komen ze voor.
    if prijs < 150 or prijs > 10000:
        return [], [f"{straat}: €{prijs} per maand is niet aannemelijk"]
    if opp and not (3 <= prijs / opp <= 120):
        return [], [f"{straat}: €{prijs / opp:.0f} per m2 is niet aannemelijk"]
    # Kamernet attendeert ook buiten de stad; die horen niet in onze reeks,
    # anders schuift een kamer in Arnhem de Nijmeegse mediaan.
    if plaats.strip().lower() != "nijmegen":
        return [], [f"{straat}, {plaats}: buiten Nijmegen"]
    # Staat er "kamer", dan is het een kamer, ook als het woord studentenhuis
    # verderop valt. Kamernet gaat standaard over onzelfstandige woonruimte.
    if RE_KAMER.search(soort_tekst):
        status = "te huur kamer"
    elif RE_ZELFSTANDIG.search(soort_tekst):
        status = "te huur"
    else:
        status = "te huur kamer"
    # De staat van oplevering hoort in de bron: een gemeubileerd appartement
    # met een kort contract brengt per m2 veel meer op dan gewone verhuur, en
    # die twee horen niet in dezelfde mediaan. Bij de geplakte lijst leggen we
    # dit al vast; uit de mail deden we het nog niet.
    bron = "kamernet"
    # Kaal eerst: "ongemeubileerd" bevat "gemeubileerd", en anders wordt een
    # kale woning als gemeubileerd geteld.
    for staat, woorden in (("kaal", ("kaal", "kale", "ongemeubileerd")),
                           ("gestoffeerd", ("gestoffeerd",)),
                           ("gemeubileerd", ("gemeubileerd", "gemeubeld"))):
        if any(woord in soort_tekst for woord in woorden):
            bron += f"-{staat}"
            break
    if inclusief:
        bron += "-incl"
    return [f"{straat} | {plaats} | {prijs} | {status} | {vandaag} "
            f"| {bron} | {opp} | "], []


# Pararius-overzicht. De buurt staat tussen haakjes achter de postcode, en waar
# een kale en een totale huurprijs staan nemen we de kale: die telt voor het
# rendement en voor het puntenstelsel.
RE_PA_POSTCODE = re.compile(
    r"^\s*(\d{4}\s?[A-Z]{2})\s+([A-Za-zÀ-ÿ\-' ]+?)\s*\(([^)]+)\)\s*$")
RE_PA_PRIJS = re.compile(r"^\s*€\s*([\d.]+)\s*per maand\s*$")
# De oppervlakte staat nu op een regel met de rest van de kenmerken:
# "40 m² · 2 kamers · Gemeubileerd · Bouwjaar 1888". Vroeger stond hij los.
# Het patroon accepteert beide.
RE_PA_OPP = re.compile(r"^\s*(\d{1,4})\s*m[²2](?:\s*[·•|].*)?\s*$")
RE_PA_KAMERS = re.compile(r"(\d{1,2})\s*kamers?", re.I)
RE_PA_BOUWJAAR = re.compile(r"bouwjaar\s*(\d{4})", re.I)
RE_PA_TITEL = re.compile(
    r"^\s*(Appartement|Huis|Studio|Kamer|Woonboot|Bungalow)\s+(.+?)\s*$", re.I)

# Leegstandbeheer is geen markthuur en hoort niet in een mediaan thuis.
PA_UITSLUITEN = ("ad hoc", "camelot", "leegstandbeheer", "anti-kraak", "antikraak")


# Drie manieren om dezelfde Huislijn-mail te lezen, want de omzetting van HTML
# naar tekst levert niet altijd dezelfde vorm op. Op 8 oktober kwamen er vier
# mails binnen waar nul objecten uit kwamen: de eerste versie eiste dat de
# straatnaam en de prijs op APARTE regels stonden, met de prijsregel beginnend
# met "Huur:". In de werkelijke mail staan ze vermoedelijk op een regel.
#
# 1. De straatnaam uit de URL. Die is het betrouwbaarst, want een link
#    overleeft elke tekstomzetting:
#    .../huurwoning/nederland/gelderland/4433366/maasstraat-nijmegen?utm...
RE_HL_URL = re.compile(r"huislijn\.nl/huurwoning/[^\s)]*?/([a-z0-9\-]+?)-nijmegen",
                       re.IGNORECASE)
# 2. Een straatnaam met Nijmegen erachter, met of zonder blokhaken.
RE_HL_STRAAT = re.compile(r"\[?([A-Za-zÀ-ÿ.'\- ]{3,40}?)\s+Nijmegen\b",
                          re.IGNORECASE)
# 3. Een bedrag, waar het ook in de regel staat.
RE_HL_HUUR = re.compile(r"(?:huur|prijs)?\s*€\s*([\d][\d.,]*)", re.IGNORECASE)
# Regels uit de reclameblokken die geen aanbod zijn.
HL_RUIS = ("kan ik dit huis betalen", "aanmelden", "wooninspiratie",
           "nieuwsbrief", "wooninfluencers", "laat je inspireren",
           "bekijk deze woning", "hypotheekaanvraag")


# De kenmerken staan niet in de mail maar op de advertentiepagina, achter de
# link die we sinds vandaag bewaren. Daar staat "Woon oppervlakte 150" en de
# postcode. Daarmee krijgt een Huislijn-waarneming een oppervlakte en telt hij
# mee in de huur per m2, zonder dat iemand een pand van een foto hoeft te
# herkennen. Het huisnummer staat er niet; dat hebben we ook niet nodig.
HL_KENMERKEN_PAD = "huislijn_kenmerken.json"
HL_MAX_OPHALEN = 25          # per run, want het zijn een paar panden per dag
RE_HL_OPP = re.compile(r"Woon\s*oppervlakte\D{0,60}?(\d{2,4})", re.IGNORECASE)
RE_HL_KAMERS = re.compile(r"Aantal\s*kamers\D{0,60}?(\d{1,2})", re.IGNORECASE)
RE_HL_POSTCODE = re.compile(r"\b(\d{4}\s?[A-Z]{2})\b")


def _hl_kenmerken_cache():
    try:
        with open(HL_KENMERKEN_PAD, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def huislijn_kenmerken(url, cache, opgehaald):
    """
    Oppervlakte, kamers en postcode van een Huislijn-advertentie.

    Eenmaal opgehaald blijft het in de cache staan: een pand dat in meerdere
    mails voorkomt wordt niet twee keer bevraagd. Lukt het ophalen niet, dan
    komt er niets terug en blijft de waarneming gewoon staan zonder
    oppervlakte; dat is hoe het hiervoor altijd was.
    """
    sleutel = re.sub(r"[?#].*$", "", url)
    if sleutel in cache:
        return cache[sleutel]
    if opgehaald[0] >= HL_MAX_OPHALEN:
        return {}
    if os.environ.get("HUISLIJN_KENMERKEN", "1") == "0":
        return {}
    opgehaald[0] += 1
    try:
        verzoek = urllib.request.Request(
            sleutel, headers={"User-Agent": "Mozilla/5.0 (vastgoedbrief)"})
        with urllib.request.urlopen(verzoek, timeout=20) as antwoord:
            rauw = antwoord.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa
        print(f"    kenmerken niet op te halen ({str(e)[:60]}): {sleutel[:70]}",
              file=sys.stderr)
        return {}
    tekst = " | ".join(strip_html(rauw))
    uit = {}
    m = RE_HL_OPP.search(tekst)
    if m:
        try:
            opp = int(m.group(1))
            # Een woonoppervlakte onder 10 of boven 1000 m2 is geen woning maar
            # een ander getal dat per ongeluk is meegepakt.
            if 10 <= opp <= 1000:
                uit["opp"] = opp
        except ValueError:
            pass
    m = RE_HL_KAMERS.search(tekst)
    if m:
        try:
            uit["kamers"] = int(m.group(1))
        except ValueError:
            pass
    m = RE_HL_POSTCODE.search(tekst)
    if m:
        uit["postcode"] = m.group(1).replace(" ", "")
    cache[sleutel] = uit
    time.sleep(0.5)
    return uit


def _hl_straat_uit_slug(slug):
    """"jan-van-speykstraat" wordt "Jan van Speykstraat"."""
    klein = {"van", "de", "den", "der", "het", "ter", "te", "op", "aan"}
    delen = [d for d in slug.split("-") if d]
    if not delen:
        return None
    uit = []
    for i, d in enumerate(delen):
        if d == "st":
            # De slug laat de punt weg, maar ons aanbod kent "St. Annastraat".
            # Zonder de punt matcht het adres niet met wat er al in staat.
            uit.append("St.")
        elif i and d in klein:
            uit.append(d)
        else:
            uit.append(d.capitalize())
    return " ".join(uit)


def parse_huislijn(regels):
    """
    Leest een Huislijn-attendering: straatnaam en huurprijs, niets meer.

    Deze bron geeft geen huisnummer en geen oppervlakte. Daarmee kan er geen
    prijs per vierkante meter uit, en die is wat de doorrekening nodig heeft.
    De waarneming is dus beperkt bruikbaar: hij telt mee voor het aanbod en
    voor de dekking van wat er in de stad te huur staat, maar niet voor de
    gemeten huur per m2. Dat laatste gaat automatisch goed, want een regel
    zonder oppervlakte valt buiten die berekening.

    Straatnaam en prijs mogen op dezelfde regel staan of op aparte regels, en
    de straatnaam mag ook uit de link komen. Dat laatste is het betrouwbaarst.
    """
    gevonden, gezien, overgeslagen = [], set(), []
    vandaag = waarnemingsdatum()
    straat = None
    link = None
    cache = _hl_kenmerken_cache()
    opgehaald = [0]

    def bewaar(naam, prijs, url):
        if not (150 <= prijs <= 10000):
            overgeslagen.append(f"{naam} (huur €{prijs} onmogelijk)")
            return
        sleutel = (naam.lower(), prijs)
        if sleutel in gezien:
            return
        gezien.add(sleutel)
        # De mail geeft geen huisnummer en geen oppervlakte. De oppervlakte
        # staat wel op de advertentiepagina, dus die halen we daar op; zonder
        # oppervlakte valt de waarneming buiten de huur per m2.
        ken = huislijn_kenmerken(url, cache, opgehaald) if url else {}
        opp = ken.get("opp") or ""
        postcode = ken.get("postcode") or ""
        gevonden.append(f"{naam} | Nijmegen | {prijs} | te huur | "
                        f"{vandaag} | huislijn | {opp} | {postcode}")

    for regel in regels:
        kaal = regel.strip()
        if not kaal:
            continue
        laag = kaal.lower()
        # Een reclameregel mag de straatnaam niet overschrijven. Maar een regel
        # met een BEDRAG erin is geen reclame, ook als er "Bekijk deze woning"
        # achter staat: in de tekstomzetting zit dat vaak aan de prijsregel
        # vast, en daar sneuvelde vorm B op.
        ruis = (any(w in laag for w in HL_RUIS)
                and not RE_HL_HUUR.search(kaal))

        # De straatnaam, eerst uit de link en anders uit de tekst.
        kandidaat = None
        m_url = RE_HL_URL.search(kaal)
        if m_url:
            kandidaat = _hl_straat_uit_slug(m_url.group(1))
            m_vol = re.search(r"https?://[^\s\])]+", kaal)
            if m_vol:
                link = m_vol.group(0)
        if not kandidaat and not ruis:
            m = RE_HL_STRAAT.search(kaal)
            if m:
                k = m.group(1).strip().strip("[]").strip()
                # "Op 7 oktober 2026 zijn er 8 nieuwe huizen gevonden" bevat
                # geen straatnaam; die regels dragen geen hoofdletter aan het
                # begin van het laatste woord of zijn te lang.
                if 3 <= len(k) <= 40 and "huislijn" not in k.lower():
                    kandidaat = k
        if kandidaat:
            straat = kandidaat

        # Het bedrag, waar het ook staat. Een los jaartal of huisnummer telt
        # niet mee, want er moet een euroteken voor staan.
        m_huur = RE_HL_HUUR.search(kaal)
        if m_huur and straat:
            bedrag = m_huur.group(1).rstrip(".,").replace(".", "").replace(",", "")
            try:
                bewaar(straat, int(bedrag), link)
            except ValueError:
                pass
            straat = None
            link = None
    if opgehaald[0]:
        print(f"    kenmerken opgehaald voor {opgehaald[0]} Huislijn-panden",
              file=sys.stderr)
        try:
            with open(HL_KENMERKEN_PAD, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=1)
        except Exception:
            pass
    return gevonden, overgeslagen


# ---------------------------------------------------------------------------
# 123Wonen
#
# De attendering zelf is vrijwel leeg: "Huurprijs EUR 2.425 per maand",
# "Nijmegen ()" en een link. Geen straat, geen oppervlakte. Achter die link
# staat wel alles, en meer dan bij Huislijn: het volledige adres met
# huisnummer, de oppervlakte, het aantal kamers, het bouwjaar en het label.
#
# Drie dingen waar je bij deze bron op moet letten, en die hieronder zijn
# afgedekt:
#
# 1. De postcode op de pagina is die van het kantoor van de makelaar
#    (Oranjesingel 51, 6511 NP) en niet die van de woning. Een algemene
#    postcodezoeker pakt de verkeerde. Wij laten de postcode daarom leeg; met
#    een huisnummer haalt de BAG hem zelf op.
# 2. De opgegeven woonoppervlakte kan een souterrain bevatten. Bij de Van
#    Spaenstraat staat "Woonoppervlakte 103 m2" in de specificaties, terwijl de
#    omschrijving spreekt van circa 65 m2 woonoppervlakte plus een souterrain
#    van 38 m2. Dat is 59% verschil in de huur per m2. Klopt de som, dan nemen
#    we de woonoppervlakte uit de omschrijving.
# 3. Het aanbod is vaak gemeubileerd. Dan zit de inrichting in de prijs en
#    hoort de waarneming niet in de mediaan, net als bij Pararius.
W1_KENMERKEN_PAD = "wonen123_kenmerken.json"
W1_MAX_OPHALEN = 25
RE_W1_URL = re.compile(r"123wonen[^\s)\]]*", re.IGNORECASE)
# De objectpagina zoals we hem nodig hebben: /huur/<plaats>/<type>/<slug>. In
# een doorstuurlink staat hij vaak percent-gecodeerd als parameter.
# Twee vormen van een objectpagina. De lange staat in de adresbalk als je
# doorklikt vanaf het aanbod; de korte is waar de mail op uitkomt en die is
# het echte adres van de advertentie: /w/1780-27.
RE_W1_OBJECT = re.compile(
    r"https?://(?:[a-z0-9\-]+\.)*123wonen\.nl/"
    r"(?:huur/[a-z\-]+/[a-z\-]+/[a-z0-9\-]+|w/\d+[\d\-]*)",
    re.IGNORECASE)


# Links in een 123Wonen-mail die nooit een woning zijn. De attendering opent
# met "Kijk altijd op onze website" en sluit met een afmeldlink, en de eerste
# stond VOOR de prijs. Daardoor werd de homepagina als objectlink gebruikt,
# opgehaald, en vond de parser daar geen adres: precies de melding "geen adres
# te vinden" die twee mails opleverden.
W1_GEEN_OBJECT = ("dounsubscribe", "/woningmail", "unsubscribe", "/afmelden",
                  "/privacy", "/sitemap", "/contact", "/over-ons",
                  "/vacatures", "/algemene-voorwaarden", "/referenties",
                  "/blog", "/beleggen", "/franchise")
# De mail gaat via SendGrid, en dan staat elke link op een eigen domein:
# https://u5283813.ct.sendgrid.net/ls/click?upn=... Het domein zegt dus niets
# meer over de bestemming; het pad wel. Wij zitten hier al in een mail die als
# 123Wonen is herkend, dus een klikteller in deze mail is een 123Wonen-link.
RE_W1_TRACKER = re.compile(
    r"https?://[^\s)\]]*?(?:/ls/click|/wf/click|/c/|/cl/|/click|/r/|/track"
    r"|/tr/|/redirect)[^\s)\]]*", re.IGNORECASE)
# De tekst achter de link. strip_html zet de link op een eigen regel, dus de
# ankertekst staat op de regels erna. Dat is het betrouwbaarste onderscheid dat
# we hebben zodra alle links op hetzelfde klikdomein staan.
W1_LINKTEKST_JA = ("bekijk deze woning", "bekijk de woning", "bekijk woning",
                   "uitgebreide presentatie", "meer informatie over deze")
W1_LINKTEKST_NEE = ("afmeld", "unsubscribe", "woningmail", "onze website",
                    "actuele aanbod", "privacy", "voorwaarden", "sitemap",
                    "klik dan hier", "vacature", "referenties",
                    "wenst u geen")


def _w1_objectlink(regel):
    """
    De objectlink uit een regel, ook uit een doorstuurlink.

    Drie poorten, van zeker naar waarschijnlijk:

    1. Een rechtstreekse objectpagina: /huur/<plaats>/<type>/<slug>. Staat die
       percent-gecodeerd in een klikteller, dan vindt hij hem na decoderen.
    2. Een klikteller zonder zichtbare bestemming. Die herken je aan een pad
       met een lange ondoorzichtige code erin; urllib volgt de doorverwijzing
       zelf, dus zo'n link werkt ook.
    3. Niets. Dan is er geen woning uit te halen en wordt dat gemeld.

    Wat er expliciet NIET door mag: de homepagina en de vaste sitepagina's. Die
    hebben geen of een kort pad zonder code, en juist die stonden in de mail
    boven de prijs.
    """
    kandidaten = [regel]
    try:
        ontcodeerd = urllib.parse.unquote(regel)
        if ontcodeerd != regel:
            kandidaten.append(ontcodeerd)
    except Exception:
        pass
    for kandidaat in kandidaten:
        m = RE_W1_OBJECT.search(kandidaat)
        if m:
            return m.group(0).rstrip(").,")
    for kandidaat in kandidaten:
        for m in RE_W1_TRACKER.finditer(kandidaat):
            url = m.group(0).rstrip(").,")
            laag = url.lower()
            if any(w in laag for w in W1_GEEN_OBJECT):
                continue
            if not re.search(r"[a-z0-9]{10,}", laag.split("?", 1)[-1] + laag):
                continue
            return url
    for kandidaat in kandidaten:
        for m in re.finditer(r"https?://[^\s)\]]+", kandidaat):
            url = m.group(0).rstrip(").,")
            laag = url.lower()
            if "123wonen" not in laag:
                continue
            if any(w in laag for w in W1_GEEN_OBJECT):
                continue
            pad = re.sub(r"^https?://[^/]+", "", laag)
            if len(pad.strip("/")) < 10:
                continue
            # Een sitepagina zoals /huren of /aanbod heeft geen code in het pad.
            if not re.search(r"[a-z0-9]{10,}", pad):
                continue
            return url
    return None
RE_W1_SLUG = re.compile(r"123wonen\.nl/huur/[a-z\-]+/[a-z\-]+/([a-z0-9\-]+)",
                        re.IGNORECASE)
# Bij de korte vorm /w/1780-27 zit er geen straatnaam in de link. De pagina
# heeft er zelf een die even goed is: het kruimelpad, "Aanbod / Nijmegen - van
# Spaenstraat". Daarmee blijft de toets op het adres bestaan, en dat is nodig,
# want verderop staat een blok "Vergelijkbaar aanbod" met andere adressen.
RE_W1_KRUIMEL = re.compile(
    r"Aanbod\s*/\s*[A-Za-zÀ-ÿ.'\- ]{3,30}?\s+-\s+"
    r"([A-Za-zÀ-ÿ.'\- ]{3,40}?)\s*(?:\||$)", re.IGNORECASE)
RE_W1_HUUR = re.compile(r"Huurprijs\s*€\s*([\d][\d.,]*)", re.IGNORECASE)
RE_W1_ADRES = re.compile(
    r"\b([A-Za-zÀ-ÿ.'\-]+(?:\s+[A-Za-zÀ-ÿ.'\-]+){0,3}?)\s+(\d{1,4})\s*,\s*"
    r"Nijmegen\b")
RE_W1_OPP = re.compile(r"Woonoppervlakte\D{0,20}?(\d{2,4})\s*m", re.IGNORECASE)
RE_W1_OPP_TEKST = re.compile(r"circa\s+(\d{2,4})\s*m.{0,3}?\s*woonoppervlakte",
                             re.IGNORECASE)
RE_W1_SOUT = re.compile(r"(?:souterrain|kelderruimte|kelder)\D{0,60}?(\d{2,3})"
                        r"\s*m", re.IGNORECASE)
RE_W1_KAMERS = re.compile(r"\bKamers\s*(\d{1,2})\b", re.IGNORECASE)
RE_W1_BOUWJAAR = re.compile(r"\bBouwjaar\s*(1[6-9]\d\d|20[0-2]\d)\b",
                            re.IGNORECASE)
RE_W1_LABEL = re.compile(r"Energielabel\s*([A-G]\+{0,4})\b")


def _w1_cache():
    try:
        with open(W1_KENMERKEN_PAD, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _w1_straat_uit_slug(slug):
    """
    "van-spaenstraat-20" wordt "van Spaenstraat", zonder huisnummer.

    Het nummer uit de slug laten we bewust vallen. Bij "aldenhof-1761-27" is
    niet te zeggen of 27 een huisnummer of een advertentienummer is, en een
    verkeerd huisnummer is erger dan geen huisnummer: dan matcht de BAG een
    andere woning. Het huisnummer komt alleen van de pagina zelf.
    """
    delen = [d for d in slug.split("-") if d and not d.isdigit()]
    return _hl_straat_uit_slug("-".join(delen)) if delen else None


def wonen123_kenmerken(url, cache, opgehaald):
    """
    Adres, oppervlakte, kamers, bouwjaar en label van een 123Wonen-advertentie.

    Het huisnummer wordt alleen overgenomen als de straat uit de pagina
    overeenkomt met de straat uit de link. Zo kan een adres uit een blok
    "vergelijkbaar aanbod" nooit voor het adres van deze woning doorgaan.
    """
    kaal = re.sub(r"[?#].*$", "", url)
    # Bij een rechtstreekse objectlink zijn de parameters telcodes en mogen ze
    # eraf. Bij een klikteller zit de bestemming erin en moet de hele URL
    # blijven staan, anders halen we een lege doorstuurpagina op.
    sleutel = kaal if RE_W1_OBJECT.fullmatch(kaal) else url
    if sleutel in cache:
        return cache[sleutel]
    if opgehaald[0] >= W1_MAX_OPHALEN:
        return {}
    if os.environ.get("WONEN123_KENMERKEN", "1") == "0":
        return {}
    opgehaald[0] += 1
    try:
        verzoek = urllib.request.Request(
            sleutel, headers={"User-Agent": "Mozilla/5.0 (vastgoedbrief)"})
        with urllib.request.urlopen(verzoek, timeout=20) as antwoord:
            rauw = antwoord.read().decode("utf-8", errors="replace")
            # Waar de klikteller op uitkwam. Die URL is de echte objectpagina
            # en daarmee de sleutel die over mails heen hetzelfde blijft; de
            # klikteller zelf is per mail anders.
            eind = antwoord.geturl() or sleutel
    except Exception as e:  # noqa
        print(f"    kenmerken niet op te halen ({str(e)[:60]}): {sleutel[:70]}",
              file=sys.stderr)
        return {}
    eind_kaal = re.sub(r"[?#].*$", "", eind)
    uit = _w1_lees_pagina(" | ".join(strip_html(rauw)), eind_kaal)
    cache[sleutel] = uit
    if eind_kaal != sleutel and RE_W1_OBJECT.fullmatch(eind_kaal):
        cache[eind_kaal] = uit
    time.sleep(0.5)
    return uit


def _w1_lees_pagina(tekst, url=""):
    """De kenmerken uit de paginatekst. Apart, zodat hij te testen is."""
    uit = {}
    slug = RE_W1_SLUG.search(url or "")
    straat_link = _w1_straat_uit_slug(slug.group(1)) if slug else None
    if not straat_link:
        m_kruimel = RE_W1_KRUIMEL.search(tekst)
        if m_kruimel:
            straat_link = m_kruimel.group(1).strip()

    plat = lambda s: re.sub(r"[^a-z]", "", (s or "").lower())
    m = RE_W1_ADRES.search(tekst)
    if m and (not straat_link
              or plat(m.group(1).strip()) == plat(straat_link)):
        uit["adres"] = f"{m.group(1).strip()} {m.group(2)}"
    elif straat_link:
        # Tweede route naar het huisnummer. De vorm "Straat 20, Nijmegen" staat
        # alleen in het contactformulier onderaan, en dat kan door de pagina
        # zelf worden ingevuld en dus in de opgehaalde HTML ontbreken. De
        # straat kennen we al uit het kruimelpad, dus er is maar een nummer
        # nodig, en dat staat ook in de omschrijving: "aan de Van Spaenstraat
        # 20 combineert". Omdat de straatnaam vooraf bekend is, kan hier geen
        # nummer van een andere straat tussendoor komen.
        nr = re.search(re.escape(straat_link) + r"\s+(\d{1,4}[a-zA-Z]?)\b"
                       r"(?!\s*(?:m²|m2|%))", tekst, re.IGNORECASE)
        uit["adres"] = (f"{straat_link} {nr.group(1)}" if nr else straat_link)

    opp = tekst_opp = sout = None
    m = RE_W1_OPP.search(tekst)
    if m:
        opp = int(m.group(1))
    m = RE_W1_OPP_TEKST.search(tekst)
    if m:
        tekst_opp = int(m.group(1))
    m = RE_W1_SOUT.search(tekst)
    if m:
        sout = int(m.group(1))
    # Alleen als de som klopt staat vast dat het souterrain in de opgegeven
    # oppervlakte zit. Dan is de omschrijving het eerlijkere getal.
    if opp and tekst_opp and sout and abs(tekst_opp + sout - opp) <= 2:
        uit["opp_advertentie"] = opp
        uit["souterrain"] = sout
        opp = tekst_opp
    if opp and 10 <= opp <= 1000:
        uit["opp"] = opp

    for naam, regex, omzet in (("kamers", RE_W1_KAMERS, int),
                               ("bouwjaar", RE_W1_BOUWJAAR, int),
                               ("label", RE_W1_LABEL, str)):
        m = regex.search(tekst)
        if m:
            try:
                uit[naam] = omzet(m.group(1))
            except ValueError:
                pass

    laag = tekst.lower()
    if "ongemeubileerd" in laag or "ongemeubeld" in laag:
        uit["staat"] = "kaal"
    elif "gestoffeerd of gemeubileerd" in laag:
        uit["staat"] = "gestoffeerd"
    elif "gemeubileerd" in laag or "gemeubeld" in laag:
        uit["staat"] = "gemeubileerd"
    elif "gestoffeerd" in laag:
        uit["staat"] = "gestoffeerd"
    return uit


def parse_123wonen(regels):
    """
    Leest een 123Wonen-attendering: de prijs uit de mail, de rest van de pagina.

    Zonder link is er niets: de mail noemt de straat niet. Zo'n regel wordt
    overgeslagen en gemeld, zodat het zichtbaar is in plaats van stil.
    """
    gevonden, gezien, overgeslagen = [], set(), []
    vandaag = waarnemingsdatum()
    cache = _w1_cache()
    opgehaald = [0]
    prijs = None
    link = None

    def bewaar(prijs, url):
        ken = wonen123_kenmerken(url, cache, opgehaald)
        adres = ken.get("adres")
        if not adres:
            overgeslagen.append(f"123wonen €{prijs} (geen adres te vinden)")
            return
        sleutel = (adres.lower(), prijs)
        if sleutel in gezien:
            return
        gezien.add(sleutel)
        opp = ken.get("opp") or ""
        status = ("te huur gemeubileerd" if ken.get("staat") == "gemeubileerd"
                  else "te huur")
        if ken.get("staat") == "gemeubileerd":
            overgeslagen.append(f"{adres} (gemeubileerd, apart bewaard)")
        if ken.get("souterrain"):
            overgeslagen.append(
                f"{adres} (advertentie noemt {ken['opp_advertentie']} m2, "
                f"waarvan {ken['souterrain']} m2 souterrain; {opp} m2 gebruikt)")
        gevonden.append(f"{adres} | Nijmegen | {prijs} | {status} | "
                        f"{vandaag} | 123wonen | {opp} | ")

    # Welke link bij welke prijs hoort, is niet uit de URL te halen zodra de
    # mail via SendGrid gaat: dan staan de homepagina, de woning en de
    # afmeldlink alle drie op hetzelfde klikdomein. Twee dingen onderscheiden
    # ze wel, en die gebruiken we in deze volgorde:
    #
    # 1. De tekst achter de link. "Bekijk deze woning" is de woning, "Wenst u
    #    geen woningmail" is het niet. strip_html zet de link op een eigen
    #    regel, dus die tekst staat op de regels erna.
    # 2. De plaats in de mail. De woninglink staat kort NA het bedrag, in
    #    hetzelfde blok. De homepagina staat in de begroeting erboven, en die
    #    werd daardoor eerder als woning opgehaald.
    schoon = [r.strip() for r in regels if r.strip()]

    def omringend(i):
        """De regel voor en de regel na de link, want daar staat de tekst.

        Alleen die twee. Met een ruimer venster slikte de woninglink de regel
        "Wenst u geen woningmail meer te ontvangen" van het blok eronder mee,
        en viel hij af op de afmeldtekst van de mail zelf.
        """
        deel = []
        if i > 0:
            deel.append(schoon[i - 1])
        if i + 1 < len(schoon):
            deel.append(schoon[i + 1])
        return " ".join(deel).lower()

    # Alle links en alle prijzen met hun plaats in de mail.
    links, prijzen = [], []
    for i, regel in enumerate(schoon):
        url = _w1_objectlink(regel)
        if url:
            tekst = omringend(i)
            links.append({"i": i, "url": url, "tekst": tekst,
                          "ja": any(w in tekst for w in W1_LINKTEKST_JA),
                          "nee": any(w in tekst for w in W1_LINKTEKST_NEE)})
        m = RE_W1_HUUR.search(regel)
        if m:
            bedrag = m.group(1).rstrip(".,").replace(".", "").replace(",", "")
            try:
                bedrag = int(bedrag)
            except ValueError:
                continue
            if 150 <= bedrag <= 10000:
                prijzen.append({"i": i, "prijs": bedrag})

    gebruikt = set()
    for p in prijzen:
        # Eerst een link met "bekijk deze woning" erachter, waar hij ook staat
        # binnen dit blok. Anders de eerste bruikbare link na het bedrag.
        keuze = None
        na = [l for l in links if l["i"] > p["i"] and l["i"] not in gebruikt
              and not l["nee"]]
        volgende_prijs = min((q["i"] for q in prijzen if q["i"] > p["i"]),
                             default=len(schoon))
        binnen_blok = [l for l in na if l["i"] < volgende_prijs]
        for l in binnen_blok:
            if l["ja"]:
                keuze = l
                break
        if keuze is None and binnen_blok:
            keuze = binnen_blok[0]
        if keuze is None:
            overgeslagen.append(f"123wonen €{p['prijs']} (geen link)")
            continue
        gebruikt.add(keuze["i"])
        bewaar(p["prijs"], keuze["url"])
    # Komt er niets uit, dan is de vorm van de mail anders dan verwacht. Zonder
    # te zien wat er dan wel staat is dat niet op te lossen, dus zetten we de
    # eerste regels in het logboek. Dit is de enige manier om een parser te
    # repareren op een mail die wij niet in handen hebben.
    if not gevonden:
        print("    123Wonen leverde niets op. Alle links en prijsregels uit "
              "deze mail:", file=sys.stderr)
        geprint = 0
        for regel in regels:
            kaal = regel.strip()
            if not kaal or geprint >= 20:
                continue
            if ("http" in kaal.lower() or "__LINK__" in kaal
                    or RE_W1_HUUR.search(kaal)):
                print(f"      | {kaal[:220]}", file=sys.stderr)
                geprint += 1
        if not geprint:
            print("      | (geen enkele link en geen prijsregel gevonden)",
                  file=sys.stderr)
    if opgehaald[0]:
        print(f"    kenmerken opgehaald voor {opgehaald[0]} 123Wonen-panden",
              file=sys.stderr)
        try:
            with open(W1_KENMERKEN_PAD, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=1)
        except Exception:
            pass
    return gevonden, overgeslagen


def parse_pararius(regels):
    """Leest een Pararius-overzicht met kale huurprijs, oppervlakte en buurt."""
    gevonden, gezien, overgeslagen = [], set(), []
    vandaag = waarnemingsdatum()

    for i, regel in enumerate(regels):
        pc = RE_PA_POSTCODE.match(regel)
        if not pc:
            continue
        postcode, plaats, buurt = (pc.group(1).replace(" ", ""),
                                   pc.group(2).strip(), pc.group(3).strip())
        if plaats.lower() not in ("nijmegen", "lent"):
            continue

        # Boven de postcode staat de straat. Vroeger als "Appartement
        # Berg en Dalseweg", nu vaak alleen "Berg en Dalseweg". We nemen de
        # soort mee als die er is, en anders de kale straatnaam.
        soort = straat = None
        for j in range(i - 1, max(-1, i - 6), -1):
            tm = RE_PA_TITEL.match(regels[j])
            if tm:
                soort, straat = tm.group(1).lower(), tm.group(2).strip()
                break
        if not straat and i > 0:
            kandidaat = regels[i - 1].strip()
            # Een straatnaam: letters, geen prijs, geen reclametekst
            if (kandidaat and not any(c.isdigit() for c in kandidaat)
                    and "€" not in kandidaat and len(kandidaat) < 60
                    and not any(w in kandidaat.lower() for w in
                                ("pararius", "bekijk", "zoekopdracht", "woning",
                                 "kijkje", "ontdek"))):
                straat = kandidaat
        if not straat:
            continue

        # Kale huurprijs heeft voorrang boven de totale huurprijs
        prijs = None
        kale_gezien = False
        for j in range(i + 1, min(len(regels), i + 12)):
            if "kale huurprijs" in regels[j].lower():
                kale_gezien = True
                continue
            if "totale huurprijs" in regels[j].lower() and prijs:
                break  # kale huur al binnen, de rest negeren
            pm = RE_PA_PRIJS.match(regels[j])
            if pm and prijs is None:
                prijs = int(pm.group(1).replace(".", ""))
                if not kale_gezien:
                    break  # er is maar een prijs, dus dat is de huur
                break

        opp = kamers = bouwjaar = None
        gemeubileerd = False
        for j in range(i + 1, min(len(regels), i + 16)):
            om = RE_PA_OPP.match(regels[j])
            if om:
                opp = int(om.group(1))
                km = RE_PA_KAMERS.search(regels[j])
                kamers = int(km.group(1)) if km else None
                bj = RE_PA_BOUWJAAR.search(regels[j])
                bouwjaar = int(bj.group(1)) if bj else None
                # Gemeubileerd is een andere markt: de huur ligt hoger omdat de
                # inrichting erbij zit. "Gestoffeerd of gemeubileerd" telt als
                # gestoffeerd, want dan kan de huurder kiezen.
                laag = regels[j].lower()
                gemeubileerd = ("gemeubileerd" in laag
                                and "gestoffeerd" not in laag)
                break

        beheerder = ""
        for j in range(i + 1, min(len(regels), i + 18)):
            if RE_PA_POSTCODE.match(regels[j]) or RE_PA_TITEL.match(regels[j]):
                break  # volgend object begint hier
            if regels[j].strip() and not any(c.isdigit() for c in regels[j]):
                beheerder = regels[j].strip().lower()
        if any(u in beheerder for u in PA_UITSLUITEN):
            overgeslagen.append(f"{straat} (leegstandbeheer)")
            continue

        if not (prijs and opp):
            overgeslagen.append(f"{straat} (onvolledig)")
            continue
        # Gemeubileerd telt niet mee in de mediaan, want de inrichting zit in
        # de prijs. Weggooien is wel zonde: het is een route die een verhuurder
        # kan kiezen, en met genoeg waarnemingen is de opslag te meten in plaats
        # van te schatten. Daarom een eigen status, zodat hij bewaard blijft en
        # nergens meetelt waar hij niet hoort.
        status = ("te huur gemeubileerd" if gemeubileerd
                  else "te huur kamer" if soort == "kamer" else "te huur")
        if gemeubileerd:
            overgeslagen.append(f"{straat} (gemeubileerd, apart bewaard)")
        sleutel = (straat.lower(), prijs, opp)
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        gevonden.append(f"{straat} | {plaats} | {prijs} | {status} | {vandaag} "
                        f"| pararius | {opp} | {postcode}")
    return gevonden, overgeslagen




# Vendr is een biedplatform: objecten worden bij opbod aangeboden, dus er staat
# geen vraagprijs in de mail. Het adres staat op een regel met de postcode
# erachter, gescheiden door een komma.
RE_VENDR = re.compile(
    r"^\s*([A-Za-zÀ-ÿ.'\- ]+?\s+\d+[A-Za-z]?)\s*,\s*(\d{4}\s?[A-Z]{2})\s+"
    r"([A-Za-zÀ-ÿ\-' ]+?)\s*$")

VENDR_PLAATSEN = ("nijmegen", "lent", "weurt", "beuningen", "malden",
                  "berg en dal", "ubbergen", "elst", "bemmel")


def parse_vendr(regels):
    """
    Leest een Vendr-attendering. Geen prijs, want er wordt geboden. We leggen
    het adres vast; de brief rekent er zelf een maximum bod bij uit.
    """
    gevonden, gezien, overgeslagen = [], {}, []
    plaatsen = {}
    vandaag = waarnemingsdatum()
    for i, regel in enumerate(regels):
        m = RE_VENDR.match(regel)
        if not m:
            continue
        adres, postcode, plaats = (m.group(1).strip(),
                                   m.group(2).replace(" ", ""),
                                   m.group(3).strip())

        if plaats.lower() not in VENDR_PLAATSEN:
            overgeslagen.append(f"{adres} ({plaats})")
            continue
        plaatsen[postcode] = plaats
        # In de kopregel staat de projectnaam voor het adres geplakt, verderop
        # staat het adres los. We groeperen op postcode en huisnummer en houden
        # de kortste schrijfwijze over.
        nr = re.search(r"(\d+[A-Za-z]?)\s*$", adres)
        sleutel = (postcode, nr.group(1) if nr else adres.lower())
        if sleutel not in gezien or len(adres) < len(gezien[sleutel]):
            gezien[sleutel] = adres

    for (postcode, _nr), adres in gezien.items():
        plaats = plaatsen.get(postcode, "Nijmegen")
        # Prijs 0 betekent: bij opbod, nog geen vraagprijs
        gevonden.append(f"{adres} | {plaats} | 0 | bieden | {vandaag} "
                        f"| vendr |  | {postcode}")
    return gevonden, overgeslagen


def bestaande_adressen(pad):
    """Adressen die al in verkopen.txt staan, om dubbelingen te vermijden."""
    bestaand = set()
    if not os.path.exists(pad):
        return bestaand
    with open(pad, encoding="utf-8") as f:
        for regel in f:
            regel = regel.strip()
            if not regel or regel.startswith("#"):
                continue
            delen = [d.strip() for d in regel.split("|")]
            if len(delen) >= 3:
                bestaand.add((delen[0].lower(), re.sub(r"[^\d]", "", delen[2])))
    return bestaand


def tel_kandidaten(verbinding, sinds):
    """
    Hoeveel post er komt van platforms waar we nog geen parser voor hebben.

    Alleen tellen, niet lezen. Zo zie je in het rapport dat een aanmelding
    werkt, en weten we welke parser het eerst de moeite waard is.
    """
    uit = {}
    for domein in KANDIDATEN:
        if any(domein in a for a in AFZENDERS):
            continue
        try:
            status, data = verbinding.search(
                None, f'(FROM "{domein}" SINCE {sinds})')
            if status == "OK":
                aantal = len((data[0] or b"").split())
                if aantal:
                    uit[domein] = aantal
        except Exception:
            continue
    return uit


def bewaar_stand(tellers, opmerking="", kandidaten=None):
    """
    De mailstand wegschrijven, ook als er niets te doen viel.

    Zonder dit zag het gezondheidsrapport geen verschil tussen "de stap draaide
    niet" en "er waren geen mails".
    """
    try:
        with open("mail_status.json", "w", encoding="utf-8") as f:
            json.dump({"datum": dt.date.today().isoformat(),
                       "bronnen": tellers, "opmerking": opmerking,
                       "kandidaten": kandidaten or {}},
                      f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true",
                    help="toon wat er toegevoegd zou worden, schrijf niets weg")
    # Standaard ook gelezen mails van de laatste dagen: Mark leest de
    # attenderingen zelf, en dan zag het script ze nooit meer. Ontdubbelen
    # gebeurt toch op het object, dus dubbel kijken kost niets.
    ap.add_argument("--dagen", type=int, default=3,
                    help="kijk ook naar gelezen mails van de laatste N dagen")
    ap.add_argument("--uit", default=VERKOPEN_PAD)
    args = ap.parse_args()
    # Per bron bijhouden hoeveel mails er waren en hoeveel objecten eruit
    # kwamen. Stond deze regel er niet, dan liep de stap stuk op de eerste mail.
    tellers = {}

    # Duidelijk zeggen wat er wel en niet is meegekomen. "ontbreekt" alleen
    # zegt niet welke van de twee, en of het secret leeg is of niet doorgegeven.
    print(f"Mailgegevens: gebruikersnaam "
          f"{'aanwezig' if GEBRUIKER else 'ONTBREEKT'}, wachtwoord "
          f"{'aanwezig' if WACHTWOORD else 'ONTBREEKT'}", file=sys.stderr)
    if not GEBRUIKER or not WACHTWOORD:
        print("Zonder beide komt er geen aanbod binnen. Staan MAIL_USERNAME en "
              "MAIL_PASSWORD als secret in de repo, en staan ze bij deze stap "
              "in het env-blok?", file=sys.stderr)
        bewaar_stand({}, "geen mailgegevens in deze stap")
        return

    try:
        verbinding = imaplib.IMAP4_SSL(IMAP_HOST)
        verbinding.login(GEBRUIKER, WACHTWOORD)
        verbinding.select("INBOX")
    except Exception as e:
        print(f"Kan niet inloggen op de mailbox: {e}", file=sys.stderr)
        print("Staat IMAP aan in Gmail, en klopt het app-wachtwoord?", file=sys.stderr)
        bewaar_stand({}, f"inloggen mislukt: {str(e)[:100]}")
        return

    ids = set()
    # Buiten de lus, want de kandidaattelling verderop gebruikt hem ook.
    sinds = ((dt.date.today() - dt.timedelta(days=args.dagen or 3))
             .strftime("%d-%b-%Y"))
    for afzender in AFZENDERS:
        zoek = f'(FROM "{afzender}")'
        if args.dagen:
            zoek = f'(FROM "{afzender}" SINCE {sinds})'
        else:
            zoek = f'(UNSEEN FROM "{afzender}")'
        try:
            status, data = verbinding.search(None, zoek)
            if status == "OK":
                ids.update(data[0].split())
        except Exception as e:
            print(f"Zoekfout bij {afzender}: {e}", file=sys.stderr)

    print(f"Gevonden berichten van Funda: {len(ids)}", file=sys.stderr)
    if not ids:
        verbinding.logout()
        return

    bestaand = bestaande_adressen(args.uit)
    nieuwe_regels, alle_overgeslagen = [], []

    for mid in sorted(ids):
        try:
            status, data = verbinding.fetch(mid, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                continue
            bericht = email.message_from_bytes(data[0][1])
            global _DATUM_VAN_MAIL
            _DATUM_VAN_MAIL = datum_van_mail(bericht)
        except Exception as e:
            print(f"Kan bericht {mid} niet lezen: {e}", file=sys.stderr)
            continue

        onderwerp = ""
        try:
            stukken = decode_header(bericht.get("Subject", ""))
            onderwerp = "".join(
                (s.decode(c or "utf-8", errors="replace") if isinstance(s, bytes) else s)
                for s, c in stukken)
        except Exception:
            pass

        regels = haal_tekst(bericht)
        blob = " ".join(regels).lower()
        afzender = (bericht.get("From", "") or "").lower()

        # Per bron een ander basisgeval. Kamernet gaat over onzelfstandige
        # eenheden; die moeten apart blijven, anders trekken ze de huur per m2
        # voor gewone woningen omhoog.
        if "vendr" in afzender or "vendr" in blob:
            soort_bron, status_label = "vendr", "bieden"
        elif "kamernet" in afzender or "kamernet" in blob:
            soort_bron, status_label = "kamernet", "te huur kamer"
        elif "pararius" in afzender or "pararius" in blob:
            soort_bron, status_label = "pararius", "te huur"
        elif "huislijn" in afzender or "huislijn" in blob:
            soort_bron, status_label = "huislijn", "te huur"
        elif "123wonen" in afzender or "123wonen" in blob:
            soort_bron, status_label = "123wonen", "te huur"
        elif "funda in business" in blob or "bedrijfspanden" in blob:
            soort_bron, status_label = "business", "belegging"
        else:
            soort_bron, status_label = "regulier", "te koop"
            # Sinds het filter op verkocht aanstaat komen er ook mails over
            # panden die zijn verkocht of onder voorbehoud staan. Zonder dit
            # kwamen die als "te koop" binnen en bleef een verkocht pand
            # eeuwig in het aanbod staan.
            # Nieuwbouw apart houden. Een prijs vrij op naam is niet
            # vergelijkbaar met kosten koper, en een bouwnummer is geen
            # bestaande woning. In de mediaan per m2 of in de groottepremie
            # hoort het dus niet. De status heet "project" en niet
            # "nieuwbouw": negen filters in andere modules matchen op het
            # voorvoegsel "nieuw" en zouden het dan alsnog als aanbod zien.
            if any(w in blob for w in ("nieuwbouwwoning", "bouwnr.", "v.o.n.",
                                       "vrij op naam")):
                status_label = "project"
            # Funda vat drie stadia samen als "in onderhandeling": onder bod,
            # onder optie en verkocht onder voorbehoud. We bewaren het stadium
            # dat in de mail staat, want ze zeggen niet hetzelfde.
            if "verkocht onder voorbehoud" in blob:
                status_label = "verkocht onder voorbehoud"
            elif "onder optie" in blob:
                status_label = "onder optie"
            elif "onder bod" in blob:
                status_label = "onder bod"
            elif "in onderhandeling" in blob:
                status_label = "in onderhandeling"
            elif "verkocht" in blob:
                status_label = "verkocht"

        if soort_bron == "vendr":
            objecten, overgeslagen = parse_vendr(regels)
        elif soort_bron == "kamernet":
            objecten, overgeslagen = parse_kamernet(regels)
            if not objecten:
                objecten, overgeslagen = parse_kamernet_attendering(regels)
        elif soort_bron == "pararius":
            objecten, overgeslagen = parse_pararius(regels)
        elif soort_bron == "huislijn":
            objecten, overgeslagen = parse_huislijn(regels)
        elif soort_bron == "123wonen":
            objecten, overgeslagen = parse_123wonen(regels)
        else:
            objecten, overgeslagen = parse_objecten(regels, status_label)
        alle_overgeslagen.extend(overgeslagen)

        toegevoegd = 0
        for regel in objecten:
            delen = [d.strip() for d in regel.split("|")]
            # Adres plus prijs: staat het adres er al met een ANDERE prijs, dan is
            # dat een prijswijziging en dus juist wel de moeite van vastleggen waard.
            sleutel = (delen[0].lower(), delen[2])
            if sleutel in bestaand:
                continue
            bestaand.add(sleutel)
            nieuwe_regels.append(regel)
            toegevoegd += 1

        tellers.setdefault(soort_bron, {"mails": 0, "objecten": 0,
                                        "overgeslagen": 0, "redenen": []})
        tellers[soort_bron]["mails"] += 1
        tellers[soort_bron]["objecten"] += len(objecten)
        # Ook vastleggen wat er bewust is overgeslagen, met de reden. Zonder dat
        # onderscheid is "42 mails, 14 objecten" niet te duiden: terecht
        # overgeslagen of niet begrepen zijn twee heel verschillende dingen.
        tellers[soort_bron]["overgeslagen"] += len(overgeslagen or [])
        for reden in (overgeslagen or [])[:3]:
            if len(tellers[soort_bron]["redenen"]) < 5:
                tellers[soort_bron]["redenen"].append(str(reden)[:80])
        if not objecten and not overgeslagen:
            if len(tellers[soort_bron]["redenen"]) < 5:
                tellers[soort_bron]["redenen"].append(
                    f"niets herkend in: {onderwerp[:50]}")
        print(f"  [{soort_bron}] {onderwerp[:60]}: {len(objecten)} objecten, "
              f"{toegevoegd} nieuw", file=sys.stderr)

        # Niets herkend? Toon dan wat er in de mail stond, zodat we het formaat
        # kunnen zien zonder een aparte diagnoseronde.
        if not objecten:
            print(f"    Geen objecten herkend. Eerste regels van deze mail:",
                  file=sys.stderr)
            for regel in [x for x in regels if x.strip()][:35]:
                print(f"    | {regel[:110]}", file=sys.stderr)

        if not args.proef:
            try:
                verbinding.store(mid, "+FLAGS", "\\Seen")
            except Exception:
                pass

    verbinding.logout()

    if alle_overgeslagen:
        print(f"Overgeslagen ({len(alle_overgeslagen)}):", file=sys.stderr)
        for o in alle_overgeslagen[:10]:
            print(f"  {o}", file=sys.stderr)

    if not nieuwe_regels:
        print("Geen nieuwe objecten om toe te voegen", file=sys.stderr)
        return

    if args.proef:
        print("PROEF, niets weggeschreven. Dit zou erbij komen:", file=sys.stderr)
        for r in nieuwe_regels:
            print(f"  {r}", file=sys.stderr)
        return

    vandaag = dt.date.today().strftime("%d-%m-%Y")
    with open(args.uit, "a", encoding="utf-8") as f:
        f.write(f"\n# Automatisch toegevoegd uit Funda-attendering op {vandaag}\n")
        for r in nieuwe_regels:
            f.write(r + "\n")

    print(f"Toegevoegd aan {args.uit}: {len(nieuwe_regels)} objecten", file=sys.stderr)

    # Per bron vastleggen hoeveel mails er waren en hoeveel objecten eruit
    # kwamen. Zonder dit zie je niet of een bron zwijgt of dat de parser hem
    # niet begrijpt, en dat zijn twee heel verschillende problemen.
    # Wat er nog meer binnenkomt, van bronnen die we nog niet uitlezen.
    try:
        kandidaten = tel_kandidaten(verbinding, sinds)
    except Exception:
        kandidaten = {}
    if kandidaten:
        print("Post van bronnen zonder parser: "
              + ", ".join(f"{d}: {n}" for d, n in sorted(kandidaten.items())),
              file=sys.stderr)
    bewaar_stand(tellers, kandidaten=kandidaten)
    for bron, t in sorted(tellers.items()):
        print(f"  {bron}: {t['mails']} mails, {t['objecten']} objecten",
              file=sys.stderr)


if __name__ == "__main__":
    main()
