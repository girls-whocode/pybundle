from __future__ import annotations

from dataclasses import dataclass
import dataclasses
from .context import RunOptions
from .steps.shell import ShellStep
from .steps.tree import TreeStep, LargestFilesStep
from .steps.compileall import CompileAllStep
from .steps.ruff import RuffCheckStep, RuffFormatCheckStep
from .steps.mypy import MypyStep
from .steps.pytest import PytestStep
from .steps.rg_scans import default_rg_steps
from .steps.error_refs import ErrorReferencedFilesStep
from .steps.context_expand import ErrorContextExpandStep
from .steps.copy_pack import CuratedCopyStep
from .steps.repro_md import ReproMarkdownStep
from .steps.handoff_md import HandoffMarkdownStep


@dataclass(frozen=True)
class Profile:
    name: str
    steps: list

def resolve_defaults(profile: str, opts: RunOptions) -> RunOptions:
    if profile == "ai":
        return dataclasses.replace(
            opts,
            no_ruff = opts.no_ruff if opts.no_ruff is not None else True,
            no_mypy = opts.no_mypy if opts.no_mypy is not None else True,
            no_pytest = opts.no_pytest if opts.no_pytest is not None else True,
            no_rg = opts.no_rg if opts.no_rg is not None else True,
            no_error_refs = opts.no_error_refs if opts.no_error_refs is not None else True,
            no_context = opts.no_context if opts.no_context is not None else True,
            no_compileall = opts.no_compileall if opts.no_compileall is not None else True,
        )
    return opts

def _analysis_steps(options: RunOptions) -> list:
    steps: list = [
        ShellStep(
            "git status", "meta/00_git_status.txt", ["git", "status"], require_cmd="git"
        ),
        ShellStep(
            "git diff", "meta/01_git_diff.txt", ["git", "diff"], require_cmd="git"
        ),
        ShellStep(
            "uname -a", "meta/21_uname.txt", ["uname", "-a"], require_cmd="uname"
        ),
        TreeStep(max_depth=4),
        LargestFilesStep(limit=80),
    ]

    # Lint/type/test (CLI-overridable)
    if not options.no_ruff:
        steps += [
            RuffCheckStep(target=options.ruff_target),
            RuffFormatCheckStep(target=options.ruff_target),
        ]

    if not options.no_mypy:
        steps += [MypyStep(target=options.mypy_target)]

    if not options.no_pytest:
        steps += [PytestStep(args=options.pytest_args or ["-q"])]

    # Landmine scans
    if not options.no_rg:
        steps += list(default_rg_steps(target="."))

    # Error-driven packs
    if not options.no_error_refs:
        steps += [ErrorReferencedFilesStep(max_files=options.error_max_files)]

    if not options.no_context:
        steps += [
            ErrorContextExpandStep(
                depth=options.context_depth,
                max_files=options.context_max_files,
            )
        ]
    
    if not options.no_compileall:
        steps.append(CompileAllStep())

    # Curated pack + repro doc
    steps += [
        CuratedCopyStep(),
        ReproMarkdownStep(),
        HandoffMarkdownStep(),
        ShellStep(
            "python -V",
            "meta/20_python_version.txt",
            ["python", "-V"],
            require_cmd="python",
        ),
        ShellStep(
            "pip freeze",
            "meta/22_pip_freeze.txt",
            ["python", "-m", "pip", "freeze"],
            require_cmd="python",
        ),
    ]

    return steps

def get_profile(name: str, options: RunOptions) -> Profile:
    if name == "analysis":
        return Profile(name="analysis", steps=_analysis_steps(options))

    if name == "debug":
        # debug inherits analysis but keeps the same options
        steps = list(_analysis_steps(options))
        steps.append(
            ShellStep(
                "pip check",
                "logs/25_pip_check.txt",
                ["python", "-m", "pip", "check"],
                require_cmd="python",
            )
        )
        return Profile(name="debug", steps=steps)

    if name == "backup":
        # Scaffold: we'll implement real backup modes next
        return Profile(
            name="backup",
            steps=[
                ShellStep(
                    "python -V",
                    "meta/20_python_version.txt",
                    ["python", "-V"],
                    require_cmd="python",
                ),
            ],
        )

    if name == "ai":
        opts = resolve_defaults("ai", options)
        return Profile(name="ai", steps=_analysis_steps(opts))

    raise ValueError(f"unknown profile: {name}")
