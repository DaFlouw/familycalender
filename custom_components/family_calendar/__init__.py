"""Familienkalender: teilt einen Kalender anhand von Kuerzeln in Personenkalender auf.

Ein Eintrag gehoert zu genau einem Quellkalender. Jede Person ist ein
Untereintrag und bekommt einen eigenen Kalender, der nur ihre Termine zeigt.
Die Termine selbst bleiben unveraendert; eine Kalenderkarte, die doppelte Termine
zusammenfasst, zeigt Termine mehrerer Personen deshalb gestreift an.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.helper_integration import async_handle_source_entity_changes

from .const import (
    CONF_SOURCE,
    CONF_SYNC_DASHBOARDS,
    CONFIG_ENTRY_VERSION,
    DEFAULT_SYNC_DASHBOARDS,
    DOMAIN,
)
from .coordinator import (
    FamilyCalendarCoordinator,
    FamilyCalendarEntry,
    FamilyCalendarRuntime,
    SourceCalendar,
)
from .dashboard_sync import DashboardColorSync

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: FamilyCalendarEntry) -> bool:
    """Richtet die Personenkalender eines Quellkalenders ein."""
    source = SourceCalendar(hass, entry.options[CONF_SOURCE])
    coordinator = FamilyCalendarCoordinator(hass, entry, source)

    # Laedt der Quellkalender spaeter als diese Integration -- etwa weil seine
    # Integration erst eine Verbindung aufbauen muss --, wirft die erste
    # Aktualisierung ConfigEntryNotReady, und Home Assistant versucht es erneut.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FamilyCalendarRuntime(source=source, coordinator=coordinator)
    entry.async_on_unload(coordinator.async_track_source())
    entry.async_on_unload(_async_follow_source(hass, entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_remove_stale_devices(hass, entry)

    if entry.options.get(CONF_SYNC_DASHBOARDS, DEFAULT_SYNC_DASHBOARDS):
        entry.async_on_unload(DashboardColorSync(hass, entry).async_start())

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FamilyCalendarEntry) -> bool:
    """Entfernt die Personenkalender."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Hebt aeltere Konfigurationseintraege auf die aktuelle Version.

    Solange nur Version 1 existiert, ist nichts zu tun. Ein Eintrag aus einer
    *neueren* Version wird abgelehnt, statt seine Daten zu beschaedigen.
    """
    if entry.version > CONFIG_ENTRY_VERSION:
        _LOGGER.error(
            "Konfigurationseintrag hat Version %s, unterstuetzt wird hoechstens %s. "
            "Vermutlich wurde die Integration heruntergestuft",
            entry.version,
            CONFIG_ENTRY_VERSION,
        )
        return False
    return True


@callback
def _async_remove_stale_devices(hass: HomeAssistant, entry: FamilyCalendarEntry) -> None:
    """Entfernt Geraete des Eintrags, die zu keiner Person gehoeren.

    Betrifft das gemeinsame Geraet aus der ersten Vorabversion. Geraete entfernter
    Personen raeumt Home Assistant beim Entfernen des Untereintrags selbst ab.
    Ein Geraet gehoert genau einem Eintrag; es wird deshalb ganz entfernt.
    """
    registry = dr.async_get(hass)
    wanted = {(DOMAIN, subentry_id) for subentry_id in entry.subentries}
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if not device.identifiers & wanted:
            registry.async_remove_device(device.id)


@callback
def _async_follow_source(hass: HomeAssistant, entry: FamilyCalendarEntry) -> CALLBACK_TYPE:
    """Folgt dem Quellkalender, wenn er umbenannt oder entfernt wird."""

    @callback
    def set_source(entity_id_or_uuid: str) -> None:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_SOURCE: entity_id_or_uuid}
        )

    async def source_removed() -> None:
        _LOGGER.warning(
            "Der Quellkalender von %s wurde entfernt; die Personenkalender sind "
            "nicht verfuegbar, bis unter Konfigurieren ein neuer gewaehlt ist",
            entry.title,
        )
        await hass.config_entries.async_reload(entry.entry_id)

    return async_handle_source_entity_changes(
        hass,
        helper_config_entry_id=entry.entry_id,
        set_source_entity_id_or_uuid=set_source,
        source_device_id=None,
        source_entity_id_or_uuid=entry.options[CONF_SOURCE],
        source_entity_removed=source_removed,
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Laedt neu, wenn sich Optionen oder Personen geaendert haben."""
    await hass.config_entries.async_reload(entry.entry_id)


__all__ = ["DOMAIN", "FamilyCalendarEntry", "FamilyCalendarRuntime"]
