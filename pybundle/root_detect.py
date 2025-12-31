from __future__ import annotations

from pathlib import Path

_MARKERS = [".git", "pyproject.toml", "requirements.txt", "setup.cfg", "setup.py"]


def detect_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        for m in _MARKERS:
            if (p / m).exists():
                return p
    return None
