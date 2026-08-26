"""output - Structured output rendering.

Mirrors axi-sdk-js output.ts: collapse home directory, error output,
merge output, render output.
"""

import os
from typing import Any
from .toon import encode as toon_encode


def collapse_home_directory(path: str, home_dir: str | None = None) -> str:
    """Collapse home directory to ~ prefix.

    Args:
        path: Path to collapse
        home_dir: Home directory (defaults to os.path.expanduser("~"))

    Returns:
        Path with home directory collapsed to ~
    """
    if home_dir is None:
        home_dir = os.path.expanduser("~")

    if not path.startswith(home_dir):
        return path

    return f"~{path[len(home_dir):]}"


def home_header_output(description: str, exec_path: str | None = None,
                       home_dir: str | None = None) -> dict[str, Any]:
    """Generate home header output.

    Args:
        description: Tool description
        exec_path: Executable path (defaults to sys.argv[0])
        home_dir: Home directory

    Returns:
        Dict with bin and description
    """
    if exec_path is None:
        import sys
        exec_path = sys.argv[0] if sys.argv else ""

    return {
        "bin": collapse_home_directory(exec_path, home_dir),
        "description": description,
    }


def error_output(message: str, code: str, suggestions: list[str] | None = None) -> dict[str, Any]:
    """Generate error output.

    Args:
        message: Error message
        code: Error code
        suggestions: Optional list of suggestions

    Returns:
        Dict with error, code, and optional help
    """
    output: dict[str, Any] = {
        "error": message,
        "code": code,
    }

    if suggestions:
        output["help"] = suggestions

    return output


def merge_output(*parts: dict[str, Any] | None) -> dict[str, Any]:
    """Merge multiple output dicts.

    Args:
        *parts: Dicts to merge (None values ignored)

    Returns:
        Merged dict
    """
    result: dict[str, Any] = {}
    for part in parts:
        if part:
            result.update(part)
    return result


def render_output(output: str | dict[str, Any]) -> str:
    """Render output to string.

    Args:
        output: String or dict to render

    Returns:
        Rendered string
    """
    if isinstance(output, str):
        return output

    return toon_encode(output)


def render_error(message: str, code: str, suggestions: list[str] | None = None) -> str:
    """Render error output to string.

    Args:
        message: Error message
        code: Error code
        suggestions: Optional list of suggestions

    Returns:
        Rendered error string
    """
    return render_output(error_output(message, code, suggestions))


def render_home_header(description: str, exec_path: str | None = None,
                       home_dir: str | None = None) -> str:
    """Render home header output to string.

    Args:
        description: Tool description
        exec_path: Executable path
        home_dir: Home directory

    Returns:
        Rendered home header string
    """
    return render_output(home_header_output(description, exec_path, home_dir))
