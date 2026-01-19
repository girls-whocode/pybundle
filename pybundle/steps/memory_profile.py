"""
Memory profiling with tracemalloc - Milestone 3 (v1.4.0)
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import StepResult
from ..context import BundleContext


@dataclass
class MemoryProfileStep:
    """
    Memory profiling using tracemalloc to identify memory-consuming operations.
    
    Outputs:
    - logs/62_memory_profile.txt: Top memory-consuming functions and allocations
    """
    
    name: str = "memory_profile"
    
    def run(self, ctx: BundleContext) -> StepResult:
        start = time.time()
        
        if ctx.options.no_profile or not ctx.options.profile_memory:
            return StepResult(self.name, "SKIP", 0, "memory profiling not enabled")
        
        # Require pytest for memory profiling
        if not ctx.tools.pytest:
            return StepResult(self.name, "SKIP", 0, "pytest not found")
        
        tests_dir = ctx.root / "tests"
        if not tests_dir.is_dir():
            return StepResult(self.name, "SKIP", 0, "no tests/ directory")
        
        ctx.emit("  Running memory profiling on test suite")
        
        # Create a temporary script to run pytest with tracemalloc
        profile_script = self._create_profile_script(ctx.root)
        
        try:
            # Run the profiling script
            result = subprocess.run(
                [str(ctx.tools.python), str(profile_script)],
                cwd=ctx.root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Write output
            output_file = ctx.workdir / "logs" / "62_memory_profile.txt"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with output_file.open("w") as f:
                f.write("=" * 70 + "\n")
                f.write("MEMORY PROFILING (tracemalloc)\n")
                f.write("=" * 70 + "\n\n")
                
                if result.returncode == 0:
                    f.write(result.stdout)
                    if result.stderr:
                        f.write("\n\nTest output:\n")
                        f.write(result.stderr)
                else:
                    f.write("Memory profiling failed\n\n")
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                    f.write("\n\nSTDERR:\n")
                    f.write(result.stderr)
            
            elapsed = int((time.time() - start) * 1000)
            if result.returncode == 0:
                return StepResult(self.name, "OK", elapsed)
            else:
                return StepResult(self.name, "FAIL", elapsed, f"exit {result.returncode}")
                
        except subprocess.TimeoutExpired:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, "timeout")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return StepResult(self.name, "FAIL", elapsed, str(e))
        finally:
            # Clean up temporary script
            if profile_script.exists():
                profile_script.unlink()
    
    def _create_profile_script(self, root: Path) -> Path:
        """Create a temporary Python script that runs pytest with tracemalloc"""
        script_path = root / ".pybundle_memory_profile.py"
        
        script_content = '''"""Temporary memory profiling script for pybundle"""
import tracemalloc
import sys
import pytest

def format_size(size_bytes):
    """Format bytes as human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

# Start tracing
tracemalloc.start()

# Record initial snapshot
snapshot1 = tracemalloc.take_snapshot()

# Run pytest
exit_code = pytest.main(["-q"])

# Take final snapshot
snapshot2 = tracemalloc.take_snapshot()

# Get traced memory
current, peak = tracemalloc.get_traced_memory()

# Stop tracing
tracemalloc.stop()

# Analyze differences
print("=" * 70)
print("MEMORY ALLOCATION SUMMARY")
print("=" * 70)
print()
print(f"Peak memory usage: {format_size(peak)}")
print()

# Top allocations
top_stats = snapshot2.compare_to(snapshot1, 'lineno')

print("TOP 30 MEMORY ALLOCATIONS (by increase):")
print("-" * 70)
print(f"{'Size':<12} {'Count':<8} {'Location'}")
print("-" * 70)

for stat in top_stats[:30]:
    print(f"{format_size(stat.size):<12} {stat.count:<8} {stat.traceback}")

# Top by current size
print()
print("=" * 70)
print("TOP 30 MEMORY CONSUMERS (by total size):")
print("-" * 70)
print(f"{'Size':<12} {'Count':<8} {'Location'}")
print("-" * 70)

current_stats = snapshot2.statistics('lineno')
for stat in current_stats[:30]:
    print(f"{format_size(stat.size):<12} {stat.count:<8} {stat.traceback}")

print()
print("=" * 70)
print("RECOMMENDATIONS:")
print("- Review functions with large memory allocations")
print("- Check for memory leaks in repeatedly allocated objects")
print("- Consider using generators for large data processing")
print("=" * 70)

sys.exit(exit_code)
'''
        
        with script_path.open("w") as f:
            f.write(script_content)
        
        return script_path
