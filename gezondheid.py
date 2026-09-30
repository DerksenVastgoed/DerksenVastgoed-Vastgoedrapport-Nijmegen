#!/usr/bin/env python3
"""
Gezondheidsrapport van de vastgoedbrief.

Draait als laatste stap en kijkt per onderdeel wat er werkelijk is opgeleverd.
Niet wat de log belooft, maar wat er in de bestanden staat: een script kan
netjes "gelukt" melden en toch niets hebben weggeschreven.

Het rapport is bedoeld om te kopiëren en te delen. Per onderdeel staat de
status, het bewijs en bij een probleem de vermoedelijke oorzaak en waar je
moet kijken.

Gebruik:
  python gezondheid.py --uit digests/2026-09-21-gezondheid.md
"""

import argparse
import datetime as dt
import json
import os
import sys

OK, LET_OP, FOUT = "OK", "LET OP", "FOUT"

# De scripts schrijven bij een probleem hun eigen diagnose weg in deze map.
# Het rapport neemt die over, zodat de oorzaak in het rapport staat en je niet
# in de logs hoeft te zoeken.
DIAGNOSE_MAP = "diagnose"


def diagnose(onderdeel):
    """
    De diagnose die een script zelf heeft achtergelaten, als die er is.

    Dubbele regels eruit: een script dat twee keer draait of twee keer
    hetzelfde vaststelt, hoort het maar een keer te zeggen.
    """
    pad = os.path.join(DIAGNOSE_MAP, f"{onderdeel}.txt")
    try:
        with open(pad, encoding="utf-8") as f:
            regels = [r.strip() for r in f if r.strip()]
    except Exception:
        return ""
    uniek = []
    for r in regels:
        if r not in uniek:
            uniek.append(r)
    return " ".join(uniek)


def automatische_keuzes():
    """Alle keuzes die een script zelf heeft gemaakt, uit alle diagnoses."""
    uit = []
    if not os.path.isdir(DIAGNOSE_MAP):
        return uit
    for naam in sorted(os.listdir(DIAGNOSE_MAP)):
        try:
            with open(os.path.join(DIAGNOSE_MAP, naam), encoding="utf-8") as f:
                for regel in f:
                    regel = regel.strip()
                    if regel.startswith("AUTOMATISCH") and regel not in uit:
                        uit.append(regel.replace("AUTOMATISCH: ", ""))
        except Exception:
            continue
    return uit


def _kort(tekst, maximum=240):
    """Een diagnose inkorten tot iets wat in een bericht past."""
    if len(tekst) <= maximum:
        return tekst
    return tekst[:maximum].rsplit(" ", 1)[0] + " (...)"
VANDAAG = dt.date.today()


def _json(pad):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _leeftijd_dagen(pad):
    """Hoeveel dagen geleden is dit bestand bijgewerkt?"""
    try:
        return (VANDAAG - dt.date.fromtimestamp(os.path.getmtime(pad))).days
    except Exception:
        return None


def _regels(pad):
    try:
        with open(pad, encoding="utf-8") as f:
            return [r for r in f if r.strip() and not r.startswith("#")]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# De controles. Elk geeft (status, bewijs, diagnose) terug.
# ---------------------------------------------------------------------------

def controle_huurdata():
    """Het belangrijkste: rust de richtprijs op metingen of op een aanname?"""
    regels = _regels("verkopen.txt")
    huur = [r for r in regels if "te huur" in r.lower()]
    pararius = [r for r in huur if "pararius" in r.lower()]
    kamernet = [r for r in huur if "kamernet" in r.lower()]
    recent = [r for r in huur
              if any(str(VANDAAG - dt.timedelta(days=d)) in r for d in range(8))]
    bewijs = (f"{len(huur)} huurwaarnemingen, waarvan {len(pararius)} Pararius "
              f"en {len(kamernet)} Kamernet; {len(recent)} in de laatste week")
    if not huur:
        return (FOUT, bewijs,
                "Geen enkele huurwaarneming. Elke richtprijs rust op een aanname. "
                "Kijk in stap 14 naar de [pararius]-regels: staat daar "
                "'0 objecten', dan herkent de parser de mail niet.")
    if not recent:
        return (LET_OP, bewijs,
                "Wel huurdata, maar niets nieuws deze week. Komen de Pararius-mails "
                "nog binnen, en worden ze herkend? Zie stap 14.")
    if len(huur) < 30:
        return (LET_OP, bewijs,
                "Er wordt gemeten, maar het aantal is nog te klein voor een "
                "betrouwbare mediaan per grootteklasse en buurt.")
    return (OK, bewijs, "")


def controle_aanbod():
    regels = _regels("verkopen.txt")
    koop = [r for r in regels if "te koop" in r.lower() or "belegging" in r.lower()]
    recent = [r for r in koop
              if any(str(VANDAAG - dt.timedelta(days=d)) in r for d in range(4))]
    bewijs = f"{len(koop)} koopobjecten, {len(recent)} in de laatste drie dagen"
    if not koop:
        return (FOUT, bewijs, "Het aanbodbestand is leeg. Zie stap 14.")
    if not recent:
        return (LET_OP, bewijs,
                "Geen nieuw aanbod in drie dagen. Kan kloppen in een stille week, "
                "maar controleer of de Funda-mails binnenkomen.")
    return (OK, bewijs, "")


