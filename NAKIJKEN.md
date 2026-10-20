# De brief van vandaag nakijken

Instructie voor de dagelijkse nakijkronde (een geplande taak). Ze staat hier en
niet in de taak zelf, zodat een verbetering een pull request is en Mark hem
ziet. De taak zegt alleen: lees dit bestand en doe wat erin staat.

## Waarom

Op 20 oktober 2026 stonden er in een verhaal vijf onjuiste beweringen. Drie
kwamen niet van de schrijver maar uit de gegevens: een losse aanvraag die als
beleid binnenkwam, een winkelgevel die naar de schrijver ging, een duiding die
de opkoopbescherming verkeerd uitlegde. Ze waren alleen te vinden door elke
zin terug te volgen naar zijn bron. Dat is deze ronde: elke dag, en de
oplossing bij de bron, als pull request.

## De grenzen

- **Je merget niets.** Je opent een pull request; Mark accepteert ze een voor
  een.
- **Je start geen workflow** en verstuurt geen mail, met een uitzondering:
  `kopie_pa.yml` aan het eind (stap 6). Een testrun van de brief doe je niet;
  meet offline (zie stap 5).
- **Repo-zichtbaarheid en secrets** zijn van Mark. Niet aanraken.
- **Geen inhoud uit de mailbox** in een issue of pull request.
- Lees `CLAUDE.md` en volg de werkwijze daarin: meten in plaats van schatten,
  elke proef breken om te zien of hij vuurt, alles wat je leert in de repo.

## Stappen

1. **Is er een brief van vandaag?** Neem de datum in UTC. Staat
   `digests/<datum>-verhaal.md` niet in main, kijk dan of de briefrun nog
   loopt:
   `gh api "repos/DerksenVastgoed/DerksenVastgoed-Vastgoedrapport-Nijmegen/actions/workflows/bekendmakingen.yml/runs?per_page=3"`.
   Loopt hij, wacht dan (elke tien minuten kijken, hooguit twee uur; op zondag
   duurt de weekeditie langer). Is er geen brief, meld dat in een zin en stop.

2. **Kijk welke pull requests er al open staan**
   (`gh api repos/DerksenVastgoed/DerksenVastgoed-Vastgoedrapport-Nijmegen/pulls`).
   Een fout waarvoor al een PR openstaat, los je niet nog een keer op; noem hem
   alleen.

3. **Bouw de gegevens op die de schrijver kreeg:**
   `python3 brief_invoer.py --datum <datum> > /tmp/invoer.txt`.
   Lees daarnaast `controle_brief.json`: wat vond de feitencontrole voor en na
   de herstelronde?

4. **Loop het verhaal zin voor zin na** tegen `/tmp/invoer.txt` en, waar nodig,
   tegen de bestanden waar de gegevens uit komen (`voorraad.json`,
   `buurten_cbs.json`, `woningprijsindex.json`, `bekendmakingen_vandaag.json`,
   de digests van die dag). Per bewering met een getal, adres, buurt, datum,
   besluit of oorzaak: klopt het, klopt het niet, of staat het nergens? En
   ook: zinnen die iets noemen om te zeggen dat het er niet toe doet.
   Schrijf voor elke fout op:
   - wat er staat en wat de gegevens zeggen;
   - **waar hij vandaan komt**: zat hij al in de gegevens (dan is de bron het
     probleem: een filter, een duiding, een ontbrekend veld), of maakte de
     schrijver hem;
   - **of de feitencontrole hem zag** (`controle_brief.json`). Zo niet, waarom
     niet.

5. **Los de belangrijkste fout op bij de bron**, als dat met een kleine,
   meetbare wijziging kan. Een fout per pull request.
   - Werk op een nieuwe tak `claude/<datum>-nakijken`.
   - Schrijf de geschiedenis van de fout in de docstring of het commentaar van
     de functie die hem maakte, met de datum en het voorbeeld.
   - Een proef op het echte geval; breek de wijziging en kijk of de proef
     vuurt.
   - Een eis in `eisen.txt` met waarom en proef.
   - Raakt het `marktprijzen_bag.py`, meet dan het effect: draai
     `python3 marktprijzen_bag.py --modus dagelijks --uit ... --dossiers ...
     --input verkopen.txt` in twee worktrees (main en jouw tak) met
     `GEHEUGEN_ALLEEN_LEZEN=1`, en vergelijk de dossiers.
   - `python3 eisen.py --proef` en `python3 tak.py` moeten schoon zijn.
   - Open de pull request via de REST-api (`gh api .../pulls -f ...`; GraphQL
     werkt niet vanuit deze omgeving). In de beschrijving: wat er in de brief
     stond, wat de gegevens zeggen, waar de fout vandaan kwam, wat er gemeten
     is, en wat nog niet klopt.
   Is er geen fout die je met zekerheid bij de bron kunt oplossen, open dan
   geen pull request. Zet de bevindingen in `VERBETERLIJST.md` onder "Nakijken"
   alleen als ze een terugkerend patroon zijn, en dan in een pull request.

6. **Laat de brief naar pa gaan.** Sinds 20 oktober krijgt pa de brief pas na
   deze ronde (zie `kopie_pa.py`). Start `kopie_pa.yml` op main:
   - Stond er niets fout in het verhaal: zonder correcties.
     `gh api -X POST repos/DerksenVastgoed/DerksenVastgoed-Vastgoedrapport-Nijmegen/actions/workflows/kopie_pa.yml/dispatches -f ref=main -f "inputs[datum]=<datum>"`
   - Stonden er fouten in: met de zinnen letterlijk zoals ze in het verhaal
     staan, en wat de gegevens zeggen. Het verhaal wordt dan met alleen die
     correcties herschreven en de verbeterde brief gaat naar pa.
     `-f 'inputs[correcties]=[{"zin": "...", "waarom": "..."}]'`
   - Alleen fouten die je met de gegevens kunt aanwijzen. Twijfel is geen
     correctie: noem hem in je bericht aan Mark.
   - Zegt `pa_kopie.json` dat het een halve update was of dat hij al
     verstuurd is, dan start je niets; de workflow zou het ook weigeren.
   - Kijk na een paar minuten of de run gelukt is en of `pa_kopie.json` op main
     `verstuurd` heeft. Zo niet, meld het; om 08:52 gaat de brief zoals hij
     was alsnog.

7. **Meld Mark** in drie tot vijf zinnen, in het Nederlands, zonder
   gedachtestreepjes: hoeveel beweringen je nakeek, welke fouten erin stonden,
   welke de feitencontrole miste, of de brief met of zonder correcties naar pa
   ging, en welke pull request je opende (met link).
   Stond er niets fout, zeg dat in een zin. Verzin niets: wat je niet kon
   nagaan, noem je zo.
