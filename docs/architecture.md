# Architecture

## Overview

lazy-coding is an AI Coding Agentic Platform built in Python, faithfully inheriting logic from:
- **axi-sdk-js** (original): TOON format, error handling
- **no-mistakes** (original): Worktree pool, gate pipeline
- **firstmate** (original): Multi-agent orchestration, watcher, control plane
- **superpowers** (original): TDD skill

## Packages

| Package | Lines | Parity | Status |
|---------|-------|--------|--------|
| **lazy-core** | 174 | 100% | Complete |
| **lazy-pool** | 438 | 82% | Complete |
| **lazy-gate** | 1,108 | 75% | Core complete |
| **lazy-master** | 3,000+ | 85% | Complete |
| **lazy-view** | - | - | TBD |
| **Total** | 4,700+ | ~85% | |

## Directory Structure

```
lazy-coding/
├── pyproject.toml              # Root workspace
├── lazy_coding.toml            # Runtime config
├── lazy_core/                  # TOON format
│   ├── src/lazy_core/
│   │   ├── toon.py            # Encoder/decoder
│   │   ├── errors.py          # AxiError, exit codes
│   │   ├── output.py          # Collapse home, render
│   │   ├── principles.py      # AXI design principles
│   │   └── ...
├── lazy_pool/                  # Worktree management
│   ├── src/lazy_pool/
│   │   ├── layout.py          # Placement, canonical, contains
│   │   ├── pool.py            # Get, return, prune
│   │   └── state.py           # Atomic write, lock, placement
├── lazy_gate/                  # Git gate + pipeline
│   ├── src/lazy_gate/
│   │   ├── gate.py            # Init, eject, push, status
│   │   ├── pipeline.py        # Step executor, approval gates
│   │   └── worktree.py        # Worktree operations
├── lazy_master/                # Multi-agent orchestrator
│   ├── src/lazy_master/
│   │   ├── watcher.py         # Daemon loop, signal scan
│   │   ├── control.py         # interrupt/exit/relaunch
│   │   ├── turnend.py         # Blind stop detection
│   │   ├── session.py         # Bootstrap, lock, wake drain
│   │   ├── guard.py           # Health checks
│   │   ├── fleet_snapshot.py  # Full status
│   │   ├── backlog.py         # Task queue
│   │   ├── dispatcher.py      # Task intake
│   │   └── project_mode.py    # Delivery modes
├── lazy_view/                  # HTML review
└── tests/                      # 211 tests
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
        Pipeline: review → test → lint → document → push → PR → CI
                ↓
        PR created on GitHub
```

## Pipeline Architecture

### Step Protocol

```python
class Step(Protocol):
    def name(self) -> StepName: ...
    def execute(self, ctx: StepContext) -> StepOutcome: ...
```

### Executor

Runs steps sequentially with:
- Approval gates (awaiting_approval → user action → continue)
- Fix-loop (fix round → re-review → next step)
- Event streaming (run_started, step_started, step_completed, etc.)
- Skip/restart support

### StepOutcome

```python
@dataclass
class StepOutcome:
    success: bool
    needs_approval: bool
    auto_fixable: bool
    findings: list[Finding]
    error: Optional[str]
    skip_remaining: bool
    restart_from: Optional[StepName]
```

## Original Repos

| Repo | What we inherit | lazy-coding module |
|------|-----------------|-------------------|
| `axi-sdk-js` (original) | TOON format, errors, output | `lazy_core` |
| `no-mistakes` (original) | Worktree pool, gate pipeline | `lazy_pool`, `lazy_gate` |
| `firstmate` (original) | Watcher, control, session, guard | `lazy_master` |
| `superpowers` | TDD skill | AGENTS.md |
| `lavish-axi` | Fleet sync | `lazy_master` |
| `treehouse` | TOON extensions | `lazy_core` |

## Key Design Decisions

1. **Python 3.10+** - Modern async, type hints
2. **TDD mandatory** - No production code without failing test
3. **TOON format** - ~40% fewer tokens than JSON
4. **Tmux backend** - Simple, reliable, debuggable
5. **Episode dedup** - Stale banner claim/clear for guard
6. **Wake classification** - Actionable vs absorb
7. **Step-based pipeline** - Modular, testable, extensible
