from __future__ import annotations

import ast
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


def _find_python_files(root: Path, max_files: int = 100) -> list[Path]:
    """Find Python files in the project, excluding common ignore directories."""
    files = []
    ignore_dirs = {
        ".venv", "venv", "__pycache__", ".mypy_cache", 
        ".ruff_cache", ".pytest_cache", "node_modules",
        "dist", "build", "artifacts", ".git", ".tox",
        "site-packages", ".eggs", "*.egg-info"
    }
    
    for py_file in root.rglob("*.py"):
        # Skip if any parent directory is in ignore list or matches pattern
        should_skip = False
        for part in py_file.parts:
            # Check exact matches
            if part in ignore_dirs:
                should_skip = True
                break
            # Check pattern matches (e.g., .pybundle-venv, any .venv variant)
            if part.startswith('.') and 'venv' in part:
                should_skip = True
                break
            if part.endswith('.egg-info') or part.endswith('-info'):
                should_skip = True
                break
        
        if should_skip:
            continue
            
        files.append(py_file)
        if len(files) >= max_files:
            break
    
    return files


def _check_syntax_errors(file_path: Path) -> list[dict]:
    """Check a Python file for syntax errors."""
    errors = []
    try:
        content = file_path.read_text(encoding="utf-8")
        ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        errors.append({
            "line": e.lineno or 0,
            "offset": e.offset or 0,
            "message": e.msg,
            "text": e.text.strip() if e.text else ""
        })
    except Exception as e:
        errors.append({
            "line": 0,
            "offset": 0,
            "message": f"Error reading file: {str(e)}",
            "text": ""
        })
    
    return errors


def _find_imports(file_path: Path) -> tuple[set[str], list[dict]]:
    """Extract import statements from a Python file."""
    imports = set()
    import_errors = []
    
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                # Skip relative imports (level > 0, e.g., "from . import x", "from .steps import y")
                if node.level > 0:
                    continue
                # For "from X import Y", we care about the module X
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception as e:
        import_errors.append({
            "file": str(file_path),
            "error": str(e)
        })
    
    return imports, import_errors


def _get_project_modules(root: Path) -> set[str]:
    """Get module names that are part of the project itself."""
    modules = set()
    
    # Look for Python packages (directories with __init__.py) at root level
    for item in root.iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('_'):
            # Check if it's a Python package
            if (item / "__init__.py").exists():
                modules.add(item.name)
                
                # Also add all .py files within this package as potential modules
                # (they can be imported as package.module)
                for py_file in item.rglob("*.py"):
                    if py_file.name != "__init__.py":
                        # Get the module name relative to root
                        # e.g., pybundle/cli.py -> add 'cli' as a project module
                        modules.add(py_file.stem)
    
    # Also add Python files in root (without .py extension)
    for item in root.glob("*.py"):
        if item.name != "__init__.py":
            modules.add(item.stem)
    
    return modules


def _get_stdlib_modules() -> set[str]:
    """Get set of standard library module names."""
    try:
        import sys
        # Python 3.10+ has this
        if hasattr(sys, 'stdlib_module_names'):
            return set(sys.stdlib_module_names)
    except Exception:
        pass
    
    # Fallback for older Python versions or if the above fails
    # This is a comprehensive list for Python 3.8+
    return {
        "__future__", "abc", "aifc", "argparse", "array", "ast", "asynchat",
        "asyncio", "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
        "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath",
        "cmd", "code", "codecs", "codeop", "collections", "colorsys", "compileall",
        "concurrent", "configparser", "contextlib", "contextvars", "copy", "copyreg",
        "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses", "datetime",
        "dbm", "decimal", "difflib", "dis", "distutils", "doctest", "email", "encodings",
        "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "fractions", "ftplib", "functools", "gc", "getopt", "getpass", "gettext",
        "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http",
        "imaplib", "imghdr", "imp", "importlib", "inspect", "io", "ipaddress",
        "itertools", "json", "keyword", "lib2to3", "linecache", "locale", "logging",
        "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
        "modulefinder", "multiprocessing", "netrc", "nis", "nntplib", "numbers",
        "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb", "pickle",
        "pickletools", "pipes", "pkgutil", "platform", "plistlib", "poplib", "posix",
        "posixpath", "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
        "pyclbr", "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
        "resource", "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
        "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
        "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics",
        "string", "stringprep", "struct", "subprocess", "sunau", "symbol", "symtable",
        "sys", "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile",
        "termios", "test", "textwrap", "threading", "time", "timeit", "tkinter",
        "token", "tokenize", "tomllib", "trace", "traceback", "tracemalloc", "tty",
        "turtle", "turtledemo", "types", "typing", "typing_extensions", "unicodedata",
        "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref",
        "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
        "zipapp", "zipfile", "zipimport", "zlib", "zoneinfo",
        # Python 3.13 additions
        "annotationlib", "dbm.sqlite3",
    }


