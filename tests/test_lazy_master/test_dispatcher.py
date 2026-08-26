"""Tests for lazy-master dispatcher."""

import pytest
from lazy_master.dispatcher import parse_request, detect_task_type, detect_priority


class TestParseRequest:
    def test_single_task(self):
        tasks = parse_request("fix login bug")
        assert len(tasks) == 1
        assert tasks[0]["description"] == "fix login bug"
        assert tasks[0]["type"] == "ship"
        assert tasks[0]["priority"] == "normal"

    def test_multiple_tasks(self):
        tasks = parse_request("fix bug and add feature")
        assert len(tasks) == 2
        assert tasks[0]["description"] == "fix bug"
        assert tasks[1]["description"] == "add feature"

    def test_urgent_task(self):
        tasks = parse_request("urgent hotfix login")
        assert tasks[0]["priority"] == "high"

    def test_low_priority_task(self):
        tasks = parse_request("low priority nice to have feature")
        assert tasks[0]["priority"] == "low"

    def test_scout_task(self):
        tasks = parse_request("investigate performance issue")
        assert tasks[0]["type"] == "scout"

    def test_empty_request(self):
        tasks = parse_request("")
        assert len(tasks) == 1
        assert tasks[0]["type"] == "ship"


class TestDetectTaskType:
    def test_investigate(self):
        assert detect_task_type("investigate performance") == "scout"

    def test_research(self):
        assert detect_task_type("research best practices") == "scout"

    def test_analyze(self):
        assert detect_task_type("analyze code") == "scout"

    def test_fix(self):
        assert detect_task_type("fix bug") == "ship"

    def test_add(self):
        assert detect_task_type("add feature") == "ship"


class TestDetectPriority:
    def test_urgent(self):
        assert detect_priority("urgent fix") == "high"

    def test_critical(self):
        assert detect_priority("critical bug") == "high"

    def test_hotfix(self):
        assert detect_priority("hotfix login") == "high"

    def test_low_priority(self):
        assert detect_priority("low priority task") == "low"

    def test_normal(self):
        assert detect_priority("fix bug") == "normal"
