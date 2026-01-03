from __future__ import annotations

import argparse
from pathlib import Path
import shlex

from .context import BundleContext, RunOptions
from .profiles import get_profile
from .root_detect import detect_project_root
from importlib.metadata import PackageNotFoundError, version as pkg_version
from .runner import run_profile


def get_version() -> str:
    # 1) Canonical for installed distributions (including editable)
    try:
        return pkg_version("gwc-pybundle")
    except PackageNotFoundError:
        pass

    # 2) Dev fallback: locate pyproject.toml by walking up from this file
    try:
        import tomllib  # py3.11+
    except Exception:
        return "unknown"

    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        pp = parent / "pyproject.toml"
        if pp.is_file():
            try:
                data = tomllib.loads(pp.read_text(encoding="utf-8"))
                return data.get("project", {}).get("version", "unknown")
            except Exception:
                return "unknown"

    return "unknown"


def add_common_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Explicit project root (skip auto-detect)",
    )
    sp.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Output directory (default: <root>/artifacts)",
    )
    sp.add_argument("--name", default=None, help="Override archive name prefix")
    sp.add_argument(
        "--strict", action="store_true", help="Fail non-zero if any step fails"
    )
    sp.add_argument(
        "--no-spinner", action="store_true", help="Disable spinner output (CI-friendly)"
    )
    sp.add_argument(
        "--redact",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Redact secrets in logs/text",
    )
    sp.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON to stdout.",
    )


def _resolve_profile_defaults(profile: str, o: RunOptions) -> RunOptions:
    if profile == "ai":
        # AI defaults: skip slow/flake-prone tools unless explicitly enabled
        return RunOptions(
            **{
                **o.__dict__,
                "no_ruff": o.no_ruff if o.no_ruff is not None else True,
                "no_mypy": o.no_mypy if o.no_mypy is not None else True,
                "no_pytest": o.no_pytest if o.no_pytest is not None else True,
                "no_rg": o.no_rg if o.no_rg is not None else True,
                "no_error_refs": o.no_error_refs
                if o.no_error_refs is not None
                else True,
                "no_context": o.no_context if o.no_context is not None else True,
            }
        )
    return o


def add_run_only_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument(
        "--format",
        choices=["auto", "zip", "tar.gz"],
        default="auto",
        help="Archive format",
    )
    sp.add_argument(
        "--clean-workdir",
        action="store_true",
        help="Delete expanded workdir after packaging",
    )


def add_knobs(sp: argparse.ArgumentParser) -> None:
    # selective skips
    sp.add_argument("--ruff", dest="no_ruff", action="store_false", default=None)
    sp.add_argument("--no-ruff", dest="no_ruff", action="store_true", default=None)
    sp.add_argument("--mypy", dest="no_mypy", action="store_false", default=None)
    sp.add_argument("--no-mypy", dest="no_mypy", action="store_true", default=None)
    sp.add_argument("--pytest", dest="no_pytest", action="store_false", default=None)
    sp.add_argument("--no-pytest", dest="no_pytest", action="store_true", default=None)
    sp.add_argument("--rg", dest="no_rg", action="store_false", default=None)
    sp.add_argument("--no-rg", dest="no_rg", action="store_true", default=None)
    sp.add_argument(
        "--error-refs", dest="no_error_refs", action="store_false", default=None
    )
    sp.add_argument(
        "--no-error-refs", dest="no_error_refs", action="store_true", default=None
    )
    sp.add_argument("--context", dest="no_context", action="store_false", default=None)
    sp.add_argument(
        "--no-context", dest="no_context", action="store_true", default=None
    )

    # targets / args
    sp.add_argument("--ruff-target", default=".")
    sp.add_argument("--mypy-target", default=".")
    sp.add_argument(
        "--pytest-args",
        default="-q",
        help='Pytest args as a single string, e.g. "--maxfail=1 -q"',
    )

    # caps
    sp.add_argument("--error-max-files", type=int, default=250)
    sp.add_argument("--context-depth", type=int, default=2)
    sp.add_argument("--context-max-files", type=int, default=600)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pybundle", description="Build portable diagnostic bundles for projects."
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="Show version")
    sub.add_parser("list-profiles", help="List available profiles")

    runp = sub.add_parser("run", help="Run a profile and build an archive")
    runp.add_argument("profile", choices=["analysis", "debug", "backup", "ai"])
    add_common_args(runp)
    add_run_only_args(runp)
    add_knobs(runp)

    docp = sub.add_parser("doctor", help="Show tool availability and what would run")
    docp.add_argument(
        "profile",
        choices=["analysis", "debug", "backup", "ai"],
        nargs="?",
        default="analysis",
    )
    add_common_args(docp)
    add_knobs(docp)

    return p


