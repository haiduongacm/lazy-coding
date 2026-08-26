"""success - Success response helper."""


def success_response(data: dict | None = None, **kwargs) -> dict:
    """Generate success response.

    Args:
        data: Optional data dict
        **kwargs: Additional key-value pairs

    Returns:
        Dict with success=True and optional data
    """
    result = {"success": True}
    if data:
        result["data"] = data
    result.update(kwargs)
    return result
