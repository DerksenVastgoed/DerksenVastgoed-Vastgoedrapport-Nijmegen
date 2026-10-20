#!/usr/bin/env python3
"""
Getallen in Nederlandse notatie: punt voor duizendtallen, komma voor
decimalen. Een implementatie voor de hele repo.

WAAROM. 20 oktober 2026. Op acht plekken stond f"... €{x:,} ...".replace(",",
"."), en daar ving de vervanging ook de komma's in de zin zelf en de decimale
punt. In de brief stond "gemeten premie 1.425 voor die klasse. dus €7.746/m2
tegen de buurtmediaan van €5.436/m2. samen €1.223.827": de premie is 1,425 en
de zin liep door met een komma. eisen.py zoekt sindsdien naar die vorm
(komma_vervanging).

  euro(1223827)        -> "€1.223.827"
  euro(1234.5, 2)      -> "€1.234,50"
  getal(1.425, 3)      -> "1,425"
"""
import sys


def getal(x, decimalen=0):
    """Nederlandse notatie zonder valutateken."""
    t = f"{x:,.{decimalen}f}"
    return t.replace(",", "\0").replace(".", ",").replace("\0", ".")


def euro(x, decimalen=0):
    return "€" + getal(x, decimalen)


def proef():
    afw = []
    for gegeven, verwacht in (((1223827,), "€1.223.827"),
                              ((1234.5, 2), "€1.234,50"),
                              ((278000,), "€278.000"),
                              ((534.7, 2), "€534,70"),
                              ((-6422,), "€-6.422")):
        if euro(*gegeven) != verwacht:
            afw.append(f"euro{gegeven} geeft {euro(*gegeven)!r}, niet "
                       f"{verwacht!r}")
    if getal(1.425, 3) != "1,425" or getal(0.5, 2) != "0,50":
        afw.append(f"decimalen worden verkeerd geschreven: {getal(1.425, 3)}")
    for a in afw:
        print("AFWIJKING: " + a, file=sys.stderr)
    print(f"Proef getal: {len(afw)} afwijkingen", file=sys.stderr)
    return 1 if afw else 0


if __name__ == "__main__":
    sys.exit(proef() if "--proef" in sys.argv else 0)
