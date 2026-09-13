"""Personenkalender: Termine, Zustand, Farben, Zwischenspeicher."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.calendar import CalendarEvent
from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.family_calendar.const import CONF_SOURCE, CONF_SYNC_DASHBOARDS, DOMAIN
from custom_components.family_calendar.domain.colors import rgb_to_hex

from .conftest import ERWARTET, PERSONEN, QuellKalender, entity_id_von, personen_subentries


async def test_je_person_ein_kalender(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    for name, buchstabe, farbe in PERSONEN:
        state = hass.states.get(entity_id_von(name))
        assert state is not None, name
        assert state.attributes["letter"] == buchstabe
        assert state.attributes["color"] == rgb_to_hex(farbe)
        assert state.attributes["friendly_name"] == f"Familienkalender {name}"


async def test_farbe_steht_in_den_kalenderoptionen(
    hass: HomeAssistant, eingerichtet: MockConfigEntry
) -> None:
    registry = er.async_get(hass)
    for name, _, farbe in PERSONEN:
        eintrag = registry.async_get(entity_id_von(name))
        assert eintrag is not None
        assert eintrag.options["calendar"]["color"] == rgb_to_hex(farbe)


@pytest.mark.parametrize(("name", "buchstabe"), [(n, b) for n, b, _ in PERSONEN])
async def test_termine_je_person_ueber_die_http_api(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    eingerichtet: MockConfigEntry,
    name: str,
    buchstabe: str,
) -> None:
    """Genau so fragt eine Kalenderkarte die Termine ab."""
    client = await hass_client()
    start = dt_util.now()
    response = await client.get(
        f"/api/calendars/{entity_id_von(name)}",
        params={"start": start.isoformat(), "end": (start + timedelta(days=7)).isoformat()},
    )
    assert response.status == 200
    assert {termin["summary"] for termin in await response.json()} == ERWARTET[buchstabe]


async def test_termine_bleiben_unveraendert(
    hass: HomeAssistant, eingerichtet: MockConfigEntry, quelle: QuellKalender
) -> None:
    """Gleiche Titel, Zeiten und Orte: nur so fasst die Karte sie zusammen."""
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id_von("Anna"))
    start = dt_util.now()
    termine = await entity.async_get_events(hass, start, start + timedelta(days=7))
    zahnarzt = next(t for t in termine if t.summary == "A Zahnarzt")
    original = next(t for t in quelle.termine if t.summary == "A Zahnarzt")
    assert zahnarzt == original


async def test_naechster_termin_je_person(
    hass: HomeAssistant, eingerichtet: MockConfigEntry
) -> None:
    erwartet = {"Anna": "A Zahnarzt", "Ben": "bc Schwimmen", "Carla": "bc Schwimmen"}
    erwartet["Dora"] = "DCBA Ausflug"
    for name, titel in erwartet.items():
        state = hass.states.get(entity_id_von(name))
        assert state.state == "off"
        assert state.attributes["message"] == titel


async def test_laufender_termin_schaltet_ein(
    hass: HomeAssistant, eingerichtet: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    freezer.tick(timedelta(hours=1, minutes=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id_von("Anna")).state == "on"
    assert hass.states.get(entity_id_von("Ben")).state == "off"


async def test_gleichzeitige_abfragen_gehen_einmal_an_die_quelle(
    hass: HomeAssistant, eingerichtet: MockConfigEntry, quelle: QuellKalender
) -> None:
    komponente = hass.data[DATA_COMPONENT]
    entities = [komponente.get_entity(entity_id_von(name)) for name, _, _ in PERSONEN]
    start = dt_util.now()
    ende = start + timedelta(days=7)

    vorher = quelle.abfragen
    await asyncio.gather(*(entity.async_get_events(hass, start, ende) for entity in entities))
    assert quelle.abfragen - vorher == 1


async def test_aenderung_der_quelle_wird_uebernommen(
    hass: HomeAssistant,
    eingerichtet: MockConfigEntry,
    quelle: QuellKalender,
    freezer: FrozenDateTimeFactory,
) -> None:
    start = dt_util.now() + timedelta(minutes=30)
    quelle.termine.append(
        CalendarEvent(start=start, end=start + timedelta(minutes=15), summary="A Frueher Termin")
    )
    quelle.async_write_ha_state()
    await hass.async_block_till_done()

    freezer.tick(timedelta(seconds=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id_von("Anna")).attributes["message"] == "A Frueher Termin"


async def test_fehlende_quelle_fuehrt_zu_neuem_versuch(
    hass: HomeAssistant, quelle: QuellKalender
) -> None:
    eintrag = MockConfigEntry(
        domain=DOMAIN,
        options={CONF_SOURCE: "calendar.gibt_es_nicht", CONF_SYNC_DASHBOARDS: False},
        subentries_data=personen_subentries(),
    )
    eintrag.add_to_hass(hass)

    await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    assert eintrag.state is ConfigEntryState.SETUP_RETRY


async def test_person_entfernen(hass: HomeAssistant, eingerichtet: MockConfigEntry) -> None:
    dora = next(s for s in eingerichtet.subentries.values() if s.title == "Dora")

    assert hass.config_entries.async_remove_subentry(eingerichtet, dora.subentry_id)
    await hass.async_block_till_done()

    assert er.async_get(hass).async_get(entity_id_von("Dora")) is None
    assert hass.states.get(entity_id_von("Dora")) is None

    # D ist kein bekanntes Kuerzel mehr: der Termin betrifft jetzt alle.
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id_von("Anna"))
    start = dt_util.now()
    titel = {t.summary for t in await entity.async_get_events(hass, start, start + timedelta(7))}
    assert "D Klassenfahrt" in titel
