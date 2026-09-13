"""Die Fachlogik bleibt frei von Home Assistant.

Nur so laufen die Domaenentests ueberall, und nur so bleibt die Kuerzelregel
ohne Home-Assistant-Testumgebung pruefbar.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_PAKET = Path(__file__).resolve().parents[2] / "custom_components" / "family_calendar"
_REINE_MODULE = [*sorted((_PAKET / "domain").glob("*.py")), _PAKET / "const.py"]


def _importe(pfad: Path) -> set[str]:
    baum = ast.parse(pfad.read_text(encoding="utf-8"))
    namen: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            namen.update(alias.name for alias in knoten.names)
        elif isinstance(knoten, ast.ImportFrom) and knoten.module:
            namen.add(knoten.module)
    return namen


@pytest.mark.parametrize("pfad", _REINE_MODULE, ids=lambda p: p.name)
def test_kein_home_assistant_import(pfad: Path) -> None:
    verboten = {name for name in _importe(pfad) if name.split(".")[0] == "homeassistant"}
    assert not verboten, f"{pfad.name} importiert {verboten}"