def _can_import(module_name: str) -> bool:
    """Test if a module can be imported."""
    try:
        import importlib.util
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ModuleNotFoundError, ValueError, AttributeError):
        return False


@dataclass
class PylanceStep:
    name: str = "pylance"
    outfile: str = "logs/34_pylance.txt"
    max_files: int = 100

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        out = ctx.workdir / self.outfile
        out.parent.mkdir(parents=True, exist_ok=True)

        sections = []
        sections.append(f"## Pylance-Style Analysis Report ##\n")
        sections.append(f"## PWD: {ctx.root}\n\n")
        
        has_issues = False
        
        # Find Python files
        py_files = _find_python_files(ctx.root, self.max_files)
        sections.append(f"Found {len(py_files)} Python files to analyze\n\n")
        
        # 1. Syntax Errors
        sections.append("## Syntax Errors ##\n")
        syntax_error_count = 0
        
        for py_file in py_files:
            errors = _check_syntax_errors(py_file)
            if errors:
                has_issues = True
                syntax_error_count += len(errors)
                rel_path = py_file.relative_to(ctx.root)
                sections.append(f"\n{rel_path}:\n")
                for err in errors:
                    sections.append(f"  Line {err['line']}, Col {err['offset']}: {err['message']}\n")
                    if err['text']:
                        sections.append(f"    {err['text']}\n")
        
        if syntax_error_count == 0:
            sections.append("No syntax errors found.\n")
        else:
            sections.append(f"\nTotal syntax errors: {syntax_error_count}\n")
        
        # 2. Import Analysis
        sections.append("\n## Import Analysis ##\n")
        all_imports = set()
        import_errors = []
        
        for py_file in py_files:
            file_imports, file_errors = _find_imports(py_file)
            all_imports.update(file_imports)
            import_errors.extend(file_errors)
        
        sections.append(f"Total unique top-level imports found: {len(all_imports)}\n")
        
        # Check which imports might be missing
        stdlib_modules = _get_stdlib_modules()
        project_modules = _get_project_modules(ctx.root)
        
        # Filter out private imports and check if modules can be imported
        public_imports = {imp for imp in all_imports if not imp.startswith('_')}
        
        potentially_missing = []
        for imp in sorted(public_imports):
            # Skip if it's in stdlib
            if imp in stdlib_modules:
                continue
            
            # Skip if it's a local project module
            if imp in project_modules:
                continue
            
            # Skip common builtin names
            if imp in {'StringIO', 'BytesIO', 'io'}:  # io module variations
                continue
                
            # Try to import it - if it fails, it's potentially missing
            if not _can_import(imp):
                potentially_missing.append(imp)
        
        if potentially_missing:
            has_issues = True
            sections.append(f"\nPotentially missing/unimportable modules ({len(potentially_missing)}):\n")
            sections.append("(Could not be imported - either missing dependencies or sub-modules)\n")
            sections.append("Note: Sub-modules of installed packages (e.g., 'requests.exceptions') may appear here.\n\n")
            for imp in potentially_missing[:30]:  # Limit to first 30
                sections.append(f"  - {imp}\n")
            
            # Add helpful note about common cases
            known_submodules = {
                'connection', 'connectionpool', 'poolmanager', 'response', 'exceptions',
                'contrib', 'fields', 'filepost', 'compression',  # urllib3 submodules
                'backports', 'base', 'http2',  # httpcore/httpx submodules  
                'lib', 'context', 'matrixlib',  # numpy submodules
            }
            submodule_matches = [imp for imp in potentially_missing if imp in known_submodules]
            if submodule_matches:
                sections.append(f"\nLikely sub-modules (not standalone packages): {', '.join(submodule_matches[:10])}\n")
        else:
            sections.append("\nAll public imports appear to be resolved.\n")
        
        if import_errors:
            sections.append(f"\nErrors while analyzing imports ({len(import_errors)}):\n")
            for err in import_errors[:10]:
                sections.append(f"  {err['file']}: {err['error']}\n")
        
        # 3. Python Environment
        sections.append("\n## Python Environment ##\n")
        try:
            py_version = subprocess.run(
                ["python", "-V"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if py_version.returncode == 0:
                sections.append(f"Python version: {py_version.stdout.strip()}\n")
            
            pip_version = subprocess.run(
                ["python", "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if pip_version.returncode == 0:
                sections.append(f"Pip: {pip_version.stdout.strip()}\n")
            
            # Get count of installed packages
            pip_list = subprocess.run(
                ["python", "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            if pip_list.returncode == 0:
                import json
                packages = json.loads(pip_list.stdout)
                sections.append(f"Installed packages: {len(packages)}\n")
            
        except Exception as e:
            sections.append(f"Error getting environment info: {e}\n")
        
        # Write the collected output
        text = "".join(sections)
        out.write_text(ctx.redact_text(text), encoding="utf-8")
        
        dur = int(time.time() - start)
        note = "issues found" if has_issues else ""
        
        return StepResult(self.name, "PASS", dur, note)
