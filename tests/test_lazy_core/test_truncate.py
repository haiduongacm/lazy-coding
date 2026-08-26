"""Tests for lazy-core truncate."""

from lazy_core.truncate import truncate


class TestTruncate:
    def test_no_truncation(self):
        assert truncate("hello", max_length=10) == "hello"

    def test_truncation(self):
        result = truncate("hello world", max_length=5)
        assert len(result) == 5
        assert result.endswith("...")

    def test_custom_suffix(self):
        result = truncate("hello world", max_length=5, suffix="~")
        assert result.endswith("~")

    def test_empty_string(self):
        assert truncate("") == ""

    def test_none(self):
        assert truncate(None) is None

    def test_exact_length(self):
        assert truncate("hello", max_length=5) == "hello"
