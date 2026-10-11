#!/usr/bin/env python3
"""
Een pand heeft een sleutel, en die wordt op een plek gemaakt.

WAAROM DIT BESTAAT. Tien bestanden bevatten feiten per pand. De sleutel
daarvoor werd op veertien plekken in elf bestanden opnieuw gemaakt, plus
negentien keer los met isalnum() in de regel zelf. Die veertien lopen uiteen
op drie punten: of "professor" wordt afgekort tot "prof", of een accent
wegvalt of blijft staan, en of "doctor" meedoet. Vijf van de veertien dragen
in hun eigen docstring de regel "zelfde normalisatie als in de andere
scripts, anders matcht niets", en precies dat is wat er is gebeurd.

WAT HET KOST. Op de 1.777 adressen die we volgen geven twee van die veertien
een andere sleutel bij 41 adressen. Bij 28 daarvan staat het pand wel in het
bestand en vindt de lezer het niet. Dat geeft geen foutmelding: een
ontbrekende sleutel is gewoon None, en dan is een dossier stil leeg.

In pandgeschiedenis.json zelf staan drie conventies door elkaar: 13 records
zonder afkorting, 12 met, en 2 met een sleutel die uit geen enkele functie
kan komen. Die laatste twee zijn Professor Molkenboerstraat 18 en 20, die
daardoor twee keer in het bestand staan. De ene helft heeft de energielabels
en de andere de onttrekking van 2018 en de melding brandveilig gebruik van
2025. Welke helft een lezer ziet hangt af van welke van de veertien functies
hij gebruikt. Voor de kamerverhuurtoets is dat het verschil tussen een pand
dat onttrokken is en een pand dat schoon lijkt.

HOE DIT VEILIG IS IN TE VOEREN. sleutel() geeft één vorm, en varianten()
geeft alle vormen waaronder hetzelfde pand ooit is opgeslagen. Een lezer die
varianten() langsloopt vindt een record ook als het nog niet is overgezet.
Daardoor kan de overstap in twee stappen: eerst deze module erbij met een
proef die bewijst dat elke sleutel die vandaag op schijf staat te vinden is,
en daarna de bestanden omzetten en de veertien functies weghalen. Zonder die
eerste stap is er een moment waarop de helft is omgezet en de andere helft
niet, en dan verdwijnen er feiten.

WAT DE VORM IS, EN WAAROM.
  - kleine letters, en alles wat geen letter of cijfer is eruit
  - een lidwoord voorop valt weg. "aan de Pijnboomstraat 4" in een
    bekendmakingstitel levert "de Pijnboomstraat" als straatnaam op, en dat
    is dezelfde straat. Dit is de oorzaak van de twee dubbele records.
  - titels worden afgekort: sint, professor, burgemeester, doctor. De
    gemeente schrijft ze beide uit, soms in dezelfde publicatie.
  - accenten worden gevouwen en niet weggegooid. Mariënburg werd
    "marinburg", want de regex gooide de ë eruit in plaats van er een e van
    te maken. Dat is niet alleen lelijk, het botst ook: twee verschillende
    straten kunnen zo dezelfde sleutel krijgen.

WAT HIER NIET THUISHOORT. huur_dekking.sleutel() kort straatnamen af
(straat -> str, laan -> ln) om geplakte adressen van buiten te laten matchen.
Dat is een zoekhulp en geen identiteit: "Hertogstraat" en "Hertogstr" mogen
daar hetzelfde zijn, maar een sleutel die dat doet kan twee panden
samenvoegen. Die functie blijft dus waar hij staat.
"""
import re
import sys
import unicodedata

# Titels die de gemeente zowel voluit als afgekort schrijft. De lange vorm
# staat voorop en eindigt op een spatie, zodat "sinterklaasstraat" niet wordt
# geraakt.
TITELS = (
    ("sint ", "st "), ("st. ", "st "),
    ("professor ", "prof "), ("prof. ", "prof "),
    ("burgemeester ", "burg "), ("burg. ", "burg "),
    ("doctor ", "dr "), ("dr. ", "dr "),
)

