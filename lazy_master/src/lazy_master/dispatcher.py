"""lazy-master dispatcher - Task parsing and dispatch profiles.

Mirrors lazy-coding AGENTS.md section 7: task lifecycle and intake.
"""

import re
from typing import Any
from pathlib import Path
import os


def parse_request(text: str) -> list[dict[str, Any]]:
    """Parse user request into task list.

    Mirrors lazy-master's intake: classify deliverable as ship or scout.
    """
    if not text or not text.strip():
        return [{"description": text, "type": "ship", "priority": "normal"}]

    tasks = []
    parts = re.split(r'\s+(?:and|then|also)\s+|\n+', text.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        task_type = detect_task_type(part)
        priority = detect_priority(part)

        tasks.append({
            "description": part,
            "type": task_type,
            "priority": priority,
        })

    return tasks if tasks else [{"description": text, "type": "ship", "priority": "normal"}]


def detect_task_type(description: str) -> str:
    """Detect task type from description.

    Ship: produces a project change through selected delivery mode.
    Scout: produces knowledge, never a PR.
    """
    desc_lower = description.lower()

    scout_keywords = ["investigate", "research", "analyze", "study", "explore",
                      "audit", "review", "diagnose", "reproduce", "plan"]
    for keyword in scout_keywords:
        if keyword in desc_lower:
            return "scout"

    return "ship"


def detect_priority(description: str) -> str:
    """Detect priority from description.

    High: urgent, critical, hotfix, ASAP, blocker.
    Low: nice to have, low priority, cleanup, cosmetic.
    """
    desc_lower = description.lower()

    high_keywords = ["urgent", "critical", "hotfix", "asap", "blocker",
                     "emergency", "p0", "p1", "production down"]
    for keyword in high_keywords:
        if keyword in desc_lower:
            return "high"

    low_keywords = ["nice to have", "low priority", "cleanup", "cosmetic",
                    "minor", "polish", "cosmetic", "p3", "p4"]
    for keyword in low_keywords:
        if keyword in desc_lower:
            return "low"

    return "normal"


def resolve_delivery_mode(project_name: str | None = None,
                          description: str = "",
                          project_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve delivery mode for a task.

    Mirrors lazy-master: resolve every ship task's concrete delivery mode and
    yolo merge posture at intake.

    Returns:
        Dict with mode, yolo, and reason
    """
    # Check if project has explicit mode
    if project_registry and project_name and project_name in project_registry:
        entry = project_registry[project_name]
        mode = entry.get("mode", "no-mistakes")
        yolo = entry.get("yolo", "off")
        return {
            "mode": mode,
            "yolo": yolo,
            "reason": f"project_registry:{project_name}",
        }

    # Check if task is internal-only tooling
    desc_lower = description.lower()
    internal_keywords = ["internal", "tooling", "automation", "ci", "cd",
                         "workflow", "process", "contributor"]
    is_internal = any(kw in desc_lower for kw in internal_keywords)

    if is_internal:
        return {
            "mode": "direct-PR",
            "yolo": "off",
            "reason": "internal_tooling",
        }

    # Default: no-mistakes with yolo off
    return {
        "mode": "no-mistakes",
        "yolo": "off",
        "reason": "default",
    }


def resolve_project(text: str, projects: list[str] | None = None) -> str | None:
    """Resolve project from request text.

    Mirrors lazy-master: resolve the project independently for every request.
    An explicit project wins, a clear follow-up inherits its referent.
    """
    if not projects:
        return None

    text_lower = text.lower()

    # Check for explicit project mention
    for project in projects:
        if project.lower() in text_lower:
            return project

    # Check for partial matches
    for project in projects:
        # Simple word boundary match
        pattern = r'\b' + re.escape(project.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return project

    return None
