"""error_response - Structured error responses.

Mirrors AXI principle #6: structured errors on stdout.
"""

from typing import Any


def error_response(code: str, message: str, suggestions: list[str] | str | None = None) -> dict[str, Any]:
    """Generate structured error response.

    Args:
        code: Error code (e.g., "NOT_FOUND", "VALIDATION_ERROR")
        message: Human-readable error message
        suggestions: Optional list of actionable suggestions or single string

    Returns:
        Dict with error=True, code, message, and optional help
    """
    output: dict[str, Any] = {
        "error": True,
        "code": code,
        "message": message,
    }
    if suggestions:
        if isinstance(suggestions, str):
            output["help"] = [suggestions]
        else:
            output["help"] = suggestions
    return output


def success_response(data: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Generate structured success response.

    Args:
        data: Optional data dict to include
        **kwargs: Additional key-value pairs

    Returns:
        Dict with success=True and optional data
    """
    output: dict[str, Any] = {"success": True}
    if data:
        output["data"] = data
    output.update(kwargs)
    return output
