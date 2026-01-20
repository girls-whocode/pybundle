"""
Step: Environment Variable Completeness Check
Verify that all required environment variables are documented.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class EnvCompletenessStep(Step):
    """Check environment variable completeness and documentation."""

    name = "env completeness"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze environment variable completeness."""
        import time

        start = time.time()

        root = ctx.root

        # Find all env var usages
        used_vars = self._find_env_var_usage(root)

        # Find documented vars
        documented_vars = self._find_documented_vars(root)

        # Generate report
        lines = [
            "=" * 80,
            "ENVIRONMENT VARIABLE COMPLETENESS REPORT",
            "=" * 80,
            "",
            f"Project root: {root}",
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"Environment variables referenced: {len(used_vars['all_vars'])}",
                f"Documented variables: {len(documented_vars['all_vars'])}",
                "",
            ]
        )

        # Used but not documented
        undocumented = used_vars["all_vars"] - documented_vars["all_vars"]
        if undocumented:
            lines.append(f"⚠ NOT DOCUMENTED ({len(undocumented)}):")
            for var in sorted(undocumented):
                lines.append(f"  - {var}")
            lines.append("")
        else:
            lines.append("✓ All referenced variables are documented")
            lines.append("")

        # Documented but not used
        unused = documented_vars["all_vars"] - used_vars["all_vars"]
        if unused:
            lines.append(f"ℹ DOCUMENTED BUT NOT USED ({len(unused)}):")
            for var in sorted(unused):
                lines.append(f"  - {var}")
            lines.append("")
        else:
            lines.append("✓ All documented variables are referenced")
            lines.append("")

        # Detailed analysis
        lines.extend(
            [
                "=" * 80,
                "DETAILED ANALYSIS",
                "=" * 80,
                "",
            ]
        )

        # Env usage by type
        if used_vars["getenv"] or used_vars["environ"]:
            lines.append("ENVIRONMENT VARIABLE ACCESS PATTERNS:")
            lines.append("")

            if used_vars["getenv"]:
                lines.append(f"  os.getenv() calls: {len(used_vars['getenv'])}")
                for var in sorted(list(used_vars["getenv"]))[:10]:
                    lines.append(f"    - {var}")
                if len(used_vars["getenv"]) > 10:
                    lines.append(f"    ... and {len(used_vars['getenv']) - 10} more")
                lines.append("")

            if used_vars["environ"]:
                lines.append(f"  os.environ[] access: {len(used_vars['environ'])}")
                for var in sorted(list(used_vars["environ"]))[:10]:
                    lines.append(f"    - {var}")
                if len(used_vars["environ"]) > 10:
                    lines.append(f"    ... and {len(used_vars['environ']) - 10} more")
                lines.append("")

        # Documentation sources
        if documented_vars["env_example"] or documented_vars["env_file"]:
            lines.append("DOCUMENTATION SOURCES:")
            lines.append("")

            if documented_vars["env_example"]:
                lines.append(f"  .env.example: {len(documented_vars['env_example'])} variables")
                for var in sorted(list(documented_vars["env_example"]))[:10]:
                    lines.append(f"    - {var}")
                if len(documented_vars["env_example"]) > 10:
                    lines.append(f"    ... and {len(documented_vars['env_example']) - 10} more")
                lines.append("")

            if documented_vars["env_file"]:
                lines.append(f"  .env: {len(documented_vars['env_file'])} variables")
                for var in sorted(list(documented_vars["env_file"]))[:10]:
                    lines.append(f"    - {var}")
                if len(documented_vars["env_file"]) > 10:
                    lines.append(f"    ... and {len(documented_vars['env_file']) - 10} more")
                lines.append("")

        # Documentation completeness score
        total_vars = len(used_vars["all_vars"])
        documented_count = len(used_vars["all_vars"] & documented_vars["all_vars"])

        if total_vars > 0:
            completeness = (documented_count / total_vars) * 100
            lines.append("=" * 80)
            lines.append("COMPLETENESS SCORE")
            lines.append("=" * 80)
            lines.append("")
            lines.append(
                f"  {documented_count}/{total_vars} variables documented ({completeness:.1f}%)"
            )
            lines.append("")

            if completeness == 100:
                lines.append("  ✓ EXCELLENT: All variables properly documented")
            elif completeness >= 80:
                lines.append("  ✓ GOOD: Most variables documented")
            elif completeness >= 50:
                lines.append("  ⚠ FAIR: Several variables missing documentation")
            else:
                lines.append("  ✗ POOR: Majority of variables not documented")

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

        if undocumented:
            lines.append("  - Add missing variables to .env.example:")
            for var in sorted(list(undocumented))[:5]:
                lines.append(f"    {var}=<value>")
            if len(undocumented) > 5:
                lines.append(f"    ... and {len(undocumented) - 5} more")

        if unused:
            lines.append("  - Remove or deprecate unused documented variables")

        if not (documented_vars["env_example"] or documented_vars["env_file"]):
            lines.append("  - Create .env.example to document all environment variables")

        lines.append("  - Use descriptive comments in .env.example")
        lines.append("  - Keep .env.example in version control, .env in .gitignore")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "120_config_completeness.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_env_var_usage(self, root: Path) -> Dict[str, Set[str]]:
        """Find all environment variable usage patterns."""
        getenv_vars = set()
        environ_vars = set()

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

                # Find os.getenv patterns
                getenv_pattern = r'os\.getenv\(["\']([A-Z_][A-Z0-9_]*)["\']'
                for match in re.finditer(getenv_pattern, source):
                    getenv_vars.add(match.group(1))

                # Find os.environ patterns
                environ_pattern = r'os\.environ\[["\']([A-Z_][A-Z0-9_]*)["\']'
                for match in re.finditer(environ_pattern, source):
                    environ_vars.add(match.group(1))

            except (OSError, UnicodeDecodeError):
                continue

        all_vars = getenv_vars | environ_vars

        return {
            "all_vars": all_vars,
            "getenv": getenv_vars,
            "environ": environ_vars,
        }

    def _find_documented_vars(self, root: Path) -> Dict[str, Set[str]]:
        """Find documented environment variables."""
        env_example_vars = set()
        env_file_vars = set()

        # Check .env.example
        env_example = root / ".env.example"
        if env_example.exists():
            try:
                content = env_example.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        var_name = line.split("=")[0].strip()
                        if var_name and var_name.isupper():
                            env_example_vars.add(var_name)
            except (OSError, UnicodeDecodeError):
                pass

        # Check .env
        env_file = root / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        var_name = line.split("=")[0].strip()
                        if var_name and var_name.isupper():
                            env_file_vars.add(var_name)
            except (OSError, UnicodeDecodeError):
                pass

        all_vars = env_example_vars | env_file_vars

        return {
            "all_vars": all_vars,
            "env_example": env_example_vars,
            "env_file": env_file_vars,
        }
