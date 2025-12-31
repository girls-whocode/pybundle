from __future__ import annotations

import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..tools import which

@dataclass
class ReproMarkdownStep:
    name: str = "generate REPRO.md"
    outfile: str = "REPRO.md"

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        repro = ctx.workdir / self.outfile

        # ---- tool detection ----
        tool_names = ["python", "pip", "git", "ruff", "mypy", "pytest", "rg", "zip", "tar"]
        detected = {t: which(t) for t in tool_names}

        # Prefer ctx.tools.python if you have it
        if getattr(ctx, "tools", None) and getattr(ctx.tools, "python", None):
            detected["python"] = ctx.tools.python

        # ---- file inventory (what actually exists) ----
        def list_txt(dirpath: Path) -> list[str]:
            if not dirpath.is_dir():
                return []
            return sorted(str(p.relative_to(ctx.workdir)) for p in dirpath.rglob("*.txt"))

        logs_list = list_txt(ctx.logdir)
        meta_list = list_txt(ctx.metadir)

        # Also include key top-level files if present
        top_files = []
        for name in ["RUN_LOG.txt", "SUMMARY.json", "error_files_from_logs.txt", "error_refs_count.txt"]:
            p = ctx.workdir / name
            if p.exists():
                top_files.append(name)

        # ---- step summary (best-effort, never crash) ----
        results = getattr(ctx, "results", [])
        ctx.results = results  # ensure it's set for future steps
        
        summary_lines = []
        for r in results:
            note = f" ({r.note})" if getattr(r, "note", "") else ""
            summary_lines.append(f"- **{r.name}**: {r.status}{note}")

        # ---- environment ----
        pyver = sys.version.split()[0]
        plat = platform.platform()
        profile = ctx.profile_name
        utc_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # ---- build markdown ----
        def fmt_tool(t: str) -> str:
            path = detected.get(t)
            return f"- `{t}`: ✅ `{path}`" if path else f"- `{t}`: ❌ not found"

        md = []
        md += ["# Reproduction Guide", ""]
        md += [
            "This bundle captures diagnostic outputs and the minimum relevant project context",
            "to reproduce issues reliably on another system.",
            "",
            "## Overview",
            f"- Profile: `{profile}`",
            f"- Generated (UTC): `{utc_now}`",
            f"- Project root: `{ctx.root}`",
            "",
            "## Environment Snapshot",
            f"- OS: `{plat}`",
            f"- Python: `{pyver}`",
            "",
            "## Tools Detected",
            *[fmt_tool(t) for t in tool_names],
            "",
        ]

        if summary_lines:
            md += ["## Steps Executed", *summary_lines, ""]

        md += [
            "## How to Reproduce",
            "",
            "From the project root:",
            "",
            "```bash",
            f"python -m pybundle run {profile}",
            "```",
            "",
            "Re-run individual tools (if installed):",
            "",
            "```bash",
            "python -m compileall .",
            "ruff check .",
            "ruff format --check .",
            "mypy .",
            "pytest -q",
            "```",
            "",
            "## Produced Artifacts",
            "",
        ]

        if top_files:
            md += ["### Top-level", *[f"- `{p}`" for p in top_files], ""]

        md += ["### logs/", *(f"- `{p}`" for p in logs_list)] if logs_list else ["### logs/", "- (none)", ""]
        md += ["", "### meta/", *(f"- `{p}`" for p in meta_list)] if meta_list else ["", "### meta/", "- (none)"]

        md += [
            "",
            "## Context Packs",
            "",
            "- `src/_error_refs/` – files directly referenced by tool output",
            "- `src/_error_context/` – related imports + pytest glue (conftest/__init__) + configs",
            "",
            "## Notes",
            "",
            "- Non-zero exits from linters/tests are recorded for diagnosis; bundle creation continues.",
            "- Missing tools typically produce SKIP logs rather than failing the bundle.",
            "",
        ]

        repro.write_text("\n".join(md) + "\n", encoding="utf-8")

        dur = int(time.time() - start)
        return StepResult(self.name, "PASS", dur, "")
