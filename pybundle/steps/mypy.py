from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


def _has_mypy_config(root: Path) -> bool:
    if (root / "mypy.ini").is_file():
        return True
    if (root / "setup.cfg").is_file():
        return True
    if (root / "pyproject.toml").is_file():
        # we don't parse TOML here; presence is enough for v1
        return True
    return False


@dataclass
class MypyStep:
    name: str = "mypy"
    target: str = "."
    outfile: str = "logs/33_mypy.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        mypy = which("mypy")
        if not mypy:
            out.write_text("mypy not found; skipping (pip install mypy)\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "missing mypy")

        if not _has_mypy_config(ctx.root):
            out.write_text("no mypy config detected (mypy.ini/setup.cfg/pyproject.toml); skipping\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "no config")

        cmd = [mypy, self.target]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False)
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        note = "" if cp.returncode == 0 else f"exit={cp.returncode} (type findings)"
        return StepResult(self.name, "PASS", dur, note)
