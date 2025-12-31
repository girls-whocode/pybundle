from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .base import StepResult
from ..context import BundleContext


def _read_lines(p: Path) -> list[str]:
    if not p.is_file():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]


def _is_under(root: Path, p: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _copy_file(src: Path, dst: Path) -> bool:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        return True
    except Exception:
        return False


def _find_repo_candidates(root: Path) -> list[Path]:
    cands = [root]
    if (root / "src").is_dir():
        cands.append(root / "src")
    return cands


def _module_to_path(roots: list[Path], module: str) -> Path | None:
    """
    Resolve an absolute module like 'pkg.sub' to a file inside repo roots:
      - <root>/pkg/sub.py
      - <root>/pkg/sub/__init__.py
    """
    parts = module.split(".")
    for r in roots:
        f1 = r.joinpath(*parts).with_suffix(".py")
        if f1.is_file():
            return f1
        f2 = r.joinpath(*parts) / "__init__.py"
        if f2.is_file():
            return f2
    return None


def _relative_module_to_path(roots: list[Path], base_file: Path, module: str | None, level: int) -> Path | None:
    """
    Resolve relative imports like:
      from . import x      (level=1, module=None)
      from ..foo import y  (level=2, module="foo")
    """
    # Find the package directory for base_file
    base_dir = base_file.parent

    # Move up `level` package levels
    rel_dir = base_dir
    for _ in range(level):
        rel_dir = rel_dir.parent

    if module:
        target = rel_dir.joinpath(*module.split("."))
    else:
        target = rel_dir

    # Try module as file or package
    f1 = target.with_suffix(".py")
    if f1.is_file():
        return f1
    f2 = target / "__init__.py"
    if f2.is_file():
        return f2

    # If relative resolution fails, try absolute resolution as fallback
    if module:
        return _module_to_path(roots, module)
    return None


def _extract_import_modules(py_file: Path) -> set[tuple[str | None, int]]:
    """
    Returns a set of (module, level) pairs:
      - absolute imports: (module, 0)
      - relative imports: (module, level>=1)
    module can be None for `from . import x` style.
    """
    out: set[tuple[str | None, int]] = set()
    try:
        src = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except Exception:
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    out.add((alias.name, 0))
        elif isinstance(node, ast.ImportFrom):
            # node.module can be None (from . import x)
            lvl = int(getattr(node, "level", 0) or 0)
            mod = node.module
            if mod:
                out.add((mod, lvl))
            else:
                # still useful; we can resolve to the package itself for context
                out.add((None, lvl))
    return out


def _add_package_chain(files: set[Path], root: Path, py: Path) -> None:
    """
    Add __init__.py from file's dir up to repo root.
    """
    cur = py.parent
    root_res = root.resolve()
    while True:
        initp = cur / "__init__.py"
        if initp.is_file():
            files.add(initp)
        if cur.resolve() == root_res:
            break
        if not _is_under(root, cur):
            break
        cur = cur.parent


def _add_conftest_chain(files: set[Path], root: Path, py: Path) -> None:
    """
    Add conftest.py from file's dir up to repo root (pytest glue).
    """
    cur = py.parent
    root_res = root.resolve()
    while True:
        cp = cur / "conftest.py"
        if cp.is_file():
            files.add(cp)
        if cur.resolve() == root_res:
            break
        if not _is_under(root, cur):
            break
        cur = cur.parent


@dataclass
class ErrorContextExpandStep:
    name: str = "expand error context"
    depth: int = 2
    max_files: int = 600
    # reads this list produced by step 8
    source_list_file: str = "error_files_from_logs.txt"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        roots = _find_repo_candidates(ctx.root)

        list_path = ctx.workdir / self.source_list_file
        rels = _read_lines(list_path)

        dest_root = ctx.srcdir / "_error_context"
        dest_root.mkdir(parents=True, exist_ok=True)

        to_copy: set[Path] = set()
        queue: list[tuple[Path, int]] = []

        # Seed with referenced python files only
        for rel_str in rels:
            p = (ctx.root / rel_str).resolve()
            if p.is_file() and p.suffix == ".py" and _is_under(ctx.root, p):
                queue.append((p, 0))
                to_copy.add(p)

        visited: set[Path] = set()

        while queue and len(to_copy) < self.max_files:
            py_file, d = queue.pop(0)
            if py_file in visited:
                continue
            visited.add(py_file)

            # add pytest + package glue around this file
            _add_package_chain(to_copy, ctx.root, py_file)
            _add_conftest_chain(to_copy, ctx.root, py_file)

            if d >= self.depth:
                continue

            # parse imports and resolve to repo files
            for mod, level in _extract_import_modules(py_file):
                target: Path | None
                if level and level > 0:
                    target = _relative_module_to_path(roots, py_file, mod, level)
                else:
                    if not mod:
                        continue
                    target = _module_to_path(roots, mod)

                if target and target.is_file() and _is_under(ctx.root, target):
                    if target.suffix == ".py":
                        if target not in to_copy:
                            to_copy.add(target)
                        queue.append((target, d + 1))

                if len(to_copy) >= self.max_files:
                    break

        # Always include top-level config files if present (small but high value)
        for cfg in ["pyproject.toml", "mypy.ini", "ruff.toml", ".ruff.toml", "pytest.ini", "setup.cfg", "requirements.txt"]:
            p = ctx.root / cfg
            if p.is_file():
                to_copy.add(p)

        copied = 0
        for p in sorted(to_copy):
            if copied >= self.max_files:
                break
            # copy under src/_error_context/<repo-relative-path>
            try:
                rel_path = p.resolve().relative_to(ctx.root.resolve())
            except Exception:
                continue
            dst = dest_root / rel_path
            if _copy_file(p, dst):
                copied += 1

        report = ctx.metadir / "61_error_context_report.txt"
        report.write_text(
            "\n".join(
                [
                    f"seed_files={len([r for r in rels if r.endswith('.py')])}",
                    f"depth={self.depth}",
                    f"max_files={self.max_files}",
                    f"resolved_total={len(to_copy)}",
                    f"copied={copied}",
                    f"dest=src/_error_context",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        dur = int(time.time() - start)
        note = f"resolved={len(to_copy)} copied={copied}"
        if copied >= self.max_files:
            note += " (HIT MAX)"
        return StepResult(self.name, "PASS", dur, note)
