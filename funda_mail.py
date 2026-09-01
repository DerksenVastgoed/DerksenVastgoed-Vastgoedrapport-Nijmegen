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
import email
import imaplib
import os
import re
import sys
from email.header import decode_header

IMAP_HOST = "imap.gmail.com"
VERKOPEN_PAD = "verkopen.txt"
AFZENDERS = ["funda.nl", "funda.com", "pararius.nl", "pararius.com", "kamernet.nl"]

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
    # Objectlinks markeren voordat de tags verdwijnen
    tekst = re.sub(
        r'(?is)<a[^>]+href=["\']([^"\']*funda[^"\']*/(?:koop|huur|detail|object)[^"\']*)["\'][^>]*>',
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

        vandaag = dt.date.today().isoformat()
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
    vandaag = dt.date.today().isoformat()

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




# Pararius-overzicht. De buurt staat tussen haakjes achter de postcode, en waar
# een kale en een totale huurprijs staan nemen we de kale: die telt voor het
# rendement en voor het puntenstelsel.
RE_PA_POSTCODE = re.compile(
    r"^\s*(\d{4}\s?[A-Z]{2})\s+([A-Za-zÀ-ÿ\-' ]+?)\s*\(([^)]+)\)\s*$")
RE_PA_PRIJS = re.compile(r"^\s*€\s*([\d.]+)\s*per maand\s*$")
RE_PA_OPP = re.compile(r"^\s*(\d{1,4})\s*m[²2]\s*$")
RE_PA_TITEL = re.compile(
    r"^\s*(Appartement|Huis|Studio|Kamer|Woonboot|Bungalow)\s+(.+?)\s*$", re.I)

# Leegstandbeheer is geen markthuur en hoort niet in een mediaan thuis.
PA_UITSLUITEN = ("ad hoc", "camelot", "leegstandbeheer", "anti-kraak", "antikraak")


def parse_pararius(regels):
    """Leest een Pararius-overzicht met kale huurprijs, oppervlakte en buurt."""
    gevonden, gezien, overgeslagen = [], set(), []
    vandaag = dt.date.today().isoformat()

    for i, regel in enumerate(regels):
        pc = RE_PA_POSTCODE.match(regel)
        if not pc:
            continue
        postcode, plaats, buurt = (pc.group(1).replace(" ", ""),
                                   pc.group(2).strip(), pc.group(3).strip())
        if plaats.lower() not in ("nijmegen", "lent"):
            continue

        # Titel met soort en straat staat boven de postcode
        soort = straat = None
        for j in range(i - 1, max(-1, i - 6), -1):
            tm = RE_PA_TITEL.match(regels[j])
            if tm:
                soort, straat = tm.group(1).lower(), tm.group(2).strip()
                break
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

        opp = None
        for j in range(i + 1, min(len(regels), i + 16)):
            om = RE_PA_OPP.match(regels[j])
            if om:
                opp = int(om.group(1))
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

        status = "te huur kamer" if soort == "kamer" else "te huur"
        sleutel = (straat.lower(), prijs, opp)
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        gevonden.append(f"{straat} | {plaats} | {prijs} | {status} | {vandaag} "
                        f"| pararius | {opp} | {postcode}")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proef", action="store_true",
                    help="toon wat er toegevoegd zou worden, schrijf niets weg")
    ap.add_argument("--dagen", type=int, default=0,
                    help="kijk ook naar gelezen mails van de laatste N dagen")
    ap.add_argument("--uit", default=VERKOPEN_PAD)
    args = ap.parse_args()

    if not GEBRUIKER or not WACHTWOORD:
        print("MAIL_USERNAME of MAIL_PASSWORD ontbreekt", file=sys.stderr)
        return

    try:
        verbinding = imaplib.IMAP4_SSL(IMAP_HOST)
        verbinding.login(GEBRUIKER, WACHTWOORD)
        verbinding.select("INBOX")
    except Exception as e:
        print(f"Kan niet inloggen op de mailbox: {e}", file=sys.stderr)
        print("Staat IMAP aan in Gmail, en klopt het app-wachtwoord?", file=sys.stderr)
        return

    ids = set()
    for afzender in AFZENDERS:
        zoek = f'(FROM "{afzender}")'
        if args.dagen:
            sinds = (dt.date.today() - dt.timedelta(days=args.dagen)).strftime("%d-%b-%Y")
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
        if "kamernet" in afzender or "kamernet" in blob:
            soort_bron, status_label = "kamernet", "te huur kamer"
        elif "pararius" in afzender or "pararius" in blob:
            soort_bron, status_label = "pararius", "te huur"
        elif "funda in business" in blob or "bedrijfspanden" in blob:
            soort_bron, status_label = "business", "belegging"
        else:
            soort_bron, status_label = "regulier", "te koop"

        if soort_bron == "kamernet":
            objecten, overgeslagen = parse_kamernet(regels)
        elif soort_bron == "pararius":
            objecten, overgeslagen = parse_pararius(regels)
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


if __name__ == "__main__":
    main()
