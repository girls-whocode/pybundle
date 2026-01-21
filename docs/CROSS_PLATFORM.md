# Cross-Platform Support

## Overview

PyBundle is designed to work across Windows, Linux, and macOS. Some analysis tools have OS-specific requirements.

## OS Detection

PyBundle automatically detects the operating system and adjusts tool usage:

- **Unix-like systems** (Linux, macOS): Use native commands like `uname`, `rg` (ripgrep)
- **Windows**: Use Python-based alternatives where native commands aren't available

## Platform-Specific Tools

### System Information

- **Unix/Linux/macOS**: Uses `uname -a` command
- **Windows**: Uses Python's `platform` module (uname not available)
- **All platforms**: Also generates `platform_info` file using Python's stdlib

### Text Search (ripgrep)

- **Unix/Linux/macOS**: Usually pre-installed or available via package managers
- **Windows**: Install via:
  - Chocolatey: `choco install ripgrep`
  - Scoop: `scoop install ripgrep`
  - Manual: Download from https://github.com/BurntSushi/ripgrep/releases

### Python-Based Tools (Cross-Platform)

These tools work on all platforms via pip:
- pytest
- mypy
- ruff
- pylint
- radon
- interrogate
- vulture
- pipdeptree
- pip-licenses
- line_profiler
- bandit
- pip-audit

## Installation

### Basic (all platforms)
```bash
pip install gwc-pybundle
```

### With analysis tools (recommended)
```bash
pip install gwc-pybundle[tools]
```

### For development
```bash
pip install -e .[dev]
```

### Everything
```bash
pip install -e .[all]
```

## Windows-Specific Notes

1. **Git**: Install [Git for Windows](https://git-scm.com/download/win)
2. **Ripgrep**: Optional but recommended - install via chocolatey or scoop
3. **Python tools**: Install via `pip install gwc-pybundle[tools]`

## Handling Missing Tools

PyBundle gracefully handles missing tools:
- If a tool is not found, that step is **SKIPPED**
- The bundle continues with available tools
- Results clearly indicate which steps were skipped

## Adding Custom Tools

To add trusted tool paths (e.g., from custom installations):

**Windows:**
```cmd
set PYBUNDLE_TRUSTED_PATHS=C:\CustomTools\bin;D:\MyTools
```

**Unix/Linux/macOS:**
```bash
export PYBUNDLE_TRUSTED_PATHS=/opt/custom/bin:/home/user/mytools
```
