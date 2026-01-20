from __future__ import annotations

from dataclasses import dataclass
import dataclasses
from .context import RunOptions
from .steps.shell import ShellStep
from .steps.tree import TreeStep, LargestFilesStep
from .steps.compileall import CompileAllStep
from .steps.ruff import RuffCheckStep, RuffFormatCheckStep
from .steps.mypy import MypyStep
from .steps.pylance import PylanceStep
from .steps.pytest import PytestStep
from .steps.bandit import BanditStep
from .steps.pip_audit import PipAuditStep
from .steps.coverage import CoverageStep
from .steps.rg_scans import default_rg_steps
from .steps.error_refs import ErrorReferencedFilesStep
from .steps.context_expand import ErrorContextExpandStep
from .steps.copy_pack import CuratedCopyStep
from .steps.repro_md import ReproMarkdownStep
from .steps.handoff_md import HandoffMarkdownStep
from .steps.roadmap import RoadmapStep

# Code quality tools (v1.3.0)
from .steps.vulture import VultureStep
from .steps.radon import RadonStep
from .steps.interrogate import InterrogateStep
from .steps.duplication import DuplicationStep

# Dependency analysis tools (v1.3.1)
from .steps.pipdeptree import PipdeptreeStep
from .steps.unused_deps import UnusedDependenciesStep
from .steps.license_scan import LicenseScanStep
from .steps.dependency_sizes import DependencySizesStep

# Performance profiling tools (v1.4.0)
from .steps.cprofile_step import CProfileStep
from .steps.import_time import ImportTimeStep
from .steps.memory_profile import MemoryProfileStep
from .steps.line_profiler import LineProfilerStep

# Test quality & coverage tools (v1.4.1)
from .steps.test_flakiness import TestFlakinessStep
from .steps.slow_tests import SlowTestsStep
from .steps.mutation_testing import MutationTestingStep

# Documentation & type quality tools (v1.5.0)
from .steps.type_coverage import TypeCoverageStep
from .steps.link_validation import LinkValidationStep
from .steps.api_docs import ApiDocsStep
from .steps.config_docs import ConfigDocumentationStep

# Git analytics tools (v1.5.1)
from .steps.git_analytics import GitAnalyticsStep

# Runtime analysis tools (v1.5.2)
from .steps.exception_patterns import ExceptionPatternsStep
from .steps.logging_analysis import LoggingAnalysisStep
from .steps.call_graph import CallGraphStep
from .steps.env_var_usage import EnvVarUsageStep

# Container & deployment tools (v2.0.0)
from .steps.dockerfile_lint import DockerfileLintStep
from .steps.dockerignore import DockerigoreStep
from .steps.container_image import ContainerImageStep

from .policy import AIContextPolicy


@dataclass(frozen=True)
class Profile:
    name: str
    steps: list


def _dedupe_steps(steps: list) -> list:
    seen = set()
    out = []
    for s in steps:
        key = (
            getattr(s, "out", None)
            or getattr(s, "out_md", None)
            or getattr(s, "name", None)
        )
        # fallback to class name if needed
        key = key or s.__class__.__name__
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def resolve_defaults(profile: str, opts: RunOptions) -> RunOptions:
    if profile == "ai":
        return dataclasses.replace(
            opts,
            no_ruff=opts.no_ruff if opts.no_ruff is not None else True,
            no_mypy=opts.no_mypy if opts.no_mypy is not None else True,
            no_pytest=opts.no_pytest if opts.no_pytest is not None else True,
            no_rg=opts.no_rg if opts.no_rg is not None else True,
            no_error_refs=opts.no_error_refs
            if opts.no_error_refs is not None
            else True,
            no_context=opts.no_context if opts.no_context is not None else True,
            no_compileall=opts.no_compileall
            if opts.no_compileall is not None
            else True,
        )
    return opts


def _analysis_steps(options: RunOptions) -> list:
    """
    Analysis profile: What the code IS
    - Structure, metrics, dependencies
    - Documentation and codebase understanding
    - No error detection or linting
    """
    policy = AIContextPolicy()

    steps: list = [
        # Environment & git status
        ShellStep(
            "git status", "meta/00_git_status.txt", ["git", "status"], require_cmd="git"
        ),
        ShellStep(
            "git diff", "meta/01_git_diff.txt", ["git", "diff"], require_cmd="git"
        ),
        ShellStep(
            "uname -a", "meta/21_uname.txt", ["uname", "-a"], require_cmd="uname"
        ),
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
        # Code structure
        TreeStep(max_depth=policy.tree_max_depth, policy=policy),
        LargestFilesStep(limit=policy.largest_limit, policy=policy),
    ]

    # Code quality metrics (what the code looks like)
    if not options.no_radon:
        steps += [RadonStep()]

    if not options.no_interrogate:
        steps += [InterrogateStep()]

    if not options.no_duplication:
        steps += [DuplicationStep()]

    # Dependency analysis (what the project uses)
    if not options.no_pipdeptree:
        steps += [PipdeptreeStep()]

    if not options.no_license_scan:
        steps += [LicenseScanStep()]

    if not options.no_dependency_sizes:
        steps += [DependencySizesStep()]

    # Performance profiling (what the code does)
    if not options.no_profile:
        steps += [CProfileStep()]
        steps += [ImportTimeStep()]

    if options.profile_memory:
        steps += [MemoryProfileStep()]

    if options.enable_line_profiler:
        steps += [LineProfilerStep()]

    # Documentation & type quality (what the code documents/types)
    if not options.no_type_coverage:
        steps += [TypeCoverageStep()]

    if not options.no_link_check:
        steps += [LinkValidationStep()]

    if not options.no_api_docs:
        steps += [ApiDocsStep()]

    if not options.no_config_docs:
        steps += [ConfigDocumentationStep()]

    # Git analytics (v1.5.1)
    if not options.no_git_analytics:
        steps += [GitAnalyticsStep()]

    # Runtime analysis (v1.5.2)
    if not options.no_runtime_analysis:
        steps += [
            ExceptionPatternsStep(),
            LoggingAnalysisStep(),
            CallGraphStep(),
            EnvVarUsageStep(),
        ]

    # Container & deployment (v2.0.0)
    if not options.no_container_analysis:
        steps += [
            DockerfileLintStep(),
            DockerigoreStep(),
            ContainerImageStep(),
        ]

    # Source snapshot and documentation
    steps += [
        CuratedCopyStep(policy=policy),
        RoadmapStep(policy=policy),
        HandoffMarkdownStep(),
    ]

    return _dedupe_steps(steps)


