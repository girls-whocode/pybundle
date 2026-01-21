from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import get_platform_info, is_windows


@dataclass
class PlatformInfoStep:
    """Cross-platform system information step.
    
    On Unix-like systems, this complements the uname command.
    On Windows, this replaces uname which is not available.
    """
    name: str = "platform info"
    outfile: str = "meta/21_platform_info.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            info = get_platform_info()
            
            lines = ["# Platform Information\n\n"]
            lines.append(f"System:          {info['system']}\n")
            lines.append(f"Release:         {info['release']}\n")
            lines.append(f"Version:         {info['version']}\n")
            lines.append(f"Machine:         {info['machine']}\n")
            lines.append(f"Processor:       {info['processor']}\n")
            lines.append(f"\nPython Version:\n{info['python_version']}\n")
            
            if is_windows():
                lines.append("\nNote: Generated using Python's platform module (uname not available on Windows)\n")
            
            out.write_text("".join(lines), encoding="utf-8")
            
            elapsed = int(time.time() - start)
            return StepResult(self.name, "PASS", elapsed, "")
            
        except Exception as e:
            out.write_text(f"Error gathering platform info: {e}\n", encoding="utf-8")
            elapsed = int(time.time() - start)
            return StepResult(self.name, "FAIL", elapsed, str(e))
