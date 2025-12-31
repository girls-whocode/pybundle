from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .context import BundleContext


def _git_commit_hash(root: Path, git_path: str | None) -> str | None:
    """Return HEAD commit hash if root is inside a git repo, else None."""
    if not git_path:
        return None
    try:
        # If this fails, we're not in a repo or git isn't functional.
        p = subprocess.run(
            [git_path, "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        return p.stdout.strip() or None
    except Exception:
        return None


def write_manifest(
    *,
    ctx: BundleContext,
    profile_name: str,
    archive_path: Path,
    archive_format_used: str,
) -> None:
    """Write a stable, machine-readable manifest for automation."""
    git_hash = _git_commit_hash(ctx.root, ctx.tools.git)

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "tool": {"name": "pybundle"},
        "timestamp_utc": ctx.ts,
        "profile": profile_name,
        "paths": {
            "root": str(ctx.root),
            "workdir": str(ctx.workdir),
            "srcdir": str(ctx.srcdir),
            "logdir": str(ctx.logdir),
            "metadir": str(ctx.metadir),
        },
        "outputs": {
            "archive": {
                "path": str(archive_path),
                "name": archive_path.name,
                "format": archive_format_used,
            },
            "summary_json": str(ctx.summary_json),
            "manifest_json": str(ctx.manifest_json),
            "runlog": str(ctx.runlog),
        },
        "options": asdict(ctx.options),
        "run": {
            "strict": ctx.strict,
            "redact": ctx.redact,
            "spinner": ctx.spinner,
            "keep_workdir": ctx.keep_workdir,
            "archive_format_requested": ctx.archive_format,
            "name_prefix": ctx.name_prefix,
        },
        "tools": asdict(ctx.tools),
        "git": {"commit": git_hash},
    }

    ctx.manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
