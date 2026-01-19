"""
Line-by-line profiling with line_profiler - Milestone 3 (v1.4.0)
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class LineProfilerStep:
    """
    Line-by-line profiling using line_profiler (optional, requires manual annotation).

    This step is disabled by default and requires:
    1. line_profiler installed
    2. Functions decorated with @profile or listed in config

    Outputs:
    - logs/63_line_profile.txt: Line-by-line execution times
    """

    name: str = "line_profiler"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()

        # Only run if explicitly enabled
        if ctx.options.no_profile or not ctx.options.enable_line_profiler:
            return StepResult(self.name, "SKIP", 0, "line profiler not enabled")

        # Check if line_profiler is installed
        if not ctx.tools.line_profiler:
            return StepResult(self.name, "SKIP", 0, "line_profiler not installed")

        # Check if entry point exists
        entry_point = ctx.options.profile_entry_point
        if not entry_point:
            return StepResult(self.name, "SKIP", 0, "no entry point specified")

        target_path = Path(entry_point)
        if not target_path.is_absolute():
            target_path = ctx.root / entry_point

        if not target_path.exists():
            return StepResult(
                self.name, "SKIP", 0, f"entry point not found: {entry_point}"
            )

        ctx.emit(f"  Running line profiler on {target_path.name}")
        ctx.emit("  Note: Functions must be decorated with @profile")

        try:
            # Run line_profiler via kernprof
            result = subprocess.run(
                [
                    str(ctx.tools.line_profiler),
                    "-l",  # Line-by-line
                    "-v",  # Verbose output
                    str(target_path),
                ],
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Write output
            output_file = ctx.workdir / "logs" / "63_line_profile.txt"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("w") as f:
                f.write("=" * 70 + "\n")
                f.write("LINE-BY-LINE PROFILING (line_profiler)\n")
                f.write("=" * 70 + "\n\n")

                if result.returncode == 0:
                    f.write(result.stdout)
                    if result.stderr:
                        f.write("\n\nWarnings/Errors:\n")
                        f.write(result.stderr)
                else:
                    f.write(
                        "Line profiling failed or no functions decorated with @profile\n\n"
                    )
                    f.write("To use line_profiler:\n")
                    f.write("1. Install: pip install line_profiler\n")
                    f.write("2. Decorate functions with @profile\n")
                    f.write(
                        "3. Specify entry point: --profile-entry-point path/to/script.py\n"
                    )
                    f.write("4. Enable: --enable-line-profiler\n\n")
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                    f.write("\n\nSTDERR:\n")
                    f.write(result.stderr)

            elapsed = int((time.time() - start) * 1000)
            if result.returncode == 0:
                return StepResult(self.name, "OK", elapsed)
            else:
                return StepResult(
                    self.name, "FAIL", elapsed, f"exit {result.returncode}"
                )

        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))
