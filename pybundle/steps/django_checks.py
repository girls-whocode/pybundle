"""
Step: Django System Checks
Run Django's built-in system checks for security and deployment best practices.
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple

from .base import Step, StepResult


class DjangoSystemChecksStep(Step):
    """Run Django system checks and parse results."""

    name = "django checks"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Run Django system checks."""
        import time

        start = time.time()

        root = ctx.root

        # Check if Django is installed and project has manage.py
        manage_py = self._find_manage_py(root)
        if not manage_py:
            elapsed = int(time.time() - start)
            return StepResult(
                self.name, "SKIP", elapsed, "No Django project found (manage.py not detected)"
            )

        # Run Django system checks
        checks_output = self._run_django_checks(manage_py)

        # Also run deploy checks
        deploy_output = self._run_django_deploy_checks(manage_py)

        # Parse results
        checks_issues = self._parse_check_output(checks_output)
        deploy_issues = self._parse_check_output(deploy_output)

        # Generate report
        lines = [
            "=" * 80,
            "DJANGO SYSTEM CHECKS REPORT",
            "=" * 80,
            "",
        ]

        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                f"Django project: {manage_py}",
                "",
            ]
        )

        # General checks
        lines.extend(
            [
                "GENERAL SYSTEM CHECKS",
                "-" * 80,
                "",
            ]
        )

        if checks_issues:
            lines.append(f"Found {len(checks_issues)} issue(s):")
            lines.append("")
            for level, msg, hint in checks_issues:
                icon = "⚠" if level.upper() == "WARNING" else "✗" if level.upper() == "ERROR" else "ℹ"
                lines.append(f"  {icon} [{level.upper()}] {msg}")
                if hint:
                    lines.append(f"      Hint: {hint}")
            lines.append("")
        else:
            lines.append("✓ All general checks passed")
            lines.append("")

        # Deployment checks
        lines.extend(
            [
                "DEPLOYMENT BEST PRACTICES (--deploy mode)",
                "-" * 80,
                "",
            ]
        )

        if deploy_issues:
            lines.append(f"Found {len(deploy_issues)} issue(s):")
            lines.append("")
            for level, msg, hint in deploy_issues:
                icon = "⚠" if level.upper() == "WARNING" else "✗" if level.upper() == "ERROR" else "ℹ"
                lines.append(f"  {icon} [{level.upper()}] {msg}")
                if hint:
                    lines.append(f"      Hint: {hint}")
            lines.append("")
        else:
            lines.append("✓ All deployment checks passed")
            lines.append("")

        # Recommendations
        lines.extend(
            [
                "=" * 80,
                "DEPLOYMENT READINESS CHECKLIST",
                "=" * 80,
                "",
                "Security Settings:",
                "  ☐ DEBUG = False in production",
                "  ☐ SECRET_KEY set to secure random value",
                "  ☐ ALLOWED_HOSTS configured",
                "  ☐ SECURE_HSTS_SECONDS >= 31536000 (1 year)",
                "  ☐ SESSION_COOKIE_SECURE = True",
                "  ☐ SESSION_COOKIE_HTTPONLY = True",
                "  ☐ CSRF_COOKIE_SECURE = True",
                "  ☐ CSRF_COOKIE_HTTPONLY = True",
                "",
                "Database:",
                "  ☐ Using production-grade database (not SQLite)",
                "  ☐ Database connections configured with SSL",
                "  ☐ Database backups automated",
                "",
                "Static & Media:",
                "  ☐ STATIC_ROOT configured",
                "  ☐ Static files collected (./manage.py collectstatic)",
                "  ☐ MEDIA_ROOT and MEDIA_URL configured",
                "",
                "Logging:",
                "  ☐ LOGGING configured for production",
                "  ☐ Error emails configured (ADMINS)",
                "  ☐ Log files retention policy set",
                "",
                "Performance:",
                "  ☐ Database connection pooling enabled",
                "  ☐ Caching configured (Redis/Memcached)",
                "  ☐ Compression enabled (gzip, brotli)",
                "",
            ]
        )

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "150_django_checks.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_manage_py(self, root: Path) -> Path | None:
        """Find Django's manage.py file."""
        # Check root
        if (root / "manage.py").exists():
            return root / "manage.py"

        # Check common locations
        for subdir in [".", "src", "app", "django_app"]:
            candidate = root / subdir / "manage.py"
            if candidate.exists():
                return candidate

        return None

    def _run_django_checks(self, manage_py: Path) -> str:
        """Run basic Django checks."""
        try:
            result = subprocess.run(
                ["python", str(manage_py), "check"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=manage_py.parent,
            )
            return result.stdout + result.stderr
        except Exception:
            return ""

    def _run_django_deploy_checks(self, manage_py: Path) -> str:
        """Run Django deployment checks."""
        try:
            result = subprocess.run(
                ["python", str(manage_py), "check", "--deploy"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=manage_py.parent,
            )
            return result.stdout + result.stderr
        except Exception:
            return ""

    def _parse_check_output(self, output: str) -> List[Tuple[str, str, str]]:
        """Parse Django check output."""
        issues = []

        lines = output.split("\n")
        for line in lines:
            # Pattern: "WARNING (security.W001): ..."
            match = re.search(r"(ERROR|WARNING|INFO)\s+\((\w+)\):\s+(.*?)(?:\nHint|$)", line)
            if match:
                level, code, msg = match.groups()
                hint = ""
                # Try to extract hint from next line
                idx = lines.index(line) if line in lines else -1
                if idx >= 0 and idx + 1 < len(lines) and "Hint:" in lines[idx + 1]:
                    hint = lines[idx + 1].replace("Hint:", "").strip()
                issues.append((level, f"{msg} ({code})", hint))

        return issues
