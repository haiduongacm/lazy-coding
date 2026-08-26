"""Tests for lazy-core principles."""

from lazy_core.principles import PRINCIPLES


class TestPrinciples:
    def test_principles_count(self):
        assert len(PRINCIPLES) == 10

    def test_principles_have_ids(self):
        for p in PRINCIPLES:
            assert "id" in p
            assert "name" in p
            assert "summary" in p

    def test_principles_ids_are_unique(self):
        ids = [p["id"] for p in PRINCIPLES]
        assert len(ids) == len(set(ids))

    def test_first_principle(self):
        assert PRINCIPLES[0]["name"] == "Token-efficient output"
