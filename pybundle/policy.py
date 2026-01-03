# pybundle/policy.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pybundle.filters import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_FILE_EXTS,
    DEFAULT_INCLUDE_FILES,
    DEFAULT_INCLUDE_DIRS,
    DEFAULT_INCLUDE_GLOBS,
    EXCLUDE_PATTERNS,
    is_excluded_by_name,
)

@dataclass(frozen=True)
class AIContextPolicy:
    exclude_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_DIRS))
    exclude_patterns: set[str] = field(default_factory=lambda: set(EXCLUDE_PATTERNS))
    exclude_file_exts: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_FILE_EXTS))

    include_files: list[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_FILES))
    include_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_DIRS))
    include_globs: list[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_GLOBS))


    # AI-friendly knobs
    tree_max_depth: int = 4
    largest_limit: int = 80
    roadmap_max_files: int = 20000
    roadmap_mermaid_depth: int = 2
    roadmap_mermaid_max_edges: int = 180

    def include_dir_candidates(self, root: Path) -> list[Path]:
        out: list[Path] = []
        for d in self.include_dirs:
            p = root / d
            if p.exists():
                out.append(p)
        return out or [root]


@dataclass
class PathFilter:
    """
    Shared filtering logic across steps:
    - prune excluded dir names
    - prune venvs by structure (any name)
    - optionally exclude noisy file types by extension
    """

    exclude_dirs: set[str]
    exclude_file_exts: set[str]
    exclude_patterns: set[str] = field(default_factory=set)
    detect_venvs: bool = True

    def is_venv_root(self, p: Path) -> bool:
        if not p.is_dir():
            return False

        if (p / "pyvenv.cfg").is_file():
            return True

        if (p / "bin").is_dir():
            if (p / "bin" / "activate").is_file() and (
                (p / "bin" / "python").exists() or (p / "bin" / "python3").exists()
            ):
                return True
            if any((p / "lib").glob("python*/site-packages")):
                return True

        if (p / "Scripts").is_dir():
            if (p / "Scripts" / "activate").is_file() and (
                (p / "Scripts" / "python.exe").is_file()
                or (p / "Scripts" / "python").exists()
            ):
                return True
            if (p / "Lib" / "site-packages").is_dir():
                return True

        if (p / ".Python").exists():
            return True

        return False

    def should_prune_dir(self, parent_dir: Path, child_name: str) -> bool:
        if is_excluded_by_name(child_name, exclude_names=self.exclude_dirs, exclude_patterns=self.exclude_patterns):
            return True
        if self.detect_venvs and self.is_venv_root(parent_dir / child_name):
            return True
        return False

    def should_include_file(self, root: Path, p: Path) -> bool:
        try:
            rel = p.relative_to(root)
        except Exception:
            return False

        # reject files under excluded dirs by name/pattern
        for part in rel.parts[:-1]:
            if is_excluded_by_name(part, exclude_names=self.exclude_dirs, exclude_patterns=self.exclude_patterns):
                return False

        # reject excluded file names by pattern (e.g. *.egg, *.rej)
        if is_excluded_by_name(rel.name, exclude_names=self.exclude_dirs, exclude_patterns=self.exclude_patterns):
            return False

        # reject excluded extensions
        ext = p.suffix.lower()
        if ext in self.exclude_file_exts:
            return False

        return True
