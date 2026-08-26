"""Tests for lazy-gate gate and pipeline."""

import pytest
import os
import tempfile
from pathlib import Path
from lazy_gate.gate import Gate, repo_id
from lazy_gate.pipeline import Pipeline
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
            # Empty pipeline should succeed (no findings)
            assert result["success"] is True
            assert result["findings"] == []
            assert len(result["results"]) == 0


class TestWorktree:
    def test_init(self):
        wt = Worktree()
        assert wt.repo_path.exists()

    def test_init_custom_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wt = Worktree(tmpdir)
            assert str(wt.repo_path) == os.path.normpath(tmpdir)