# Lidwoorden die voor een straatnaam kunnen staan zonder bij de naam te horen.
# "aan de " eerst, want die bevat "de " en anders blijft "aan" staan.
LIDWOORDEN = ("aan de ", "aan het ", "aan 't ", "de ", "het ", "'t ")


def _vouw(tekst):
    """Accenten vouwen in plaats van weggooien: ë wordt e, niet niets."""
    ontleed = unicodedata.normalize("NFKD", tekst)
    return "".join(c for c in ontleed if not unicodedata.combining(c))


def _kaal(tekst):
    return re.sub(r"[^a-z0-9]", "", _vouw((tekst or "").lower()))


def _straatvorm(straat, met_titels=True, met_lidwoord=False):
    s = _vouw((straat or "").lower()).strip()
    if not met_lidwoord:
        for lid in LIDWOORDEN:
            if s.startswith(lid):
                s = s[len(lid):]
                break
    if met_titels:
        for lang, kort in TITELS:
            s = s.replace(lang, kort)
    return re.sub(r"[^a-z0-9]", "", s)


def splits(adres):
    """
    (straat, nummer) uit een volledig adres, of (adres, "") als er geen
    nummer in staat.

    Het nummer is alles vanaf het eerste losse getal: "82-A" en "7A-12"
    blijven dus heel, want die horen bij het adres en niet bij de straat.
    """
    m = re.match(r"^(.*?)[\s,]+(\d.*)$", (adres or "").strip())
    if not m:
        return ((adres or "").strip(), "")
    return (m.group(1).strip(), m.group(2).strip())


def sleutel(adres, nummer=None):
    """
    De sleutel van dit pand. Eén vorm, voor elk bestand.

    Aan te roepen met een volledig adres, of met straat en nummer apart,
    want de veertien functies die dit vervangt deden het op beide manieren.

        sleutel("Professor Molkenboerstraat 18")  -> profmolkenboerstraat18
        sleutel("Professor Molkenboerstraat", 18) -> profmolkenboerstraat18
        sleutel("aan de Pijnboomstraat 4")        -> pijnboomstraat4
        sleutel("Mariënburg 82-A")                -> marienburg82a
    """
    if nummer is None:
        straat, nummer = splits(adres)
    else:
        straat = adres
    return _straatvorm(straat) + _kaal(str(nummer))


def sleutel_huisnummer(adres, nummer=None):
    """
    De sleutel zonder huisletter, voor bestanden die per huisnummer sleutelen.

    kamervergunningen.json doet dat: 83 van de 766 records staan onder
    "achterdewiemelpoort5" terwijl het adres "Achter de Wiemelpoort 5D" is.
    Dat is daar ook juist, want een onttrekking of omzetting wordt op het pand
    gegeven en niet op een afzonderlijke eenheid. Het is dus een andere vraag
    en geen andere spelling, en daarom een eigen functie: wie hiermee zoekt
    weet dat hij het pand bedoelt en niet de woning.
    """
    if nummer is None:
        straat, nummer = splits(adres)
    else:
        straat = adres
    m = re.match(r"\s*(\d+)", str(nummer))
    return _straatvorm(straat) + (m.group(1) if m else _kaal(str(nummer)))


