from __future__ import annotations

import shutil


def which(cmd: str) -> str | None:
    return shutil.which(cmd)
