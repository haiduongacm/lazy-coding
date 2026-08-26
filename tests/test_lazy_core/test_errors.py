"""Tests for lazy-core errors."""

import pytest
from lazy_core.errors import AxiError, exit_code_for_error


class TestAxiError:
    def test_create_error(self):
        error = AxiError("test message", "TEST_CODE")
        assert str(error) == "test message"
        assert error.message == "test message"
        assert error.code == "TEST_CODE"
        assert error.suggestions == []

    def test_create_error_with_suggestions(self):
        error = AxiError("test message", "TEST_CODE", ["suggestion 1", "suggestion 2"])
        assert error.suggestions == ["suggestion 1", "suggestion 2"]


class TestExitCodeForError:
    def test_validation_error(self):
        error = AxiError("test", "VALIDATION_ERROR")
        assert exit_code_for_error(error) == 2

    def test_other_error(self):
        error = AxiError("test", "OTHER_ERROR")
        assert exit_code_for_error(error) == 1

    def test_generic_error(self):
        error = Exception("test")
        assert exit_code_for_error(error) == 1
