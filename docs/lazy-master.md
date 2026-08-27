# lazy-master

Multi-agent orchestrator with tmux backend, control plane, fleet management.

## Usage

```python
from lazy_master import (
    Master, LazyHand, Watcher, ControlPlane,
    TurnEndGuard, SessionManager, FleetSnapshot,
    Backlog, Guard, Dispatcher, ProjectMode,
)

# Dispatch task
master = Master(max_hands=4)
hand = await master.dispatch({"description": "fix bug"})

# Watcher (daemon loop)
watcher = Watcher(state_dir="~/.lazy-coding/master")
await watcher.main_loop()

# Control plane
cp = ControlPlane(state_dir="~/.lazy-coding/master")
await cp.interrupt("task-1")
await cp.exit("task-1")
await cp.relaunch("task-1", harness="claude")

# Turn-end guard
guard = TurnEndGuard()
if guard.should_block():
    guard.acknowledge()

# Session manager
session = SessionManager()
await session.bootstrap()

# Fleet snapshot
fleet = FleetSnapshot()
snapshot = fleet.generate()
```

## CLI

```bash
# Dispatch task
lazy-master dispatch "fix bug"
lazy-master dispatch --backend tmux --agent claude "fix bug"

# Status
lazy-master status
lazy-master liveness
lazy-master busy
lazy-master snapshot

# Control
lazy-master control <handId> interrupt
lazy-master control <handId> exit
lazy-master control <handId> relaunch

# Guard
lazy-master guard

# Secondmate
lazy-master secondmate add --name backend-team --agent claude
lazy-master secondmate list

# Backlog
lazy-master backlog add "Fix login bug"
lazy-master backlog list
lazy-master backlog ready

# Project modes
lazy-master project set my-api no-mistakes
lazy-master project set my-scripts local-only --yolo

# Operational memory
lazy-master stow "Login uses JWT tokens"
lazy-master memory

# Fleet sync
lazy-master sync
lazy-master sync --project ~/projects/api
lazy-master sync history
```

## Components

| Component | File | Description |
|-----------|------|-------------|
| `Master` | `master.py` | Main orchestrator |
| `LazyHand` | `hand.py` | Single agent instance |
| `Watcher` | `watcher.py` | Daemon loop, signal scan, wedge detection |
| `ControlPlane` | `control.py` | interrupt/exit/relaunch with adapter delivery |
| `TurnEndGuard` | `turnend.py` | Blind stop detection, epoch budget |
| `SessionManager` | `session.py` | Bootstrap, lock, wake drain |
| `FleetSnapshot` | `fleet_snapshot.py` | Full status, crew state, secondmate summaries |
| `Backlog` | `backlog.py` | Task queue with dependencies, holds |
| `Guard` | `guard.py` | Health checks, episode dedup |
| `Dispatcher` | `dispatcher.py` | Task intake, priority detection |
| `ProjectMode` | `project_mode.py` | Delivery mode resolution |

## Watcher Daemon

The watcher runs as a background daemon:

```python
watcher = Watcher(state_dir="~/.lazy-coding/master")

# Acquire exclusive lock
if watcher.acquire_lock():
    # Run main loop
    await watcher.main_loop()
```

Main loop features:
- Signal scan (wedge detection, busy turn bounds)
- Secondmate wake stall detection
- Heartbeat scan (fleet liveness)
- Inbox steer check
- Wake classification (actionable vs absorb)

## Control Plane

```python
cp = ControlPlane(state_dir="~/.lazy-coding/master")

# Check if agent exists
exists = await cp._target_exists("task-1")

# Get agent state (tmux has-session)
state = await cp._agent_state("task-1")

# Send tmux key
await cp._send_key("task-1", "C-c")

# Interrupt with adapter delivery
result = await cp.interrupt("task-1")

# Exit with wait
result = await cp.exit("task-1")

# Relaunch with checkpoint
result = await cp.relaunch("task-1", harness="claude", note="switching")
```

## Turn-End Guard

```python
guard = TurnEndGuard(
    epoch_budget=10,
    stale_timeout=30,
    hook_timeout=5,
)

# Check if should block
if guard.should_block():
    print("Blocked:", guard.get_status())
    guard.acknowledge()

# Per-task status
status = guard.get_status_for_task("task-1")
```

## Fleet Snapshot

```python
fleet = FleetSnapshot()
snapshot = fleet.generate()

# Fields:
# - tasks: list of task statuses
# - backlog: pending/ready items
# - projects: registered projects
# - secondmates: agent summaries
# - warnings: health warnings
# - timestamp: generation time
```

## Backlog

```python
backlog = Backlog(state_dir="~/.lazy-coding/master")

# Add item
item = backlog.add("Fix login bug", priority="high", dependencies=["auth-refactor"])

# List items
items = backlog.list_items()

# Get ready items (no unmet dependencies)
ready = backlog.ready()

# Hold/unhold
backlog.hold("task-1", reason="blocked")
backlog.unhold("task-1")

# Complete
backlog.complete("task-1")

# Block
backlog.block("task-1", reason="needs API key")
```
