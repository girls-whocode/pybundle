from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TYPE_CHECKING

from .tools import which

if TYPE_CHECKING:
    from .steps.base import StepResult
    from .profiles import Profile


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

    # code quality tools (v1.3.0)
    vulture: str | None
    radon: str | None
    interrogate: str | None
    pylint: str | None

    # dependency analysis tools (v1.3.1)
    pipdeptree: str | None
    pip_licenses: str | None

    # performance profiling tools (v1.4.0)
    line_profiler: str | None

    # documentation & type quality tools (v1.5.0)
    pdoc: str | None
    markdown_link_check: str | None

    @staticmethod
    def detect(strict_paths: bool = False) -> "Tooling":
        """Detect available tools, optionally enforcing trusted paths.

        Args:
            strict_paths: If True, only accept tools in trusted system directories
        """
        return Tooling(
            git=which("git", strict=strict_paths),
            python=which("python", strict=strict_paths)
            or which("python3", strict=strict_paths),
            pip=which("pip", strict=strict_paths) or which("pip3", strict=strict_paths),
            zip=which("zip", strict=strict_paths),
            tar=which("tar", strict=strict_paths),
            uname=which("uname", strict=strict_paths),
            ruff=which("ruff", strict=strict_paths),
            mypy=which("mypy", strict=strict_paths),
            pytest=which("pytest", strict=strict_paths),
            rg=which("rg", strict=strict_paths),
            tree=which("tree", strict=strict_paths),
            npm=which("npm", strict=strict_paths),
            vulture=which("vulture", strict=strict_paths),
            radon=which("radon", strict=strict_paths),
            interrogate=which("interrogate", strict=strict_paths),
            pylint=which("pylint", strict=strict_paths),
            pipdeptree=which("pipdeptree", strict=strict_paths),
            pip_licenses=which("pip-licenses", strict=strict_paths),
            line_profiler=which("kernprof", strict=strict_paths),
            pdoc=which("pdoc", strict=strict_paths),
            markdown_link_check=which("markdown-link-check", strict=strict_paths),
        )


