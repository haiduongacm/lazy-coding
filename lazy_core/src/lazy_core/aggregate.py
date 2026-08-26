"""Pre-computed aggregate utilities."""


def aggregate(items, key=None):
    """Compute aggregates from a list of items.

    Args:
        items: List of items
        key: Key to aggregate by (for dicts)

    Returns:
        Aggregate dict with counts
    """
    if not items:
        return {"total": 0}

    counts = {}
    for item in items:
        if key and isinstance(item, dict):
            value = item.get(key, "unknown")
        else:
            value = str(item)

        counts[value] = counts.get(value, 0) + 1

    return {"total": len(items), **counts}
