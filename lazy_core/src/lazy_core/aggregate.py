"""aggregate - Pre-computed aggregates.

Mirrors AXI principle #4: include aggregated counts and statuses.
"""

from typing import Any


def aggregate(items: list, key: str | None = None) -> dict:
    """Aggregate items into counts.

    Args:
        items: List of items to aggregate
        key: Optional key to extract from dict items

    Returns:
        Dict with 'total' and per-value counts
    """
    result: dict[str, Any] = {"total": len(items)}

    for item in items:
        if key and isinstance(item, dict):
            val = str(item.get(key, "unknown"))
        else:
            val = str(item)

        if val in result:
            result[val] += 1
        else:
            result[val] = 1

    return result
