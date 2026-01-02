from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .base import StepResult
from pybundle.context import BundleContext
from pybundle.tools import which
from pybundle.policy import AIContextPolicy, PathFilter

BIN_EXTS = {
    ".appimage", ".deb", ".rpm", ".exe", ".msi", ".dmg", ".pkg",
    ".so", ".dll", ".dylib",
}
DB_EXTS = {".db", ".sqlite", ".sqlite3"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z"}

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
    policy: AIContextPolicy | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        policy = self.policy or AIContextPolicy()

        # allow overrides
        exclude_dirs = set(self.excludes) if self.excludes else set(policy.exclude_dirs)
        filt = PathFilter(exclude_dirs=exclude_dirs, exclude_file_exts=set(policy.exclude_file_exts))

        out = ctx.metadir / "10_tree.txt"
        out.parent.mkdir(parents=True, exist_ok=True)

        root = ctx.root
        lines: list[str] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)
            rel_dp = dp.relative_to(root)
            depth = 0 if rel_dp == Path(".") else len(rel_dp.parts)

            if depth > self.max_depth:
                dirnames[:] = []
                continue

            # prune dirs (name + venv-structure)
            kept = []
            for d in dirnames:
                if filt.should_prune_dir(dp, d):
                    continue
                kept.append(d)
            dirnames[:] = kept

            for fn in filenames:
                p = dp / fn
                if not filt.should_include_file(root, p):
                    continue
                lines.append(str(p.relative_to(root)))

        lines.sort()
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        dur = int(time.time() - start)
        return StepResult(self.name, "PASS", dur, "python-walk")

@dataclass
class LargestFilesStep:
    name: str = "largest files"
    limit: int = 80
    excludes: list[str] | None = None
    policy: AIContextPolicy | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        policy = self.policy or AIContextPolicy()

        exclude_dirs = set(self.excludes) if self.excludes else set(policy.exclude_dirs)
        filt = PathFilter(exclude_dirs=exclude_dirs, exclude_file_exts=set(policy.exclude_file_exts))

        out = ctx.metadir / "11_largest_files.txt"
        out.parent.mkdir(parents=True, exist_ok=True)

        files: list[tuple[int, str]] = []
        root = ctx.root

        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)

            kept = []
            for d in dirnames:
                if filt.should_prune_dir(dp, d):
                    continue
                kept.append(d)
            dirnames[:] = kept

            for fn in filenames:
                p = dp / fn
                if not filt.should_include_file(root, p):
                    continue
                try:
                    size = p.stat().st_size
                except OSError:
                    continue
                files.append((size, str(p.relative_to(root))))

        files.sort(key=lambda x: x[0], reverse=True)
        lines = [f"{size}\t{path}" for size, path in files[: self.limit]]
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        dur = int(time.time() - start)
        return StepResult(self.name, "PASS", dur, f"count={len(files)}")

