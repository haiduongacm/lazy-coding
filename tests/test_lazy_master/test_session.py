"""Tests for lazy-master session."""

import pytest
import tempfile
from pathlib import Path
from lazy_master.session import SessionManager


class TestSession:
    def test_acquire_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(state_dir=tmpdir)
            result = manager.acquire_lock()
            assert result["success"]
            assert "session_id" in result

    def test_release_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(state_dir=tmpdir)
            manager.acquire_lock()
            manager.release_lock()
            assert not manager.lock_file.exists()

    def test_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(state_dir=tmpdir)
            result = manager.bootstrap()
            assert result["success"]

    def test_generate_digest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(state_dir=tmpdir)
            manager.acquire_lock()
            result = manager.generate_digest()
            assert result["success"]

    def test_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(state_dir=tmpdir)
            status = manager.status()
            assert status["active"] is False

            manager.acquire_lock()
            status = manager.status()
            assert status["active"]
