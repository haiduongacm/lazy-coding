"""Tests for lazy-master watcher."""

import pytest
import asyncio
from lazy_master.watcher import Watcher


class TestWatcher:
    def test_create_watcher(self):
        watcher = Watcher()
        assert watcher.running is False
        assert watcher.interval == 10

    def test_create_watcher_with_interval(self):
        watcher = Watcher(interval=5)
        assert watcher.interval == 5

    def test_status(self):
        watcher = Watcher()
        status = watcher.status()
        assert status["running"] is False
        assert status["interval"] == 10
        assert status["hands_watching"] == 0

    def test_record_activity(self):
        watcher = Watcher()
        import time
        watcher.last_activity["hand-1"] = time.time()
        assert "hand-1" in watcher.last_activity

    def test_on_callback(self):
        watcher = Watcher()
        callback_called = False

        def callback(data):
            nonlocal callback_called
            callback_called = True

        watcher.on("test", callback)
        watcher.emit("test", {})
        assert callback_called is True
