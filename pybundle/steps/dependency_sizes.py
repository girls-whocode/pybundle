from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
from dataclasses import dataclass

from .base import StepResult
from ..context import BundleContext


@dataclass
class DependencySizesStep:
    name: str = "dependency sizes"
    outfile: str = "meta/33_dependency_sizes.txt"
    top_n: int = 50  # Show top N largest packages

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        python = ctx.tools.python
        if not python:
            out.write_text("python not found; skipping\n", encoding="utf-8")
            return StepResult(self.name, "SKIP", 0, "missing python")

        try:
            # Get list of installed packages
            list_result = subprocess.run(  # nosec B603
                [python, "-m", "pip", "list", "--format=json"],
                cwd=ctx.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            
            if list_result.returncode != 0:
                out.write_text(f"pip list failed: {list_result.stderr}\n", encoding="utf-8")
                return StepResult(self.name, "FAIL", 0, "pip list failed")
            
            import json
            packages = json.loads(list_result.stdout)
            
            # Get size for each package
            package_sizes = []
            for pkg in packages:
                pkg_name = pkg["name"]
                try:
                    show_result = subprocess.run(  # nosec B603
                        [python, "-m", "pip", "show", pkg_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5,
                    )
                    
                    if show_result.returncode == 0:
                        # Parse Location from pip show output
                        location = None
                        for line in show_result.stdout.splitlines():
                            if line.startswith("Location:"):
                                location = line.split(":", 1)[1].strip()
                                break
                        
                        if location:
                            # Calculate directory size
                            from pathlib import Path
                            pkg_path = Path(location) / pkg_name.replace("-", "_")
                            if not pkg_path.exists():
                                pkg_path = Path(location) / pkg_name
                            
                            if pkg_path.exists() and pkg_path.is_dir():
                                size = sum(f.stat().st_size for f in pkg_path.rglob("*") if f.is_file())
                                package_sizes.append((pkg_name, pkg["version"], size))
                except Exception:
                    # Skip packages that fail
                    continue
            
            # Sort by size (descending)
            package_sizes.sort(key=lambda x: x[2], reverse=True)
            
            # Write results
            with out.open("w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write(f"TOP {min(self.top_n, len(package_sizes))} LARGEST DEPENDENCIES\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Total packages analyzed: {len(packages)}\n")
                f.write(f"Packages with size data: {len(package_sizes)}\n\n")
                
                if package_sizes:
                    # Calculate total size
                    total_size = sum(size for _, _, size in package_sizes)
                    f.write(f"Total size: {self._format_size(total_size)}\n\n")
                    
                    f.write(f"{'Package':<40} {'Version':<15} {'Size':>15}\n")
                    f.write("-" * 70 + "\n")
                    
                    for pkg_name, version, size in package_sizes[:self.top_n]:
                        f.write(f"{pkg_name:<40} {version:<15} {self._format_size(size):>15}\n")
                else:
                    f.write("No package size data available.\n")
            
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "OK", elapsed, None)
            
        except subprocess.TimeoutExpired:
            out.write_text("Analysis timed out\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", int((time.time() - start) * 1000), "timeout")
        except Exception as e:
            out.write_text(f"Error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", int((time.time() - start) * 1000), str(e))

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
