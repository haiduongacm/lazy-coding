"""Tests for lazy-master master."""

import pytest
import asyncio
from lazy_master.master import LazyMaster


class TestLazyMaster:
    def test_create_master(self):
        master = LazyMaster()
        assert master.agent == "claude"
        assert master.max_hands == 4
        assert len(master.hands) == 0

    def test_create_master_with_config(self):
        master = LazyMaster(agent="opencode", max_hands=2)
        assert master.agent == "opencode"
        assert master.max_hands == 2

    def test_status(self):
        master = LazyMaster()
        status = master.status()
        assert status["total"] == 0
        assert status["working"] == 0
        assert status["done"] == 0
        assert status["failed"] == 0

    @pytest.mark.asyncio
    async def test_dispatch(self):
        master = LazyMaster()
        await master.init()
        task = {"description": "fix bug", "type": "ship"}
        result = await master.dispatch(task)
        assert result["success"] is True
        assert "hand_id" in result
        assert len(master.hands) == 1

    @pytest.mark.asyncio
    async def test_dispatch_max_hands(self):
        master = LazyMaster(max_hands=1)
        await master.init()
        task = {"description": "fix bug"}
        await master.dispatch(task)
        result = await master.dispatch({"description": "another bug"})
        assert result["error"] is True
        assert result["code"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_teardown_all(self):
        master = LazyMaster()
        await master.init()
        await master.dispatch({"description": "fix bug"})
        results = await master.teardown_all()
        assert len(results) == 1
        assert len(master.hands) == 0
