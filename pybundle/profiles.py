from __future__ import annotations

from dataclasses import dataclass

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
        CompileAllStep(),
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

    raise ValueError(f"unknown profile: {name}")
