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

---

## Why pybundle?

**pybundle** exists to solve a boring but expensive problem:

> **Context loss.**

Modern debugging, CI, audits, and AI-assisted workflows fail not because tools are weak —
but because **context is fragmented, ephemeral, or missing entirely**.

pybundle creates a **single, deterministic artifact** that captures:

* the exact source code that mattered
* the tools that ran (and their versions)
* the environment they ran in
* the outputs they produced
* and the metadata required to reproduce or reason about it later

For humans, automation, and AI.

Think:

> **`git archive` + diagnostics + metadata**
> without heuristics, guesswork, or “works on my machine.”

---

## What pybundle is good at

pybundle is designed for:

* handing a project to another engineer
* attaching full context to a bug report
* generating CI artifacts that actually explain failures
* feeding codebases to AI tools without noise
* audits, reviews, and reproducibility
* answering *“what exactly did we run?”* weeks later

It prioritizes **determinism, traceability, and automation** over cleverness.

---

## Installation

```bash
pip install gwc-pybundle
```

> **Note:**
> The PyPI package name is `gwc-pybundle`, but the CLI command is `pybundle`.

Quick sanity check:

```bash
pybundle version
```

---

## Where to go next

📚 **Documentation (Wiki)**
➡ [https://github.com/girls-whocode/pybundle/wiki](https://github.com/girls-whocode/pybundle/wiki)

The Wiki contains:

* Usage and profiles
* Security & redaction
* JSON output contracts
* CI integration
* AI handoff workflows
* FAQs and design rationale

💬 **Questions & Discussion**
➡ [https://github.com/girls-whocode/pybundle/discussions](https://github.com/girls-whocode/pybundle/discussions)

Use Discussions for:

* “Is pybundle right for this?”
* Workflow questions
* Design feedback
* Feature ideas
* Real-world use cases

---

## Philosophy

> If a tool produces output, it should also produce metadata explaining
> **how** and **why** that output exists.

pybundle treats **context as a first-class artifact**.

---

## License

MIT License

