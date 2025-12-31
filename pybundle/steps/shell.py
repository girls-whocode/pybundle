from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class ShellStep:
    name: str
    outfile_rel: str
    cmd: list[str]
    cwd_is_root: bool = True
    allow_fail: bool = True
    require_cmd: str | None = None

    @property
    def out_rel(self) -> str:
        return self.outfile_rel

    def run(self, ctx: BundleContext) -> StepResult:
        if self.require_cmd and not getattr(ctx.tools, self.require_cmd, None):
            out = ctx.workdir / self.outfile_rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(f"{self.require_cmd} not found; skipping\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, f"missing {self.require_cmd}")

        out = ctx.workdir / self.outfile_rel
        out.parent.mkdir(parents=True, exist_ok=True)

        start = time.time()
        header = (
            f"## PWD: {ctx.root if self.cwd_is_root else Path.cwd()}\n"
            f"## CMD: {' '.join(self.cmd)}\n\n"
        )

        try:
            cp = subprocess.run(
                self.cmd,
                cwd=str(ctx.root) if self.cwd_is_root else None,
                text=True,
                capture_output=True,
                check=False,
            )
            text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
            out.write_text(ctx.redact_text(text), encoding="utf-8")
            status = "PASS" if cp.returncode == 0 else ("FAIL" if not self.allow_fail else "PASS")
            note = "" if cp.returncode == 0 else f"exit={cp.returncode}"
        except Exception as e:
            out.write_text(ctx.redact_text(header + f"\nEXCEPTION: {e}\n"), encoding="utf-8")
            status = "FAIL" if not self.allow_fail else "PASS"
            note = str(e)

        dur = int(time.time() - start)
        return StepResult(self.name, status, dur, note)
