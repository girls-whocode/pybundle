"""
Step: Migration History Tracking
Analyze database migrations and track migration status.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class MigrationHistoryStep(Step):
    """Track and analyze database migrations."""

    name = "migration history"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze database migrations."""
        import time

        start = time.time()

        root = ctx.root

        # Find migrations
        migrations = self._find_migrations(root)

        # Generate report
        lines = [
            "=" * 80,
            "DATABASE MIGRATION ANALYSIS REPORT",
            "=" * 80,
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"Migration frameworks detected: {len(migrations['frameworks'])}",
                f"Total migration files found: {migrations['total_migrations']}",
                "",
            ]
        )

        if not migrations["frameworks"]:
            lines.extend(
                [
                    "⊘ No database migrations detected",
                    "",
                    "This project does not appear to use database migrations.",
                    "Consider using migrations for schema versioning and deployment.",
                    "",
                ]
            )
        else:
            # Framework breakdown
            lines.extend(
                [
                    "MIGRATION FRAMEWORKS DETECTED",
                    "=" * 80,
                    "",
                ]
            )

            for framework, details in migrations["frameworks"].items():
                lines.append(f"✓ {framework}")
                lines.append(f"  Location: {details['location']}")
                lines.append(f"  Migration count: {len(details['migrations'])}")

                if details["migrations"]:
                    lines.append("  Files:")
                    for mig_file in sorted(details["migrations"])[:10]:
                        lines.append(f"    - {mig_file}")
                    if len(details["migrations"]) > 10:
                        lines.append(
                            f"    ... and {len(details['migrations']) - 10} more"
                        )

                lines.append("")

            # Django-specific analysis
            if "Django" in migrations["frameworks"]:
                django_info = migrations["frameworks"]["Django"]
                lines.extend(
                    [
                        "DJANGO MIGRATIONS DETAIL",
                        "=" * 80,
                        "",
                    ]
                )

                lines.append(f"Total Django migrations: {len(django_info['migrations'])}")

                # Extract migration info
                initial_count = sum(
                    1
                    for m in django_info["migrations"]
                    if "0001_initial" in m or "initial" in m.lower()
                )
                lines.append(f"Initial migrations: {initial_count}")

                # Check for dependencies
                has_dependencies = self._check_django_dependencies(
                    root, django_info["location"]
                )
                if has_dependencies:
                    lines.append("✓ Migration dependencies detected")
                else:
                    lines.append("⚠ No migration dependencies detected")

                lines.append("")

                lines.append("Latest migrations:")
                for mig_file in sorted(django_info["migrations"])[-5:]:
                    lines.append(f"  - {mig_file}")

                lines.append("")

            # Alembic-specific analysis
            if "Alembic" in migrations["frameworks"]:
                alembic_info = migrations["frameworks"]["Alembic"]
                lines.extend(
                    [
                        "ALEMBIC MIGRATIONS DETAIL",
                        "=" * 80,
                        "",
                    ]
                )

                lines.append(f"Total Alembic versions: {len(alembic_info['migrations'])}")

                # Check for downgrade capability
                versions_with_downgrade = self._check_alembic_downgrades(
                    root, alembic_info["location"]
                )
                lines.append(
                    f"Versions with downgrade support: {versions_with_downgrade}"
                )

                lines.append("Latest versions:")
                for mig_file in sorted(alembic_info["migrations"])[-5:]:
                    lines.append(f"  - {mig_file}")

                lines.append("")

        # Migration statistics
        if migrations["total_migrations"] > 0:
            lines.extend(
                [
                    "=" * 80,
                    "MIGRATION STATISTICS",
                    "=" * 80,
                    "",
                ]
            )

            lines.append(f"Total migration files: {migrations['total_migrations']}")

            # Check for common issues
            issues = self._check_migration_issues(root, migrations)
            if issues:
                lines.append(f"Potential issues found: {len(issues)}")
                lines.append("")
                for issue in issues[:10]:
                    lines.append(f"  ⚠ {issue}")
                if len(issues) > 10:
                    lines.append(f"  ... and {len(issues) - 10} more")
            else:
                lines.append("✓ No obvious migration issues detected")

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

        if migrations["frameworks"]:
            lines.append("  - Review migration dependencies for circular references")
            lines.append("  - Ensure downgrade paths are tested")
            lines.append("  - Keep migration files in version control")
            lines.append("  - Document any manual migrations")
            lines.append("  - Test migrations in CI/CD pipeline")
            lines.append("  - Consider squashing old migrations periodically")

        else:
            lines.append("  - Consider implementing database migrations")
            lines.append("  - Django projects: python manage.py makemigrations")
            lines.append("  - SQLAlchemy projects: alembic init migrations")
            lines.append("  - Tortoise ORM: aerich init-db")
            lines.append("  - Benefits: reproducible deployments, rollback capability")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "140_migrations.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_migrations(self, root: Path) -> Dict:
        """Find all migration directories and files."""
        frameworks = {}
        total_migrations = 0

        # Django migrations
        django_migrations = list(root.rglob("migrations"))
        for mig_dir in django_migrations:
            # Check if it's a Django migration directory
            init_file = mig_dir / "__init__.py"
            py_files = list(mig_dir.glob("*.py"))

            if init_file.exists() and any(
                f.name.startswith(("0001_", "0002_", "0003_")) or "000" in f.name
                for f in py_files
            ):
                rel_path = str(mig_dir.relative_to(root))
                migration_files = [
                    f.name
                    for f in py_files
                    if f.name != "__init__.py" and f.name != "__pycache__"
                ]
                if migration_files:
                    if "Django" not in frameworks:
                        frameworks["Django"] = {"location": rel_path, "migrations": []}
                    frameworks["Django"]["migrations"].extend(migration_files)
                    total_migrations += len(migration_files)

        # Alembic migrations
        alembic_dirs = list(root.rglob("alembic"))
        for alembic_dir in alembic_dirs:
            versions_dir = alembic_dir / "versions"
            if versions_dir.exists():
                py_files = list(versions_dir.glob("*.py"))
                migration_files = [f.name for f in py_files if f.name != "__init__.py"]
                if migration_files:
                    rel_path = str(alembic_dir.relative_to(root))
                    frameworks["Alembic"] = {
                        "location": rel_path,
                        "migrations": migration_files,
                    }
                    total_migrations += len(migration_files)

        # Check for Tortoise ORM migrations
        tortoise_dirs = list(root.rglob("aerich_migrations"))
        for tortoise_dir in tortoise_dirs:
            py_files = list(tortoise_dir.glob("*.sql"))
            if py_files:
                rel_path = str(tortoise_dir.relative_to(root))
                migration_files = [f.name for f in py_files]
                frameworks["Tortoise ORM"] = {
                    "location": rel_path,
                    "migrations": migration_files,
                }
                total_migrations += len(migration_files)

        return {
            "frameworks": frameworks,
            "total_migrations": total_migrations,
        }

    def _check_django_dependencies(self, root: Path, location: str) -> bool:
        """Check if Django migrations have dependency information."""
        mig_dir = root / location
        if not mig_dir.exists():
            return False

        py_files = list(mig_dir.glob("*.py"))
        for py_file in py_files:
            if py_file.name == "__init__.py":
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "dependencies" in content and "[" in content:
                    return True
            except (OSError, UnicodeDecodeError):
                continue

        return False

    def _check_alembic_downgrades(self, root: Path, location: str) -> int:
        """Check how many Alembic versions have downgrade functions."""
        versions_dir = root / location / "versions"
        if not versions_dir.exists():
            return 0

        with_downgrade = 0
        py_files = list(versions_dir.glob("*.py"))

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "def downgrade()" in content or "def downgrade():" in content:
                    with_downgrade += 1
            except (OSError, UnicodeDecodeError):
                continue

        return with_downgrade

    def _check_migration_issues(self, root: Path, migrations: Dict) -> List[str]:
        """Check for common migration issues."""
        issues = []

        # Check for migration files without corresponding reverse
        if "Alembic" in migrations["frameworks"]:
            alembic_info = migrations["frameworks"]["Alembic"]
            alembic_dir = root / alembic_info["location"]
            versions_dir = alembic_dir / "versions"

            if versions_dir.exists():
                for py_file in versions_dir.glob("*.py"):
                    try:
                        content = py_file.read_text(encoding="utf-8", errors="ignore")
                        if "def upgrade()" in content and "def downgrade()" not in content:
                            if "pass" not in content.split("def downgrade()")[1].split(
                                "\n"
                            )[0]:
                                issues.append(
                                    f"Missing downgrade path in {py_file.name}"
                                )
                    except (OSError, UnicodeDecodeError, IndexError):
                        continue

        return issues
