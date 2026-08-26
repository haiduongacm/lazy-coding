"""Tests for lazy-core TOON format."""

import pytest
from lazy_core.toon import encode, decode, encode_dict, encode_list, decode_dict, decode_list, decode_scalar


class TestEncode:
    def test_encode_string(self):
        assert encode("hello") == "hello"

    def test_encode_int(self):
        assert encode(42) == "42"

    def test_encode_float(self):
        assert encode(3.14) == "3.14"

    def test_encode_bool_true(self):
        assert encode(True) == "true"

    def test_encode_bool_false(self):
        assert encode(False) == "false"

    def test_encode_none(self):
        assert encode(None) == "null"

    def test_encode_simple_dict(self):
        result = encode({"name": "test", "value": 42})
        assert "name: test" in result
        assert "value: 42" in result

    def test_encode_simple_list(self):
        result = encode([1, 2, 3])
        assert "[3]:" in result

    def test_encode_nested_dict(self):
        result = encode({"user": {"name": "test"}})
        assert "user:" in result

    def test_encode_empty_dict(self):
        assert encode({}) == "{}"

    def test_encode_empty_list(self):
        assert encode([]) == "[]"


class TestDecode:
    def test_decode_string(self):
        assert decode("hello") == "hello"

    def test_decode_int(self):
        assert decode("42") == 42

    def test_decode_float(self):
        assert decode("3.14") == 3.14

    def test_decode_bool_true(self):
        assert decode("true") is True

    def test_decode_bool_false(self):
        assert decode("false") is False

    def test_decode_none(self):
        assert decode("null") is None

    def test_decode_empty(self):
        assert decode("") is None

    def test_decode_simple_dict(self):
        toon = "name: test\nvalue: 42"
        result = decode(toon)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_decode_simple_list(self):
        toon = "[3]:\n  1\n  2\n  3"
        result = decode(toon)
        assert result == [1, 2, 3]

    def test_decode_nested_dict(self):
        toon = "user:\n  name: test\n  age: 25"
        result = decode(toon)
        assert result["user"]["name"] == "test"


class TestDecodeScalar:
    def test_decode_int(self):
        assert decode_scalar("42") == 42

    def test_decode_float(self):
        assert decode_scalar("3.14") == 3.14

    def test_decode_bool_true(self):
        assert decode_scalar("true") is True

    def test_decode_bool_false(self):
        assert decode_scalar("false") is False

    def test_decode_none(self):
        assert decode_scalar("null") is None

    def test_decode_string(self):
        assert decode_scalar("hello") == "hello"

    def test_decode_empty(self):
        assert decode_scalar("") is None


class TestEncodeDecode:
    def test_roundtrip_dict(self):
        original = {"name": "test", "value": 42, "active": True}
        encoded = encode(original)
        decoded = decode(encoded)
        assert decoded["name"] == "test"
        assert decoded["value"] == 42
        assert decoded["active"] is True

    def test_roundtrip_list(self):
        original = [1, 2, 3, "hello", True]
        encoded = encode(original)
        decoded = decode(encoded)
        assert decoded == [1, 2, 3, "hello", True]
