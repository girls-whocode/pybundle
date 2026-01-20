"""
Step: Configuration Schema Validation
Validate configuration files and environment variable schemas.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional

from .base import Step, StepResult


class ConfigValidationStep(Step):
    """Validate configuration schemas and .env completeness."""

    name = "config validation"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Validate configuration schemas and environment files."""
        import time

        start = time.time()

        root = ctx.root

        # Find configuration files
        config_files = self._find_config_files(root)
        env_file = root / ".env"
        env_example = root / ".env.example"

        # Analyze Pydantic settings
        pydantic_settings = self._analyze_pydantic_settings(root)

        # Compare .env and .env.example
        env_comparison = self._compare_env_files(env_file, env_example)

        # Generate report
        lines = [
            "=" * 80,
            "CONFIGURATION VALIDATION REPORT",
            "=" * 80,
            "",
            f"Project root: {root}",
            "",
        ]

        # Configuration files found
        lines.extend(
            [
                "=" * 80,
                "CONFIGURATION FILES",
                "=" * 80,
                "",
            ]
        )

        if config_files:
            for file_type, files in config_files.items():
                lines.append(f"{file_type}:")
                for f in files:
                    rel_path = f.relative_to(root)
                    lines.append(f"  - {rel_path}")
            lines.append("")
        else:
            lines.append("No standard configuration files found")
            lines.append("")

        # Pydantic settings analysis
        if pydantic_settings:
            lines.extend(
                [
                    "=" * 80,
                    "PYDANTIC SETTINGS ANALYSIS",
                    "=" * 80,
                    "",
                ]
            )

            for settings_class, details in pydantic_settings.items():
                lines.append(f"Class: {settings_class}")
                lines.append(f"  Location: {details['file']}")
                lines.append(f"  Fields: {details['field_count']}")

                if details["fields"]:
                    lines.append("  Field annotations:")
                    for field, field_type in details["fields"][:10]:
                        lines.append(f"    - {field}: {field_type}")
                    if len(details["fields"]) > 10:
                        lines.append(f"    ... and {len(details['fields']) - 10} more")

                lines.append("")

        # .env file analysis
        if env_file.exists() or env_example.exists():
            lines.extend(
                [
                    "=" * 80,
                    "ENVIRONMENT FILES ANALYSIS",
                    "=" * 80,
                    "",
                ]
            )

            if env_example.exists():
                lines.append("✓ .env.example found")
                example_count = len(env_comparison["example_vars"])
                lines.append(f"  Documented variables: {example_count}")

                if env_comparison["example_vars"]:
                    lines.append("  Variables:")
                    for var in sorted(list(env_comparison["example_vars"]))[:15]:
                        lines.append(f"    - {var}")
                    if len(env_comparison["example_vars"]) > 15:
                        lines.append(
                            f"    ... and {len(env_comparison['example_vars']) - 15} more"
                        )

                lines.append("")

            if env_file.exists():
                lines.append("✓ .env found")
                env_count = len(env_comparison["env_vars"])
                lines.append(f"  Variables set: {env_count}")
                lines.append("")

            # Comparison
            if env_file.exists() and env_example.exists():
                missing = env_comparison["missing_in_env"]
                extra = env_comparison["extra_in_env"]

                lines.append("ENV FILE COMPARISON:")
                if missing:
                    lines.append(
                        f"  ⚠ Missing in .env (documented but not set): {len(missing)}"
                    )
                    for var in sorted(missing)[:10]:
                        lines.append(f"    - {var}")
                    if len(missing) > 10:
                        lines.append(f"    ... and {len(missing) - 10} more")
                else:
                    lines.append("  ✓ All documented variables are set in .env")

                if extra:
                    lines.append(
                        f"  ⚠ Extra in .env (not in .env.example): {len(extra)}"
                    )
                    for var in sorted(extra)[:10]:
                        lines.append(f"    - {var}")
                    if len(extra) > 10:
                        lines.append(f"    ... and {len(extra) - 10} more")
                else:
                    lines.append("  ✓ All .env variables are documented in .env.example")

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

        if not env_example.exists():
            lines.append("  - Create .env.example to document required variables")
        if env_file.exists() and not env_example.exists():
            lines.append("  - Use .env.example to version-control configuration schema")
        if pydantic_settings:
            lines.append("  - Pydantic settings detected: leverage validation at runtime")
        if not pydantic_settings and (env_file.exists() or env_example.exists()):
            lines.append("  - Consider using Pydantic BaseSettings for type-safe configuration")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "120_config_validation.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_config_files(self, root: Path) -> Dict[str, List[Path]]:
        """Find common configuration files."""
        config_patterns = {
            "YAML/YML": ["*.yaml", "*.yml"],
            "TOML": ["*.toml"],
            "JSON": ["*.json"],
            "INI": ["*.ini", "*.cfg"],
            "YAML/JSON": ["config.yaml", "config.json", "settings.yaml"],
        }

        found = {}
        for file_type, patterns in config_patterns.items():
            files = []
            for pattern in patterns:
                files.extend(root.glob(pattern))
            if files:
                found[file_type] = files

        return found

    def _analyze_pydantic_settings(self, root: Path) -> Dict[str, dict]:
        """Find and analyze Pydantic BaseSettings classes."""
        settings = {}

        python_files = root.rglob("*.py")
        for py_file in python_files:
            # Skip venv and cache
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")

                # Check if file imports BaseSettings
                if "BaseSettings" not in source:
                    continue

                # Find class definitions that inherit from BaseSettings
                class_pattern = (
                    r"class\s+(\w+)\s*\(\s*.*BaseSettings.*\s*\):"
                )
                matches = re.finditer(class_pattern, source)

                for match in matches:
                    class_name = match.group(1)
                    rel_path = py_file.relative_to(root)

                    # Extract fields (simple annotation parsing)
                    fields = []
                    class_body_start = source.find(match.group(0)) + len(match.group(0))
                    class_body = source[class_body_start :]

                    # Find annotations before any method definitions
                    annotation_pattern = r"(\w+)\s*:\s*([^\n=]+)"
                    for field_match in re.finditer(annotation_pattern, class_body):
                        field_name = field_match.group(1)
                        field_type = field_match.group(2).strip()

                        # Stop at method definitions
                        if field_name == "def":
                            break

                        fields.append((field_name, field_type))

                    settings[class_name] = {
                        "file": str(rel_path),
                        "field_count": len(fields),
                        "fields": fields,
                    }

            except (OSError, UnicodeDecodeError):
                continue

        return settings

    def _compare_env_files(
        self, env_file: Path, env_example: Path
    ) -> Dict[str, Set[str]]:
        """Compare .env and .env.example files."""
        env_vars = set()
        example_vars = set()

        # Parse .env
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        var_name = line.split("=")[0].strip()
                        if var_name:
                            env_vars.add(var_name)
            except (OSError, UnicodeDecodeError):
                pass

        # Parse .env.example
        if env_example.exists():
            try:
                content = env_example.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        var_name = line.split("=")[0].strip()
                        if var_name:
                            example_vars.add(var_name)
            except (OSError, UnicodeDecodeError):
                pass

        return {
            "env_vars": env_vars,
            "example_vars": example_vars,
            "missing_in_env": example_vars - env_vars,
            "extra_in_env": env_vars - example_vars,
        }
