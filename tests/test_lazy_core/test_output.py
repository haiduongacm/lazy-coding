"""Tests for lazy-core output."""

import pytest
from lazy_core.output import (
    render_output, render_error, error_output, merge_output,
    home_header_output, collapse_home_directory,
)


class TestRenderOutput:
    def test_string(self):
        assert render_output("hello") == "hello"

    def test_dict(self):
        result = render_output({"name": "test"})
        assert "name: test" in result


class TestRenderError:
    def test_basic(self):
        result = render_error("test error", "TEST_CODE")
        assert "error: test error" in result
        assert "code: TEST_CODE" in result

    def test_with_suggestions(self):
        result = render_error("test error", "TEST_CODE", ["suggestion 1"])
        assert "help:" in result
        assert "suggestion 1" in result


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


class TestHomeHeaderOutput:
    def test_basic(self):
        result = home_header_output("test description", "/path/to/bin")
        assert result["description"] == "test description"
        assert "bin" in result


class TestCollapseHomeDirectory:
    def test_no_collapse(self):
        assert collapse_home_directory("/other/path") == "/other/path"

    def test_collapse(self):
        result = collapse_home_directory("/home/user/path", "/home/user")
        assert result == "~/path"
