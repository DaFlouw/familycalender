"""Einrichtung, Optionen und Personen des Familienkalenders.

Die Einrichtung waehlt den Quellkalender und legt die ersten Personen an. Jede
Person ist ein Untereintrag; weitere lassen sich spaeter an der Integration
hinzufuegen, bearbeiten und entfernen.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    ColorRGBSelector,
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
)

from .const import (
    CONF_COLOR,
    CONF_LETTER,
    CONF_SOURCE,
    CONF_SYNC_DASHBOARDS,
    CONFIG_ENTRY_VERSION,
    DEFAULT_SYNC_DASHBOARDS,
    DEFAULT_TITLE,
    DOMAIN,
    SUBENTRY_PERSON,
)
from .domain.colors import suggest_color, to_rgb
from .domain.prefix import InvalidLetterError, normalize_letter


class FamilyCalendarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Waehlt den Quellkalender und legt die ersten Personen an."""

    VERSION = CONFIG_ENTRY_VERSION

    def __init__(self) -> None:
        self._title = DEFAULT_TITLE
        self._source = ""
        self._persons: list[ConfigSubentryData] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            source, error = validate_source(self.hass, user_input[CONF_SOURCE])
            if error:
                errors[CONF_SOURCE] = error
            else:
                await self.async_set_unique_id(source)
                self._abort_if_unique_id_configured()
                self._title = str(user_input.get(CONF_NAME, "")).strip() or DEFAULT_TITLE
                self._source = source
                return await self.async_step_person()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_TITLE): TextSelector(),
                vol.Required(CONF_SOURCE): _source_selector(),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_person(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults: Mapping[str, Any] = {
            CONF_COLOR: suggest_color(person["data"][CONF_COLOR] for person in self._persons)
        }
        if user_input is not None:
            taken = {person["data"][CONF_LETTER] for person in self._persons}
            person, errors = validate_person(user_input, taken)
            if not errors:
                self._persons.append(
                    ConfigSubentryData(
                        data={CONF_LETTER: person[CONF_LETTER], CONF_COLOR: person[CONF_COLOR]},
                        subentry_type=SUBENTRY_PERSON,
                        title=person[CONF_NAME],
                        unique_id=person[CONF_LETTER],
                    )
                )
                return await self.async_step_more()
            defaults = user_input

        return self.async_show_form(
            step_id="person",
            data_schema=person_schema(defaults),
            errors=errors,
            description_placeholders={"persons": _describe(self._persons)},
        )

    async def async_step_more(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="more",
            menu_options=["person", "finish"],
            description_placeholders={"persons": _describe(self._persons)},
        )

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_create_entry(
            title=self._title,
            data={},
            options={CONF_SOURCE: self._source, CONF_SYNC_DASHBOARDS: DEFAULT_SYNC_DASHBOARDS},
            subentries=self._persons,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FamilyCalendarOptionsFlow:
        return FamilyCalendarOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_PERSON: PersonSubentryFlow}


class FamilyCalendarOptionsFlow(OptionsFlow):
    """Quellkalender wechseln und den Farbabgleich schalten."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}

        if user_input is not None:
            source, error = validate_source(self.hass, user_input[CONF_SOURCE])
            if error is None and any(
                other.entry_id != entry.entry_id and other.unique_id == source
                for other in self.hass.config_entries.async_entries(DOMAIN)
            ):
                error = "already_configured"
            if error:
                errors[CONF_SOURCE] = error
            else:
                if entry.unique_id != source:
                    self.hass.config_entries.async_update_entry(entry, unique_id=source)
                return self.async_create_entry(
                    data={
                        CONF_SOURCE: source,
                        CONF_SYNC_DASHBOARDS: bool(user_input[CONF_SYNC_DASHBOARDS]),
                    }
                )

        current = er.async_resolve_entity_id(
            er.async_get(self.hass), entry.options.get(CONF_SOURCE, "")
        )
        suggested = user_input or {
            CONF_SOURCE: current,
            CONF_SYNC_DASHBOARDS: entry.options.get(CONF_SYNC_DASHBOARDS, DEFAULT_SYNC_DASHBOARDS),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE): _source_selector(),
                vol.Required(CONF_SYNC_DASHBOARDS): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )


class PersonSubentryFlow(ConfigSubentryFlow):
    """Legt eine Person an oder bearbeitet sie."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        return await self._async_step_person("user", None, user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_step_person(
            "reconfigure", self._get_reconfigure_subentry(), user_input
        )

    async def _async_step_person(
        self,
        step_id: str,
        subentry: ConfigSubentry | None,
        user_input: dict[str, Any] | None,
    ) -> SubentryFlowResult:
        entry = self._get_entry()
        others = [
            other
            for other in entry.subentries.values()
            if other.subentry_type == SUBENTRY_PERSON
            and (subentry is None or other.subentry_id != subentry.subentry_id)
        ]
        errors: dict[str, str] = {}

        if user_input is not None:
            person, errors = validate_person(user_input, {o.data[CONF_LETTER] for o in others})
            if not errors:
                data = {CONF_LETTER: person[CONF_LETTER], CONF_COLOR: person[CONF_COLOR]}
                if subentry is None:
                    return self.async_create_entry(
                        title=person[CONF_NAME], data=data, unique_id=person[CONF_LETTER]
                    )
                return self.async_update_and_abort(
                    entry,
                    subentry,
                    title=person[CONF_NAME],
                    data=data,
                    unique_id=person[CONF_LETTER],
                )
            defaults: Mapping[str, Any] = user_input
        elif subentry is not None:
            defaults = {CONF_NAME: subentry.title, **subentry.data}
        else:
            defaults = {CONF_COLOR: suggest_color(other.data[CONF_COLOR] for other in others)}

        return self.async_show_form(
            step_id=step_id, data_schema=person_schema(defaults), errors=errors
        )


