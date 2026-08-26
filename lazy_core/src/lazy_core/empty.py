"""empty - Definitive empty states.

Mirrors AXI principle #5: explicit "0 results" rather than ambiguous empty output.
"""

from typing import Any


def empty_response(item_type: str = "items") -> dict[str, Any]:
    """Generate definitive empty response.

    Args:
        item_type: Name of the item type (e.g., "tasks", "items")

    Returns:
        Dict with total=0, empty list, and clear message
    """
    return {
        "total": 0,
        item_type: [],
        "message": f"No {item_type} found",
    }
