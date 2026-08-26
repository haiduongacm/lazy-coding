"""Tests for lazy-master turnend guard."""

import pytest
from lazy_master.turnend import TurnEndGuard


class TestTurnEndGuard:
    def test_create_guard(self):
        guard = TurnEndGuard()
        assert guard.max_block_budget == 3
        assert guard.block_counts == {}

    def test_create_guard_with_budget(self):
        guard = TurnEndGuard(max_block_budget=5)
        assert guard.max_block_budget == 5

    def test_acknowledge(self):
        guard = TurnEndGuard()
        guard.block_counts["hand-1"] = 2
        guard.acknowledge("hand-1")
        assert "hand-1" not in guard.block_counts

    def test_acknowledge_nonexistent(self):
        guard = TurnEndGuard()
        guard.acknowledge("hand-999")  # Should not raise
