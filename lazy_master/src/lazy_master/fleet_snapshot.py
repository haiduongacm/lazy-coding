"""lazy-master fleet_snapshot - Read-only structured fleet snapshot.

Mirrors firstmate fm-fleet-snapshot.sh: read-only structured snapshot
of the firstmate fleet.

Key concepts from firstmate:
- Schema versioning for stable output
- Tasks from state/<id>.meta files
- Backlog from data/backlog.md
- Git status for each project
- PR status for each project
"""

import os
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone
import subprocess


class FleetSnapshot:
    """Read-only structured fleet snapshot.

    Mirrors firstmate fm-fleet-snapshot.sh:
    - schema: stable schema id
    - generated: UTC observation time
    - tasks[]: one row per state/<id>.meta
    - backlog: {path, present, records[]}
    """

    def __init__(self, state_dir: str | None = None, data_dir: str | None = None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.data_dir = Path(data_dir or os.path.expanduser("~/.lazy-coding/data"))

    def generate(self, projects_dir: str | None = None) -> dict[str, Any]:
        """Generate fleet snapshot.

        Args:
            projects_dir: Directory containing project clones

        Returns:
            Structured fleet snapshot
        """
        now = datetime.now(timezone.utc).isoformat()

        # Collect tasks from state files
        tasks = self._collect_tasks()

        # Collect backlog
        backlog = self._collect_backlog()

        # Collect project statuses
        projects = self._collect_projects(projects_dir)

        return {
            "schema": "lazy-coding-fleet-snapshot.v1",
            "generated": now,
            "tasks": tasks,
            "backlog": backlog,
            "projects": projects,
            "summary": {
                "total_tasks": len(tasks),
                "active_tasks": sum(1 for t in tasks if t.get("status") == "working"),
                "total_projects": len(projects),
            },
        }

    def _collect_tasks(self) -> list[dict[str, Any]]:
        """Collect task metadata from state files."""
        tasks = []
        if not self.state_dir.exists():
            return tasks

        for meta_file in self.state_dir.glob("*.meta"):
            if not meta_file.is_file():
                continue

            task_id = meta_file.stem
            try:
                with open(meta_file, "r") as f:
                    meta = {}
                    for line in f:
                        if "=" in line:
                            key, _, value = line.partition("=")
                            meta[key.strip()] = value.strip()

                # Read status tail
                status_file = self.state_dir / f"{task_id}.status"
                status_tail = []
                if status_file.exists():
                    with open(status_file, "r") as f:
                        lines = f.readlines()
                        status_tail = [l.strip() for l in lines[-5:]]

                tasks.append({
                    "id": task_id,
                    "meta": meta,
                    "status_tail": status_tail,
                    "has_worktree": (self.state_dir / f"{task_id}.worktree").exists(),
                    "has_turn_ended": (self.state_dir / f"{task_id}.turn-ended").exists(),
                })
            except Exception:
                pass

        return tasks

    def _collect_backlog(self) -> dict[str, Any]:
        """Collect backlog from data/backlog.md."""
        backlog_file = self.data_dir / "backlog.md"
        if not backlog_file.exists():
            return {
                "present": False,
                "records": [],
            }

        try:
            with open(backlog_file, "r") as f:
                content = f.read()
            return {
                "present": True,
                "records": self._parse_backlog(content),
            }
        except Exception:
            return {
                "present": True,
                "records": [],
                "error": "Failed to read backlog",
            }

    def _parse_backlog(self, content: str) -> list[dict[str, Any]]:
        """Parse backlog markdown into records."""
        records = []
        current = None

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Parse task items (e.g., "- [ ] Task description")
            if line.startswith("- ["):
                if current:
                    records.append(current)
                done = line.startswith("- [x]")
                current = {
                    "description": line[4:].strip() if done else line[4:].strip(),
                    "done": done,
                }
            elif current:
                current["description"] = current.get("description", "") + " " + line

        if current:
            records.append(current)

        return records

    def _collect_projects(self, projects_dir: str | None = None) -> list[dict[str, Any]]:
        """Collect project statuses."""
        projects = []
        if not projects_dir:
            return projects

        projects_path = Path(projects_dir)
        if not projects_path.exists():
            return projects

        for project_dir in projects_path.iterdir():
            if not project_dir.is_dir():
                continue

            # Check if it's a git repo
            git_dir = project_dir / ".git"
            if not git_dir.exists():
                continue

            project_info = {
                "name": project_dir.name,
                "path": str(project_dir),
            }

            # Get git status
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(project_dir),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                project_info["dirty"] = bool(result.stdout.strip())
                project_info["modified_files"] = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
            except Exception:
                project_info["dirty"] = None

            # Get current branch
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(project_dir),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                project_info["branch"] = result.stdout.strip() if result.returncode == 0 else None
            except Exception:
                project_info["branch"] = None

            projects.append(project_info)

        return projects
