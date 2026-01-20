from __future__ import annotations

import subprocess  # nosec B404 - Required for tool execution, paths validated
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


def _repo_has_py_files(root: Path) -> bool:
    """Fast check if there are Python files to scan."""
    for p in root.rglob("*.py"):
        parts = set(p.parts)
        if (
            ".venv" not in parts
            and "__pycache__" not in parts
            and "node_modules" not in parts
            and "dist" not in parts
            and "build" not in parts
            and "artifacts" not in parts
        ):
            return True
    return False


def _detect_framework_decorators(root: Path) -> set[str]:
    """Detect common framework decorators that should be whitelisted."""
    decorators = set()
    
    # Check for FastAPI
    for p in root.rglob("*.py"):
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if "from fastapi" in content or "import fastapi" in content:
                decorators.update([
                    "@app.get",
                    "@app.post", 
                    "@app.put",
                    "@app.delete",
                    "@app.patch",
                    "@router.get",
                    "@router.post",
                    "@router.put",
                    "@router.delete",
                    "@router.patch",
                    "@app.on_event",
                    "@app.middleware",
                ])
            if "from flask" in content or "import flask" in content:
                decorators.update([
                    "@app.route",
                    "@app.before_request",
                    "@app.after_request",
                    "@app.errorhandler",
                ])
            if "from django" in content or "import django" in content:
                decorators.update([
                    "@login_required",
                    "@permission_required",
                    "@staff_member_required",
                ])
        except Exception:
            continue
    
    return decorators


@dataclass
class VultureStep:
    name: str = "vulture"
    target: str = "."
    outfile: str = "logs/50_vulture.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        vulture = which("vulture")
        if not vulture:
            out.write_text(
                "vulture not found; skipping (pip install vulture)\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "missing vulture")

        if not _repo_has_py_files(ctx.root):
            out.write_text(
                "no .py files detected; skipping vulture\n", encoding="utf-8"
            )
            return StepResult(self.name, "SKIP", 0, "no python files")

        target_path = ctx.root / self.target
        
        # Create FastAPI/framework decorator whitelist if applicable
        whitelist_file = self._create_framework_whitelist(ctx)
        
        cmd = [
            vulture,
            str(target_path),
            "--exclude",
            "*venv*,*.venv*,.pybundle-venv,venv,env,.env,__pycache__,artifacts,build,dist,.git,.tox,node_modules",
            "--min-confidence",
            "60",  # Configurable confidence threshold
            "--sort-by-size",
        ]
        
        # Add whitelist if framework decorators detected
        if whitelist_file and whitelist_file.exists():
            cmd.extend(["--make-whitelist"])
            cmd.append(str(whitelist_file))

        try:
            result = subprocess.run(  # nosec B603 - Using full path from which()
                cmd,
                cwd=ctx.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            out.write_text(result.stdout, encoding="utf-8")
            elapsed = int((time.time() - start) * 1000)

            # Vulture exit codes:
            # 0 = no dead code found
            # 1 = usage/configuration error
            # 3 = dead code found (this is success!)
            if result.returncode in (0, 3):
                return StepResult(self.name, "OK", elapsed, "")
            else:
                return StepResult(
                    self.name, "FAIL", elapsed, f"exit {result.returncode}"
                )
        except subprocess.TimeoutExpired:
            out.write_text("vulture timed out after 120s\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 120000, "timeout")
        except Exception as e:
            out.write_text(f"vulture error: {e}\n", encoding="utf-8")
            return StepResult(self.name, "FAIL", 0, str(e))
    
    def _create_framework_whitelist(self, ctx: BundleContext) -> Path | None:
        """Create a temporary whitelist file for framework decorators."""
        decorators = _detect_framework_decorators(ctx.root)
        
        if not decorators:
            return None
        
        whitelist_path = ctx.workdir / "logs" / "vulture_whitelist.py"
        whitelist_path.parent.mkdir(parents=True, exist_ok=True)
        
        with whitelist_path.open("w", encoding="utf-8") as f:
            f.write("# Auto-generated whitelist for framework decorators\n")
            f.write("# These patterns are commonly used but appear unused to vulture\n\n")
            for decorator in sorted(decorators):
                # Create dummy functions to whitelist the decorator pattern
                func_name = decorator.replace("@", "").replace(".", "_")
                f.write(f"def {func_name}(): pass\n")
        
        return whitelist_path
