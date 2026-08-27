# lazy-coding

AI Coding Agentic Platform - Zero-install, token-efficient, agent-native

## Features

| Package | Lines | Parity | Description |
|---------|-------|--------|-------------|
| **lazy-core** | 174 | 100% | TOON format encoder/decoder, AXI principles |
| **lazy-pool** | 438 | 82% | Git worktree pool manager |
| **lazy-gate** | 1,108 | 75% | Git gate + pipeline validation |
| **lazy-master** | 3,000+ | 85% | Multi-agent orchestrator |
| **lazy-view** | - | - | HTML artifact review tool |

## Installation

```bash
# Install with uv (recommended)
uv pip install -e lazy_core -e lazy_pool -e lazy_gate -e lazy_master -e lazy_view

# Or install with pip
pip install -e lazy_core -e lazy_pool -e lazy_gate -e lazy_master -e lazy_view
```

## Quick Start

```bash
# Pool management
lazy-pool get              # Get a worktree
lazy-pool return           # Return a worktree
lazy-pool status           # Show pool status

# Gate validation
lazy-gate push             # Push through gate

# Multi-agent orchestration
lazy-master dispatch "fix bug"
lazy-master status
lazy-master control <handId> interrupt

# HTML review
lazy-view open index.html
```

## TOON Format

TOON (Token-Optimized Object Notation) uses ~40% fewer tokens than JSON.

```bash
# Encode JSON to TOON
echo '{"name":"test","items":[1,2,3]}' | lazy-core encode

# Decode TOON to JSON
echo "name: test
items[3]:
  1
  2
  3" | lazy-core decode
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    lazy-master                           │
├─────────────────────────────────────────────────────────┤
│  dispatch() → lazy-hand → tmux backend → agent          │
│       │              ↑                                   │
│  watcher() ─────────┘  (daemon loop, signal scan)       │
│  control() ──────────── (interrupt/exit/relaunch)       │
│  guard() ────────────── (health checks)                 │
│  snapshot() ─────────── (fleet status)                  │
│  session() ──────────── (bootstrap, lock)               │
│  backlog() ──────────── (task queue)                    │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│                    lazy-gate                             │
├─────────────────────────────────────────────────────────┤
│  Pipeline: review → test → lint → document → push → PR  │
│  Executor: step-based, approval gates, fix-loop         │
│  Gate: init, eject, push, status                        │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│                    lazy-pool                             │
├─────────────────────────────────────────────────────────┤
│  Layout: canonical, contains, placement                 │
│  Pool: get, return, prune                               │
│  State: atomic write, lock, placement                   │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│                    lazy-core                             │
├─────────────────────────────────────────────────────────┤
│  TOON: encode/decode (40% fewer tokens)                 │
│  Errors: AxiError, exit codes                           │
│  Output: collapse home, render                          │
│  Principles: 10 AXI design rules                       │
└─────────────────────────────────────────────────────────┘
```

## Commands

```bash
# Dispatch
lazy-master dispatch "fix login bug"
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

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=lazy_core --cov=lazy_pool --cov=lazy_gate --cov=lazy_master

# Lint
ruff check .

# Type check
mypy .
```

## License

MIT
