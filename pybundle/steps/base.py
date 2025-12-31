from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..context import BundleContext


@dataclass
class StepResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    seconds: int
    note: str = ""


class Step(Protocol):
    name: str

    def run(self, ctx: BundleContext) -> StepResult: ...
