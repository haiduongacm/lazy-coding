# lazy-coding

Zero-install AI Coding Agentic Platform for AI agents.

## Setup

### 1. Clone lazy-coding (one time)

```bash
git clone https://github.com/haiduongacm/lazy-coding.git D:\lazy-coding
```

### 2. In your project, create CLAUDE.md

```markdown
@D:\lazy-coding\docs\agent-guide.md
```

### 3. Create .claude/settings.json

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
