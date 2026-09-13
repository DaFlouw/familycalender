"""Farbabgleich fuer Daylight-Calendar-Karten in einer Dashboard-Konfiguration.

Die Karte liest Kalenderfarben ausschliesslich aus ihrem eigenen ``colors``-Feld.
Damit die Farben der Integration dort ankommen, werden sie hier eingetragen --
nur fuer Kalender dieser Integration, die die Karte tatsaechlich anzeigt.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

DAYLIGHT_CARD_TYPE = "custom:daylight-calendar-card"


def iter_cards(node: Any) -> Iterator[dict[str, Any]]:
    """Liefert jedes Objekt mit ``type`` aus einer Dashboard-Konfiguration.

    Durchlaeuft die Konfiguration vollstaendig statt nur bekannter Behaelter:
    Karten stecken in Ansichten, Abschnitten, Stapeln, bedingten Karten und in
    Behaeltern von Zusatzkarten, deren Aufbau hier nicht bekannt sein muss.
    """
    stack: list[Any] = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if isinstance(current.get("type"), str):
                yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def card_entity_ids(card: Mapping[str, Any]) -> set[str]:
    """Die Kalender, die eine Karte anzeigt."""
    entities = card.get("entities")
    if not isinstance(entities, list):
        return set()

    entity_ids: set[str] = set()
    for item in entities:
        if isinstance(item, str):
            entity_ids.add(item)
        elif isinstance(item, dict):
            value = item.get("entity") or item.get("entity_id")
            if isinstance(value, str):
                entity_ids.add(value)
    return entity_ids


def apply_colors(config: Any, colors: Mapping[str, str]) -> int:
    """Traegt Farben in alle Daylight-Karten ein und zaehlt die Aenderungen.

    Veraendert ``config`` an Ort und Stelle. Gleiche Farben in anderer
    Schreibweise (``#ABCDEF`` gegenueber ``#abcdef``) gelten nicht als Aenderung.
    """
    changed = 0
    for card in iter_cards(config):
        if card.get("type") != DAYLIGHT_CARD_TYPE:
            continue

        shown = card_entity_ids(card) & colors.keys()
        if not shown:
            continue

        card_colors = card.get("colors")
        if not isinstance(card_colors, dict):
            card_colors = {}

        changed_here = 0
        for entity_id in sorted(shown):
            wanted = colors[entity_id]
            if str(card_colors.get(entity_id, "")).lower() != wanted.lower():
                card_colors[entity_id] = wanted
                changed_here += 1

        if changed_here:
            card["colors"] = card_colors
            changed += changed_here
    return changed