def _build_options(args) -> RunOptions:
    pytest_args = (
        shlex.split(args.pytest_args) if getattr(args, "pytest_args", None) else ["-q"]
    )
    return RunOptions(
        no_ruff=getattr(args, "no_ruff", None),
        no_mypy=getattr(args, "no_mypy", None),
        no_pytest=getattr(args, "no_pytest", None),
        no_rg=getattr(args, "no_rg", None),
        no_error_refs=getattr(args, "no_error_refs", None),
        no_context=getattr(args, "no_context", None),
        ruff_target=getattr(args, "ruff_target", "."),
        mypy_target=getattr(args, "mypy_target", "."),
        pytest_args=pytest_args,
        error_max_files=getattr(args, "error_max_files", 250),
        context_depth=getattr(args, "context_depth", 2),
        context_max_files=getattr(args, "context_max_files", 600),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "version":
        print(f"pybundle {get_version()}")
        return 0

    if args.cmd == "list-profiles":
        print("ai        - AI-friendly context bundle (fast, low-flake defaults)")
        print("backup    - portable snapshot (scaffold)")
        print("analysis  - neutral diagnostic bundle (humans, tools, assistants)")
        print("debug     - deeper diagnostics for developers")
        return 0

    # run + doctor need a root
    root = args.project_root or detect_project_root(Path.cwd())
    if root is None:
        print("❌ Could not detect project root. Use --project-root PATH.")
        return 20

    outdir = args.outdir or (root / "artifacts")

    options = _resolve_profile_defaults(args.profile, _build_options(args))
    profile = get_profile(args.profile, options)

    if args.cmd == "doctor":
        ctx = BundleContext.create(
            root=root,
            outdir=outdir,
            profile_name=args.profile,
            archive_format="auto",
            name_prefix=args.name,
            strict=args.strict,
            redact=args.redact,
            json_mode=args.json,
            spinner=not args.no_spinner,
            keep_workdir=True,
            options=options,
        )

        if args.json:
            ctx.emit_json(ctx.doctor_report(profile))
        else:
            ctx.print_doctor(profile)
        return 0

    # cmd == run
    keep_workdir = not args.clean_workdir

    ctx = BundleContext.create(
        root=root,
        outdir=outdir,
        profile_name=args.profile,
        archive_format=args.format,
        name_prefix=args.name,
        strict=args.strict,
        redact=args.redact,
        json_mode=args.json,  # <-- add this
        spinner=not args.no_spinner,
        keep_workdir=keep_workdir,
        options=options,
    )

    rc = run_profile(ctx, profile)

    if args.json:
        copied = None
        excluded = None

        mf = ctx.metadir / "50_copy_manifest.txt"
        if mf.exists():
            data: dict[str, str] = {}
            for line in mf.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()

            copied = int(data.get("copied_files", "0"))
            excluded = int(data.get("excluded_files", "0"))

        payload = {
            "status": "ok" if rc == 0 else "fail",
            "command": "run",
            "profile": profile.name,
            "files_included": copied if copied is not None else 0,
            "files_excluded": excluded if excluded is not None else 0,
            "duration_ms": ctx.duration_ms or 0,
            "bundle_path": str(ctx.archive_path) if ctx.archive_path else None,
        }
        ctx.emit_json(payload)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
