from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import Step, StepResult


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_read(path: Path) -> str:
    if not path.exists():
        return f"(missing: {path.as_posix()})"
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _tool_table(tools_obj: Any) -> list[str]:
    d = (
        asdict(tools_obj)
        if hasattr(tools_obj, "__dataclass_fields__")
        else dict(tools_obj)
    )
    lines = ["| Tool | Status |", "|------|--------|"]
    for k in sorted(d.keys()):
        v = d[k]
        if v:
            lines.append(f"| `{k}` | ✅ `{v}` |")
        else:
            lines.append(f"| `{k}` | ❌ `<missing>` |")
    return lines


class HandoffMarkdownStep(Step):
    name = "generate HANDOFF.md"

    def run(self, ctx: Any) -> StepResult:
        start = time.time()

        created_utc = getattr(ctx, "created_utc", None) or _utc_now()
        profile = getattr(ctx, "profile_name", "<unknown>")
        root_path = Path(getattr(ctx, "root"))
        project = root_path.name
        root = str(root_path)
        workdir_path = Path(getattr(ctx, "workdir"))
        workdir = str(workdir_path)

        # filenames fixed to match your repo
        uname = _safe_read(workdir_path / "meta" / "21_uname.txt")
        pyver = _safe_read(workdir_path / "meta" / "20_python_version.txt")

        redact = bool(getattr(ctx, "redact", True))
        redact_status = "enabled" if redact else "disabled"

        results: list[Any] = list(getattr(ctx, "results", []))
        pass_n = sum(1 for r in results if getattr(r, "status", "") == "PASS")
        fail_n = sum(1 for r in results if getattr(r, "status", "") == "FAIL")
        skip_n = sum(1 for r in results if getattr(r, "status", "") == "SKIP")
        total_n = len(results)

        overall = "FAIL" if fail_n else ("DEGRADED" if skip_n else "PASS")

        # tool table
        tools_obj = getattr(ctx, "tools", None) or getattr(ctx, "tooling", None)
        tools_table = (
            _tool_table(tools_obj) if tools_obj is not None else ["(no tools detected)"]
        )

        command_used = getattr(ctx, "command_used", "") or "(not captured)"

        lines: list[str] = []
        lines.append("# Bundle Handoff")
        lines.append("")
        lines.append("## Overview")
        lines.append(
            f"- **Bundle tool:** pybundle {getattr(ctx, 'version', '<unknown>')}"
        )
        lines.append(f"- **Profile:** {profile}")
        lines.append(f"- **Created (UTC):** {created_utc}")
        lines.append(f"- **Project:** {project}")
        lines.append(f"- **Root:** {root}")
        lines.append(f"- **Workdir:** {workdir}")
        lines.append("")
        lines.append("## System")
        lines.append(f"- **OS:** {uname}")
        lines.append(f"- **Python:** {pyver}")
        lines.append(f"- **Redaction:** {redact_status}")
        lines.append("")
        lines.append("## At a glance")

        lines.append("## AI context summary")

        copy_manifest = _safe_read(
            workdir_path / "meta" / "50_copy_manifest.txt"
        ).strip()
        if copy_manifest:
            lines.append("### Curated copy")
            lines.append("```")
            lines.append(copy_manifest)
            lines.append("```")
        else:
            lines.append("- Curated copy manifest not found.")

        roadmap_json = _safe_read(workdir_path / "meta" / "70_roadmap.json").strip()
        if roadmap_json:
            try:
                import json

                rj = json.loads(roadmap_json)
                langs = set()
                for n in rj.get("nodes", []):
                    if isinstance(n, dict):
                        lang = n.get("lang")
                        if lang:
                            langs.add(lang)
                eps = rj.get("entrypoints", []) or []
                lines.append(
                    f"- **Languages detected:** {', '.join(sorted(langs)) if langs else '(none)'}"
                )
                if eps:
                    lines.append("- **Entrypoints:**")
                    for ep in eps[:10]:
                        node = ep.get("node") if isinstance(ep, dict) else None
                        reason = ep.get("reason") if isinstance(ep, dict) else None
                        conf = ep.get("confidence") if isinstance(ep, dict) else None
                        if node:
                            extra = ""
                            if reason is not None and conf is not None:
                                extra = f" — {reason} ({conf}/3)"
                            lines.append(f"  - `{node}`{extra}")
                else:
                    lines.append("- **Entrypoints:** (none detected)")
            except Exception:
                lines.append("- Roadmap JSON present but could not be parsed.")
        else:
            lines.append("- Roadmap not found.")

        lines.append("")

        lines.append(f"- **Overall status:** {overall}")
        lines.append(
            f"- **Steps:** {total_n} total — {pass_n} PASS, {fail_n} FAIL, {skip_n} SKIP"
        )
        lines.append("")
        lines.append("## Tools")
        lines.extend(tools_table)
        lines.append("")
        lines.append("## Command used")
        lines.append("```bash")
        lines.append(command_used)
        lines.append("```")
        lines.append("")
        lines.append("## Reproduction")
        lines.append("See **REPRO.md** for step-by-step reproduction instructions.")
        lines.append("")

        out_path = workdir_path / "HANDOFF.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")

        secs = int(time.time() - start)
        return StepResult(
            name=self.name, status="PASS", seconds=secs, note="wrote HANDOFF.md"
        )
