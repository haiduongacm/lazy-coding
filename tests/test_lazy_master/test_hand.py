"""Tests for lazy-master hand."""

import pytest
import asyncio
from lazy_master.hand import LazyHand


class TestLazyHand:
    def test_create_hand(self):
        hand = LazyHand(id="test-hand")
        assert hand.id == "test-hand"
        assert hand.status == "idle"
        assert hand.agent == "claude"

    def test_create_hand_with_agent(self):
        hand = LazyHand(id="test-hand", agent="opencode")
        assert hand.agent == "opencode"

    def test_get_status(self):
        hand = LazyHand(id="test-hand")
        status = hand.get_status()
        assert status["id"] == "test-hand"
        assert status["status"] == "idle"
        assert status["agent"] == "claude"

    def test_complete(self):
        hand = LazyHand(id="test-hand")
        hand.complete({"result": "success"})
        assert hand.status == "done"
        assert hand.result == {"result": "success"}
        assert hand.completed_at is not None

    def test_fail(self):
        hand = LazyHand(id="test-hand")
        hand.fail(Exception("test error"))
        assert hand.status == "failed"
        assert hand.result["error"] == "test error"
        assert hand.completed_at is not None

    def test_assign_task(self):
        hand = LazyHand(id="test-hand")
        task = {"description": "fix bug", "type": "ship"}
        hand.task = task
        hand.status = "assigned"
        assert hand.task == task
        assert hand.status == "assigned"

    def test_set_worktree(self):
        hand = LazyHand(id="test-hand")
        hand.worktree = "/path/to/worktree"
        assert hand.worktree == "/path/to/worktree"
