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
        # Windows system directories + common dev tool locations
        default_prefixes = [
            "C:\\Windows\\System32\\",
            "C:\\Windows\\system32\\",
            "C:\\Windows\\SysWOW64\\",
            "C:\\Program Files\\",
            "C:\\Program Files (x86)\\",
            # Git for Windows
            "C:\\Program Files\\Git\\cmd\\",
            "C:\\Program Files\\Git\\usr\\bin\\",
            "C:\\Program Files (x86)\\Git\\cmd\\",
            "C:\\Program Files (x86)\\Git\\usr\\bin\\",
            # Package managers
            "C:\\ProgramData\\chocolatey\\bin\\",
            # Scoop
            "C:\\Users\\",  # Scoop installs to %USERPROFILE%\scoop (we catch this via pattern)
            # MSYS2
            "C:\\msys64\\usr\\bin\\",
            "C:\\msys64\\mingw64\\bin\\",
            "C:\\msys2\\usr\\bin\\",
            "C:\\msys2\\mingw64\\bin\\",
            # Python user scripts
            "C:\\Users\\",  # Python user scripts in AppData (pattern match)
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
            "/opt/bin/",  # Custom opt installations
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
    if any(venv in tool_path for venv in [".venv", "venv", ".pybundle-venv"]):
        return True

    # On Windows, check for common dev locations even with case variations
    if sys.platform == "win32":
        tool_path_lower = tool_path.lower()
        # Scoop installs to %USERPROFILE%\scoop\shims\
        if "\\scoop\\shims\\" in tool_path_lower:
            return True
        # Python user scripts in AppData
        if "\\appdata\\roaming\\python" in tool_path_lower:
            return True
        # PowerShell user modules
        if "\\powershell\\modules\\" in tool_path_lower:
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

def has_python_zipfile() -> bool:
    """Check if Python's built-in zipfile module can be used as fallback for 'zip'.
    
    This is useful on Windows where the zip command may not be available.
    Returns True if Python zipfile module is available (which is always true for
    standard Python installations).
    """
    try:
        import zipfile
        return True
    except ImportError:
        return False


def get_platform_info() -> dict[str, str]:
    """Get platform information using Python stdlib (fallback for 'uname').
    
    Returns dict with keys like 'system', 'release', 'version', 'machine', etc.
    This is useful on Windows where uname may not be available.
    """
    import platform
    import sys
    
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python_version": sys.version,
        "processor": platform.processor(),
    }


def is_windows() -> bool:
    """Check if running on Windows."""
    import sys
    return sys.platform == "win32"


def is_unix() -> bool:
    """Check if running on Unix-like system (Linux, macOS, BSD, etc.)."""
    import sys
    return sys.platform in ("linux", "darwin") or sys.platform.startswith(("freebsd", "openbsd"))


def get_platform_specific_tool(tool_name: str) -> str | None:
    """Get platform-specific alternative for a tool if available.
    
    For example, on Windows:
    - 'uname' -> Python's platform module (no direct replacement)
    - 'rg' -> may need to be installed via chocolatey/scoop
    
    Returns the tool name to use, or None if not available on this platform.
    """
    import sys
    
    # Most Python-based tools work cross-platform
    python_tools = {
        "pytest", "mypy", "ruff", "vulture", "radon", 
        "interrogate", "pylint", "pipdeptree", "pip-licenses",
        "line_profiler", "pdoc", "bandit", "pip-audit"
    }
    
    if tool_name in python_tools:
        return tool_name
    
    # Tools that need special handling on Windows
    if sys.platform == "win32":
        # uname doesn't exist on Windows - use Python's platform module instead
        if tool_name == "uname":
            return None  # Handled by get_platform_info()
        
        # ripgrep works on Windows but needs separate installation
        if tool_name == "rg":
            return "rg.exe" if which("rg.exe") else "rg"
    
    return tool_name