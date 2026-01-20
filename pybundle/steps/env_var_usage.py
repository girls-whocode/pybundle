"""
Step: Environment Variable Usage
Track usage of environment variables via os.getenv, os.environ patterns.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

from .base import Step, StepResult


class EnvVarUsageStep(Step):
    """Analyze environment variable usage patterns in Python code."""

    name = "env var usage"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Find all environment variable accesses."""
        import time

        start = time.time()

        root = ctx.root
        python_files = sorted(root.rglob("*.py"))
        if not python_files:
            return StepResult(self.name, "SKIP", int(time.time() - start), "No Python files found")

        # Track environment variable patterns
        env_vars: Dict[str, List[str]] = {}  # var_name -> [file:line, ...]
        env_patterns = {
            "os.getenv": [],
            "os.environ.get": [],
            "os.environ[]": [],
            "dotenv": [],
        }

        # Regex patterns for detection
        getenv_pattern = re.compile(r'os\.getenv\(["\']([^"\']+)["\']')
        environ_get_pattern = re.compile(r'os\.environ\.get\(["\']([^"\']+)["\']')
        environ_bracket_pattern = re.compile(r'os\.environ\[["\']([^"\']+)["\']\]')
        dotenv_pattern = re.compile(r'load_dotenv|from\s+dotenv\s+import')

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

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = py_file.relative_to(root)

                # Check for environment variable usage patterns
                if "os.getenv" not in source and "os.environ" not in source and "dotenv" not in source:
                    continue

                # Check for dotenv usage
                if dotenv_pattern.search(source):
                    env_patterns["dotenv"].append(str(rel_path))

                # Parse with regex (faster for simple patterns)
                for line_num, line in enumerate(source.split("\n"), start=1):
                    location = f"{rel_path}:{line_num}"

                    # os.getenv()
                    for match in getenv_pattern.finditer(line):
                        var_name = match.group(1)
                        if var_name not in env_vars:
                            env_vars[var_name] = []
                        env_vars[var_name].append(location)
                        env_patterns["os.getenv"].append(location)

                    # os.environ.get()
                    for match in environ_get_pattern.finditer(line):
                        var_name = match.group(1)
                        if var_name not in env_vars:
                            env_vars[var_name] = []
                        env_vars[var_name].append(location)
                        env_patterns["os.environ.get"].append(location)

                    # os.environ[]
                    for match in environ_bracket_pattern.finditer(line):
                        var_name = match.group(1)
                        if var_name not in env_vars:
                            env_vars[var_name] = []
                        env_vars[var_name].append(location)
                        env_patterns["os.environ[]"].append(location)

            except (UnicodeDecodeError, OSError):
                continue

        # Calculate statistics
        total_vars = len(env_vars)
        total_accesses = sum(len(locations) for locations in env_vars.values())

        # Generate report
        lines = [
            "=" * 80,
            "ENVIRONMENT VARIABLE USAGE ANALYSIS",
            "=" * 80,
            "",
            f"Total Python files analyzed: {len(python_files)}",
            f"Unique environment variables: {total_vars}",
            f"Total environment variable accesses: {total_accesses}",
            "",
        ]

        # Usage patterns
        lines.extend(
            [
                "=" * 80,
                "USAGE PATTERNS",
                "=" * 80,
                "",
            ]
        )

        for pattern, locations in env_patterns.items():
            lines.append(f"{pattern:20} {len(locations):5} occurrence(s)")
        lines.append("")

        # Dotenv detection
        if env_patterns["dotenv"]:
            lines.extend(
                [
                    "=" * 80,
                    "DOTENV USAGE DETECTED",
                    "=" * 80,
                    "",
                ]
            )
            for file in env_patterns["dotenv"]:
                lines.append(f"  - {file}")
            lines.append("")

        # Environment variables
        if env_vars:
            lines.extend(
                [
                    "=" * 80,
                    "ENVIRONMENT VARIABLES (sorted by frequency)",
                    "=" * 80,
                    "",
                ]
            )

            sorted_vars = sorted(env_vars.items(), key=lambda x: len(x[1]), reverse=True)
            for var_name, locations in sorted_vars:
                lines.append(f"{var_name}: {len(locations)} access(es)")
                for loc in locations[:3]:  # Show first 3 locations
                    lines.append(f"  - {loc}")
                if len(locations) > 3:
                    lines.append(f"  ... and {len(locations) - 3} more")
                lines.append("")

        # Check for .env file
        env_file = root / ".env"
        env_example = root / ".env.example"
        
        lines.extend(
            [
                "=" * 80,
                "ENVIRONMENT FILES",
                "=" * 80,
                "",
            ]
        )

        if env_file.exists():
            lines.append("  ✓ .env file found")
        else:
            lines.append("  ✗ .env file not found")

        if env_example.exists():
            lines.append("  ✓ .env.example file found")
            # Parse .env.example for documented variables
            try:
                example_content = env_example.read_text(encoding="utf-8")
                example_vars = set()
                for line_content in example_content.split("\n"):
                    line_content = line_content.strip()
                    if line_content and not line_content.startswith("#"):
                        if "=" in line_content:
                            var = line_content.split("=")[0].strip()
                            example_vars.add(var)
                
                if example_vars:
                    lines.append(f"  - Documents {len(example_vars)} variable(s)")
                    
                    # Check for undocumented variables
                    undocumented = set(env_vars.keys()) - example_vars
                    if undocumented:
                        lines.append(f"  - {len(undocumented)} variable(s) used but not documented:")
                        for var in sorted(undocumented)[:10]:
                            lines.append(f"      {var}")
                        if len(undocumented) > 10:
                            lines.append(f"      ... and {len(undocumented) - 10} more")
            except (OSError, UnicodeDecodeError):
                pass
        else:
            lines.append("  ✗ .env.example file not found")

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

        if total_vars == 0:
            lines.append("  - No environment variables detected")
        else:
            if not env_example.exists():
                lines.append("  - Create .env.example to document required environment variables")
            
            # Check for hardcoded defaults
            if len(env_patterns["os.environ[]"]) > 0:
                lines.append("  - Consider using os.getenv() with defaults instead of os.environ[]")
                lines.append("    to avoid KeyError exceptions")
            
            if not env_patterns["dotenv"]:
                lines.append("  - Consider using python-dotenv to load .env files")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "104_env_var_usage.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")
