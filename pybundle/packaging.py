from __future__ import annotations

import subprocess
from pathlib import Path

from .context import BundleContext


def make_archive(ctx: BundleContext) -> Path:
    fmt = ctx.archive_format
    if fmt == "auto":
        fmt = "zip" if ctx.tools.zip else "tar.gz"

    if fmt == "zip":
        out = ctx.outdir / f"{ctx.name_prefix}.zip"
        # zip wants working dir above target folder
        subprocess.run(
            ["zip", "-qr", str(out), ctx.workdir.name],
            cwd=str(ctx.workdir.parent),
            check=False,
        )
        return out

    out = ctx.outdir / f"{ctx.name_prefix}.tar.gz"
    subprocess.run(
        ["tar", "-czf", str(out), ctx.workdir.name],
        cwd=str(ctx.workdir.parent),
        check=False,
    )
    return out
