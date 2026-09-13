"""Laden, Entladen, Migration und Umbenennen der Quelle."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.family_calendar.const import CONF_SOURCE, CONF_SYNC_DASHBOARDS, DOMAIN

from .conftest import ERWARTET, QuellKalender, entity_id_von, personen_subentries


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


async def test_umbenannte_quelle(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    er.async_get(hass).async_update_entity("calendar.quelle", new_entity_id="calendar.neu")
    await hass.async_block_till_done()

    assert eingerichtet.state is ConfigEntryState.LOADED
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id_von("Anna"))
    start = dt_util.now()
    termine = await entity.async_get_events(hass, start, start + timedelta(days=7))
    assert {t.summary for t in termine} == ERWARTET["A"]
