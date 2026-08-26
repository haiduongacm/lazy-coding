"""Tests for lazy-master session."""

import pytest
from lazy_master.session import create_session, list_sessions, load_session


class TestSession:
    def test_create_session(self):
        session = create_session()
        assert "id" in session
        assert session["status"] == "active"
        assert "created" in session

    def test_list_sessions(self):
        sessions = list_sessions()
        assert isinstance(sessions, list)

    def test_create_and_load(self):
        session = create_session()
        loaded = load_session(session["id"])
        assert loaded is not None
        assert loaded["id"] == session["id"]
