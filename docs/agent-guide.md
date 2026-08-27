# Agent Guide

How AI agents (Claude, OpenCode) should use lazy-coding.

## Agent Instructions

When you receive a coding task, follow this workflow:

### 1. Set environment

```bash
source D:\lazy-coding\agent.sh
```

### 2. Get worktree

```bash
python -m lazy_pool.cli get
```

Returns worktree path. Work in that directory.

### 3. Write test first (RED)

```python
def test_feature():
    result = feature()
    assert result == expected
```

Run test - expect failure.

### 4. Implement (GREEN)

Write minimal code to pass the test.

### 5. Push through gate

```bash
python -m lazy_gate.cli push
```

### 6. Return worktree

```bash
python -m lazy_pool.cli return <worktree-path>
```

## Available Commands

### Pool (worktree management)

```bash
python -m lazy_pool.cli get              # Get a worktree
python -m lazy_pool.cli return <path>    # Return a worktree
python -m lazy_pool.cli status           # Pool status
```

### Gate (validation pipeline)

```bash
python -m lazy_gate.cli push             # Push through gate
python -m lazy_gate.cli status           # Gate status
python -m lazy_gate.cli pipeline         # Run validation
```

### Master (orchestration)

```bash
python -m lazy_master.cli status         # Fleet status
python -m lazy_master.cli guard          # Health checks
python -m lazy_master.cli snapshot       # Full status
python -m lazy_master.cli control <id> interrupt   # Control task
```

### Backlog

```bash
python -m lazy_master.cli backlog add "task description"
python -m lazy_master.cli backlog list
python -m lazy_master.cli backlog ready
```

## Rules

1. Always use TDD - write test before code
2. Always use worktrees - never modify files directly
3. Always push through gate - never push directly
4. Return worktree when done
