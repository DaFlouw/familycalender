"""Farb- und Namensabgleich in Dashboard-Konfigurationen."""

from __future__ import annotations

import copy
from typing import Any

from custom_components.family_calendar.domain.cards import (
    DAYLIGHT_CARD_TYPE,
    apply_colors,
    apply_names,
    card_entity_ids,
    iter_cards,
)

FARBEN = {
    "calendar.familie_anna": "#6fa8dc",
    "calendar.familie_ben": "#f4a6c6",
}

NAMEN = {
    "calendar.familie_anna": "Anna",
    "calendar.familie_ben": "Ben",
}


def _karte(**felder: Any) -> dict[str, Any]:
    return {"type": DAYLIGHT_CARD_TYPE, **felder}


def _dashboard(*karten: dict[str, Any]) -> dict[str, Any]:
    return {
        "views": [
            {
                "type": "sections",
                "sections": [
                    {"type": "grid", "cards": [{"type": "vertical-stack", "cards": list(karten)}]}
                ],
            }
        ]
    }


def test_traegt_farben_in_verschachtelte_karte_ein() -> None:
    karte = _karte(entities=["calendar.familie_anna", "calendar.familie_ben"])
    config = _dashboard(karte)

    assert apply_colors(config, FARBEN) == 2
    assert karte["colors"] == FARBEN


def test_behaelt_fremde_farben_und_ueberschreibt_nur_eigene() -> None:
    karte = _karte(
        entities=["calendar.muell", "calendar.familie_anna"],
        colors={"calendar.muell": "#a1a1a1", "calendar.familie_anna": "#000000"},
    )

    assert apply_colors(_dashboard(karte), FARBEN) == 1
    assert karte["colors"] == {"calendar.muell": "#a1a1a1", "calendar.familie_anna": "#6fa8dc"}


def test_nur_angezeigte_kalender_bekommen_eine_farbe() -> None:
    karte = _karte(entities=["calendar.familie_ben"])
    apply_colors(_dashboard(karte), FARBEN)
    assert karte["colors"] == {"calendar.familie_ben": "#f4a6c6"}


def test_zweiter_durchlauf_aendert_nichts() -> None:
    config = _dashboard(_karte(entities=list(FARBEN)))
    apply_colors(config, FARBEN)
    apply_names(config, NAMEN)
    vorher = copy.deepcopy(config)

    assert apply_colors(config, FARBEN) == 0
    assert apply_names(config, NAMEN) == 0
    assert config == vorher


def test_schreibweise_der_farbe_ist_keine_aenderung() -> None:
    karte = _karte(entities=["calendar.familie_anna"], colors={"calendar.familie_anna": "#6FA8DC"})
    assert apply_colors(_dashboard(karte), FARBEN) == 0
    assert karte["colors"] == {"calendar.familie_anna": "#6FA8DC"}


def test_andere_kartentypen_bleiben_unberuehrt() -> None:
    fremd = {"type": "custom:calendar-card-pro", "entities": ["calendar.familie_anna"]}
    kalender = {"type": "calendar", "entities": ["calendar.familie_anna"]}
    config = _dashboard(fremd, kalender)
    vorher = copy.deepcopy(config)

    assert apply_colors(config, FARBEN) == 0
    assert apply_names(config, NAMEN) == 0
    assert config == vorher


def test_karte_ohne_eigene_kalender_bleibt_unberuehrt() -> None:
    karte = _karte(entities=["calendar.muell"])
    assert apply_colors(_dashboard(karte), FARBEN) == 0
    assert apply_names(_dashboard(karte), NAMEN) == 0
    assert "colors" not in karte
    assert "calendar_names" not in karte


def test_ungueltiges_farbfeld_wird_ersetzt() -> None:
    karte = _karte(entities=["calendar.familie_anna"], colors="kaputt")
    assert apply_colors(_dashboard(karte), FARBEN) == 1
    assert karte["colors"] == {"calendar.familie_anna": "#6fa8dc"}


def test_entities_als_objekte() -> None:
    karte = _karte(entities=[{"entity": "calendar.familie_anna"}, {"entity_id": "calendar.x"}])
    assert card_entity_ids(karte) == {"calendar.familie_anna", "calendar.x"}


def test_entities_ohne_liste() -> None:
    assert card_entity_ids(_karte(entities="calendar.familie_anna")) == set()
    assert card_entity_ids(_karte()) == set()


def test_findet_karten_in_unbekannten_behaeltern() -> None:
    config = {
        "views": [
            {
                "cards": [
                    {"type": "conditional", "card": _karte(entities=["calendar.familie_anna"])},
                    {"type": "custom:button-card", "custom_fields": {"x": {"card": _karte()}}},
                ]
            }
        ]
    }
    typen = [karte["type"] for karte in iter_cards(config)]
    assert typen.count(DAYLIGHT_CARD_TYPE) == 2
    assert apply_colors(config, FARBEN) == 1


def test_leere_konfiguration() -> None:
    assert apply_colors({}, FARBEN) == 0
    assert apply_colors(_dashboard(_karte(entities=list(FARBEN))), {}) == 0
    assert apply_names({}, NAMEN) == 0


def test_namen_werden_ergaenzt() -> None:
    karte = _karte(
        entities=["calendar.muell", "calendar.familie_anna", "calendar.familie_ben"],
        calendar_names={"calendar.muell": "Muelltonnen"},
    )

    assert apply_names(_dashboard(karte), NAMEN) == 2
    assert karte["calendar_names"] == {"calendar.muell": "Muelltonnen", **NAMEN}


def test_vorhandener_name_bleibt_stehen() -> None:
    karte = _karte(
        entities=["calendar.familie_anna"], calendar_names={"calendar.familie_anna": "Mama"}
    )

    assert apply_names(_dashboard(karte), NAMEN) == 0
    assert karte["calendar_names"] == {"calendar.familie_anna": "Mama"}


def test_leerer_name_wird_ersetzt() -> None:
    karte = _karte(
        entities=["calendar.familie_anna"], calendar_names={"calendar.familie_anna": " "}
    )
    assert apply_names(_dashboard(karte), NAMEN) == 1
    assert karte["calendar_names"] == {"calendar.familie_anna": "Anna"}


def test_ungueltiges_namensfeld_wird_ersetzt() -> None:
    karte = _karte(entities=["calendar.familie_ben"], calendar_names=["kaputt"])
    assert apply_names(_dashboard(karte), NAMEN) == 1
    assert karte["calendar_names"] == {"calendar.familie_ben": "Ben"}
