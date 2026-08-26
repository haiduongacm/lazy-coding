"""Tests for lazy-core error responses."""

from lazy_core.error import error_response, success_response


class TestErrorResponse:
    def test_basic_error(self):
        result = error_response("NOT_FOUND", "Item not found")
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"
        assert result["message"] == "Item not found"
        assert "help" not in result

    def test_error_with_help(self):
        result = error_response("NOT_FOUND", "Item not found", ["Check ID", "Try again"])
        assert result["help"] == ["Check ID", "Try again"]

    def test_error_with_string_help(self):
        result = error_response("NOT_FOUND", "Item not found", "Check ID")
        assert result["help"] == ["Check ID"]


class TestSuccessResponse:
    def test_basic_success(self):
        result = success_response()
        assert result["success"] is True

    def test_success_with_data(self):
        result = success_response({"id": 1, "name": "test"})
        assert result["success"] is True
        assert result["data"]["id"] == 1

    def test_success_with_kwargs(self):
        result = success_response(name="test", value=42)
        assert result["success"] is True
        assert result["name"] == "test"
        assert result["value"] == 42
