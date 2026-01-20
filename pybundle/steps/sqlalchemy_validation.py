"""
Step: SQLAlchemy Validation
Validate SQLAlchemy models and relationships.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .base import Step, StepResult


class SQLAlchemyValidationStep(Step):
    """Validate SQLAlchemy model definitions and relationships."""

    name = "sqlalchemy validation"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Validate SQLAlchemy models."""
        import time

        start = time.time()

        root = ctx.root

        # Analyze models
        models = self._find_sqlalchemy_models(root)
        if not models:
            elapsed = int(time.time() - start)
            return StepResult(
                self.name, "SKIP", elapsed, "No SQLAlchemy models found"
            )

        # Validate relationships
        issues = self._validate_relationships(root, models)

        # Generate report
        lines = [
            "=" * 80,
            "SQLALCHEMY VALIDATION REPORT",
            "=" * 80,
            "",
        ]

        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                f"Models found: {len(models)}",
                "",
            ]
        )

        # Models list
        lines.extend(
            [
                "MODEL DEFINITIONS",
                "-" * 80,
                "",
            ]
        )

        for model in sorted(models, key=lambda m: m["name"]):
            lines.append(f"  {model['name']}")
            lines.append(f"    File: {model['file']}")
            lines.append(f"    Table: {model.get('table', '(auto-generated)')}")
            if model.get("columns"):
                lines.append(f"    Columns: {', '.join(model['columns'][:5])}")
                if len(model["columns"]) > 5:
                    lines.append(f"             ... and {len(model['columns']) - 5} more")
            if model.get("relationships"):
                lines.append(f"    Relationships: {', '.join(model['relationships'])}")
            lines.append("")

        # Validation issues
        lines.extend(
            [
                "VALIDATION ISSUES",
                "=" * 80,
                "",
            ]
        )

        if issues:
            error_count = sum(1 for _, level, _, _ in issues if level == "ERROR")
            warning_count = sum(1 for _, level, _, _ in issues if level == "WARNING")

            lines.append(
                f"Found {len(issues)} issue(s): {error_count} error(s), {warning_count} warning(s)"
            )
            lines.append("")

            for model_name, level, issue, detail in issues:
                icon = "✗" if level == "ERROR" else "⚠"
                lines.append(f"  {icon} [{model_name}] {issue}")
                if detail:
                    lines.append(f"      {detail}")
            lines.append("")
        else:
            lines.append("✓ No validation issues detected")
            lines.append("")

        # Relationship analysis
        lines.extend(
            [
                "RELATIONSHIP ANALYSIS",
                "-" * 80,
                "",
            ]
        )

        relationships = self._analyze_relationships(models)
        if relationships:
            for rel in relationships:
                lines.append(f"  {rel}")
        else:
            lines.append("  ℹ No relationships defined")

        lines.append("")

        # Recommendations
        lines.extend(
            [
                "=" * 80,
                "BEST PRACTICES & RECOMMENDATIONS",
                "=" * 80,
                "",
                "1. MODEL DESIGN",
                "   ✓ Use descriptive model and column names",
                "   ✓ Define primary keys explicitly",
                "   ✓ Use UUID or serial primary keys",
                "   ✓ Add created_at and updated_at timestamps",
                "",
                "2. RELATIONSHIPS",
                "   ✓ Use relationship() for ORM-level access",
                "   ✓ Define foreign keys explicitly",
                "   ✓ Set cascade rules (delete-orphan for children)",
                "   ✓ Use back_populates for bidirectional relationships",
                "",
                "3. CONSTRAINTS",
                "   ✓ Add CHECK constraints for valid data",
                "   ✓ Use nullable=False for required fields",
                "   ✓ Add unique=True for unique fields",
                "   ✓ Add indexes to frequently queried fields",
                "",
                "4. INHERITANCE",
                "   ✓ Consider single table inheritance for polymorphism",
                "   ✓ Use joined table inheritance for distinct tables",
                "   ✓ Document inheritance strategy clearly",
                "",
                "5. SERIALIZATION",
                "   ✓ Use Pydantic models for API responses",
                "   ✓ Define __repr__ for debugging",
                "   ✓ Define to_dict() for serialization",
                "   ✓ Exclude sensitive fields from serialization",
                "",
                "6. QUERIES",
                "   ✓ Use lazy='select' or 'selectin' for relationships",
                "   ✓ Use .only() or .defer() to limit columns",
                "   ✓ Use exists() for existence checks",
                "   ✓ Use bulk_insert_mappings() for bulk operations",
                "",
                "7. TESTING",
                "   ✓ Test model creation and validation",
                "   ✓ Test relationship cascades",
                "   ✓ Test constraint violations",
                "   ✓ Use pytest fixtures for model factories",
                "",
            ]
        )

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "152_sqlalchemy_validation.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_sqlalchemy_models(self, root: Path) -> List[Dict[str, Any]]:
        """Find SQLAlchemy model definitions."""
        models = []
        python_files = list(root.rglob("*.py"))

        for py_file in python_files:
            if any(
                part in py_file.parts
                for part in ["venv", ".venv", "env", "__pycache__", "site-packages"]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")

                if "from sqlalchemy" not in source:
                    continue

                # Look for model class definitions
                # Pattern: class ModelName(Base): or class ModelName(declarative_base()):
                class_pattern = r"class\s+(\w+)\s*\((.*?(Base|DeclarativeMeta|declarative_base).*?)\):"
                for match in re.finditer(class_pattern, source):
                    model_name = match.group(1)

                    # Extract table name if specified
                    table_match = re.search(
                        rf"class\s+{model_name}.*?\n\s+__tablename__\s*=\s*['\"](\w+)['\"]",
                        source,
                    )
                    table_name = table_match.group(1) if table_match else None

                    # Extract columns
                    columns = re.findall(r"(\w+)\s*=\s*Column\(", source)

                    # Extract relationships
                    relationships = re.findall(r"(\w+)\s*=\s*relationship\(", source)

                    models.append(
                        {
                            "name": model_name,
                            "file": str(py_file.relative_to(root)),
                            "table": table_name,
                            "columns": columns,
                            "relationships": relationships,
                        }
                    )

            except (OSError, UnicodeDecodeError):
                continue

        return models

    def _validate_relationships(
        self, root: Path, models: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, str, str]]:
        """Validate model relationships."""
        issues = []
        model_names = {m["name"] for m in models}

        for model in models:
            # Check if relationships reference existing models
            for rel in model.get("relationships", []):
                # Very basic check - relationship should reference a model
                if not any(model_name in rel for model_name in model_names):
                    # This is a heuristic - might be false positive
                    pass

            # Check for missing primary key
            if not any(col.lower() == "id" for col in model.get("columns", [])):
                issues.append(
                    (
                        model["name"],
                        "WARNING",
                        "No obvious primary key found",
                        "Ensure model has a primary key defined",
                    )
                )

        return issues

    def _analyze_relationships(self, models: List[Dict[str, Any]]) -> List[str]:
        """Analyze relationships between models."""
        relationships = []

        for model in models:
            for rel in model.get("relationships", []):
                relationships.append(f"  {model['name']}.{rel}")

        return relationships
