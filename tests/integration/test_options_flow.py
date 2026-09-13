"""Optionen: Quellkalender und Farbabgleich."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.family_calendar.const import CONF_SOURCE, CONF_SYNC_DASHBOARDS

from .conftest import entity_id_von, neuer_eintrag, registry_id


async def test_quelle_wechseln(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    options = hass.config_entries.options
    result = await options.async_init(eingerichtet.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await options.async_configure(
        result["flow_id"],
        {CONF_SOURCE: "calendar.zweite_quelle", CONF_SYNC_DASHBOARDS: True},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    zweite_id = registry_id(hass, "calendar.zweite_quelle")
    assert eingerichtet.options == {CONF_SOURCE: zweite_id, CONF_SYNC_DASHBOARDS: True}
    # Jede weitere Aenderung am Eintrag loeste ein Neuladen mit den alten
    # Optionen aus und verschluckte das fuer die neuen (Issue 8).
    assert eingerichtet.unique_id == registry_id(hass, "calendar.quelle")
    assert eingerichtet.state is ConfigEntryState.LOADED

    # Die zweite Quelle hat keine Termine.
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id_von("Anna"))
    start = dt_util.now()
    assert await entity.async_get_events(hass, start, start + timedelta(days=7)) == []


async def test_ungueltige_quelle(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    options = hass.config_entries.options
    result = await options.async_init(eingerichtet.entry_id)
    result = await options.async_configure(
        result["flow_id"], {CONF_SOURCE: "calendar.gibt_es_nicht", CONF_SYNC_DASHBOARDS: False}
    )
    assert result["errors"] == {CONF_SOURCE: "source_not_found"}


async def test_quelle_eines_anderen_eintrags(
    hass: HomeAssistant, eingerichtet: MockConfigEntry
) -> None:
    neuer_eintrag(hass, quelle="calendar.zweite_quelle")

    options = hass.config_entries.options
    result = await options.async_init(eingerichtet.entry_id)
    result = await options.async_configure(
        result["flow_id"], {CONF_SOURCE: "calendar.zweite_quelle", CONF_SYNC_DASHBOARDS: False}
    )
    assert result["errors"] == {CONF_SOURCE: "already_configured"}
