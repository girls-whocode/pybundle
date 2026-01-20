"""
Step: FastAPI Integration
Validate FastAPI OpenAPI schema and endpoint documentation.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from .base import Step, StepResult


class FastAPIIntegrationStep(Step):
    """Validate FastAPI schema and endpoint completeness."""

    name = "fastapi schema"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Validate FastAPI integration."""
        import time

        start = time.time()

        root = ctx.root

        # Find FastAPI app
        app_info = self._find_fastapi_app(root)
        if not app_info:
            elapsed = int(time.time() - start)
            return StepResult(
                self.name, "SKIP", elapsed, "No FastAPI application found"
            )

        # Analyze endpoints
        endpoints = self._analyze_endpoints(root, app_info)

        # Generate report
        lines = [
            "=" * 80,
            "FASTAPI INTEGRATION REPORT",
            "=" * 80,
            "",
        ]

        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                f"FastAPI app location: {app_info['file']}:{app_info['name']}",
                f"Total endpoints: {len(endpoints)}",
                "",
            ]
        )

        # Endpoint analysis
        lines.extend(
            [
                "ENDPOINTS",
                "=" * 80,
                "",
            ]
        )

        documented = 0
        undocumented = 0

        for endpoint in sorted(endpoints, key=lambda e: e["path"]):
            doc_status = "✓" if endpoint["has_docstring"] else "⚠"
            documented += 1 if endpoint["has_docstring"] else 0
            undocumented += 0 if endpoint["has_docstring"] else 1

            lines.append(f"{doc_status} {endpoint['method']:6} {endpoint['path']}")
            if endpoint["has_docstring"]:
                lines.append(f"   Summary: {endpoint['docstring_first_line']}")
            else:
                lines.append("   ⚠ Missing docstring (won't appear in OpenAPI)")

        lines.append("")

        # Statistics
        lines.extend(
            [
                "DOCUMENTATION STATISTICS",
                "-" * 80,
                f"Documented endpoints: {documented}/{len(endpoints)} ({100*documented//len(endpoints)}%)" if endpoints else "No endpoints found",
                f"Undocumented endpoints: {undocumented}/{len(endpoints)}" if endpoints else "",
                "",
            ]
        )

        # Response models
        lines.extend(
            [
                "RESPONSE MODELS",
                "=" * 80,
                "",
            ]
        )

        models_count = 0
        for endpoint in endpoints:
            if endpoint.get("response_model"):
                models_count += 1
                lines.append(f"  {endpoint['method']:6} {endpoint['path']}")
                lines.append(f"    Response: {endpoint['response_model']}")

        if models_count == 0:
            lines.append("  ℹ No response models found")

        lines.append("")

        # Recommendations
        lines.extend(
            [
                "=" * 80,
                "BEST PRACTICES & RECOMMENDATIONS",
                "=" * 80,
                "",
                "1. DOCUMENTATION",
                "   ✓ Add docstrings to all endpoint handlers",
                "   ✓ Use triple-quoted docstrings for OpenAPI summary",
                "   ✓ Include examples in docstrings for clarity",
                "",
                "2. RESPONSE MODELS",
                "   ✓ Define Pydantic models for all responses",
                "   ✓ Use response_model parameter in @app.get/post/etc",
                "   ✓ Include status_code for non-200 responses",
                "",
                "3. REQUEST VALIDATION",
                "   ✓ Use Pydantic models for request bodies",
                "   ✓ Use Path, Query, Header for parameter validation",
                "   ✓ Provide examples in Field descriptions",
                "",
                "4. ERROR HANDLING",
                "   ✓ Define responses for 400, 404, 500, etc",
                "   ✓ Use HTTPException with detail messages",
                "   ✓ Document possible error responses in docstrings",
                "",
                "5. SECURITY",
                "   ✓ Use security=[] parameter for protected endpoints",
                "   ✓ Document security requirements in OpenAPI",
                "   ✓ Validate bearer tokens and API keys",
                "",
                "6. TESTING",
                "   ✓ Use TestClient for endpoint testing",
                "   ✓ Test all response status codes",
                "   ✓ Test request validation (happy path + errors)",
                "",
            ]
        )

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "150_fastapi_schema.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_fastapi_app(self, root: Path) -> Optional[Dict[str, Any]]:
        """Find FastAPI app instance."""
        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")

                # Look for FastAPI imports and app creation
                if "from fastapi import" in source or "import fastapi" in source:
                    if "app = FastAPI" in source or "app: FastAPI" in source:
                        # Extract app variable name
                        import re

                        match = re.search(r"(\w+)\s*=\s*FastAPI\(", source)
                        if match:
                            return {
                                "file": str(py_file.relative_to(root)),
                                "name": match.group(1),
                            }
            except (OSError, UnicodeDecodeError):
                continue

        return None

    def _analyze_endpoints(self, root: Path, app_info: Dict) -> List[Dict[str, Any]]:
        """Analyze FastAPI endpoints."""
        endpoints = []

        # Look for route decorators in the app file
        app_file = root / app_info["file"]
        if not app_file.exists():
            return endpoints

        try:
            source = app_file.read_text(encoding="utf-8", errors="ignore")

            # Look for decorators: @app.get, @app.post, etc.
            import re

            # Pattern: @app.method("path")
            pattern = r"@(?:app|router)\.(get|post|put|delete|patch|head|options)\(['\"]([^'\"]+)['\"]"
            for match in re.finditer(pattern, source):
                method, path = match.groups()
                endpoints.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "has_docstring": False,
                        "docstring_first_line": "",
                        "response_model": None,
                    }
                )

            # Check for docstrings in functions following decorators
            lines = source.split("\n")
            for i, line in enumerate(lines):
                if re.search(r"@(?:app|router)\.(get|post|put|delete|patch|head|options)", line):
                    # Look for function definition
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if "def " in lines[j]:
                            # Check for docstring
                            if j + 1 < len(lines):
                                next_line = lines[j + 1].strip()
                                if next_line.startswith('"""') or next_line.startswith("'''"):
                                    docstring = next_line.replace('"""', "").replace("'''", "").strip()
                                    if endpoints:
                                        endpoints[-1]["has_docstring"] = True
                                        endpoints[-1]["docstring_first_line"] = docstring
                            break

            # Check for response_model
            for i, line in enumerate(lines):
                if "response_model=" in line and endpoints:
                    import re

                    match = re.search(r"response_model=(\w+)", line)
                    if match:
                        endpoints[-1]["response_model"] = match.group(1)

        except Exception:
            pass

        return endpoints
