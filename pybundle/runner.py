from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from .context import BundleContext
from .packaging import make_archive


def run_profile(ctx: BundleContext, profile) -> int:
    ctx.write_runlog(f"=== pybundle run {profile.name} ===")
    ctx.write_runlog(f"ROOT: {ctx.root}")
    ctx.write_runlog(f"WORK: {ctx.workdir}")

    results = []
    ctx.results = results
    any_fail = False

    for step in profile.steps:
        ctx.write_runlog(f"-- START: {step.name}")
        r = step.run(ctx)
        results.append(r)
        ctx.results = results
        ctx.write_runlog(f"-- DONE:  {step.name} [{r.status}] ({r.seconds}s) {r.note}".rstrip())
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
    archive_path = make_archive(ctx)
    ctx.write_runlog(f"ARCHIVE: {archive_path}")

    print(f"✅ Archive created: {archive_path}")
    if ctx.keep_workdir:
        print(f"📁 Workdir kept:     {ctx.workdir}")

    if not ctx.keep_workdir:
        shutil.rmtree(ctx.workdir, ignore_errors=True)

    if any_fail and ctx.strict:
        return 10
    return 0
