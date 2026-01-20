"""
Step: AsyncIO Task Analysis
Static analysis of async/await patterns in codebase.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class AsyncioAnalysisStep(Step):
    """Analyze async/await patterns in Python code."""

    name = "asyncio analysis"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze asyncio usage and patterns."""
        import time

        start = time.time()

        root = ctx.root

        # Find all async definitions
        async_funcs = self._find_async_functions(root)

        # Analyze async patterns
        patterns = self._analyze_async_patterns(root, async_funcs)

        # Generate report
        lines = [
            "=" * 80,
            "ASYNCIO ANALYSIS REPORT",
            "=" * 80,
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"Async functions found: {len(async_funcs['all_async'])}",
                f"Coroutines: {len(async_funcs['coroutines'])}",
                f"Async generators: {len(async_funcs['async_generators'])}",
                f"Async context managers: {len(async_funcs['async_context_managers'])}",
                "",
            ]
        )

        if not async_funcs["all_async"]:
            lines.extend(
                [
                    "⊘ No async code detected in project",
                    "",
                    "This project does not appear to use asyncio patterns.",
                    "If this is incorrect, ensure async functions are in analyzed files.",
                    "",
                ]
            )
        else:
            # Detailed breakdown
            lines.extend(
                [
                    "ASYNC FUNCTIONS BY TYPE",
                    "=" * 80,
                    "",
                ]
            )

            if async_funcs["coroutines"]:
                lines.append(f"COROUTINES ({len(async_funcs['coroutines'])}):")
                for file_path, func_name, line_no in sorted(
                    async_funcs["coroutines"], key=lambda x: (x[0], x[2])
                )[:20]:
                    lines.append(f"  {file_path}:{line_no} - {func_name}")
                if len(async_funcs["coroutines"]) > 20:
                    lines.append(f"  ... and {len(async_funcs['coroutines']) - 20} more")
                lines.append("")

            if async_funcs["async_generators"]:
                lines.append(f"ASYNC GENERATORS ({len(async_funcs['async_generators'])}):")
                for file_path, func_name, line_no in sorted(
                    async_funcs["async_generators"], key=lambda x: (x[0], x[2])
                )[:20]:
                    lines.append(f"  {file_path}:{line_no} - {func_name}")
                if len(async_funcs["async_generators"]) > 20:
                    lines.append(
                        f"  ... and {len(async_funcs['async_generators']) - 20} more"
                    )
                lines.append("")

            if async_funcs["async_context_managers"]:
                lines.append(
                    f"ASYNC CONTEXT MANAGERS ({len(async_funcs['async_context_managers'])}):"
                )
                for file_path, func_name, line_no in sorted(
                    async_funcs["async_context_managers"], key=lambda x: (x[0], x[2])
                )[:20]:
                    lines.append(f"  {file_path}:{line_no} - {func_name}")
                if len(async_funcs["async_context_managers"]) > 20:
                    lines.append(
                        f"  ... and {len(async_funcs['async_context_managers']) - 20} more"
                    )
                lines.append("")

        # Pattern analysis
        if async_funcs["all_async"]:
            lines.extend(
                [
                    "=" * 80,
                    "ASYNC PATTERNS",
                    "=" * 80,
                    "",
                ]
            )

            if patterns["missing_awaits"]:
                lines.append(
                    f"⚠ POTENTIAL MISSING AWAITS ({len(patterns['missing_awaits'])}):"
                )
                for item in patterns["missing_awaits"][:15]:
                    lines.append(f"  {item['file']}:{item['line']}")
                    if item.get("context"):
                        context_line = item["context"].strip()
                        if len(context_line) > 70:
                            context_line = context_line[:67] + "..."
                        lines.append(f"    > {context_line}")
                if len(patterns["missing_awaits"]) > 15:
                    lines.append(
                        f"  ... and {len(patterns['missing_awaits']) - 15} more"
                    )
                lines.append("")
            else:
                lines.append("✓ No obvious missing await calls detected")
                lines.append("")

            if patterns["async_context_managers"]:
                lines.append(
                    f"✓ ASYNC CONTEXT MANAGERS ({len(patterns['async_context_managers'])}):"
                )
                for item in patterns["async_context_managers"][:10]:
                    lines.append(f"  {item}")
                if len(patterns["async_context_managers"]) > 10:
                    lines.append(
                        f"  ... and {len(patterns['async_context_managers']) - 10} more"
                    )
                lines.append("")

            # Python version features
            lines.extend(
                [
                    "PYTHON 3.9+ FEATURES",
                    "=" * 80,
                    "",
                ]
            )

            if patterns["taskgroup_usage"]:
                lines.append(f"✓ TaskGroup usage (Python 3.11+): {len(patterns['taskgroup_usage'])}")
                for item in patterns["taskgroup_usage"][:5]:
                    lines.append(f"  {item}")
                lines.append("")
            else:
                lines.append("ℹ No TaskGroup usage (available in Python 3.11+)")
                lines.append("")

            if patterns["exception_groups"]:
                lines.append(f"✓ Exception Groups usage: {len(patterns['exception_groups'])}")
                for item in patterns["exception_groups"][:5]:
                    lines.append(f"  {item}")
                lines.append("")
            else:
                lines.append("ℹ No exception groups detected")
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

        if async_funcs["all_async"]:
            if patterns["missing_awaits"]:
                lines.append("  - Review potential missing await calls marked above")
                lines.append("  - Use linters (ruff, pylint) with async checks enabled")
            else:
                lines.append("  - ✓ Good: No obvious missing awaits detected")

            lines.append("  - Use asyncio.gather() for concurrent execution")
            lines.append("  - Prefer TaskGroup (Python 3.11+) for structured concurrency")
            lines.append("  - Use asyncio.timeout() for deadline management")
            lines.append("  - Avoid blocking calls (use async equivalents)")
            lines.append("  - Use pytest-asyncio for testing async code")
        else:
            lines.append("  - No async code detected")
            lines.append("  - If planning to add asyncio, use structured concurrency patterns")
            lines.append("  - Consider asyncio for I/O-bound operations")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "130_async_analysis.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_async_functions(self, root: Path) -> Dict[str, List[Tuple[str, str, int]]]:
        """Find all async function definitions."""
        coroutines = []
        async_generators = []
        async_context_managers = []

        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            # Skip venv and cache
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(root))

                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef):
                        func_name = node.name
                        line_no = node.lineno

                        # Determine type by checking for yield/yield from
                        has_yield = any(
                            isinstance(n, (ast.Yield, ast.YieldFrom))
                            for n in ast.walk(node)
                        )

                        if has_yield:
                            async_generators.append((rel_path, func_name, line_no))
                        elif func_name.startswith("__aenter__") or func_name.startswith(
                            "__aexit__"
                        ):
                            async_context_managers.append((rel_path, func_name, line_no))
                        else:
                            coroutines.append((rel_path, func_name, line_no))

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        all_async = coroutines + async_generators + async_context_managers

        return {
            "all_async": all_async,
            "coroutines": coroutines,
            "async_generators": async_generators,
            "async_context_managers": async_context_managers,
        }

    def _analyze_async_patterns(self, root: Path, async_funcs: Dict) -> Dict:
        """Analyze async patterns and best practices."""
        missing_awaits = []
        async_context_managers = []
        taskgroup_usage = []
        exception_groups = []

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

                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef):
                        # Check for missing awaits
                        for call_node in ast.walk(node):
                            if isinstance(call_node, ast.Call):
                                # Check if it's a coroutine call without await
                                if isinstance(call_node.func, ast.Name):
                                    func_name = call_node.func.id
                                    # Look for common async functions not being awaited
                                    if func_name in [
                                        "sleep",
                                        "gather",
                                        "create_task",
                                    ] or any(
                                        n[1] == func_name
                                        for n in async_funcs["all_async"]
                                    ):
                                        # Check if parent is not Await
                                        if not any(
                                            isinstance(p, ast.Await)
                                            for p in ast.walk(node)
                                            if call_node in list(ast.walk(p))
                                        ):
                                            # This is a simple heuristic
                                            context = source.split("\n")[
                                                call_node.lineno - 1
                                            ]
                                            missing_awaits.append(
                                                {
                                                    "file": rel_path,
                                                    "line": call_node.lineno,
                                                    "context": context,
                                                }
                                            )

                        # Check for async with
                        for stmt in ast.walk(node):
                            if isinstance(stmt, ast.AsyncWith):
                                async_context_managers.append(
                                    f"{rel_path}:{node.lineno}"
                                )

                # Global patterns
                for line_num, line in enumerate(source.split("\n"), 1):
                    if "TaskGroup" in line:
                        taskgroup_usage.append(f"{rel_path}:{line_num}")

                    if "ExceptionGroup" in line:
                        exception_groups.append(f"{rel_path}:{line_num}")

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Deduplicate
        async_context_managers = list(set(async_context_managers))
        taskgroup_usage = list(set(taskgroup_usage))
        exception_groups = list(set(exception_groups))

        return {
            "missing_awaits": missing_awaits,
            "async_context_managers": async_context_managers,
            "taskgroup_usage": taskgroup_usage,
            "exception_groups": exception_groups,
        }
