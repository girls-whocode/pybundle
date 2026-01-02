from __future__ import annotations
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .roadmap_model import Node, Edge, EntryPoint, RoadmapGraph

PY_EXT = {".py"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs"}
TS_EXT = {".ts", ".tsx"}
RUST_EXT = {".rs"}

IMPORT_RE = re.compile(r'^\s*import\s+.*?\s+from\s+[\'"](.+?)[\'"]\s*;?\s*$', re.M)
REQUIRE_RE = re.compile(r'require\(\s*[\'"](.+?)[\'"]\s*\)')
RUST_USE_RE = re.compile(r'^\s*use\s+([a-zA-Z0-9_:]+)', re.M)
RUST_MOD_RE = re.compile(r'^\s*mod\s+([a-zA-Z0-9_]+)\s*;', re.M)

def _rel(root: Path, p: Path) -> str:
    return str(p.resolve().relative_to(root.resolve())).replace("\\", "/")

def guess_lang(p: Path) -> str:
    suf = p.suffix.lower()
    if suf in PY_EXT: return "python"
    if suf in TS_EXT: return "ts"
    if suf in JS_EXT: return "js"
    if suf in RUST_EXT: return "rust"
    if suf in {".html", ".jinja", ".j2"}: return "html"
    if suf in {".css", ".scss", ".sass"}: return "css"
    if suf in {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}: return "config"
    return "unknown"

def scan_python_imports(root: Path, file_path: Path) -> list[str]:
    # returns import module strings (not resolved paths)
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    mods: list[str] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                mods.append(a.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                mods.append(n.module)
    return mods

def scan_js_imports(text: str) -> list[str]:
    out = []
    out += IMPORT_RE.findall(text)
    out += REQUIRE_RE.findall(text)
    return out

def scan_rust_uses(text: str) -> tuple[list[str], list[str]]:
    uses = RUST_USE_RE.findall(text)
    mods = RUST_MOD_RE.findall(text)
    return uses, mods

def detect_entrypoints(root: Path) -> list[EntryPoint]:
    eps: list[EntryPoint] = []

    # Python CLI entry: __main__.py
    p = root / "src"
    if p.exists():
        for main in p.rglob("__main__.py"):
            eps.append(EntryPoint(node=_rel(root, main), reason="python __main__.py", confidence=3))

    # Rust main.rs (including tauri src-tauri)
    for mr in root.rglob("main.rs"):
        if "target/" in str(mr):  # safety
            continue
        eps.append(EntryPoint(node=_rel(root, mr), reason="rust main.rs", confidence=3))

    # package.json scripts as entrypoints (synthetic)
    pkg = root / "package.json"
    if pkg.is_file():
        eps.append(EntryPoint(node="package.json", reason="node scripts", confidence=2))

    return eps

def build_roadmap(root: Path, include_dirs: list[Path], exclude_dirs: set[str], max_files: int = 20000) -> RoadmapGraph:
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    # Walk selected dirs
    files: list[Path] = []
    for d in include_dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_dir():
                if p.name in exclude_dirs:
                    # skip subtree
                    continue
                continue
            if p.stat().st_size > 2_000_000:  # 2MB safety; tune later
                continue
            files.append(p)
            if len(files) >= max_files:
                break

    # Create nodes
    for f in files:
        rel = _rel(root, f)
        nodes[rel] = Node(id=rel, path=rel, lang=guess_lang(f))

    # Scan edges
    for f in files:
        rel = _rel(root, f)
        lang = nodes[rel].lang
        text = None

        if lang in {"js", "ts", "rust", "html", "config"}:
            text = f.read_text(encoding="utf-8", errors="replace")

        if lang == "python":
            for mod in scan_python_imports(root, f):
                edges.append(Edge(src=rel, dst=f"py:{mod}", type="import"))
        elif lang in {"js", "ts"} and text is not None:
            for spec in scan_js_imports(text):
                edges.append(Edge(src=rel, dst=f"js:{spec}", type="import"))
        elif lang == "rust" and text is not None:
            uses, mods = scan_rust_uses(text)
            for u in uses:
                edges.append(Edge(src=rel, dst=f"rs:{u}", type="use"))
            for m in mods:
                edges.append(Edge(src=rel, dst=f"rsmod:{m}", type="mod"))

        # TODO: add template includes, docker compose, pyproject scripts, etc.

    # Entrypoints
    eps = detect_entrypoints(root)

    # Stats
    stats: dict[str, int] = {}
    for n in nodes.values():
        stats[f"nodes_{n.lang}"] = stats.get(f"nodes_{n.lang}", 0) + 1
    for e in edges:
        stats[f"edges_{e.type}"] = stats.get(f"edges_{e.type}", 0) + 1

    # determinism: sort
    node_list = sorted(nodes.values(), key=lambda x: x.id)
    edge_list = sorted(edges, key=lambda e: (e.src, e.dst, e.type, e.note))
    eps_sorted = sorted(eps, key=lambda e: (e.node, -e.confidence, e.reason))

    return RoadmapGraph(
        version=1,
        root=str(root),
        nodes=node_list,
        edges=edge_list,
        entrypoints=eps_sorted,
        stats=stats,
    )
