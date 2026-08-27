# Setup Guide

How to use lazy-coding with your projects.

## Step 1: Clone lazy-coding (one time)

```bash
git clone https://github.com/haiduongacm/lazy-coding.git D:\lazy-coding
```

## Step 2: In your project, create CLAUDE.md

Create `D:\my-app\CLAUDE.md`:

```markdown
# Agent Instructions

Always source lazy-coding before any task:

1. source D:\lazy-coding\agent.sh
2. Use lazy-pool for worktrees
3. Use lazy-gate for validation
4. Use lazy-master for orchestration

## Workflow

When user requests a task:

1. python -m lazy_pool.cli get
2. Write test first (RED)
3. Implement (GREEN)
4. python -m lazy_gate.cli push
5. python -m lazy_pool.cli return
```

## Step 3: Create .claude/settings.json

Create `D:\my-app\.claude\settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "source D:\\lazy-coding\\agent.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Step 4: Use

```bash
cd D:\my-app
claude

# Then tell agent:
"Fix login bug"
```

Agent will automatically:
1. Source lazy-coding
2. Get a worktree
3. Write tests
4. Implement code
5. Push through gate
6. Return worktree

## For OpenCode

Create `D:\my-app\.opencode\config.json`:

```json
{
  "agent": {
    "instructions": "Always source D:\\lazy-coding\\agent.sh before any task. Use lazy-pool, lazy-gate, lazy-master for all operations."
  }
}
```

## Directory Structure

After setup:

```
D:\lazy-coding\          ← tools live here (clone once)
├── agent.sh
├── lazy_core/
├── lazy_pool/
├── lazy_gate/
└── lazy_master/

D:\my-app\               ← your project
├── CLAUDE.md            ← tells agent about lazy-coding
├── .claude/
│   └── settings.json    ← hooks to source lazy-coding
└── src/
```
