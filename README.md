# 🧳 pybundle
 
**pybundle** is a deterministic, automation-friendly tool for collecting Python project context into a single, shareable bundle - ideal for debugging, audits, AI assistance, CI artifacts, or handoff between engineers.

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
* 🔍 Optional tooling checks (ruff, mypy, pytest, ripgrep scans)
* 🧪 Deterministic output (stable paths, timestamps, schemas)
* 🔒 Secret-safe (optional redaction)

---

## 📂 What’s in a pybundle archive?

At minimum, a bundle contains:

```text
MANIFEST.json        # stable, machine-readable metadata
SUMMARY.json         # structured summary of collected data
src/                 # filtered project source snapshot
logs/                # tool outputs (ruff, mypy, etc.)
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
gwc-pybundle==0.4.3
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
pip install "gwc-pybundle @ git+https://github.com/girls-whocode/pybundle.git@v0.4.3"
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

Available profiles include:

* `analysis` - **full diagnostics** (lint, type-check, tests, scans)
* `debug` - **analysis + additional environment validation**
* `backup` - **minimal environment snapshot**
* `ai` - **AI-optimized context bundle** (lean, source-first)

To list all available profiles:

```bash
pybundle list-profiles
```

Profiles are always invoked via:

```bash
pybundle run <profile>
```
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
* `--no-spinner` - disable spinner output (CI-friendly)
* `--redact / --no-redact` - control secret redaction

Tool execution can be selectively disabled:

```bash
--no-ruff
--no-mypy
--no-pytest
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

No filename guessing. No surprises.

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

---

## 📌 Versioning

pybundle follows **Semantic Versioning**.

Pinned Git tags are recommended when used as a dependency:

```txt
gwc-pybundle @ git+https://github.com/girls-whocode/pybundle.git@v0.4.3
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
 Look in the autocreated `artifacts/` folder

## 📄 License

MIT License