@dataclass(frozen=True)
class RunOptions:
    no_ruff: bool | None = None
    no_mypy: bool | None = None
    no_pylance: bool | None = None
    no_pytest: bool | None = None
    no_bandit: bool | None = None
    no_pip_audit: bool | None = None
    no_coverage: bool | None = None
    no_rg: bool | None = None
    no_error_refs: bool | None = None
    no_context: bool | None = None
    no_compileall: bool | None = None

    # code quality tools (v1.3.0)
    no_vulture: bool | None = None
    no_radon: bool | None = None
    no_interrogate: bool | None = None
    no_duplication: bool | None = None

    # dependency analysis tools (v1.3.1)
    no_pipdeptree: bool | None = None
    no_unused_deps: bool | None = None
    no_license_scan: bool | None = None
    no_dependency_sizes: bool | None = None

    # performance profiling (v1.4.0)
    no_profile: bool | None = None
    profile_entry_point: str | None = None
    profile_memory: bool = True  # v1.4.2: enabled by default
    enable_line_profiler: bool = False  # requires @profile decorators

    # test quality & coverage (v1.4.1)
    test_flakiness_runs: int = 3
    slow_test_threshold: float = 1.0
    enable_mutation_testing: bool = False

    # documentation & type quality (v1.5.0)
    no_type_coverage: bool | None = None
    no_link_check: bool | None = None
    no_api_docs: bool | None = None
    no_config_docs: bool | None = None

    # git analytics (v1.5.1)
    no_git_analytics: bool | None = None
    git_blame_depth: int = 100

    # runtime analysis (v1.5.2)
    no_runtime_analysis: bool | None = None

    # container & deployment (v2.0.0)
    no_container_analysis: bool | None = None
    docker_image: str | None = None

    # configuration & security (v2.0.0)
    no_config_security_analysis: bool | None = None

    # async & modern python (v2.0.0)
    no_async_analysis: bool | None = None

    strict_paths: bool = False  # Enforce trusted path validation

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
    keep_workdir: bool
    tools: Tooling
    results: list["StepResult"] = field(default_factory=list)
    command_used: str = ""
    json_mode: bool = False
    archive_path: Path | None = None
    duration_ms: int | None = None

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
        keep_workdir: bool,
        json_mode: bool = False,
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

        options = options or RunOptions()
        tools = Tooling.detect(strict_paths=options.strict_paths)
        prefix = name_prefix or f"pybundle_{profile_name}_{ts}"

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
            keep_workdir=keep_workdir,
            tools=tools,
            json_mode=json_mode,
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

    def print_doctor(self, profile: "Profile") -> None:
        from .doctor import plan_for_profile, print_tool_info

        print(f"Root: {self.root}")
        print(f"Out:  {self.outdir}\n")

        # Enhanced tool information with security validation
        print_tool_info(self)
        print()

        # Options (super useful)
        print("Options:")
        o = self.options
        print(f"  strict_paths:      {o.strict_paths}")
        print(f"  ruff_target:       {o.ruff_target}")
        print(f"  mypy_target:       {o.mypy_target}")
        print(f"  pytest_args:       {' '.join(o.pytest_args)}")
        print(f"  no_ruff:           {o.no_ruff}")
        print(f"  no_mypy:           {o.no_mypy}")
        print(f"  no_pylance:        {o.no_pylance}")
        print(f"  no_pytest:         {o.no_pytest}")
        print(f"  no_bandit:         {o.no_bandit}")
        print(f"  no_pip_audit:      {o.no_pip_audit}")
        print(f"  no_coverage:       {o.no_coverage}")
        print(f"  no_rg:             {o.no_rg}")
        print(f"  no_error_refs:     {o.no_error_refs}")
        print(f"  no_context:        {o.no_context}")
        print(f"  error_max_files:   {o.error_max_files}")
        print(f"  context_depth:     {o.context_depth}")
        print(f"  context_max_files: {o.context_max_files}")
        print()

        # Plan
        plan = plan_for_profile(self, profile)

        print(f"Plan ({profile.name}):")
        for item in plan:
            out = f" -> {item.out_rel}" if item.out_rel else ""
            if item.status == "RUN":
                print(f"  RUN  {item.name:<28}{out}")
            else:
                why = f" ({item.reason})" if item.reason else ""
                print(f"  SKIP {item.name:<28}{out}{why}")

    def doctor_report(self, profile: "Profile") -> dict:
        from .doctor import plan_for_profile

        plan = plan_for_profile(self, profile)

        tools = {}
        for k, v in asdict(self.tools).items():
            tools[k] = {"present": v is not None, "path": v}

        o = self.options
        return {
            "status": "ok",
            "command": "doctor",
            "profile": profile.name,
            "root": str(self.root),
            "outdir": str(self.outdir),
            "tools": tools,
            "options": {
                "ruff_target": o.ruff_target,
                "mypy_target": o.mypy_target,
                "pytest_args": list(o.pytest_args),
                "no_ruff": o.no_ruff,
                "no_mypy": o.no_mypy,
                "no_pylance": o.no_pylance,
                "no_pytest": o.no_pytest,
                "no_bandit": o.no_bandit,
                "no_pip_audit": o.no_pip_audit,
                "no_coverage": o.no_coverage,
                "no_rg": o.no_rg,
                "no_error_refs": o.no_error_refs,
                "no_context": o.no_context,
                "no_vulture": o.no_vulture,
                "no_radon": o.no_radon,
                "no_interrogate": o.no_interrogate,
                "no_duplication": o.no_duplication,
                "no_pipdeptree": o.no_pipdeptree,
                "no_unused_deps": o.no_unused_deps,
                "no_license_scan": o.no_license_scan,
                "no_dependency_sizes": o.no_dependency_sizes,
                "no_profile": o.no_profile,
                "profile_entry_point": o.profile_entry_point,
                "profile_memory": o.profile_memory,
                "enable_line_profiler": o.enable_line_profiler,
                "test_flakiness_runs": o.test_flakiness_runs,
                "slow_test_threshold": o.slow_test_threshold,
                "enable_mutation_testing": o.enable_mutation_testing,
                "error_max_files": o.error_max_files,
                "context_depth": o.context_depth,
                "context_max_files": o.context_max_files,
            },
            "plan": [
                {
                    "name": item.name,
                    "status": item.status,  # "RUN" or "SKIP"
                    "out_rel": item.out_rel,
                    "reason": item.reason,
                }
                for item in plan
            ],
        }

    def emit(self, msg: str) -> None:
        """Human output only."""
        if not self.json_mode:
            print(msg)

    def emit_json(self, payload: dict) -> None:
        """JSON output only (stdout contract)."""
        print(json.dumps(payload, ensure_ascii=False))
