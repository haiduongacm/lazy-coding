# Workflow

## Standard Workflow (with TDD)

```
1. Get worktree
   lazy-pool get

2. Write test FIRST (RED)
   cat > tests/test_feature.py << 'EOF'
   def test_feature():
       result = feature()
       assert result == expected
   EOF

3. Watch it fail
   pytest tests/test_feature.py
   # Expected: FAIL

4. Write minimal implementation (GREEN)
   cat > src/feature.py << 'EOF'
   def feature():
       return expected
   EOF

5. Watch it pass
   pytest tests/test_feature.py
   # Expected: PASS

6. Refactor if needed (keep tests green)

7. Push through gate
   lazy-gate push

8. Review HTML output if applicable
   lazy-view open

9. Return worktree
   lazy-pool return
```

## TDD Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

### Red-Green-Refactor Cycle

```
RED → Verify RED → GREEN → Verify GREEN → REFACTOR → Repeat
```

| Phase | Action | Verification |
|-------|--------|--------------|
| RED | Write failing test | Test fails for expected reason |
| GREEN | Write minimal code | Test passes, all tests pass |
| REFACTOR | Clean up code | Tests still green |

## Fleet Management

```
1. Dispatch task
   lazy-master dispatch "fix bug"

2. Monitor
   lazy-master status
   lazy-master liveness

3. Control if needed
   lazy-master control <id> interrupt
   lazy-master control <id> exit
   lazy-master control <id> relaunch

4. Guard before push
   lazy-master guard

5. Push through gate
   lazy-gate push
```

## Pipeline Execution

```
Pipeline.run(repo_path, branch)
    ↓
Executor.execute(steps)
    ↓
Step 1: Review (findings?)
    ↓ approval gate
Step 2: Test (pass?)
    ↓
Step 3: Lint (clean?)
    ↓
Step 4: Document (valid?)
    ↓
Push → PR → CI
```

## Control Plane Operations

### Interrupt
```python
cp = ControlPlane(state_dir="~/.lazy-coding/master")
await cp.interrupt("task-1")  # Send SIGINT via tmux
```

### Exit
```python
await cp.exit("task-1")  # Send Ctrl-C, wait for exit
```

### Relaunch
```python
await cp.relaunch("task-1", harness="claude")  # Kill, restart, restore
```

## Guard Checks

```python
guard = Guard(state_dir="~/.lazy-coding/master")
warnings = guard.check()

# Returns:
# - worktree_tangle: branch divergence
# - watcher_down: daemon not running
# - queued_wakes: pending signals
```

## Fleet Snapshot

```python
fleet = FleetSnapshot()
snapshot = fleet.generate()

# Returns:
# - tasks: list of task statuses
# - backlog: pending/ready items
# - projects: registered projects
# - secondmates: agent summaries
# - warnings: health warnings
```
