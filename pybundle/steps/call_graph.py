"""
Step: Call Graph Generation
Generate static call graph and identify orphaned functions.
"""

import ast
from pathlib import Path
from typing import Dict, List, Set

from .base import Step, StepResult


class CallGraphStep(Step):
    """Generate static call graph and identify orphaned functions."""

    name = "call graph"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze function definitions and calls to build call graph."""
        import time

        start = time.time()

        root = ctx.root
        python_files = sorted(root.rglob("*.py"))
        if not python_files:
            return StepResult(self.name, "SKIP", int(time.time() - start), "No Python files found")

        # Track functions
        defined_functions: Dict[str, str] = {}  # func_name -> file:line
        called_functions: Set[str] = set()  # func_name
        function_calls: Dict[str, List[str]] = {}  # func_name -> [called_func, ...]
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
                rel_path = py_file.relative_to(root)

                # Find function definitions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        # Skip private and magic methods
                        if not func_name.startswith("_"):
                            location = f"{rel_path}:{node.lineno}"
                            defined_functions[func_name] = location
                            
                            # Track calls within this function
                            calls = self._extract_function_calls(node)
                            if func_name not in function_calls:
                                function_calls[func_name] = []
                            function_calls[func_name].extend(calls)
                            called_functions.update(calls)

            except (SyntaxError, UnicodeDecodeError):
                continue

        # Identify orphaned functions (defined but never called)
        orphaned = set(defined_functions.keys()) - called_functions

        # Identify entry points (called but not defined in codebase)
        external_calls = called_functions - set(defined_functions.keys())

        # Calculate statistics
        total_functions = len(defined_functions)
        total_calls = sum(len(calls) for calls in function_calls.values())

        # Generate report
        lines = [
            "=" * 80,
            "CALL GRAPH ANALYSIS",
            "=" * 80,
            "",
            f"Total Python files analyzed: {analyzed_files}",
            f"Total functions defined: {total_functions}",
            f"Total function calls: {total_calls}",
            f"Orphaned functions (never called): {len(orphaned)}",
            f"External/library calls: {len(external_calls)}",
            "",
        ]

        # Orphaned functions
        if orphaned:
            lines.extend(
                [
                    "=" * 80,
                    "ORPHANED FUNCTIONS (defined but never called)",
                    "=" * 80,
                    "",
                ]
            )
            for func in sorted(orphaned):
                location = defined_functions[func]
                lines.append(f"  {func:30} at {location}")
            lines.append("")

        # Most called functions
        if function_calls:
            # Count how many times each function is called
            call_counts: Dict[str, int] = {}
            for calls in function_calls.values():
                for called_func in calls:
                    call_counts[called_func] = call_counts.get(called_func, 0) + 1

            # Filter to only defined functions
            internal_call_counts = {
                func: count
                for func, count in call_counts.items()
                if func in defined_functions
            }

            if internal_call_counts:
                lines.extend(
                    [
                        "=" * 80,
                        "MOST CALLED FUNCTIONS (top 20)",
                        "=" * 80,
                        "",
                    ]
                )

                sorted_calls = sorted(
                    internal_call_counts.items(), key=lambda x: x[1], reverse=True
                )
                for func, count in sorted_calls[:20]:
                    location = defined_functions[func]
                    lines.append(f"  {func:30} {count:4} call(s) at {location}")
                lines.append("")

        # Functions that call many others
        if function_calls:
            lines.extend(
                [
                    "=" * 80,
                    "FUNCTIONS WITH MOST CALLS (top 20)",
                    "=" * 80,
                    "",
                ]
            )

            sorted_callers = sorted(
                function_calls.items(), key=lambda x: len(x[1]), reverse=True
            )
            for func, calls in sorted_callers[:20]:
                if func in defined_functions:
                    location = defined_functions[func]
                    unique_calls = len(set(calls))
                    lines.append(
                        f"  {func:30} calls {unique_calls:3} function(s) at {location}"
                    )
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

        if len(orphaned) > 10:
            lines.append(f"  - {len(orphaned)} orphaned functions found; consider removing unused code")
        if len(orphaned) > 0:
            lines.append("  - Review orphaned functions for dead code removal")
        if total_functions > 0:
            orphan_pct = len(orphaned) / total_functions * 100
            if orphan_pct > 30:
                lines.append(f"  - {orphan_pct:.1f}% of functions are never called")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "103_call_graph.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _extract_function_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract all function calls within a function definition."""
        calls = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node.func)
                if func_name and not func_name.startswith("_"):
                    calls.append(func_name)
        return calls

    def _get_call_name(self, node: ast.expr) -> str:
        """Extract function name from call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # For method calls, just return the method name
            return node.attr
        return ""
