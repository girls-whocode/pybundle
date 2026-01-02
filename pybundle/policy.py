# pybundle/policy.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# Common junk that AI should not ingest by default
DEFAULT_EXCLUDE_DIRS: set[str] = {
    ".git", ".hg", ".svn",
    ".venv", "venv", ".direnv",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__",
    "node_modules",
    "dist", "build", "target", "out",
    ".next", ".nuxt", ".svelte-kit",
    "artifacts",
    ".cache",
}

# File extensions that commonly produce noise or massive distraction in AI mode
DEFAULT_EXCLUDE_FILE_EXTS: set[str] = {
    # packaging/installers/binaries
    ".appimage", ".deb", ".rpm", ".exe", ".msi", ".dmg", ".pkg",
    ".so", ".dll", ".dylib",

    # runtime DBs
    ".db", ".sqlite", ".sqlite3",

    # archives (often huge)
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z",
}

# Manifests + config files that are often essential for polyglot projects
DEFAULT_INCLUDE_FILES: list[str] = [
    # Python
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
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

    # Docs / meta
    "README.md",
    "README.rst",
    "README.txt",
    "CHANGELOG.md",
    "LICENSE",
    "LICENSE.md",

    # Node / frontend
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "tsconfig.json",
    "vite.config.js",
    "vite.config.ts",
    "webpack.config.js",
    "webpack.config.ts",

    # Rust / Tauri
    "Cargo.toml",
    "Cargo.lock",
    "tauri.conf.json",
    "tauri.conf.json5",
    "tauri.conf.toml",
]

DEFAULT_INCLUDE_DIRS: list[str] = [
    # Python-ish
    "src",
    "app",
    "tests",
    "tools",
    "docs",
    ".github",
    "templates",
    "static",

    # Polyglot/common
    "frontend",
    "web",
    "ui",
    "gaslog-desktop",  # important for Gaslog, harmless elsewhere
]

DEFAULT_INCLUDE_GLOBS: list[str] = [
    "*.py",
    "*/**/*.py",
    "templates/**/*",
    "static/**/*",
]


@dataclass(frozen=True)
class AIContextPolicy:
    # path filters
    exclude_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_DIRS))
    exclude_file_exts: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_FILE_EXTS))

    # curated inclusion
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
                (p / "Scripts" / "python.exe").is_file() or (p / "Scripts" / "python").exists()
            ):
                return True
            if (p / "Lib" / "site-packages").is_dir():
                return True

        if (p / ".Python").exists():
            return True

        return False

    def should_prune_dir(self, parent_dir: Path, child_name: str) -> bool:
        if child_name in self.exclude_dirs:
            return True
        if self.detect_venvs and self.is_venv_root(parent_dir / child_name):
            return True
        return False

    def should_include_file(self, root: Path, p: Path) -> bool:
        try:
            rel = p.relative_to(root)
        except Exception:
            return False

        # reject files under excluded dirs by name
        for part in rel.parts[:-1]:
            if part in self.exclude_dirs:
                return False

        # reject excluded extensions
        ext = p.suffix.lower()
        if ext in self.exclude_file_exts:
            return False

        return True
