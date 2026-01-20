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
class RadonStep:
    name: str = "radon"
    target: str = "."
    outfile: str = "logs/51_radon_complexity.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        radon = which("radon")
        if not radon:
            out.write_text(
                "radon not found; skipping (pip install radon)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing radon")

        if not _repo_has_py_files(ctx.root):
            out.write_text("no .py files detected; skipping radon\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "no python files")

        target_path = ctx.root / self.target

        # Build exclude patterns to avoid scanning artifacts, venvs, caches
        # CRITICAL: Radon scans everything by default, including prior pybundle runs
        # Use simple patterns without wildcards - radon's --exclude is finicky
        excludes = [
            # Artifacts from prior pybundle runs (CRITICAL - prevents duplicate reports)
            "artifacts",
            # Virtual environments (all common patterns)
            ".venv",
            "venv",
            "env",
            ".env",
            ".freeze-venv",
            ".pybundle-venv",
            # Also catch custom venv names with glob patterns
            "*-venv",
            "*_venv",
            ".gaslog-venv",
            # Caches
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".tox",
            ".nox",
            # Build outputs
            "node_modules",
            "dist",
            "build",
            "target",
            # Version control
            ".git",
        ]
        
        # Radon --exclude takes comma-separated patterns
        exclude_arg = ",".join(excludes)

        # Run cyclomatic complexity check
        cmd_cc = [
            radon,
            "cc",
            str(target_path),
            "-s",  # Show complexity score
            "-a",  # Average complexity
            "-nc",  # No color
            "--exclude",
            exclude_arg,
        ]

        # Run maintainability index check
        cmd_mi = [
            radon,
            "mi",
            str(target_path),
            "-s",  # Show maintainability index
            "-nc",  # No color
            "--exclude",
            exclude_arg,
        ]

        try:
            # Collect both metrics in one output file
            with out.open("w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("CYCLOMATIC COMPLEXITY\n")
                f.write("=" * 70 + "\n\n")

                result_cc = subprocess.run(  # nosec B603 - Using full path from which()
                    cmd_cc,
                    cwd=ctx.root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=120,
                )
                f.write(result_cc.stdout)

                f.write("\n\n")
                f.write("=" * 70 + "\n")
                f.write("MAINTAINABILITY INDEX\n")
                f.write("=" * 70 + "\n\n")

                result_mi = subprocess.run(  # nosec B603 - Using full path from which()
                    cmd_mi,
                    cwd=ctx.root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=120,
                )
                f.write(result_mi.stdout)

            elapsed = int((time.time() - start) * 1000)

            # Radon returns 0 on success
            if result_cc.returncode == 0 and result_mi.returncode == 0:
                return StepResult(self.name, "OK", elapsed, "")
            else:
                return StepResult(
                    self.name,
                    "FAIL",
                    elapsed,
                    f"exit cc:{result_cc.returncode} mi:{result_mi.returncode}",
                )
        except subprocess.TimeoutExpired:
            out.write_text("radon timed out after 120s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 120000, "timeout")
        except Exception as e:
            out.write_text(f"radon error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))
