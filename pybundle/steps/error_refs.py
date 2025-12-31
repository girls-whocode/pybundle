from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


DEFAULT_EXCLUDE_PREFIXES = (
    ".git/",
    ".venv/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    "__pycache__/",
    "node_modules/",
    "dist/",
    "build/",
    "artifacts/",
)

# Patterns based on your bash sed rules:
# 1) tool-style: path:line(:col)...
_RE_COLON_LINE = re.compile(r"^([A-Za-z0-9_.\/-]+\.[A-Za-z0-9]+):\d+(?::\d+)?\b.*$")

# 2) pytest traceback: File "path", line N
_RE_PYTEST_FILE = re.compile(r'^\s*File "([^"]+)", line \d+\b.*$')

# 3) mypy: (optional "mypy:") ./path:line: (error|note|warning):
_RE_MYPY_LINE = re.compile(
    r"^(?:mypy:\s*)?(?:\./)?([A-Za-z0-9_.\/-]+\.[A-Za-z0-9]+):\d+:\s*(?:error|note|warning):.*$"
)

# 4) mypy rare: path: (error|note|warning): ...
_RE_MYPY_NOLINE = re.compile(
    r"^(?:mypy:\s*)?(?:\./)?([A-Za-z0-9_.\/-]+\.[A-Za-z0-9]+):\s*(?:error|note|warning):.*$"
)


def _normalize_to_repo_rel(root: Path, p: str) -> str | None:
    p = p.strip()
    if not p:
        return None

    # remove leading ./ for consistency
    if p.startswith("./"):
        p = p[2:]

    # absolute path -> must be under repo root
    if p.startswith("/"):
        try:
            rp = Path(p).resolve()
            rr = rp.relative_to(root.resolve())
            return str(rr).replace("\\", "/")
        except Exception:
            return None

    # relative path
    return p.replace("\\", "/")


def _is_allowed_repo_file(root: Path, rel: str) -> bool:
    rel = rel.lstrip("./")
    if not rel or rel.endswith("/"):
        return False

    # exclude common junk
    for pref in DEFAULT_EXCLUDE_PREFIXES:
        if rel.startswith(pref):
            return False
    if "/__pycache__/" in f"/{rel}/":
        return False

    # must exist and be a file inside repo
    fp = (root / rel).resolve()
    try:
        fp.relative_to(root.resolve())
    except Exception:
        return False

    return fp.is_file()


def _extract_paths_from_text(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        m = _RE_COLON_LINE.match(line)
        if m:
            out.append(m.group(1))
            continue

        m = _RE_PYTEST_FILE.match(line)
        if m:
            out.append(m.group(1))
            continue

        m = _RE_MYPY_LINE.match(line)
        if m:
            out.append(m.group(1))
            continue

        m = _RE_MYPY_NOLINE.match(line)
        if m:
            out.append(m.group(1))
            continue

    return out


@dataclass
class ErrorReferencedFilesStep:
    name: str = "collect error-referenced files"
    max_files: int = 250
    # Paths are relative to the bundle workdir
    log_files: list[str] | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()

        # Default set aligned to our step numbers
        log_files = self.log_files or [
            "logs/31_ruff_check.txt",
            "logs/32_ruff_format_check.txt",
            "logs/33_mypy.txt",
            "logs/34_pytest_q.txt",
        ]

        out_list = ctx.workdir / "error_files_from_logs.txt"
        out_count = ctx.workdir / "error_refs_count.txt"
        report = ctx.metadir / "60_error_refs_report.txt"

        dest_root = ctx.srcdir / "_error_refs"
        dest_root.mkdir(parents=True, exist_ok=True)

        # Collect candidate paths
        candidates: set[str] = set()
        scanned = 0
        missing_logs = 0

        for lf in log_files:
            lp = ctx.workdir / lf
            if not lp.is_file():
                missing_logs += 1
                continue
            scanned += 1
            try:
                txt = lp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for raw in _extract_paths_from_text(txt):
                norm = _normalize_to_repo_rel(ctx.root, raw)
                if norm:
                    candidates.add(norm)

        # Normalize / filter to real repo files
        allowed = sorted([p for p in candidates if _is_allowed_repo_file(ctx.root, p)])

        # Write list file (even if empty)
        out_list.write_text("\n".join(allowed) + ("\n" if allowed else ""), encoding="utf-8")

        # Copy up to max_files
        copied = 0
        for rel in allowed:
            if copied >= self.max_files:
                break
            src = ctx.root / rel
            dst = dest_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                # preserve mode/timestamps
                dst.write_bytes(src.read_bytes())
                copied += 1
            except Exception:
                continue

        out_count.write_text(f"{copied}\n", encoding="utf-8")

        report.write_text(
            "\n".join(
                [
                    f"scanned_logs={scanned}",
                    f"missing_logs={missing_logs}",
                    f"candidates_total={len(candidates)}",
                    f"allowed_repo_files={len(allowed)}",
                    f"copied={copied}",
                    f"max_files={self.max_files}",
                    f"dest=src/_error_refs",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        dur = int(time.time() - start)
        note = f"allowed={len(allowed)} copied={copied}"
        if copied >= self.max_files:
            note += " (HIT MAX)"
        return StepResult(self.name, "PASS", dur, note)
