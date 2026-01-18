from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext
from ..tools import which


@dataclass
class PipAuditStep:
    name: str = "pip-audit"
    outfile: str = "logs/51_pip_audit.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        pip_audit = which("pip-audit")
        if not pip_audit:
            out.write_text(
                "pip-audit not found; skipping (pip install pip-audit)\n",
                encoding="utf-8",
            )
            return StepResult(self.name, "SKIP", 0, "missing pip-audit")

        # Run pip-audit to check for known vulnerabilities
        cmd = [pip_audit, "--desc", "--format", "columns"]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        # pip-audit exit codes: 0=no vulnerabilities, 1=vulnerabilities found
        note = (
            ""
            if cp.returncode == 0
            else f"exit={cp.returncode} (vulnerable packages)"
        )
        return StepResult(self.name, "PASS", dur, note)
