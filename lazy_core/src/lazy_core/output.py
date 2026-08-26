"""Output rendering utilities.

Mirrors axi-sdk-js output.ts - renders structured output to TOON format.
"""

import os
from .toon import encode


def collapse_home_directory(path: str, home_dir: str | None = None) -> str:
    """Collapse home directory to ~ prefix."""
    if home_dir is None:
        home_dir = os.path.expanduser("~")
    if not path.startswith(home_dir):
        return path
    return f"~{path[len(home_dir):]}"


def home_header_output(description: str, exec_path: str | None = None, home_dir: str | None = None) -> dict:
    """Generate home header output with bin and description."""
    if exec_path is None:
        exec_path = ""
    return {
        "bin": collapse_home_directory(exec_path, home_dir),
        "description": description,
    }


def error_output(message: str, code: str, suggestions: list[str] | None = None) -> dict:
    """Generate structured error output."""
    output = {"error": message, "code": code}
    if suggestions:
        output["help"] = suggestions
    return output


def merge_output(*parts: dict | None) -> dict:
    """Merge multiple output dicts."""
    result = {}
    for part in parts:
        if part:
            result.update(part)
    return result


def render_output(output) -> str:
    """Render output to string - TOON format for dicts, plain for strings."""
    if isinstance(output, str):
        return output
    return encode(output)


def render_error(message: str, code: str, suggestions: list[str] | None = None) -> str:
    """Render error to string."""
    return render_output(error_output(message, code, suggestions))


def render_home_header(description: str, exec_path: str | None = None, home_dir: str | None = None) -> str:
    """Render home header to string."""
    return render_output(home_header_output(description, exec_path, home_dir))
