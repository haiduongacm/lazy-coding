"""Definitive empty state responses."""


def empty_response(item_type="items"):
    """Create a definitive empty state response.

    Args:
        item_type: Type of items (e.g., 'results', 'tasks')

    Returns:
        Empty state dict
    """
    return {
        "total": 0,
        f"{item_type}": [],
        "message": f"No {item_type} found",
    }
