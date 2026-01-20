"""
Step: Dockerfile Linting
Validate Dockerfile best practices using hadolint.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict

from .base import Step, StepResult


class DockerfileLintStep(Step):
    """Lint Dockerfiles for best practices using hadolint."""

    name = "dockerfile lint"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Run hadolint on all Dockerfiles found."""
        import time

        start = time.time()

        # Find all Dockerfiles (exact name or name with .suffix)
        dockerfiles = []
        for pattern in ["Dockerfile", "dockerfile", "Dockerfile.*", "dockerfile.*"]:
            dockerfiles.extend(ctx.root.rglob(pattern))
        
        # Filter to files that are actually Dockerfiles (exclude .py, .pyc, etc)
        seen = set()
        unique_dockerfiles = []
        for df in dockerfiles:
            if df.is_file():
                # Skip if it's clearly not a Dockerfile (has a code extension)
                if df.suffix in [".py", ".pyc", ".pyo", ".pyw", ".pyd"]:
                    continue
                
                key = str(df).lower()
                if key not in seen:
                    seen.add(key)
                    unique_dockerfiles.append(df)

        if not unique_dockerfiles:
            elapsed = int(time.time() - start)
            return StepResult(self.name, "SKIP", elapsed, "No Dockerfiles found")

        # Check if hadolint is available
        hadolint_path = None
        try:
            result = subprocess.run(
                ["which", "hadolint"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                hadolint_path = result.stdout.strip()
        except FileNotFoundError:
            pass

        # Generate report
        lines = [
            "=" * 80,
            "DOCKERFILE LINTING REPORT",
            "=" * 80,
            "",
            f"Dockerfiles found: {len(unique_dockerfiles)}",
            "",
        ]

        # List dockerfiles
        lines.extend(
            [
                "=" * 80,
                "DOCKERFILES",
                "=" * 80,
                "",
            ]
        )

        for df in sorted(unique_dockerfiles):
            rel_path = df.relative_to(ctx.root)
            lines.append(f"  - {rel_path}")
            
            # Show file size
            try:
                size = df.stat().st_size
                lines.append(f"    Size: {size} bytes")
            except OSError:
                pass

        lines.append("")

        # Run hadolint if available
        if hadolint_path:
            lines.extend(
                [
                    "=" * 80,
                    "HADOLINT RESULTS",
                    "=" * 80,
                    "",
                ]
            )

            hadolint_issues: Dict[str, List[str]] = {}
            total_warnings = 0
            total_errors = 0

            for df in sorted(unique_dockerfiles):
                rel_path = df.relative_to(ctx.root)
                
                try:
                    result = subprocess.run(
                        [hadolint_path, str(df)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    output = result.stdout + result.stderr
                    if output.strip():
                        issues = self._parse_hadolint_output(output)
                        if issues:
                            hadolint_issues[str(rel_path)] = issues
                            
                            # Count issue types
                            for issue in issues:
                                if "warning" in issue.lower() or "note" in issue.lower():
                                    total_warnings += 1
                                elif "error" in issue.lower():
                                    total_errors += 1

                except subprocess.TimeoutExpired:
                    lines.append(f"⚠ Timeout analyzing {rel_path}")
                except Exception as e:
                    lines.append(f"⚠ Error analyzing {rel_path}: {e}")

            if hadolint_issues:
                lines.append(f"Total issues found: {total_errors} error(s), {total_warnings} warning(s)")
                lines.append("")

                for dockerfile, issues in sorted(hadolint_issues.items()):
                    lines.append(f"\n{dockerfile}:")
                    lines.append("-" * 80)
                    for issue in issues:
                        lines.append(f"  {issue}")
            else:
                lines.append("✓ No issues found")
                lines.append("")

        else:
            lines.extend(
                [
                    "=" * 80,
                    "HADOLINT RESULTS",
                    "=" * 80,
                    "",
                    "⚠ hadolint not installed. Install with: pip install hadolint-py",
                    "  or via system package manager for full features.",
                    "",
                ]
            )

        # Dockerfile content analysis
        lines.extend(
            [
                "=" * 80,
                "DOCKERFILE ANALYSIS",
                "=" * 80,
                "",
            ]
        )

        analysis = self._analyze_dockerfiles(unique_dockerfiles, ctx.root)

        if analysis["uses_multistage"]:
            lines.append("✓ Multi-stage builds detected")
        else:
            lines.append("⚠ No multi-stage builds detected")

        if analysis["uses_user"]:
            lines.append("✓ Non-root user configured")
        else:
            lines.append("⚠ No non-root user found (security risk)")

        if analysis["pinned_versions"]:
            lines.append(f"✓ Pinned base images: {analysis['pinned_versions']}")
        else:
            lines.append("⚠ Unpinned base image versions detected")

        if analysis["has_healthcheck"]:
            lines.append("✓ HEALTHCHECK configured")
        else:
            lines.append("⚠ No HEALTHCHECK found")

        if analysis["use_args"]:
            lines.append(f"✓ ARG variables: {analysis['use_args']}")

        lines.append("")

        # Best practices recommendations
        lines.extend(
            [
                "=" * 80,
                "RECOMMENDATIONS",
                "=" * 80,
                "",
            ]
        )

        if not analysis["uses_multistage"]:
            lines.append("  - Consider using multi-stage builds to reduce final image size")
        if not analysis["uses_user"]:
            lines.append("  - Add RUN groupadd -r appuser && useradd -r -g appuser appuser")
            lines.append("    and USER appuser for security")
        if not analysis["pinned_versions"]:
            lines.append("  - Pin base image versions (use specific tags, not 'latest')")
        if not analysis["has_healthcheck"]:
            lines.append("  - Add HEALTHCHECK instruction for production containers")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "105_dockerfile_lint.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _parse_hadolint_output(self, output: str) -> List[str]:
        """Parse hadolint output and extract issue lines."""
        issues = []
        for line in output.split("\n"):
            line = line.strip()
            if line and not line.startswith("=="):
                issues.append(line)
        return issues

    def _analyze_dockerfiles(self, dockerfiles: List[Path], root: Path) -> Dict:
        """Perform static analysis of Dockerfile content."""
        analysis = {
            "uses_multistage": False,
            "uses_user": False,
            "pinned_versions": 0,
            "has_healthcheck": False,
            "use_args": 0,
        }

        for dockerfile in dockerfiles:
            try:
                content = dockerfile.read_text(encoding="utf-8", errors="ignore")

                # Check for multi-stage
                if "FROM" in content and content.count("FROM") > 1:
                    analysis["uses_multistage"] = True

                # Check for USER instruction
                if re.search(r"^\s*USER\s+\w+", content, re.MULTILINE):
                    if not "USER root" in content or "USER appuser" in content or "USER app" in content:
                        analysis["uses_user"] = True

                # Check for pinned versions
                from_pattern = re.findall(r"FROM\s+([^\s]+)", content)
                for from_ref in from_pattern:
                    # Check if has tag (not latest or missing)
                    if ":" in from_ref and not from_ref.endswith(":latest"):
                        analysis["pinned_versions"] += 1

                # Check for HEALTHCHECK
                if "HEALTHCHECK" in content:
                    analysis["has_healthcheck"] = True

                # Count ARG instructions
                arg_count = len(re.findall(r"^\s*ARG\s+", content, re.MULTILINE))
                analysis["use_args"] += arg_count

            except (OSError, UnicodeDecodeError):
                continue

        return analysis
