# lazy-coding

Zero-install AI Coding Agentic Platform for AI agents (Claude, OpenCode, etc.)

## Quick Start (for AI Agents)

```bash
git clone https://github.com/haiduongacm/lazy-coding.git
cd lazy-coding
set PYTHONPATH=lazy_core/src;lazy_pool/src;lazy_gate/src;lazy_master/src

# Ready to use
python -m lazy_master.cli status
python -m lazy_pool.cli get
python -m lazy_gate.cli push
```

**No pip install needed. Just clone and run.**

## Documentation

- **[Agent Guide](docs/agent-guide.md)** - How to use in Claude/OpenCode
- **[Architecture](docs/architecture.md)** - System design
- **[lazy-master](docs/lazy-master.md)** - Orchestrator API
- **[lazy-gate](docs/lazy-gate.md)** - Pipeline API
- **[lazy-pool](docs/lazy-pool.md)** - Worktree pool API

## Trong Claude

Khi bạn yêu cầu Claude làm task:

```
Bạn: "Fix login bug"

Claude:
  1. cd D:\lazy-coding
  2. python -m lazy_pool.cli get
  3. Viết test, code trong worktree
  4. python -m lazy_gate.cli push
  5. python -m lazy_pool.cli return
```

Không cần cài đặt. Không cần pip. Chỉ cần clone và chạy.