def controle_rente():
    d = _json("rente_actueel.json") or {}
    leeftijd = _leeftijd_dagen("rente_actueel.json")
    rente = d.get("rente") or d.get("ltv70")
    if not rente:
        return (FOUT, "geen rente in rente_actueel.json",
                "De rentestap leverde niets op. Zie stap 8; financieren.nl kan van "
                "opmaak zijn veranderd.")
    if leeftijd is not None and leeftijd > 3:
        return (LET_OP, f"rente {rente}%, bestand {leeftijd} dagen oud",
                "De rente is niet vernieuwd. Zie stap 8.")
    return (OK, f"rente {rente}% bij 70% financiering", "")


def controle_ecb():
    d = _json("rente_actueel.json") or {}
    markt = d.get("kapitaalmarkt")
    if markt is None:
        return (FOUT, "geen kapitaalmarktrente vastgelegd",
                "De ECB gaf geen antwoord. Zie stap 8, de regel 'ECB-rente'. Staat "
                "er 'mislukt op alle manieren', dan blokkeert de ECB verzoeken "
                "vanaf GitHub en helpt een andere vraagvorm niet.")
    rente = d.get("ltv70") or d.get("rente")
    opslag = (f", opslag bij 70% financiering {rente - markt:.2f}".replace(".", ",")
              + " procentpunt") if rente else ""
    return (OK, f"tienjaars AAA-rente " + f"{markt:.2f}".replace(".", ",")
            + f"% ({d.get('kapitaalmarkt_datum', '')}){opslag}", "")


def controle_bouwkosten():
    d = _json("bouwkosten_index.json") or {}
    if not d:
        return (FOUT, "bouwkosten_index.json ontbreekt of is leeg",
                diagnose("bouwkosten")
                or "De verbouwkosten worden niet geindexeerd. Zie stap 17.")
    laatste = max(d)
    return (OK, f"{len(d)} maanden, laatste {laatste}", "")


def controle_eigen_bouwkosten():
    eigen = [r for r in _regels("bouwkosten_eigen.txt") if "|" in r]
    if not eigen:
        return (LET_OP, "geen eigen bouwkosten ingevuld",
                "De verbouwkosten zijn aannames van het script. Vul in "
                "bouwkosten_eigen.txt wat verhuurklaar maken en verduurzaming per "
                "m2 kosten; uit het hoofd is al beter dan de aanname.")
    return (OK, f"{len(eigen)} eigen tarieven ingevuld", "")


def controle_buurtcijfers():
    d = _json("buurten_cbs.json") or {}
    buurten = [b for b in d if not str(b).startswith("_")]
    if not buurten:
        return (FOUT, "buurten_cbs.json leeg", "Zie stap 7.")
    eerste = d[buurten[0]] if buurten else {}
    ontbreekt = [v for v in ("inkomen", "vermogen", "eenpersoons", "leeftijd",
                             "afstand_trein")
                 if eerste.get(v) is None]
    bewijs = f"{len(buurten)} buurten"
    if ontbreekt:
        return (LET_OP, bewijs + f"; ontbreekt: {', '.join(ontbreekt)}",
                diagnose("buurtcijfers")
                or "Deze velden worden niet gevonden in de CBS-kaart. In stap 7 "
                   "staat welke veldnamen er wel zijn.")
    return (OK, bewijs + ", alle velden gevuld", "")


def controle_vergunningen():
    per_buurt = _json("vergunningen_per_buurt.json") or {}
    lijst = _json("kamervergunningen.json") or {}
    if not lijst:
        return (FOUT, "kamervergunningen.json ontbreekt", "")
    if len(per_buurt) < 3:
        return (LET_OP, f"{len(lijst)} adressen, maar {len(per_buurt)} buurten "
                        f"gekoppeld",
                diagnose("vergunningen")
                or "De koppeling aan buurten is niet gemaakt; de kolom in de brief "
                   "blijft leeg. Zie stap 5.")
    return (OK, f"{len(lijst)} adressen in {len(per_buurt)} buurten", "")


def controle_kamerverhuur():
    """Het register van kamerverhuurpanden, en hoe ver de meldingen teruggaan."""
    d = _json("kamerverhuur_per_buurt.json") or {}
    per = d.get("per_buurt") or {}
    if not per:
        return (FOUT, "kamerverhuur_per_buurt.json ontbreekt of is leeg",
                diagnose("kamerverhuur") or "Zie de stap Kamerverhuurregister.")
    totaal = sum(v.get("totaal", 0) for v in per.values())
    via_melding = sum(v.get("alleen_melding_of_besluit", 0) for v in per.values())
    jaren = d.get("meldingen_per_jaar") or {}
    jaartekst = (", ".join(f"{j}: {n}" for j, n in jaren.items())
                 if jaren else "geen meldingen")
    bewijs = (f"{totaal} panden in de ring, waarvan {via_melding} alleen via een "
              f"melding of besluit; meldingen per jaar: {jaartekst}")
    if not jaren:
        return (LET_OP, bewijs, diagnose("kamerverhuur") or
                "Geen meldingen in het archief; het register rust dan alleen op de "
                "vergunningenlijst.")
    return (OK, bewijs, "")


