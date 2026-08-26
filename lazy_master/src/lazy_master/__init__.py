"""lazy-master - Multi-agent orchestrator."""

from .master import LazyMaster
from .hand import LazyHand
from .master2 import LazyMaster2
from .dispatcher import parse_request
from .session import create_session, list_sessions

__version__ = "1.0.0"

__all__ = [
    "LazyMaster",
    "LazyHand",
    "LazyMaster2",
    "parse_request",
    "create_session",
    "list_sessions",
]
