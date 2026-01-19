"""Type hint coverage analysis step.

Analyzes Python source files to compute type annotation coverage percentage,
identifying functions/methods/classes that lack type hints.
"""

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .base import StepResult
from ..context import BundleContext


@dataclass
class TypeCoverageStats:
    """Type coverage statistics."""

    total_functions: int = 0
    typed_functions: int = 0
    total_classes: int = 0
    typed_classes: int = 0
    total_attributes: int = 0
    typed_attributes: int = 0
    missing_items: List[Tuple[str, int, str]] = None  # (file, line, name)

    def __post_init__(self):
        if self.missing_items is None:
            self.missing_items = []

    @property
    def function_coverage(self) -> float:
        """Return function type coverage percentage."""
        if self.total_functions == 0:
            return 100.0
        return (self.typed_functions / self.total_functions) * 100

    @property
    def class_coverage(self) -> float:
        """Return class type coverage percentage."""
        if self.total_classes == 0:
            return 100.0
        return (self.typed_classes / self.total_classes) * 100

    @property
    def attribute_coverage(self) -> float:
        """Return attribute type coverage percentage."""
        if self.total_attributes == 0:
            return 100.0
        return (self.typed_attributes / self.total_attributes) * 100

    @property
    def overall_coverage(self) -> float:
        """Return overall type coverage percentage."""
        total = self.total_functions + self.total_classes + self.total_attributes
        typed = self.typed_functions + self.typed_classes + self.typed_attributes
        if total == 0:
            return 100.0
        return (typed / total) * 100


class TypeCoverageAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing type coverage."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.stats = TypeCoverageStats()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(self, node):
        """Analyze function/method for type hints."""
        # Skip special methods and private methods
        if node.name.startswith("_") and not node.name.startswith("__"):
            return

        self.stats.total_functions += 1

        # Check if function has type hints
        has_return_type = node.returns is not None
        has_param_types = all(
            arg.annotation is not None
            for arg in node.args.args
            if arg.arg not in ("self", "cls")
        )

        if has_return_type and (has_param_types or len([a for a in node.args.args if a.arg not in ("self", "cls")]) == 0):
            self.stats.typed_functions += 1
        else:
            self.stats.missing_items.append(
                (self.filepath, node.lineno, f"function '{node.name}'")
            )

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        # Skip private classes
        if node.name.startswith("_"):
            self.generic_visit(node)
            return

        self.stats.total_classes += 1

        # Check if class has any type-hinted attributes
        has_annotations = any(
            isinstance(stmt, ast.AnnAssign) for stmt in node.body
        )

        # Check __init__ for parameter types
        init_method = None
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
                init_method = stmt
                break

        if init_method:
            has_init_types = any(
                arg.annotation is not None
                for arg in init_method.args.args
                if arg.arg not in ("self", "cls")
            )
            if has_annotations or has_init_types:
                self.stats.typed_classes += 1
            else:
                self.stats.missing_items.append(
                    (self.filepath, node.lineno, f"class '{node.name}'")
                )
        else:
            # Class without __init__ - check for annotated attributes
            if has_annotations:
                self.stats.typed_classes += 1
            else:
                self.stats.missing_items.append(
                    (self.filepath, node.lineno, f"class '{node.name}'")
                )

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit annotated assignment (class/module level)."""
        # Count as typed attribute
        self.stats.total_attributes += 1
        self.stats.typed_attributes += 1
        self.generic_visit(node)


@dataclass
class TypeCoverageStep:
    """Step that analyzes type hint coverage."""

    name: str = "type-coverage"
    outfile: str = "logs/80_type_coverage.txt"

    def run(self, context: BundleContext) -> StepResult:
        """Analyze type coverage in Python files."""
        import time

        start = time.time()

        # Get all Python files in the project
        python_files = self._find_python_files(context.root)

        if not python_files:
            elapsed = time.time() - start
            note = "No Python files found"
            return StepResult(self.name, "SKIP", elapsed, note)

        # Analyze all files
        overall_stats = TypeCoverageStats()

        for filepath in python_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source, filename=str(filepath))
                analyzer = TypeCoverageAnalyzer(str(filepath))
                analyzer.visit(tree)

                # Merge stats
                overall_stats.total_functions += analyzer.stats.total_functions
                overall_stats.typed_functions += analyzer.stats.typed_functions
                overall_stats.total_classes += analyzer.stats.total_classes
                overall_stats.typed_classes += analyzer.stats.typed_classes
                overall_stats.total_attributes += analyzer.stats.total_attributes
                overall_stats.typed_attributes += analyzer.stats.typed_attributes
                overall_stats.missing_items.extend(analyzer.stats.missing_items)

            except SyntaxError:
                # Skip files with syntax errors
                continue
            except Exception:
                # Skip files that can't be parsed
                continue

        elapsed = time.time() - start

        # Write report
        log_path = context.workdir / self.outfile
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("TYPE HINT COVERAGE ANALYSIS\n")
            f.write("=" * 80 + "\n\n")

            f.write("Summary:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Overall Coverage:    {overall_stats.overall_coverage:6.2f}%\n")
            f.write(f"Function Coverage:   {overall_stats.function_coverage:6.2f}% "
                   f"({overall_stats.typed_functions}/{overall_stats.total_functions})\n")
            f.write(f"Class Coverage:      {overall_stats.class_coverage:6.2f}% "
                   f"({overall_stats.typed_classes}/{overall_stats.total_classes})\n")
            f.write(f"Attribute Coverage:  {overall_stats.attribute_coverage:6.2f}% "
                   f"({overall_stats.typed_attributes}/{overall_stats.total_attributes})\n")
            f.write("\n")

            if overall_stats.missing_items:
                f.write("Missing Type Hints:\n")
                f.write("-" * 80 + "\n")

                # Sort by file, then line number
                sorted_missing = sorted(overall_stats.missing_items, key=lambda x: (x[0], x[1]))

                current_file = None
                for filepath, lineno, name in sorted_missing:
                    # Show relative path
                    rel_path = os.path.relpath(filepath, context.root)
                    if rel_path != current_file:
                        f.write(f"\n{rel_path}:\n")
                        current_file = rel_path
                    f.write(f"  Line {lineno:4d}: {name}\n")

                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write(f"Analysis complete - {len(python_files)} files analyzed\n")
            f.write("=" * 80 + "\n")

        # Determine status
        coverage = overall_stats.overall_coverage
        if coverage >= 80:
            status = "OK"
        elif coverage >= 50:
            status = "WARN"
        else:
            status = "FAIL"

        note = f"{coverage:.1f}% type coverage"
        return StepResult(self.name, status, elapsed, note)

    def _find_python_files(self, root: Path) -> List[Path]:
        """Find all Python source files, excluding common directories."""
        python_files = []
        exclude_dirs = {
            "__pycache__",
            ".git",
            ".tox",
            "venv",
            "env",
            ".venv",
            ".env",
            "node_modules",
            "artifacts",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "htmlcov",
            ".coverage",
        }

        for path in root.rglob("*.py"):
            # Skip if any parent is in exclude_dirs
            if any(part in exclude_dirs for part in path.parts):
                continue
            python_files.append(path)

        return python_files
