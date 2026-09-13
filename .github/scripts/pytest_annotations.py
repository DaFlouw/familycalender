"""Macht fehlgeschlagene Tests als GitHub-Annotationen lesbar.

Job-Logs sind nur mit Anmeldung abrufbar, Annotationen dagegen oeffentlich.
GitHub zeigt je Schritt hoechstens zehn Fehler-Annotationen; deshalb wird hier
nicht jede Zeile einzeln gemeldet, sondern je fehlgeschlagenem Test ein Block
mit Traceback und den Fehlern aus dem mitgeschnittenen Protokoll.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_ANNOTATIONS = 10
MAX_BLOCK = 6000

#: Zeilen, die fuer die Diagnose zaehlen: Assertion, Code-Stelle, Protokollfehler.
_LINE_PREFIXES = ("E ", ">", "tests/", "custom_components/")
_CODE_PREFIXES = ("File ", "raise ", "assert ")
_MARKERS = (" ERROR ", "Traceback", "Error", "Exception")

_SECTION = re.compile(r"^_{3,} (?P<name>.+?) _{3,}$", re.MULTILINE)


def _escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _sections(log: str) -> list[tuple[str, str]]:
    matches = list(_SECTION.finditer(log))
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(log)
        result.append((match.group("name"), log[match.end() : end]))
    return result


def _condense(body: str) -> str:
    keep = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if (
            line.startswith(_LINE_PREFIXES)
            or stripped.startswith(_CODE_PREFIXES)
            or any(marker in line for marker in _MARKERS)
        ):
            keep.append(line)
    text = "\n".join(keep) or body
    return text[:MAX_BLOCK]


def main(path: str) -> None:
    log = Path(path).read_text(encoding="utf-8", errors="replace")
    summary = log[log.find("short test summary info") :] if "short test summary" in log else ""

    annotations = []
    if summary:
        annotations.append(("Zusammenfassung", summary[:MAX_BLOCK]))
    for name, body in _sections(log):
        if name.startswith(("FAILURES", "ERRORS", "warnings summary")):
            continue
        annotations.append((name, _condense(body)))

    for title, text in annotations[:MAX_ANNOTATIONS]:
        print(f"::error title={_escape(title)[:200]}::{_escape(text)}")


if __name__ == "__main__":
    main(sys.argv[1])
