"""Konstanten des Familienkalenders.

Bewusst ohne Home-Assistant-Import, damit auch die Domaenentests sie nutzen koennen.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "family_calendar"

CONFIG_ENTRY_VERSION: Final = 1
DEFAULT_TITLE: Final = "Familienkalender"

# Optionen des Eintrags
CONF_SOURCE: Final = "source_calendar"
CONF_SYNC_DASHBOARDS: Final = "sync_dashboards"
DEFAULT_SYNC_DASHBOARDS: Final = True

# Personen sind Untereintraege (Config Subentries)
SUBENTRY_PERSON: Final = "person"
CONF_LETTER: Final = "letter"
CONF_COLOR: Final = "color"

#: Wie oft der naechste Termin je Person neu bestimmt wird. Zusaetzlich loest
#: jede Zustandsaenderung des Quellkalenders eine Aktualisierung aus.
UPDATE_INTERVAL: Final = timedelta(minutes=15)

#: Wie weit der naechste Termin im Voraus gesucht wird.
LOOKAHEAD: Final = timedelta(days=30)

#: Wie lange eine Abfrage des Quellkalenders fuer denselben Zeitraum gilt. Eine
#: Kalenderkarte fragt alle Personenkalender gleichzeitig ab; so geht dafuer
#: nur eine Abfrage an den Quellkalender.
SOURCE_CACHE_TTL: Final = timedelta(seconds=30)

#: Wartezeit, bevor nach einer Dashboard-Aenderung die Farben abgeglichen werden.
DASHBOARD_SYNC_COOLDOWN: Final = 2.0
