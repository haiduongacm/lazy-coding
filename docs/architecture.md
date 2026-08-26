# Architecture

## Overview

lazy-coding is an AI Coding Agentic Platform built in Python.

## Packages

| Package | Description |
|---------|-------------|
| lazy-core | TOON format encoder/decoder |
| lazy-pool | Git worktree pool manager |
| lazy-gate | Git gate + pipeline validation |
| lazy-master | Multi-agent orchestrator |
| lazy-view | HTML artifact review |

## Directory Structure

```
lazy-coding/
├── pyproject.toml           # Root workspace
├── lazy_core/               # TOON format
│   ├── pyproject.toml
│   └── src/lazy_core/
├── lazy_pool/               # Worktree management
│   ├── pyproject.toml
│   └── src/lazy_pool/
├── lazy_gate/               # Git gate
│   ├── pyproject.toml
│   └── src/lazy_gate/
├── lazy_master/             # Orchestrator
│   ├── pyproject.toml
│   └── src/lazy_master/
├── lazy_view/               # HTML review
│   ├── pyproject.toml
│   └── src/lazy_view/
└── tests/                   # Test suite
```

## Data Flow

```
User → lazy-master dispatch → lazy-hand → tmux backend → agent
                ↓
        lazy-pool get (worktree)
                ↓
        agent works in worktree
                ↓
        lazy-gate push (validation)
                ↓
        PR created
```
