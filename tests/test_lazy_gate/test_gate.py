"""Tests for lazy-gate gate and pipeline."""

import pytest
import os
import tempfile
from pathlib import Path
from lazy_gate.gate import Gate, repo_id
from lazy_gate.pipeline import (
    Pipeline, Executor, StepName, StepStatus, ApprovalAction,
    Finding, StepOutcome, StepContext, BaseStep, ReviewStep, RunTestStep
)
from lazy_gate.worktree import Worktree


class TestRepoId:
    def test_repo_id_deterministic(self):
        id1 = repo_id("/test/path")
        id2 = repo_id("/test/path")
        assert id1 == id2

    def test_repo_id_different_paths(self):
        id1 = repo_id("/test/path1")
        id2 = repo_id("/test/path2")
        assert id1 != id2

    def test_repo_id_length(self):
        rid = repo_id("/test/path")
        assert len(rid) == 12


class TestGate:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = Gate(tmpdir)
            assert gate.repo_path.exists()

    def test_status_not_initialized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = Gate(tmpdir)
            status = gate.status()
            assert status["initialized"] is False


class TestFinding:
    def test_finding_to_dict(self):
        f = Finding(id="1", file="test.py", line=10, message="error", severity="error")
        d = f.to_dict()
        assert d["id"] == "1"
        assert d["file"] == "test.py"
        assert d["line"] == 10
        assert d["severity"] == "error"


class TestStepOutcome:
    def test_outcome_success(self):
        o = StepOutcome(success=True)
        assert o.success is True
        assert o.has_ask_user_findings is False

    def test_outcome_with_findings(self):
        f = Finding(id="1", file="x.py", line=1, message="err", action="ask-user")
        o = StepOutcome(findings=[f])
        assert o.has_ask_user_findings is True

    def test_outcome_to_dict(self):
        o = StepOutcome(success=True, exit_code=0)
        d = o.to_dict()
        assert d["success"] is True
        assert d["exit_code"] == 0


class TestStepContext:
    def test_context_log(self):
        ctx = StepContext(work_dir="/tmp", step_name=StepName.TEST, run_id="r1")
        ctx.log("test message")


class TestPipeline:
    def test_init_default(self):
        pipeline = Pipeline()
        assert pipeline.stages == ["review", "test", "lint"]

    def test_init_custom(self):
        pipeline = Pipeline(stages=["test", "lint"])
        assert pipeline.stages == ["test", "lint"]

    def test_add_stage(self):
        pipeline = Pipeline()
        pipeline.add_stage("custom", ["echo", "custom"])
        assert "custom" in pipeline.stages
        assert pipeline.commands["custom"] == ["echo", "custom"]

    def test_remove_stage(self):
        pipeline = Pipeline()
        pipeline.remove_stage("test")
        assert "test" not in pipeline.stages

    def test_run_empty_stages(self):
        pipeline = Pipeline(stages=[], commands={})
        with tempfile.TemporaryDirectory() as tmpdir:
            result = pipeline.run(tmpdir)
            # Empty pipeline should have no results
            assert result["results"] == []

    def test_run_with_events(self):
        events = []
        pipeline = Pipeline(stages=[], commands={})
        with tempfile.TemporaryDirectory() as tmpdir:
            result = pipeline.run(tmpdir, on_event=lambda e: events.append(e))
            assert len(events) >= 2  # run_started + run_completed


class TestExecutor:
    def test_execute_empty_steps(self):
        executor = Executor(steps=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = executor.execute(work_dir=tmpdir, run_id="test-1")
            assert result["success"] is True
            assert result["results"] == []

    def test_execute_skip_steps(self):
        step = BaseStep(StepName.TEST, commands={"test": ["python", "-c", "print('ok')"]})
        executor = Executor(steps=[step])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = executor.execute(
                work_dir=tmpdir,
                run_id="test-2",
                skip_steps=[StepName.TEST],
            )
            assert result["results"][0]["status"] == "skipped"

    def test_execute_success(self):
        step = BaseStep(StepName.TEST, commands={"test": ["python", "-c", "print('ok')"]})
        executor = Executor(steps=[step])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = executor.execute(work_dir=tmpdir, run_id="test-3")
            assert result["success"] is True
            assert result["results"][0]["status"] == "passed"

    def test_execute_failure(self):
        step = BaseStep(StepName.TEST, commands={"test": ["python", "-c", "import sys; sys.exit(1)"]})
        executor = Executor(steps=[step])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = executor.execute(work_dir=tmpdir, run_id="test-4")
            assert result["success"] is False
            assert result["results"][0]["status"] == "failed"


class TestWorktree:
    def test_init(self):
        wt = Worktree()
        assert wt.repo_path.exists()

    def test_init_custom_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wt = Worktree(tmpdir)
            assert str(wt.repo_path) == os.path.normpath(tmpdir)
