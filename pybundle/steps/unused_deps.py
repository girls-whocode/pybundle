from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class UnusedDependenciesStep:
    name: str = "unused dependencies"
    outfile: str = "meta/31_unused_packages.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        python = ctx.tools.python
        if not python:
            out.write_text("python not found; skipping\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "missing python")

        try:
            # Get all installed packages
            pip_freeze_result = subprocess.run(  # nosec B603
                [python, "-m", "pip", "freeze"],
                cwd=ctx.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )

            if pip_freeze_result.returncode != 0:
                out.write_text(
                    f"pip freeze failed: {pip_freeze_result.stderr}\n", encoding="utf-8"
                )
                return StepResult(self.name, "FAIL", 0, "pip freeze failed")

            # Parse installed packages (normalize names)
            installed_packages: list[str] = []
            for line in pip_freeze_result.stdout.splitlines():
                if line and not line.startswith("-") and "==" in line:
                    pkg_name = line.split("==")[0].strip().lower().replace("_", "-")
                    installed_packages.append(pkg_name)

            # Get imported modules from source code
            imported_modules = self._get_imported_modules(ctx.root)

            # Find unused packages (installed but not imported)
            # Note: This is a heuristic - some packages are used indirectly
            unused = sorted(set(installed_packages) - imported_modules)
            
            # Categorize by confidence level
            likely_unused, maybe_unused = self._categorize_by_confidence(
                unused, ctx.root
            )

            # Write results
            with out.open("w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("UNUSED DEPENDENCIES ANALYSIS\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Total installed packages: {len(installed_packages)}\n")
                f.write(f"Total imported modules: {len(imported_modules)}\n")
                f.write(f"Potentially unused packages: {len(unused)}\n\n")

                if likely_unused:
                    f.write("LIKELY UNUSED (high confidence - no obvious indirect usage):\n")
                    f.write("These packages are good candidates for removal.\n\n")
                    for pkg in likely_unused:
                        f.write(f"  - {pkg}\n")
                    f.write("\n")
                
                if maybe_unused:
                    f.write("MAYBE UNUSED (lower confidence - might be plugins/indirect deps):\n")
                    f.write("These may be used indirectly or as plugins. Verify before removing.\n\n")
                    for pkg in maybe_unused:
                        f.write(f"  - {pkg}\n")
                    f.write("\n")
                
                if not unused:
                    f.write("No obviously unused packages detected.\n")

            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "OK", elapsed, "")

        except subprocess.TimeoutExpired:
            out.write_text("Analysis timed out\n", encoding="utf-8")
            return StepResult(
                self.name, "FAIL", int((time.time() - start) * 1000), "timeout"
            )
        except Exception as e:
            out.write_text(f"Error: {e}\n", encoding="utf-8")
            return StepResult(
                self.name, "FAIL", int((time.time() - start) * 1000), str(e)
            )

    def _get_imported_modules(self, root: Path) -> set[str]:
        """Extract top-level module names from import statements."""
        imported = set()

        for py_file in root.rglob("*.py"):
            # Skip venv and common excluded directories
            parts = set(py_file.parts)
            if any(
                x in parts
                for x in [
                    ".venv",
                    "venv",
                    "__pycache__",
                    "node_modules",
                    "dist",
                    "build",
                    "artifacts",
                    ".git",
                    ".tox",
                ]
            ):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    # Match: import foo, from foo import bar
                    if line.startswith("import "):
                        module = line[7:].split()[0].split(".")[0].split(",")[0].strip()
                        imported.add(module.lower().replace("_", "-"))
                    elif line.startswith("from "):
                        line_parts = line.split()
                        if len(line_parts) >= 2:
                            module = line_parts[1].split(".")[0].strip()
                            imported.add(module.lower().replace("_", "-"))
            except Exception:
                continue

        return imported
    
    def _categorize_by_confidence(
        self, unused: list[str], root: Path
    ) -> tuple[list[str], list[str]]:
        """Categorize unused packages by confidence level.
        
        Returns:
            (likely_unused, maybe_unused) tuple of package lists
        """
        # Packages that are commonly indirect deps or plugins (lower confidence)
        indirect_patterns = {
            # Build/dev tools often used indirectly
            "setuptools", "wheel", "pip", "build",
            # Testing plugins
            "pytest-", "coverage", "pluggy",
            # Type checking stubs
            "types-", "-stubs",
            # Common indirect deps
            "certifi", "charset-normalizer", "idna", "urllib3",
            "six", "packaging", "pyparsing",
            # Web framework plugins often auto-discovered
            "uvicorn", "gunicorn", "hypercorn",
            # Database drivers (might be dynamically loaded)
            "psycopg2", "pymysql", "cx-oracle",
            # Celery/async workers
            "celery", "redis", "kombu", "amqp",
        }
        
        likely_unused = []
        maybe_unused = []
        
        for pkg in unused:
            # Check if package matches indirect dependency patterns
            is_likely_indirect = any(
                pattern in pkg for pattern in indirect_patterns
            )
            
            # Check if mentioned in config files (pyproject.toml, setup.py, etc.)
            mentioned_in_config = self._is_mentioned_in_config(pkg, root)
            
            if is_likely_indirect or mentioned_in_config:
                maybe_unused.append(pkg)
            else:
                likely_unused.append(pkg)
        
        return likely_unused, maybe_unused
    
    def _is_mentioned_in_config(self, pkg: str, root: Path) -> bool:
        """Check if package is mentioned in config files."""
        config_files = [
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "requirements-dev.txt",
        ]
        
        for config_file in config_files:
            config_path = root / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text(encoding="utf-8", errors="ignore")
                    # Normalize package name for comparison
                    if pkg in content or pkg.replace("-", "_") in content:
                        return True
                except Exception:
                    continue
        
        return False
