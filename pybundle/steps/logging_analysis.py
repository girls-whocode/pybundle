"""
Step: Logging Analysis
Analyze logging calls and log level distribution.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List

from .base import Step, StepResult


class LoggingAnalysisStep(Step):
    """Analyze logging calls and log level distribution in Python code."""

    name = "logging analysis"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Extract logging calls and analyze log level distribution."""
        import time

        start = time.time()

        root = ctx.root
        python_files = sorted(root.rglob("*.py"))
        if not python_files:
            return StepResult(self.name, "SKIP", int(time.time() - start), "No Python files found")

        # Track logging patterns
        log_levels: Dict[str, List[str]] = {
            "debug": [],
            "info": [],
            "warning": [],
            "error": [],
            "critical": [],
            "exception": [],
        }
        logging_configs = []
        logger_names = set()
        analyzed_files = 0

        # Common logging patterns to detect
        logging_import_pattern = re.compile(r"import\s+logging")
        getlogger_pattern = re.compile(r"logging\.getLogger\(['\"]?([^'\")\s]+)?['\"]?\)")
        basicconfig_pattern = re.compile(r"logging\.basicConfig\(")

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
                
                # Check for logging usage
                if "logging" not in source and "logger" not in source:
                    continue

                rel_path = py_file.relative_to(root)

                # Find logging configurations
                if basicconfig_pattern.search(source):
                    logging_configs.append(str(rel_path))

                # Find logger names
                for match in getlogger_pattern.finditer(source):
                    logger_name = match.group(1) or "__main__"
                    logger_names.add(logger_name)

                # Parse AST to find logging calls
                try:
                    tree = ast.parse(source, str(py_file))

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            # Check if it's a logging call
                            level = self._extract_log_level(node)
                            if level:
                                location = f"{rel_path}:{node.lineno}"
                                log_levels[level].append(location)

                except SyntaxError:
                    continue

            except (UnicodeDecodeError, OSError):
                continue

        # Calculate statistics
        total_logs = sum(len(locations) for locations in log_levels.values())

        # Generate report
        lines = [
            "=" * 80,
            "LOGGING ANALYSIS",
            "=" * 80,
            "",
            f"Total Python files analyzed: {analyzed_files}",
            f"Total logging calls found: {total_logs}",
            f"Logging configurations found: {len(logging_configs)}",
            f"Unique logger names: {len(logger_names)}",
            "",
        ]

        # Log level distribution
        if total_logs > 0:
            lines.extend(
                [
                    "=" * 80,
                    "LOG LEVEL DISTRIBUTION",
                    "=" * 80,
                    "",
                ]
            )

            for level in ["debug", "info", "warning", "error", "critical", "exception"]:
                count = len(log_levels[level])
                percentage = (count / total_logs * 100) if total_logs > 0 else 0
                lines.append(f"{level.upper():12} {count:6} ({percentage:5.1f}%)")

            lines.append("")

            # Show sample locations for each level
            lines.extend(
                [
                    "=" * 80,
                    "LOG LEVEL LOCATIONS (sample)",
                    "=" * 80,
                    "",
                ]
            )

            for level in ["debug", "info", "warning", "error", "critical", "exception"]:
                locations = log_levels[level]
                if locations:
                    lines.append(f"{level.upper()}: {len(locations)} occurrence(s)")
                    for loc in locations[:5]:  # Show first 5
                        lines.append(f"  - {loc}")
                    if len(locations) > 5:
                        lines.append(f"  ... and {len(locations) - 5} more")
                    lines.append("")

        # Logger names
        if logger_names:
            lines.extend(
                [
                    "=" * 80,
                    "LOGGER NAMES",
                    "=" * 80,
                    "",
                ]
            )
            for name in sorted(logger_names):
                lines.append(f"  - {name}")
            lines.append("")

        # Logging configurations
        if logging_configs:
            lines.extend(
                [
                    "=" * 80,
                    "LOGGING CONFIGURATIONS (basicConfig)",
                    "=" * 80,
                    "",
                ]
            )
            for config in logging_configs:
                lines.append(f"  - {config}")
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

        if total_logs == 0:
            lines.append("  - Consider adding logging to improve debuggability")
        else:
            debug_pct = len(log_levels["debug"]) / total_logs * 100 if total_logs > 0 else 0
            info_pct = len(log_levels["info"]) / total_logs * 100 if total_logs > 0 else 0
            
            if debug_pct > 50:
                lines.append("  - High percentage of DEBUG logs; consider reducing in production")
            if info_pct < 10 and total_logs > 10:
                lines.append("  - Low INFO logging; consider adding more informational logs")
            if len(log_levels["exception"]) == 0 and len(log_levels["error"]) > 0:
                lines.append("  - Consider using logger.exception() in exception handlers for stack traces")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "102_logging_analysis.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _extract_log_level(self, node: ast.Call) -> str:
        """Extract log level from logging call."""
        # Check for logger.level() or logging.level()
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr.lower()
            if method in ["debug", "info", "warning", "error", "critical", "exception"]:
                # Verify it's a logging call
                if isinstance(node.func.value, ast.Name):
                    var_name = node.func.value.id.lower()
                    if "log" in var_name:
                        return method
                elif isinstance(node.func.value, ast.Attribute):
                    # logging.getLogger().debug()
                    return method

        return ""
