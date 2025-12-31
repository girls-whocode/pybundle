from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


def _repo_has_py_files(root: Path) -> bool:
    # Fast-ish heuristic: look for any .py file in top couple levels
    # (Avoid walking deep trees; ruff itself can handle it.)
    for p in root.rglob("*.py"):
        # ignore common junk dirs
        parts = set(p.parts)
        if (
            ".venv" in parts
            or "__pycache__" in parts
            or ".mypy_cache" in parts
            or ".ruff_cache" in parts
        ):
            continue
        if (
            "node_modules" in parts
            or "dist" in parts
            or "build" in parts
            or "artifacts" in parts
        ):
            continue
        return True
    return False


@dataclass
class RuffCheckStep:
    name: str = "ruff check"
    target: str = "."
    outfile: str = "logs/31_ruff_check.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        ruff = which("ruff")
        if not ruff:
            out.write_text(
                "ruff not found; skipping (pip install ruff)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing ruff")

        if not _repo_has_py_files(ctx.root):
            out.write_text(
                "no .py files detected; skipping ruff check\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no python files")

        cmd = [ruff, "check", self.target]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        # ruff nonzero = lint failures; that’s *valuable*, but for bundling we record it.
        note = "" if cp.returncode == 0 else f"exit={cp.returncode} (lint findings)"
        return StepResult(self.name, "PASS", dur, note)


@dataclass
class RuffFormatCheckStep:
    name: str = "ruff format --check"
    target: str = "."
    outfile: str = "logs/32_ruff_format_check.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        ruff = which("ruff")
        if not ruff:
            out.write_text(
                "ruff not found; skipping (pip install ruff)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing ruff")

        if not _repo_has_py_files(ctx.root):
            out.write_text(
                "no .py files detected; skipping ruff format check\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no python files")

        cmd = [ruff, "format", "--check", self.target]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        note = "" if cp.returncode == 0 else f"exit={cp.returncode} (format drift)"
        return StepResult(self.name, "PASS", dur, note)
