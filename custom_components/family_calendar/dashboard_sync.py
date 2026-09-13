"""Traegt die Farben der Personen in Daylight-Calendar-Karten ein.

Die Karte liest Kalenderfarben nur aus ihrer eigenen Konfiguration. Ist der
Abgleich eingeschaltet, schreibt die Integration die Farben ihrer Kalender in
jede Karte, die sie anzeigt -- beim Start, nach jeder Aenderung an Personen und
nach jeder gespeicherten Dashboard-Aenderung, damit auch neu angelegte Karten
ihre Farben bekommen.

Beruehrt werden ausschliesslich Dashboards im Speichermodus und darin nur das
``colors``-Feld von Daylight-Karten. YAML-Dashboards bleiben unangetastet.
"""

from __future__ import annotations

import asyncio
import copy
import logging

from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE, ConfigNotFound
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_LOVELACE_UPDATED
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.start import async_at_started

from .const import CONF_COLOR, DASHBOARD_SYNC_COOLDOWN, SUBENTRY_PERSON
from .coordinator import FamilyCalendarEntry
from .domain.cards import apply_colors
from .domain.colors import rgb_to_hex

_LOGGER = logging.getLogger(__name__)


class DashboardColorSync:
    """Farbabgleich eines Eintrags mit den Dashboards."""

    def __init__(self, hass: HomeAssistant, entry: FamilyCalendarEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._lock = asyncio.Lock()
        self._debouncer: Debouncer[object] = Debouncer(
            hass,
            _LOGGER,
            cooldown=DASHBOARD_SYNC_COOLDOWN,
            immediate=False,
            function=self.async_sync,
        )

    @callback
    def async_start(self) -> CALLBACK_TYPE:
        """Beginnt den Abgleich und liefert die Funktion zum Beenden."""

        @callback
        def _schedule(*_: object) -> None:
            self._debouncer.async_schedule_call()

        @callback
        def _cancel(_: Event) -> None:
            self._debouncer.async_cancel()

        unsubscribers = [
            self._hass.bus.async_listen(EVENT_LOVELACE_UPDATED, _schedule),
            self._hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, _cancel),
            async_at_started(self._hass, _schedule),
        ]

        @callback
        def stop() -> None:
            for unsubscribe in unsubscribers:
                unsubscribe()
            self._debouncer.async_shutdown()

        return stop

    @callback
    def colors(self) -> dict[str, str]:
        """Die Farbe je Entity-ID der Personenkalender dieses Eintrags."""
        registry = er.async_get(self._hass)
        result: dict[str, str] = {}
        for registry_entry in er.async_entries_for_config_entry(registry, self._entry.entry_id):
            subentry = self._entry.subentries.get(registry_entry.config_subentry_id or "")
            if subentry is None or subentry.subentry_type != SUBENTRY_PERSON:
                continue
            result[registry_entry.entity_id] = rgb_to_hex(subentry.data[CONF_COLOR])
        return result

    async def async_sync(self) -> int:
        """Gleicht alle Dashboards ab und liefert die Zahl geaenderter Farben."""
        async with self._lock:
            colors = self.colors()
            lovelace = self._hass.data.get(LOVELACE_DATA)
            if not colors or lovelace is None:
                return 0

            total = 0
            for url_path, dashboard in list(lovelace.dashboards.items()):
                if dashboard.mode != MODE_STORAGE:
                    continue
                try:
                    current = await dashboard.async_load(False)
                except ConfigNotFound:
                    continue

                # Die geladene Konfiguration ist der Cache des Dashboards selbst;
                # veraendert wird deshalb nur eine Kopie.
                updated = copy.deepcopy(current)
                if not (changed := apply_colors(updated, colors)):
                    continue

                try:
                    await dashboard.async_save(updated)
                except HomeAssistantError as err:
                    _LOGGER.warning("Dashboard %s nicht gespeichert: %s", url_path, err)
                    continue

                total += changed
                _LOGGER.info(
                    "%s Farbe(n) im Dashboard %s eingetragen", changed, url_path or "lovelace"
                )
            return total
