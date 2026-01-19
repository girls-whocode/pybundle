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
class InterrogateStep:
    name: str = "interrogate"
    target: str = "."
    outfile: str = "logs/52_docstring_coverage.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        interrogate = which("interrogate")
        if not interrogate:
            out.write_text(
                "interrogate not found; skipping (pip install interrogate)\n",
                encoding="utf-8",
            )
            return StepResult(self.name, "SKIP", 0, "missing interrogate")

        if not _repo_has_py_files(ctx.root):
            out.write_text(
                "no .py files detected; skipping interrogate\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no python files")

        target_path = ctx.root / self.target
        cmd = [
            interrogate,
            str(target_path),
            "-v",  # Verbose output
            "--fail-under",
            "0",  # Don't fail the step based on coverage percentage
            "--color",
        ]

        try:
            result = subprocess.run(  # nosec B603 - Using full path from which()
                cmd,
                cwd=ctx.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            out.write_text(result.stdout, encoding="utf-8")
            elapsed = int((time.time() - start) * 1000)

            # interrogate returns 0 even with missing docstrings when --fail-under=0
            # We consider any execution a success
            return StepResult(self.name, "OK", elapsed, "")
        except subprocess.TimeoutExpired:
            out.write_text("interrogate timed out after 120s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 120000, "timeout")
        except Exception as e:
            out.write_text(f"interrogate error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))
