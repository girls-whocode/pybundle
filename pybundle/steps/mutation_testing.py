"""
Mutation testing with mutmut - Milestone 4 (v1.4.1)
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext
from ..tools import which


@dataclass
class MutationTestingStep:
    """
    Mutation testing to measure test suite effectiveness.
    
    EXPENSIVE: Disabled by default. Run many test executions with code mutations.
    
    Outputs:
    - logs/72_mutation_testing.txt: Mutation testing results
    """
    
    name: str = "mutation_testing"
    
    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        
        # Only run if explicitly enabled (very slow!)
        if not ctx.options.enable_mutation_testing:
            return StepResult(self.name, "SKIP", 0, "mutation testing not enabled (slow!)")
        
        # Check for mutmut
        mutmut = which("mutmut")
        if not mutmut:
            output_file = ctx.workdir / "logs" / "72_mutation_testing.txt"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                "mutmut not found; install with: pip install mutmut\n",
                encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "mutmut not installed")
        
        if not ctx.tools.pytest:
            return StepResult(self.name, "SKIP", 0, "pytest not found")
        
        tests_dir = ctx.root / "tests"
        if not tests_dir.is_dir():
            return StepResult(self.name, "SKIP", 0, "no tests/ directory")
        
        ctx.emit("  ⚠️  Running mutation testing (this may take several minutes)...")
        
        output_file = ctx.workdir / "logs" / "72_mutation_testing.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Run mutmut
            # First, run mutmut run to generate mutations
            run_result = subprocess.run(
                [mutmut, "run", "--paths-to-mutate", "."],
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout (mutation testing is SLOW)
            )
            
            # Then get results summary
            results_result = subprocess.run(
                [mutmut, "results"],
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Generate report
            with output_file.open("w") as f:
                f.write("=" * 70 + "\n")
                f.write("MUTATION TESTING (mutmut)\n")
                f.write("=" * 70 + "\n")
                f.write("⚠️  WARNING: Mutation testing is VERY SLOW\n")
                f.write("=" * 70 + "\n\n")
                
                f.write("MUTATION RUN OUTPUT:\n")
                f.write("-" * 70 + "\n")
                f.write(run_result.stdout)
                if run_result.stderr:
                    f.write("\nErrors:\n")
                    f.write(run_result.stderr)
                
                f.write("\n" + "=" * 70 + "\n")
                f.write("MUTATION RESULTS SUMMARY:\n")
                f.write("-" * 70 + "\n")
                f.write(results_result.stdout)
                if results_result.stderr:
                    f.write("\nErrors:\n")
                    f.write(results_result.stderr)
                
                f.write("\n" + "=" * 70 + "\n")
                f.write("INTERPRETATION:\n")
                f.write("-" * 70 + "\n")
                f.write("- Killed mutations: Your tests caught the bug (GOOD!)\n")
                f.write("- Survived mutations: Your tests missed the bug (BAD!)\n")
                f.write("- Timeout/Suspicious: Tests took too long or behaved oddly\n")
                f.write("\n")
                f.write("Mutation Score = Killed / (Killed + Survived + Timeout)\n")
                f.write("Target: >80% mutation score for well-tested code\n")
                f.write("\n")
                f.write("To see specific survived mutations:\n")
                f.write("  mutmut show <id>\n")
                f.write("\n")
                f.write("=" * 70 + "\n")
                f.write("RECOMMENDATIONS:\n")
                f.write("- Add tests for survived mutations\n")
                f.write("- Focus on edge cases and boundary conditions\n")
                f.write("- Improve assertion quality (not just 'assert result')\n")
            
            elapsed = int((time.time() - start) * 1000)
            
            if run_result.returncode == 0:
                return StepResult(self.name, "OK", elapsed)
            else:
                return StepResult(self.name, "FAIL", elapsed, f"exit {run_result.returncode}")
                
        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            with output_file.open("w") as f:
                f.write("Mutation testing timed out after 10 minutes\n")
                f.write("Consider testing a smaller subset or using --paths-to-mutate\n")
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))
