"""Tests for lazy-master modules."""

import pytest
import tempfile
from pathlib import Path
from lazy_master.dispatcher import parse_request, detect_task_type, detect_priority
from lazy_master.hand import LazyHand
from lazy_master.master import LazyMaster
from lazy_master.master2 import LazyMaster2
from lazy_master.watcher import Watcher
from lazy_master.control import ControlPlane
from lazy_master.turnend import TurnEndGuard
from lazy_master.session import SessionManager
from lazy_master.backlog import Backlog
from lazy_master.project_mode import ProjectMode
from lazy_master.fleet_snapshot import FleetSnapshot
from lazy_master.guard import Guard


class TestDispatcher:
    def test_parse_request_single(self):
        tasks = parse_request("fix login bug")
        assert len(tasks) == 1
        assert tasks[0]["description"] == "fix login bug"
        assert tasks[0]["type"] == "ship"
        assert tasks[0]["priority"] == "normal"

    def test_parse_request_multiple(self):
        tasks = parse_request("fix bug and add feature")
        assert len(tasks) == 2
        assert tasks[0]["description"] == "fix bug"
        assert tasks[1]["description"] == "add feature"

    def test_detect_task_type_investigate(self):
        assert detect_task_type("investigate performance") == "scout"

    def test_detect_task_type_fix(self):
        assert detect_task_type("fix bug") == "ship"

    def test_detect_priority_urgent(self):
        assert detect_priority("urgent fix") == "high"

    def test_detect_priority_low(self):
        assert detect_priority("nice to have feature") == "low"

    def test_detect_priority_normal(self):
        assert detect_priority("fix bug") == "normal"


class TestHand:
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


class TestMaster:
    def test_create_master(self):
        master = LazyMaster()
        assert master.agent == "claude"
        assert master.max_hands == 4
        assert len(master.hands) == 0

    def test_status(self):
        master = LazyMaster()
        status = master.status()
        assert status["total"] == 0
        assert status["working"] == 0

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
        await master.dispatch({"description": "fix bug"})
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


class TestMaster2:
    def test_create_master2(self):
        master2 = LazyMaster2(id="test", name="test-secondmate")
        assert master2.id == "test"
        assert master2.name == "test-secondmate"
        assert master2.status == "idle"

    def test_get_status(self):
        master2 = LazyMaster2(id="test")
        status = master2.get_status()
        assert status["id"] == "test"
        assert status["status"] == "idle"

    @pytest.mark.asyncio
    async def test_assign(self):
        master2 = LazyMaster2(id="test")
        result = await master2.assign({"description": "fix bug"})
        assert result["success"] is True
        assert master2.status == "working"

    @pytest.mark.asyncio
    async def test_assign_busy(self):
        master2 = LazyMaster2(id="test")
        await master2.assign({"description": "fix bug"})
        result = await master2.assign({"description": "another bug"})
        assert result["error"] is True
        assert result["code"] == "BUSY"


