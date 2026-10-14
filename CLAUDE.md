# Lees dit voordat je iets bouwt

Dit bestand bestaat omdat Mark anders bij elke nieuwe sessie moet typen "kijk
eerst wat er in de repo staat". Een instructie die een mens moet onthouden,
wordt vergeten; dat is dezelfde fout als een lijst met namen die bijgewerkt
moet worden, en die fout is hier vier keer gemaakt.

## Eerst lezen, in deze volgorde

1. **`eisen.txt`**. Elke eis zegt wat de regel is, WAAROM hij
   bestaat (met de datum en het incident) en welke proef hem afdwingt. Dit is
   geen stijlgids maar een lijst van fouten die al een keer gemaakt zijn. Bijna
   elke eis komt uit iets dat stil misging. Hoeveel het er zijn zegt
   `eisen.py --proef`; dat getal staat hier niet, want een getal in
   lopende tekst veroudert.
2. **`VERBETERLIJST.md`**. Wat we nog willen bouwen en waarom. Geen planning
   maar een geheugen.
3. **`python3 eisen.py --proef`**. Draai dit voor je begint en voor je
   committeert. Het leest alle eisen, kijkt of elke genoemde proef nog bestaat
   en draait ze.
4. **`python3 tak.py`** voordat je pusht. Die meldt of je tak botst met main of
   met een andere open PR, en of de PR van je tak al gemerged is terwijl er nog
   commits op staan.

## De werkwijze die hier geldt

- **Meet voordat je iets beweert.** Geen schattingen, alleen harde of
  narekenbare getallen. Een getal uit een eigen scriptje naast de module is
  geen meting van de module; dat verschil kostte op 14 oktober 64 tegen 8.
- **Leid een regel af uit echte gegevens, nooit uit een verzonnen geval.** Een
  proef die op je eigen aanname rust, meet je aanname.
- **Breek elke controle om te zien of hij vuurt.** Blijft hij stil, dan kan hij
  de fout niet zien waarvoor hij is geschreven, en dan moet de proef veranderen
  en niet de code. Dit gebeurt vaak: reken erop.
- **Een melding die afgaat bij goed gedrag is erger dan geen melding.** Hij
  leert de lezer het verslag over te slaan.
- **"Niet gekeken" en "gekeken en niets gevonden" krijgen nooit hetzelfde
  woord.** Hetzelfde voor "niet gemeten" en "nul".
- **Een veld heet naar wat het meet**, niet naar wat je wilde weten.
- **Een afgeleid verband mag er niet uitzien als een hard verband.** Zet erbij
  hoe je eraan komt.
- **Eén implementatie per afspraak.** Twee plekken die hetzelfde doen, lopen
  uiteen.
- **Alles wat je leert gaat in de repo**, in het bestand waar het over gaat:
  een eis in `eisen.txt`, kennis in `bronnen.py`, de geschiedenis van een fout
  in de docstring van de functie die hem maakte. Wat alleen in een chat staat,
  is weg.

## Harde grenzen, niet in code af te dwingen

- **Tekeningen uit bouwdossiers komen nooit in de repo.** Op die documenten
  rust auteursrecht en de digitale kopie is uitsluitend voor persoonlijk
  gebruik; deze repo is openbaar. Eigen metingen eruit ("op deze laag is 48 m2
  bruikbaar") zijn onze observatie en mogen wel.
- **`jeleefomgeving.nl` geeft ROBOTS_DISALLOWED.** Daar wordt niet
  geautomatiseerd opgehaald, van geen enkel netwerk, ook niet achter een
  menselijke klik. Wat telt is niet waar de code draait maar of een mens elke
  ophaalactie kiest.
- **Zichtbaarheid van de repo en de secrets zijn van Mark.** Claude zet die
  niet om en maakt geen tokens aan.
- **Een samenvatting uit de mailbox in een openbaar issue bevat nooit
  afzender, onderwerp, link of inhoud.** Alleen aantallen en vormen.
- **De brief gaat naar pa.** Bij een halve update gaat de kopie eraf; zie de
  eis daarover. Een testrun gaat alleen naar Mark.

## Hoe Mark werkt

Hij accepteert pull requests een voor een en wil directe tegenspraak, geen
bevestiging. Hij leest de uitleg in de PR, dus die moet zeggen wat er is
gemeten en wat er nog niet klopt. Hij schrijft via spraak naar tekst, dus een
enkel woord kan fonetisch verkeerd staan; vraag niet na wat uit de context
duidelijk is.
