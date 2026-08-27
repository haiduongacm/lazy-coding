# Agent Guide

How to use lazy-coding in AI agents (Claude, OpenCode, etc.)

## Setup

No installation needed. Just set the environment:

```bash
source D:\lazy-coding\agent.sh
```

Or manually:

```bash
export PYTHONPATH="D:/lazy-coding/lazy_core/src:D:/lazy-coding/lazy_pool/src:D:/lazy-coding/lazy_gate/src:D:/lazy-coding/lazy_master/src"
```

## Usage

```bash
# Pool
python -m lazy_pool.cli get
python -m lazy_pool.cli return <path>
python -m lazy_pool.cli status

# Gate
python -m lazy_gate.cli push
python -m lazy_gate.cli status

# Master
python -m lazy_master.cli status
python -m lazy_master.cli guard
python -m lazy_master.cli dispatch "fix bug"
```

## Agent Workflow

When user requests a task:

```
User: "Fix login bug"

Agent:
  1. source D:\lazy-coding\agent.sh
  2. python -m lazy_pool.cli get
  3. Write test (RED)
  4. Implement (GREEN)
  5. python -m lazy_gate.cli push
  6. python -m lazy_pool.cli return
```

## Configuration

Add to Claude settings (`.claude/settings.json`):

```json
{
  "permissions": {
    "allow": [
      "bash(source D:\\lazy-coding\\agent.sh)",
      "bash(python -m lazy_*)"
    ]
  }
}
```

## Python API

```python
import sys
sys.path.insert(0, "D:/lazy-coding/lazy_core/src")
sys.path.insert(0, "D:/lazy-coding/lazy_pool/src")
sys.path.insert(0, "D:/lazy-coding/lazy_gate/src")
sys.path.insert(0, "D:/lazy-coding/lazy_master/src")

from lazy_pool.pool import Pool
from lazy_gate.gate import Gate
from lazy_master.watcher import Watcher
```
