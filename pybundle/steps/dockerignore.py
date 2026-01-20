"""
Step: .dockerignore Effectiveness Analysis
Validate .dockerignore and analyze build context efficiency.
"""

import fnmatch
from pathlib import Path
from typing import Set, List

from .base import Step, StepResult


class DockerigoreStep(Step):
    """Analyze .dockerignore effectiveness and build context."""

    name = "dockerignore analysis"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze .dockerignore patterns and effectiveness."""
        import time

        start = time.time()

        root = ctx.root

        # Check if Dockerfile exists
        dockerfiles = list(root.rglob("Dockerfile*"))
        if not dockerfiles:
            elapsed = int(time.time() - start)
            return StepResult(self.name, "SKIP", elapsed, "No Dockerfiles found")

        # Find .dockerignore
        dockerignore_path = root / ".dockerignore"
        if not dockerignore_path.exists():
            elapsed = int(time.time() - start)
            return StepResult(self.name, "SKIP", elapsed, "No .dockerignore found")

        # Parse .dockerignore patterns
        ignore_patterns = self._parse_dockerignore(dockerignore_path)

        # Analyze what would be included/excluded
        included_files, excluded_files, analysis = self._analyze_build_context(
            root, ignore_patterns
        )

        # Generate report
        lines = [
            "=" * 80,
            ".DOCKERIGNORE EFFECTIVENESS ANALYSIS",
            "=" * 80,
            "",
            f"Build context root: {root}",
            f".dockerignore location: {dockerignore_path}",
            "",
        ]

        # Stats
        lines.extend(
            [
                "=" * 80,
                "BUILD CONTEXT STATISTICS",
                "=" * 80,
                "",
                f"Total files in build context: {len(included_files) + len(excluded_files)}",
                f"Included files: {len(included_files)}",
                f"Excluded files: {len(excluded_files)}",
                f"Exclusion rate: {len(excluded_files) / (len(included_files) + len(excluded_files)) * 100:.1f}%",
                "",
            ]
        )

        # Show ignored files by category
        if excluded_files:
            lines.extend(
                [
                    "=" * 80,
                    "EXCLUDED FILES BY CATEGORY",
                    "=" * 80,
                    "",
                ]
            )

            categories = {
                "version_control": [],
                "cache": [],
                "tests": [],
                "docs": [],
                "build_artifacts": [],
                "env": [],
                "venv": [],
                "node": [],
                "other": [],
            }

            for file_path in sorted(excluded_files):
                path_str = str(file_path).lower()

                if any(
                    x in path_str
                    for x in [".git", ".hg", ".svn", ".bzr", ".gitignore"]
                ):
                    categories["version_control"].append(file_path)
                elif any(
                    x in path_str for x in ["__pycache__", ".pytest_cache", ".mypy_cache"]
                ):
                    categories["cache"].append(file_path)
                elif any(x in path_str for x in ["test", "spec"]):
                    categories["tests"].append(file_path)
                elif any(x in path_str for x in ["docs", "readme", "doc"]):
                    categories["docs"].append(file_path)
                elif any(
                    x in path_str
                    for x in ["build", "dist", ".egg", "*.pyc", "*.o", "*.so"]
                ):
                    categories["build_artifacts"].append(file_path)
                elif any(x in path_str for x in [".env", "secrets"]):
                    categories["env"].append(file_path)
                elif any(x in path_str for x in ["venv", ".venv", "env/"]):
                    categories["venv"].append(file_path)
                elif any(x in path_str for x in ["node_modules", "npm", "yarn"]):
                    categories["node"].append(file_path)
                else:
                    categories["other"].append(file_path)

            for category, files in categories.items():
                if files:
                    cat_name = category.replace("_", " ").title()
                    lines.append(f"\n{cat_name} ({len(files)} files):")
                    for f in files[:10]:  # Show first 10
                        lines.append(f"  - {f}")
                    if len(files) > 10:
                        lines.append(f"  ... and {len(files) - 10} more")

            lines.append("")

        # Show .dockerignore patterns
        lines.extend(
            [
                "=" * 80,
                ".DOCKERIGNORE PATTERNS",
                "=" * 80,
                "",
                f"Total patterns: {len(ignore_patterns)}",
                "",
            ]
        )

        for i, pattern in enumerate(ignore_patterns[:50], 1):
            lines.append(f"{i:3}. {pattern}")

        if len(ignore_patterns) > 50:
            lines.append(f"    ... and {len(ignore_patterns) - 50} more patterns")

        lines.append("")

        # Analysis of included files that might be unnecessary
        if included_files:
            large_files = []
            for file_path in included_files:
                try:
                    size = file_path.stat().st_size
                    if size > 1024 * 1024:  # > 1MB
                        large_files.append((file_path, size))
                except OSError:
                    pass

            if large_files:
                large_files.sort(key=lambda x: x[1], reverse=True)

                lines.extend(
                    [
                        "=" * 80,
                        "LARGE INCLUDED FILES (potential optimization targets)",
                        "=" * 80,
                        "",
                    ]
                )

                for file_path, size in large_files[:20]:
                    size_mb = size / (1024 * 1024)
                    lines.append(f"  {str(file_path):50} {size_mb:8.2f} MB")

                if len(large_files) > 20:
                    lines.append(f"  ... and {len(large_files) - 20} more")

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

        if analysis["has_venv"]:
            lines.append("  - Virtual environments should be excluded: add 'venv/' or '.venv/'")
        if analysis["has_tests"]:
            lines.append("  - Consider excluding test files: add 'test*' or 'tests/'")
        if analysis["has_docs"]:
            lines.append("  - Consider excluding documentation: add 'docs/'")
        if analysis["has_cache"]:
            lines.append("  - Cache directories should be excluded: add '__pycache__/'")
        if analysis["has_git"]:
            lines.append("  - VCS files should be excluded: add '.git/'")

        if not (
            analysis["has_venv"]
            or analysis["has_tests"]
            or analysis["has_cache"]
            or analysis["has_git"]
        ):
            lines.append("  - .dockerignore is well configured")

        # Image size impact
        if excluded_files:
            estimated_excluded = 0
            for file_path in excluded_files:
                try:
                    estimated_excluded += file_path.stat().st_size
                except OSError:
                    pass

            if estimated_excluded > 1024 * 1024:
                excluded_mb = estimated_excluded / (1024 * 1024)
                lines.append(f"  - Estimated space saved: ~{excluded_mb:.1f} MB")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "106_dockerignore_analysis.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _parse_dockerignore(self, dockerignore_path: Path) -> List[str]:
        """Parse .dockerignore file and return patterns."""
        patterns = []
        try:
            content = dockerignore_path.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
        except (OSError, UnicodeDecodeError):
            pass

        return patterns

    def _analyze_build_context(
        self, root: Path, ignore_patterns: List[str]
    ) -> tuple[Set[Path], Set[Path], dict]:
        """Analyze build context and determine included/excluded files."""
        included = set()
        excluded = set()
        analysis = {
            "has_venv": False,
            "has_tests": False,
            "has_docs": False,
            "has_cache": False,
            "has_git": False,
        }

        # Walk directory tree
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            rel_path = file_path.relative_to(root)
            rel_str = str(rel_path)

            # Check if matches any ignore pattern
            is_ignored = False
            for pattern in ignore_patterns:
                # Handle patterns with/without trailing slash
                if pattern.endswith("/"):
                    # Directory pattern
                    if fnmatch.fnmatch(rel_str, pattern.rstrip("/") + "*"):
                        is_ignored = True
                        break
                else:
                    # File or glob pattern
                    if fnmatch.fnmatch(rel_str, pattern):
                        is_ignored = True
                        break

            if is_ignored:
                excluded.add(rel_path)

                # Track what's being excluded
                rel_lower = rel_str.lower()
                if "venv" in rel_lower or ".venv" in rel_lower:
                    analysis["has_venv"] = True
                if "test" in rel_lower:
                    analysis["has_tests"] = True
                if "docs" in rel_lower or "readme" in rel_lower:
                    analysis["has_docs"] = True
                if "__pycache__" in rel_lower or "cache" in rel_lower:
                    analysis["has_cache"] = True
                if ".git" in rel_lower:
                    analysis["has_git"] = True
            else:
                included.add(rel_path)

        return included, excluded, analysis
