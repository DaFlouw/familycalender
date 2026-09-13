"""Kuerzelregel: welche Personen betrifft ein Termin?

Alle Titel sind erfunden.
"""

from __future__ import annotations

import itertools
import random

import pytest

from custom_components.family_calendar.domain.prefix import (
    InvalidLetterError,
    affected_letters,
    normalize_letter,
    normalize_letters,
)

FAMILIE = normalize_letters("FAEC")

#: Jede Kombination und Reihenfolge aus ein bis vier Buchstaben.
ALLE_KUERZEL = [
    "".join(buchstaben)
    for anzahl in range(1, 5)
    for buchstaben in itertools.permutations("FAEC", anzahl)
]


def _schreibweisen(kuerzel: str) -> list[str]:
    zufall = random.Random(kuerzel)
    gemischt = "".join(c.lower() if zufall.random() < 0.5 else c for c in kuerzel)
    return [kuerzel, kuerzel.lower(), gemischt]


def test_es_gibt_64_kuerzel() -> None:
    assert len(ALLE_KUERZEL) == 4 + 12 + 24 + 24
    assert len(set(ALLE_KUERZEL)) == 64


@pytest.mark.parametrize("kuerzel", ALLE_KUERZEL)
def test_jedes_kuerzel_in_jeder_schreibweise(kuerzel: str) -> None:
    for variante in _schreibweisen(kuerzel):
        for titel in (
            f"{variante} Zahnarzt",
            variante,
            f"  {variante} Zahnarzt",
            f"{variante}\tZahnarzt",
            f"{variante}  Treffen mit F und A",
        ):
            assert affected_letters(titel, FAMILIE) == frozenset(kuerzel), titel


@pytest.mark.parametrize(
    "titel",
    [
        None,
        "",
        "   ",
        "Alle Sommerfest",
        "Übernachtung bei Oma",
        "FF doppelter Buchstabe",
        "CAC doppelter Buchstabe",
        "cAc doppelt in anderer Schreibweise",
        "CAFEF zu lang",
        "F-Jugend Spiel",
        "A2 Raststaette",
        "F.Physio",
        "AB unbekannter Buchstabe",
        "Fee holen",
        "Einkaufen F",
    ],
)
def test_ohne_gueltiges_kuerzel_sind_alle_betroffen(titel: str | None) -> None:
    assert affected_letters(titel, FAMILIE) == FAMILIE


def test_nur_das_erste_wort_zaehlt() -> None:
    assert affected_letters("E CA Training", FAMILIE) == {"E"}


def test_woerter_aus_kuerzelbuchstaben_gelten_als_kuerzel() -> None:
    """Bekannte Grenze der Regel, in der README beschrieben."""
    assert affected_letters("Cafe Treffen", FAMILIE) == FAMILIE
    assert affected_letters("Ca 10 Uhr Abfahrt", FAMILIE) == {"C", "A"}


def test_andere_buchstaben() -> None:
    buchstaben = normalize_letters(["m", "P", "L"])
    assert affected_letters("ML Kino", buchstaben) == {"M", "L"}
    assert affected_letters("F Kino", buchstaben) == buchstaben


def test_umlaute_als_kuerzel() -> None:
    buchstaben = normalize_letters(["Ö", "a"])
    assert affected_letters("öA Ausflug", buchstaben) == {"Ö", "A"}


def test_ohne_personen_ist_niemand_betroffen() -> None:
    assert affected_letters("F Zahnarzt", frozenset()) == frozenset()


@pytest.mark.parametrize(("eingabe", "erwartet"), [("f", "F"), (" e ", "E"), ("Ä", "Ä")])
def test_normalize_letter(eingabe: str, erwartet: str) -> None:
    assert normalize_letter(eingabe) == erwartet


@pytest.mark.parametrize("eingabe", ["", " ", "AB", "1", "-", "ß"])
def test_normalize_letter_lehnt_ab(eingabe: str) -> None:
    with pytest.raises(InvalidLetterError):
        normalize_letter(eingabe)


def test_ergebnis_ist_nie_leer_und_nie_fremd() -> None:
    zufall = random.Random(4711)
    zeichen = "FAECfaecXx -\t"
    for _ in range(5000):
        titel = "".join(zufall.choice(zeichen) for _ in range(zufall.randint(0, 12)))
        ergebnis = affected_letters(titel, FAMILIE)
        assert ergebnis
        assert ergebnis <= FAMILIE
