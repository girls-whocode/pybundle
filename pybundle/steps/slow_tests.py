"""
Slow test identification - Milestone 4 (v1.4.1)
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext


@dataclass
class SlowTestsStep:
    """
    Identify slow tests by parsing pytest duration output.

    Outputs:
    - logs/71_slow_tests.txt: Ranked list of slowest tests
    """

    name: str = "slow_tests"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()

        if not ctx.tools.pytest:
            return StepResult(self.name, "SKIP", 0, "pytest not found")

        tests_dir = ctx.root / "tests"
        if not tests_dir.is_dir():
            return StepResult(self.name, "SKIP", 0, "no tests/ directory")

        threshold = ctx.options.slow_test_threshold
        ctx.emit(f"  Identifying tests slower than {threshold}s...")

        output_file = ctx.workdir / "logs" / "71_slow_tests.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Run pytest with duration reporting
            result = subprocess.run(
                [
                    str(ctx.tools.pytest),
                    "-v",
                    "--durations=0",  # Show all durations
                    "--tb=no",  # No traceback to keep output clean
                ],
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout
            )

            # Parse durations from output
            slow_tests = self._parse_durations(result.stdout, threshold)

            # Generate report
            with output_file.open("w") as f:
                f.write("=" * 70 + "\n")
                f.write(f"SLOW TEST IDENTIFICATION (threshold: {threshold}s)\n")
                f.write("=" * 70 + "\n\n")

                if slow_tests:
                    f.write(
                        f"Found {len(slow_tests)} test(s) exceeding {threshold}s:\n\n"
                    )

                    # Sort by duration (descending)
                    slow_tests.sort(key=lambda x: x[1], reverse=True)

                    f.write(f"{'Duration (s)':<15} {'Test'}\n")
                    f.write("-" * 70 + "\n")

                    for test_name, duration in slow_tests:
                        f.write(f"{duration:>13.2f}  {test_name}\n")

                    f.write("\n" + "=" * 70 + "\n")
                    f.write("STATISTICS:\n")
                    f.write("-" * 70 + "\n")
                    total_time = sum(d for _, d in slow_tests)
                    avg_time = total_time / len(slow_tests)
                    f.write(f"Total slow test time: {total_time:.2f}s\n")
                    f.write(f"Average slow test time: {avg_time:.2f}s\n")
                    f.write(
                        f"Slowest test: {slow_tests[0][1]:.2f}s ({slow_tests[0][0]})\n"
                    )

                    f.write("\n" + "=" * 70 + "\n")
                    f.write("RECOMMENDATIONS:\n")
                    f.write("- Profile slow tests to identify bottlenecks\n")
                    f.write("- Consider using pytest fixtures to reduce setup time\n")
                    f.write("- Mock external dependencies (DB, API calls, file I/O)\n")
                    f.write("- Use pytest-xdist for parallel test execution\n")
                else:
                    f.write(f"✅ No tests exceed {threshold}s threshold!\n\n")

                    # Still show fastest tests for context
                    all_tests = self._parse_all_durations(result.stdout)
                    if all_tests:
                        all_tests.sort(key=lambda x: x[1], reverse=True)
                        f.write("Top 10 longest tests (all under threshold):\n\n")
                        f.write(f"{'Duration (s)':<15} {'Test'}\n")
                        f.write("-" * 70 + "\n")
                        for test_name, duration in all_tests[:10]:
                            f.write(f"{duration:>13.2f}  {test_name}\n")

                # Append raw duration output for reference
                f.write("\n" + "=" * 70 + "\n")
                f.write("RAW PYTEST DURATION OUTPUT:\n")
                f.write("-" * 70 + "\n")
                # Find and include the duration section
                in_duration_section = False
                for line in result.stdout.splitlines():
                    if "slowest durations" in line.lower() or "=== " in line:
                        in_duration_section = True
                    if in_duration_section:
                        f.write(line + "\n")

            elapsed = int((time.time() - start) * 1000)

            if slow_tests:
                return StepResult(
                    self.name, "OK", elapsed, f"{len(slow_tests)} slow tests"
                )
            else:
                return StepResult(self.name, "OK", elapsed)

        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))

    def _parse_durations(
        self, output: str, threshold: float
    ) -> list[tuple[str, float]]:
        """Parse pytest --durations output for tests exceeding threshold"""
        slow_tests = []

        # Look for duration lines like: "0.52s call     test_file.py::test_name"
        for line in output.splitlines():
            if "s call" in line or "s setup" in line or "s teardown" in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        duration_str = parts[0].rstrip("s")
                        duration = float(duration_str)

                        if duration >= threshold:
                            # Extract test name (usually the last part)
                            test_name = parts[-1]
                            slow_tests.append((test_name, duration))
                    except (ValueError, IndexError):
                        continue

        return slow_tests

    def _parse_all_durations(self, output: str) -> list[tuple[str, float]]:
        """Parse all test durations"""
        all_tests = []

        for line in output.splitlines():
            if "s call" in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        duration_str = parts[0].rstrip("s")
                        duration = float(duration_str)
                        test_name = parts[-1]
                        all_tests.append((test_name, duration))
                    except (ValueError, IndexError):
                        continue

        return all_tests