def controle_woningprijzen():
    d = _json("woningprijsindex.json") or {}
    l, r = d.get("landelijk"), d.get("regio")
    if not l and not r:
        return (FOUT, "woningprijsindex.json leeg",
                diagnose("woningprijzen") or "Zie de stap Woningprijsindex CBS.")
    delen = []
    if l:
        delen.append(f"landelijk {l['periode']}")
    if r:
        delen.append(f"{r['naam']} {r['periode']}")
    if d.get("ingang"):
        delen.append(f"via {d['ingang']}")
    v = d.get("vergelijking") or {}
    if v.get("beste_verband"):
        b = v["beste_verband"]
        delen.append(f"eigen reeks {v['maanden']} maanden, sterkste samenhang bij "
                     f"{b['vertraging_maanden']} maanden vooruit ({b['r']})")
    elif v.get("maanden"):
        delen.append(f"eigen reeks {v['maanden']} maanden sinds {v['sinds']}, "
                     f"vergelijking start bij 13")
    if not r:
        return (LET_OP, ", ".join(delen) + "; geen regio",
                diagnose("woningprijzen") or "Nijmegen niet gevonden in de regiotabel.")
    return (OK, ", ".join(delen), "")


def controle_begroting():
    d = _json("begroting_nijmegen.json") or {}
    if not d.get("paginas"):
        return (LET_OP, "nog geen begroting opgehaald",
                diagnose("begroting") or "Draait de stap Stadsbegroting al?")
    return (OK, f"Stadsbegroting {d.get('jaar')}, {len(d['paginas'])} pagina's, "
                f"opgehaald {d.get('opgehaald')}", "")


