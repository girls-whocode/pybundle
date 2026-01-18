from __future__ import annotations

import subprocess  # nosec B404 - Required for archive creation, paths validated
from pathlib import Path

from .context import BundleContext


def resolve_archive_format(ctx: BundleContext) -> str:
    fmt_used = ctx.archive_format
    if fmt_used == "auto":
        fmt_used = "zip" if ctx.tools.zip else "tar.gz"
    return fmt_used


def archive_output_path(ctx: BundleContext, fmt_used: str) -> Path:
    if fmt_used == "zip":
        return ctx.outdir / f"{ctx.name_prefix}.zip"
    return ctx.outdir / f"{ctx.name_prefix}.tar.gz"


def make_archive(ctx: BundleContext) -> tuple[Path, str]:
    fmt_used = resolve_archive_format(ctx)

    if fmt_used == "zip":
        if not ctx.tools.zip:
            raise RuntimeError("zip tool not available")
        out = archive_output_path(ctx, fmt_used)
        # zip wants working dir above target folder
        subprocess.run(  # nosec B603
            [ctx.tools.zip, "-qr", str(out), ctx.workdir.name],
            cwd=str(ctx.workdir.parent),
            check=False,
        )
        return out, fmt_used

    if not ctx.tools.tar:
        raise RuntimeError("tar tool not available")
    out = archive_output_path(ctx, fmt_used)
    subprocess.run(  # nosec B603
        [ctx.tools.tar, "-czf", str(out), ctx.workdir.name],
        cwd=str(ctx.workdir.parent),
        check=False,
    )
    return out, fmt_used
