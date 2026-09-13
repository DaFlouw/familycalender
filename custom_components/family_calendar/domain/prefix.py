"""Auswertung der Kuerzel am Anfang eines Termintitels.

Regel: Das erste Wort des Titels ist ein Kuerzel, wenn es ausschliesslich aus
Buchstaben der eingerichteten Personen besteht und jeden davon hoechstens einmal
enthaelt. Reihenfolge sowie Gross- und Kleinschreibung spielen keine Rolle.

Ein Titel ohne gueltiges Kuerzel betrifft **alle** Personen. Dazu zaehlen auch
Titel wie ``Alle Hochzeit`` oder ``FF Test``: Ein Wort mit fremden oder doppelten
Buchstaben ist kein Kuerzel.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

#: Erstes Wort, gefolgt von Leerraum oder dem Ende des Titels.
_FIRST_WORD = re.compile(r"\s*(\S+)(?:\s|$)")


class InvalidLetterError(ValueError):
    """Ein Personenkuerzel ist kein einzelner Buchstabe."""


def normalize_letter(value: str) -> str:
    """Bringt ein Personenkuerzel in die gespeicherte Form: ein Grossbuchstabe.

    Abgelehnt wird alles, was nach dem Umwandeln nicht genau ein Buchstabe ist.
    Das betrifft auch ``ß``, dessen Grossform ``SS`` zwei Zeichen hat.
    """
    letter = value.strip().upper()
    if len(letter) != 1 or not letter.isalpha():
        raise InvalidLetterError(value)
    return letter


def normalize_letters(values: Iterable[str]) -> frozenset[str]:
    """Normalisiert eine Menge von Personenkuerzeln."""
    return frozenset(normalize_letter(value) for value in values)


def affected_letters(summary: str | None, letters: frozenset[str]) -> frozenset[str]:
    """Liefert die Kuerzel der Personen, die ein Termin betrifft.

    ``letters`` muss bereits normalisiert sein (siehe :func:`normalize_letters`).
    """
    if not letters:
        return letters

    match = _FIRST_WORD.match(summary or "")
    if match is None:
        return letters

    word = match.group(1).upper()
    characters = frozenset(word)
    if len(characters) == len(word) and characters <= letters:
        return characters
    return letters
