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
class VultureStep:
    name: str = "vulture"
    target: str = "."
    outfile: str = "logs/50_vulture.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        vulture = which("vulture")
        if not vulture:
            out.write_text(
                "vulture not found; skipping (pip install vulture)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing vulture")

        if not _repo_has_py_files(ctx.root):
            out.write_text(
                "no .py files detected; skipping vulture\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no python files")

        target_path = ctx.root / self.target
        cmd = [
            vulture,
            str(target_path),
            "--exclude",
            "*venv*,*.venv*,.pybundle-venv,venv,env,.env,__pycache__,artifacts,build,dist,.git,.tox,node_modules",
            "--min-confidence",
            "60",  # Configurable confidence threshold
            "--sort-by-size",
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

            # Vulture exit codes:
            # 0 = no dead code found
            # 1 = usage/configuration error
            # 3 = dead code found (this is success!)
            if result.returncode in (0, 3):
                return StepResult(self.name, "OK", elapsed, "")
            else:
                return StepResult(
                    self.name, "FAIL", elapsed, f"exit {result.returncode}"
                )
        except subprocess.TimeoutExpired:
            out.write_text("vulture timed out after 120s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 120000, "timeout")
        except Exception as e:
            out.write_text(f"vulture error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))
