from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


def _repo_has_py_files(root: Path) -> bool:
    """Fast check if there are Python files to scan."""
    for p in root.rglob("*.py"):
        parts = set(p.parts)
        if (
            ".venv" not in parts
            and "__pycache__" not in parts
            and "node_modules" not in parts
            and "dist" not in parts
            and "build" not in parts
            and "artifacts" not in parts
        ):
            return True
    return False


@dataclass
class BanditStep:
    name: str = "bandit"
    target: str = "."
    outfile: str = "logs/50_bandit.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        bandit = which("bandit")
        if not bandit:
            out.write_text(
                "bandit not found; skipping (pip install bandit)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing bandit")

        if not _repo_has_py_files(ctx.root):
            out.write_text("no .py files detected; skipping bandit\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "no python files")

        # Run bandit with recursive mode, excluding common directories
        cmd = [
            bandit,
            "-r",
            self.target,
            "--exclude",
            "**/artifacts/**,.venv,venv,__pycache__,.mypy_cache,.ruff_cache,node_modules,dist,build,.git,.tox,*.egg-info",
            "--format",
            "txt",
        ]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(  # nosec B603
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        # Bandit exit codes: 0=no issues, 1=issues found
        note = "" if cp.returncode == 0 else f"exit={cp.returncode} (security issues)"
        return StepResult(self.name, "PASS", dur, note)
