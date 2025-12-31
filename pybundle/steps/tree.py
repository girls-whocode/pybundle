from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which


DEFAULT_EXCLUDES = [
    ".git",
    ".venv",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "artifacts",
    ".cache",
]


def _is_excluded(rel: Path, excludes: set[str]) -> bool:
    # Exclude if any path component matches
    for part in rel.parts:
        if part in excludes:
            return True
    return False


@dataclass
class TreeStep:
    name: str = "tree (filtered)"
    max_depth: int = 4
    excludes: list[str] | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        import time

        start = time.time()
        excludes = set(self.excludes or DEFAULT_EXCLUDES)
        out = ctx.metadir / "10_tree.txt"
        out.parent.mkdir(parents=True, exist_ok=True)

        tree_bin = which("tree")
        if tree_bin:
            # Prefer `tree` if available
            exclude_pat = "|".join(self.excludes or DEFAULT_EXCLUDES)
            cmd = [
                tree_bin,
                "-a",
                "-L",
                str(self.max_depth),
                "-I",
                exclude_pat,
            ]
            text = "## CMD: " + " ".join(cmd) + "\n\n"
            try:
                import subprocess

                cp = subprocess.run(cmd, cwd=str(ctx.root), text=True, capture_output=True, check=False)
                text += (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
                out.write_text(ctx.redact_text(text), encoding="utf-8")
                dur = int(time.time() - start)
                # tree returns 0 even if it prints warnings; treat nonzero as PASS unless strict later
                return StepResult(self.name, "PASS", dur, "" if cp.returncode == 0 else f"exit={cp.returncode}")
            except Exception as e:
                out.write_text(ctx.redact_text(text + f"\nEXCEPTION: {e}\n"), encoding="utf-8")
                dur = int(time.time() - start)
                return StepResult(self.name, "PASS", dur, f"fallback (tree exception: {e})")

        # Fallback: find-like listing implemented in Python
        lines: list[str] = []
        root = ctx.root

        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)
            rel_dp = dp.relative_to(root)

            # prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in excludes]

            depth = 0 if rel_dp == Path(".") else len(rel_dp.parts)
            if depth > self.max_depth:
                dirnames[:] = []
                continue

            for fn in filenames:
                p = dp / fn
                rel = p.relative_to(root)
                if _is_excluded(rel, excludes):
                    continue
                # Only list files up to max_depth (depth is dir depth; file is within it)
                if depth <= self.max_depth:
                    lines.append(str(rel))

        lines.sort()
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        dur = int(time.time() - start)
        return StepResult(self.name, "PASS", dur, "python-walk fallback")


@dataclass
class LargestFilesStep:
    name: str = "largest files"
    limit: int = 80
    excludes: list[str] | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        import time

        start = time.time()
        excludes = set(self.excludes or DEFAULT_EXCLUDES)
        out = ctx.metadir / "11_largest_files.txt"
        out.parent.mkdir(parents=True, exist_ok=True)

        files: list[tuple[int, str]] = []
        root = ctx.root

        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)
            rel_dp = dp.relative_to(root)

            dirnames[:] = [d for d in dirnames if d not in excludes]

            for fn in filenames:
                p = dp / fn
                rel = p.relative_to(root)
                if _is_excluded(rel, excludes):
                    continue
                try:
                    size = p.stat().st_size
                except OSError:
                    continue
                files.append((size, str(rel)))

        files.sort(key=lambda x: x[0], reverse=True)
        lines = [f"{size}\t{path}" for size, path in files[: self.limit]]
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        dur = int(time.time() - start)
        return StepResult(self.name, "PASS", dur, f"count={len(files)}")
