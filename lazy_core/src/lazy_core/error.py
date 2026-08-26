"""Structured error and success responses."""


def error_response(code, message, help_text=None):
    """Create a structured error response.

    Args:
        code: Error code (e.g., 'NOT_FOUND')
        message: Human-readable error message
        help_text: Optional help text

    Returns:
        Error dict
    """
    response = {"error": True, "code": code, "message": message}
    if help_text:
        response["help"] = help_text if isinstance(help_text, list) else [help_text]
    return response


def success_response(data=None, **kwargs):
    """Create a structured success response.

    Args:
        data: Optional data payload
        **kwargs: Additional fields

    Returns:
        Success dict
    """
    response = {"success": True}
    if data:
        response["data"] = data
    response.update(kwargs)
    return response