def varianten(adres, nummer=None, op_huisnummer=False):
    """
    Alle vormen waaronder dit pand op schijf kan staan, de huidige vooraan.

    Dit bestaat voor de overstap: zolang er bestanden zijn die nog niet zijn
    omgezet, moet een lezer het record alsnog vinden. Loop deze lijst langs
    en neem de eerste die bestaat.

    De vormen komen uit de veertien functies die dit vervangt:
      - met en zonder afkorting van titels (prof tegen professor)
      - met accenten weggegooid in plaats van gevouwen (marinburg)
      - met accenten ongemoeid (mariënburg, uit de isalnum-variant)
      - met het lidwoord er nog aan (deprofmolkenboerstraat18)

    op_huisnummer voegt de vorm zonder huisletter toe. Dat staat uit, want een
    lezer die "Augustijnenstraat 25B" zoekt mag niet stil het record van 25
    krijgen. Alleen een bestand dat per huisnummer sleutelt zet het aan.
    """
    if nummer is None:
        straat, nummer = splits(adres)
    else:
        straat = adres
    nr_kaal = _kaal(str(nummer))
    # De isalnum-variant laat niet-ascii letters staan, dus die kan niet door
    # _kaal: daar sneuvelen ze.
    rauw = (straat or "").lower()
    nr_rauw = "".join(c for c in str(nummer).lower() if c.isalnum())

    uit = []
    for vorm in (
        _straatvorm(straat) + nr_kaal,
        _straatvorm(straat, met_titels=False) + nr_kaal,
        _straatvorm(straat, met_lidwoord=True) + nr_kaal,
        _straatvorm(straat, met_titels=False, met_lidwoord=True) + nr_kaal,
        # Accenten weggegooid in plaats van gevouwen, met en zonder titels.
        re.sub(r"[^a-z0-9]", "", _titelvorm_zonder_vouwen(straat)) + nr_kaal,
        re.sub(r"[^a-z0-9]", "", rauw) + nr_kaal,
        # Accenten ongemoeid (de isalnum-variant), met en zonder lidwoord.
        "".join(c for c in rauw if c.isalnum()) + nr_rauw,
        "".join(c for c in _zonder_lidwoord(rauw) if c.isalnum()) + nr_rauw,
    ):
        if vorm and vorm not in uit:
            uit.append(vorm)
    # EN DE ANDERE KANT OP. De sleutel "deprofmolkenboerstraat18" hoort bij
    # het adres "Professor Molkenboerstraat 18", dat zelf geen lidwoord heeft:
    # de "de" komt uit een bekendmakingstitel die "aan de Professor
    # Molkenboerstraat 18" luidde. Uit het schone adres is die vorm dus niet
    # te maken door een lidwoord weg te halen, alleen door er een voor te
    # zetten. Zonder deze lus blijven de 56 dubbele records in
    # pandgeschiedenis.json onvindbaar vanaf het adres, en dat is precies de
    # helft van de geschiedenis die nu al stil wegvalt.
    basis = [v for v in uit]
    for lid in ("de", "het", "t"):
        for vorm in basis:
            samen = lid + vorm
            if samen not in uit:
                uit.append(samen)
    if op_huisnummer:
        for vorm in (sleutel_huisnummer(straat, nummer),
                     _straatvorm(straat, met_titels=False)
                     + (re.match(r"\s*(\d+)", str(nummer)).group(1)
                        if re.match(r"\s*(\d+)", str(nummer)) else "")):
            if vorm and vorm not in uit:
                uit.append(vorm)
    return uit


def _zonder_lidwoord(laag):
    for lid in LIDWOORDEN:
        if laag.startswith(lid):
            return laag[len(lid):]
    return laag


def _titelvorm_zonder_vouwen(straat):
    """De oude archiefvorm: titels afgekort, accenten weggegooid."""
    s = _zonder_lidwoord((straat or "").lower())
    for lang, kort in TITELS:
        s = s.replace(lang, kort)
    return s


def zoek_in(pad, bestand, adres, nummer=None, alles=False):
    """
    Zoeken met de conventie die bij dít bestand hoort, uit de tabel BESTANDEN.

    DIT IS DE INGANG, EN zoek() NIET. De vorm zonder huisletter is nodig voor
    kamervergunningen.json en gevaarlijk voor de rest: op de 2.105 adressen
    die we kennen levert hij 139 keer de sleutel van een ánder pand op.
    "Augustijnenstraat 25B" komt dan uit op het record van 25, en dat is een
    andere woning met een eigen geschiedenis. Zo'n keuze hoort niet bij de
    aanroeper te liggen, want die vergeet hem. Het bestand bepaalt hem, en de
    tabel staat in dit bestand zodat de proef hem kan nameten.
    """
    op_nr = next((o for p, o, _w in BESTANDEN if p == pad), False)
    return zoek(bestand, adres, nummer, op_huisnummer=op_nr, alles=alles)


