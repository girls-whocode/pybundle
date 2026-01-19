"""
CPU profiling with cProfile - Milestone 3 (v1.4.0)
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class CProfileStep:
    """
    Run cProfile on the project entry point or test suite to identify CPU bottlenecks.
    
    Outputs:
    - logs/60_cprofile.txt: Top 50 slowest functions
    - meta/60_cprofile.stats: Binary stats file for further analysis
    """
    
    name: str = "cprofile"
    
    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        
        if ctx.options.no_profile:
            return StepResult(self.name, "SKIP", 0, "profiling disabled")
        
        # Determine default profiling target
        entry_point = ctx.options.profile_entry_point
        if not entry_point:
            # Default: profile pytest if tests/ exists
            tests_dir = ctx.root / "tests"
            if not tests_dir.is_dir():
                return StepResult(self.name, "SKIP", 0, "no tests/ and no entry point")
        
        # Determine what to profile
        if entry_point:
            target_path = Path(entry_point)
            if not target_path.is_absolute():
                target_path = ctx.root / entry_point
            
            if not target_path.exists():
                return StepResult(self.name, "SKIP", 0, f"entry point not found: {entry_point}")
            
            if target_path.is_file():
                # Profile a specific script
                cmd = [
                    str(ctx.tools.python),
                    "-m", "cProfile",
                    "-o", str(ctx.workdir / "meta" / "60_cprofile.stats"),
                    str(target_path)
                ]
                desc = f"Profiling {target_path.name}"
            else:
                # Assume it's a directory, profile pytest
                cmd = [
                    str(ctx.tools.python),
                    "-m", "cProfile",
                    "-o", str(ctx.workdir / "meta" / "60_cprofile.stats"),
                    "-m", "pytest",
                    str(target_path),
                    "-q"
                ]
                desc = f"Profiling pytest in {target_path.name}/"
        else:
            # Default: profile pytest
            cmd = [
                str(ctx.tools.python),
                "-m", "cProfile",
                "-o", str(ctx.workdir / "meta" / "60_cprofile.stats"),
                "-m", "pytest",
                "-q"
            ]
            desc = "Profiling pytest"
        
        ctx.emit(f"  {desc}")
        
        try:
            # Run profiling
            result = subprocess.run(
                cmd,
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for profiling
            )
            
            # Generate human-readable report
            stats_file = ctx.workdir / "meta" / "60_cprofile.stats"
            if stats_file.exists():
                self._generate_report(stats_file, ctx.workdir)
                elapsed = int((time.time() - start) * 1000)
                return StepResult(self.name, "OK", elapsed)
            else:
                # Still write output for debugging
                output_file = ctx.workdir / "logs" / "60_cprofile.txt"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with output_file.open("w") as f:
                    f.write("=" * 70 + "\n")
                    f.write("CPU PROFILING FAILED\n")
                    f.write("=" * 70 + "\n\n")
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                    f.write("\n\nSTDERR:\n")
                    f.write(result.stderr)
                
                elapsed = int((time.time() - start) * 1000)
                return StepResult(self.name, "FAIL", elapsed, "stats file not created")
                
        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))
    
    def _generate_report(self, stats_file: Path, workdir: Path) -> None:
        """Generate top 50 slowest functions report"""
        import pstats
        
        output_file = workdir / "logs" / "60_cprofile.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with output_file.open("w") as f:
            f.write("=" * 70 + "\n")
            f.write("TOP 50 SLOWEST FUNCTIONS (CPU PROFILING)\n")
            f.write("=" * 70 + "\n\n")
            
            # Load stats
            stats = pstats.Stats(str(stats_file), stream=f)
            
            # Remove directory paths for cleaner output
            stats.strip_dirs()
            
            # Sort by cumulative time and print top 50
            f.write("Sorted by cumulative time:\n")
            f.write("-" * 70 + "\n")
            stats.sort_stats('cumulative')
            stats.print_stats(50)
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("Sorted by total time (time spent in function itself):\n")
            f.write("-" * 70 + "\n")
            stats.sort_stats('time')
            stats.print_stats(50)
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("Full binary stats saved to: meta/60_cprofile.stats\n")
            f.write("Analyze with: python -m pstats meta/60_cprofile.stats\n")
