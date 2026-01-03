from fnmatch import fnmatch
from pathlib import Path

EXCLUDE_PATTERNS = {
    "*.egg",
    "*.egg-info",
    "*.appimage",
    "*.deb",
    "*.rpm",
    "*.exe",
    "*.msi",
    "*.dmg",
    "*.pkg",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.tgz",
    "*.bz2",
    "*.xz",
    "*.7z",
    "*.rej",
    "*.orig",
}

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
    "target",
    ".next",
    ".nuxt",
    "artifacts",
    ".cache",
    ".hg",
    ".svn",
    "venv",
    ".direnv",
    ".pybundle-venv",
    "binaries",
    "out",
    ".svelte-kit",
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
    "README.md",
    "README.rst",
    "README.txt",
    "CHANGELOG.md",
    "LICENSE",
    "LICENSE.md",
    ".tox",
    ".nox",
    ".direnv",
    "requirements-dev.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "tsconfig.json",
    "vite.config.js",
    "vite.config.ts",
    "webpack.config.js",
    "webpack.config.ts",
    "Cargo.toml",
    "Cargo.lock",
    "tauri.conf.json",
    "tauri.conf.json5",
    "tauri.conf.toml",
]

DEFAULT_INCLUDE_DIRS = [
    "src",
    "tests",
    "tools",
    "docs",
    ".github",
    "app",
    "templates",
    "static",
    "src-tauri",
    "frontend",
    "web",
    "ui",
]

DEFAULT_INCLUDE_GLOBS = [
    "*.py",
    "*/**/*.py",
    "templates/**/*",
    "static/**/*",
]

DEFAULT_EXCLUDE_FILE_EXTS: set[str] = {
    ".appimage",
    ".deb",
    ".rpm",
    ".exe",
    ".msi",
    ".dmg",
    ".pkg",
    ".so",
    ".dll",
    ".dylib",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
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


def is_excluded_by_name(name: str, *, exclude_names: set[str], exclude_patterns: set[str]) -> bool:
    if name in exclude_names:
        return True
    return any(fnmatch(name, pat) for pat in exclude_patterns)


def is_excluded_name(self, name: str) -> bool:
    return is_excluded_by_name(name, exclude_names=self.exclude_dirs, exclude_patterns=self.exclude_patterns)


def is_excluded_path(
    rel: Path,
    exclude_names: set[str],
    exclude_patterns: set[str],
) -> bool:
    # Exclude if *any* part matches (dirs) OR the final filename matches
    for part in rel.parts:
        if is_excluded_by_name(part, exclude_names=exclude_names, exclude_patterns=exclude_patterns):
            return True
    return False