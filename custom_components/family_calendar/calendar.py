"""Ein Kalender je Person."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_COLOR, CONF_LETTER, DEFAULT_TITLE, DOMAIN, SUBENTRY_PERSON
from .coordinator import FamilyCalendarCoordinator, FamilyCalendarEntry
from .domain.colors import rgb_to_hex
from .domain.prefix import affected_letters, normalize_letter

# Die Entities lesen nur aus dem Coordinator; es gibt nichts zu drosseln.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FamilyCalendarEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Legt fuer jede Person einen Kalender an."""
    coordinator = entry.runtime_data.coordinator
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_PERSON:
            continue
        async_add_entities(
            [PersonCalendarEntity(coordinator, entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class PersonCalendarEntity(CoordinatorEntity[FamilyCalendarCoordinator], CalendarEntity):
    """Zeigt die Termine des Quellkalenders, die eine Person betreffen."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FamilyCalendarCoordinator,
        entry: FamilyCalendarEntry,
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(coordinator)
        self.letter = normalize_letter(subentry.data[CONF_LETTER])
        self.color = rgb_to_hex(subentry.data[CONF_COLOR])

        self._attr_name = subentry.title
        self._attr_unique_id = f"{entry.entry_id}_{subentry.subentry_id}"
        self._attr_initial_color = self.color
        self._attr_extra_state_attributes = {"letter": self.letter, "color": self.color}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="DaFlouw",
            model=DEFAULT_TITLE,
        )

    def _concerns(self, event: CalendarEvent) -> bool:
        return self.letter in affected_letters(event.summary, self.coordinator.letters)

    @property
    def event(self) -> CalendarEvent | None:
        """Der laufende oder naechste Termin dieser Person."""
        now = dt_util.now()
        for event in self.coordinator.data or ():
            if event.end_datetime_local > now and self._concerns(event):
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Termine dieser Person im Zeitraum."""
        events = await self.coordinator.source.async_get_events(start_date, end_date)
        return [event for event in events if self._concerns(event)]

    async def async_added_to_hass(self) -> None:
        """Uebernimmt die Farbe auch in die Kalenderoptionen der Entity.

        Home Assistant setzt ``initial_color`` nur beim ersten Anlegen. Damit eine
        spaeter geaenderte Farbe auch im Kalender-Panel ankommt, wird sie hier
        nachgezogen; die Integration bleibt die fuehrende Quelle.
        """
        await super().async_added_to_hass()
        registry = er.async_get(self.hass)
        if (registry_entry := registry.async_get(self.entity_id)) is None:
            return
        options = dict(registry_entry.options.get(CALENDAR_DOMAIN, {}))
        if options.get("color") != self.color:
            options["color"] = self.color
            registry.async_update_entity_options(self.entity_id, CALENDAR_DOMAIN, options)
