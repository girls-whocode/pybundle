# pybundle CLI Arguments Reference

Comprehensive guide to all `pybundle` command-line arguments, options, and expected outputs.

---

## Table of Contents

- [Commands](#commands)
  - [run](#run-command)
  - [doctor](#doctor-command)
  - [version](#version-command)
  - [list-profiles](#list-profiles-command)
- [Profiles](#profiles)
- [Common Arguments](#common-arguments)
- [Tool Control Flags](#tool-control-flags)
- [Security Options](#security-options)
- [Target & Argument Options](#target--argument-options)
- [Capacity Options](#capacity-options)
- [Examples](#examples)

---

## Commands

### `run` Command

Execute a profile and create a bundle archive.

**Syntax:**
```bash
pybundle run <profile> [options]
```

**Required:**
- `<profile>` - One of: `analysis`, `debug`, `backup`, `ai`

**Example:**
```bash
pybundle run analysis
```

**Expected Output:**
```
✅ Archive created: /path/to/artifacts/pybundle_analysis_20260118T120000Z.zip
📁 Workdir kept:     /path/to/artifacts/pybundle_analysis_20260118T120000Z
```

---

### `doctor` Command

Preview what would run without creating a bundle. Useful for validating tool availability and configuration.

**Syntax:**
```bash
pybundle doctor [profile] [options]
```

**Optional:**
- `[profile]` - One of: `analysis`, `debug`, `backup`, `ai` (default: `analysis`)

**Example:**
```bash
pybundle doctor
```

**Expected Output:**
```
Root: /home/user/project
Out:  /home/user/project/artifacts

🔧 Tool Detection:
======================================================================
  git        ✅ /usr/bin/git
  python     ✅ /path/to/venv/bin/python
  pip        ✅ /path/to/venv/bin/pip
  zip        ✅ /usr/bin/zip
  tar        ✅ /usr/bin/tar
  uname      ✅ /usr/bin/uname
  ruff       ✅ /path/to/venv/bin/ruff
  mypy       ✅ /path/to/venv/bin/mypy
  pytest     ❌ <missing>
  rg         ✅ /usr/bin/rg
  tree       ✅ /usr/bin/tree
  npm        ⚠️  /home/user/.nvm/versions/node/v20.0.0/bin/npm
======================================================================

Options:
  strict_paths:      False
  ruff_target:       .
  mypy_target:       .
  pytest_args:       -q
  no_ruff:           None
  no_mypy:           None
  ...

Plan (analysis):
  RUN  git status                   -> meta/00_git_status.txt
  RUN  git diff                     -> meta/01_git_diff.txt
  SKIP pytest                       -> logs/34_pytest_q.txt (no tests/ directory found)
  ...
```

**With strict-paths:**
```bash
pybundle doctor --strict-paths
```

Shows `⚠️ STRICT-PATHS MODE ENABLED` warning and filters untrusted tools.

---

### `version` Command

Display installed pybundle version.

**Syntax:**
```bash
pybundle version
```

**Expected Output:**
```
pybundle 1.2.1
```

---

### `list-profiles` Command

List all available profiles.

**Syntax:**
```bash
pybundle list-profiles
```

**Expected Output:**
```
Available profiles:
  - analysis
  - debug
  - backup
  - ai
```

---

## Profiles

### `analysis`

Full diagnostic bundle with all quality checks.

**Includes:**
- Git status and diff
- System information (uname)
- Directory tree
- Largest files report
- Ruff linting and format checking
- Mypy type checking
- Pylance syntax/import analysis
- Pytest execution
- Bandit security scanning
- pip-audit CVE checking
- Coverage analysis
- Ripgrep pattern scans (TODOs, prints, bare excepts)
- Error reference collection
- Context expansion
- Python compilation check
- Source code snapshot

**Use when:** You need comprehensive diagnostics for debugging or code review.

---

### `debug`

All of `analysis` plus additional validation.

**Additional steps:**
- `pip check` - Verify package compatibility

**Use when:** Troubleshooting dependency or environment issues.

---

### `backup`

Minimal snapshot for archival or disaster recovery.

**Includes:**
- Git status and diff
- Python version
- pip freeze (exact package versions)
- Source code snapshot
- **Excludes:** All analysis tools (no linting, testing, scanning)

**Use when:** Creating version snapshots, archiving releases, or disaster recovery backups.

---

### `ai`

Optimized bundle for AI/LLM consumption.

**Includes:**
- Source code snapshot
- Git metadata
- Environment info
- REPRO.md and HANDOFF.md generation
- Pylance analysis (syntax/imports)
- **Excludes by default:** Ruff, mypy, pytest, coverage, ripgrep scans

**Can selectively enable:**
```bash
pybundle run ai --ruff --mypy
```

**Use when:** Feeding codebase to ChatGPT, Claude, or other AI coding assistants.

---

## Common Arguments

### `--format {auto,zip,tar.gz}`

Archive format. Default: `auto` (prefers zip, falls back to tar.gz if zip unavailable).

**Examples:**
```bash
pybundle run analysis --format zip
pybundle run backup --format tar.gz
```

**Output:**
```
✅ Archive created: .../pybundle_analysis_20260118T120000Z.zip
```

---

### `--outdir PATH`

Output directory for artifacts. Default: `<project>/artifacts`

**Example:**
```bash
pybundle run analysis --outdir ./build/bundles
```

**Creates:**
```
build/bundles/
  pybundle_analysis_20260118T120000Z/
  pybundle_analysis_20260118T120000Z.zip
```

---

### `--name NAME`

Override archive name prefix. Default: `pybundle_<profile>_<timestamp>`

**Example:**
```bash
pybundle run analysis --name myproject-v1.0.0
```

**Creates:**
```
artifacts/myproject-v1.0.0.zip
```

---

### `--strict`

Fail with non-zero exit code if any step fails. Default: false (steps can fail without stopping bundle creation).

**Example:**
```bash
pybundle run analysis --strict
```

**Behavior:**
- Exit code 0: All steps passed
- Exit code 1: At least one step failed

**Use when:** CI/CD pipelines that should fail on quality issues.

---

### `--redact` / `--no-redact`

Control secret redaction in logs. Default: `--redact` (enabled).

**Example:**
```bash
pybundle run debug --no-redact
```

**When enabled:** Paths and sensitive strings are replaced with `<REDACTED>` in output files.

---

### `--json`

Output machine-readable JSON instead of human-friendly text.

**Example:**
```bash
pybundle run analysis --json
```

**Output:**
```json
{
  "status": "ok",
  "command": "run",
  "profile": "analysis",
  "files_included": 42,
  "files_excluded": 0,
  "duration_ms": 1250,
  "bundle_path": "/path/to/artifacts/pybundle_analysis_20260118T120000Z.zip"
}
```

**Use when:** Integrating with scripts, CI/CD, or automation tools.

---

### `--clean-workdir`

Delete expanded workdir after archiving. Default: keep workdir.

**Example:**
```bash
pybundle run analysis --clean-workdir
```

**Result:** Only `.zip` file remains, extracted directory is deleted.

---

## Tool Control Flags

Control which analysis tools run. All tools are enabled by default in `analysis`/`debug` profiles.

### Linting & Type Checking

**`--ruff` / `--no-ruff`**

Enable/disable Ruff linting and format checking.

```bash
pybundle run analysis --no-ruff      # Skip ruff
pybundle run ai --ruff                # Enable in ai profile
```

**`--mypy` / `--no-mypy`**

Enable/disable Mypy type checking.

```bash
pybundle run analysis --no-mypy
```

**`--pylance` / `--no-pylance`**

Enable/disable Pylance syntax/import analysis.

```bash
pybundle run analysis --no-pylance
```

**`--vulture` / `--no-vulture` (v1.3.0+)**

Enable/disable dead code detection.

```bash
pybundle run analysis --no-vulture
```

**`--radon` / `--no-radon` (v1.3.0+)**

Enable/disable complexity and maintainability metrics.

```bash
pybundle run analysis --no-radon
```

**`--interrogate` / `--no-interrogate` (v1.3.0+)**

Enable/disable docstring coverage analysis.

```bash
pybundle run analysis --no-interrogate
```

**`--duplication` / `--no-duplication` (v1.3.0+)**

Enable/disable code duplication detection.

```bash
pybundle run analysis --no-duplication
```

---

### Testing & Coverage

**`--pytest` / `--no-pytest`**

Enable/disable pytest execution.

```bash
pybundle run analysis --no-pytest
```

**`--coverage` / `--no-coverage`**

Enable/disable coverage analysis (via pytest-cov).

```bash
pybundle run analysis --no-coverage
```

---

### Security Scanning

**`--bandit` / `--no-bandit`**

Enable/disable Bandit security vulnerability scanning.

```bash
pybundle run analysis --no-bandit
```

**`--pip-audit` / `--no-pip-audit`**

Enable/disable pip-audit CVE checking.

```bash
pybundle run analysis --no-pip-audit
```

---

### Dependency Analysis (v1.3.1+)

**`--pipdeptree` / `--no-pipdeptree`**

Enable/disable dependency tree visualization with conflict detection.

```bash
pybundle run analysis --no-pipdeptree
```

**`--unused-deps` / `--no-unused-deps`**

Enable/disable unused dependency detection.

```bash
pybundle run analysis --no-unused-deps
```

**`--license-scan` / `--no-license-scan`**

Enable/disable license scanning and compatibility warnings.

```bash
pybundle run analysis --no-license-scan
```

**`--dependency-sizes` / `--no-dependency-sizes`**

Enable/disable dependency size analysis.

```bash
pybundle run analysis --no-dependency-sizes
```

---

### Performance Profiling (v1.4.0+)

**`--profile` / `--no-profile`**

Enable/disable performance profiling (CPU and import time analysis).

```bash
pybundle run analysis --no-profile
```

**`--profile-entry-point PATH`**

Specify entry point for profiling (file or directory).

```bash
pybundle run analysis --profile-entry-point main.py
pybundle run analysis --profile-entry-point tests/
```

**`--profile-memory`**

Enable memory profiling with tracemalloc (requires pytest).

```bash
pybundle run analysis --profile-memory
```

**`--enable-line-profiler`**

Enable line-by-line profiling (requires line_profiler and @profile decorators).

```bash
pybundle run analysis --enable-line-profiler --profile-entry-point script.py
```

---

### Pattern Scanning

**`--rg` / `--no-rg`**

Enable/disable ripgrep pattern scans (TODOs, prints, bare excepts).

```bash
pybundle run analysis --no-rg
```

---

### Context Collection

**`--error-refs` / `--no-error-refs`**

Enable/disable error-referenced file collection.

```bash
pybundle run analysis --no-error-refs
```

**`--context` / `--no-context`**

Enable/disable error context expansion.

```bash
pybundle run analysis --no-context
```

**`--compileall` / `--no-compileall`**

Enable/disable Python compilation check (disabled by default in `ai` profile).

```bash
pybundle run ai --compileall
```

---

## Security Options

### `--strict-paths` (v1.2.0+)

**Enforce trusted path validation for all tools.**

Only tools from trusted system directories are used:
- `/usr/bin/`, `/usr/local/bin/`, `/bin/`
- `/opt/homebrew/bin/` (macOS)
- `/snap/bin/` (Ubuntu snaps)
- Virtual environments (`.venv`, `venv`, `.pybundle-venv`)

**Example:**
```bash
pybundle run analysis --strict-paths
```

**Doctor output shows trust status:**
```
🔧 Tool Detection:
======================================================================
  git        ✅ /usr/bin/git
  npm        ❌ <missing>  (was in /home/user/.nvm/... - untrusted)

⚠️  STRICT-PATHS MODE ENABLED
   Only tools in trusted directories are available.
```

**Custom trusted paths:**
```bash
export PYBUNDLE_TRUSTED_PATHS="/opt/custom/bin:/company/tools"
pybundle run analysis --strict-paths
```

**Use when:**
- High-security corporate environments
- Preventing PATH manipulation attacks
- Ensuring only system-managed tools execute

---

## Target & Argument Options

### `--ruff-target PATH`

Directory for Ruff to check. Default: `.` (current directory).

**Example:**
```bash
pybundle run analysis --ruff-target ./src
```

---

### `--mypy-target PATH`

Directory for Mypy to check. Default: `.`

**Example:**
```bash
pybundle run analysis --mypy-target ./src
```

---

### `--pytest-args "ARGS"`

Arguments passed to pytest. Default: `-q` (quiet mode).

**Example:**
```bash
pybundle run analysis --pytest-args "--maxfail=1 -v"
pybundle run analysis --pytest-args "-k test_critical"
```

**Note:** Provide as single quoted string with space-separated arguments.

---

## Capacity Options

Control limits for file scanning and context collection.

### `--error-max-files N`

Maximum files to collect for error references. Default: `250`

**Example:**
```bash
pybundle run debug --error-max-files 500
```

---

### `--context-depth N`

Depth of context expansion around errors. Default: `2`

**Example:**
```bash
pybundle run debug --context-depth 3
```

---

### `--context-max-files N`

Maximum files for context expansion. Default: `600`

**Example:**
```bash
pybundle run debug --context-max-files 1000
```

---

## Examples

### Basic Usage

**Create analysis bundle:**
```bash
pybundle run analysis
```

**Check what would run:**
```bash
pybundle doctor analysis
```

**Quick backup:**
```bash
pybundle run backup
```

---

### AI/LLM Workflows

**Prepare for ChatGPT:**
```bash
pybundle run ai
```

**Enable syntax checking only:**
```bash
pybundle run ai --pylance
```

**Full analysis for AI with linting:**
```bash
pybundle run ai --ruff --mypy --pylance
```

---

### CI/CD Integration

**Strict mode with JSON output:**
```bash
pybundle run analysis --strict --json
```

**Parse JSON result:**
```bash
result=$(pybundle run analysis --json)
status=$(echo "$result" | jq -r '.status')
if [ "$status" != "ok" ]; then
  echo "Bundle creation failed"
  exit 1
fi
```

---

### Security-Focused

**Enterprise security mode:**
```bash
pybundle run debug --strict-paths --strict
```

**Verify tool paths before running:**
```bash
pybundle doctor --strict-paths
```

**Custom trusted paths:**
```bash
export PYBUNDLE_TRUSTED_PATHS="/opt/company/bin"
pybundle run analysis --strict-paths
```

---

### Selective Tool Execution

**Lint and type-check only:**
```bash
pybundle run analysis \
  --no-pytest \
  --no-bandit \
  --no-pip-audit \
  --no-coverage \
  --no-rg \
  --no-error-refs \
  --no-context
```

**Security audit only:**
```bash
pybundle run analysis \
  --no-ruff \
  --no-mypy \
  --no-pylance \
  --no-pytest \
  --no-coverage \
  --no-rg
```

---

### Custom Output

**Specific output directory:**
```bash
pybundle run analysis --outdir ./release-bundles
```

**Custom name for versioned releases:**
```bash
pybundle run backup --name myproject-v2.1.0-backup
```

**Tar.gz format for Linux servers:**
```bash
pybundle run analysis --format tar.gz
```

---

### Advanced Combinations

**Comprehensive debug bundle with strict security:**
```bash
pybundle run debug \
  --strict-paths \
  --strict \
  --outdir ./debug-artifacts \
  --name critical-issue-2026-01-18 \
  --context-depth 3 \
  --error-max-files 500
```

**Minimal AI bundle with custom args:**
```bash
pybundle run ai \
  --pylance \
  --pytest-args "-k test_important" \
  --outdir ./ai-context \
  --name feature-implementation
```

**CI/CD quality gate:**
```bash
#!/bin/bash
set -e

# Run with strict checking
pybundle run analysis \
  --strict \
  --strict-paths \
  --json \
  --clean-workdir > bundle_result.json

# Parse results
status=$(jq -r '.status' bundle_result.json)
bundle_path=$(jq -r '.bundle_path' bundle_result.json)

if [ "$status" = "ok" ]; then
  echo "✅ Quality checks passed"
  echo "📦 Bundle: $bundle_path"
  exit 0
else
  echo "❌ Quality checks failed"
  exit 1
fi
```

---

## Quick Reference Table

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--format` | choice | `auto` | Archive format: auto, zip, tar.gz |
| `--outdir` | path | `artifacts/` | Output directory |
| `--name` | string | `pybundle_<profile>_<ts>` | Archive name prefix |
| `--strict` | flag | `false` | Fail on step errors |
| `--strict-paths` | flag | `false` | Enforce trusted tool paths |
| `--redact` | flag | `true` | Enable secret redaction |
| `--no-redact` | flag | - | Disable secret redaction |
| `--json` | flag | `false` | Machine-readable JSON output |
| `--clean-workdir` | flag | `false` | Delete workdir after archiving |
| `--ruff-target` | path | `.` | Ruff check directory |
| `--mypy-target` | path | `.` | Mypy check directory |
| `--pytest-args` | string | `-q` | Arguments for pytest |
| `--error-max-files` | int | `250` | Max error reference files |
| `--context-depth` | int | `2` | Error context depth |
| `--context-max-files` | int | `600` | Max context expansion files |

**Tool flags:** All support `--<tool>` and `--no-<tool>` pattern:
- `ruff`, `mypy`, `pylance`, `pytest`, `coverage`
- `bandit`, `pip-audit`, `rg`
- `error-refs`, `context`, `compileall`

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (bundle created, all checks passed with `--strict`) |
| `1` | Failure (bundle creation failed, or step failed with `--strict`) |

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `PYBUNDLE_TRUSTED_PATHS` | Colon-separated list of additional trusted directories for `--strict-paths` mode | `/opt/custom/bin:/company/tools` |

---

## See Also

- [README.md](README.md) - Full project documentation
- [Security Considerations](README.md#-security-considerations) - Security features and best practices
