"""lazy-master - Multi-agent orchestrator.

Mirrors firstmate's AGENTS.md sections 1-14.
"""

from .master import LazyMaster
from .hand import LazyHand
from .master2 import LazyMaster2
from .watcher import Watcher
from .control import ControlPlane
from .turnend import TurnEndGuard
from .dispatcher import parse_request, detect_task_type, detect_priority
from .session import create_session, list_sessions, load_session
from .backlog import Backlog
from .project_mode import ProjectMode
from .fleet_snapshot import FleetSnapshot
from .guard import Guard

__all__ = [
    "LazyMaster", "LazyHand", "LazyMaster2",
    "Watcher", "ControlPlane", "TurnEndGuard",
    "parse_request", "detect_task_type", "detect_priority",
    "create_session", "list_sessions", "load_session",
    "Backlog", "ProjectMode", "FleetSnapshot", "Guard",
]
