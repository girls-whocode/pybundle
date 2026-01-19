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
        RED: str = ""
        YELLOW: str = ""
        GREEN: str = ""
        CYAN: str = ""
        RESET: str = ""
    class Style:
        BRIGHT: str = ""
        RESET_ALL: str = ""

from .context import BundleContext
from .packaging import archive_output_path, make_archive, resolve_archive_format
from .manifest import write_manifest
from .steps.base import StepResult
from .profiles import Profile


def _format_duration(milliseconds: int) -> str:
    """Format milliseconds into human-readable duration (hr min sec)."""
    seconds = milliseconds / 1000.0
    
    if seconds < 1:
        return f"{milliseconds}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


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
    
    # Format duration in human-readable format
    duration = _format_duration(result.seconds)
    
    # Build status line with colorful step counter and status-colored step name
    step_counter = f"{Fore.BLACK}{Style.BRIGHT}[{Fore.MAGENTA}{idx}{Fore.WHITE}/{Fore.CYAN}{total}{Fore.BLACK}{Style.BRIGHT}]{Style.RESET_ALL}"
    status_msg = f"{step_counter} {color}{Style.BRIGHT}{symbol} {step_name}{Style.RESET_ALL}"
    
    # Add note and duration in terminal default color
    if result.note:
        status_msg += f" - {result.note}"
    status_msg += f" ({duration})"
    
    print(status_msg, file=sys.stderr, flush=True)


def run_profile(ctx: BundleContext, profile: Profile) -> int:
    t0 = time.time()
    ctx.write_runlog(f"=== pybundle run {profile.name} ===")
    ctx.write_runlog(f"ROOT: {ctx.root}")
    ctx.write_runlog(f"WORK: {ctx.workdir}")

    ctx.results.clear()
    results: list[StepResult] = ctx.results
    any_fail = False

    total_steps = len(profile.steps)
    for idx, step in enumerate(profile.steps, 1):
        # Progress indicator with colorful step count: [magenta#white/cyan#] Running: step
        step_counter = f"{Fore.BLACK}{Style.BRIGHT}[{Fore.MAGENTA}{idx}{Fore.WHITE}/{Fore.CYAN}{total_steps}{Fore.BLACK}{Style.BRIGHT}]{Style.RESET_ALL}"
        print(f"{step_counter} {Fore.WHITE}Running: {step.name}...{Style.RESET_ALL}", file=sys.stderr, flush=True)
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
