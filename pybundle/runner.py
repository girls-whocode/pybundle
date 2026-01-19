from __future__ import annotations

import json
import shutil
import sys
import time
from dataclasses import asdict

try:
    from colorama import Fore, Style, init as colorama_init
    # Force colors in xterm and other terminals
    # strip=False keeps ANSI codes, autoreset=True resets after each print
    colorama_init(autoreset=True, strip=False)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback if colorama not available
    class Fore:
        RED = ""
        YELLOW = ""
        GREEN = ""
        CYAN = ""
        RESET = ""
    class Style:
        BRIGHT = ""
        RESET_ALL = ""

from .context import BundleContext
from .packaging import archive_output_path, make_archive, resolve_archive_format
from .manifest import write_manifest
from .steps.base import StepResult


def _emit_progress(msg: str, color: str = "cyan") -> None:
    """Emit a progress message with optional color."""
    color_code = getattr(Fore, color.upper(), Fore.CYAN)
    print(f"{color_code}{msg}{Style.RESET_ALL}", file=sys.stderr, flush=True)


def _emit_step_result(idx: int, total: int, step_name: str, result: StepResult) -> None:
    """Emit colored step result based on status."""
    # Determine color and symbol based on status
    if result.status == "OK":
        color = Fore.GREEN
        symbol = "✓"
    elif result.status == "SKIP":
        color = Fore.YELLOW
        symbol = "⊘"
    elif result.status == "FAIL":
        color = Fore.RED
        symbol = "✗"
    else:
        color = Fore.CYAN
        symbol = "•"
    
    # Format duration
    duration = f"{result.seconds:.2f}s"
    
    # Build status line
    status_msg = f"[{idx}/{total}] {symbol} {step_name}"
    if result.note:
        status_msg += f" - {result.note}"
    status_msg += f" ({duration})"
    
    print(f"{color}{Style.BRIGHT}{status_msg}{Style.RESET_ALL}", file=sys.stderr, flush=True)


def run_profile(ctx: BundleContext, profile) -> int:
    t0 = time.time()
    ctx.write_runlog(f"=== pybundle run {profile.name} ===")
    ctx.write_runlog(f"ROOT: {ctx.root}")
    ctx.write_runlog(f"WORK: {ctx.workdir}")

    ctx.results.clear()
    results: list[StepResult] = ctx.results
    any_fail = False

    total_steps = len(profile.steps)
    for idx, step in enumerate(profile.steps, 1):
        # Progress indicator with step count
        _emit_progress(f"[{idx}/{total_steps}] Running: {step.name}...", "cyan")
        ctx.write_runlog(f"-- START: {step.name}")
        
        r = step.run(ctx)
        results.append(r)
        ctx.results = results
        
        # Colored status output
        _emit_step_result(idx, total_steps, step.name, r)
        ctx.write_runlog(
            f"-- DONE:  {step.name} [{r.status}] ({r.seconds}s) {r.note}".rstrip()
        )
        
        if r.status == "FAIL":
            any_fail = True
            if ctx.strict:
                break

    ctx.summary_json.write_text(
        json.dumps(
            {
                "profile": profile.name,
                "root": str(ctx.root),
                "workdir": str(ctx.workdir),
                "results": [asdict(r) for r in results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    ctx.results = results

    # Write the manifest BEFORE archiving so it's included inside the bundle.
    archive_fmt_used = resolve_archive_format(ctx)
    archive_path = archive_output_path(ctx, archive_fmt_used)

    write_manifest(
        ctx=ctx,
        profile_name=profile.name,
        archive_path=archive_path,
        archive_format_used=archive_fmt_used,
    )

    archive_path, archive_fmt_used = make_archive(ctx)
    ctx.archive_path = archive_path
    ctx.duration_ms = int((time.time() - t0) * 1000)

    ctx.write_runlog(f"ARCHIVE: {archive_path}")

    ctx.emit(f"✅ Archive created: {archive_path}")
    if ctx.keep_workdir:
        ctx.emit(f"📁 Workdir kept:     {ctx.workdir}")

    if not ctx.keep_workdir:
        shutil.rmtree(ctx.workdir, ignore_errors=True)

    if any_fail and ctx.strict:
        return 10
    return 0
