from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext
from ..tools import which


@dataclass
class RipgrepScanStep:
    name: str
    pattern: str
    outfile: str
    target: str = "."  # directory or file
    extra_args: list[str] | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        rg = which("rg")
        if not rg:
            out.write_text(
                "rg (ripgrep) not found; skipping (install ripgrep)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing rg")

        args = self.extra_args or []
        # -n line numbers, --no-heading keeps it grep-like, -S smart case can be handy
        cmd = [rg, "-n", "--no-heading", "-S", *args, self.pattern, self.target]
        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n\n"

        cp = subprocess.run(
            cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False
        )
        # rg exit codes:
        # 0 = matches found
        # 1 = no matches found (not an error!)
        # 2 = actual error
        text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        out.write_text(ctx.redact_text(text), encoding="utf-8")

        dur = int(time.time() - start)
        note = ""
        if cp.returncode == 2:
            note = "rg error (exit=2) recorded"
        elif cp.returncode == 1:
            note = "no matches"

        # Always PASS; we’re collecting info, not enforcing policy (yet).
        return StepResult(self.name, "PASS", dur, note)


def default_rg_steps(target: str = ".") -> list[RipgrepScanStep]:
    return [
        RipgrepScanStep(
            name="rg TODO/FIXME/HACK",
            pattern=r"TODO|FIXME|HACK",
            outfile="logs/40_rg_todos.txt",
            target=target,
        ),
        RipgrepScanStep(
            name="rg print(",
            pattern=r"^\s*print\(",
            outfile="logs/41_rg_prints.txt",
            target=target,
        ),
        RipgrepScanStep(
            name="rg except patterns",
            pattern=r"except\s+Exception|except\s*:",
            outfile="logs/42_rg_bare_excepts.txt",
            target=target,
        ),
    ]