def validate_source(hass: HomeAssistant, entity_id: str) -> tuple[str, str | None]:
    """Prueft den gewaehlten Quellkalender.

    Liefert die zu speichernde Kennung -- die Registry-ID, weil sie ein Umbenennen
    der Entity uebersteht, sonst die Entity-ID -- oder einen Fehlerschluessel.
    """
    registry_entry = er.async_get(hass).async_get(entity_id)
    if not entity_id.startswith(f"{CALENDAR_DOMAIN}.") or (
        registry_entry is None and hass.states.get(entity_id) is None
    ):
        return "", "source_not_found"
    if registry_entry is None:
        return entity_id, None
    if registry_entry.platform == DOMAIN:
        return "", "source_is_family_calendar"
    return registry_entry.id, None


def validate_person(
    user_input: Mapping[str, Any], taken_letters: Iterable[str]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Prueft Name, Kuerzel und Farbe einer Person."""
    errors: dict[str, str] = {}

    name = str(user_input.get(CONF_NAME, "")).strip()
    if not name:
        errors[CONF_NAME] = "name_required"

    letter = ""
    try:
        letter = normalize_letter(str(user_input.get(CONF_LETTER, "")))
    except InvalidLetterError:
        errors[CONF_LETTER] = "invalid_letter"
    else:
        if letter in set(taken_letters):
            errors[CONF_LETTER] = "letter_taken"

    color = list(to_rgb(user_input[CONF_COLOR]))
    return {CONF_NAME: name, CONF_LETTER: letter, CONF_COLOR: color}, errors


def person_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Formular fuer eine Person, mit Vorgaben vorbelegt."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, vol.UNDEFINED)): TextSelector(),
            vol.Required(
                CONF_LETTER, default=defaults.get(CONF_LETTER, vol.UNDEFINED)
            ): TextSelector(),
            vol.Required(CONF_COLOR, default=list(defaults[CONF_COLOR])): ColorRGBSelector(),
        }
    )


def _source_selector() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain=CALENDAR_DOMAIN))


def _describe(persons: Iterable[ConfigSubentryData]) -> str:
    names = [f"{person['title']} ({person['data'][CONF_LETTER]})" for person in persons]
    return ", ".join(names) if names else "-"
