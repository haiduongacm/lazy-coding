"""Session management."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


SESSIONS_DIR = Path.home() / ".lazy-coding" / "sessions"


def create_session() -> dict:
    """Create a new session."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session = {
        "id": uuid.uuid4().hex[:8],
        "created": datetime.now().isoformat(),
        "status": "active",
    }

    session_file = SESSIONS_DIR / f"{session['id']}.json"
    with open(session_file, "w") as f:
        json.dump(session, f, indent=2)

    return session


def list_sessions() -> list:
    """List all sessions."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    sessions = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                sessions.append(json.load(fh))
        except (json.JSONDecodeError, IOError):
            pass

    return sessions


def load_session(session_id: str) -> Optional[dict]:
    """Load a session by ID."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        with open(session_file) as f:
            return json.load(f)
    return None
