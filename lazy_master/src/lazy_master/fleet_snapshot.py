"""lazy-master fleet_snapshot - Read-only structured fleet snapshot.

Mirrors lazy-master's fleet snapshot: read-only structured snapshot
of the lazy-master fleet.

Key concepts from lazy-master:
- Schema versioning for stable output
- Tasks from state/<id>.meta files
- Backlog from data/backlog.md
- Git status for each project
- PR status for each project
- Secondmate summaries
- Main inventory validation
"""

import os
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone
import subprocess


class FleetSnapshot:
    """Read-only structured fleet snapshot.

    Mirrors lazy-master's fleet snapshot:
    - schema: stable schema id
    - generated: UTC observation time
    - tasks[]: one row per state/<id>.meta
    - backlog: {path, present, records[]}
    - secondmate_current: bounded current summaries
    - main_inventory: validity checks
    """

    def __init__(self, state_dir: str | None = None, data_dir: str | None = None,
                 projects_dir: str | None = None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.data_dir = Path(data_dir or os.path.expanduser("~/.lazy-coding/data"))
        self.projects_dir = Path(projects_dir or os.path.expanduser("~/.lazy-coding/projects"))

    def generate(self) -> dict[str, Any]:
        """Generate fleet snapshot."""
        now = datetime.now(timezone.utc).isoformat()

        tasks = self._collect_tasks()
        backlog = self._collect_backlog()
        projects = self._collect_projects()
        secondmates = self._collect_secondmates()
        main_inventory = self._validate_main_inventory(tasks, backlog)

        return {
            "schema": "lazy-coding-fleet-snapshot.v1",
            "generated": now,
            "fm_home": str(self.state_dir.parent),
            "tasks": tasks,
            "backlog": backlog,
            "projects": projects,
            "secondmate_current": secondmates,
            "main_inventory": main_inventory,
            "summary": {
                "total_tasks": len(tasks),
                "active_tasks": sum(1 for t in tasks if t.get("status") == "working"),
                "total_projects": len(projects),
                "total_secondmates": len(secondmates.get("records", [])),
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

                status_file = self.state_dir / f"{task_id}.status"
                status_tail = []
                if status_file.exists():
                    with open(status_file, "r") as f:
                        lines = f.readlines()
                        status_tail = [l.strip() for l in lines[-5:]]

                # Check endpoint existence
                endpoint_exists = False
                backend = meta.get("backend", "tmux")
                window = meta.get("window", "")
                if backend == "tmux" and window:
                    try:
                        result = subprocess.run(
                            ["tmux", "has-session", "-t", window],
                            capture_output=True,
                            timeout=5,
                        )
                        endpoint_exists = result.returncode == 0
                    except Exception:
                        pass

                tasks.append({
                    "id": task_id,
                    "meta": meta,
                    "status_tail": status_tail,
                    "has_worktree": (self.state_dir / f"{task_id}.worktree").exists(),
                    "has_turn_ended": (self.state_dir / f"{task_id}.turn-ended").exists(),
                    "endpoint_exists": endpoint_exists,
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

    def _collect_projects(self) -> list[dict[str, Any]]:
        """Collect project statuses."""
        projects = []
        if not self.projects_dir.exists():
            return projects

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            git_dir = project_dir / ".git"
            if not git_dir.exists():
                continue

            project_info = {
                "name": project_dir.name,
                "path": str(project_dir),
            }

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

    def _collect_secondmates(self) -> dict[str, Any]:
        """Collect lazy-master2 summaries.

        Mirrors lazy-master: bounded current summaries for registered lazy-master2s.
        """
        records = []
        secondmates_file = self.data_dir / "secondmates.md"

        if not secondmates_file.exists():
            return {
                "records": [],
                "total": 0,
                "shown": 0,
                "truncated": False,
            }

        try:
            with open(secondmates_file, "r") as f:
                content = f.read()

            # Parse lazy-master2 entries
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Simple parsing: - name: home=/path/to/home
                match = re.match(r'-\s+(\S+):\s+home=(\S+)', line)
                if match:
                    name = match.group(1)
                    home = match.group(2)
                    home_path = Path(home)

                    if home_path.exists():
                        # Try to get status from home's state
                        state_dir = home_path / "state"
                        if state_dir.exists():
                            meta_files = list(state_dir.glob("*.meta"))
                            records.append({
                                "name": name,
                                "home": home,
                                "active_children": len(meta_files),
                                "status": "active",
                            })
                        else:
                            records.append({
                                "name": name,
                                "home": home,
                                "active_children": 0,
                                "status": "idle",
                            })
                    else:
                        records.append({
                            "name": name,
                            "home": home,
                            "status": "unreachable",
                        })
        except Exception:
            pass

        return {
            "records": records[:20],  # Bounded
            "total": len(records),
            "shown": min(len(records), 20),
            "truncated": len(records) > 20,
        }

    def _validate_main_inventory(self, tasks: list[dict],
                                 backlog: dict) -> dict[str, Any]:
        """Validate main inventory.

        Mirrors lazy-master: orphan structured in-flight ids with no state/<id>.meta,
        and unstructured current backlog rows.
        """
        orphans = []
        for task in tasks:
            meta_file = self.state_dir / f"{task['id']}.meta"
            if not meta_file.exists():
                orphans.append(task['id'])

        unstructured_count = 0
        if backlog.get("present"):
            for record in backlog.get("records", []):
                if not record.get("done") and not record.get("id"):
                    unstructured_count += 1

        return {
            "valid": len(orphans) == 0 and unstructured_count == 0,
            "orphan_in_flight": orphans,
            "unstructured_current_count": unstructured_count,
            "reason": "ok" if len(orphans) == 0 and unstructured_count == 0 else "issues_found",
        }


# Need to import re for lazy-master2 parsing
import re
