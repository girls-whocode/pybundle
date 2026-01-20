"""
Step: Exception Pattern Tracking
Track all raise statements and categorize exception types.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

from .base import Step, StepResult


class ExceptionPatternsStep(Step):
    """Analyze exception patterns and raise statements in Python code."""

    name = "exception patterns"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Find all raise statements and categorize exception types."""
        import time

        start = time.time()

        root = ctx.root
        python_files = sorted(root.rglob("*.py"))
        if not python_files:
            return StepResult(self.name, "SKIP", int(time.time() - start), "No Python files found")

        # Track exception patterns
        exception_types: Dict[str, List[str]] = {}  # exception_type -> [file:line, ...]
        custom_exceptions: Set[str] = set()
        bare_raises = []  # re-raise without argument
        exception_chaining = []  # raise ... from ...
        analyzed_files = 0

        for py_file in python_files:
            # Skip non-user code
            if any(
                part in py_file.parts
                for part in [
                    "venv",
                    ".venv",
                    "env",
                    "site-packages",
                    "__pycache__",
                    ".git",
                    "node_modules",
                ]
            ):
                continue

            analyzed_files += 1

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, str(py_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.Raise):
                        rel_path = py_file.relative_to(root)
                        location = f"{rel_path}:{node.lineno}"

                        if node.exc is None:
                            # Bare raise (re-raise)
                            bare_raises.append(location)
                        else:
                            # Extract exception type
                            exc_type = self._extract_exception_type(node.exc)
                            if exc_type:
                                if exc_type not in exception_types:
                                    exception_types[exc_type] = []
                                exception_types[exc_type].append(location)

                                # Check if it's a custom exception (not in builtins)
                                if exc_type not in dir(__builtins__) and not exc_type.startswith(
                                    ("OSError", "IOError", "ValueError", "TypeError", "RuntimeError")
                                ):
                                    custom_exceptions.add(exc_type)

                        # Check for exception chaining (raise ... from ...)
                        if node.cause is not None:
                            exception_chaining.append(location)

            except (SyntaxError, UnicodeDecodeError):
                continue

        # Generate report
        lines = [
            "=" * 80,
            "EXCEPTION PATTERN ANALYSIS",
            "=" * 80,
            "",
            f"Total Python files analyzed: {analyzed_files}",
            f"Total exception types found: {len(exception_types)}",
            f"Custom exceptions: {len(custom_exceptions)}",
            f"Bare raises (re-raise): {len(bare_raises)}",
            f"Exception chaining (raise...from): {len(exception_chaining)}",
            "",
        ]

        # Exception type breakdown
        if exception_types:
            lines.extend(
                [
                    "=" * 80,
                    "EXCEPTION TYPES (sorted by frequency)",
                    "=" * 80,
                    "",
                ]
            )

            sorted_exceptions = sorted(exception_types.items(), key=lambda x: len(x[1]), reverse=True)
            for exc_type, locations in sorted_exceptions:
                lines.append(f"{exc_type}: {len(locations)} occurrence(s)")
                for loc in locations[:5]:  # Show first 5 locations
                    lines.append(f"  - {loc}")
                if len(locations) > 5:
                    lines.append(f"  ... and {len(locations) - 5} more")
                lines.append("")

        # Custom exceptions
        if custom_exceptions:
            lines.extend(
                [
                    "=" * 80,
                    "CUSTOM EXCEPTIONS",
                    "=" * 80,
                    "",
                ]
            )
            for exc in sorted(custom_exceptions):
                lines.append(f"  - {exc}")
            lines.append("")

        # Bare raises
        if bare_raises:
            lines.extend(
                [
                    "=" * 80,
                    "BARE RAISES (re-raise without argument)",
                    "=" * 80,
                    "",
                ]
            )
            for loc in bare_raises:
                lines.append(f"  - {loc}")
            lines.append("")

        # Exception chaining
        if exception_chaining:
            lines.extend(
                [
                    "=" * 80,
                    "EXCEPTION CHAINING (raise...from)",
                    "=" * 80,
                    "",
                ]
            )
            for loc in exception_chaining:
                lines.append(f"  - {loc}")
            lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "101_exception_patterns.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _extract_exception_type(self, node: ast.expr) -> str:
        """Extract exception type name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            # Exception instantiation: ValueError("msg")
            return self._extract_exception_type(node.func)
        elif isinstance(node, ast.Attribute):
            # Module exception: module.ExceptionType
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.insert(0, current.id)
            return ".".join(parts)
        return "Unknown"
