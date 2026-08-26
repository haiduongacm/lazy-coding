"""Tests for lazy-core aggregate."""

from lazy_core.aggregate import aggregate


class TestAggregate:
    def test_empty_list(self):
        result = aggregate([])
        assert result == {"total": 0}

    def test_simple_list(self):
        result = aggregate(["a", "b", "a"])
        assert result["total"] == 3
        assert result["a"] == 2
        assert result["b"] == 1

    def test_with_key(self):
        items = [{"type": "bug"}, {"type": "feature"}, {"type": "bug"}]
        result = aggregate(items, key="type")
        assert result["total"] == 3
        assert result["bug"] == 2
        assert result["feature"] == 1

    def test_mixed_types(self):
        result = aggregate([1, "hello", 1, "hello", 1])
        assert result["total"] == 5
        assert result["1"] == 3
        assert result["hello"] == 2
