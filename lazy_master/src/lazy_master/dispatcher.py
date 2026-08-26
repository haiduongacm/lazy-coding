"""Task dispatcher."""

import re


def parse_request(request: str) -> list:
    """Parse a user request into tasks.

    Args:
        request: User request string

    Returns:
        List of task dicts
    """
    tasks = []

    # Split on 'and', 'và', '&'
    parts = re.split(r"\s+(?:and|và|&)\s+", request, flags=re.IGNORECASE)

    for part in parts:
        trimmed = part.strip()
        if not trimmed:
            continue

        task = {
            "id": f"task-{id(trimmed) % 100000}",
            "description": trimmed,
            "type": detect_task_type(trimmed),
            "priority": detect_priority(trimmed),
        }
        tasks.append(task)

    if not tasks:
        tasks.append({
            "id": f"task-{id(request) % 100000}",
            "description": request,
            "type": "ship",
            "priority": "normal",
        })

    return tasks


def detect_task_type(description: str) -> str:
    """Detect task type from description."""
    lower = description.lower()
    if any(kw in lower for kw in ["investigate", "research", "analyze"]):
        return "scout"
    return "ship"


def detect_priority(description: str) -> str:
    """Detect task priority from description."""
    lower = description.lower()
    if any(kw in lower for kw in ["urgent", "critical", "hotfix"]):
        return "high"
    if any(kw in lower for kw in ["low priority", "nice to have"]):
        return "low"
    return "normal"
