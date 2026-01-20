"""
Step: Blocking Call Detection
Detect synchronous/blocking calls in async functions.
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .base import Step, StepResult


class BlockingCallDetectionStep(Step):
    """Detect blocking calls within async functions."""

    name = "blocking call detection"

    # Common blocking calls to detect
    BLOCKING_CALLS = {
        # Time
        "time.sleep": "Time",
        "time.time": "Time",  # Can be called in tight loops
        # Network
        "requests.get": "Network",
        "requests.post": "Network",
        "requests.put": "Network",
        "requests.delete": "Network",
        "requests.request": "Network",
        "urllib.request.urlopen": "Network",
        # I/O
        "open": "I/O",
        "Path.read_text": "I/O",
        "Path.write_text": "I/O",
        "json.load": "I/O",
        "json.dump": "I/O",
        "pickle.load": "I/O",
        "pickle.dump": "I/O",
        # Database
        "query": "Database",
        "execute": "Database",
        "fetch": "Database",
        "commit": "Database",
        "rollback": "Database",
        # Subprocess
        "subprocess.run": "Subprocess",
        "subprocess.call": "Subprocess",
        "subprocess.Popen": "Subprocess",
        "os.system": "Subprocess",
    }

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Detect blocking calls in async functions."""
        import time

        start = time.time()

        root = ctx.root

        # Find blocking calls in async context
        blocking_issues = self._find_blocking_calls(root)

        # Generate report
        lines = [
            "=" * 80,
            "BLOCKING CALL DETECTION REPORT",
            "=" * 80,
            "",
        ]

        # Summary
        lines.extend(
            [
                "SUMMARY",
                "=" * 80,
                "",
                f"Async functions analyzed: {blocking_issues['async_functions_count']}",
                f"Functions with blocking calls: {len(blocking_issues['affected_functions'])}",
                f"Total blocking calls detected: {blocking_issues['total_issues']}",
                "",
            ]
        )

        if not blocking_issues["affected_functions"]:
            lines.extend(
                [
                    "✓ No blocking calls detected in async functions",
                    "",
                    "Great! Your async code appears to be non-blocking.",
                    "",
                ]
            )
        else:
            # Detailed breakdown
            lines.extend(
                [
                    "BLOCKING CALLS BY TYPE",
                    "=" * 80,
                    "",
                ]
            )

            # Count by category
            category_counts: Dict[str, int] = {}
            for func_issues in blocking_issues["affected_functions"].values():
                for issue in func_issues:
                    category = issue["category"]
                    category_counts[category] = category_counts.get(category, 0) + 1

            for category in sorted(category_counts.keys()):
                lines.append(f"{category}: {category_counts[category]} calls")
            lines.append("")

            # Detailed issues
            lines.append("ISSUES BY FUNCTION")
            lines.append("-" * 80)
            lines.append("")

            for func_key in sorted(blocking_issues["affected_functions"].keys()):
                issues = blocking_issues["affected_functions"][func_key]
                file_path, func_name, line_no = func_key.rsplit(":", 2)
                line_no = int(line_no)

                lines.append(f"Function: {func_name}")
                lines.append(f"Location: {file_path}:{line_no}")
                lines.append(f"Blocking calls: {len(issues)}")
                lines.append("")

                for issue in issues[:10]:
                    lines.append(
                        f"  Line {issue['line']}: {issue['call_name']} ({issue['category']})"
                    )
                    if issue.get("context"):
                        context_line = issue["context"].strip()
                        if len(context_line) > 70:
                            context_line = context_line[:67] + "..."
                        lines.append(f"    > {context_line}")

                if len(issues) > 10:
                    lines.append(f"  ... and {len(issues) - 10} more")

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

        if blocking_issues["affected_functions"]:
            lines.append("To fix blocking calls in async functions:")
            lines.append("")
            lines.append("  1. NETWORK (requests → aiohttp/httpx)")
            lines.append("     Before:  response = requests.get(url)")
            lines.append("     After:   response = await client.get(url)")
            lines.append("")
            lines.append("  2. TIME (time.sleep → asyncio.sleep)")
            lines.append("     Before:  time.sleep(1)")
            lines.append("     After:   await asyncio.sleep(1)")
            lines.append("")
            lines.append("  3. DATABASE (sync drivers → async drivers)")
            lines.append("     Before:  results = session.query(...).all()")
            lines.append("     After:   results = await session.execute(...)")
            lines.append("")
            lines.append("  4. FILE I/O (open → aiofiles)")
            lines.append("     Before:  with open(file) as f: data = f.read()")
            lines.append("     After:   async with aiofiles.open(file) as f: data = await f.read()")
            lines.append("")
            lines.append("  5. SUBPROCESS (subprocess → asyncio.create_subprocess_exec)")
            lines.append(
                "     Before:  result = subprocess.run(['cmd'], capture_output=True)"
            )
            lines.append(
                "     After:   proc = await asyncio.create_subprocess_exec('cmd')"
            )
            lines.append("")

        else:
            lines.append("  ✓ Great: No blocking calls detected in async functions")
            lines.append("  - Continue following non-blocking patterns")
            lines.append("  - Use type hints to indicate async functions")
            lines.append("  - Document expected async library usage")

        lines.append("")

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "logs" / "131_async_blocking.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _find_blocking_calls(self, root: Path) -> Dict:
        """Find blocking calls in async functions."""
        affected_functions: Dict[str, List[Dict]] = {}
        async_functions_count = 0

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

                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef):
                        async_functions_count += 1
                        func_name = node.name
                        func_line = node.lineno
                        func_key = f"{rel_path}:{func_name}:{func_line}"

                        # Find blocking calls in this async function
                        issues = self._find_blocking_in_function(
                            node, rel_path, source
                        )

                        if issues:
                            affected_functions[func_key] = issues

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Count total issues
        total_issues = sum(len(v) for v in affected_functions.values())

        return {
            "affected_functions": affected_functions,
            "async_functions_count": async_functions_count,
            "total_issues": total_issues,
        }

    def _find_blocking_in_function(
        self, func_node: ast.AsyncFunctionDef, file_path: str, source: str
    ) -> List[Dict]:
        """Find blocking calls within a single async function."""
        issues = []
        source_lines = source.split("\n")

        for call_node in ast.walk(func_node):
            if isinstance(call_node, ast.Call):
                call_name = self._get_call_name(call_node)

                if call_name:
                    # Check if this is a blocking call
                    for blocking_pattern, category in self.BLOCKING_CALLS.items():
                        if blocking_pattern in call_name or call_name == blocking_pattern.split(
                            "."
                        )[
                            -1
                        ]:
                            context = source_lines[call_node.lineno - 1]

                            issues.append(
                                {
                                    "line": call_node.lineno,
                                    "call_name": call_name,
                                    "category": category,
                                    "context": context,
                                }
                            )
                            break

        return issues

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))
        return None
