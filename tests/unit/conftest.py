"""Gemeinsame Vorbereitung der Domaenentests.

Diese Tests laufen bewusst ohne Home-Assistant-Runtime. Damit das moeglich
bleibt, wird das Paket ``custom_components.family_calendar`` hier als Namensraum
registriert, *ohne* sein ``__init__.py`` auszufuehren: dieses importiert Home
Assistant und wuerde die Domaenentests an eine HA-Installation binden.

Der Nebeneffekt ist erwuenscht: bekommt ein Modul unter ``domain`` versehentlich
einen Home-Assistant-Import, schlagen diese Tests fehl.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _register_namespace() -> None:
    """Meldet die Paketstruktur an, ohne das echte ``__init__.py`` zu laden."""
    for name, path in (
        ("custom_components", _ROOT / "custom_components"),
        ("custom_components.family_calendar", _ROOT / "custom_components" / "family_calendar"),
    ):
        if name in sys.modules:
            continue
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module


_register_namespace()
