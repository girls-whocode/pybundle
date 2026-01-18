from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


def _has_pytest(root: Path) -> bool:
    """Check if pytest is likely used (tests exist or pytest in deps)."""
    # Look for common test directories (exclude venv)
    for test_dir in ["tests", "test"]:
        test_path = root / test_dir
        if test_path.is_dir():
            # Make sure it's not inside a venv
            if not any(p.name.endswith('venv') or p.name.startswith('.') for p in test_path.parents):
                return True
    
    # Look for test files in the project root and immediate subdirectories
    # (not deep recursion to avoid finding venv tests)
    for pattern in ["test_*.py", "*_test.py"]:
        for p in root.glob(pattern):
            return True
        # Check one level deep
        for subdir in root.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.') and not subdir.name.endswith('venv'):
                for p in subdir.glob(pattern):
                    return True
    
    return False


@dataclass
class CoverageStep:
    name: str = "coverage"
    outfile: str = "logs/35_coverage.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        # Check for pytest first (since we use pytest-cov)
        pytest_bin = which("pytest")
        if not pytest_bin:
            out.write_text(
                "pytest not found; skipping coverage (pip install pytest pytest-cov)\n",
                encoding="utf-8",
            )
            return StepResult(self.name, "SKIP", 0, "missing pytest")

        # Check if there are tests to run
        if not _has_pytest(ctx.root):
            out.write_text(
                "no tests detected; skipping coverage\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no tests")

        # Run pytest with coverage
        cmd = [
            pytest_bin,
            "--cov",
            "--cov-report=term-missing:skip-covered",
            "--no-cov-on-fail",
            "-q",
        ]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        
        # Combine stdout and stderr
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        
        # If pytest-cov is not installed, provide helpful message
        if "pytest: error: unrecognized arguments: --cov" in text:
            text = (
                header
                + "pytest-cov not found; install with: pip install pytest-cov\n\n"
                + text
            )
            out.write_text(ctx.redact_text(text), encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "missing pytest-cov")
        
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        # Non-zero exit means test failures or coverage threshold not met
        note = "" if cp.returncode == 0 else f"exit={cp.returncode}"
        return StepResult(self.name, "PASS", dur, note)
