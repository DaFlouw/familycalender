"""Zugriff auf den Quellkalender und Bestimmung der naechsten Termine."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.calendar.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LETTER,
    DOMAIN,
    LOOKAHEAD,
    SOURCE_CACHE_TTL,
    SUBENTRY_PERSON,
    UPDATE_INTERVAL,
)
from .domain.prefix import normalize_letters

_LOGGER = logging.getLogger(__name__)


class SourceUnavailableError(HomeAssistantError):
    """Der Quellkalender ist nicht vorhanden."""


class SourceCalendar:
    """Liest Termine aus dem Quellkalender.

    Die Kennung ist bevorzugt die Registry-ID der Entity; sie uebersteht ein
    Umbenennen. Kalender ohne Registry-Eintrag werden ueber ihre Entity-ID gefuehrt.

    Abfragen fuer denselben Zeitraum werden kurz zwischengespeichert: Eine
    Kalenderkarte fragt alle Personenkalender gleichzeitig ab, der Quellkalender
    -- oft ein entfernter Dienst -- soll dafuer nur einmal gefragt werden.
    """

    def __init__(self, hass: HomeAssistant, entity_id_or_uuid: str) -> None:
        self._hass = hass
        self._entity_id_or_uuid = entity_id_or_uuid
        self._cache: dict[tuple[datetime, datetime], tuple[float, list[CalendarEvent]]] = {}
        self._lock = asyncio.Lock()

    @property
    def entity_id(self) -> str | None:
        """Aktuelle Entity-ID des Quellkalenders, sofern er existiert."""
        return er.async_resolve_entity_id(er.async_get(self._hass), self._entity_id_or_uuid)

    def _entity(self) -> CalendarEntity:
        entity_id = self.entity_id
        component = self._hass.data.get(DATA_COMPONENT)
        entity = component.get_entity(entity_id) if component is not None and entity_id else None
        if not isinstance(entity, CalendarEntity):
            raise SourceUnavailableError(
                f"Quellkalender {entity_id or self._entity_id_or_uuid} ist nicht verfuegbar"
            )
        return entity

    @callback
    def invalidate(self) -> None:
        """Verwirft zwischengespeicherte Abfragen."""
        self._cache.clear()

    async def async_get_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Termine im Zeitraum, unveraendert aus dem Quellkalender."""
        key = (start, end)
        async with self._lock:
            now = time.monotonic()
            ttl = SOURCE_CACHE_TTL.total_seconds()
            self._cache = {k: v for k, v in self._cache.items() if now - v[0] < ttl}
            if (cached := self._cache.get(key)) is not None:
                return cached[1]

            events = await self._entity().async_get_events(self._hass, start, end)
            self._cache[key] = (time.monotonic(), events)
            return events


@dataclass
class FamilyCalendarRuntime:
    """Laufzeitdaten eines Eintrags."""

    source: SourceCalendar
    coordinator: FamilyCalendarCoordinator


type FamilyCalendarEntry = ConfigEntry[FamilyCalendarRuntime]


class FamilyCalendarCoordinator(DataUpdateCoordinator[list[CalendarEvent]]):
    """Haelt die kommenden Termine fuer den Zustand der Personenkalender bereit.

    Die Terminlisten fuer Karten und Aktionen fragen den Quellkalender direkt ab;
    der Coordinator liefert nur, was die Entities fuer ``event`` brauchen.
    """

    config_entry: FamilyCalendarEntry

    def __init__(
        self, hass: HomeAssistant, entry: FamilyCalendarEntry, source: SourceCalendar
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=UPDATE_INTERVAL,
        )
        self.source = source
        self.letters = normalize_letters(
            subentry.data[CONF_LETTER]
            for subentry in entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_PERSON
        )

    async def _async_update_data(self) -> list[CalendarEvent]:
        now = dt_util.now()
        try:
            events = await self.source.async_get_events(now, now + LOOKAHEAD)
        except HomeAssistantError as err:
            raise UpdateFailed(str(err)) from err
        return sorted(events, key=lambda event: event.start_datetime_local)

    @callback
    def async_track_source(self) -> CALLBACK_TYPE:
        """Aktualisiert, sobald sich der Zustand des Quellkalenders aendert."""
        entity_id = self.source.entity_id
        if entity_id is None:
            return lambda: None

        @callback
        def _source_changed(event: Event[EventStateChangedData]) -> None:
            self.source.invalidate()
            self.hass.async_create_task(self.async_request_refresh())

        return async_track_state_change_event(self.hass, entity_id, _source_changed)
