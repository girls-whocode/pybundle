from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Dict, List, Optional

Lang = Literal["python", "js", "ts", "rust", "html", "css", "config", "unknown"]
EdgeType = Literal["import", "require", "use", "mod", "include", "script", "entrypoint"]

@dataclass(frozen=True)
class Node:
    id: str                 # stable id (usually path)
    path: str               # repo-relative
    lang: Lang

@dataclass(frozen=True)
class Edge:
    src: str                # node id
    dst: str                # node id (or synthetic id)
    type: EdgeType
    note: str = ""          # e.g. "from X import Y", "package.json script: dev"

@dataclass
class EntryPoint:
    node: str               # node id
    reason: str             # why we think it's an entry
    confidence: int = 2     # 1-3

@dataclass
class RoadmapGraph:
    version: int
    root: str
    nodes: List[Node]
    edges: List[Edge]
    entrypoints: List[EntryPoint]
    stats: Dict[str, int]   # counts by lang/edge types/etc.

    def to_dict(self) -> dict:
        return asdict(self)
