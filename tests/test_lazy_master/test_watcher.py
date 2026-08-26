"""Tests for lazy-master watcher."""

import pytest
import tempfile
from pathlib import Path
from lazy_master.watcher import Watcher


class TestWatcher:
    def test_create_watcher(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            assert watcher.running is False
            assert watcher.poll_interval == 15

    def test_create_watcher_with_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir, poll_interval=5)
            assert watcher.poll_interval == 5

    def test_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            status = watcher.status()
            assert status["running"] is False
            assert status["poll_interval"] == 15

    def test_record_activity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            import time
            watcher.last_activity["hand-1"] = time.time()
            assert "hand-1" in watcher.last_activity

    def test_on_callback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            callback_called = False

            def callback(data):
                nonlocal callback_called
                callback_called = True

            watcher.on("test", callback)
            watcher.emit("test", {})
            assert callback_called is True

    def test_acquire_release_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            assert watcher.acquire_lock()
            assert watcher.lock_file.exists()
            watcher.release_lock()
            assert not watcher.lock_file.exists()

    def test_check_worker_liveness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            import time
            watcher.last_activity["hand-1"] = time.time()
            result = watcher.check_worker_liveness("hand-1")
            assert result["alive"] is True

    def test_check_worker_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir, stale_grace=0)
            watcher.last_activity["hand-1"] = 0
            result = watcher.check_worker_liveness("hand-1")
            assert result["alive"] is False

    def test_get_fleet_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            status = watcher.get_fleet_status()
            assert status["total"] == 0
