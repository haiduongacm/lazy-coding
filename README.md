# lazy-coding

Zero-install AI Coding Agentic Platform for AI agents.

## Quick Start

```bash
# Clone
git clone https://github.com/haiduongacm/lazy-coding.git

# Set environment (one time)
source lazy-coding/agent.sh        # Linux/Mac
# OR
lazy-coding\agent.bat              # Windows

# Use
python -m lazy_master.cli status
python -m lazy_pool.cli get
python -m lazy_gate.cli push
```

## Documentation

- **[Agent Guide](docs/agent-guide.md)** - How to use in Claude/OpenCode
- **[Architecture](docs/architecture.md)** - System design
- **[lazy-master](docs/lazy-master.md)** - Orchestrator API
- **[lazy-gate](docs/lazy-gate.md)** - Pipeline API
- **[lazy-pool](docs/lazy-pool.md)** - Worktree pool API
