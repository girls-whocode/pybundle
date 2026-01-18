from __future__ import annotations

import shutil
import os


def get_trusted_path_prefixes() -> list[str]:
    """Return list of trusted directory prefixes for tool validation.

    These are common system directories where legitimate tools are installed.
    Can be extended via environment variable PYBUNDLE_TRUSTED_PATHS (colon-separated).
    """
    default_prefixes = [
        "/usr/bin/",
        "/usr/local/bin/",
        "/bin/",
        "/opt/homebrew/bin/",  # macOS Homebrew (Apple Silicon)
        "/opt/homebrew/opt/",  # Homebrew linked tools
        "/home/linuxbrew/.linuxbrew/bin/",  # Linux Homebrew
        "/snap/bin/",  # Ubuntu snaps
        "/usr/sbin/",
        "/sbin/",
    ]

    # Allow user-specified trusted paths via environment
    extra_paths = os.environ.get("PYBUNDLE_TRUSTED_PATHS", "")
    if extra_paths:
        default_prefixes.extend(p.strip() for p in extra_paths.split(":") if p.strip())

    return default_prefixes


def is_path_trusted(tool_path: str | None) -> bool:
    """Check if a tool path is in a trusted directory."""
    if not tool_path:
        return False

    # Virtual environment paths are implicitly trusted
    # (they're part of the project context)
    if ".venv" in tool_path or "venv" in tool_path or ".pybundle-venv" in tool_path:
        return True

    trusted_prefixes = get_trusted_path_prefixes()
    return any(tool_path.startswith(prefix) for prefix in trusted_prefixes)


def which(cmd: str, strict: bool = False) -> str | None:
    """Resolve tool path with optional strict mode validation.

    Args:
        cmd: Command name to resolve
        strict: If True, only return paths in trusted directories

    Returns:
        Full path to command, or None if not found (or not trusted in strict mode)
    """
    path = shutil.which(cmd)

    if strict and path:
        if not is_path_trusted(path):
            return None

    return path
