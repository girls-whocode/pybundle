from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext
from ..tools import which


@dataclass
class PipdeptreeStep:
    name: str = "pipdeptree"
    outfile: str = "meta/30_dependency_tree.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        pipdeptree = which("pipdeptree")
        if not pipdeptree:
            out.write_text(
                "pipdeptree not found; skipping (pip install pipdeptree)\n",
                encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing pipdeptree")

        # Run pipdeptree with warnings for conflicts
        cmd = [
            pipdeptree,
            "--warn", "fail",  # Show warnings for conflicting dependencies
        ]

        try:
            result = subprocess.run(  # nosec B603 - Using full path from which()
                cmd,
                cwd=ctx.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )
            
            # Combine stdout and stderr to capture both tree and warnings
            output = result.stdout
            if result.stderr:
                output += "\n\n=== WARNINGS ===\n" + result.stderr
            
            out.write_text(output, encoding="utf-8")
            elapsed = int((time.time() - start) * 1000)
            
            # pipdeptree returns 0 on success, even with warnings
            return StepResult(self.name, "OK", elapsed, None)
        except subprocess.TimeoutExpired:
            out.write_text("pipdeptree timed out after 60s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 60000, "timeout")
        except Exception as e:
            out.write_text(f"pipdeptree error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))
