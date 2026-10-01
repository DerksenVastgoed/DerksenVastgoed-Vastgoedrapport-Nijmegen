#!/usr/bin/env python3
"""
Hoogtes en oppervlakken per pand uit de 3D BAG, bewaard in de eigen repo.

Waarom in de repo: als de bron wegvalt of van opzet verandert, hebben we onze
eigen panden nog. Het landelijke bestand is ruim een gigabyte en past daar niet
in, maar onze paar duizend panden wel; dat is een bestand van enkele
megabytes.

Wat we eruit halen, en waarom het telt voor de bouwkosten:
- b3_opp_buitenmuur: het buitenmuuroppervlak in m2. Dit is de hele schil van
  het pand, dus inclusief de zijgevels die tegen de buren staan; die eraf halen
  is een volgende stap.
- b3_opp_dak_plat en b3_opp_dak_schuin: het dakoppervlak, gesplitst.
- b3_opp_grond: het grondvlak, nodig om het aantal bouwlagen te controleren.
- b3_bouwlagen: het geschatte aantal bouwlagen.
- b3_h_nok en b3_h_maaiveld: nokhoogte en maaiveld, allebei in NAP.
- b3_kwaliteitsindicator: zegt of de meting betrouwbaar is; zonder AHN-dekking
  kunnen de waarden leeg of onbruikbaar zijn.

Bron: 3D BAG, 3D Geoinformation Research Group TU Delft en 3DGI, op basis van
de BAG en het Actueel Hoogtebestand Nederland. Licentie CC BY 4.0, dus de bron
hoort vermeld te worden waar we de cijfers gebruiken.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

UIT_PAD = "bag3d.json"
API = "https://api.3dbag.nl/collections/pand/items"
PER_RONDE = int(os.environ.get("BAG3D_PER_RONDE") or 300)

VELDEN = ("b3_opp_buitenmuur", "b3_opp_dak_plat", "b3_opp_dak_schuin",
          "b3_opp_grond", "b3_bouwlagen", "b3_h_nok", "b3_h_maaiveld",
          "b3_dak_type", "b3_volume_lod13", "b3_kwaliteitsindicator",
          "identificatie", "bouwjaar")


def lees(pad=UIT_PAD):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"versie": "", "panden": {}, "bijgewerkt": ""}


PREFIX = "NL.IMBAG.Pand."


def volledig_id(pand_id):
    """
    Het pand-id zoals de 3D BAG het verwacht.

    Wij bewaren het kale nummer uit de BAG, zoals 0268100000001130. De 3D BAG
    wil er NL.IMBAG.Pand. voor; zonder dat voorvoegsel antwoordt de bron met
    een 502 op elk verzoek, en dat is geen fout die zichzelf verklaart.
    """
    pand_id = (pand_id or "").strip()
    return pand_id if pand_id.startswith(PREFIX) else PREFIX + pand_id


def _haal(pand_id):
    """De 3D BAG-gegevens van een pand, of None als er niets is."""
    url = f"{API}/{volledig_id(pand_id)}"
    verzoek = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "NijmegenVastgoedMonitor/1.0"})
    try:
        with urllib.request.urlopen(verzoek, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _velden_uit(antwoord):
    """
    De velden die we willen, waar ze ook zitten.

    De API geeft een GeoJSON-feature terug; bij een pand met meerdere delen
    zitten de kenmerken soms een laag dieper. Daarom hier zoeken in plaats van
    een vaste plek aannemen: een verandering in de opzet van de bron mag geen
    lege waarden opleveren zonder dat iemand het merkt.
    """
    kandidaten = []
    if isinstance(antwoord, dict):
        kandidaten.append(antwoord.get("properties") or {})
        kandidaten.append(antwoord)
        for deel in (antwoord.get("features") or []):
            if isinstance(deel, dict):
                kandidaten.append(deel.get("properties") or {})
        # De 3D BAG antwoordt in CityJSON: de kenmerken zitten onder
        # feature.CityObjects.<id>.attributes, niet in properties.
        for blok in (antwoord.get("feature"), antwoord):
            if not isinstance(blok, dict):
                continue
            for obj in (blok.get("CityObjects") or {}).values():
                if isinstance(obj, dict):
                    kandidaten.append(obj.get("attributes") or {})
    uit = {}
    for bron in kandidaten:
        if not isinstance(bron, dict):
            continue
        for veld in VELDEN:
            if veld in bron and bron[veld] is not None and veld not in uit:
                uit[veld] = bron[veld]
    return uit


def te_doen(opgeslagen, pand_ids, versie_nu):
    """
    Welke panden opgehaald moeten worden.

    Bij een nieuwe versie van de bron opnieuw alles, want dan is de
    hoogtemeting vernieuwd. Anders alleen wat we nog niet hebben.
    """
    if versie_nu and opgeslagen.get("versie") and versie_nu != opgeslagen["versie"]:
        return list(pand_ids), True
    return [p for p in pand_ids if p not in opgeslagen.get("panden", {})], False


def pand_ids_uit_geschiedenis(pad="pandgeschiedenis.json"):
    """De pand-ids die we al kennen uit de geschiedenis per pand."""
    try:
        with open(pad, encoding="utf-8") as f:
            g = json.load(f)
    except Exception:
        return []
    ids = []
    for pand in g.values():
        pid = pand.get("pand_id")
        if pid and pid not in ids:
            ids.append(pid)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uit", default=UIT_PAD)
    ap.add_argument("--per-ronde", type=int, default=PER_RONDE)
    ap.add_argument("--versie", default="",
                    help="versie van de bron; bij een andere waarde wordt alles "
                         "opnieuw opgehaald")
    args = ap.parse_args()

    opgeslagen = lees(args.uit)
    ids = pand_ids_uit_geschiedenis()
    if not ids:
        print("Geen pand-ids bekend; draai eerst de geschiedenisstap",
              file=sys.stderr)
        return 0

    wachtrij, opnieuw = te_doen(opgeslagen, ids, args.versie)
    if opnieuw:
        print(f"Nieuwe versie van de bron ({args.versie}); alles opnieuw",
              file=sys.stderr)
    if not wachtrij:
        print(f"3D BAG bij: {len(opgeslagen.get('panden', {}))} panden",
              file=sys.stderr)
        return 0

    gedaan, leeg, fout = 0, 0, 0
    for pand_id in wachtrij[:args.per_ronde]:
        try:
            antwoord = _haal(pand_id)
        except Exception as e:
            fout += 1
            if fout <= 3:
                print(f"  {pand_id}: {str(e)[:90]}", file=sys.stderr)
            if fout > 20:
                print("Te veel fouten; de bron lijkt onbereikbaar of veranderd",
                      file=sys.stderr)
                break
            continue
        velden = _velden_uit(antwoord) if antwoord else {}
        if not velden:
            leeg += 1
            opgeslagen.setdefault("panden", {})[pand_id] = {"leeg": True}
            continue
        velden["opgehaald"] = dt.date.today().isoformat()
        opgeslagen.setdefault("panden", {})[pand_id] = velden
        gedaan += 1

    if args.versie:
        opgeslagen["versie"] = args.versie
    opgeslagen["bijgewerkt"] = dt.date.today().isoformat()
    opgeslagen["bron"] = ("3D BAG, TU Delft en 3DGI, op basis van de BAG en het "
                          "AHN; CC BY 4.0")
    with open(args.uit, "w", encoding="utf-8") as f:
        json.dump(opgeslagen, f, ensure_ascii=False, indent=1)

    rest = max(0, len(wachtrij) - args.per_ronde)
    print(f"3D BAG: {gedaan} panden opgehaald, {leeg} zonder gegevens, "
          f"{fout} fouten, nog {rest} te gaan "
          f"(totaal {len(opgeslagen.get('panden', {}))})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