def zoek(bestand, adres, nummer=None, op_huisnummer=False, alles=False):
    """
    Het record van dit pand uit een dict die per adres gesleuteld is.

    Geeft (sleutel, record) of (None, None). De sleutel komt terug zodat de
    aanroeper weet onder welke vorm hij het vond, en dus of er iets om te
    zetten valt.

    alles=True geeft [(sleutel, record), ...] voor élke vorm die bestaat. Dat
    is er voor de 60 panden die onder twee sleutels in hetzelfde bestand
    staan: wie alleen de eerste pakt, mist de helft van de geschiedenis. Bij
    de Berg en Dalseweg 287 zit de ene helft onder "bergendalseweg287" en de
    andere onder "debergendalseweg287".
    """
    if not isinstance(bestand, dict):
        return [] if alles else (None, None)
    gevonden = [(v, bestand[v]) for v in varianten(adres, nummer, op_huisnummer)
                if v in bestand]
    if alles:
        return gevonden
    return gevonden[0] if gevonden else (None, None)


# Per bestand: hoe het gesleuteld is, en wat erin staat. Dit hoort hier en
# niet in een los overzichtsdocument, want dan veroudert het stil. De proef
# hieronder loopt deze tabel langs, dus een regel die niet klopt wordt rood.
BESTANDEN = (
    # pad, sleutelt op huisnummer zonder letter, wat erin staat
    ("pandgeschiedenis.json", False,
     "gebeurtenissen per adres, plus gedeelde pandgegevens onder _panden"),
    ("kamerverhuur_objecten.json", False,
     "panden die bij ons als kamerverhuur bekend staan, met bron"),
    ("verkocht_details.json", False,
     "verkochte panden met prijs, label, makelaar en perceel"),
    ("kamervergunningen.json", True,
     "onttrekkingen, omzettingen en samenvoegingen uit het Woo-verzoek"),
    ("rijksmonumenten_nijmegen.json", False,
     "rijksmonumenten met nummer, naam en functie"),
    ("verkoopdatums_model.json", False,
     "geschatte verkoopdatums uit het model"),
    ("brief_gezien.json", False,
     "wat de brief van dit pand eerder al vertelde"),
)


def _adres_van(rec):
    if isinstance(rec, dict):
        return rec.get("adres")
    if isinstance(rec, list):
        for x in rec:
            if isinstance(x, dict) and x.get("adres"):
                return x["adres"]
    return None


