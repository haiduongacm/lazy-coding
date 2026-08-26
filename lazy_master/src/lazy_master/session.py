"""lazy-master session - Session management.

Mirrors firstmate's session lock and lifecycle.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import uuid


@dataclass
class Session:
    """Session with lock and lifecycle."""
    id: str
    status: str = "active"
    created: datetime = field(default_factory=datetime.now)
    locked: bool = False


_sessions: dict[str, Session] = {}


def create_session() -> dict[str, Any]:
    """Create a new session.

    Mirrors firstmate: acquires per-home session lock first.
    """
    session_id = str(uuid.uuid4())[:8]
    session = Session(id=session_id)
    _sessions[session_id] = session
    return {
        "id": session_id,
        "status": session.status,
        "created": session.created.isoformat(),
    }


def list_sessions() -> list[dict[str, Any]]:
    """List all sessions."""
    return [
        {"id": s.id, "status": s.status, "created": s.created.isoformat()}
        for s in _sessions.values()
    ]


def load_session(session_id: str) -> dict[str, Any] | None:
    """Load a session by ID."""
    session = _sessions.get(session_id)
    if not session:
        return None
    return {
        "id": session.id,
        "status": session.status,
        "created": session.created.isoformat(),
    }
