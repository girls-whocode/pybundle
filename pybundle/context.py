from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TYPE_CHECKING

from .tools import which

if TYPE_CHECKING:
    from .steps.base import StepResult


def fmt_tool(path: str | None) -> str:
    if path:
        return path
    return "\x1b[31m<missing>\x1b[0m"


@dataclass(frozen=True)
class Tooling:
    git: str | None
    python: str | None
    pip: str | None
    zip: str | None
    tar: str | None
    uname: str | None

    # analysis/debug tools
    ruff: str | None
    mypy: str | None
    pytest: str | None
    rg: str | None
    tree: str | None
    npm: str | None

    @staticmethod
    def detect() -> "Tooling":
        return Tooling(
            git=which("git"),
            python=which("python") or which("python3"),
            pip=which("pip") or which("pip3"),
            zip=which("zip"),
            tar=which("tar"),
            uname=which("uname"),
            ruff=which("ruff"),
            mypy=which("mypy"),
            pytest=which("pytest"),
            rg=which("rg"),
            tree=which("tree"),
            npm=which("npm"),
        )


@dataclass(frozen=True)
class RunOptions:
    no_ruff: bool = False
    no_mypy: bool = False
    no_pytest: bool = False
    no_rg: bool = False
    no_error_refs: bool = False
    no_context: bool = False

    ruff_target: str = "."
    mypy_target: str = "."
    pytest_args: list[str] = field(default_factory=lambda: ["-q"])

    error_max_files: int = 250
    context_depth: int = 2
    context_max_files: int = 600


@dataclass
class BundleContext:
    root: Path
    options: RunOptions
    outdir: Path
    profile_name: str
    ts: str
    workdir: Path
    srcdir: Path
    logdir: Path
    metadir: Path
    runlog: Path
    summary_json: Path
    manifest_json: Path
    archive_format: str
    name_prefix: str
    strict: bool
    redact: bool
    spinner: bool
    keep_workdir: bool
    tools: Tooling
    results: list["StepResult"] = field(default_factory=list)

    def have(self, cmd: str) -> bool:
        return getattr(self.tools, cmd, None) is not None

    @staticmethod
    def utc_ts() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    @classmethod
    def create(
        cls,
        *,
        root: Path,
        options: RunOptions | None = None,
        outdir: Path,
        profile_name: str,
        archive_format: str,
        name_prefix: str | None,
        strict: bool,
        redact: bool,
        spinner: bool,
        keep_workdir: bool,
    ) -> "BundleContext":
        ts = cls.utc_ts()
        outdir.mkdir(parents=True, exist_ok=True)

        workdir = outdir / f"pybundle_{profile_name}_{ts}"
        srcdir = workdir / "src"
        logdir = workdir / "logs"
        metadir = workdir / "meta"

        srcdir.mkdir(parents=True, exist_ok=True)
        logdir.mkdir(parents=True, exist_ok=True)
        metadir.mkdir(parents=True, exist_ok=True)

        runlog = workdir / "RUN_LOG.txt"
        summary_json = workdir / "SUMMARY.json"
        manifest_json = workdir / "MANIFEST.json"

        tools = Tooling.detect()
        prefix = name_prefix or f"pybundle_{profile_name}_{ts}"

        options = options or RunOptions()

        return cls(
            root=root,
            options=options,
            outdir=outdir,
            profile_name=profile_name,
            ts=ts,
            workdir=workdir,
            srcdir=srcdir,
            logdir=logdir,
            metadir=metadir,
            runlog=runlog,
            summary_json=summary_json,
            manifest_json=manifest_json,
            archive_format=archive_format,
            name_prefix=prefix,
            strict=strict,
            redact=redact,
            spinner=spinner,
            keep_workdir=keep_workdir,
            tools=tools,
        )

    def rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.root))
        except Exception:
            return str(p)

    def redact_text(self, text: str) -> str:
        if not self.redact:
            return text
        # Minimal default redaction rules (you can expand with a rules file later)
        rules: Iterable[tuple[str, str]] = [
            (
                r"(?i)(api[_-]?key)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{10,})",
                r"\1=<REDACTED>",
            ),
            (r"(?i)(token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{10,})", r"\1=<REDACTED>"),
            (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\s]+)", r"\1=<REDACTED>"),
            (r"(?i)(dsn)\s*[:=]\s*['\"]?([^'\"\s]+)", r"\1=<REDACTED>"),
        ]
        out = text
        for pat, repl in rules:
            out = re.sub(pat, repl, out)
        return out

    def write_runlog(self, line: str) -> None:
        self.runlog.parent.mkdir(parents=True, exist_ok=True)
        with self.runlog.open("a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")

    def print_doctor(self, profile) -> None:
        print(f"Root: {self.root}")
        print(f"Out:  {self.outdir}\n")

        # Tools (keep your existing output)
        print("Tools:")
        for k, v in asdict(self.tools).items():
            print(f"{k:>8}: {fmt_tool(v)}")
        print()

        # Options (super useful)
        print("Options:")
        o = self.options
        print(f"  ruff_target:       {o.ruff_target}")
        print(f"  mypy_target:       {o.mypy_target}")
        print(f"  pytest_args:       {' '.join(o.pytest_args)}")
        print(f"  no_ruff:           {o.no_ruff}")
        print(f"  no_mypy:           {o.no_mypy}")
        print(f"  no_pytest:         {o.no_pytest}")
        print(f"  no_rg:             {o.no_rg}")
        print(f"  no_error_refs:     {o.no_error_refs}")
        print(f"  no_context:        {o.no_context}")
        print(f"  error_max_files:   {o.error_max_files}")
        print(f"  context_depth:     {o.context_depth}")
        print(f"  context_max_files: {o.context_max_files}")
        print()

        # Plan
        from .doctor import plan_for_profile  # local import avoids circulars

        plan = plan_for_profile(self, profile)

        print(f"Plan ({profile.name}):")
        for item in plan:
            out = f" -> {item.out_rel}" if item.out_rel else ""
            if item.status == "RUN":
                print(f"  RUN  {item.name:<28}{out}")
            else:
                why = f" ({item.reason})" if item.reason else ""
                print(f"  SKIP {item.name:<28}{out}{why}")
