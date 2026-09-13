"""Personen hinzufuegen und bearbeiten."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.family_calendar.const import CONF_COLOR, CONF_LETTER, SUBENTRY_PERSON
from custom_components.family_calendar.domain.colors import PALETTE

from .conftest import entity_id_von
from .test_config_flow import vorgabe


async def test_person_hinzufuegen(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    subentries = hass.config_entries.subentries
    result = await subentries.async_init(
        (eingerichtet.entry_id, SUBENTRY_PERSON), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    # Die vier Personen haben die ersten vier Farben der Palette.
    assert vorgabe(result, CONF_COLOR) == list(PALETTE[4])

    result = await subentries.async_configure(
        result["flow_id"], {CONF_NAME: "Emil", CONF_LETTER: "e", CONF_COLOR: [1, 2, 3]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    state = hass.states.get(entity_id_von("Emil"))
    assert state is not None
    assert state.attributes["letter"] == "E"
    assert state.attributes["color"] == "#010203"


async def test_vergebenes_kuerzel(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    subentries = hass.config_entries.subentries
    result = await subentries.async_init(
        (eingerichtet.entry_id, SUBENTRY_PERSON), context={"source": SOURCE_USER}
    )
    result = await subentries.async_configure(
        result["flow_id"], {CONF_NAME: "Andrea", CONF_LETTER: "a", CONF_COLOR: [1, 2, 3]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_LETTER: "letter_taken"}


async def test_person_bearbeiten(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    anna = next(s for s in eingerichtet.subentries.values() if s.title == "Anna")
    subentries = hass.config_entries.subentries
    result = await subentries.async_init(
        (eingerichtet.entry_id, SUBENTRY_PERSON),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": anna.subentry_id},
    )
    assert result["type"] is FlowResultType.FORM
    assert vorgabe(result, CONF_NAME) == "Anna"
    assert vorgabe(result, CONF_LETTER) == "A"

    # Das eigene Kuerzel zu behalten ist kein Konflikt.
    result = await subentries.async_configure(
        result["flow_id"], {CONF_NAME: "Anna", CONF_LETTER: "a", CONF_COLOR: [10, 20, 30]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    assert hass.states.get(entity_id_von("Anna")).attributes["color"] == "#0a141e"
    eintrag = er.async_get(hass).async_get(entity_id_von("Anna"))
    assert eintrag.options["calendar"]["color"] == "#0a141e"


async def test_bearbeiten_auf_fremdes_kuerzel(
    hass: HomeAssistant, eingerichtet: MockConfigEntry
) -> None:
    anna = next(s for s in eingerichtet.subentries.values() if s.title == "Anna")
    subentries = hass.config_entries.subentries
    result = await subentries.async_init(
        (eingerichtet.entry_id, SUBENTRY_PERSON),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": anna.subentry_id},
    )
    result = await subentries.async_configure(
        result["flow_id"], {CONF_NAME: "Anna", CONF_LETTER: "B", CONF_COLOR: [10, 20, 30]}
    )
    assert result["errors"] == {CONF_LETTER: "letter_taken"}
