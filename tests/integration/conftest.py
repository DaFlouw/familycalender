"""Fixtures der Home-Assistant-Komponententests.

Diese Tests benoetigen ``pytest-homeassistant-custom-component`` und damit eine
Linux-nahe Python-Umgebung. Sie laufen in der CI, nicht auf einem
Windows-Entwicklungsrechner.

Alle Termine und Personen sind erfunden.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta

import pytest
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    setup_test_component_platform,
)

from custom_components.family_calendar.const import (
    CONF_COLOR,
    CONF_LETTER,
    CONF_SOURCE,
    CONF_SYNC_DASHBOARDS,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    SUBENTRY_PERSON,
)
from custom_components.family_calendar.domain.colors import PALETTE

#: Fester Bezugszeitpunkt aller Komponententests.
JETZT = "2026-09-14 06:00:00+00:00"

#: Name, Kuerzel, Farbe
PERSONEN: list[tuple[str, str, list[int]]] = [
    ("Anna", "A", list(PALETTE[0])),
    ("Ben", "B", list(PALETTE[1])),
    ("Carla", "C", list(PALETTE[2])),
    ("Dora", "D", list(PALETTE[3])),
]

#: Welche Termine (ab jetzt, eine Woche) jede Person sehen muss.
ERWARTET: dict[str, set[str]] = {
    "A": {"A Zahnarzt", "DCBA Ausflug", "Sommerfest", "AA Tippfehler"},
    "B": {"bc Schwimmen", "DCBA Ausflug", "Sommerfest", "AA Tippfehler"},
    "C": {"bc Schwimmen", "DCBA Ausflug", "Sommerfest", "AA Tippfehler", "C Sport"},
    "D": {"DCBA Ausflug", "Sommerfest", "AA Tippfehler", "D Klassenfahrt"},
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Friert die Zeit ein, bevor irgendeine Fixture laeuft.

    Die Zugriffstoken der Test-Clients gelten nur kurz. Wird die Zeit erst nach
    ihrer Ausgabe vorgestellt, lehnt die HTTP-API sie als abgelaufen ab.
    """
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.freeze_time(JETZT))


def entity_id_von(name: str, geraet: str = "familienkalender") -> str:
    return f"calendar.{geraet}_{name.lower()}"


class QuellKalender(CalendarEntity):
    """Ein Kalender mit erfundenen Terminen, der seine Abfragen mitzaehlt."""

    def __init__(self, name: str, unique_id: str) -> None:
        self._attr_name = name
        self._attr_unique_id = unique_id
        self.termine: list[CalendarEvent] = []
        self.abfragen = 0

    @property
    def event(self) -> CalendarEvent | None:
        jetzt = dt_util.now()
        kommende = [t for t in self.termine if t.end_datetime_local > jetzt]
        return min(kommende, key=lambda t: t.start_datetime_local, default=None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        self.abfragen += 1
        return [
            t
            for t in self.termine
            if t.start_datetime_local < end_date and t.end_datetime_local > start_date
        ]


def termine_ab(jetzt: datetime) -> list[CalendarEvent]:
    def termin(stunden: float, dauer: float, titel: str, **felder: str) -> CalendarEvent:
        start = jetzt + timedelta(hours=stunden)
        return CalendarEvent(
            start=start, end=start + timedelta(hours=dauer), summary=titel, **felder
        )

    # Uebermorgen statt morgen: Die Testumgebung rechnet in US/Pacific, wo der
    # Bezugszeitpunkt schon spaet am Abend liegt. Ein ganztaegiger Termin
    # "morgen" begaenne dann vor allen anderen Terminen des Tests.
    uebermorgen = jetzt.date() + timedelta(days=2)
    return [
        # Ort und Beschreibung sind fuer die Zuordnung ohne Bedeutung.
        termin(1, 1, "A Zahnarzt", location="B-Strasse 5"),
        termin(2, 2, "bc Schwimmen"),
        termin(3, 1, "DCBA Ausflug"),
        termin(4, 1, "Sommerfest"),
        termin(5, 1, "AA Tippfehler"),
        termin(6, 1, "C Sport", description="D bitte abholen"),
        CalendarEvent(
            start=uebermorgen, end=uebermorgen + timedelta(days=2), summary="D Klassenfahrt"
        ),
        termin(-3, 1, "A vorbei"),
    ]


def personen_subentries() -> list[ConfigSubentryData]:
    return [
        ConfigSubentryData(
            data={CONF_LETTER: buchstabe, CONF_COLOR: farbe},
            subentry_type=SUBENTRY_PERSON,
            title=name,
            unique_id=buchstabe,
        )
        for name, buchstabe, farbe in PERSONEN
    ]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Laesst Home Assistant die Integration aus custom_components laden."""
    yield


@pytest.fixture
def expected_lingering_timers() -> bool:
    """Zeitgeber der Kalender-Entities sind hier erwartet.

    Jede Kalender-Entity plant ihren Zustandswechsel zu Beginn und Ende des
    naechsten Termins. Die Testumgebung haelt Home Assistant an, ohne die
    Entities zu entfernen; diese Zeitgeber bleiben deshalb stehen. Das betrifft
    die Quellkalender des Tests ebenso und ist kein Leck der Integration.
    """
    return True


@pytest.fixture
async def quelle(hass: HomeAssistant) -> QuellKalender:
    """``calendar.quelle`` mit Terminen und ``calendar.zweite_quelle`` ohne."""
    kalender = QuellKalender("Quelle", "quelle_1")
    kalender.termine = termine_ab(dt_util.now())
    zweite = QuellKalender("Zweite Quelle", "quelle_2")

    setup_test_component_platform(hass, "calendar", [kalender, zweite])
    assert await async_setup_component(hass, "calendar", {"calendar": {"platform": "test"}})
    await hass.async_block_till_done()
    return kalender


def registry_id(hass: HomeAssistant, entity_id: str) -> str:
    eintrag = er.async_get(hass).async_get(entity_id)
    assert eintrag is not None
    return eintrag.id


def neuer_eintrag(
    hass: HomeAssistant, *, abgleich: bool = False, quelle: str = "calendar.quelle"
) -> MockConfigEntry:
    quelle_id = registry_id(hass, quelle)
    eintrag = MockConfigEntry(
        domain=DOMAIN,
        title="Familienkalender",
        data={},
        unique_id=quelle_id,
        options={CONF_SOURCE: quelle_id, CONF_SYNC_DASHBOARDS: abgleich},
        subentries_data=personen_subentries(),
        version=CONFIG_ENTRY_VERSION,
    )
    eintrag.add_to_hass(hass)
    return eintrag


@pytest.fixture
async def eingerichtet(hass: HomeAssistant, quelle: QuellKalender) -> MockConfigEntry:
    """Ein geladener Eintrag mit vier Personen, ohne Farbabgleich."""
    eintrag = neuer_eintrag(hass)
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    return eintrag
