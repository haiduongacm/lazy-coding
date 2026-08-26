"""lazy-core - TOON format encoder/decoder and shared utilities."""

from .toon import encode, decode
from .principles import PRINCIPLES
from .truncate import truncate
from .aggregate import aggregate
from .error import error_response, success_response
from .empty import empty_response

__version__ = "1.0.0"

__all__ = [
    "encode",
    "decode",
    "PRINCIPLES",
    "truncate",
    "aggregate",
    "error_response",
    "success_response",
    "empty_response",
]
