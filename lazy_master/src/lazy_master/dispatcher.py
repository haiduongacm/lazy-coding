"""lazy-master dispatcher - Task parsing and dispatch profiles.

Mirrors firstmate AGENTS.md section 7: task lifecycle and intake.
"""

import re
from typing import Any


def parse_request(text: str) -> list[dict[str, Any]]:
    """Parse user request into task list.

    Mirrors firstmate's intake: classify deliverable as ship or scout.
    """
    if not text or not text.strip():
        return [{"description": text, "type": "ship", "priority": "normal"}]

    tasks = []
    # Split on common separators
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
