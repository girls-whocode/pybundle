from __future__ import annotations
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..roadmap_scan import build_roadmap
from ..steps.copy_pack import DEFAULT_EXCLUDE_DIRS  # reuse your excludes

@dataclass
class RoadmapStep:
    name: str = "roadmap (project map)"
    out_md: str = "meta/70_roadmap.md"
    out_json: str = "meta/70_roadmap.json"
    include: list[str] = None
    max_files: int = 20000

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()

        include_dirs = []
        if self.include:
            include_dirs = [ctx.root / p for p in self.include]
        else:
            # sane defaults: mimic your curated source approach
            include_dirs = [ctx.root / "src", ctx.root]

        graph = build_roadmap(
            root=ctx.root,
            include_dirs=include_dirs,
            exclude_dirs=set(DEFAULT_EXCLUDE_DIRS),
            max_files=self.max_files,
        )

        # Write JSON
        out_json_path = ctx.workdir / self.out_json
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")

        # Write Markdown (with Mermaid)
        out_md_path = ctx.workdir / self.out_md
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        out_md_path.write_text(self._render_md(graph), encoding="utf-8")

        dur = int(time.time() - start)
        note = f"nodes={len(graph.nodes)} edges={len(graph.edges)} entrypoints={len(graph.entrypoints)}"
        return StepResult(self.name, "PASS", dur, note)

    def _render_md(self, graph) -> str:
        lines = []
        lines.append("# Project Roadmap")
        lines.append("")
        lines.append("## Entrypoints")
        if not graph.entrypoints:
            lines.append("- (none detected)")
        else:
            for ep in graph.entrypoints[:50]:
                lines.append(f"- `{ep.node}` — {ep.reason} (confidence {ep.confidence}/3)")
        lines.append("")
        lines.append("## High-level map")
        lines.append("```mermaid")
        lines.append("flowchart LR")

        # Keep graph readable: only show edges from entrypoints + top N by frequency
        ep_nodes = {ep.node for ep in graph.entrypoints}
        shown = 0
        for e in graph.edges:
            if e.src in ep_nodes:
                lines.append(f'  "{e.src}" --> "{e.dst}"')
                shown += 1
                if shown >= 120:
                    break

        if shown == 0:
            lines.append('  A["(no edges rendered)"]')
        lines.append("```")
        lines.append("")
        lines.append("## Stats")
        for k in sorted(graph.stats.keys()):
            lines.append(f"- **{k}**: {graph.stats[k]}")
        lines.append("")
        lines.append("## Notes")
        lines.append("- Destinations like `py:...`, `js:...`, `rs:...` are dependency specs (not resolved to paths yet).")
        lines.append("- This is designed to be deterministic and readable, not a perfect compiler-grade call graph.")
        lines.append("")
        return "\n".join(lines)
