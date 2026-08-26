"""lazy-master project_mode - Project delivery posture.

Mirrors firstmate fm-project-mode.sh: resolve registered delivery posture
from data/projects.md registry.

Key concepts from firstmate:
- Mode: no-mistakes, direct-PR, local-only
- Yolo: on (auto-merge green), off (captain approves every merge)
- Project registry in data/projects.md
- Present working directory detection
"""

import os
import re
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


# Valid delivery modes
VALID_MODES = ("no-mistakes", "direct-PR", "local-only", "no-mistakes-prod-only")


class ProjectMode:
    """Project delivery posture.

    Mirrors firstmate:
    - no-mistakes: full pipeline -> PR -> configured merge authority
    - direct-PR: push + PR via gh-axi, no pipeline
    - local-only: local branch, no remote/PR, guarded local merge
    """

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or os.path.expanduser("~/.lazy-coding/data"))
        self.projects_file = self.data_dir / "projects.md"

    def resolve(self, project_name: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
        """Resolve project's registered delivery posture.

        Returns mode and yolo merge posture.
        """
        if registry and project_name in registry:
            entry = registry[project_name]
            mode = entry.get("mode", "no-mistakes")
            yolo = entry.get("yolo", "off")

            # Validate mode
            if mode not in VALID_MODES:
                return {
                    "mode": "no-mistakes",
                    "yolo": "off",
                    "warning": f"Unknown mode '{mode}', defaulting to no-mistakes",
                }

            # Map conditional policy to most rigorous leg
            if mode == "no-mistakes-prod-only":
                mode = "no-mistakes"

            return {"mode": mode, "yolo": yolo}

        # Check projects.md registry
        if self.projects_file.exists():
            entry = self._parse_registry(project_name)
            if entry:
                return entry

        # Default: no-mistakes with yolo off
        return {
            "mode": "no-mistakes",
            "yolo": "off",
            "warning": f"Project '{project_name}' not in registry",
        }

    def _parse_registry(self, project_name: str) -> dict[str, Any] | None:
        """Parse projects.md for project entry."""
        try:
            with open(self.projects_file, "r") as f:
                content = f.read()

            # Simple markdown parsing for project entries
            # Look for lines like: - project-name: mode=no-mistakes yolo=off
            for line in content.split("\n"):
                if project_name in line:
                    mode_match = re.search(r'mode=(\S+)', line)
                    yolo_match = re.search(r'yolo=(\S+)', line)

                    mode = mode_match.group(1) if mode_match else "no-mistakes"
                    yolo = yolo_match.group(1) if yolo_match else "off"

                    if mode not in VALID_MODES:
                        mode = "no-mistakes"

                    if mode == "no-mistakes-prod-only":
                        mode = "no-mistakes"

                    return {"mode": mode, "yolo": yolo}
        except Exception:
            pass

        return None

    def register(self, project_name: str, mode: str = "no-mistakes",
                 yolo: str = "off") -> dict[str, Any]:
        """Register project in registry.

        Mirrors firstmate: updates data/projects.md.
        """
        if mode not in VALID_MODES:
            return {
                "error": True,
                "code": "INVALID_MODE",
                "message": f"Invalid mode '{mode}'. Valid: {', '.join(VALID_MODES)}",
            }

        if yolo not in ("on", "off"):
            return {
                "error": True,
                "code": "INVALID_YOLO",
                "message": "yolo must be 'on' or 'off'",
            }

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Read existing content
        content = ""
        if self.projects_file.exists():
            with open(self.projects_file, "r") as f:
                content = f.read()

        # Update or add entry
        entry_line = f"- {project_name}: mode={mode} yolo={yolo}\n"

        # Check if project already exists
        lines = content.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if project_name in line and "mode=" in line:
                lines[i] = entry_line.strip()
                updated = True
                break

        if not updated:
            lines.append(entry_line.strip())

        # Write back
        with open(self.projects_file, "w") as f:
            f.write("\n".join(lines))

        return {
            "success": True,
            "project": project_name,
            "mode": mode,
            "yolo": yolo,
        }

    def list_projects(self) -> list[dict[str, Any]]:
        """List all registered projects."""
        if not self.projects_file.exists():
            return []

        projects = []
        try:
            with open(self.projects_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or not line.startswith("-"):
                        continue

                    # Parse: - project-name: mode=no-mistakes yolo=off
                    match = re.match(r'-\s+(\S+):\s+mode=(\S+)\s+yolo=(\S+)', line)
                    if match:
                        projects.append({
                            "name": match.group(1),
                            "mode": match.group(2),
                            "yolo": match.group(3),
                        })
        except Exception:
            pass

        return projects

    def detect_project(self, path: str | None = None) -> str | None:
        """Detect project name from path.

        Mirrors firstmate: present working directory detection.
        """
        if path is None:
            path = os.getcwd()

        # Try to find project name from git remote
        try:
            import subprocess
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract project name from URL
                # https://github.com/user/project.git -> project
                # git@github.com:user/project.git -> project
                parts = url.rstrip("/").split("/")
                if parts:
                    name = parts[-1]
                    if name.endswith(".git"):
                        name = name[:-4]
                    return name
        except Exception:
            pass

        # Fallback to directory name
        return os.path.basename(path)
