"""API documentation generation step using pdoc.

Generates HTML API documentation and validates docstring parsing.
"""

import shutil
import subprocess
import time
from pathlib import Path
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext


@dataclass
class ApiDocsStep:
    """Step that generates API documentation using pdoc."""

    name: str = "api-docs"
    outfile: str = "logs/82_api_docs.txt"

    def run(self, context: BundleContext) -> StepResult:
        """Generate API documentation."""
        start = time.time()

        # Check if pdoc is available and get version
        pdoc_path = shutil.which("pdoc")
        if not pdoc_path:
            elapsed = time.time() - start
            note = "pdoc not installed (pip install pdoc)"
            return StepResult(self.name, "SKIP", int(elapsed), note)

        # Get pdoc version for diagnostics
        pdoc_version = None
        try:
            version_result = subprocess.run(
                ["pdoc", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pdoc_version = version_result.stdout.strip() or version_result.stderr.strip()
        except Exception:
            pdoc_version = "unknown"

        # Find Python package(s) in project
        packages = self._find_packages(context.root)

        if not packages:
            elapsed = time.time() - start
            note = "No Python packages found"
            return StepResult(self.name, "SKIP", int(elapsed), note)

        # Create output directory in meta
        output_dir = context.workdir / "meta/82_api_docs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate docs for each package
        success_count = 0
        error_count = 0
        errors = []

        for package in packages:
            try:
                # Use pdoc v14+ syntax (--output-dir instead of --html + --output-dir)
                # Try modern syntax first, fallback to legacy if it fails
                result = subprocess.run(
                    [
                        "pdoc",
                        "--output-dir",
                        str(output_dir),
                        str(package),
                    ],
                    cwd=context.root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    success_count += 1
                else:
                    error_count += 1
                    error_msg = result.stderr or result.stdout
                    errors.append((package.name, result.returncode, error_msg))

            except subprocess.TimeoutExpired:
                error_count += 1
                errors.append((package.name, -1, "Timeout after 60s"))
            except Exception as e:
                error_count += 1
                errors.append((package.name, -1, str(e)))

        elapsed = time.time() - start

        # Write summary report
        log_path = context.workdir / self.outfile
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("API DOCUMENTATION GENERATION\n")
            f.write("=" * 80 + "\n\n")

            f.write("Environment:\n")
            f.write("-" * 80 + "\n")
            f.write(f"pdoc path:       {pdoc_path}\n")
            f.write(f"pdoc version:    {pdoc_version}\n")
            f.write("\n")

            f.write("Summary:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Packages processed:  {len(packages)}\n")
            f.write(f"Successful:          {success_count}\n")
            f.write(f"Failed:              {error_count}\n")
            f.write(f"Output directory:    {output_dir.relative_to(context.workdir)}\n")
            f.write("\n")

            if errors:
                f.write("Errors:\n")
                f.write("-" * 80 + "\n")
                for package_name, retcode, error_msg in errors:
                    f.write(f"\n{package_name}:\n")
                    f.write(f"  Exit code: {retcode}\n")
                    # Limit error message length
                    if len(error_msg) > 500:
                        error_msg = error_msg[:500] + "\n... (truncated)"
                    f.write(f"  Error: {error_msg}\n")
                    
                    # Add actionable fix suggestions
                    f.write("\n  💡 How to fix:\n")
                    if "--html" in error_msg or "unrecognized arguments" in error_msg:
                        f.write("     - Your pdoc version may not support --html flag\n")
                        f.write("     - pdoc < 14.0: use 'pdoc --html'\n")
                        f.write("     - pdoc >= 14.0: use 'pdoc --output-dir'\n")
                        f.write(f"     - Detected version: {pdoc_version}\n")
                        f.write("     - Try: pip install --upgrade pdoc\n")
                    elif "Timeout" in error_msg:
                        f.write("     - Package is too large or has import errors\n")
                        f.write("     - Check for circular imports or missing dependencies\n")
                    else:
                        f.write("     - Check that package imports work: python -c 'import <package>'\n")
                        f.write("     - Verify dependencies are installed\n")
                        f.write("     - Run manually: pdoc --output-dir docs/ <package>\n")

            if success_count > 0:
                f.write("\nGenerated Documentation:\n")
                f.write("-" * 80 + "\n")
                # List generated HTML files
                html_files = sorted(output_dir.rglob("*.html"))
                for html_file in html_files[:20]:  # Limit to first 20
                    rel_path = html_file.relative_to(context.workdir)
                    f.write(f"  {rel_path}\n")
                if len(html_files) > 20:
                    f.write(f"  ... and {len(html_files) - 20} more files\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("Documentation generation complete\n")
            f.write("=" * 80 + "\n")

        # Determine status
        if error_count == 0:
            status = "OK"
            note = f"Generated docs for {success_count} package(s)"
        elif success_count > 0:
            status = "WARN"
            note = f"{success_count} OK, {error_count} failed"
        else:
            status = "FAIL"
            note = f"All {error_count} package(s) failed"

        return StepResult(self.name, status, int(elapsed), note)

    def _find_packages(self, root: Path) -> list[Path]:
        """Find Python packages (directories with __init__.py).

        Returns top-level packages only, excluding common directories.
        """
        packages = []
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
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "htmlcov",
            ".egg-info",
            "tests",
            "test",
            ".pybundle-venv",  # pybundle's venv
        }

        # Look for directories with __init__.py at root level first
        for item in root.iterdir():
            if item.is_dir() and item.name not in exclude_dirs:
                init_file = item / "__init__.py"
                if init_file.exists():
                    packages.append(item)

        # If no packages found at root, look one level deeper
        if not packages:
            for item in root.iterdir():
                if item.is_dir() and item.name not in exclude_dirs:
                    for subitem in item.iterdir():
                        if subitem.is_dir() and subitem.name not in exclude_dirs:
                            init_file = subitem / "__init__.py"
                            if init_file.exists():
                                packages.append(subitem)

        return packages
