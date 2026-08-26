"""Content truncation utilities."""


def truncate(text, max_length=500, suffix="..."):
    """Truncate text to max length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    truncated = text[: max_length - len(suffix)]
    return truncated + suffix
