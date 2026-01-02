from __future__ import annotations
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext
from ..roadmap_scan import build_roadmap
from ..steps.copy_pack import DEFAULT_EXCLUDE_DIRS
from ..policy import AIContextPolicy

@dataclass
class RoadmapStep:
    name: str = "roadmap (project map)"
    out_md: str = "meta/70_roadmap.md"
    out_json: str = "meta/70_roadmap.json"
    include: list[str] | None = None
    max_files: int = 20000
    policy: AIContextPolicy | None = None

    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()

        include_dirs = []
        if self.include:
            include_dirs = [ctx.root / p for p in self.include]
        else:
            # sane defaults: mimic your curated source approach
            include_dirs: list[Path] = []
            if self.include:
                include_dirs = [ctx.root / p for p in self.include]
            else:
                # sane defaults: scan source trees, not the whole repo
                candidates = [
                    ctx.root / "src",
                    ctx.root / "pybundle",        # in case this repo isn't src-layout
                    ctx.root / "src-tauri",
                    ctx.root / "frontend",
                    ctx.root / "web",
                    ctx.root / "ui",
                    ctx.root / "templates",
                    ctx.root / "static",
                ]
                include_dirs = [p for p in candidates if p.exists()]

                # fallback if none exist
                if not include_dirs:
                    include_dirs = [ctx.root]

        policy = self.policy or AIContextPolicy()
        include_dirs = [p for p in policy.include_dir_candidates(ctx.root)]
        exclude_dirs = set(policy.exclude_dirs)

        graph = build_roadmap(
            root=ctx.root,
            include_dirs=include_dirs,
            exclude_dirs=exclude_dirs,
            max_files=policy.roadmap_max_files,
            # later: depth=policy.roadmap_depth
        )

        # Write JSON
        out_json_path = ctx.workdir / self.out_json
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")

        # Write Markdown (with Mermaid)
        out_md_path = ctx.workdir / self.out_md
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        out_md_path.write_text(self._render_md(graph), encoding="utf-8")

        langs = sorted({n.lang for n in graph.nodes if getattr(n, "lang", None)})
        summary = {
            "languages": langs,
            "entrypoints": [ep.node for ep in graph.entrypoints[:50]],
            "stats": graph.stats,
        }
        (ctx.workdir / "meta" / "71_roadmap_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

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

        depth = 2
        max_edges = 180
        try:
            # if policy is passed through, prefer it
            if hasattr(self, "policy") and self.policy is not None:
                depth = self.policy.roadmap_mermaid_depth
                max_edges = self.policy.roadmap_mermaid_max_edges
        except Exception:
            pass

        lines.append("```mermaid")
        lines.append("flowchart LR")
        lines.extend(self._render_mermaid_bfs(graph, max_depth=depth, max_edges=max_edges))
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

    def _render_mermaid_bfs(self, graph, max_depth: int = 2, max_edges: int = 180) -> list[str]:
        from collections import deque

        adj: dict[str, list[str]] = {}
        for e in graph.edges:
            adj.setdefault(e.src, []).append(e.dst)

        entry = [ep.node for ep in graph.entrypoints]
        if not entry:
            return ['  A["(no entrypoints)"]']

        q = deque([(n, 0) for n in entry])
        seen_edges: set[tuple[str, str]] = set()
        shown: list[str] = []
        seen_nodes: set[str] = set(entry)

        while q and len(shown) < max_edges:
            node, depth = q.popleft()
            if depth >= max_depth:
                continue
            for dst in adj.get(node, []):
                key = (node, dst)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                shown.append(f'  "{node}" --> "{dst}"')
                if dst not in seen_nodes:
                    seen_nodes.add(dst)
                    q.append((dst, depth + 1))
                if len(shown) >= max_edges:
                    break

        return shown or ['  A["(no edges rendered)"]']