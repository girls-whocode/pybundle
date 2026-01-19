"""
Import time analysis - Milestone 3 (v1.4.0)
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class ImportTimeStep:
    """
    Analyze Python import times using -X importtime to identify slow imports.
    
    Outputs:
    - logs/61_import_time.txt: Ranked list of slowest imports
    """
    
    name: str = "import_time"
    
    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        
        if ctx.options.no_profile:
            return StepResult(self.name, "SKIP", 0, "profiling disabled")
        
        # Find entry point
        entry_point = self._find_entry_point(ctx)
        
        if not entry_point:
            return StepResult(self.name, "SKIP", 0, "no suitable entry point found")
        
        ctx.emit(f"  Analyzing import time for {entry_point.name}")
        
        try:
            # Run with -X importtime
            result = subprocess.run(
                [
                    str(ctx.tools.python),
                    "-X", "importtime",
                    "-c", f"import runpy; runpy.run_path('{entry_point}')"
                ],
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse and rank import times
            self._generate_report(result.stderr, ctx.workdir)  # importtime outputs to stderr
            
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "OK", elapsed)
            
        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))
    
    def _find_entry_point(self, ctx: BundleContext) -> Path | None:
        """Find the best entry point to analyze"""
        if ctx.options.profile_entry_point:
            ep = Path(ctx.options.profile_entry_point)
            if not ep.is_absolute():
                ep = ctx.root / ctx.options.profile_entry_point
            if ep.exists() and ep.is_file():
                return ep
        
        # Try package/__main__.py
        pyproject = ctx.root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                    pkg_name = data.get("project", {}).get("name", "").replace("-", "_")
                    if pkg_name:
                        pkg_main = ctx.root / pkg_name / "__main__.py"
                        if pkg_main.exists():
                            return pkg_main
            except Exception:
                pass
        
        # Try common entry points
        for entry in ["__main__.py", "main.py", "app.py", "cli.py"]:
            path = ctx.root / entry
            if path.exists():
                return path
        
        return None
    
    def _generate_report(self, importtime_output: str, workdir: Path) -> None:
        """Parse -X importtime output and generate ranked report"""
        output_file = workdir / "logs" / "61_import_time.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse import times
        # Format: "import time: self [us] | cumulative | imported package"
        imports = []
        for line in importtime_output.splitlines():
            if "import time:" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        # Extract times
                        time_part = parts[0].split(":")[-1].strip()
                        self_time = int(time_part.split()[0])
                        cumulative = int(parts[1].strip())
                        module = parts[2].strip()
                        imports.append((cumulative, self_time, module))
                    except (ValueError, IndexError):
                        continue
        
        # Sort by cumulative time (descending)
        imports.sort(reverse=True)
        
        with output_file.open("w") as f:
            f.write("=" * 70 + "\n")
            f.write("IMPORT TIME ANALYSIS\n")
            f.write("=" * 70 + "\n\n")
            
            if not imports:
                f.write("No import time data collected.\n")
                f.write("\nRaw output:\n")
                f.write(importtime_output)
                return
            
            # Calculate total
            total_time = sum(imp[0] for imp in imports[:1])  # Top-level cumulative
            
            f.write(f"Total import time: {total_time / 1000:.1f} ms\n")
            f.write(f"Number of imports analyzed: {len(imports)}\n\n")
            
            f.write("TOP 30 SLOWEST IMPORTS (by cumulative time):\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Cumulative (ms)':<18} {'Self (ms)':<15} {'Module'}\n")
            f.write("-" * 70 + "\n")
            
            for cumulative, self_time, module in imports[:30]:
                f.write(f"{cumulative / 1000:>15.1f}  {self_time / 1000:>12.1f}  {module}\n")
            
            # Also show slowest by self time
            imports_by_self = sorted(imports, key=lambda x: x[1], reverse=True)
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("TOP 20 SLOWEST IMPORTS (by self time, excluding children):\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Self (ms)':<15} {'Cumulative (ms)':<18} {'Module'}\n")
            f.write("-" * 70 + "\n")
            
            for cumulative, self_time, module in imports_by_self[:20]:
                f.write(f"{self_time / 1000:>12.1f}  {cumulative / 1000:>15.1f}  {module}\n")
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("Recommendations:\n")
            f.write("- Consider lazy imports for modules with high cumulative times\n")
            f.write("- Review modules with high self times for optimization\n")
            f.write("- Use conditional imports to defer loading when possible\n")
