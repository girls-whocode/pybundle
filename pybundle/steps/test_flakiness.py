"""
Test flakiness detection - Milestone 4 (v1.4.1)
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class TestFlakinessStep:
    """
    Run tests multiple times to detect non-deterministic failures (flaky tests).
    
    Outputs:
    - logs/70_test_flakiness.txt: Report of flaky tests with pass/fail patterns
    """
    
    name: str = "test_flakiness"
    
    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        
        if not ctx.tools.pytest:
            return StepResult(self.name, "SKIP", 0, "pytest not found")
        
        tests_dir = ctx.root / "tests"
        if not tests_dir.is_dir():
            return StepResult(self.name, "SKIP", 0, "no tests/ directory")
        
        runs = ctx.options.test_flakiness_runs
        ctx.emit(f"  Running tests {runs}x to detect flakiness...")
        
        output_file = ctx.workdir / "logs" / "70_test_flakiness.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Run tests multiple times and collect results
            results = []
            test_outcomes = {}  # test_name -> [pass/fail/error]
            
            for i in range(runs):
                ctx.emit(f"    Run {i+1}/{runs}...")
                result = subprocess.run(
                    [str(ctx.tools.pytest), "-v", "--tb=no"],
                    cwd=ctx.root,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout per run
                )
                results.append(result)
                
                # Parse test results
                self._parse_test_outcomes(result.stdout, test_outcomes, i)
            
            # Analyze for flakiness
            flaky_tests = self._identify_flaky_tests(test_outcomes)
            
            # Generate report
            with output_file.open("w") as f:
                f.write("=" * 70 + "\n")
                f.write(f"TEST FLAKINESS DETECTION ({runs} runs)\n")
                f.write("=" * 70 + "\n\n")
                
                if not test_outcomes:
                    f.write("No test results collected.\n\n")
                    for i, result in enumerate(results):
                        f.write(f"Run {i+1} output:\n")
                        f.write(result.stdout[:500])
                        f.write("\n\n")
                else:
                    total_tests = len(test_outcomes)
                    f.write(f"Total tests analyzed: {total_tests}\n")
                    f.write(f"Flaky tests detected: {len(flaky_tests)}\n\n")
                    
                    if flaky_tests:
                        f.write("=" * 70 + "\n")
                        f.write("FLAKY TESTS (non-deterministic results):\n")
                        f.write("=" * 70 + "\n\n")
                        
                        for test_name, outcomes in flaky_tests.items():
                            pattern = " -> ".join(outcomes)
                            f.write(f"⚠️  {test_name}\n")
                            f.write(f"    Pattern: {pattern}\n\n")
                    else:
                        f.write("✅ No flaky tests detected - all tests deterministic!\n\n")
                    
                    # Summary of all tests
                    f.write("=" * 70 + "\n")
                    f.write("ALL TESTS SUMMARY:\n")
                    f.write("=" * 70 + "\n\n")
                    
                    stable_pass = []
                    stable_fail = []
                    flaky = []
                    
                    for test_name, outcomes in test_outcomes.items():
                        unique_outcomes = set(outcomes)
                        if len(unique_outcomes) == 1:
                            if "PASSED" in unique_outcomes:
                                stable_pass.append(test_name)
                            else:
                                stable_fail.append(test_name)
                        else:
                            flaky.append(test_name)
                    
                    f.write(f"Stable passing: {len(stable_pass)}\n")
                    f.write(f"Stable failing: {len(stable_fail)}\n")
                    f.write(f"Flaky: {len(flaky)}\n\n")
                    
                    if stable_fail:
                        f.write("Consistently failing tests:\n")
                        for test in stable_fail[:20]:  # Limit to 20
                            f.write(f"  - {test}\n")
                        if len(stable_fail) > 20:
                            f.write(f"  ... and {len(stable_fail) - 20} more\n")
                        f.write("\n")
                    
                    f.write("=" * 70 + "\n")
                    f.write("RECOMMENDATIONS:\n")
                    f.write("- Fix flaky tests by removing non-deterministic behavior\n")
                    f.write("- Common causes: timing issues, random data, external dependencies\n")
                    f.write("- Use pytest-randomly to test with different orderings\n")
            
            elapsed = int((time.time() - start) * 1000)
            
            if flaky_tests:
                return StepResult(self.name, "OK", elapsed, f"{len(flaky_tests)} flaky tests")
            else:
                return StepResult(self.name, "OK", elapsed)
                
        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))
    
    def _parse_test_outcomes(self, output: str, test_outcomes: dict, run_num: int) -> None:
        """Parse pytest -v output to extract test results"""
        for line in output.splitlines():
            # Look for pytest verbose output: "test_file.py::test_name PASSED"
            if "::" in line and any(status in line for status in ["PASSED", "FAILED", "ERROR", "SKIPPED"]):
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0]
                    # Find status
                    status = None
                    for s in ["PASSED", "FAILED", "ERROR", "SKIPPED"]:
                        if s in line:
                            status = s
                            break
                    
                    if status:
                        if test_name not in test_outcomes:
                            test_outcomes[test_name] = []
                        test_outcomes[test_name].append(status)
    
    def _identify_flaky_tests(self, test_outcomes: dict) -> dict:
        """Identify tests with inconsistent results across runs"""
        flaky = {}
        for test_name, outcomes in test_outcomes.items():
            unique_outcomes = set(outcomes)
            # Flaky if not all the same outcome
            if len(unique_outcomes) > 1:
                flaky[test_name] = outcomes
        return flaky
