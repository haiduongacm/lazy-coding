"""Tests for lazy-core output."""

import pytest
import os
from lazy_core.output import (
    render_output, render_error, error_output, merge_output,
    home_header_output, collapse_home_directory,
    render_home_header,
)


class TestCollapseHomeDirectory:
    def test_no_collapse(self):
        assert collapse_home_directory("/other/path") == "/other/path"

    def test_collapse(self):
        home = os.path.expanduser("~")
        result = collapse_home_directory(f"{home}/path")
        assert result == "~/path"

    def test_collapse_custom_home(self):
        result = collapse_home_directory("/home/user/path", "/home/user")
        assert result == "~/path"


class TestHomeHeaderOutput:
    def test_basic(self):
        result = home_header_output("test description")
        assert result["description"] == "test description"
        assert "bin" in result

    def test_with_exec_path(self):
        result = home_header_output("test", "/usr/bin/tool")
        assert "tool" in result["bin"]


class TestErrorOutput:
    def test_basic(self):
        result = error_output("test error", "TEST_CODE")
        assert result["error"] == "test error"
        assert result["code"] == "TEST_CODE"
        assert "help" not in result

    def test_with_suggestions(self):
        result = error_output("test error", "TEST_CODE", ["suggestion 1"])
        assert result["help"] == ["suggestion 1"]


class TestMergeOutput:
    def test_merge(self):
        result = merge_output({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_with_none(self):
        result = merge_output({"a": 1}, None, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_override(self):
        result = merge_output({"a": 1}, {"a": 2})
        assert result == {"a": 2}


class TestRenderOutput:
    def test_string(self):
        assert render_output("hello") == "hello"

    def test_dict(self):
        result = render_output({"name": "test"})
        assert "name: test" in result


class TestRenderError:
    def test_basic(self):
        result = render_error("test error", "TEST_CODE")
        assert "test error" in result
        assert "TEST_CODE" in result


class TestRenderHomeHeader:
    def test_basic(self):
        result = render_home_header("test description")
        assert "test description" in result
        assert "bin" in result
