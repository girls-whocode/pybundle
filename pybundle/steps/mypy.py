from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
import sys
import re
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


def _check_python_version_mismatch(root: Path) -> tuple[str | None, str | None]:
    """Check for Python version mismatch between runtime and mypy config.
    
    Returns (runtime_version, config_version) where config_version is from mypy.ini
    """
    # Get runtime Python version (e.g., "3.11")
    runtime_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    # Check mypy.ini for python_version
    mypy_ini = root / "mypy.ini"
    if mypy_ini.is_file():
        try:
            content = mypy_ini.read_text(encoding="utf-8")
            match = re.search(r'^python_version\s*=\s*["\']?(\d+\.\d+)', content, re.MULTILINE)
            if match:
                config_version = match.group(1)
                if config_version != runtime_version:
                    return (runtime_version, config_version)
        except Exception:
            pass
    
    return (None, None)


@dataclass
class MypyStep:
    name: str = "mypy"
    target: str = "pybundle"
    outfile: str = "logs/33_mypy.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        mypy = which("mypy")
        if not mypy:
            out.write_text(
                "mypy not found; skipping (pip install mypy)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing mypy")

        if not _has_mypy_config(ctx.root):
            out.write_text(
                "no mypy config detected (mypy.ini/setup.cfg/pyproject.toml); skipping\n",
                encoding="utf-8",
            )
            return StepResult(self.name, "SKIP", 0, "no config")

        # Check for Python version mismatch
        runtime_ver, config_ver = _check_python_version_mismatch(ctx.root)
        version_warning = ""
        if runtime_ver and config_ver:
            version_warning = (
                f"\n⚠ WARNING: Python version mismatch!\n"
                f"  Runtime: Python {runtime_ver}\n"
                f"  mypy.ini: python_version = {config_ver}\n"
                f"  This may allow/reject syntax that won't work at runtime.\n"
                f"  Recommendation: Set mypy.ini python_version = {runtime_ver}\n\n"
            )

        cmd = [mypy, "--exclude", "^artifacts/", self.target]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n{version_warning}\n"

        cp = subprocess.run(  # nosec B603
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        note = "" if cp.returncode == 0 else f"exit={cp.returncode} (type findings)"
        
        # Add version warning to note if present
        if version_warning:
            note = (note + "; " if note else "") + f"Python {runtime_ver} vs config {config_ver}"
        
        return StepResult(self.name, "PASS", dur, note)
