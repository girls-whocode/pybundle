from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from pybundle.context import BundleContext
from pybundle.policy import AIContextPolicy, PathFilter


def _is_venv_root(p: Path) -> bool:
    if not p.is_dir():
        return False

    # Strong marker: standard venv metadata
    if (p / "pyvenv.cfg").is_file():
        return True

    # Typical venv executables (Linux/macOS)
    if (p / "bin").is_dir():
        # venv/virtualenv always has python here
        if (p / "bin" / "python").exists() or (p / "bin" / "python3").exists():
            # activation script is common but not guaranteed; still strong signal
            if (p / "bin" / "activate").is_file():
                return True
            # also accept presence of site-packages under lib
            if any((p / "lib").glob("python*/site-packages")):
                return True

    # Windows venv layout
    if (p / "Scripts").is_dir():
        if (p / "Scripts" / "python.exe").is_file() or (
            p / "Scripts" / "python"
        ).exists():
            if (p / "Scripts" / "activate").is_file():
                return True
            if (p / "Lib" / "site-packages").is_dir():
                return True

    # Some virtualenvs keep a .Python marker (macOS, older tooling)
    if (p / ".Python").exists():
        return True

    return False


def _is_under_venv(root: Path, rel_path: Path) -> bool:
    # walk ancestors: a/b/c.py -> check a, a/b, a/b/c
    cur = root
    for part in rel_path.parts:
        cur = cur / part
        if _is_venv_root(cur):
            return True
    return False


def _safe_copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # preserve mode + timestamps where possible
    shutil.copy2(src, dst)


def _copy_tree_filtered(
    root: Path,
    src_dir: Path,
    dst_dir: Path,
    filt: "PathFilter",
) -> tuple[int, int, int]:
    """
    Copy directory tree while pruning excluded directories and skipping excluded files.

    Returns: (files_copied, dirs_pruned, files_excluded)
    """
    seen_files = 0
    files_copied = 0
    pruned_dirs = 0

    for dirpath, dirnames, filenames in os.walk(src_dir):
        dp = Path(dirpath)
        rel_dir = dp.relative_to(src_dir)

        # prune dirs in-place so os.walk doesn't descend into them
        kept: list[str] = []
        for d in dirnames:
            if filt.should_prune_dir(dp, d):
                pruned_dirs += 1
                continue
            kept.append(d)
        dirnames[:] = kept

        for fn in filenames:
            seen_files += 1
            sp = dp / fn
            rel_file = rel_dir / fn

            # single source of truth: PathFilter handles excluded dirs, patterns, and extensions
            if not filt.should_include_file(root, sp):
                continue

            tp = dst_dir / rel_file
            try:
                _safe_copy_file(sp, tp)
            except OSError:
                continue

            files_copied += 1

    files_excluded = max(0, seen_files - files_copied)
    return files_copied, pruned_dirs, files_excluded


def _guess_package_dirs(root: Path, filt: "PathFilter") -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if filt.should_prune_dir(root, p.name):
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
    max_files: int = 20000
    policy: AIContextPolicy | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        dst_root = ctx.srcdir  # bundle/src
        dst_root.mkdir(parents=True, exist_ok=True)

        policy = self.policy or AIContextPolicy()

        exclude = (
            set(self.exclude_dirs) if self.exclude_dirs else set(policy.exclude_dirs)
        )
        exclude_patterns = set(policy.exclude_patterns)
        filt = PathFilter(
            exclude_dirs=exclude,
            exclude_patterns=exclude_patterns,
            exclude_file_exts=set(policy.exclude_file_exts),
        )
        include_files = self.include_files or list(policy.include_files)
        include_dirs = self.include_dirs or list(policy.include_dirs)
        include_globs = self.include_globs or list(policy.include_globs)

        copied = 0
        pruned = 0
        excluded_total = 0

        # 1) Include well-known top-level files if present
        for rel_file in include_files:
            if copied >= self.max_files:
                break

            sp = ctx.root / rel_file
            if not sp.is_file():
                continue
            if not filt.should_include_file(ctx.root, sp):
                continue

            try:
                _safe_copy_file(sp, dst_root / rel_file)
                copied += 1
                if copied >= self.max_files:
                    break
            except OSError:
                pass

        # 2) Include common top-level dirs (src/tests/tools)
        for rel_dir in include_dirs:
            sp = ctx.root / rel_dir
            if not sp.is_dir():
                continue

            # policy prune (exact + patterns + venv detection inside PathFilter)
            if filt.should_prune_dir(ctx.root, rel_dir):
                pruned += 1
                continue

            # extra-strong venv detection for oddly-named envs
            if _is_venv_root(sp):
                pruned += 1
                continue

            files_copied, dirs_pruned, files_excluded = _copy_tree_filtered(ctx.root, sp, dst_root / rel_dir, filt)
            copied += files_copied
            pruned += dirs_pruned
            excluded_total += files_excluded

            if copied >= self.max_files:
                break

        # 3) Include detected package dirs at root (if not already copied)
        if copied < self.max_files:
            for pkg_dir in _guess_package_dirs(ctx.root, filt):
                rel_pkg_name = pkg_dir.name
                if (dst_root / rel_pkg_name).exists():
                    continue
                files_copied, dirs_pruned, files_excluded = _copy_tree_filtered(ctx.root, pkg_dir, dst_root / rel_pkg_name, filt)
                copied += files_copied
                pruned += dirs_pruned
                excluded_total += files_excluded
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

                        if _is_under_venv(ctx.root, rel_path):
                            pruned += 1
                            continue

                        dst = dst_root / rel_path
                        if dst.exists():
                            continue

                        if sp.is_file():
                            if not filt.should_include_file(ctx.root, sp):
                                continue
                            _safe_copy_file(sp, dst)
                            copied += 1

                        elif sp.is_dir():
                            # prune dir itself before copying
                            parent = ctx.root if rel_path.parent == Path(".") else (ctx.root / rel_path.parent)
                            if filt.should_prune_dir(parent, rel_path.name):
                                pruned += 1
                                continue
                            if _is_venv_root(sp):
                                pruned += 1
                                continue

                            files_copied, dirs_pruned, files_excluded = _copy_tree_filtered(ctx.root, sp, dst_root / rel_path, filt)
                            copied += files_copied
                            pruned += dirs_pruned
                            excluded_total += files_excluded

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
            f"copied_files={copied}\n"
            f"excluded_files={excluded_total}\n"
            f"pruned_dirs={pruned}\n"
            f"max_files={self.max_files}\n",
            encoding="utf-8",
        )

        dur = int(time.time() - start)
        note = f"copied={copied} pruned={pruned}"
        if copied >= self.max_files:
            note += " (HIT MAX)"
        return StepResult(self.name, "PASS", dur, note)
