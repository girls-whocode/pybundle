from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext
from ..tools import which


@dataclass
class LicenseScanStep:
    name: str = "license scan"
    outfile: str = "meta/32_licenses.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        pip_licenses = which("pip-licenses")
        if not pip_licenses:
            out.write_text(
                "pip-licenses not found; skipping (pip install pip-licenses)\n",
                encoding="utf-8",
            )
            return StepResult(self.name, "SKIP", 0, "missing pip-licenses")

        # Run pip-licenses with detailed output
        cmd = [
            pip_licenses,
            "--format=markdown",  # Markdown table format
            "--with-urls",  # Include project URLs
            "--with-description",  # Include package descriptions
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

            output = result.stdout

            # Add license compatibility warnings
            warnings = self._check_license_compatibility(output)
            if warnings:
                output += "\n\n" + "=" * 70 + "\n"
                output += "LICENSE COMPATIBILITY WARNINGS\n"
                output += "=" * 70 + "\n\n"
                output += "\n".join(warnings)

            out.write_text(output, encoding="utf-8")
            elapsed = int((time.time() - start) * 1000)

            return StepResult(self.name, "OK", elapsed, "")
        except subprocess.TimeoutExpired:
            out.write_text("pip-licenses timed out after 60s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 60000, "timeout")
        except Exception as e:
            out.write_text(f"pip-licenses error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))

    def _check_license_compatibility(self, output: str) -> list[str]:
        """Check for common license compatibility issues."""
        warnings = []

        # Simple heuristic: look for GPL + permissive license mixing
        has_gpl = any(gpl in output for gpl in ["GPL", "AGPL", "LGPL"])
        has_mit = "MIT" in output
        has_apache = "Apache" in output
        has_bsd = "BSD" in output

        if has_gpl and (has_mit or has_apache or has_bsd):
            warnings.append(
                "⚠️  Potential GPL compatibility issue detected:\n"
                "   - GPL/LGPL/AGPL licenses found alongside permissive licenses (MIT/Apache/BSD)\n"
                "   - Review GPL obligations if redistributing\n"
                "   - LGPL is generally compatible with permissive licenses\n"
                "   - Consult legal counsel for production use"
            )

        # Check for proprietary or unknown licenses
        if "UNKNOWN" in output:
            warnings.append(
                "⚠️  Packages with UNKNOWN licenses detected:\n"
                "   - Review manually before distribution\n"
                "   - May indicate missing license metadata"
            )

        return warnings
