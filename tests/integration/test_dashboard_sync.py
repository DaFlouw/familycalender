"""Farb- und Namensabgleich mit Daylight-Calendar-Karten."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceStorage
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.family_calendar.const import CONF_COLOR, DASHBOARD_SYNC_COOLDOWN
from custom_components.family_calendar.domain.colors import rgb_to_hex

from .conftest import PERSONEN, QuellKalender, entity_id_von, neuer_eintrag

MUELL = {"calendar.muell": "#a1a1a1"}


def _dashboard(*entities: str, **felder: Any) -> dict[str, Any]:
    return {
        "views": [
            {
                "type": "sections",
                "sections": [
                    {
                        "type": "grid",
                        "cards": [
                            {
                                "type": "custom:daylight-calendar-card",
                                "entities": ["calendar.muell", *entities],
                                "colors": dict(MUELL),
                                **felder,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _karte(config: dict[str, Any]) -> dict[str, Any]:
    return config["views"][0]["sections"][0]["cards"][0]


@pytest.fixture
async def lovelace(hass: HomeAssistant) -> LovelaceStorage:
    assert await async_setup_component(hass, "lovelace", {})
    dashboard = hass.data[LOVELACE_DATA].dashboards[None]
    assert isinstance(dashboard, LovelaceStorage)
    return dashboard


async def _warte_auf_abgleich(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=DASHBOARD_SYNC_COOLDOWN + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _einrichten(hass: HomeAssistant, *, abgleich: bool) -> MockConfigEntry:
    eintrag = neuer_eintrag(hass, abgleich=abgleich)
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    return eintrag


async def test_farben_und_namen_werden_beim_start_eingetragen(
    hass: HomeAssistant,
    quelle: QuellKalender,
    lovelace: LovelaceStorage,
    freezer: FrozenDateTimeFactory,
) -> None:
    await lovelace.async_save(_dashboard(entity_id_von("Anna"), entity_id_von("Ben")))

    await _einrichten(hass, abgleich=True)
    await _warte_auf_abgleich(hass, freezer)

    karte = _karte(await lovelace.async_load(False))
    assert karte["colors"] == {
        **MUELL,
        entity_id_von("Anna"): rgb_to_hex(PERSONEN[0][2]),
        entity_id_von("Ben"): rgb_to_hex(PERSONEN[1][2]),
    }
    assert karte["calendar_names"] == {entity_id_von("Anna"): "Anna", entity_id_von("Ben"): "Ben"}


async def test_vorhandener_name_bleibt_stehen(
    hass: HomeAssistant,
    quelle: QuellKalender,
    lovelace: LovelaceStorage,
    freezer: FrozenDateTimeFactory,
) -> None:
    await lovelace.async_save(
        _dashboard(entity_id_von("Anna"), calendar_names={entity_id_von("Anna"): "Mama"})
    )

    await _einrichten(hass, abgleich=True)
    await _warte_auf_abgleich(hass, freezer)

    assert _karte(await lovelace.async_load(False))["calendar_names"] == {
        entity_id_von("Anna"): "Mama"
    }


async def test_neue_karte_bekommt_farben(
    hass: HomeAssistant,
    quelle: QuellKalender,
    lovelace: LovelaceStorage,
    freezer: FrozenDateTimeFactory,
) -> None:
    await _einrichten(hass, abgleich=True)
    await _warte_auf_abgleich(hass, freezer)

    await lovelace.async_save(_dashboard(entity_id_von("Carla")))
    await _warte_auf_abgleich(hass, freezer)

    assert _karte(await lovelace.async_load(False))["colors"] == {
        **MUELL,
        entity_id_von("Carla"): rgb_to_hex(PERSONEN[2][2]),
    }


async def test_farbaenderung_erreicht_die_karte(
    hass: HomeAssistant,
    quelle: QuellKalender,
    lovelace: LovelaceStorage,
    freezer: FrozenDateTimeFactory,
) -> None:
    await lovelace.async_save(_dashboard(entity_id_von("Anna")))
    eintrag = await _einrichten(hass, abgleich=True)
    await _warte_auf_abgleich(hass, freezer)

    anna = next(s for s in eintrag.subentries.values() if s.title == "Anna")
    hass.config_entries.async_update_subentry(
        eintrag, anna, data={**anna.data, CONF_COLOR: [10, 20, 30]}
    )
    await _warte_auf_abgleich(hass, freezer)

    assert _karte(await lovelace.async_load(False))["colors"][entity_id_von("Anna")] == "#0a141e"


async def test_ohne_abgleich_bleibt_das_dashboard_unberuehrt(
    hass: HomeAssistant,
    quelle: QuellKalender,
    lovelace: LovelaceStorage,
    freezer: FrozenDateTimeFactory,
) -> None:
    await lovelace.async_save(_dashboard(entity_id_von("Anna")))

    await _einrichten(hass, abgleich=False)
    await _warte_auf_abgleich(hass, freezer)

    karte = _karte(await lovelace.async_load(False))
    assert karte["colors"] == MUELL
    assert "calendar_names" not in karte
