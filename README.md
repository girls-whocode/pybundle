# 🧳 pybundle ![PyPI - Version](https://img.shields.io/pypi/v/gwc-pybundle)

![GitHub Release Date](https://img.shields.io/github/release-date/girls-whocode/pybundle?color=orange)

[![Python versions](https://img.shields.io/pypi/pyversions/gwc-pybundle.svg?color=3776AB)](https://pypi.org/project/gwc-pybundle/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE.md)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/gwc-pybundle?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLUE&right_color=GREY&left_text=downloads)](https://pepy.tech/projects/gwc-pybundle)
![GitHub Sponsors](https://img.shields.io/github/sponsors/girls-whocode?color=ec4899)

[![CI](https://github.com/girls-whocode/pybundle/actions/workflows/publish.yml/badge.svg?color=fb923c)](https://github.com/girls-whocode/pybundle/actions)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-14b8a6.svg)](https://github.com/astral-sh/ruff)
[![Type checked](https://img.shields.io/badge/type%20checked-mypy-0ea5e9.svg)](https://mypy-lang.org/)
![Commit Activity](https://img.shields.io/github/commit-activity/t/girls-whocode/pybundle?color=f59e0b)


**pybundle** is a deterministic, automation-friendly CLI that captures Python project context into a single, reproducible bundle — ideal for debugging, CI artifacts, audits, and AI-assisted workflows.

It produces **machine-readable outputs first**, with optional human-readable summaries layered on top.

> Think “`git archive` + diagnostics + metadata”, without guessing or heuristics.  

> **Note:** The PyPI package name is `gwc-pybundle`, but the tool is installed and used as `pybundle`.
---

## 🧠 Why pybundle exists

Modern software development compresses what used to be entire teams into a single role.

Today, one developer is often responsible for:
- application code
- build systems
- test tooling
- deployment logic
- CI/CD behavior
- environment differences
- security implications
- and increasingly, AI-assisted workflows

The problem is no longer *how* to write code.

It’s answering:

> **“Why is this system behaving the way it is?”**

That question is hard to answer when:
- context is scattered
- tooling output is ephemeral
- environment details are lost
- source snapshots are incomplete or noisy

AI didn’t create this problem - it exposed it.

Large language models don’t fail because they lack intelligence.
They fail because we give them **uncurated context**.

Humans don’t fail because they can’t debug.
They fail because the **cost of reconstructing context** exceeds the time they have.

**pybundle exists to reduce context debt.**

It captures *what matters*, ignores what doesn’t, and produces a deterministic artifact that explains:
- what code exists
- what tools ran
- what environment was used
- and why the outputs exist

For humans, automation, and AI alike.

---

## ✨ Features

* 📦 **Single archive output** (`.zip` or `.tar.gz`)
* 🧠 **Machine-readable manifest** (`MANIFEST.json`) for automation
* 🧾 **Structured summaries** (`SUMMARY.json`)
* 🧭 **Respects `.gitignore`** exactly when available
* 🛑 **Safely ignores virtualenvs and caches** (even with non-standard names)
* 🔍 Optional tooling checks (ruff, mypy, pytest, pylance, bandit, pip-audit, coverage)
* 🛡️ Security scanning (bandit for code issues, pip-audit for dependency CVEs)
* 🧪 Deterministic output (stable paths, timestamps, schemas)
* 🔒 Secret-safe (optional redaction)
* **v2.1.0 NEW:** Enhanced AI context, smarter dead code detection, confidence-scored dependency analysis
* **v2.0.1:** 22 advanced analysis steps including:
  - 🔐 Security hardening (secrets detection, security headers)
  - ⚡ Async/await pattern detection
  - 📊 Database & ORM optimization
  - 🏗️ Framework-specific analysis (Django, FastAPI, Flask)
  - 🐳 Container & deployment analysis

---

## 📂 What’s in a pybundle archive?

At minimum, a bundle contains:

```text
MANIFEST.json        # stable, machine-readable metadata
SUMMARY.json         # structured summary of collected data
src/                 # filtered project source snapshot
logs/                # tool outputs (ruff, mypy, pytest, pylance, bandit, pip-audit, coverage, rg scans)
meta/                # environment + tool detection
```

### `MANIFEST.json` (automation fuel)

Includes:

* tool paths detected
* options used
* archive name + format
* git commit hash (if available)
* UTC timestamp
* schema version (stable)

Another script can fully understand a bundle **without reading markdown**.

---

## 🚀 Installation

We recommend using a Python virtual environment for development tooling.

### Quick installation (pybundle tooling) - RECOMMENDED

Create a dedicated requirements file in the root of your project:

```txt
# requirements-pybundle.txt
ruff
mypy
pytest
pytest-cov
bandit
pip-audit
gwc-pybundle==2.1.0
```

Then install:

```bash
pip install -r requirements-pybundle.txt
```

> **System dependency:**
> pybundle uses `ripgrep (rg)` for source scanning and expects the system binary.
>
> * macOS: `brew install ripgrep`
> * Ubuntu/Debian: `sudo apt install ripgrep`
> * Fedora: `sudo dnf install ripgrep`

After installation, run:

```bash
pybundle run analysis
```

A new `artifacts/` directory will be created containing:

* the compressed bundle
* an extracted working directory
* machine-readable metadata (`MANIFEST.json`, `SUMMARY.json`)

See **Usage** for more details.

---

### Advanced installation

#### From GitHub

```bash
pip install "gwc-pybundle @ git+https://github.com/girls-whocode/pybundle.git@v1.3.1"
```

Pinning to a tag ensures reproducible behavior.

#### Editable install (for development)

```bash
pip install -e .
```

---

## 🧪 Usage

From the root of a Python project, run a profile using the `run` command:

```bash
pybundle run analysis
```

This builds a timestamped diagnostic bundle under the default `artifacts/` directory.

### Profiles

Profiles define *what* pybundle collects and *which tools* are run.

**Available profiles** (v1.4.3+):

* **`analysis`** - What the code IS (structure, metrics, dependencies, docs)
  - Code structure, complexity metrics, documentation coverage
  - Dependency analysis, licenses, performance profiling
  - No error detection or linting
  
* **`debug`** - What's WRONG with the code (errors, issues, problems)
  - Linting, type checking, testing, security scans
  - Error context extraction, anti-pattern detection
  - Includes everything needed for troubleshooting

* **`ai`** - Debug optimized for AI (reduced noise, problem-focused)
  - Same as debug but with defaults tuned for AI consumption
  
* **`backup`** - Minimal snapshot (source + git + env, no analysis)

To list all available profiles:

```bash
pybundle list-profiles
```

Profiles are always invoked via:

```bash
pybundle run <profile>
```

---

### 💾 Backup profile

The `backup` profile creates a minimal, lightweight snapshot ideal for version archival or disaster recovery.

Run it with:

```bash
pybundle run backup
```

#### What `backup` includes

* ✅ Full source code snapshot (respects `.gitignore`)
* ✅ Git status and diff (`meta/00_git_status.txt`, `meta/01_git_diff.txt`)
* ✅ Python version (`meta/20_python_version.txt`)
* ✅ Installed packages (`meta/22_pip_freeze.txt`)
* ✅ Copy manifest (`meta/50_copy_manifest.txt`)
* ❌ No linting, type-checking, or tests
* ❌ No security scanning
* ❌ No ripgrep scans

The result is a **fast, small, restorable archive** with just source code and environment context.

#### Restoring a backup

Backups are created as either `.zip` or `.tar.gz` archives (see Archive Format below).

To extract and inspect:

**For .zip archives:**
```bash
# Look for filename with *_backup_<TIMESTAMP>.zip
unzip <FILENAME>.zip -d restored/
cd restored/<FILENAME>/
```

**For .tar.gz archives:**
```bash
# Look for filename with *_backup_<TIMESTAMP>.tar.gz
tar -xzf <FILENAME>.tar.gz -C restored/
cd restored/<FILENAME>/
```

Inside the extracted directory:

```text
src/                      # Your project source code
meta/
  00_git_status.txt       # Git working tree status at backup time
  01_git_diff.txt         # Uncommitted changes (if any)
  20_python_version.txt   # Python version used
  22_pip_freeze.txt       # Exact package versions
  50_copy_manifest.txt    # List of files included
MANIFEST.json             # Machine-readable metadata
SUMMARY.json              # Structured summary
RUN_LOG.txt               # Execution log
```

The `src/` directory contains your complete project structure.
The `meta/22_pip_freeze.txt` file can be used to recreate the exact environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r meta/22_pip_freeze.txt
```

Then copy your source code back:

```bash
cp -r src/* /path/to/your/project/
```

#### Archive format fallback

pybundle uses **zip** by default for maximum portability.

If the `zip` command is not available on your system, pybundle **automatically falls back to tar.gz** format without requiring configuration.

This ensures backups can be created on any system, regardless of installed compression tools.

To explicitly control the format:

```bash
pybundle run backup --format zip      # Force zip (requires zip command)
pybundle run backup --format tar.gz   # Force tar.gz (requires tar command)
pybundle run backup --format auto     # Auto-detect (default behavior)
```

Both formats preserve the same internal structure and metadata.

---

### 🔍 Analysis Tools

The `analysis` and `debug` profiles run comprehensive quality and security checks:

#### Code Quality
* **ruff** - Fast Python linter and formatter checks
* **mypy** - Static type checking for type hints
* **pylance** - Syntax error detection and import analysis
* **vulture** - Dead code detection (v1.3.0+)
* **radon** - Cyclomatic complexity and maintainability metrics (v1.3.0+)
* **interrogate** - Docstring coverage analysis (v1.3.0+)
* **pylint duplication** - Code duplication detection (v1.3.0+)

#### Testing & Coverage
* **pytest** - Test execution and results
* **coverage** - Code coverage analysis (shows tested vs untested code)

#### Security
* **bandit** - Security vulnerability scanning for Python code
* **pip-audit** - Dependency vulnerability checking against known CVEs

#### Dependency Analysis (v1.3.1+)
* **pipdeptree** - Full dependency tree with conflict detection
* **unused dependencies** - Identify installed but unused packages
* **pip-licenses** - License scanning and compatibility warnings
* **dependency sizes** - Disk usage analysis per package

#### Performance Profiling (v1.4.0+)
* **cProfile** - CPU profiling to identify bottlenecks
* **import time analysis** - Detect slow module imports
* **tracemalloc** - Memory profiling (*enabled by default in v1.4.2+*)
* **line_profiler** - Line-by-line profiling (optional, requires `@profile` decorators and `--enable-line-profiler`)

#### Test Quality & Coverage Enhancement (v1.4.1+)
* **Colorful progress indicators** - Real-time colored output with step counts (🟢 green = success, 🟡 yellow = skipped, 🔴 red = failed)
  - *v1.4.2: Fixed color support for xterm and other terminals*
* **Test flakiness detection** - Run tests multiple times to identify non-deterministic failures
* **Branch coverage** - Enhanced coverage.py integration showing missing branches, not just lines
* **Slow test identification** - Automatically identify and rank tests exceeding time threshold
* **Mutation testing** - Optional mutmut integration to measure test suite effectiveness (VERY SLOW - disabled by default)

#### Performance Profiling (v1.4.0+)
* **cProfile integration** - CPU profiling showing slowest functions
* **import time analysis** - Detect slow module imports
* **tracemalloc** - Memory profiling (*v1.4.2: enabled by default*)
* **line_profiler** - Line-by-line profiling (optional, requires `@profile` decorators and `--enable-line-profiler`)

#### Pattern Scanning
* **ripgrep scans** - TODO detection, print statements, bare excepts

All tools gracefully skip if not installed. Install recommended tools:

```bash
pip install ruff mypy pytest pytest-cov bandit pip-audit vulture radon interrogate pylint pipdeptree pip-licenses
```

For ripgrep (system dependency):
* macOS: `brew install ripgrep`
* Ubuntu/Debian: `sudo apt install ripgrep`

---

### 🤖 AI profile (NEW)

The `ai` profile is optimized for handing a project to AI tooling
(ChatGPT, local LLMs, code assistants, etc.).

It prioritizes **source code and reproducible context**, while skipping
expensive or noisy steps by default.

Run it with:

```bash
pybundle run ai
```

#### What `ai` does by default

* ✅ Includes full curated source snapshot (`src/`)
* ✅ Includes environment + git metadata
* ✅ Generates `REPRO.md` and `HANDOFF.md`
* ❌ Skips linting, type-checking, tests
* ❌ Skips ripgrep scans and error-context expansion
* ❌ Skips `compileall` unless explicitly enabled

The result is a **small, fast, AI-friendly bundle** that still preserves
determinism and traceability.

You may selectively re-enable tools:

```bash
pybundle run ai --ruff --mypy
pybundle run ai --compileall
```

This makes `ai` suitable for:

* AI-assisted refactoring
* Large-context summarization
* Code review handoff
* Offline or local LLM workflows

---

### Common options

Most usage customizations are done through flags on `pybundle run`.

Example:

```bash
pybundle run analysis \
  --format zip \
  --outdir ./artifacts \
  --name myproject-bundle \
  --strict
```

Commonly used options:

* `--format {auto,zip,tar.gz}` - archive format
* `--outdir PATH` - output directory (default: `<project>/artifacts`)
* `--name NAME` - override archive name prefix
* `--strict` - fail with non-zero exit code if any step fails
* `--redact / --no-redact` - control secret redaction

Tool execution can be selectively disabled:

```bash
--no-ruff
--no-mypy
--no-pylance
--no-pytest
--no-bandit
--no-pip-audit
--no-coverage
--no-rg
--no-error-refs
--no-context
```

For the full list of options:

```bash
pybundle run --help
```

---

### Doctor mode

To see which tools are available and what *would* run (without creating a bundle):

```bash
pybundle doctor
```

You may optionally specify a profile to preview:

```bash
pybundle doctor analysis
```

This is useful for validating environment readiness (CI, fresh machines, etc.).

---

### Version

To check the installed version:

```bash
pybundle version
```

---

## 🧠 Ignore behavior (important)

### If inside a Git repository

pybundle uses **Git itself** to determine which files are included:

* `.gitignore`
* `.git/info/exclude`
* global gitignore rules

This guarantees pybundle sees the project **exactly as Git does**.

### If Git is unavailable

pybundle falls back to safe structural rules:

* ignores `__pycache__`, `.ruff_cache`, `.mypy_cache`, `.pytest_cache`, etc.
* detects virtual environments by structure (`pyvenv.cfg`, `bin/activate`), not by name
  → works with `.venv`, `.pybundle-venv`, `env-prod-2025`, etc.

---

## 🧾 Machine-Readable Output (`--json`)

All `pybundle` commands support a **machine-readable JSON output mode** via the `--json` flag.

When enabled, `pybundle` emits **exactly one JSON object to stdout**, with a **stable schema** intended for:

* CI pipelines
* automation scripts
* external tooling
* AI orchestration
* reproducible analysis

No human text or formatting are mixed into the output.

### Example

```bash
pybundle run analysis --json
```

Output:

```json
{
  "status": "ok",
  "command": "run",
  "profile": "analysis",
  "files_included": 39,
  "files_excluded": 0,
  "duration_ms": 394,
  "bundle_path": "/home/jessica/repositories/python/pybundle/artifacts/pybundle_analysis_20260103T102440Z.zip"
}
```

The same structure applies to **all profiles**:

```bash
pybundle run ai --json
pybundle run debug --json
pybundle run backup --json
```

---

### JSON Field Definitions

| Field            | Description                                        |
| ---------------- | -------------------------------------------------- |
| `status`         | `"ok"` or `"fail"` based on execution result       |
| `command`        | The command executed (`run` or `doctor`)           |
| `profile`        | The profile used (`analysis`, `ai`, `debug`, etc.) |
| `files_included` | Number of files copied into the bundle             |
| `files_excluded` | Number of *evaluated* files skipped by policy      |
| `duration_ms`    | Total execution time in milliseconds               |
| `bundle_path`    | Absolute path to the generated archive             |

---

### Important Semantics: `files_excluded`

`files_excluded` **does not** mean “everything in the repository that was not bundled.”

Instead, it means:

> Files that were **eligible under the active profile’s policy** and were *explicitly skipped* after evaluation.

Files and directories that are **intentionally out of scope** — such as:

* `.git/`
* `node_modules/`
* virtual environments
* build artifacts
* caches

are **never considered**, and therefore are **not counted as excluded**.

This design keeps metrics honest and avoids inflating counts with known-irrelevant infrastructure.

A value of `files_excluded = 0` simply means:

> *Everything that was evaluated was worth keeping.*

This is expected and normal for clean, well-structured projects — especially in `ai` mode.

---

### JSON Stability Guarantee

The JSON schema emitted by `--json` is considered **part of the public API**.

Starting with **v1.0**, field names and meanings will remain stable.
New fields may be added, but existing fields will not be renamed or removed.

This allows `pybundle` to be safely embedded into:

* CI workflows
* automation scripts
* AI pipelines
* external tooling

without fear of breaking changes.

---

## 📜 Profiles

pybundle is profile-driven. Each profile defines:

* what files are collected
* which tools run
* what metadata is emitted

Example profiles:

* `analysis`
* `source`
* `minimal`

Profiles are extensible - add your own without modifying core logic.

---

## 🔐 Safety & Redaction

By default, pybundle:

* avoids scanning known secret locations
* supports optional redaction of sensitive strings in logs

Use `--redact / --no-redact` to control behavior.

---
## 🔒 Security Considerations

**pybundle** is a development tool designed for trusted environments.

### Threat Model

* **Environment:** Development machines and CI/CD pipelines
* **Trust Boundary:** Assumes trusted development environment
* **Execution Context:** Runs external tools (git, ruff, mypy, pytest, etc.)
* **Input Sources:** Project files, git repository, installed packages

### Security Posture

**Tool Path Resolution:**
- All external tools use full resolved paths (via `shutil.which()`)
- Tools are resolved at detection time and stored in `Tooling` dataclass
- No dynamic PATH manipulation or shell interpretation
- Eliminates partial path execution vulnerabilities (B607)
- **Optional strict-paths mode** for enhanced security (v1.2.0+)
- **Code quality tools** for dead code, complexity, docstrings, and duplication (v1.3.0+)
- **Dependency intelligence** for conflict detection, license scanning, and size analysis (v1.3.1+)

**Subprocess Execution:**
- All subprocess calls use `shell=False` (default, secure)
- Arguments passed as lists, never as strings
- No user-controlled command construction
- Commands are hardcoded in source code

**Data Handling:**
- Optional secret redaction for sensitive strings in logs
- Environment variables and paths logged for reproducibility
- All file operations respect `.gitignore` rules

### Strict-Paths Mode (v1.2.0+)

For high-security environments, enable `--strict-paths` to enforce that all tools must be in trusted system directories:

```bash
pybundle run analysis --strict-paths
```

**Trusted directories** (configurable via `PYBUNDLE_TRUSTED_PATHS`):
- `/usr/bin/`, `/usr/local/bin/`, `/bin/`
- `/opt/homebrew/bin/` (macOS Homebrew)
- `/snap/bin/` (Ubuntu snaps)
- Virtual environment paths (`.venv`, `venv`, `.pybundle-venv`)

Tools outside trusted directories are excluded in strict mode. This prevents:
- Accidental execution of tools from user-writable directories
- PATH manipulation attacks
- Use of potentially compromised tool installations

**Example:** Verify tool paths before running:
```bash
pybundle doctor --strict-paths
```

Output shows trust status:
```
🔧 Tool Detection:
git        ✅ /usr/bin/git
python     ✅ /path/to/venv/bin/python
npm        ⚠️  /home/user/.nvm/.../npm  (untrusted in strict mode)
```

**Configure custom trusted paths:**
```bash
export PYBUNDLE_TRUSTED_PATHS="/opt/custom/bin:/company/tools/bin"
pybundle run debug --strict-paths
```

### Known Limitations

1. **Requires Trusted Environment**
   - Assumes developer controls their machine and installed tools
   - Not designed for untrusted code execution or sandboxing
   - Tool integrity depends on system package management

2. **Tool Availability**
   - External tools (git, ruff, mypy) are optional
   - Missing tools result in SKIP status, not failure
   - Use `pybundle doctor` to verify available tools

3. **File System Access**
   - Reads entire project tree (respecting ignore rules)
   - Writes to `artifacts/` directory by default
   - No privilege escalation or system modification

### For Security Auditors

**Bandit Security Scan Results:**
- 33 low-severity findings (all expected for CLI tool)
- **B404** (subprocess import): Required for tool functionality
- **B603** (subprocess calls): Using secure pattern (shell=False, full paths)
- **B112** (try/except/continue): Acceptable error handling pattern

**Risk Classification:** LOW
- No user-controlled command injection
- No untrusted input in command execution
- Full path resolution prevents PATH manipulation attacks
- Standard development tool security posture

**Recommended Usage:**
```bash
# Verify tool paths before execution
pybundle doctor

# Review what tools will be used
pybundle doctor analysis --json
```

---
## 🧩 Why pybundle?

pybundle is designed for:

* handing a project to another engineer
* attaching context to a bug report
* feeding a codebase to AI tooling
* generating CI artifacts
* preserving “what exactly did we run?”
* producing **AI-consumable project context** without guesswork

It prioritizes **determinism, traceability, and automation** over clever heuristics.

---

## 🛠 Development Notes

* Python ≥ 3.9
* Uses modern tooling (ruff, mypy)
* Fully type-checked
* Formatter-clean
* No test suite *yet* (intentional; coming later)

During development, run:

```bash
python -m pybundle ...
```

to bypass shell caching.

### Release Process

To release a new version:

```bash
./release.sh --push-release v2.1.0
```

The script automates:
- Version updates (pyproject.toml, README.md)
- Git tagging and pushing
- GitHub release creation
- Triggers PyPI publish via CI

See [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md) for details.

---

## 📌 Versioning

pybundle follows **Semantic Versioning**.

Pinned Git tags are recommended when used as a dependency:

```txt
gwc-pybundle @ git+https://github.com/girls-whocode/pybundle.git@v1.3.1
```

---

## 🧠 Philosophy

> If a tool produces output, it should also produce metadata about **how** and **why** that output exists.

pybundle treats context as a first-class artifact.

---

## 📦 Package naming note

The distribution name on PyPI is **`gwc-pybundle`** to avoid conflicts with existing packages.

The project name, imports, and CLI remain **`pybundle`**.

```bash
pip install gwc-pybundle
pybundle run analysis
```
Look in the autocreated `artifacts/` folder.

## 📄 License

MIT License
