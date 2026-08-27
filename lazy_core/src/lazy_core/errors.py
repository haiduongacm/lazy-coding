"""AxiError - structured error with code and suggestions.

Mirrors the original error handling logic.
"""


class AxiError(Exception):
    """Structured error with code and suggestions."""

    def __init__(self, message: str, code: str, suggestions: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.suggestions = suggestions or []


def exit_code_for_error(error: Exception) -> int:
    """Return exit code for an error.

    VALIDATION_ERROR -> 2, everything else -> 1.
    """
    if isinstance(error, AxiError) and error.code == "VALIDATION_ERROR":
        return 2
    return 1
