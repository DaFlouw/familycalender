"""Laden, Entladen, Migration und Umbenennen der Quelle."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.family_calendar.const import CONF_SOURCE, CONF_SYNC_DASHBOARDS, DOMAIN

from .conftest import (
    ERWARTET,
    PERSONEN,
    QuellKalender,
    entity_id_von,
    neuer_eintrag,
    personen_subentries,
)


async def test_entladen(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(eingerichtet.entry_id)
    await hass.async_block_till_done()

    assert eingerichtet.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(entity_id_von("Anna")).state == STATE_UNAVAILABLE


async def test_neuere_version_wird_abgelehnt(hass: HomeAssistant, quelle: QuellKalender) -> None:
    eintrag = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        options={CONF_SOURCE: "calendar.quelle", CONF_SYNC_DASHBOARDS: False},
        subentries_data=personen_subentries(),
    )
    eintrag.add_to_hass(hass)

    await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    assert eintrag.state is ConfigEntryState.MIGRATION_ERROR


async def test_quelle_ohne_registry_eintrag(hass: HomeAssistant, quelle: QuellKalender) -> None:
    """Auch eine Entity-ID statt einer Registry-ID wird aufgeloest."""
    eintrag = MockConfigEntry(
        domain=DOMAIN,
        title="Familienkalender",
        options={CONF_SOURCE: "calendar.quelle", CONF_SYNC_DASHBOARDS: False},
        subentries_data=personen_subentries(),
    )
    eintrag.add_to_hass(hass)
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()

    assert eintrag.state is ConfigEntryState.LOADED
    assert hass.states.get(entity_id_von("Anna")).attributes["message"] == "A Zahnarzt"


async def test_ein_geraet_je_person(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    """Ein gemeinsames Geraet liesse nur den zuletzt angelegten Kalender uebrig."""
    geraete = dr.async_get(hass)
    namen = sorted(
        g.name for g in dr.async_entries_for_config_entry(geraete, eingerichtet.entry_id)
    )
    assert namen == [f"Familienkalender {name}" for name, _, _ in PERSONEN]

    entities = er.async_get(hass)
    for name, _, _ in PERSONEN:
        eintrag = entities.async_get(entity_id_von(name))
        assert eintrag is not None, name
        assert geraete.async_get(eintrag.device_id).name == f"Familienkalender {name}"


async def test_altes_gemeinsames_geraet_wird_geloest(
    hass: HomeAssistant, quelle: QuellKalender
) -> None:
    eintrag = neuer_eintrag(hass)
    alt = dr.async_get(hass).async_get_or_create(
        config_entry_id=eintrag.entry_id,
        identifiers={(DOMAIN, eintrag.entry_id)},
        name="Familienkalender",
    )

    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()

    assert dr.async_get(hass).async_get(alt.id) is None
    assert hass.states.get(entity_id_von("Anna")) is not None


async def test_umbenannte_quelle(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    er.async_get(hass).async_update_entity("calendar.quelle", new_entity_id="calendar.neu")
    await hass.async_block_till_done()

    assert eingerichtet.state is ConfigEntryState.LOADED
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id_von("Anna"))
    start = dt_util.now()
    termine = await entity.async_get_events(hass, start, start + timedelta(days=7))
    assert {t.summary for t in termine} == ERWARTET["A"]


async def test_entfernte_quelle(
    hass: HomeAssistant, eingerichtet: MockConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Ohne Quelle wartet der Eintrag auf einen neuen Versuch, statt abzustuerzen."""
    er.async_get(hass).async_remove("calendar.quelle")
    await hass.async_block_till_done()

    assert eingerichtet.state is ConfigEntryState.SETUP_RETRY
    assert "wurde entfernt" in caplog.text
