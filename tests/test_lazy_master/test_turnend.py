"""Tests for lazy-master turnend."""

import pytest
import tempfile
from lazy_master.turnend import TurnEndGuard


class TestTurnEndGuard:
    def test_create_guard(self):
        guard = TurnEndGuard()
        assert guard.block_budget == 3
        assert guard.block_counts == {}

    def test_create_guard_with_budget(self):
        guard = TurnEndGuard(block_budget=5)
        assert guard.block_budget == 5

    def test_should_block_healthy_watcher(self):
        guard = TurnEndGuard()
        result = guard.should_block("hand-1", True)
        assert result["blocked"] is False
        assert result["reason"] == "watcher_healthy"

    def test_should_block_unhealthy(self):
        guard = TurnEndGuard()
        result = guard.should_block("hand-1", False)
        assert result["blocked"] is True
        assert result["reason"] == "watcher_unhealthy"

    def test_should_block_hook_active(self):
        guard = TurnEndGuard()
        result = guard.should_block("hand-1", False, hook_active=True)
        assert result["blocked"] is False
        assert result["reason"] == "hook_already_active"

    def test_should_block_budget_exceeded(self):
        guard = TurnEndGuard()
        guard.block_counts["hand-1"] = 3
        result = guard.should_block("hand-1", False)
        assert result["blocked"] is False
        assert result["reason"] == "budget_exceeded"

    def test_acknowledge(self):
        guard = TurnEndGuard()
        guard.block_counts["hand-1"] = 2
        guard.acknowledge("hand-1")
        assert "hand-1" not in guard.block_counts

    def test_acknowledge_nonexistent(self):
        guard = TurnEndGuard()
        guard.acknowledge("hand-1")  # Should not raise

    def test_get_status(self):
        guard = TurnEndGuard()
        status = guard.get_status()
        assert status["total_blocked"] == 0
        assert status["budget"] == 3

    def test_get_status_for_task(self):
        guard = TurnEndGuard()
        guard.block_counts["hand-1"] = 2
        status = guard.get_status("hand-1")
        assert status["task_id"] == "hand-1"
        assert status["block_count"] == 2
