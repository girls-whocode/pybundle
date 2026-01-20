"""
Step: Flask Debugging
Detect Flask debug mode and other security issues in Flask apps.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .base import Step, StepResult


class FlaskDebuggingStep(Step):
    """Detect Flask debug mode and security issues."""

    name = "flask debugging"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Check Flask debugging configuration."""
        import time

        start = time.time()

        root = ctx.root

        # Find Flask app
        flask_info = self._find_flask_app(root)
        if not flask_info:
            elapsed = int(time.time() - start)
            return StepResult(
                self.name, "SKIP", elapsed, "No Flask application found"
            )

        # Analyze Flask configuration
        config_issues = self._analyze_flask_config(root, flask_info)

        # Generate report
        lines = [
            "=" * 80,
            "FLASK SECURITY & DEBUGGING REPORT",
            "=" * 80,
            "",
        ]

        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                f"Flask app location: {flask_info['file']}:{flask_info['name']}",
                "",
            ]
        )

        # Configuration issues
        lines.extend(
            [
                "SECURITY ISSUES",
                "=" * 80,
                "",
            ]
        )

        if config_issues:
            for level, issue, detail in config_issues:
                icon = "✗" if level == "ERROR" else "⚠"
                lines.append(f"{icon} [{level}] {issue}")
                if detail:
                    lines.append(f"    {detail}")
            lines.append("")
        else:
            lines.append("✓ No critical security issues detected")
            lines.append("")

        # Debug mode analysis
        lines.extend(
            [
                "DEBUG MODE ANALYSIS",
                "-" * 80,
                "",
            ]
        )

        debug_findings = self._check_debug_mode(root, flask_info)
        for finding in debug_findings:
            lines.append(f"  • {finding}")

        lines.append("")

        # Routes analysis
        lines.extend(
            [
                "ROUTES ANALYSIS",
                "=" * 80,
                "",
            ]
        )

        routes = self._extract_routes(root, flask_info)
        if routes:
            lines.append(f"Found {len(routes)} route(s):")
            lines.append("")
            for method, path, handler in routes:
                lines.append(f"  {method:6} {path:40} -> {handler}")
        else:
            lines.append("  ℹ No routes found via static analysis")

        lines.append("")

        # Recommendations
        lines.extend(
            [
                "=" * 80,
                "FLASK DEPLOYMENT BEST PRACTICES",
                "=" * 80,
                "",
                "1. DEBUG MODE",
                "   ✗ NEVER use DEBUG=True in production",
                "   ✓ Use environment variables to control debug mode",
                "   ✓ Set DEBUG=False in production configuration",
                "   ✓ Use app.config.from_object('config.Production')",
                "",
                "2. SECRET KEY",
                "   ✓ Use strong, random SECRET_KEY (os.urandom(24))",
                "   ✓ Store SECRET_KEY in environment variables",
                "   ✓ Never hardcode secrets in source code",
                "   ✓ Rotate SECRET_KEY regularly in production",
                "",
                "3. SESSION SECURITY",
                "   ✓ Set SESSION_COOKIE_SECURE=True",
                "   ✓ Set SESSION_COOKIE_HTTPONLY=True",
                "   ✓ Set SESSION_COOKIE_SAMESITE='Lax' or 'Strict'",
                "   ✓ Use secure session backends (Redis, database)",
                "",
                "4. CORS & HEADERS",
                "   ✓ Use Flask-CORS with restricted origins",
                "   ✓ Set X-Frame-Options: DENY",
                "   ✓ Set X-Content-Type-Options: nosniff",
                "   ✓ Set X-XSS-Protection: 1; mode=block",
                "   ✓ Set Strict-Transport-Security (HSTS)",
                "",
                "5. ERROR HANDLING",
                "   ✓ Implement custom 404, 500 error handlers",
                "   ✓ Log errors securely (no sensitive data)",
                "   ✓ Hide stack traces in production",
                "   ✓ Return generic error messages to users",
                "",
                "6. DEPENDENCIES",
                "   ✓ Use pip-audit to check for vulnerabilities",
                "   ✓ Keep Flask and extensions updated",
                "   ✓ Review security advisories regularly",
                "",
                "7. DEPLOYMENT",
                "   ✓ Use WSGI server (Gunicorn, uWSGI, Waitress)",
                "   ✓ Run behind reverse proxy (Nginx, Apache)",
                "   ✓ Use HTTPS with valid certificate",
                "   ✓ Enable security headers in reverse proxy",
                "",
            ]
        )

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "151_flask_checks.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_flask_app(self, root: Path) -> Optional[Dict[str, str]]:
        """Find Flask app instance."""
        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")

                # Look for Flask imports and app creation
                if "from flask import" in source or "import flask" in source:
                    if "Flask(" in source:
                        # Extract app variable name
                        match = re.search(r"(\w+)\s*=\s*Flask\(", source)
                        if match:
                            return {
                                "file": str(py_file.relative_to(root)),
                                "name": match.group(1),
                            }
            except (OSError, UnicodeDecodeError):
                continue

        return None

    def _analyze_flask_config(
        self, root: Path, flask_info: Dict[str, str]
    ) -> List[Tuple[str, str, str]]:
        """Analyze Flask configuration for security issues."""
        issues = []

        # Check for hardcoded secrets
        python_files = list(root.rglob("*.py"))
        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")

                # Check for hardcoded SECRET_KEY
                if re.search(
                    r"['\"]SECRET_KEY['\"]?\s*[:=]\s*['\"](?!<|{{)", source
                ):
                    issues.append(
                        (
                            "ERROR",
                            "Hardcoded SECRET_KEY detected",
                            f"File: {py_file.relative_to(root)}",
                        )
                    )

                # Check for DEBUG=True in code
                if re.search(r"DEBUG\s*=\s*True", source):
                    issues.append(
                        (
                            "ERROR",
                            "DEBUG=True found in code",
                            f"File: {py_file.relative_to(root)} - Use environment variables instead",
                        )
                    )

            except (OSError, UnicodeDecodeError):
                continue

        return issues

    def _check_debug_mode(self, root: Path, flask_info: Dict[str, str]) -> List[str]:
        """Check debug mode configuration."""
        findings = []

        app_file = root / flask_info["file"]
        if app_file.exists():
            try:
                source = app_file.read_text(encoding="utf-8", errors="ignore")

                if "app.run(debug=True)" in source:
                    findings.append(
                        "⚠ app.run(debug=True) found - ensure this is only in development"
                    )

                if "FLASK_ENV" in source:
                    findings.append(
                        "✓ FLASK_ENV environment variable is used"
                    )

                if "os.getenv('DEBUG')" in source or "os.environ.get('DEBUG')" in source:
                    findings.append(
                        "✓ DEBUG mode controlled via environment variable"
                    )

                if not any(
                    pattern in source
                    for pattern in ["debug=", "FLASK_ENV", "DEBUG", "app.run()"]
                ):
                    findings.append(
                        "ℹ No explicit debug configuration found - verify Flask configuration chain"
                    )

            except (OSError, UnicodeDecodeError):
                pass

        return findings

    def _extract_routes(self, root: Path, flask_info: Dict[str, str]) -> List[Tuple[str, str, str]]:
        """Extract Flask routes."""
        routes = []

        app_file = root / flask_info["file"]
        if not app_file.exists():
            return routes

        try:
            source = app_file.read_text(encoding="utf-8", errors="ignore")
            lines = source.split("\n")

            # Pattern: @app.route or @app.get, @app.post, etc.
            for i, line in enumerate(lines):
                route_match = re.search(r"@(?:app|blueprint)\.(route|get|post|put|delete)\(['\"]([^'\"]+)", line)
                if route_match:
                    method = route_match.group(1).upper()
                    path = route_match.group(2)

                    # Find handler function
                    for j in range(i + 1, min(i + 3, len(lines))):
                        func_match = re.search(r"def\s+(\w+)\s*\(", lines[j])
                        if func_match:
                            handler = func_match.group(1)
                            routes.append((method, path, handler))
                            break

        except Exception:
            pass

        return routes
