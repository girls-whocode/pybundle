from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


def _has_tests(root: Path) -> bool:
    # common conventions
    if (root / "tests").is_dir():
        return True
    # sometimes tests are inside the package
    # (don’t walk the whole tree; just check a couple likely paths)
    for candidate in ["src/tests", "app/tests"]:
        if (root / candidate).is_dir():
            return True
    # any */tests at depth 2 is also a common pattern
    for p in root.glob("*/tests"):
        if p.is_dir():
            return True
    return False


@dataclass
class PytestStep:
    name: str = "pytest"
    args: list[str] = None
    outfile: str = "logs/34_pytest_q.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        pytest_bin = which("pytest")
        if not pytest_bin:
            out.write_text("pytest not found; skipping (pip install pytest)\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "missing pytest")

        if not _has_tests(ctx.root):
            out.write_text("no tests directory detected; skipping pytest\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "no tests")

        args = self.args or ["-q"]
        cmd = [pytest_bin, *args]

        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False)
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        note = "" if cp.returncode == 0 else f"exit={cp.returncode} (test failures)"
        return StepResult(self.name, "PASS", dur, note)
