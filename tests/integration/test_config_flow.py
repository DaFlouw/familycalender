"""Einrichtung ueber den Config Flow."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.family_calendar.const import (
    CONF_COLOR,
    CONF_LETTER,
    CONF_SOURCE,
    CONF_SYNC_DASHBOARDS,
    DOMAIN,
    SUBENTRY_PERSON,
)
from custom_components.family_calendar.domain.colors import PALETTE

from .conftest import QuellKalender, entity_id_von, registry_id


def vorgabe(result: FlowResult, feld: str) -> Any:
    for schluessel in result["data_schema"].schema:
        if schluessel == feld:
            return schluessel.default()
    raise KeyError(feld)


async def _starte(hass: HomeAssistant) -> FlowResult:
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})


async def test_einrichtung_mit_zwei_personen(hass: HomeAssistant, quelle: QuellKalender) -> None:
    flow = hass.config_entries.flow
    result = await _starte(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await flow.async_configure(
        result["flow_id"], {CONF_NAME: "Familie", CONF_SOURCE: "calendar.quelle"}
    )
    assert result["step_id"] == "person"
    assert vorgabe(result, CONF_COLOR) == list(PALETTE[0])

    result = await flow.async_configure(
        result["flow_id"], {CONF_NAME: "Anna", CONF_LETTER: "a", CONF_COLOR: [1, 2, 3]}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "more"

    result = await flow.async_configure(result["flow_id"], {"next_step_id": "person"})
    assert result["step_id"] == "person"
    assert vorgabe(result, CONF_COLOR) == list(PALETTE[0])

    result = await flow.async_configure(
        result["flow_id"], {CONF_NAME: "Ben", CONF_LETTER: "A", CONF_COLOR: [4, 5, 6]}
    )
    assert result["errors"] == {CONF_LETTER: "letter_taken"}

    result = await flow.async_configure(
        result["flow_id"], {CONF_NAME: " Ben ", CONF_LETTER: "b", CONF_COLOR: [4, 5, 6]}
    )
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "finish"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Familie"
    await hass.async_block_till_done()

    eintrag = result["result"]
    quelle_id = registry_id(hass, "calendar.quelle")
    assert eintrag.unique_id == quelle_id
    assert eintrag.options == {CONF_SOURCE: quelle_id, CONF_SYNC_DASHBOARDS: True}

    personen = {s.title: s for s in eintrag.subentries.values()}
    assert set(personen) == {"Anna", "Ben"}
    assert personen["Anna"].subentry_type == SUBENTRY_PERSON
    assert personen["Anna"].unique_id == "A"
    assert dict(personen["Ben"].data) == {CONF_LETTER: "B", CONF_COLOR: [4, 5, 6]}

    assert hass.states.get(entity_id_von("Anna", "familie")) is not None
    assert hass.states.get(entity_id_von("Ben", "familie")) is not None


async def test_quelle_gibt_es_nicht(hass: HomeAssistant, quelle: QuellKalender) -> None:
    result = await _starte(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Familie", CONF_SOURCE: "calendar.gibt_es_nicht"}
    )
    assert result["errors"] == {CONF_SOURCE: "source_not_found"}


async def test_personenkalender_als_quelle(
    hass: HomeAssistant, eingerichtet: MockConfigEntry
) -> None:
    result = await _starte(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Familie", CONF_SOURCE: entity_id_von("Anna")}
    )
    assert result["errors"] == {CONF_SOURCE: "source_is_family_calendar"}


async def test_quelle_bereits_eingerichtet(
    hass: HomeAssistant, eingerichtet: MockConfigEntry
) -> None:
    result = await _starte(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Nochmal", CONF_SOURCE: "calendar.quelle"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_ungueltige_person(hass: HomeAssistant, quelle: QuellKalender) -> None:
    result = await _starte(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Familie", CONF_SOURCE: "calendar.quelle"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "  ", CONF_LETTER: "AB", CONF_COLOR: [1, 2, 3]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "name_required", CONF_LETTER: "invalid_letter"}