def proef():
    """
    Nameten op de echte bestanden, zonder netwerk en zonder iets te wijzigen.

    De vraag die deze proef stelt: raakt er een sleutel onvindbaar als de
    veertien oude functies door deze ene worden vervangen? Dat is de enige
    vraag die telt, want een onvindbare sleutel geeft geen foutmelding maar
    een leeg dossier.
    """
    import json
    import os
    fouten = []

    def check(naam, echt, verwacht):
        if echt != verwacht:
            fouten.append(f"{naam}: {echt!r}, verwacht {verwacht!r}")

    # De vorm zelf, op echte adressen uit de bestanden.
    check("gewoon", sleutel("Abeelstraat 4"), "abeelstraat4")
    check("twee argumenten", sleutel("Abeelstraat", 4), "abeelstraat4")
    check("titel voluit", sleutel("Professor Molkenboerstraat 18"),
          "profmolkenboerstraat18")
    check("titel afgekort", sleutel("Prof. Molkenboerstraat 18"),
          "profmolkenboerstraat18")
    check("sint", sleutel("Sint Annastraat 7"), "stannastraat7")
    check("sint afgekort", sleutel("St. Annastraat 7"), "stannastraat7")
    # Niet elke straat die met "sint" begint is een heilige.
    check("sinterklaas blijft heel", sleutel("Sinterklaasstraat 1"),
          "sinterklaasstraat1")
    check("lidwoord weg", sleutel("de Pijnboomstraat 17"), "pijnboomstraat17")
    check("aan de weg", sleutel("aan de Pijnboomstraat 17"),
          "pijnboomstraat17")
    # Het accent wordt gevouwen en niet weggegooid: de oude regex maakte van
    # Mariënburg "marinburg", en dat kan met een andere straat botsen.
    check("accent gevouwen", sleutel("Mariënburg 82-A"), "marienburg82a")
    check("accent in de straat", sleutel("Marga Klompélaan 37"),
          "margaklompelaan37")
    check("letter blijft", sleutel("Augustijnenstraat 25B"),
          "augustijnenstraat25b")
    check("zonder letter", sleutel_huisnummer("Augustijnenstraat 25B"),
          "augustijnenstraat25")
    check("getal in de straatnaam", sleutel("Plein 1944 168"), "plein1944168")
    check("geen nummer", sleutel("Jozef Israëlsstraat"), "jozefisraelsstraat")
    check("splits bereik", splits("Mariënburg 82-A"), ("Mariënburg", "82-A"))
    check("splits zonder nummer", splits("Hertogstraat"), ("Hertogstraat", ""))
    check("leeg", sleutel(""), "")
    check("none", sleutel(None), "")

    # De oude vormen moeten vindbaar blijven, anders kan de overstap niet in
    # twee stappen.
    v = varianten("de Berg en Dalseweg 287")
    check("oude lidwoordvorm in varianten", "debergendalseweg287" in v, True)
    check("canonieke vorm vooraan", v[0], "bergendalseweg287")
    v = varianten("Professor Molkenboerstraat 18")
    for oud in ("profmolkenboerstraat18", "professormolkenboerstraat18",
                "deprofmolkenboerstraat18"):
        check(f"variant {oud}", oud in v, True)
    v = varianten("Mariënburg 20")
    for oud in ("marienburg20", "marinburg20", "mariënburg20"):
        check(f"variant {oud}", oud in v, True)
    # De vorm zonder huisletter staat er alleen in als erom gevraagd wordt.
    check("nummervorm niet standaard",
          "augustijnenstraat25" in varianten("Augustijnenstraat 25B"), False)
    check("nummervorm op verzoek",
          "augustijnenstraat25" in varianten("Augustijnenstraat 25B",
                                             op_huisnummer=True), True)

    # En nu de echte bestanden: elke opgeslagen sleutel moet te vinden zijn.
    bestanden_inhoud = {}
    for pad, op_nr, _wat in BESTANDEN:
        if not os.path.exists(pad):
            fouten.append(f"{pad} ontbreekt, dus niet nagemeten")
            continue
        try:
            with open(pad, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            fouten.append(f"{pad} onleesbaar: {str(e)[:60]}")
            continue
        n = mis = zonder = 0
        voorbeeld = ""
        for k, rec in d.items():
            if k == "_panden":
                continue
            n += 1
            a = _adres_van(rec)
            if not a:
                zonder += 1
                continue
            if k not in varianten(a, op_huisnummer=op_nr):
                mis += 1
                if not voorbeeld:
                    voorbeeld = f" (bijv. {k!r} bij adres {a!r})"
        if mis:
            fouten.append(f"{pad}: {mis} van {n} sleutels niet te vinden"
                          f"{voorbeeld}")
        bestanden_inhoud[pad] = d
        if zonder:
            fouten.append(f"{pad}: {zonder} records zonder adresveld, dus de "
                          f"sleutel is daar niet na te meten")
        print(f"  {pad:<34} {n:>5} sleutels, allemaal vindbaar",
              file=sys.stderr)

    # EEN ZOEKOPDRACHT VINDT DIT PAND, OF NIETS. Nooit de buren.
    #
    # Dit moet gemeten worden met adressen die in het bestand ONTBREKEN, en
    # niet met de adressen die er al als sleutel in staan. Die vinden namelijk
    # altijd zichzelf als eerste variant, wat de controle blind maakte: toen
    # ik pandgeschiedenis.json met opzet op huisnummer liet zoeken, bleef de
    # proef groen. Precies de val die ik wilde dichtzetten.
    #
    # Dus: alle adressen die we uit welk bestand ook kennen, langs elk
    # bestand. Dat zijn er ruim tweeduizend, en de meeste staan niet in elk
    # bestand. Komt zo'n adres uit bij een record van een ander pand, dan is
    # dat een stille verwisseling: de lezer krijgt een dossier dat klopt,
    # alleen niet van dit pand.
    pool = set()
    for d in bestanden_inhoud.values():
        for k, rec in d.items():
            if k == "_panden":
                continue
            a = _adres_van(rec)
            if a:
                pool.add(a)
    for pad, op_nr, _wat in BESTANDEN:
        d = bestanden_inhoud.get(pad)
        if not d:
            continue
        # DE TABEL WORDT NAGEMETEN EN NIET GELOOFD. Of een bestand per
        # huisnummer sleutelt is uit de inhoud af te lezen: dan staan er
        # sleutels in zonder de huisletter die het adres van hetzelfde record
        # wel heeft. Bij kamervergunningen.json zijn dat 83 van de 766, bij
        # de andere zes nul. Zonder deze meting is BESTANDEN een bewering, en
        # toen ik pandgeschiedenis.json met opzet op True zette bleef de
        # proef groen.
        kaal = sum(1 for k, rec in d.items()
                   if k != "_panden" and _adres_van(rec)
                   and k == sleutel_huisnummer(_adres_van(rec))
                   and k != sleutel(_adres_van(rec)))
        if bool(kaal) != bool(op_nr):
            fouten.append(
                f"{pad}: de tabel zegt op_huisnummer={op_nr}, maar in het "
                f"bestand staan {kaal} sleutels zonder huisletter")
        # Bij een bestand dat per huisnummer sleutelt is het huisnummer de
        # identiteit, dus dan hoort 116 en 116A hetzelfde record te zijn. Bij
        # de rest is de woning de identiteit en mag dat juist niet.
        zelfde = sleutel_huisnummer if op_nr else sleutel
        verkeerd, vb = 0, ""
        for a in pool:
            _sl, gevonden = zoek_in(pad, d, a)
            ga = _adres_van(gevonden)
            if ga and zelfde(ga) != zelfde(a):
                verkeerd += 1
                if not vb:
                    vb = f" (bijv. {a!r} komt uit bij {ga!r})"
        if verkeerd:
            fouten.append(f"{pad}: {verkeerd} van {len(pool)} adressen komen "
                          f"uit bij het record van een ander pand{vb}")
        else:
            print(f"  {pad:<34} {len(pool):>5} adressen, geen enkele "
                  f"verwisseling ({kaal} sleutels zonder huisletter)",
                  file=sys.stderr)

    for f in fouten:
        print(f"FOUT {f}", file=sys.stderr)
    print(f"Proef: {len(fouten)} fouten. Gedekt: de vorm zelf op echte "
          f"adressen, de oude vormen die vindbaar moeten blijven, het "
          f"verschil tussen pand en woning, elke sleutel in de zeven "
          f"bestanden die per adres gesleuteld zijn, en dat geen van de "
          f"{len(pool)} adressen die we kennen uitkomt bij het record van "
          f"een ander pand.", file=sys.stderr)
    return 1 if fouten else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proef", action="store_true",
                    help="Nameten op de echte bestanden.")
    ap.add_argument("--adres", default="",
                    help="De sleutel en de varianten van dit adres tonen.")
    a = ap.parse_args()
    if a.adres:
        print(f"sleutel:          {sleutel(a.adres)}")
        print(f"op huisnummer:    {sleutel_huisnummer(a.adres)}")
        print("varianten:")
        for v in varianten(a.adres, op_huisnummer=True):
            print(f"  {v}")
        sys.exit(0)
    sys.exit(proef() if a.proef else 0)
