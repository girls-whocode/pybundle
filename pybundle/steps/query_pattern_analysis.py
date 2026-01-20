"""
Step: Query Pattern Analysis
Analyze database query patterns and detect performance issues.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class QueryPatternAnalysisStep(Step):
    """Analyze database query patterns for performance issues."""

    name = "query pattern analysis"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze query patterns in codebase."""
        import time

        start = time.time()

        root = ctx.root

        # Analyze query patterns
        patterns = self._analyze_query_patterns(root)

        # Generate report
        lines = [
            "=" * 80,
            "QUERY PATTERN ANALYSIS REPORT",
            "=" * 80,
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"ORM framework detected: {patterns['orm_type']}",
                f"Model definitions found: {patterns['model_count']}",
                f"Query patterns analyzed: {patterns['query_count']}",
                "",
            ]
        )

        if not patterns["orm_type"]:
            lines.extend(
                [
                    "⊘ No ORM detected",
                    "",
                    "This project does not appear to use an ORM.",
                    "If this is incorrect, ensure ORM imports are in analyzed files.",
                    "",
                ]
            )
        else:
            # ORM Details
            lines.extend(
                [
                    f"{patterns['orm_type'].upper()} ANALYSIS",
                    "=" * 80,
                    "",
                ]
            )

            lines.append(f"Models/Entities found: {patterns['model_count']}")
            if patterns["models"]:
                for model in sorted(patterns["models"])[:15]:
                    lines.append(f"  - {model}")
                if len(patterns["models"]) > 15:
                    lines.append(f"  ... and {len(patterns['models']) - 15} more")

            lines.append("")

            # N+1 Query Patterns
            if patterns["suspected_n_plus_1"]:
                lines.extend(
                    [
                        "SUSPECTED N+1 QUERY PATTERNS",
                        "=" * 80,
                        "",
                    ]
                )

                for issue in patterns["suspected_n_plus_1"][:15]:
                    lines.append(f"File: {issue['file']}")
                    lines.append(f"Line: {issue['line']}")
                    lines.append(f"Pattern: {issue['pattern']}")
                    if issue.get("context"):
                        context = issue["context"].strip()
                        if len(context) > 70:
                            context = context[:67] + "..."
                        lines.append(f"Context: {context}")
                    lines.append("")

                if len(patterns["suspected_n_plus_1"]) > 15:
                    lines.append(
                        f"... and {len(patterns['suspected_n_plus_1']) - 15} more suspected N+1 patterns"
                    )
                    lines.append("")

            else:
                lines.append("✓ No obvious N+1 query patterns detected")
                lines.append("")

            # Lazy Loading Patterns
            if patterns["lazy_loading"]:
                lines.extend(
                    [
                        "LAZY LOADING PATTERNS (Potential Performance Issues)",
                        "=" * 80,
                        "",
                    ]
                )

                for issue in patterns["lazy_loading"][:10]:
                    lines.append(f"File: {issue['file']}")
                    lines.append(f"Line: {issue['line']}")
                    lines.append(f"Type: {issue['type']}")
                    lines.append("")

                if len(patterns["lazy_loading"]) > 10:
                    lines.append(
                        f"... and {len(patterns['lazy_loading']) - 10} more lazy loading patterns"
                    )
                    lines.append("")

            # Relationship Access
            if patterns["relationship_access"]:
                lines.extend(
                    [
                        "RELATIONSHIP ACCESS PATTERNS",
                        "=" * 80,
                        "",
                    ]
                )

                lines.append(
                    f"Foreign key accesses: {patterns['relationship_access'].get('foreign_keys', 0)}"
                )
                lines.append(
                    f"Many-to-many accesses: {patterns['relationship_access'].get('many_to_many', 0)}"
                )
                lines.append(
                    f"Reverse relationship accesses: {patterns['relationship_access'].get('reverse', 0)}"
                )

                lines.append("")

        # Recommendations
        lines.extend(
            [
                "=" * 80,
                "RECOMMENDATIONS",
                "=" * 80,
                "",
            ]
        )

        if patterns["orm_type"]:
            if patterns["suspected_n_plus_1"]:
                if patterns["orm_type"].lower() == "django":
                    lines.append("  N+1 Query Fixes (Django):")
                    lines.append("    - Use select_related() for ForeignKey relationships")
                    lines.append("    - Use prefetch_related() for ManyToMany and reverse ForeignKey")
                    lines.append("")
                    lines.append("  Example:")
                    lines.append(
                        "    users = User.objects.select_related('profile').prefetch_related('posts')"
                    )

                elif patterns["orm_type"].lower() == "sqlalchemy":
                    lines.append("  N+1 Query Fixes (SQLAlchemy):")
                    lines.append("    - Use joinedload() for eager loading")
                    lines.append("    - Use contains_eager() with joins")
                    lines.append("    - Use selectinload() for relationships")
                    lines.append("")
                    lines.append("  Example:")
                    lines.append(
                        "    query.options(joinedload(User.posts)).all()"
                    )

                lines.append("")

            if patterns["lazy_loading"]:
                lines.append("  Lazy Loading Best Practices:")
                lines.append("    - Load related objects within query, not after retrieval")
                lines.append("    - Use batch loading for sets of objects")
                lines.append("    - Consider caching for frequently accessed relationships")
                lines.append("")

            lines.append("  General Recommendations:")
            lines.append("    - Use database query profiling (Django Debug Toolbar, etc.)")
            lines.append("    - Review query execution plans (EXPLAIN)")
            lines.append("    - Add indexes to frequently filtered columns")
            lines.append("    - Monitor query count and execution time")

        else:
            lines.append("  - No ORM detected; static query analysis not applicable")
            lines.append("  - If using raw SQL, consider adopting an ORM for consistency")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "140_query_patterns.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _analyze_query_patterns(self, root: Path) -> Dict:
        """Analyze query patterns in codebase."""
        orm_type = None
        models = set()
        model_count = 0
        query_count = 0
        suspected_n_plus_1 = []
        lazy_loading = []
        relationship_access = {"foreign_keys": 0, "many_to_many": 0, "reverse": 0}

        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(root))

                # Detect ORM
                if "from django.db import models" in source or "from django.db.models" in source:
                    if not orm_type:
                        orm_type = "Django"
                elif (
                    "from sqlalchemy" in source
                    and "declarative_base" in source
                ):
                    if not orm_type:
                        orm_type = "SQLAlchemy"
                elif "from tortoise import fields" in source:
                    if not orm_type:
                        orm_type = "Tortoise ORM"

                # Count models
                for line in source.split("\n"):
                    if re.search(r"class\s+(\w+)\s*\(.*Model.*\):", line):
                        match = re.search(r"class\s+(\w+)\s*\(", line)
                        if match:
                            model_name = match.group(1)
                            models.add(model_name)
                            model_count += 1

                # Detect query patterns
                for line_num, line in enumerate(source.split("\n"), 1):
                    # N+1 patterns
                    if re.search(
                        r"for\s+\w+\s+in\s+.*\.\s*(all|filter|get)\(\)",
                        line
                    ):
                        query_count += 1
                        suspected_n_plus_1.append(
                            {
                                "file": rel_path,
                                "line": line_num,
                                "pattern": "Loop with query",
                                "context": line,
                            }
                        )

                    # Django patterns
                    if "select_related" not in source and "for obj in" in line:
                        if ".objects.all()" in source or ".objects.filter" in source:
                            query_count += 1

                    # Lazy loading patterns (accessing attributes after query)
                    if (
                        re.search(r"\.[\w_]+\s*(?:$|#)", line)
                        and "select_related" not in line
                        and "prefetch" not in line
                    ):
                        # Potential lazy loading
                        if any(
                            kw in line
                            for kw in ["for ", r"\.all(", r"\.filter("]
                        ):
                            pass
                        else:
                            lazy_loading.append(
                                {
                                    "file": rel_path,
                                    "line": line_num,
                                    "type": "Potential lazy loading",
                                }
                            )

                    # Relationship access patterns
                    if re.search(r"\.\w+_set\.", line):  # Reverse FK Django
                        relationship_access["reverse"] += 1
                    elif re.search(r"\.objects\.through", line):  # Many-to-many
                        relationship_access["many_to_many"] += 1
                    elif re.search(r"\..*_id\b", line):  # FK access
                        relationship_access["foreign_keys"] += 1

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Deduplicate and limit
        suspected_n_plus_1 = list(
            {(item["file"], item["line"]): item for item in suspected_n_plus_1}.values()
        )
        lazy_loading = list(
            {(item["file"], item["line"]): item for item in lazy_loading}.values()
        )

        return {
            "orm_type": orm_type,
            "models": models,
            "model_count": model_count,
            "query_count": query_count,
            "suspected_n_plus_1": suspected_n_plus_1,
            "lazy_loading": lazy_loading,
            "relationship_access": relationship_access,
        }
