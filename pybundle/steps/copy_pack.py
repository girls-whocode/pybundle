from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .base import StepResult
from ..context import BundleContext


DEFAULT_EXCLUDE_DIRS = {
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
}

DEFAULT_INCLUDE_FILES = [
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "pdm.lock",
    "uv.lock",
    "setup.cfg",
    "setup.py",
    "mypy.ini",
    "ruff.toml",
    ".ruff.toml",
    "pytest.ini",
    "tox.ini",
    ".python-version",
]

DEFAULT_INCLUDE_DIRS = [
    "src",
    "tests",
    "tools",
]

DEFAULT_INCLUDE_GLOBS = [
    # common python project layouts
    "*.py",
    "*/**/*.py",
    # templates/assets if present
    "templates/**/*",
    "static/**/*",
]


def _is_excluded_path(rel: Path, exclude_dirs: set[str]) -> bool:
    for part in rel.parts:
        if part in exclude_dirs:
            return True
    return False


def _safe_copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # preserve mode + timestamps where possible
    shutil.copy2(src, dst)


def _copy_tree_filtered(src_dir: Path, dst_dir: Path, exclude_dirs: set[str]) -> tuple[int, int]:
    """
    Copy directory tree while pruning excluded directories.
    Returns: (files_copied, dirs_pruned)
    """
    files = 0
    pruned = 0

    for dirpath, dirnames, filenames in os.walk(src_dir):
        dp = Path(dirpath)
        rel = dp.relative_to(src_dir)

        # prune excluded dirs
        kept = []
        for d in dirnames:
            if d in exclude_dirs:
                pruned += 1
            else:
                kept.append(d)
        dirnames[:] = kept

        for fn in filenames:
            sp = dp / fn
            rel_file = (src_dir / rel / fn).relative_to(src_dir)
            # skip files that live under excluded dirs (paranoia)
            if _is_excluded_path(rel_file, exclude_dirs):
                continue

            tp = dst_dir / rel / fn
            try:
                _safe_copy_file(sp, tp)
                files += 1
            except OSError:
                # keep going; bundle is best-effort
                continue

    return files, pruned


def _guess_package_dirs(root: Path, exclude_dirs: set[str]) -> list[Path]:
    """
    Heuristic: top-level dirs containing __init__.py are packages.
    """
    out: list[Path] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if p.name in exclude_dirs:
            continue
        if (p / "__init__.py").is_file():
            out.append(p)
    return out


@dataclass
class CuratedCopyStep:
    name: str = "copy curated source pack"
    include_files: list[str] | None = None
    include_dirs: list[str] | None = None
    include_globs: list[str] | None = None
    exclude_dirs: set[str] | None = None
    max_files: int = 20000  # safety valve

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        dst_root = ctx.srcdir  # bundle/src
        dst_root.mkdir(parents=True, exist_ok=True)

        exclude = set(self.exclude_dirs or DEFAULT_EXCLUDE_DIRS)
        include_files = self.include_files or DEFAULT_INCLUDE_FILES
        include_dirs = self.include_dirs or DEFAULT_INCLUDE_DIRS
        include_globs = self.include_globs or DEFAULT_INCLUDE_GLOBS

        copied = 0
        pruned = 0

        # 1) Include well-known top-level files if present
        for rel_file in include_files:
            sp = ctx.root / rel_file
            if sp.is_file():
                if _is_excluded_path(Path(rel_file), exclude):
                    continue
                try:
                    _safe_copy_file(sp, dst_root / rel_file)
                    copied += 1
                except OSError:
                    pass

        # 2) Include common top-level dirs (src/tests/tools)
        for rel_dir in include_dirs:
            sp = ctx.root / rel_dir
            if sp.is_dir() and rel_dir not in exclude:
                if _is_excluded_path(Path(rel_file), exclude):
                    continue
                files_copied, dirs_pruned = _copy_tree_filtered(sp, dst_root / rel_dir, exclude)
                copied += files_copied
                pruned += dirs_pruned
                if copied >= self.max_files:
                    break

        # 3) Include detected package dirs at root (if not already copied)
        if copied < self.max_files:
            for pkg_dir in _guess_package_dirs(ctx.root, exclude):
                rel_pkg_name = pkg_dir.name
                if (dst_root / rel_pkg_name).exists():
                    continue
                files_copied, dirs_pruned = _copy_tree_filtered(pkg_dir, dst_root / rel_pkg_name, exclude)
                copied += files_copied
                pruned += dirs_pruned
                if copied >= self.max_files:
                    break

        # 4) Optional globs (best-effort; avoid deep explosion by pruning excluded dirs)
        # We’ll apply globs but skip anything under excluded dirs.
        if copied < self.max_files:
            for g in include_globs:
                for sp in ctx.root.glob(g):
                    try:
                        if not sp.exists():
                            continue
                        rel_path = sp.relative_to(ctx.root)
                        if _is_excluded_path(rel_path, exclude):
                            continue

                        if sp.is_file():
                            _safe_copy_file(sp, dst_root / rel_file)
                            copied += 1
                        elif sp.is_dir():
                            files_copied, dirs_pruned = _copy_tree_filtered(sp, dst_root / rel_dir, exclude)
                            copied += files_copied
                            pruned += dirs_pruned
                        if copied >= self.max_files:
                            break
                    except Exception:
                        continue
                if copied >= self.max_files:
                    break

        # write a short manifest for sanity
        manifest = ctx.workdir / "meta" / "50_copy_manifest.txt"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            f"copied_files={copied}\npruned_dirs={pruned}\nmax_files={self.max_files}\n",
            encoding="utf-8",
        )

        dur = int(time.time() - start)
        note = f"copied={copied} pruned={pruned}"
        if copied >= self.max_files:
            note += " (HIT MAX)"
        return StepResult(self.name, "PASS", dur, note)
