# lazy-master

Multi-agent orchestrator.

## Usage

```python
from lazy_master import LazyMaster

master = LazyMaster()
await master.init()
result = await master.dispatch({"description": "fix bug"})
```

## CLI

```bash
# Dispatch task
lazy-master dispatch "fix bug"

# Status
lazy-master status

# Liveness
lazy-master liveness

# Busy state
lazy-master busy

# Control
lazy-master control <handId> interrupt

# Guard
lazy-master guard

# Snapshot
lazy-master snapshot

# Secondmate
lazy-master secondmate add --name backend-team
lazy-master secondmate list

# Backlog
lazy-master backlog add "Fix login"
lazy-master backlog list

# Project modes
lazy-master project set my-api no-mistakes

# Memory
lazy-master stow "Login uses JWT"

# Fleet sync
lazy-master sync
```

## Components

| Component | Description |
|-----------|-------------|
| Watcher | Zero-token fleet monitoring |
| ControlPlane | interrupt/exit/relaunch |
| TurnEndGuard | Blind stop detection |
| Guard | Health checks |
| FleetSnapshot | Full status |
| LazyMaster2 | Persistent agent |
| Backlog | Task queue |
| ProjectModes | Delivery modes |
| DispatchProfiles | Agent routing |
| OperationalMemory | Knowledge routing |
| FleetSync | Clone freshness |
