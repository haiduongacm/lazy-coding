# lazy-coding

AI Coding Agentic Platform - Zero-install, token-efficient, agent-native

## Features

- **lazy-core**: TOON format encoder/decoder, AXI principles
- **lazy-pool**: Git worktree pool manager
- **lazy-gate**: Git gate + pipeline validation
- **lazy-master**: Multi-agent orchestrator with tmux backend
- **lazy-view**: HTML artifact review tool

## Installation

```bash
# Install with uv (recommended)
uv pip install -e lazy_core -e lazy_pool -e lazy_gate -e lazy_master -e lazy_view

# Or install with pip
pip install -e lazy_core -e lazy_pool -e lazy_gate -e lazy_master -e lazy_view
```

## Usage

```bash
# Pool management
lazy-pool get
lazy-pool return
lazy-pool status

# Gate validation
lazy-gate push

# Multi-agent orchestration
lazy-master dispatch "fix bug"
lazy-master status
lazy-master control <handId> interrupt

# HTML review
lazy-view open index.html
```

## TOON Format

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

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Type check
mypy .
```

## License

MIT
