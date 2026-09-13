"""Farben der Personen."""

from __future__ import annotations

import pytest

from custom_components.family_calendar.domain.colors import (
    PALETTE,
    luminance,
    rgb_to_hex,
    suggest_color,
    to_rgb,
)


def test_rgb_to_hex() -> None:
    assert rgb_to_hex((111, 168, 220)) == "#6fa8dc"
    assert rgb_to_hex([0, 0, 0]) == "#000000"
    assert rgb_to_hex([255, 255, 255]) == "#ffffff"


@pytest.mark.parametrize("wert", [(256, 0, 0), (-1, 0, 0), (1, 2), (1, 2, 3, 4)])
def test_ungueltige_farben(wert: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        to_rgb(wert)


def test_palette_ohne_doppelte_farben() -> None:
    assert len(set(PALETTE)) == len(PALETTE) == 8


@pytest.mark.parametrize("farbe", PALETTE)
def test_palette_traegt_dunkle_schrift(farbe: tuple[int, int, int]) -> None:
    """Oberhalb von 0.6 waehlt die Daylight-Karte schwarze Schrift."""
    assert luminance(farbe) > 0.6


def test_vorschlag_nimmt_die_erste_freie_farbe() -> None:
    assert suggest_color([]) == PALETTE[0]
    assert suggest_color([list(PALETTE[0]), PALETTE[1]]) == PALETTE[2]
    assert suggest_color([PALETTE[1]]) == PALETTE[0]


def test_vorschlag_wiederholt_die_palette_wenn_alle_vergeben_sind() -> None:
    assert suggest_color(PALETTE) == PALETTE[0]
    assert suggest_color([*PALETTE, PALETTE[0]]) == PALETTE[1]
