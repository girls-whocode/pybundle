"""
Step: Event Loop Patterns Analysis
Analyze event loop creation and usage patterns.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class EventLoopPatternsStep(Step):
    """Analyze event loop patterns and best practices."""

    name = "event loop patterns"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze event loop patterns in codebase."""
        import time

        start = time.time()

        root = ctx.root

        # Find event loop patterns
        patterns = self._find_event_loop_patterns(root)

        # Generate report
        lines = [
            "=" * 80,
            "EVENT LOOP PATTERNS ANALYSIS REPORT",
            "=" * 80,
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"Event loop creations found: {len(patterns['asyncio_run'])}",
                f"get_event_loop() calls: {len(patterns['get_event_loop'])}",
                f"new_event_loop() calls: {len(patterns['new_event_loop'])}",
                f"Event loop close() calls: {len(patterns['close'])}",
                "",
            ]
        )

        if not patterns["has_async"]:
            lines.extend(
                [
                    "⊘ No event loop patterns detected",
                    "",
                    "This project does not appear to use explicit event loop management.",
                    "If this is incorrect, ensure asyncio code is in analyzed files.",
                    "",
                ]
            )
        else:
            # Event loop creation patterns
            lines.extend(
                [
                    "EVENT LOOP CREATION PATTERNS",
                    "=" * 80,
                    "",
                ]
            )

            if patterns["asyncio_run"]:
                lines.append("✓ ASYNCIO.RUN (Recommended - Python 3.7+):")
                lines.append("  Creates and closes event loop automatically")
                for item in patterns["asyncio_run"][:10]:
                    lines.append(f"    {item}")
                if len(patterns["asyncio_run"]) > 10:
                    lines.append(f"    ... and {len(patterns['asyncio_run']) - 10} more")
                lines.append("")

            if patterns["get_event_loop"]:
                lines.append("⚠ GET_EVENT_LOOP (Legacy Pattern):")
                lines.append("  Deprecated in Python 3.10+, can raise DeprecationWarning")
                for item in patterns["get_event_loop"][:10]:
                    lines.append(f"    {item}")
                if len(patterns["get_event_loop"]) > 10:
                    lines.append(f"    ... and {len(patterns['get_event_loop']) - 10} more")
                lines.append("")

            if patterns["new_event_loop"]:
                lines.append("⚠ NEW_EVENT_LOOP (Manual Management):")
                lines.append("  Less convenient than asyncio.run(), requires explicit close()")
                for item in patterns["new_event_loop"][:10]:
                    lines.append(f"    {item}")
                if len(patterns["new_event_loop"]) > 10:
                    lines.append(f"    ... and {len(patterns['new_event_loop']) - 10} more")
                lines.append("")

            # Resource management
            lines.extend(
                [
                    "RESOURCE MANAGEMENT",
                    "=" * 80,
                    "",
                ]
            )

            if patterns["close"]:
                lines.append(f"✓ Event loop close() calls: {len(patterns['close'])}")
            else:
                if patterns["get_event_loop"] or patterns["new_event_loop"]:
                    lines.append("⚠ No explicit loop.close() calls found")
                    lines.append("  Event loops created with get_event_loop() or new_event_loop()")
                    lines.append("  should be explicitly closed to avoid resource leaks")
                else:
                    lines.append("ℹ No explicit close() calls needed (using asyncio.run)")

            lines.append("")

            # Best practices
            lines.extend(
                [
                    "BEST PRACTICES ANALYSIS",
                    "=" * 80,
                    "",
                ]
            )

            # Check Python version requirement
            lines.append("Python Version Compatibility:")
            lines.append("")

            if patterns["asyncio_run"]:
                lines.append("  ✓ asyncio.run() requires Python 3.7+")
                lines.append("    Check pyproject.toml requires-python >= 3.7")
            else:
                lines.append("  ℹ No asyncio.run() usage found")

            lines.append("")

            # Running mode
            if patterns["asyncio_run"] and not patterns["get_event_loop"]:
                lines.append("  ✓ Consistent event loop pattern (asyncio.run)")
            elif patterns["get_event_loop"] and not patterns["asyncio_run"]:
                lines.append("  ⚠ Using legacy get_event_loop() pattern")
                lines.append("    Consider migrating to asyncio.run() for clarity")
            elif patterns["asyncio_run"] and patterns["get_event_loop"]:
                lines.append("  ⚠ Mixed event loop patterns (both asyncio.run and get_event_loop)")
                lines.append("    Consider standardizing on asyncio.run()")

            lines.append("")

            # Context managers
            if patterns["async_with_count"] > 0:
                lines.append(f"  ✓ Using async with statements: {patterns['async_with_count']} instances")
            else:
                if patterns["has_async"]:
                    lines.append("  ℹ No async with statements found")

            lines.append("")

        # Recommendations
        lines.extend(
            [
                "=" * 80,
                "RECOMMENDATIONS",
                "=" * 80,
                "",
            ]
        )

        if patterns["has_async"]:
            if patterns["get_event_loop"] and not patterns["asyncio_run"]:
                lines.append("  1. Migrate from get_event_loop() to asyncio.run()")
                lines.append("")
                lines.append("     Before (Python 3.7-3.9):")
                lines.append("       loop = asyncio.get_event_loop()")
                lines.append("       try:")
                lines.append("           loop.run_until_complete(main())")
                lines.append("       finally:")
                lines.append("           loop.close()")
                lines.append("")
                lines.append("     After (Python 3.7+):")
                lines.append("       asyncio.run(main())")
                lines.append("")

            lines.append("  - Use asyncio.run() as entry point (automatically manages loop)")
            lines.append("  - Use async with for resource management in async code")
            lines.append("  - Avoid get_event_loop() except in special cases")
            lines.append("  - Consider asyncio.Runner for multiple runs (Python 3.11+)")
            lines.append("  - Document asyncio requirements in README")

        else:
            lines.append("  - No event loop patterns detected in code")
            lines.append("  - If planning to use asyncio, use asyncio.run() as main entry point")
            lines.append("  - Review async best practices: https://docs.python.org/3/library/asyncio-dev.html")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "132_event_loop_patterns.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_event_loop_patterns(self, root: Path) -> Dict:
        """Find event loop creation and usage patterns."""
        asyncio_run = []
        get_event_loop = []
        new_event_loop = []
        close = []
        async_with_count = 0
        has_async = False

        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(root))

                # Check for async keyword
                if "async " in source:
                    has_async = True

                tree = ast.parse(source)

                # Count async context managers
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncWith):
                        async_with_count += 1

                # Find event loop patterns via source regex (for robustness)
                for line_num, line in enumerate(source.split("\n"), 1):
                    # asyncio.run() pattern
                    if re.search(r"asyncio\.run\s*\(", line):
                        asyncio_run.append(f"{rel_path}:{line_num}")

                    # get_event_loop() pattern
                    if re.search(
                        r"asyncio\.get_event_loop\s*\(|get_event_loop\s*\(", line
                    ):
                        get_event_loop.append(f"{rel_path}:{line_num}")

                    # new_event_loop() pattern
                    if re.search(
                        r"asyncio\.new_event_loop\s*\(|new_event_loop\s*\(", line
                    ):
                        new_event_loop.append(f"{rel_path}:{line_num}")

                    # close() pattern
                    if re.search(r"(loop|event_loop)\.close\s*\(", line):
                        close.append(f"{rel_path}:{line_num}")

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Deduplicate
        asyncio_run = list(set(asyncio_run))
        get_event_loop = list(set(get_event_loop))
        new_event_loop = list(set(new_event_loop))
        close = list(set(close))

        return {
            "asyncio_run": sorted(asyncio_run),
            "get_event_loop": sorted(get_event_loop),
            "new_event_loop": sorted(new_event_loop),
            "close": sorted(close),
            "async_with_count": async_with_count,
            "has_async": has_async,
        }
