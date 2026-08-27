"""lazy-core - TOON format encoder/decoder and shared utilities.

Mirrors the original output and error handling logic.
"""

from .toon import encode, decode, encode_dict, encode_list, decode_dict, decode_list, decode_scalar
from .errors import AxiError, exit_code_for_error
from .output import (
    render_output,
    render_error,
    error_output,
    merge_output,
    home_header_output,
    collapse_home_directory,
)
from .principles import PRINCIPLES
from .truncate import truncate
from .aggregate import aggregate
from .empty import empty_response

__all__ = [
    "encode", "decode", "encode_dict", "encode_list", "decode_dict", "decode_list", "decode_scalar",
    "AxiError", "exit_code_for_error",
    "render_output", "render_error", "error_output", "merge_output",
    "home_header_output", "collapse_home_directory",
    "PRINCIPLES", "truncate", "aggregate", "empty_response",
]
