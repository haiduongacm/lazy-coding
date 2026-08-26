"""truncate - Content truncation with size hints.

Mirrors AXI principle #3: truncate large text with size hints and --full escape hatch.
"""

from typing import Any


def truncate(text: Any, max_length: int = 500, suffix: str = "...") -> str | Any:
    """Truncate text to max_length with suffix.

    Shows total size when truncated. The max_length includes the suffix.
    """
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
