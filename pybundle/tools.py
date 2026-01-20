from __future__ import annotations

import shutil
import os


def get_trusted_path_prefixes() -> list[str]:
    """Return list of trusted directory prefixes for tool validation.

    These are common system directories where legitimate tools are installed.
    Can be extended via environment variable PYBUNDLE_TRUSTED_PATHS (colon-separated on
    Unix, semicolon-separated on Windows).
    """
    import sys

    if sys.platform == "win32":
        # Windows system directories
        default_prefixes = [
            "C:\\Windows\\System32\\",
            "C:\\Windows\\system32\\",
            "C:\\Windows\\SysWOW64\\",
            "C:\\Program Files\\",
            "C:\\Program Files (x86)\\",
        ]
        path_separator = ";"
    else:
        # Unix-like systems (Linux, macOS, etc.)
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
        path_separator = ":"

    # Allow user-specified trusted paths via environment
    extra_paths = os.environ.get("PYBUNDLE_TRUSTED_PATHS", "")
    if extra_paths:
        default_prefixes.extend(p.strip() for p in extra_paths.split(path_separator) if p.strip())

    return default_prefixes


def is_path_trusted(tool_path: str | None) -> bool:
    """Check if a tool path is in a trusted directory."""
    import sys

    if not tool_path:
        return False

    # Virtual environment paths are implicitly trusted
    # (they're part of the project context)
    if ".venv" in tool_path or "venv" in tool_path or ".pybundle-venv" in tool_path:
        return True

    trusted_prefixes = get_trusted_path_prefixes()

    # On Windows, paths are case-insensitive
    if sys.platform == "win32":
        tool_path_lower = tool_path.lower()
        return any(tool_path_lower.startswith(prefix.lower()) for prefix in trusted_prefixes)

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
