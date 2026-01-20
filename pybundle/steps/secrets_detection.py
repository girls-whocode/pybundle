"""
Step: Enhanced Secrets Detection
Advanced secrets detection using entropy analysis and patterns.
"""

import re
import math
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class SecretsDetectionStep(Step):
    """Detect secrets in codebase using entropy and regex patterns."""

    name = "secrets detection"

    # Common secret patterns
    SECRET_PATTERNS = {
        "AWS_KEY_ID": r"AKIA[0-9A-Z]{16}",
        "AWS_SECRET": r"aws_secret_access_key[\"']?\s*[:=]\s*[\"']([^\"'\n]+)[\"']",
        "GITHUB_TOKEN": r"gh[pousr]_[A-Za-z0-9_]{36,255}",
        "PRIVATE_KEY": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
        "API_KEY": r"api[_-]?key[\"']?\s*[:=]\s*[\"']([^\"'\n]+)[\"']",
        "DATABASE_PASSWORD": r"(?:password|passwd)[\"']?\s*[:=]\s*[\"']([^\"'\n]+)[\"']",
        "JWT_SECRET": r"jwt[_-]?secret[\"']?\s*[:=]\s*[\"']([^\"'\n]+)[\"']",
        "SLACK_TOKEN": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}",
        "STRIPE_KEY": r"sk_live_[0-9a-zA-Z]{24}",
    }

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Detect secrets in codebase."""
        import time

        start = time.time()

        root = ctx.root

        # Scan for secrets
        secrets_found = self._scan_for_secrets(root)

        # Generate report
        lines = [
            "=" * 80,
            "SECRETS DETECTION REPORT",
            "=" * 80,
            "",
        ]

        if secrets_found["matches"]:
            lines.append("⚠ POTENTIAL SECRETS DETECTED (pattern-based)")
            lines.append("")

            for file_path, details in secrets_found["matches"].items():
                lines.append(f"File: {file_path}")

                for issue in details:
                    lines.append(f"  Line {issue['line']}: {issue['type']}")
                    if issue.get("context"):
                        context_line = issue["context"].strip()
                        if len(context_line) > 70:
                            context_line = context_line[:67] + "..."
                        lines.append(f"    Context: {context_line}")
                    if issue.get("entropy"):
                        lines.append(f"    Entropy: {issue['entropy']:.2f}")

                lines.append("")

            lines.append(f"Total files with potential secrets: {len(secrets_found['matches'])}")
            lines.append(f"Total potential secrets: {secrets_found['total_matches']}")
        else:
            lines.append("✓ No pattern-based secrets detected")
            lines.append("  (API keys, AWS keys, GitHub tokens, private keys, etc.)")

        lines.extend(
            [
                "",
                "=" * 80,
                "ENTROPY ANALYSIS",
                "=" * 80,
                "",
            ]
        )

        # High entropy strings analysis (LIMITED OUTPUT)
        high_entropy = secrets_found.get("high_entropy", [])
        if high_entropy:
            lines.append(f"Found {len(high_entropy)} high-entropy strings (may include hashes, tokens, UUIDs):")
            lines.append("")
            lines.append("NOTE: High-entropy detection produces many false positives.")
            lines.append("      Focus on pattern-based findings above for actual secrets.")
            lines.append("")

            # Show only top 10 highest-entropy, not all
            display_count = min(10, len(high_entropy))
            for item in high_entropy[:display_count]:
                lines.append(f"  File: {item['file']}")
                lines.append(f"  Line: {item['line']}")
                lines.append(f"  Entropy: {item['entropy']:.3f}")
                if item.get("context"):
                    context = item["context"].strip()
                    if len(context) > 60:
                        context = context[:57] + "..."
                    lines.append(f"  Value preview: {context}")
                lines.append("")

            if len(high_entropy) > display_count:
                lines.append(f"  ... and {len(high_entropy) - display_count} more (suppressed for readability)")
                lines.append(f"      Run with --deep-scan to see full entropy analysis")
                lines.append("")

        else:
            lines.append("✓ No high-entropy strings detected")
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

        if secrets_found["matches"] or high_entropy:
            lines.append("  - Review and rotate any exposed secrets immediately")
            lines.append("  - Use a secrets manager (AWS Secrets Manager, HashiCorp Vault)")
            lines.append("  - Configure git hooks to prevent committing secrets")
            lines.append("  - Use .gitignore to exclude .env and secrets files")
            lines.append("  - Consider using detect-secrets or similar tools in CI/CD")

        else:
            lines.append("  - ✓ Good security practice: no obvious secrets detected")
            lines.append("  - Continue to use secrets management best practices")
            lines.append("  - Store sensitive data in .env or secrets manager")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "121_secrets_advanced.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _scan_for_secrets(self, root: Path) -> Dict:
        """Scan files for secrets using patterns and entropy analysis."""
        matches = {}
        high_entropy = []
        total_matches = 0

        python_files = list(root.rglob("*.py")) + list(root.rglob("*.json")) + list(
            root.rglob("*.yaml")
        ) + list(root.rglob("*.yml"))

        for py_file in python_files:
            # Skip venv, cache, and dependency directories (PROJECT SCOPE ONLY)
            if any(
                part in py_file.parts
                for part in [
                    "venv", ".venv", "env", "__pycache__", "site-packages",
                    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".freeze-venv",
                    "node_modules", "dist", "build", "target"
                ]
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(root))

                file_matches = []

                # Check against secret patterns
                for line_num, line in enumerate(source.split("\n"), 1):
                    for secret_type, pattern in self.SECRET_PATTERNS.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            file_matches.append(
                                {
                                    "line": line_num,
                                    "type": secret_type,
                                    "context": line,
                                }
                            )
                            total_matches += 1

                # Check entropy of quoted strings
                string_pattern = r'["\']([A-Za-z0-9_\-\.]{20,})["\']'
                for line_num, line in enumerate(source.split("\n"), 1):
                    for match in re.finditer(string_pattern, line):
                        string_val = match.group(1)
                        entropy = self._calculate_entropy(string_val)

                        # Flag high entropy strings (likely encrypted or random)
                        if entropy > 4.0:
                            high_entropy.append(
                                {
                                    "file": rel_path,
                                    "line": line_num,
                                    "entropy": entropy,
                                    "context": string_val,
                                }
                            )

                if file_matches:
                    matches[rel_path] = file_matches

            except (OSError, UnicodeDecodeError):
                continue

        # Sort high entropy by entropy score
        high_entropy.sort(key=lambda x: x["entropy"], reverse=True)

        return {
            "matches": matches,
            "total_matches": total_matches,
            "high_entropy": high_entropy,
        }

    def _calculate_entropy(self, s: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not s:
            return 0.0

        entropy = 0.0
        for byte in set(s):
            freq = s.count(byte) / len(s)
            entropy -= freq * math.log2(freq)

        return entropy
