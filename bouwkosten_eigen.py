# Eigen bouwkosten per vierkante meter
#
# Wat hier staat gaat voor op de aannames in marktprijzen_bag.py. Een getal uit
# de eigen administratie is altijd beter dan een geschat kental, ook als het uit
# het hoofd komt: jij hebt in Nijmegen gebouwd, het script niet.
#
# FORMAAT
#   soort | euro per m2 | peildatum | toelichting
#
# SOORTEN
#   verduurzaming-g    kosten om vanaf label G naar B of beter te komen
#   verduurzaming-f    idem vanaf label F
#   verduurzaming-e    idem vanaf E
#   verduurzaming-d    idem vanaf D
#   verduurzaming-c    idem vanaf C
#   verduurzaming      geldt voor alle labels waarvoor niets specifieks staat
#   verhuurklaar       keuken, badkamer, schilderwerk, vloeren, elektra
#
# De bedragen zijn EXCLUSIEF btw; het script telt daar 15% bij op, de menging
# van 9% arbeid en 21% materiaal die het PBL hanteert. Staat jouw bedrag al
# inclusief btw, deel het dan door 1,15 voordat je het hier zet.
#
# De peildatum is belangrijk: het script indexeert vanaf mei 2025 met de CBS
# bouwkostenindex. Is jouw cijfer van een ander moment, zet dat er dan bij, dan
# passen we de indexering daarop aan.
#
# WAT HET SCRIPT NU AANNEEMT, zodat je ziet wat je vervangt:
#   verduurzaming-g    550
#   verduurzaming-f    475
#   verduurzaming-e    400
#   verduurzaming-d    275
#   verduurzaming-c    150
#   verduurzaming-a/b    0
#   verhuurklaar       275
#
# Dat zijn getallen die Claude heeft gekozen, niet overgenomen uit de
# RVO-kostenkentallen. Die kentallen bestaan wel en staan op
# regelhulpenvoorbedrijven.nl/kostenkentallen, maar zijn nog niet ingelezen.
#
# JE HEBT GEEN FACTUREN NODIG om dit te verbeteren. Een bedrag uit je hoofd met
# een marge eromheen is al beter dan een aanname van buiten. Vul in wat je weet,
# en scherp het aan zodra je de administratie erbij hebt.
#
# VOORBEELD, verwijder het hekje en pas de bedragen aan:
# verhuurklaar | 310 | 2026-06 | keuken en badkamer Graafsedwarsstraat, excl btw
# verduurzaming-e | 385 | 2026-03 | dak, spouw en HR++ bij een pand uit 1920
