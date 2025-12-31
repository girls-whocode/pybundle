from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


def _guess_targets(root: Path) -> list[str]:
    """
    Heuristic targets:
    - If there are top-level Python package dirs (contain __init__.py), compile those.
    - Otherwise compile '.' (repo root).
    """
    targets: list[str] = []

    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if (p / "__init__.py").is_file():
            targets.append(p.name)

    return targets or ["."]
    

@dataclass
class CompileAllStep:
    name: str = "compileall"
    quiet: bool = True

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.logdir / "30_compileall.txt"
        out.parent.mkdir(parents=True, exist_ok=True)

        py = ctx.tools.python
        if not py:
            out.write_text("python not found; skipping compileall\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "missing python")

        targets = _guess_targets(ctx.root)
        cmd = [py, "-m", "compileall"]
        if self.quiet:
            cmd.append("-q")
        cmd.extend(targets)

        header = f"## PWD: {ctx.root}\n## CMD: {' '.join(cmd)}\n## TARGETS: {targets}\n\n"

        try:
            cp = subprocess.run(
                cmd,
                cwd=str(ctx.root),
                text=True,
                capture_output=True,
                check=False,
            )
            text = header + (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
            out.write_text(ctx.redact_text(text), encoding="utf-8")
            dur = int(time.time() - start)

            # compileall uses non-zero for compile failures; we record it but don't fail bundling.
            note = "" if cp.returncode == 0 else f"exit={cp.returncode} (recorded)"
            return StepResult(self.name, "PASS", dur, note)
        except Exception as e:
            out.write_text(ctx.redact_text(header + f"\nEXCEPTION: {e}\n"), encoding="utf-8")
            dur = int(time.time() - start)
            return StepResult(self.name, "PASS", dur, f"exception recorded: {e}")