def controle_geschiedenis():
    """Hoeveel panden we volgen, en hoeveel er nog nooit zijn nagekeken."""
    d = _json("pandgeschiedenis.json") or {}
    if not d:
        return (LET_OP, "nog geen geschiedenis opgebouwd",
                diagnose("geschiedenis") or "Draait de stap Geschiedenis per pand?")
    met_verhaal = sum(1 for p in d.values()
                      if len(p.get("gebeurtenissen") or []) > 1)
    nooit = sum(1 for p in d.values() if not p.get("bag_gezien"))
    zonder_id = sum(1 for p in d.values() if p.get("bag_zonder_id"))
    # Wat er werkelijk is opgehaald: de eenheden uit de BAG en de labels uit
    # EP-Online. Dat was tot nu toe alleen af te leiden uit een aftreksom.
    met_bag = sum(1 for p in d.values() if p.get("bag_eenheden"))
    met_label = sum(1 for p in d.values() if p.get("labels"))
    eenheden = sum(len(p.get("bag_eenheden") or []) for p in d.values())
    # Het getal uit het script zelf, niet een eigen kopie: die liepen uiteen
    # toen de standaard van 200 naar 500 ging.
    try:
        from pandgeschiedenis import MAX_BAG_PER_RONDE as per_ronde
    except Exception:
        per_ronde = int(os.environ.get("BAG_PER_RONDE") or 500)
    bewijs = (f"{len(d)} panden gevolgd, {met_verhaal} met meer dan een "
              f"gebeurtenis; {met_bag} met BAG-gegevens ({eenheden} woningen), "
              f"{met_label} met een energielabel, {nooit} nog nooit nagekeken"
              + (f", {zonder_id} zonder pand-id in de BAG" if zonder_id else ""))
    if nooit:
        runs = -(-nooit // per_ronde)
        oorzaak = (f"Bij {per_ronde} panden per ronde zijn dat nog {runs} "
                   f"run(s). Elke handmatige start werkt er een ronde af.")
        return (LET_OP, bewijs, diagnose("geschiedenis") or oorzaak)
    return (OK, bewijs + "; iedereen is minstens een keer nagekeken",
            diagnose("geschiedenis") or "")


def controle_mailbronnen():
    """Welke attenderingen er binnenkomen, en of er iets uit te halen valt."""
    d = _json("mail_status.json") or {}
    bronnen = d.get("bronnen") or {}
    if d.get("opmerking"):
        return (LET_OP, f"mailstap van {d.get('datum', '?')}: {d['opmerking']}",
                "De mailstap kwam niet bij de mailbox; zonder die stap komt er "
                "geen aanbod binnen.")
    if not bronnen:
        return (LET_OP, f"mailstap van {d.get('datum', '?')}: geen enkele mail "
                        f"van een van de bronnen",
                "Komen de attenderingen in deze mailbox binnen, en staan ze in "
                "de inbox en niet in een map?")
    delen, stil, stom = [], [], []
    for bron, t in sorted(bronnen.items()):
        stuk = (f"{bron}: {t.get('mails', 0)} mails, "
                f"{t.get('objecten', 0)} objecten")
        if t.get("overgeslagen"):
            stuk += f", {t['overgeslagen']} bewust overgeslagen"
        delen.append(stuk)
        if not t.get("mails"):
            stil.append(bron)
        elif not t.get("objecten") and not t.get("overgeslagen"):
            # Alleen alarm slaan als er niets uitkwam en er ook niets bewust is
            # overgeslagen. Een mail met alleen een gemeubileerde woning levert
            # terecht nul objecten op; dat is geen parserfout.
            stom.append(bron)
    for verwacht in ("kamernet", "pararius", "funda"):
        if verwacht not in bronnen:
            stil.append(verwacht)
    bewijs = f"laatste ronde {d.get('datum', '?')}: " + "; ".join(delen)
    if stom:
        voorbeelden = []
        for bron in stom:
            for r in (bronnen[bron].get("redenen") or [])[:2]:
                voorbeelden.append(f"{bron}: {r}")
        staart = (" Voorbeeld: " + "; ".join(voorbeelden)) if voorbeelden else ""
        return (LET_OP, bewijs,
                f"Van {', '.join(stom)} komen wel mails binnen maar het script "
                f"haalt er niets uit; de opmaak is waarschijnlijk veranderd."
                + staart)
    if stil:
        return (LET_OP, bewijs,
                f"Van {', '.join(sorted(set(stil)))} kwam geen enkele mail. "
                f"Staat de attendering aan en komt hij in deze mailbox binnen?")
    return (OK, bewijs, "")


def controle_peildata():
    """
    Bedragen en grenzen die elk jaar opnieuw worden vastgesteld.

    De huurprijstabel wordt per 1 januari geindexeerd, en daarmee verschuift de
    grens tussen middenhuur en vrije sector. Hetzelfde geldt voor de WOZ-grenzen
    in de huisvestingsverordening en voor de overdrachtsbelasting. Staat hier
    een ouder jaar dan het huidige, dan rekent het script met verouderde
    grenzen zonder dat iemand dat merkt.
    """
    dit_jaar = dt.date.today().year
    regels, verouderd = [], []
    try:
        from wwso import TABEL_PEILDATUM, TABEL_BRON, WWS_TABEL
        jaar = int(TABEL_PEILDATUM[:4])
        regels.append(f"huurprijstabel {TABEL_PEILDATUM} (grens vrije sector "
                      f"€{WWS_TABEL.get(186, 0):.2f})")
        if jaar < dit_jaar:
            verouderd.append(f"de huurprijstabel is van {jaar}; de nieuwe staat "
                             f"in {TABEL_BRON}")
    except Exception as e:
        return (LET_OP, "huurprijstabel niet te lezen", str(e)[:120])

    try:
        from subsidie_svoh import PEILDATUM as SVOH_PEIL, PER_M2
        jaar = int(SVOH_PEIL[:4])
        regels.append(f"SVOH-bedragen {SVOH_PEIL} (gevelisolatie "
                      f"€{PER_M2['gevelisolatie'][1]:.2f} per m2)")
        if jaar < dit_jaar:
            verouderd.append(f"de SVOH-bedragen zijn van {jaar}; ze worden "
                             f"jaarlijks opnieuw vastgesteld door de RVO.")
    except Exception:
        pass

    try:
        from marktprijzen_bag import WOZ_GRENS_OMZETTING, WOZ_GRENS_WEIGERING
        regels.append(f"WOZ-grenzen €{WOZ_GRENS_OMZETTING:,} en "
                      f"€{WOZ_GRENS_WEIGERING:,}".replace(",", "."))
    except Exception:
        pass

    if verouderd:
        return (LET_OP, "; ".join(regels),
                " ".join(verouderd) + " Werk de tabel bij en zet de nieuwe "
                "peildatum erbij.")
    return (OK, "; ".join(regels), "")


def controle_bag3d():
    """De eigen snapshot van hoogtes en oppervlakken per pand."""
    d = _json("bag3d.json") or {}
    panden = d.get("panden") or {}
    if not panden:
        return (LET_OP, "nog geen 3D BAG-gegevens opgehaald",
                "Zonder hoogte en buitenmuuroppervlak is er geen basis voor de "
                "bouwkosten per pand. Zie de stap in het logboek.")
    met = sum(1 for p in panden.values() if p.get("b3_opp_buitenmuur"))
    leeg = sum(1 for p in panden.values() if p.get("leeg"))
    bewijs = (f"{len(panden)} panden in de eigen snapshot, {met} met een "
              f"buitenmuuroppervlak, {leeg} zonder gegevens bij de bron; "
              f"bijgewerkt {d.get('bijgewerkt', '?')}")
    if met < len(panden) * 0.5:
        return (LET_OP, bewijs,
                "Van minder dan de helft kwamen bruikbare waarden; controleer "
                "of de opzet van de bron is veranderd.")
    return (OK, bewijs, "")


def controle_corop():
    """De kwartaalcijfers voor het eigen COROP-gebied."""
    d = _json("corop_prijzen.json") or {}
    if not d.get("periode"):
        return (LET_OP, "geen COROP-cijfers opgehaald",
                "Zonder deze tabel vergelijkt de brief onze buurtcijfers met "
                "heel Gelderland; dat is te grof. Zie de stap in het logboek.")
    oud = ""
    try:
        jaar, kw = d["periode"][:4], d["periode"][-1]
        maanden = (dt.date.today().year - int(jaar)) * 12 + \
                  (dt.date.today().month - int(kw) * 3)
        if maanden > 6:
            oud = (f" De cijfers zijn van {d['periode']}; het CBS publiceert "
                   f"ongeveer 22 dagen na afloop van een kwartaal.")
    except Exception:
        pass
    bewijs = (f"{d.get('gebied')} {d['periode']}: index {d.get('index')}, "
              f"{d.get('jaar_pct')}% op jaarbasis, "
              f"{int(d.get('transacties') or 0)} transacties")
    return ((LET_OP, bewijs, oud.strip()) if oud else (OK, bewijs, ""))


def controle_wozschatting():
    """Hoe betrouwbaar is de eigen WOZ-schatting inmiddels?"""
    d = _json("woz_kalibratie.json") or {}
    aantal = d.get("aantal") or 0
    if aantal < 8:
        return (LET_OP, f"geijkt op {aantal} panden, te weinig om iets te zeggen",
                "Voer WOZ-waarden in bij grensgevallen; vanaf acht panden begint "
                "de schatting zichzelf te corrigeren.")
    vgl = d.get("vergelijking") or {}
    delen = []
    for naam in ("kenmerken", "prijs"):
        v = vgl.get(naam)
        if v:
            delen.append(f"{naam} {v['mediane_fout'] * 100:.1f}%")
    afwijking = abs(1 - (d.get("correctie") or 1)) * 100
    spreiding = (d.get("spreiding") or 0) * 100
    kb = d.get("kenmerken_beschikbaar") or {}
    bewijs = (f"geijkt op {aantal} panden: correctie {d.get('correctie'):.3f} "
              f"({afwijking:.0f}% stelselmatig), spreiding ±{spreiding:.1f}%"
              + (f"; mediane fout per methode: {', '.join(delen)}" if delen else "")
              + (f"; kenmerken uit {kb.get('straten', 0)} straten en "
                 f"{kb.get('buurten', 0)} buurten" if kb else ""))
    if spreiding > 7:
        return (LET_OP, bewijs,
                "De spreiding is nog te groot om op de schatting te varen; blijf "
                "de WOZ opzoeken bij panden die ertoe doen.")
    return (OK, bewijs + "; nauwkeurig genoeg om alleen grensgevallen op te "
            "zoeken", "")


def controle_nieuwe_onderwerpen():
    """
    Onderwerpen die in het nieuws terugkomen en waar nog geen stuk over is.

    De signaalstap vindt ze en schrijft ze in een bestand; zonder deze controle
    blijft dat bestand liggen en gebeurt er niets mee. Dit is de schakel tussen
    "het script ziet een nieuw onderwerp" en "er komt een achtergrondstuk".
    """
    voorstellen = []
    try:
        with open("onderwerpen_voorstel.md", encoding="utf-8") as f:
            for regel in f:
                regel = regel.strip(" -*\t\n")
                if regel and not regel.startswith("#") and len(regel) < 120:
                    voorstellen.append(regel)
    except Exception:
        pass
    gevolgd = _json("onderwerpen_volgen.json") or {}
    if not voorstellen and not gevolgd:
        return (OK, "geen nieuwe onderwerpen voorgesteld", "")
    bewijs = (f"{len(voorstellen)} voorgestelde onderwerpen, "
              f"{len(gevolgd)} gevolgd")
    if voorstellen:
        return (LET_OP, bewijs + ": " + "; ".join(voorstellen[:4]),
                "Deze komen terug in het nieuws en hebben nog geen "
                "achtergrondstuk. Bespreek ze, dan kan er een stuk met bronnen "
                "bij; het script schrijft die niet zelf, want juridische tekst "
                "zonder gecontroleerde bron is precies wat we niet willen.")
    return (OK, bewijs, "")


def controle_achtergronddekking():
    """
    Heeft elk soort bekendmaking een achtergrondstuk dat de inhoud uitlegt?

    Een melding constateren is iets anders dan uitleggen wat er dan van je
    gevraagd wordt. Komt er een soort voorbij waarvoor geen stuk klaarligt, dan
    blijft het bij de constatering.
    """
    try:
        from bekendmakingen_archief import SIGNAALWOORDEN
        from bronnen import ACHTERGROND, ACHTERGROND_TREFWOORDEN
    except Exception as e:
        return (LET_OP, "kon de onderwerpen niet vergelijken", str(e)[:120])
    alle_trefwoorden = " ".join(
        " ".join(v) for v in ACHTERGROND_TREFWOORDEN.values()).lower()
    titels = " ".join(t for t, _ in ACHTERGROND).lower()
    zonder = []
    for soort, woorden in SIGNAALWOORDEN.items():
        raak = any(w.lower()[:8] in alle_trefwoorden or w.lower()[:8] in titels
                   for w in [soort] + list(woorden))
        if not raak:
            zonder.append(soort)
    bewijs = (f"{len(ACHTERGROND)} achtergrondstukken voor "
              f"{len(SIGNAALWOORDEN)} soorten bekendmakingen")
    if zonder:
        return (LET_OP, bewijs + f"; geen stuk voor: {', '.join(sorted(zonder))}",
                "Bij die soorten blijft het bij constateren dat er iets is "
                "gemeld, zonder uit te leggen wat de regel inhoudt.")
    return (OK, bewijs + "; elk soort heeft een stuk", "")


def controle_vve():
    """Van hoeveel appartementen in een complex kennen we de VvE-bijdrage?"""
    try:
        from marktprijzen_bag import lees_vve_kosten
        tabel = lees_vve_kosten()
    except Exception as e:
        return (LET_OP, "VvE-bestand niet te lezen", str(e)[:120])
    if not tabel:
        return (LET_OP, "geen enkele VvE-bijdrage ingevoerd",
                "Appartementen in een complex worden nu doorgerekend alsof er "
                "geen VvE is; de richtprijs valt daardoor te hoog uit. Zet de "
                "maandbijdrage in vve_kosten.txt, een regel per adres.")
    bedragen = sorted(tabel.values())
    return (OK, f"{len(tabel)} panden met een VvE-bijdrage, mediaan "
            f"€{bedragen[len(bedragen)//2]:.2f} per maand", "")


def controle_veroudering():
    """
    Hoe oud is het aanbod dat we tonen?

    Een pand blijft in de tabellen staan tot iets anders bewijst dat het weg
    is. De attenderingen melden alleen nieuw en gewijzigd aanbod, dus een pand
    dat stilletjes verkocht wordt, blijft staan. Dit telt hoe groot die groep
    is, zodat de brief niet ongemerkt met verouderd aanbod rekent.
    """
    vandaag = dt.date.today()
    laatst = {}
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 5 or not v[3].lower().startswith("te koop"):
                    continue
                sleutel = v[0].lower()
                laatst[sleutel] = max(laatst.get(sleutel, ""), v[4])
    except Exception:
        return (LET_OP, "aanbod niet te lezen", "Staat verkopen.txt er wel?")
    if not laatst:
        return (LET_OP, "geen aanbod in het bestand", "")
    ouderdom = []
    for datum in laatst.values():
        try:
            ouderdom.append((vandaag - dt.date.fromisoformat(datum)).days)
        except Exception:
            continue
    ouderdom.sort()
    oud = sum(1 for d in ouderdom if d > 60)
    bewijs = (f"{len(ouderdom)} panden te koop, mediaan {ouderdom[len(ouderdom)//2]} "
              f"dagen geleden voor het laatst bevestigd, oudste {ouderdom[-1]} dagen")
    if oud:
        return (LET_OP, bewijs + f", {oud} langer dan 60 dagen",
                "Die panden zijn waarschijnlijk al van de markt; ze blijven "
                "staan omdat de attendering alleen nieuw aanbod meldt. Een "
                "geplakte verkooplijst haalt ze eruit.")
    return (OK, bewijs, "")


def controle_verkopen():
    """
    Hoe de verkopen binnenkomen: via de mail of met de hand geplakt.

    Belangrijk om te weten of de attendering de verkopen meeneemt sinds Mark
    dat filter aanzette. Zo ja, dan hoeft er niets meer geplakt te worden.
    """
    per_bron, laatste = {}, ""
    try:
        with open("verkopen.txt", encoding="utf-8") as f:
            for regel in f:
                v = [x.strip() for x in regel.split("|")]
                if len(v) < 6 or not v[3].lower().startswith("verkocht"):
                    continue
                bron = "geplakt" if "plak" in v[5] else "uit de mail"
                per_bron[bron] = per_bron.get(bron, 0) + 1
                laatste = max(laatste, v[4])
    except Exception:
        return (LET_OP, "verkopen niet te lezen", "Staat verkopen.txt er wel?")
    if not per_bron:
        return (LET_OP, "nog geen verkopen in de reeks",
                "Zet in de Funda-attendering het filter op verkocht en onder "
                "bod; dan komen ze vanzelf binnen. Werkt dat niet, dan blijft "
                "plakken over.")
    delen = ", ".join(f"{n} {b}" for b, n in sorted(per_bron.items()))
    uit_mail = per_bron.get("uit de mail", 0)
    bewijs = f"{sum(per_bron.values())} verkopen: {delen}; laatste {laatste}"
    if not uit_mail:
        return (LET_OP, bewijs,
                "Er komt nog geen enkele verkoop uit de attendering. Controleer "
                "of het filter op verkocht daar echt aan staat.")
    return (OK, bewijs, "")


def controle_plakbestanden():
    """De lijsten die Mark met de hand aanlevert: verkopen en Kamernet."""
    uit = []
    for pad, wat in (("funda_verkocht_plak.txt", "verkooplijst van Funda"),
                     ("kamernet_plak.txt", "kamerlijst van Kamernet")):
        if os.path.exists(pad) and os.path.getsize(pad) > 200:
            uit.append(f"{wat}: aanwezig")
        else:
            uit.append(f"{wat}: ontbreekt")
    verkocht = _json("verkocht_details.json") or {}
    if verkocht:
        uit.append(f"{len(verkocht)} verkochte woningen verwerkt")
    # Komt een bron via de mail binnen, dan is het plakbestand overbodig.
    mail = (_json("mail_status.json") or {}).get("bronnen") or {}
    if (mail.get("kamernet") or {}).get("objecten"):
        uit[1] = "kamerlijst van Kamernet: niet nodig, komt uit de mail"
    if all(("aanwezig" in x or "niet nodig" in x) for x in uit[:2]):
        return (OK, "; ".join(uit), "")
    return (LET_OP, "; ".join(uit),
            "Plak de tekst van de pagina in dat bestand en commit het; het "
            "script verwerkt hem bij de volgende run.")


def controle_misdrijven():
    d = _json("misdrijven_per_buurt.json") or {}
    if not d:
        return (FOUT, "geen misdrijfcijfers", "Zie stap 6.")
    return (OK, f"{len(d)} buurten", "")


def controle_ov():
    haltes = _json("ov_haltes.json") or []
    afstanden = _json("ov_afstand_cache.json") or {}
    if not haltes:
        return (FOUT, "geen haltebestand",
                "Zie stap 16. Verwijder ov_haltes.json om opnieuw op te halen.")
    if len(haltes) < 50:
        return (LET_OP, f"{len(haltes)} haltes",
                "Verdacht weinig voor de ring; controleer het zoekgebied in "
                "ov_haltes.py.")
    geschat = sum(1 for a in afstanden.values()
                  if isinstance(a, dict) and a.get("geschat"))
    bewijs = f"{len(haltes)} haltes, {len(afstanden)} panden gerouteerd"
    if afstanden and geschat == len(afstanden):
        return (LET_OP, bewijs + ", alle afstanden geschat",
                "De routering via OSRM lukt niet; alle afstanden zijn de rechte "
                "lijn maal 1,35.")
    return (OK, bewijs, "")


def controle_archief():
    d = _json("bekendmakingen_archief.json") or {}
    leeftijd = _leeftijd_dagen("bekendmakingen_archief.json")
    if not d:
        return (FOUT, "archief leeg", "Zie stap 13.")
    publ = sum(len(v) for v in d.values() if isinstance(v, list))
    bewijs = f"{len(d)} adressen, {publ} publicaties"
    if leeftijd is not None and leeftijd > 3:
        return (LET_OP, bewijs + f", {leeftijd} dagen niet bijgewerkt",
                "Zie stap 13.")
    return (OK, bewijs, "")


def controle_regelgeving():
    d = _json("regelgeving_status.json")
    if d is None:
        return (LET_OP, "nog geen regelgevingsstatus",
                "De monitor draait op zondag. Na de eerste zondag hoort hier een "
                "aantal regelingen te staan.")
    # Sleutels die met een liggend streepje beginnen zijn geen regeling maar
    # administratie van het script zelf, zoals de lijst met zoektermen.
    d = {k: v for k, v in d.items()
         if not str(k).startswith("_") and isinstance(v, dict)}
    gemeente = sum(1 for g in d.values() if g.get("bron") == "gemeente")
    landelijk = sum(1 for g in d.values() if g.get("bron") == "landelijk")
    bewijs = f"{gemeente} verordeningen, {landelijk} wetten"
    if not gemeente:
        return (LET_OP, bewijs,
                "Geen gemeentelijke verordeningen gevonden via CVDR. Zie stap 9 op "
                "zondag; de zoekopdracht op 'Nijmegen' levert mogelijk niets op.")
    return (OK, bewijs, "")


def controle_geheugen():
    gezien = _json("brief_gezien.json") or {}
    trend = _json("prijstrend.json") or {}
    if not gezien:
        return (FOUT, "brief_gezien.json leeg",
                "Zonder geheugen wordt elk pand elke dag als nieuw behandeld.")
    weken = max((len(v) for v in trend.values() if isinstance(v, dict)), default=0)
    bewijs = f"{len(gezien)} panden onthouden, prijstrend over {weken} metingen"
    if weken < 4:
        return (LET_OP, bewijs,
                "De prijstrend is nog te kort voor een vergelijking over vier "
                "weken. Dat lost zich vanzelf op.")
    return (OK, bewijs, "")


def controle_commit():
    """Werd er de vorige keer iets teruggeschreven?"""
    leeftijd = _leeftijd_dagen("brief_gezien.json")
    if leeftijd is None:
        return (FOUT, "brief_gezien.json ontbreekt", "")
    if leeftijd > 2:
        return (FOUT, f"gegevens {leeftijd} dagen niet bijgewerkt",
                "Het terugcommitten lukt vermoedelijk niet. Zie de stap "
                "'Digests + gegevensbestanden terugcommitten'.")
    return (OK, "gegevens van de laatste run bewaard", "")


CONTROLES = [
    ("Huurdata", controle_huurdata),
    ("Aanbod", controle_aanbod),
    ("Marktrente", controle_rente),
    ("Kapitaalmarkt (ECB)", controle_ecb),
    ("Bouwkostenindex", controle_bouwkosten),
    ("Eigen bouwkosten", controle_eigen_bouwkosten),
    ("Buurtcijfers CBS", controle_buurtcijfers),
    ("Kamervergunningen", controle_vergunningen),
    ("Kamerverhuurregister", controle_kamerverhuur),
    ("Woningprijsindex CBS", controle_woningprijzen),
    ("Stadsbegroting", controle_begroting),
    ("Geschiedenis per pand", controle_geschiedenis),
    ("Handmatige lijsten", controle_plakbestanden),
    ("Verkopen", controle_verkopen),
    ("Veroudering aanbod", controle_veroudering),
    ("VvE-bijdragen", controle_vve),
    ("WOZ-schatting", controle_wozschatting),
    ("COROP Arnhem/Nijmegen", controle_corop),
    ("3D BAG eigen snapshot", controle_bag3d),
    ("Achtergronddekking", controle_achtergronddekking),
    ("Nieuwe onderwerpen", controle_nieuwe_onderwerpen),
    ("Jaarlijkse grenzen", controle_peildata),
    ("Attenderingen", controle_mailbronnen),
    ("Misdrijfcijfers", controle_misdrijven),
    ("OV-haltes", controle_ov),
    ("Bekendmakingen-archief", controle_archief),
    ("Regelgevingsmonitor", controle_regelgeving),
    ("Geheugen en trend", controle_geheugen),
    ("Terugschrijven", controle_commit),
]


def rapport(kort=False):
    uitkomsten = []
    for naam, functie in CONTROLES:
        try:
            status, bewijs, diagnose = functie()
        except Exception as e:
            status, bewijs, diagnose = FOUT, "controle zelf faalde", str(e)[:120]
        uitkomsten.append((naam, status, bewijs, diagnose))

    aantal = {s: sum(1 for u in uitkomsten if u[1] == s) for s in (OK, LET_OP, FOUT)}

    if kort:
        # De versie om te plakken: alleen wat aandacht vraagt, ingekort, en de
        # onderdelen die goed gaan in een regel
        r = [f"GEZONDHEID {VANDAAG.isoformat()}: {aantal[OK]} ok, "
             f"{aantal[LET_OP]} let op, {aantal[FOUT]} fout"]
        for status in (FOUT, LET_OP):
            for naam, s_, bewijs, diag in uitkomsten:
                if s_ != status:
                    continue
                r.append(f"[{status}] {naam}: {bewijs}")
                if diag:
                    r.append(f"   {_kort(diag)}")
        goed = [naam for naam, s_, _b, _d in uitkomsten if s_ == OK]
        if goed:
            r.append("[OK] " + ", ".join(goed))

        # Automatische keuzes altijd tonen, ook als het onderdeel groen is.
        # Juist dan: een automatisch gekozen veld dat verkeerd is, geeft geen
        # fout maar een plausibel verkeerd getal.
        for regel in automatische_keuzes():
            r.append(f"[CONTROLEER] {regel}")
        return "\n".join(r)

    r = [f"# Gezondheidsrapport {VANDAAG.isoformat()}", "",
         f"{aantal[OK]} in orde, {aantal[LET_OP]} aandachtspunten, "
         f"{aantal[FOUT]} fouten.", ""]

    # Eerst wat er mis is, dan de rest: daar gaat het om bij het delen
    for status in (FOUT, LET_OP, OK):
        groep = [u for u in uitkomsten if u[1] == status]
        if not groep:
            continue
        r.append(f"## {status}")
        for naam, _s, bewijs, diag in groep:
            r.append(f"- **{naam}**: {bewijs}")
            if diag:
                r.append(f"  {diag}")
        r.append("")
    return "\n".join(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default="")
    args = ap.parse_args()

    # In de log de korte versie, om te kopieren en te delen. In het bestand de
    # volledige versie, voor als je alle details wilt nalezen.
    print("=" * 60)
    print("KOPIEER VANAF HIER")
    print("=" * 60)
    print(rapport(kort=True))
    print("=" * 60)
    print("TOT HIER")
    print("=" * 60)
    if args.uit:
        os.makedirs(os.path.dirname(args.uit) or ".", exist_ok=True)
        with open(args.uit, "w", encoding="utf-8") as f:
            f.write(rapport(kort=False) + "\n")
        print(f"\nVolledig rapport met alle details: {args.uit}")


if __name__ == "__main__":
    main()
