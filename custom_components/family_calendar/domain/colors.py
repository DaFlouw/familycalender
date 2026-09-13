"""Farben der Personen.

Home Assistant liefert Farben aus dem Farbwaehler als RGB-Liste, Kalenderkarten
erwarten Hex-Werte. Die Palette ist so gewaehlt, dass dunkle Schrift auf jeder
Farbe lesbar bleibt, auch auf gestreiften Terminen mehrerer Personen.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

type RGB = tuple[int, int, int]

PALETTE: tuple[RGB, ...] = (
    (111, 168, 220),  # Blau
    (244, 166, 198),  # Rosa
    (147, 196, 125),  # Gruen
    (246, 178, 107),  # Orange
    (180, 160, 220),  # Lila
    (110, 200, 200),  # Tuerkis
    (240, 205, 100),  # Senf
    (235, 140, 140),  # Koralle
)


def to_rgb(value: Sequence[int]) -> RGB:
    """Prueft eine RGB-Angabe und gibt sie als Tupel zurueck."""
    if len(value) != 3:
        raise ValueError(f"RGB braucht drei Werte, nicht {len(value)}")
    red, green, blue = (int(channel) for channel in value)
    for channel in (red, green, blue):
        if not 0 <= channel <= 255:
            raise ValueError(f"RGB-Wert ausserhalb von 0 bis 255: {channel}")
    return red, green, blue


def rgb_to_hex(value: Sequence[int]) -> str:
    """Wandelt RGB in die Hex-Schreibweise ``#rrggbb``."""
    red, green, blue = to_rgb(value)
    return f"#{red:02x}{green:02x}{blue:02x}"


def luminance(value: Sequence[int]) -> float:
    """Wahrgenommene Helligkeit zwischen 0 und 1.

    Dieselbe Formel, mit der die Daylight Calendar Card zwischen schwarzer und
    weisser Schrift waehlt.
    """
    red, green, blue = to_rgb(value)
    return (0.299 * red + 0.587 * green + 0.114 * blue) / 255


def suggest_color(used: Iterable[Sequence[int]]) -> RGB:
    """Schlaegt die erste noch nicht vergebene Farbe der Palette vor."""
    taken = [to_rgb(color) for color in used]
    for color in PALETTE:
        if color not in taken:
            return color
    return PALETTE[len(taken) % len(PALETTE)]
