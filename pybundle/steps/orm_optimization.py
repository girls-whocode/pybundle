"""
Step: ORM Optimization Analysis
Analyze ORM usage and provide optimization suggestions.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class ORMOptimizationStep(Step):
    """Analyze ORM usage patterns and suggest optimizations."""

    name = "orm optimization"

    # Django-specific patterns
    DJANGO_PATTERNS = {
        "bulk_create": r"\.bulk_create\(",
        "bulk_update": r"\.bulk_update\(",
        "select_related": r"\.select_related\(",
        "prefetch_related": r"\.prefetch_related\(",
        "only": r"\.only\(",
        "defer": r"\.defer\(",
        "values": r"\.values\(",
        "values_list": r"\.values_list\(",
        "exists": r"\.exists\(",
        "count": r"\.count\(",
    }

    # SQLAlchemy patterns
    SQLALCHEMY_PATTERNS = {
        "joinedload": r"joinedload\(",
        "selectinload": r"selectinload\(",
        "contains_eager": r"contains_eager\(",
        "defer": r"defer\(",
        "load_only": r"load_only\(",
        "raiseload": r"raiseload\(",
    }

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze ORM optimization patterns."""
        import time

        start = time.time()

        root = ctx.root

        # Analyze ORM usage
        analysis = self._analyze_orm_optimization(root)

        # Generate report
        lines = [
            "=" * 80,
            "ORM OPTIMIZATION ANALYSIS REPORT",
            "=" * 80,
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"Primary ORM: {analysis['primary_orm'] or 'None detected'}",
                "",
            ]
        )

        if not analysis["primary_orm"]:
            lines.extend(
                [
                    "⊘ No ORM detected",
                    "",
                    "This project does not appear to use a common ORM.",
                    "If this is incorrect, ensure ORM imports are visible.",
                    "",
                ]
            )
        else:
            # Django Analysis
            if analysis["primary_orm"] == "Django":
                lines.extend(
                    [
                        "DJANGO ORM OPTIMIZATION",
                        "=" * 80,
                        "",
                    ]
                )

                django_analysis = analysis["django"]

                # Optimization techniques used
                lines.append("Optimization Techniques Used:")
                lines.append("")

                for technique, count in sorted(django_analysis.items()):
                    if count > 0:
                        lines.append(f"  ✓ {technique}: {count} usage(s)")

                if not any(count > 0 for count in django_analysis.values()):
                    lines.append("  ⚠ No optimization techniques detected")

                lines.append("")

                # Missing optimizations
                lines.extend(
                    [
                        "OPTIMIZATION OPPORTUNITIES",
                        "-" * 80,
                        "",
                    ]
                )

                if django_analysis.get("select_related", 0) == 0:
                    lines.append(
                        "  • Missing select_related():"
                    )
                    lines.append(
                        "    Useful for ForeignKey and OneToOneField relationships"
                    )
                    lines.append("    Reduces queries by joining related tables")
                    lines.append("")

                if django_analysis.get("prefetch_related", 0) == 0:
                    lines.append(
                        "  • Missing prefetch_related():"
                    )
                    lines.append(
                        "    Useful for ManyToManyField and reverse ForeignKey"
                    )
                    lines.append(
                        "    Fetches related objects in separate optimized queries"
                    )
                    lines.append("")

                if django_analysis.get("only", 0) == 0 and django_analysis.get(
                    "defer", 0
                ) == 0:
                    lines.append("  • Consider using only() or defer():")
                    lines.append("    Reduces data transferred from database")
                    lines.append("    Useful for large text/blob fields")
                    lines.append("")

                if django_analysis.get("bulk_create", 0) == 0:
                    lines.append("  • Missing bulk operations:")
                    lines.append("    Use bulk_create() for batch inserts")
                    lines.append("    Use bulk_update() for batch updates")
                    lines.append("")

                if django_analysis.get("exists", 0) == 0:
                    lines.append("  • Consider using exists() for existence checks:")
                    lines.append("    Faster than count() when just checking presence")
                    lines.append("")

            # SQLAlchemy Analysis
            elif analysis["primary_orm"] == "SQLAlchemy":
                lines.extend(
                    [
                        "SQLALCHEMY ORM OPTIMIZATION",
                        "=" * 80,
                        "",
                    ]
                )

                sqlalchemy_analysis = analysis["sqlalchemy"]

                # Optimization techniques used
                lines.append("Eager Loading Techniques Used:")
                lines.append("")

                for technique, count in sorted(sqlalchemy_analysis.items()):
                    if count > 0:
                        lines.append(f"  ✓ {technique}: {count} usage(s)")

                if not any(count > 0 for count in sqlalchemy_analysis.values()):
                    lines.append("  ⚠ No eager loading techniques detected")

                lines.append("")

                # Recommendations
                lines.extend(
                    [
                        "OPTIMIZATION OPPORTUNITIES",
                        "-" * 80,
                        "",
                    ]
                )

                if sqlalchemy_analysis.get("joinedload", 0) == 0:
                    lines.append("  • Missing joinedload():")
                    lines.append("    Performs eager loading with SQL joins")
                    lines.append("    Reduces number of queries")
                    lines.append("")

                if sqlalchemy_analysis.get("selectinload", 0) == 0:
                    lines.append("  • Missing selectinload():")
                    lines.append("    Performs eager loading with IN clause")
                    lines.append("    Better for large collections")
                    lines.append("")

                if sqlalchemy_analysis.get("raiseload", 0) == 0:
                    lines.append("  • Consider using raiseload():")
                    lines.append("    Catches lazy-loaded accesses (helpful for debugging)")
                    lines.append("")

            # Tortoise ORM
            elif analysis["primary_orm"] == "Tortoise ORM":
                lines.extend(
                    [
                        "TORTOISE ORM OPTIMIZATION",
                        "=" * 80,
                        "",
                        "  • Use prefetch_related() for relationships",
                        "  • Use select_related() for ForeignKey",
                        "  • Consider indexed fields for frequently filtered columns",
                        "  • Use bulk_create() for multiple insertions",
                        "",
                    ]
                )

        # General recommendations
        lines.extend(
            [
                "=" * 80,
                "GENERAL OPTIMIZATION PRINCIPLES",
                "=" * 80,
                "",
                "1. USE QUERY ANALYSIS TOOLS",
                "   - Django Debug Toolbar: Inspect query count and time",
                "   - SQLAlchemy echo=True: Log all queries",
                "   - Database EXPLAIN: Analyze query execution plans",
                "",
                "2. OPTIMIZE COMMON PATTERNS",
                "   - Batch operations (bulk_create, bulk_update)",
                "   - Eager loading (select_related, prefetch_related)",
                "   - Field selection (only, defer, values, values_list)",
                "",
                "3. DATABASE LEVEL",
                "   - Add indexes to filtered/joined columns",
                "   - Denormalize if query patterns justify it",
                "   - Use database-level aggregations when possible",
                "",
                "4. CACHING",
                "   - Cache frequently accessed objects",
                "   - Use query result caching",
                "   - Consider materialized views for complex aggregations",
                "",
                "5. MONITORING",
                "   - Track slow queries in production",
                "   - Monitor database connection pool",
                "   - Alert on query performance degradation",
                "",
            ]
        )

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "141_orm_optimization.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _analyze_orm_optimization(self, root: Path) -> Dict:
        """Analyze ORM optimization patterns."""
        primary_orm = None
        django_patterns = {k: 0 for k in self.DJANGO_PATTERNS}
        sqlalchemy_patterns = {k: 0 for k in self.SQLALCHEMY_PATTERNS}

        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")

                # Detect ORM
                if "from django.db" in source:
                    if not primary_orm:
                        primary_orm = "Django"
                    # Count Django patterns
                    for pattern_name, pattern in self.DJANGO_PATTERNS.items():
                        django_patterns[pattern_name] += len(
                            re.findall(pattern, source)
                        )

                elif "from sqlalchemy" in source:
                    if not primary_orm:
                        primary_orm = "SQLAlchemy"
                    # Count SQLAlchemy patterns
                    for pattern_name, pattern in self.SQLALCHEMY_PATTERNS.items():
                        sqlalchemy_patterns[pattern_name] += len(
                            re.findall(pattern, source)
                        )

                elif "from tortoise" in source:
                    if not primary_orm:
                        primary_orm = "Tortoise ORM"

            except (OSError, UnicodeDecodeError):
                continue

        return {
            "primary_orm": primary_orm,
            "django": django_patterns,
            "sqlalchemy": sqlalchemy_patterns,
        }
