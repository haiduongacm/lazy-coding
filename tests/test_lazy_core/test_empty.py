"""Tests for lazy-core empty response."""

from lazy_core.empty import empty_response


class TestEmptyResponse:
    def test_default_type(self):
        result = empty_response()
        assert result["total"] == 0
        assert result["items"] == []
        assert "No items found" in result["message"]

    def test_custom_type(self):
        result = empty_response("tasks")
        assert result["total"] == 0
        assert result["tasks"] == []
        assert "No tasks found" in result["message"]
