"""Tests for lazy-pool worktree pool."""

import pytest
import os
import tempfile
import sys
from pathlib import Path
from lazy_pool.pool import Pool
from lazy_pool.worktree import Worktree
from lazy_pool.state import State
from lazy_pool.layout import Layout, canonical, contains, check_placement


class TestLayout:
    def test_canonical(self):
        path = os.path.join("foo", "bar", "baz")
        result = canonical(path)
        assert "foo" in result
        assert "bar" in result
        assert "baz" in result

    def test_contains_same_dir(self):
        assert contains("/foo", "/foo") is True

    def test_contains_subdir(self):
        assert contains("/foo", "/foo/bar") is True

    def test_contains_not_subdir(self):
        assert contains("/foo", "/bar") is False

    def test_check_placement_valid(self):
        result = check_placement("/nm-home", "/checkout", "/custom-root")
        assert result is None

    def test_check_placement_inside_nm_home(self):
        result = check_placement("/nm-home", "/checkout", "/nm-home/worktrees")
        assert result is not None
        assert "inside no-mistakes" in result

    def test_check_placement_inside_checkout(self):
        result = check_placement("/nm-home", "/checkout", "/checkout/worktrees")
        assert result is not None
        assert "inside the checkout" in result

    def test_layout_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_home = os.path.join(tmpdir, "nm-home")
            layout = Layout(nm_home, {"/checkout": "/custom-root"})
            assert layout.nm_home == nm_home
            assert len(layout.roots) == 1

    def test_layout_custom_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_home = os.path.join(tmpdir, "nm-home")
            layout = Layout(nm_home, {"/checkout": "/custom-root"})
            root = layout.custom_root("/checkout")
            # Normalize for platform
            assert root == os.path.normpath("/custom-root")

    def test_layout_custom_root_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_home = os.path.join(tmpdir, "nm-home")
            layout = Layout(nm_home)
            root = layout.custom_root("/checkout")
            assert root is None

    def test_layout_dir_custom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_home = os.path.join(tmpdir, "nm-home")
            layout = Layout(nm_home, {"/checkout": "/custom-root"})
            result = layout.dir("repo1", "run1", "/checkout")
            expected = os.path.normpath("/custom-root") + os.sep + "run1"
            assert result == expected

    def test_layout_dir_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_home = os.path.join(tmpdir, "nm-home")
            layout = Layout(nm_home)
            result = layout.dir("repo1", "run1")
            expected = os.path.normpath(nm_home) + os.sep + "worktrees" + os.sep + "repo1" + os.sep + "run1"
            assert result == expected

    def test_layout_checkouts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_home = os.path.join(tmpdir, "nm-home")
            layout = Layout(nm_home, {"/checkout": "/custom-root"})
            checkouts = layout.checkouts()
            assert len(checkouts) == 1
            assert checkouts[0] == os.path.normpath("/checkout")


class TestState:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = State(tmpdir)
            assert state.state_dir.exists()

    def test_load_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = State(tmpdir)
            data = state.load()
            assert "worktrees" in data
            assert "leases" in data
            assert "placement" in data

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = State(tmpdir)
            data = {"worktrees": {"wt1": {"path": "/tmp/wt1"}}}
            state.save(data)
            loaded = state.load()
            assert loaded["worktrees"]["wt1"]["path"] == "/tmp/wt1"

    def test_record_placement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = State(tmpdir)
            state.record_placement("/tmp/wt1", "repo1", "run1")
            placement = state.get_placement("/tmp/wt1")
            assert placement is not None
            assert placement["repo_id"] == "repo1"
            assert placement["run_id"] == "run1"


class TestWorktree:
    def test_init(self):
        wt = Worktree("/tmp/test")
        assert str(wt.repo_path) == os.path.normpath("/tmp/test")

    def test_get_default_branch(self):
        wt = Worktree()
        # Should return a valid branch name
        branch = wt.get_default_branch()
        assert branch in ("main", "master")


class TestPool:
    def test_init(self):
        pool = Pool()
        assert pool.repo_path.exists()

    def test_status(self):
        pool = Pool()
        status = pool.status()
        assert status["total"] == 0
        assert status["in_use"] == 0
        assert status["idle"] == 0

    def test_prune_empty(self):
        pool = Pool()
        pruned = pool.prune(dry_run=True)
        assert pruned == []
