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
class DuplicationStep:
    name: str = "duplication"
    target: str = "."
    outfile: str = "logs/53_duplication.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        pylint = which("pylint")
        if not pylint:
            out.write_text(
                "pylint not found; skipping (pip install pylint)\n", 
                encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing pylint")

        if not _repo_has_py_files(ctx.root):
            out.write_text(
                "no .py files detected; skipping duplication check\n", 
                encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no python files")

        target_path = ctx.root / self.target
        cmd = [
            pylint,
            str(target_path),
            "--disable=all",  # Disable all other checks
            "--enable=duplicate-code",  # Only check for duplication
            "--min-similarity-lines=6",  # Minimum 6 lines to be considered duplicate
        ]

        try:
            result = subprocess.run(  # nosec B603 - Using full path from which()
                cmd,
                cwd=ctx.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=180,  # Duplication detection can be slower
            )
            out.write_text(result.stdout, encoding="utf-8")
            elapsed = int((time.time() - start) * 1000)
            
            # pylint returns various exit codes:
            # 0 = no issues
            # 1, 2, 4, 8, 16 = various issue types (we still want the output)
            # We consider all of these as success
            if result.returncode in (0, 1, 2, 4, 8, 16, 24, 32):
                return StepResult(self.name, "OK", elapsed, None)
            else:
                return StepResult(
                    self.name, 
                    "FAIL", 
                    elapsed, 
                    f"exit {result.returncode}"
                )
        except subprocess.TimeoutExpired:
            out.write_text("duplication check timed out after 180s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 180000, "timeout")
        except Exception as e:
            out.write_text(f"duplication check error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))
