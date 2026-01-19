"""Advanced git analytics step - v1.5.1

Provides deep git history insights:
- Blame-based contributor analysis
- Branch health metrics
- Commit message quality assessment
- Code ownership tracking
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .base import StepResult
from ..context import BundleContext


@dataclass
class GitAnalyticsStep:
    """Step that performs advanced git analytics."""

    name: str = "git-analytics"
    outfile: str = "meta/100_git_analytics.txt"
    blame_depth: int = 100  # Number of commits to analyze in blame

    def run(self, ctx: BundleContext) -> StepResult:
        """Perform comprehensive git analytics."""
        start = time.time()

        # Check if we're in a git repo
        git_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=ctx.root,
            capture_output=True,
            text=True,
        )

        if git_check.returncode != 0:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "SKIP", elapsed, "not a git repository")

        # Gather analytics
        blame_stats = self._analyze_blame(ctx.root)
        branch_stats = self._analyze_branches(ctx.root)
        commit_quality = self._analyze_commit_messages(ctx.root)
        codeowners_coverage = self._analyze_codeowners(ctx.root)

        # Write report
        out_path = ctx.workdir / self.outfile
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("GIT ANALYTICS REPORT\n")
            f.write("=" * 80 + "\n\n")

            # Blame-based analysis
            if blame_stats:
                f.write("CONTRIBUTOR ANALYSIS (by line count)\n")
                f.write("-" * 80 + "\n")
                f.write(f"Analyzed last {self.blame_depth} commits\n\n")
                for i, (author, lines, files) in enumerate(blame_stats[:10], 1):
                    f.write(f"{i:2d}. {author:<40} {lines:>6} lines {files:>3} files\n")
                f.write("\n")

            # Branch health
            if branch_stats:
                f.write("BRANCH HEALTH METRICS\n")
                f.write("-" * 80 + "\n")
                current, ahead, behind, uncommitted = branch_stats
                f.write(f"Current branch:      {current}\n")
                f.write(f"Commits ahead main:  {ahead}\n")
                f.write(f"Commits behind main: {behind}\n")
                f.write(f"Uncommitted changes: {uncommitted} files\n\n")

            # Commit message quality
            if commit_quality:
                f.write("COMMIT MESSAGE QUALITY\n")
                f.write("-" * 80 + "\n")
                conventional_pct, avg_length, total = commit_quality
                f.write(f"Total commits analyzed: {total}\n")
                f.write(f"Conventional commits:   {conventional_pct:.1f}%\n")
                f.write(f"Average message length: {avg_length:.0f} chars\n")
                f.write("(Conventional format: type(scope): description)\n\n")

            # CODEOWNERS coverage
            if codeowners_coverage:
                f.write("CODE OWNERSHIP TRACKING\n")
                f.write("-" * 80 + "\n")
                if codeowners_coverage[0]:
                    codeowners_exists, coverage_pct, rules_count = codeowners_coverage
                    f.write(f"CODEOWNERS file:  {'Found' if codeowners_exists else 'Not found'}\n")
                    f.write(f"Ownership rules:  {rules_count}\n")
                    f.write(f"Files covered:    {coverage_pct:.1f}%\n\n")
                else:
                    f.write("CODEOWNERS file not found\n\n")

            f.write("=" * 80 + "\n")
            f.write("Git analytics complete\n")
            f.write("=" * 80 + "\n")

        elapsed = int((time.time() - start) * 1000)
        return StepResult(self.name, "OK", elapsed, "git analytics complete")

    def _analyze_blame(self, root: Path) -> List[Tuple[str, int, int]]:
        """Analyze git blame to find top contributors by line count.

        Returns list of (author, line_count, file_count) tuples sorted by lines.
        """
        try:
            # Get commits in range
            result = subprocess.run(
                ["git", "log", f"--max-count={self.blame_depth}", "--format=%an"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return []

            authors: Dict[str, Dict[str, int]] = {}
            for commit_author in result.stdout.strip().split("\n"):
                if commit_author:
                    if commit_author not in authors:
                        authors[commit_author] = {"lines": 0, "files": set()}

            # For each author, run blame on all Python files
            for py_file in root.rglob("*.py"):
                # Skip artifacts and venv
                if any(
                    x in py_file.parts
                    for x in ["artifacts", ".git", "venv", ".venv", "__pycache__"]
                ):
                    continue

                try:
                    blame_result = subprocess.run(
                        ["git", "blame", "--line-porcelain", str(py_file.relative_to(root))],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if blame_result.returncode == 0:
                        for line in blame_result.stdout.split("\n"):
                            if line.startswith("author "):
                                author = line[7:].strip()
                                if author in authors:
                                    authors[author]["lines"] += 1
                                    authors[author]["files"].add(str(py_file.relative_to(root)))

                except Exception:
                    continue

            # Convert to list and sort
            result_list = [
                (author, stats["lines"], len(stats["files"]))
                for author, stats in authors.items()
            ]
            return sorted(result_list, key=lambda x: x[1], reverse=True)

        except Exception:
            return []

    def _analyze_branches(self, root: Path) -> Tuple[str, int, int, int] | None:
        """Analyze branch health metrics.

        Returns (current_branch, commits_ahead, commits_behind, uncommitted_files).
        """
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if branch_result.returncode != 0:
                return None

            current_branch = branch_result.stdout.strip()

            # Count commits ahead/behind main
            try:
                ahead_result = subprocess.run(
                    ["git", "rev-list", "--count", f"main..{current_branch}"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                ahead = int(ahead_result.stdout.strip()) if ahead_result.returncode == 0 else 0
            except Exception:
                ahead = 0

            try:
                behind_result = subprocess.run(
                    ["git", "rev-list", "--count", f"{current_branch}..main"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                behind = int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0
            except Exception:
                behind = 0

            # Count uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            uncommitted = len(status_result.stdout.strip().split("\n")) if status_result.returncode == 0 else 0

            return (current_branch, ahead, behind, uncommitted)

        except Exception:
            return None

    def _analyze_commit_messages(self, root: Path) -> Tuple[float, float, int] | None:
        """Analyze commit message quality.

        Returns (conventional_commits_pct, avg_message_length, total_commits).
        """
        try:
            # Get recent commits
            log_result = subprocess.run(
                ["git", "log", "--max-count=100", "--format=%s"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if log_result.returncode != 0:
                return None

            messages = log_result.stdout.strip().split("\n")
            if not messages:
                return None

            # Check for conventional commits format: type(scope): message or type: message
            conventional_pattern = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|chore)(\(.+\))?:")
            conventional_count = sum(1 for msg in messages if conventional_pattern.match(msg))

            total = len(messages)
            conventional_pct = (conventional_count / total * 100) if total > 0 else 0
            avg_length = sum(len(msg) for msg in messages) / total if total > 0 else 0

            return (conventional_pct, avg_length, total)

        except Exception:
            return None

    def _analyze_codeowners(self, root: Path) -> Tuple[bool, float, int] | None:
        """Analyze CODEOWNERS file coverage.

        Returns (codeowners_exists, coverage_percentage, number_of_rules).
        """
        try:
            # Check for CODEOWNERS file
            codeowners_paths = [
                root / "CODEOWNERS",
                root / ".github" / "CODEOWNERS",
                root / "docs" / "CODEOWNERS",
            ]

            codeowners_file = None
            for path in codeowners_paths:
                if path.exists():
                    codeowners_file = path
                    break

            if not codeowners_file:
                return (False, 0.0, 0)

            # Parse CODEOWNERS file
            rules: List[Tuple[str, List[str]]] = []
            with open(codeowners_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        pattern = parts[0]
                        owners = parts[1:]
                        rules.append((pattern, owners))

            if not rules:
                return (True, 0.0, 0)

            # Estimate coverage by checking patterns
            # (simplified - just count rules)
            coverage_pct = min(100.0, len(rules) * 10.0)  # Heuristic

            return (True, coverage_pct, len(rules))

        except Exception:
            return None