def _debug_steps(options: RunOptions) -> list:
    """
    Debug profile: What's WRONG with the code
    - Linting, type checking, testing
    - Security vulnerabilities
    - Code quality issues
    - Error detection and context
    """
    policy = AIContextPolicy()

    steps: list = [
        # Environment & git status
        ShellStep(
            "git status", "meta/00_git_status.txt", ["git", "status"], require_cmd="git"
        ),
        ShellStep(
            "git diff", "meta/01_git_diff.txt", ["git", "diff"], require_cmd="git"
        ),
        ShellStep(
            "uname -a", "meta/21_uname.txt", ["uname", "-a"], require_cmd="uname"
        ),
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
        ShellStep(
            "pip check",
            "logs/25_pip_check.txt",
            ["python", "-m", "pip", "check"],
            require_cmd="python",
        ),
        # Code structure (for context)
        TreeStep(max_depth=policy.tree_max_depth, policy=policy),
        LargestFilesStep(limit=policy.largest_limit, policy=policy),
    ]

    # Compilation errors
    if not options.no_compileall:
        steps.append(CompileAllStep())

    # Linting & type checking (what's wrong with code style/types)
    if not options.no_ruff:
        steps += [
            RuffCheckStep(target=options.ruff_target),
            RuffFormatCheckStep(target=options.ruff_target),
        ]

    if not options.no_mypy:
        steps += [MypyStep(target=options.mypy_target)]

    if not options.no_pylance:
        steps += [PylanceStep()]

    # Testing (what's broken in functionality)
    if not options.no_pytest:
        steps += [PytestStep(args=options.pytest_args or ["-q"])]

    if not options.no_coverage:
        steps += [CoverageStep()]

    # Test quality issues
    steps += [TestFlakinessStep()]  # Non-deterministic tests
    steps += [SlowTestsStep()]  # Performance issues in tests

    if options.enable_mutation_testing:
        steps += [MutationTestingStep()]  # Test effectiveness

    # Security vulnerabilities
    if not options.no_bandit:
        steps += [BanditStep()]

    if not options.no_pip_audit:
        steps += [PipAuditStep()]

    # Code quality issues (dead code, complexity)
    if not options.no_vulture:
        steps += [VultureStep()]

    if not options.no_radon:
        steps += [RadonStep()]

    # Dependency issues
    if not options.no_unused_deps:
        steps += [UnusedDependenciesStep()]

    if not options.no_pipdeptree:
        steps += [PipdeptreeStep()]  # For conflict detection

    # Pattern scanning (anti-patterns, TODOs)
    if not options.no_rg:
        steps += list(default_rg_steps(target="."))

    # Error context extraction
    if not options.no_error_refs:
        steps += [ErrorReferencedFilesStep(max_files=options.error_max_files)]

    if not options.no_context:
        steps += [
            ErrorContextExpandStep(
                depth=options.context_depth,
                max_files=options.context_max_files,
            )
        ]

    # Source snapshot + repro documentation
    steps += [
        CuratedCopyStep(policy=policy),
        ReproMarkdownStep(),
        HandoffMarkdownStep(),
    ]

    return _dedupe_steps(steps)


def get_profile(name: str, options: RunOptions) -> Profile:
    if name == "analysis":
        return Profile(name="analysis", steps=_analysis_steps(options))

    if name == "debug":
        return Profile(name="debug", steps=_debug_steps(options))

    if name == "backup":
        # Minimal backup: source + environment, no analysis
        policy = AIContextPolicy()
        return Profile(
            name="backup",
            steps=[
                ShellStep(
                    "git status",
                    "meta/00_git_status.txt",
                    ["git", "status"],
                    require_cmd="git",
                ),
                ShellStep(
                    "git diff",
                    "meta/01_git_diff.txt",
                    ["git", "diff"],
                    require_cmd="git",
                ),
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
                CuratedCopyStep(policy=policy),  # Copy source code
            ],
        )

    if name == "ai":
        # AI profile: debug optimized for AI consumption
        # Disables some noisy tools but keeps everything for problem understanding
        opts = resolve_defaults("ai", options)
        return Profile(name="ai", steps=_debug_steps(opts))

    raise ValueError(f"unknown profile: {name}")
