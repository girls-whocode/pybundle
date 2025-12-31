from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from .steps.shell import ShellStep
from .steps.ruff import RuffCheckStep, RuffFormatCheckStep
from .steps.mypy import MypyStep
from .steps.pytest import PytestStep
from .steps.rg_scans import RipgrepScanStep

T = TypeVar("T")


@dataclass(frozen=True)
class PlanItem:
    name: str
    status: str  # "RUN" | "SKIP"
    out_rel: str | None
    reason: str


EvalFn = Callable[[Any, T], PlanItem]


def _out(step: Any) -> str | None:
    return (
        getattr(step, "out_rel", None)
        or getattr(step, "outfile_rel", None)
        or getattr(step, "outfile", None)
    )


def eval_shell(ctx: Any, step: ShellStep) -> PlanItem:
    if step.require_cmd and not ctx.have(step.require_cmd):
        return PlanItem(
            step.name, "SKIP", _out(step), f"missing tool: {step.require_cmd}"
        )
    return PlanItem(step.name, "RUN", _out(step), "")


def eval_ruff(ctx: Any, step: Any) -> PlanItem:
    if ctx.options.no_ruff:
        return PlanItem(step.name, "SKIP", _out(step), "disabled by --no-ruff")
    if not ctx.have("ruff"):
        return PlanItem(step.name, "SKIP", _out(step), "missing tool: ruff")
    return PlanItem(step.name, "RUN", _out(step), "")


def eval_mypy(ctx: Any, step: MypyStep) -> PlanItem:
    if ctx.options.no_mypy:
        return PlanItem(step.name, "SKIP", _out(step), "disabled by --no-mypy")
    if not ctx.have("mypy"):
        return PlanItem(step.name, "SKIP", _out(step), "missing tool: mypy")
    return PlanItem(step.name, "RUN", _out(step), "")


def eval_pytest(ctx: Any, step: PytestStep) -> PlanItem:
    if ctx.options.no_pytest:
        return PlanItem(step.name, "SKIP", _out(step), "disabled by --no-pytest")
    if not ctx.have("pytest"):
        return PlanItem(step.name, "SKIP", _out(step), "missing tool: pytest")
    if (
        not (ctx.root / "tests").exists()
        and not (ctx.root / "sentra" / "tests").exists()
    ):
        return PlanItem(step.name, "SKIP", _out(step), "no tests/ directory found")
    return PlanItem(step.name, "RUN", _out(step), "")


def eval_rg(ctx: Any, step: Any) -> PlanItem:
    if ctx.options.no_rg:
        return PlanItem(step.name, "SKIP", _out(step), "disabled by --no-rg")
    if not ctx.have("rg"):
        return PlanItem(step.name, "SKIP", _out(step), "missing tool: rg")
    return PlanItem(step.name, "RUN", _out(step), "")


REGISTRY: list[tuple[type[Any], Callable[[Any, Any], PlanItem]]] = [
    (ShellStep, eval_shell),
    (RuffCheckStep, eval_ruff),
    (RuffFormatCheckStep, eval_ruff),
    (MypyStep, eval_mypy),
    (PytestStep, eval_pytest),
    (RipgrepScanStep, eval_rg),
]


def plan_for_profile(ctx: Any, profile: Any) -> list[PlanItem]:
    items: list[PlanItem] = []
    for step in profile.steps:
        item: PlanItem | None = None

        for cls, fn in REGISTRY:
            if isinstance(step, cls):
                item = fn(ctx, step)
                break
        if item is None:
            item = PlanItem(step.name, "RUN", _out(step), "")
        items.append(item)
    return items
