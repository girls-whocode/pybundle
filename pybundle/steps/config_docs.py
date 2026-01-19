"""Configuration documentation step.

Extracts and documents environment variables and configuration options
from Python source code.
"""

import ast
import re
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext


class ConfigVarExtractor(ast.NodeVisitor):
    """AST visitor for extracting environment variable accesses."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.env_vars: List[Tuple[int, str, str]] = []  # (line, var_name, default)

    def visit_Call(self, node: ast.Call):
        """Visit function calls looking for os.getenv, os.environ.get, etc."""
        # Check for os.getenv(var, default) or os.environ.get(var, default)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("getenv", "get"):
                # Check if it's os.getenv or os.environ.get
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "os":
                        self._extract_env_var(node)
                elif isinstance(node.func.value, ast.Attribute):
                    if (
                        node.func.value.attr == "environ"
                        and isinstance(node.func.value.value, ast.Name)
                        and node.func.value.value.id == "os"
                    ):
                        self._extract_env_var(node)

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        """Visit subscript operations like os.environ['VAR']."""
        if isinstance(node.value, ast.Attribute):
            if (
                node.value.attr == "environ"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
            ):
                if isinstance(node.slice, ast.Constant):
                    var_name = node.slice.value
                    if isinstance(var_name, str):
                        self.env_vars.append((node.lineno, var_name, None))

        self.generic_visit(node)

    def _extract_env_var(self, node: ast.Call):
        """Extract environment variable from getenv/get call."""
        if len(node.args) >= 1:
            # First argument is the variable name
            if isinstance(node.args[0], ast.Constant):
                var_name = node.args[0].value
                if isinstance(var_name, str):
                    # Check for default value
                    default = None
                    if len(node.args) >= 2:
                        if isinstance(node.args[1], ast.Constant):
                            default = repr(node.args[1].value)
                        else:
                            default = "<expression>"

                    self.env_vars.append((node.lineno, var_name, default))


@dataclass
class ConfigDocumentationStep:
    """Step that documents configuration variables."""

    name: str = "config-docs"
    outfile: str = "meta/83_config_vars.txt"

    def run(self, context: BundleContext) -> StepResult:
        """Extract and document configuration variables."""
        start = time.time()

        # Find all Python files
        python_files = self._find_python_files(context.root)

        if not python_files:
            elapsed = time.time() - start
            note = "No Python files found"
            return StepResult(self.name, "SKIP", elapsed, note)

        # Extract environment variables from code
        env_vars = self._extract_env_vars(python_files, context.root)

        # Look for config files
        config_files = self._find_config_files(context.root)

        # Parse config file patterns
        config_patterns = self._extract_config_patterns(config_files, context.root)

        elapsed = time.time() - start

        # Write report
        log_path = context.workdir / self.outfile
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("CONFIGURATION DOCUMENTATION\n")
            f.write("=" * 80 + "\n\n")

            # Environment variables section
            if env_vars:
                f.write("Environment Variables Used:\n")
                f.write("-" * 80 + "\n\n")

                # Group by variable name
                vars_grouped: Dict[str, List[Tuple[str, int, str]]] = {}
                for filepath, lineno, var_name, default in env_vars:
                    if var_name not in vars_grouped:
                        vars_grouped[var_name] = []
                    vars_grouped[var_name].append((filepath, lineno, default))

                # Sort by variable name
                for var_name in sorted(vars_grouped.keys()):
                    locations = vars_grouped[var_name]
                    f.write(f"{var_name}\n")

                    # Show default if consistent
                    defaults = [d for _, _, d in locations if d is not None]
                    if defaults:
                        if len(set(defaults)) == 1:
                            f.write(f"  Default: {defaults[0]}\n")
                        else:
                            f.write(f"  Defaults: {', '.join(set(defaults))}\n")

                    f.write("  Used in:\n")
                    for filepath, lineno, _ in sorted(locations, key=lambda x: (x[0], x[1])):
                        f.write(f"    {filepath}:{lineno}\n")

                    f.write("\n")

                f.write(f"Total: {len(vars_grouped)} unique environment variables\n\n")
            else:
                f.write("No environment variables found in source code.\n\n")

            # Configuration files section
            if config_files:
                f.write("Configuration Files:\n")
                f.write("-" * 80 + "\n")
                for config_file in sorted(config_files):
                    f.write(f"  {config_file}\n")
                f.write("\n")

            # Configuration patterns section
            if config_patterns:
                f.write("Configuration Patterns Detected:\n")
                f.write("-" * 80 + "\n")
                for pattern, locations in sorted(config_patterns.items()):
                    f.write(f"\n{pattern}\n")
                    for filepath, lineno in locations[:5]:  # Limit to 5
                        f.write(f"  {filepath}:{lineno}\n")
                    if len(locations) > 5:
                        f.write(f"  ... and {len(locations) - 5} more\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("Configuration documentation complete\n")
            f.write("=" * 80 + "\n")

        # Determine status
        total_items = len(env_vars) + len(config_patterns)
        if total_items > 0:
            status = "OK"
            note = f"Found {len(set(v[2] for v in env_vars))} env vars, {len(config_files)} config files"
        else:
            status = "SKIP"
            note = "No configuration found"

        return StepResult(self.name, status, elapsed, note)

    def _find_python_files(self, root: Path) -> List[Path]:
        """Find all Python source files."""
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
            ".pybundle-venv",  # pybundle's venv
        }

        for path in root.rglob("*.py"):
            if any(part in exclude_dirs for part in path.parts):
                continue
            python_files.append(path)

        return python_files

    def _extract_env_vars(
        self, python_files: List[Path], root: Path
    ) -> List[Tuple[str, int, str, str]]:
        """Extract environment variables from Python files.
        
        Returns list of (filepath, lineno, var_name, default).
        """
        env_vars = []

        for filepath in python_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source, filename=str(filepath))
                extractor = ConfigVarExtractor(str(filepath))
                extractor.visit(tree)

                rel_path = str(filepath.relative_to(root))
                for lineno, var_name, default in extractor.env_vars:
                    env_vars.append((rel_path, lineno, var_name, default))

            except (SyntaxError, Exception):
                # Skip files that can't be parsed
                continue

        return env_vars

    def _find_config_files(self, root: Path) -> List[str]:
        """Find configuration files in the project."""
        config_patterns = [
            "*.ini",
            "*.cfg",
            "*.conf",
            "*.yaml",
            "*.yml",
            "*.toml",
            ".env*",
            "config.*",
        ]

        config_files = []
        exclude_dirs = {
            "__pycache__",
            ".git",
            ".tox",
            "venv",
            "env",
            ".venv",
            "node_modules",
            "artifacts",
            "build",
            "dist",
            ".pybundle-venv",  # pybundle's venv
        }

        for pattern in config_patterns:
            for path in root.rglob(pattern):
                if path.is_file():
                    if any(part in exclude_dirs for part in path.parts):
                        continue
                    try:
                        rel_path = str(path.relative_to(root))
                        config_files.append(rel_path)
                    except ValueError:
                        continue

        return config_files

    def _extract_config_patterns(
        self, config_files: List[str], root: Path
    ) -> Dict[str, List[Tuple[str, int]]]:
        """Extract configuration patterns from config files.
        
        Returns dict of {pattern: [(filepath, lineno)]}.
        """
        patterns: Dict[str, List[Tuple[str, int]]] = {}

        # Simple pattern matching for common config formats
        var_patterns = [
            (re.compile(r'^([A-Z_][A-Z0-9_]*)\s*='), "Environment variable"),
            (re.compile(r'^\s*([a-z_][a-z0-9_]*)\s*:'), "YAML/INI key"),
            (re.compile(r'^\s*\[([^\]]+)\]'), "Section header"),
        ]

        for config_file in config_files:
            filepath = root / config_file
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        for pattern, description in var_patterns:
                            match = pattern.match(line)
                            if match:
                                key = f"{description}: {match.group(1)}"
                                if key not in patterns:
                                    patterns[key] = []
                                patterns[key].append((config_file, lineno))
                                break
            except Exception:
                # Skip files that can't be read
                continue

        return patterns
