from __future__ import annotations
import ast
import os
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Literal
from .steps.copy_pack import _is_venv_root, _is_under_venv

from .roadmap_model import Node, Edge, EntryPoint, RoadmapGraph

PY_EXT = {".py"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs"}
TS_EXT = {".ts", ".tsx"}
RUST_EXT = {".rs"}
Lang = Literal["python", "js", "ts", "rust", "html", "css", "config", "unknown"]

IMPORT_RE = re.compile(r'^\s*import\s+.*?\s+from\s+[\'"](.+?)[\'"]\s*;?\s*$', re.M)
REQUIRE_RE = re.compile(r'require\(\s*[\'"](.+?)[\'"]\s*\)')
RUST_USE_RE = re.compile(r'^\s*use\s+([a-zA-Z0-9_:]+)', re.M)
RUST_MOD_RE = re.compile(r'^\s*mod\s+([a-zA-Z0-9_]+)\s*;', re.M)

def _rel(root: Path, p: Path) -> str:
    return str(p.resolve().relative_to(root.resolve())).replace("\\", "/")

def guess_lang(p: Path) -> Lang:
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

def detect_entrypoints_from_nodes(nodes: dict[str, Node]) -> list[EntryPoint]:
    """Derive entrypoints from the scanned node list (deterministic, no FS scope issues)."""
    eps: list[EntryPoint] = []

    for nid, n in nodes.items():
        path = n.path
        if path.endswith("__main__.py"):
            eps.append(EntryPoint(node=nid, reason="python __main__.py", confidence=3))
        elif path.endswith("main.rs"):
            eps.append(EntryPoint(node=nid, reason="rust main.rs", confidence=3))
        elif path == "package.json":
            eps.append(EntryPoint(node=nid, reason="node package.json scripts", confidence=2))
        elif path == "pyproject.toml":
            eps.append(EntryPoint(node=nid, reason="python pyproject.toml (scripts/entrypoints likely)", confidence=1))

    # Optional hints (useful for library-ish layouts)
    for hint in ("src/pybundle/cli.py", "src/pybundle/__init__.py"):
        if hint in nodes:
            eps.append(EntryPoint(node=hint, reason="likely CLI/module entry", confidence=1))

    # Deduplicate deterministically
    uniq = {(e.node, e.reason, e.confidence) for e in eps}
    eps = [EntryPoint(node=a, reason=b, confidence=c) for (a, b, c) in uniq]
    return sorted(eps, key=lambda e: (e.node, -e.confidence, e.reason))

def _resolve_py_to_node(root: Path, src_rel: str, mod: str) -> Optional[str]:
    """
    Resolve a Python import module string to a local file node (relative path),
    if it exists in the scanned repo. Deterministic, no sys.path tricks.
    """
    # Normalize relative imports like ".cli" or "..utils"
    # We only support relative imports within the src file's package directory.
    if mod.startswith("."):
        # count leading dots
        dots = 0
        for ch in mod:
            if ch == ".":
                dots += 1
            else:
                break
        tail = mod[dots:]  # remaining name after dots
        src_dir = Path(src_rel).parent  # e.g. pybundle/
        # go up (dots-1) levels: from . = same package, .. = parent, etc
        base = src_dir
        for _ in range(max(dots - 1, 0)):
            base = base.parent
        if tail:
            parts = tail.split(".")
            cand = base.joinpath(*parts)
        else:
            cand = base
    else:
        cand = Path(*mod.split("."))

    # candidate file paths relative to root
    py_file = (root / cand).with_suffix(".py")
    init_file = root / cand / "__init__.py"

    if py_file.is_file():
        return _rel(root, py_file)
    if init_file.is_file():
        return _rel(root, init_file)
    return None

def build_roadmap(root: Path, include_dirs: list[Path], exclude_dirs: set[str], max_files: int = 20000) -> RoadmapGraph:
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    # Walk selected dirs
    files: list[Path] = []
    root_res = root.resolve()

    skipped_big = 0

    for d in include_dirs:
        if not d.exists():
            continue

        if _is_venv_root(d):
            continue

        for dirpath, dirnames, filenames in os.walk(d):
            dirpath_p = Path(dirpath)

            # 1) prune excluded dirs by name
            dirnames[:] = [dn for dn in dirnames if dn not in exclude_dirs]

            # 2) prune venv dirs by structure (ANY name)
            dirnames[:] = [dn for dn in dirnames if dn not in exclude_dirs and dn != ".pybundle-venv"]
            dirnames[:] = [dn for dn in dirnames if not _is_venv_root(dirpath_p / dn)]

            for fn in filenames:
                p = dirpath_p / fn

                # 3️⃣ skip anything under a venv (belt + suspenders)
                rel = Path(_rel(root, p))
                if _is_under_venv(root, rel):
                    continue

                rel_s = _rel(root, p)
                if rel_s.startswith(".pybundle-venv/") or "/site-packages/" in rel_s:
                    continue
                if _is_under_venv(root, Path(rel_s)):
                    continue

                try:
                    if p.stat().st_size > 2_000_000:
                        skipped_big += 1
                        continue
                except OSError:
                    continue

                files.append(p)
                if len(files) >= max_files:
                    break

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
                resolved = _resolve_py_to_node(root, rel, mod)
                if resolved and resolved in nodes:
                    edges.append(Edge(src=rel, dst=resolved, type="import"))
                else:
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
    eps = detect_entrypoints_from_nodes(nodes)

    # Stats
    stats: dict[str, int] = {}
    for n in nodes.values():
        stats[f"nodes_{n.lang}"] = stats.get(f"nodes_{n.lang}", 0) + 1
    for e in edges:
        stats[f"edges_{e.type}"] = stats.get(f"edges_{e.type}", 0) + 1
    stats["skipped_big_files"] = skipped_big

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
