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
AFZENDERS = ["funda.nl", "funda.com"]

GEBRUIKER = os.environ.get("MAIL_USERNAME", "")
WACHTWOORD = os.environ.get("MAIL_PASSWORD", "")

# Zelfde patronen als de browser-verzamelaar
RE_ADRES_KOMMA = re.compile(
    r"^\s*([A-Za-zÀ-ÿ.'\-\s]+?\s+\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\s*,\s*"
    r"([A-Za-zÀ-ÿ\-' ]+?)\s*$")
RE_POSTCODE = re.compile(r"^\s*(\d{4}\s?[A-Z]{2})\s+([A-Za-zÀ-ÿ\-' ]+?)\s*$")
RE_ADRES = re.compile(r"^\s*([A-Za-zÀ-ÿ.'\-\s]+?\s+\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\s*$")
RE_PRIJS = re.compile(r"([\d][\d.]{2,})")


def strip_html(tekst):
    """Maakt van een HTML-mail leesbare regels."""
    tekst = re.sub(r"(?is)<(script|style).*?</\1>", " ", tekst)
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


def parse_objecten(regels, status):
    """
    Haalt objecten uit de regels van een attenderingsmail.
    Twee vormen:
      'Waalkade 60, Nijmegen'  gevolgd door  '€ 495.000 k.k.'
      'Vondelstraat 26'  '6512 BG Nijmegen'  '€ 545.000 k.k.'
    """
    gevonden, gezien, overgeslagen = [], set(), []

    for i, regel in enumerate(regels):
        adres = plaats = None
        adres_idx = i

        komma = RE_ADRES_KOMMA.match(regel)
        if komma:
            adres, plaats = komma.group(1).strip(), komma.group(2).strip()
        else:
            pc = RE_POSTCODE.match(regel)
            if not pc:
                continue
            plaats = pc.group(2).strip()
            for j in range(i - 1, max(-1, i - 5), -1):
                a = RE_ADRES.match(regels[j])
                if a:
                    adres, adres_idx = a.group(1).strip(), j
                    break
            if not adres:
                continue

        # Alleen Nijmegen en directe omgeving
        if plaats.lower() not in ("nijmegen", "lent", "nijmegen-oost", "nijmegen-west"):
            continue

        prijs = None
        for p in range(i + 1, min(len(regels), i + 8)):
            laag = regels[p].lower()
            if "aanvraag" in laag or "n.o.t.k" in laag:
                break
            pm = RE_PRIJS.search(regels[p])
            if pm and "." in pm.group(1) and len(pm.group(1).replace(".", "")) >= 5:
                prijs = pm.group(1).replace(".", "")
                break
        if not prijs:
            overgeslagen.append(f"{adres} (geen prijs gevonden)")
            continue

        sleutel = (adres.lower(), prijs)
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        vandaag = dt.date.today().isoformat()
        gevonden.append(f"{adres} | {plaats} | {prijs} | {status} | {vandaag}")

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
        # Business-attendering levert beleggingsobjecten, regulier Funda woningen
        zakelijk = "funda in business" in blob or "bedrijfspanden" in blob
        status_label = "belegging" if zakelijk else "te koop"

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

        soort = "business" if zakelijk else "regulier"
        print(f"  [{soort}] {onderwerp[:60]}: {len(objecten)} objecten, "
              f"{toegevoegd} nieuw", file=sys.stderr)

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
