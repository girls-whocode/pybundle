"""
Step: Container Image Analysis
Analyze Docker images for size and layer optimization.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Optional

from .base import Step, StepResult


class ContainerImageStep(Step):
    """Analyze Docker images for size and layer information."""

    name = "container image analysis"

    def run(self, ctx: "BundleContext") -> StepResult:  # type: ignore[name-defined]
        """Analyze Docker images from docker-compose or specified images."""
        import time

        start = time.time()

        root = ctx.root

        # Try to get image name from options or docker-compose
        image_name = getattr(ctx.options, "docker_image", None)

        if not image_name:
            # Try to find docker-compose.yml
            compose_files = [
                root / "docker-compose.yml",
                root / "docker-compose.yaml",
            ]

            image_name = None
            for compose_file in compose_files:
                if compose_file.exists():
                    image_name = self._extract_image_from_compose(compose_file)
                    if image_name:
                        break

        if not image_name:
            elapsed = int(time.time() - start)
            return StepResult(
                self.name, "SKIP", elapsed, "No docker image specified or found"
            )

        # Check if Docker is available
        docker_available = self._check_docker()
        if not docker_available:
            elapsed = int(time.time() - start)
            return StepResult(self.name, "SKIP", elapsed, "Docker not available")

        # Generate report
        lines = [
            "=" * 80,
            "CONTAINER IMAGE ANALYSIS",
            "=" * 80,
            "",
            f"Target image: {image_name}",
            "",
        ]

        # Get image info
        image_info = self._inspect_image(image_name)
        if not image_info:
            lines.extend(
                [
                    "⚠ Could not inspect image. Image may not be built or available.",
                    "",
                    "Build the image first with:",
                    f"  docker build -t {image_name} .",
                    "",
                ]
            )
        else:
            # Image details
            lines.extend(
                [
                    "=" * 80,
                    "IMAGE INFORMATION",
                    "=" * 80,
                    "",
                    f"Image ID:       {image_info.get('Id', 'N/A')[:19]}...",
                    f"Created:        {image_info.get('Created', 'N/A')}",
                    f"Architecture:   {image_info.get('Architecture', 'N/A')}",
                    f"OS:             {image_info.get('Os', 'N/A')}",
                    f"Docker Version: {image_info.get('DockerVersion', 'N/A')}",
                    "",
                ]
            )

            # Size information
            size = image_info.get("Size", 0)
            virtual_size = image_info.get("VirtualSize", 0)

            lines.extend(
                [
                    "=" * 80,
                    "SIZE INFORMATION",
                    "=" * 80,
                    "",
                    f"Compressed size:   {self._format_size(size)}",
                    f"Uncompressed size: {self._format_size(virtual_size)}",
                    "",
                ]
            )

            # Layer analysis
            layers = self._get_image_history(image_name)
            if layers:
                lines.extend(
                    [
                        "=" * 80,
                        "LAYER ANALYSIS (top 20 by size)",
                        "=" * 80,
                        "",
                    ]
                )

                # Sort by size descending
                sorted_layers = sorted(
                    layers, key=lambda x: x.get("Size", 0), reverse=True
                )

                total_layer_size = 0
                for i, layer in enumerate(sorted_layers[:20], 1):
                    size = layer.get("Size", 0)
                    total_layer_size += size
                    cmd = layer.get("CreatedBy", "").strip()
                    
                    # Truncate long commands
                    if len(cmd) > 70:
                        cmd = cmd[:67] + "..."

                    size_str = self._format_size(size)
                    lines.append(f"{i:2}. {size_str:12} {cmd}")

                if len(sorted_layers) > 20:
                    lines.append(f"\n... and {len(sorted_layers) - 20} more layers")

                lines.append("")

                # Recommendations for optimization
                lines.extend(
                    [
                        "=" * 80,
                        "OPTIMIZATION RECOMMENDATIONS",
                        "=" * 80,
                        "",
                    ]
                )

                # Check for common issues
                has_large_run = any(
                    layer.get("Size", 0) > 50 * 1024 * 1024 for layer in layers
                )
                layer_count = len(layers)

                if has_large_run:
                    lines.append("  - Large RUN layers detected (>50MB)")
                    lines.append("    Consider combining RUN commands and cleaning up in same layer")

                if layer_count > 30:
                    lines.append(
                        f"  - Many layers detected ({layer_count})"
                    )
                    lines.append("    Consider combining related RUN instructions")

                if total_layer_size > 1024 * 1024 * 1024:
                    size_gb = total_layer_size / (1024 * 1024 * 1024)
                    lines.append(f"  - Large total size ({size_gb:.1f}GB)")
                    lines.append("    Consider using multi-stage builds or base image optimization")

                lines.append("")

        # Recommendations
        if not image_info:
            lines.extend(
                [
                    "=" * 80,
                    "NEXT STEPS",
                    "=" * 80,
                    "",
                    f"1. Build the Docker image:",
                    f"   docker build -t {image_name} .",
                    "",
                    f"2. Re-run pybundle to analyze the built image:",
                    f"   pybundle run analysis --docker-image {image_name}",
                    "",
                ]
            )

        # Write report
        output = "\n".join(lines)
        dest = ctx.workdir / "meta" / "107_container_image.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output, encoding="utf-8")

        elapsed = int(time.time() - start)
        return StepResult(self.name, "OK", elapsed, "")

    def _check_docker(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _extract_image_from_compose(self, compose_file: Path) -> Optional[str]:
        """Extract image name from docker-compose file."""
        try:
            content = compose_file.read_text(encoding="utf-8", errors="ignore")
            # Simple regex to find image references
            match = re.search(r'image:\s*([^\s\n]+)', content)
            if match:
                return match.group(1)
        except (OSError, UnicodeDecodeError):
            pass

        return None

    def _inspect_image(self, image_name: str) -> dict:
        """Use docker inspect to get image information."""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    return data[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return {}

    def _get_image_history(self, image_name: str) -> List[dict]:
        """Get layer history from docker history."""
        layers = []
        try:
            result = subprocess.run(
                ["docker", "history", "--no-trunc", "--human", image_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                import json

                # Try to get JSON format
                result = subprocess.run(
                    ["docker", "history", "--no-trunc", image_name, "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            try:
                                layer = json.loads(line)
                                layers.append(layer)
                            except json.JSONDecodeError:
                                pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return layers

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes into human readable size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024

        return f"{size_bytes:.1f}PB"
