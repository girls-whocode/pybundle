"""
Step: Security Headers Analysis
Detect security headers in Flask, FastAPI, and Django applications.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class SecurityHeadersStep(Step):
    """Analyze security headers in web applications."""

    name = "security headers"

    # Security headers and their implementations
    SECURITY_HEADERS = {
        "Content-Security-Policy": "CSP",
        "X-Content-Type-Options": "MIME Type",
        "X-Frame-Options": "Clickjacking",
        "Strict-Transport-Security": "HSTS",
        "X-XSS-Protection": "XSS",
        "Referrer-Policy": "Referrer",
        "Permissions-Policy": "Permissions",
        "Access-Control-Allow-Origin": "CORS",
    }

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze security headers in codebase."""
        import time

        start = time.time()

        root = ctx.root

        # Detect frameworks
        frameworks = self._detect_frameworks(root)

        # Find security header implementations
        headers_found = self._find_security_headers(root, frameworks)

        # Generate report
        lines = [
            "=" * 80,
            "SECURITY HEADERS ANALYSIS REPORT",
            "=" * 80,
            "",
        ]

        # Framework detection
        lines.extend(
            [
                "FRAMEWORK DETECTION",
                "=" * 80,
                "",
            ]
        )

        if frameworks:
            for framework, details in frameworks.items():
                lines.append(f"✓ {framework}")
                if details.get("files"):
                    lines.append(f"  Found in: {', '.join(details['files'][:3])}")
                    if len(details["files"]) > 3:
                        lines.append(f"  ... and {len(details['files']) - 3} more")
                lines.append("")

        else:
            lines.append("⊘ No web frameworks detected")
            lines.append("")

        # Security headers summary
        lines.extend(
            [
                "SECURITY HEADERS IMPLEMENTATION",
                "=" * 80,
                "",
            ]
        )

        if headers_found:
            implemented_count = len(headers_found["implemented"])
            total_count = len(self.SECURITY_HEADERS)

            lines.append(f"Headers implemented: {implemented_count}/{total_count}")
            lines.append("")

            if headers_found["implemented"]:
                lines.append("✓ IMPLEMENTED HEADERS:")
                for header, details in headers_found["implemented"].items():
                    lines.append(f"  - {header}")
                    if details.get("files"):
                        for file_path in details["files"][:2]:
                            lines.append(f"    Found in: {file_path}")
                        if len(details["files"]) > 2:
                            lines.append(f"    ... and {len(details['files']) - 2} more files")

                lines.append("")

            if headers_found["missing"]:
                lines.append(f"⚠ MISSING HEADERS ({len(headers_found['missing'])}):")
                for header in sorted(headers_found["missing"]):
                    purpose = self.SECURITY_HEADERS.get(header, "")
                    lines.append(f"  - {header} ({purpose})")

                lines.append("")

        else:
            lines.append("⊘ No security headers found in codebase")
            lines.append("")

        # Implementation patterns
        if headers_found and headers_found.get("patterns"):
            lines.extend(
                [
                    "IMPLEMENTATION PATTERNS",
                    "=" * 80,
                    "",
                ]
            )

            for pattern_type, details in headers_found["patterns"].items():
                lines.append(f"{pattern_type}:")
                for location in details[:5]:
                    lines.append(f"  - {location}")
                if len(details) > 5:
                    lines.append(f"  ... and {len(details) - 5} more")
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

        if frameworks:
            framework_name = list(frameworks.keys())[0]
            lines.append(f"For {framework_name}:")
            lines.append("")

            if framework_name == "Flask":
                lines.append("  @app.after_request")
                lines.append("  def set_security_headers(response):")
                lines.append(
                    "      response.headers['X-Content-Type-Options'] = 'nosniff'"
                )
                lines.append(
                    "      response.headers['X-Frame-Options'] = 'SAMEORIGIN'"
                )
                lines.append(
                    "      response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'"
                )
                lines.append("      return response")

            elif framework_name == "FastAPI":
                lines.append("  from fastapi.middleware.cors import CORSMiddleware")
                lines.append("  from fastapi.middleware.trustedhost import TrustedHostMiddleware")
                lines.append("")
                lines.append("  app.add_middleware(TrustedHostMiddleware, ...)")
                lines.append("  app.add_middleware(CORSMiddleware, ...)")

            elif framework_name == "Django":
                lines.append("  # In settings.py:")
                lines.append("  SECURE_BROWSER_XSS_FILTER = True")
                lines.append("  SECURE_CONTENT_SECURITY_POLICY = {...}")
                lines.append("  SESSION_COOKIE_SECURE = True")
                lines.append("  CSRF_COOKIE_SECURE = True")

            lines.append("")

        lines.append("  1. Implement missing security headers")
        lines.append("  2. Set appropriate CSP directives for your application")
        lines.append("  3. Enable HSTS in production")
        lines.append("  4. Configure CORS for necessary origins only")
        lines.append("  5. Use security header testing tools (securityheaders.com)")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "122_security_headers.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _detect_frameworks(self, root: Path) -> Dict[str, dict]:
        """Detect web frameworks in the project."""
        frameworks = {}

        python_files = list(root.rglob("*.py"))
        file_contents = {}

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                file_contents[py_file] = content
            except (OSError, UnicodeDecodeError):
                continue

        # Check for Flask
        for py_file, content in file_contents.items():
            if "from flask import" in content or "import flask" in content:
                if "Flask" not in frameworks:
                    frameworks["Flask"] = {"files": []}
                frameworks["Flask"]["files"].append(str(py_file.relative_to(root)))

            # Check for FastAPI
            if "from fastapi import" in content or "import fastapi" in content:
                if "FastAPI" not in frameworks:
                    frameworks["FastAPI"] = {"files": []}
                frameworks["FastAPI"]["files"].append(str(py_file.relative_to(root)))

            # Check for Django
            if "django" in content and (
                "from django" in content or "import django" in content
            ):
                if "Django" not in frameworks:
                    frameworks["Django"] = {"files": []}
                frameworks["Django"]["files"].append(str(py_file.relative_to(root)))

        return frameworks

    def _find_security_headers(self, root: Path, frameworks: Dict) -> Dict:
        """Find security header implementations."""
        implemented = {}
        patterns = {
            "Flask after_request": [],
            "FastAPI Middleware": [],
            "Django middleware": [],
            "Direct response.headers": [],
            "Custom header functions": [],
        }

        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(root))

                # Find header implementations
                for header in self.SECURITY_HEADERS:
                    # Various patterns for setting headers
                    header_variants = [
                        f"'{header}'",
                        f'"{header}"',
                        header.replace("-", "_").upper(),
                    ]

                    for variant in header_variants:
                        if variant in content:
                            if header not in implemented:
                                implemented[header] = {"files": []}
                            if rel_path not in implemented[header]["files"]:
                                implemented[header]["files"].append(rel_path)

                # Detect patterns
                if "@app.after_request" in content:
                    patterns["Flask after_request"].append(rel_path)

                if "CORSMiddleware" in content or "TrustedHostMiddleware" in content:
                    patterns["FastAPI Middleware"].append(rel_path)

                if "MIDDLEWARE" in content and "django" in content:
                    patterns["Django middleware"].append(rel_path)

                if "response.headers" in content or "set_header" in content:
                    patterns["Direct response.headers"].append(rel_path)

                # Check for custom header functions
                if re.search(
                    r"def\s+\w*header\w*|def\s+\w*security\w*", content, re.IGNORECASE
                ):
                    patterns["Custom header functions"].append(rel_path)

            except (OSError, UnicodeDecodeError):
                continue

        # Calculate missing headers
        missing = set(self.SECURITY_HEADERS.keys()) - set(implemented.keys())

        # Filter patterns
        patterns = {k: list(set(v)) for k, v in patterns.items() if v}

        return {
            "implemented": implemented,
            "missing": sorted(missing),
            "patterns": patterns,
        }