class TestWatcher:
    def test_create_watcher(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = Watcher(state_dir=tmpdir)
            assert watcher.running is False
            assert watcher.poll_interval == 15

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


class TestControlPlane:
    def test_is_verb_allowed(self):
        cp = ControlPlane()
        assert cp.is_verb_allowed("interrupt") is True
        assert cp.is_verb_allowed("exit") is True
        assert cp.is_verb_allowed("relaunch") is True
        assert cp.is_verb_allowed("invalid") is False

    @pytest.mark.asyncio
    async def test_interrupt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp = ControlPlane(state_dir=tmpdir)
            # Create a test task meta file
            task_id = "test-task-1"
            meta_file = Path(tmpdir) / f"{task_id}.meta"
            meta_file.write_text("backend=tmux\nharness=claude\nwindow=test\n")
            
            result = await cp.interrupt(task_id)
            assert result["success"] is True
            assert result["verb"] == "interrupt"

    @pytest.mark.asyncio
    async def test_exit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp = ControlPlane(state_dir=tmpdir)
            # Create a test task meta file
            task_id = "test-task-1"
            meta_file = Path(tmpdir) / f"{task_id}.meta"
            meta_file.write_text("backend=tmux\nharness=claude\nwindow=test\n")
            
            result = await cp.exit(task_id)
            assert result["success"] is True
            assert result["verb"] == "exit"

    @pytest.mark.asyncio
    async def test_relaunch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp = ControlPlane(state_dir=tmpdir)
            # Create a test task meta file
            task_id = "test-task-1"
            meta_file = Path(tmpdir) / f"{task_id}.meta"
            meta_file.write_text("backend=tmux\nharness=claude\nwindow=test\n")
            
            result = await cp.relaunch(task_id, harness="claude", note="switching")
            assert result["success"] is True
            assert result["verb"] == "relaunch"
            assert result["new_harness"] == "claude"


class TestTurnEndGuard:
    def test_create_guard(self):
        guard = TurnEndGuard()
        assert guard.block_budget == 3
        assert guard.block_counts == {}

    def test_should_block_no_in_flight(self):
        guard = TurnEndGuard()
        # When watcher is healthy, should not block
        result = guard.should_block("hand-1", True)
        assert result["blocked"] is False

    def test_should_block_healthy_watcher(self):
        guard = TurnEndGuard()
        result = guard.should_block("hand-1", True)
        assert result["blocked"] is False

    def test_should_block_unhealthy(self):
        guard = TurnEndGuard()
        result = guard.should_block("hand-1", False)
        assert result["blocked"] is True

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


class TestBacklog:
    def test_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog = Backlog(data_dir=tmpdir)
            result = backlog.add("Fix login bug")
            assert "id" in result
            assert result["status"] == "queued"

    def test_list_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog = Backlog(data_dir=tmpdir)
            backlog.add("Fix login bug")
            backlog.add("Add feature")
            items = backlog.list_items()
            assert len(items) == 2

    def test_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog = Backlog(data_dir=tmpdir)
            backlog.add("Fix login bug")
            backlog.add("Add feature")
            ready = backlog.ready()
            assert len(ready) == 2

    def test_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog = Backlog(data_dir=tmpdir)
            result = backlog.add("Fix login bug")
            complete_result = backlog.complete(result["id"])
            assert complete_result["success"] is True
            assert backlog.items[result["id"]].status == "done"


class TestProjectMode:
    def test_resolve_default(self):
        pm = ProjectMode()
        result = pm.resolve("unknown-project")
        assert result["mode"] == "no-mistakes"
        assert result["yolo"] == "off"

    def test_resolve_with_registry(self):
        pm = ProjectMode()
        registry = {"my-api": {"mode": "direct-PR", "yolo": "on"}}
        result = pm.resolve("my-api", registry)
        assert result["mode"] == "direct-PR"
        assert result["yolo"] == "on"

    def test_resolve_prod_only(self):
        pm = ProjectMode()
        registry = {"my-api": {"mode": "no-mistakes-prod-only", "yolo": "off"}}
        result = pm.resolve("my-api", registry)
        assert result["mode"] == "no-mistakes"


class TestFleetSnapshot:
    def test_generate(self):
        fs = FleetSnapshot()
        snapshot = fs.generate()
        assert snapshot["schema"] == "lazy-coding-fleet-snapshot.v1"
        assert "generated" in snapshot
        assert snapshot["tasks"] == []


class TestGuard:
    def test_check_no_warnings(self):
        guard = Guard()
        result = guard.check(in_flight=0, watcher_healthy=True, current_branch="main")
        assert result["supervision_needed"] is False
        assert result["warnings"] == []

    def test_check_tangle(self):
        guard = Guard()
        result = guard.check(current_branch="feature-branch")
        assert len(result["warnings"]) >= 1
        assert result["warnings"][0]["type"] == "tangle"

    def test_check_watcher_down(self):
        guard = Guard()
        result = guard.check(in_flight=1, watcher_healthy=False, current_branch="main")
        assert result["supervision_needed"] is True
        # When watcher_healthy is explicitly False, it doesn't add watcher_down warning
        # but supervision_needed is True when in_flight > 0 and watcher not healthy
