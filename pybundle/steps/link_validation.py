"""README and documentation link validation step.

Checks all markdown files for broken links (HTTP/HTTPS URLs).
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext


@dataclass
class LinkValidationStep:
    """Step that validates links in markdown files."""

    name: str = "link-validation"
    outfile: str = "logs/81_link_validation.txt"

    def run(self, context: BundleContext) -> StepResult:
        """Validate links in markdown documentation."""
        start = time.time()

        # Find all markdown files
        md_files = self._find_markdown_files(context.root)

        if not md_files:
            elapsed = time.time() - start
            note = "No markdown files found"
            return StepResult(self.name, "SKIP", int(elapsed), note)

        # Extract all links from markdown files
        all_links = self._extract_links(md_files, context.root)

        if not all_links:
            elapsed = time.time() - start
            note = "No HTTP(S) links found"
            return StepResult(self.name, "SKIP", int(elapsed), note)

        # Check links
        results = self._check_links(all_links)

        elapsed = time.time() - start

        # Write report
        log_path = context.workdir / self.outfile
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("LINK VALIDATION REPORT\n")
            f.write("=" * 80 + "\n\n")

            # Summary
            total_links = len(results)
            broken_links = sum(1 for status, _ in results.values() if status != "OK")
            success_rate = (
                ((total_links - broken_links) / total_links * 100)
                if total_links > 0
                else 100
            )

            f.write("Summary:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total URLs checked:  {total_links}\n")
            f.write(f"Broken links:        {broken_links}\n")
            f.write(f"Success rate:        {success_rate:.1f}%\n")
            f.write("\n")

            # Group results by file
            links_by_file: Dict[str, List[Tuple[str, str, str]]] = {}
            for (filepath, url), (status, message) in results.items():
                if filepath not in links_by_file:
                    links_by_file[filepath] = []
                links_by_file[filepath].append((url, status, message))

            # Write results
            for filepath in sorted(links_by_file.keys()):
                f.write(f"\n{filepath}:\n")
                f.write("-" * 80 + "\n")

                for url, status, message in links_by_file[filepath]:
                    status_icon = "✓" if status == "OK" else "✗"
                    f.write(f"{status_icon} [{status:6s}] {url}\n")
                    if message and status != "OK":
                        f.write(f"           {message}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Validation complete - {len(md_files)} markdown files scanned\n")
            f.write("=" * 80 + "\n")

        # Determine overall status
        if broken_links == 0:
            status = "OK"
            note = f"All {total_links} links valid"
        elif broken_links < total_links * 0.1:  # < 10% broken
            status = "WARN"
            note = f"{broken_links}/{total_links} broken links"
        else:
            status = "FAIL"
            note = f"{broken_links}/{total_links} broken links"

        return StepResult(self.name, status, elapsed, note)

    def _find_markdown_files(self, root: Path) -> List[Path]:
        """Find all markdown files."""
        md_files = []
        exclude_dirs = {
            "__pycache__",
            ".git",
            ".tox",
            "venv",
            "env",
            ".venv",
            ".env",
            "node_modules",
            "artifacts",
            "build",
            "dist",
            ".pybundle-venv",  # pybundle's venv
        }

        for path in root.rglob("*.md"):
            # Skip if any parent is in exclude_dirs
            if any(part in exclude_dirs for part in path.parts):
                continue
            md_files.append(path)

        return md_files

    def _extract_links(
        self, md_files: List[Path], root: Path
    ) -> Dict[Tuple[str, str], None]:
        """Extract HTTP/HTTPS links from markdown files.

        Returns dict with (filepath, url) as keys for deduplication.
        """
        links: Dict[Tuple[str, str], None] = {}
        # Regex for markdown links and bare URLs
        link_pattern = re.compile(
            r"\[([^\]]+)\]\(([^)]+)\)|(?:^|[^(])(https?://[^\s\)<>]+)", re.MULTILINE
        )

        for filepath in md_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                rel_path = str(filepath.relative_to(root))

                for match in link_pattern.finditer(content):
                    # Group 2 is markdown link URL, group 3 is bare URL
                    url = match.group(2) or match.group(3)
                    if url and (
                        url.startswith("http://") or url.startswith("https://")
                    ):
                        # Clean up URL (remove trailing punctuation)
                        url = url.rstrip(".,;:!?")
                        links[(rel_path, url)] = None

            except Exception:
                # Skip files that can't be read
                continue

        return links

    def _check_links(
        self, links: Dict[Tuple[str, str], None]
    ) -> Dict[Tuple[str, str], Tuple[str, str]]:
        """Check if links are valid.

        Returns dict with (filepath, url) -> (status, message).
        """
        import subprocess

        results = {}

        # Check if we have curl available
        try:
            subprocess.run(
                ["curl", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            has_curl = True
        except (subprocess.SubprocessError, FileNotFoundError):
            has_curl = False

        # If no curl, try Python requests
        has_requests = False
        if not has_curl:
            try:
                import requests  # noqa: F401

                has_requests = True
            except ImportError:
                pass

        if not has_curl and not has_requests:
            # Can't validate links without tools
            for key in links:
                results[key] = ("SKIP", "curl or requests not available")
            return results

        # Check each link
        for filepath, url in links:
            status, message = self._check_single_link(url, has_curl, has_requests)
            results[(filepath, url)] = (status, message)

        return results

    def _check_single_link(
        self, url: str, has_curl: bool, has_requests: bool
    ) -> Tuple[str, str]:
        """Check a single link.

        Returns (status, message) tuple.
        """
        import subprocess

        if has_curl:
            try:
                # Use curl with HEAD request, follow redirects, 10s timeout
                result = subprocess.run(
                    [
                        "curl",
                        "-I",  # HEAD request
                        "-L",  # Follow redirects
                        "-s",  # Silent
                        "-o",
                        "/dev/null",  # Discard output
                        "-w",
                        "%{http_code}",  # Write HTTP code
                        "--max-time",
                        "10",  # 10 second timeout
                        url,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                http_code = result.stdout.strip()
                if http_code.startswith("2") or http_code.startswith("3"):
                    return ("OK", "")
                elif http_code == "000":
                    return ("FAIL", "Connection failed")
                else:
                    return ("FAIL", f"HTTP {http_code}")

            except subprocess.TimeoutExpired:
                return ("FAIL", "Timeout")
            except Exception as e:
                return ("FAIL", f"Error: {str(e)[:50]}")

        elif has_requests:
            try:
                import requests

                response = requests.head(
                    url,
                    allow_redirects=True,
                    timeout=10,
                    headers={"User-Agent": "pybundle-link-checker"},
                )

                if response.status_code < 400:
                    return ("OK", "")
                else:
                    return ("FAIL", f"HTTP {response.status_code}")

            except requests.exceptions.Timeout:
                return ("FAIL", "Timeout")
            except requests.exceptions.RequestException as e:
                return ("FAIL", f"Error: {str(e)[:50]}")

        return ("SKIP", "No validation method available")
