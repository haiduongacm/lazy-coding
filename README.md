# lazy-coding

Zero-install AI Coding Agentic Platform for AI agents.

## Setup

### 1. Clone lazy-coding (one time)

```bash
git clone https://github.com/haiduongacm/lazy-coding.git D:\lazy-coding
```

### 2. In your project, create CLAUDE.md

Create `D:\my-app\CLAUDE.md`:

```markdown
# Agent Instructions

When working on this project:

1. source D:\lazy-coding\agent.sh
2. Use lazy-pool for worktrees
3. Use lazy-gate for validation
4. Use lazy-master for orchestration
5. Always use TDD
```

### 3. Create .claude/settings.json

Create `D:\my-app\.claude\settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "source D:\\lazy-coding\\agent.sh"
      }]
    }]
  }
}
```

### 4. Use

```bash
cd D:\my-app
claude
# Tell agent: "Fix login bug"
```

## Docs

- **[Agent Guide](docs/agent-guide.md)** - Agent workflow
- **[Architecture](docs/architecture.md)** - System design
