# Using lazy-coding in AI Agents

Zero-install guide for Claude, OpenCode, and other AI coding agents.

## Quick Setup

### Step 1: Clone the repo

```bash
git clone https://github.com/haiduongacm/lazy-coding.git
cd lazy-coding
```

### Step 2: Set environment

```bash
# PowerShell (Windows)
$env:PYTHONPATH = "lazy_core/src;lazy_pool/src;lazy_gate/src;lazy_master/src"

# Bash (Linux/Mac)
export PYTHONPATH="lazy_core/src:lazy_pool/src:lazy_gate/src:lazy_master/src"
```

### Step 3: Verify

```bash
python -m lazy_master.cli status
python -m lazy_pool.cli status
python -m lazy_gate.cli status
```

## Agent Configuration

### For Claude

Add to your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "bash(set PYTHONPATH=*)",
      "bash(python -m lazy_*)",
      "bash(cd D:\\lazy-coding && *)"
    ]
  }
}
```

Or add to `~/.claude/CLAUDE.md`:

```markdown
# lazy-coding Tools

When working on code tasks, use lazy-coding tools:

1. Get worktree: `cd D:\lazy-coding && python -m lazy_pool.cli get`
2. Return worktree: `cd D:\lazy-coding && python -m lazy_pool.cli return <path>`
3. Push changes: `cd D:\lazy-coding && python -m lazy_gate.cli push`
4. Check status: `cd D:\lazy-coding && python -m lazy_master.cli status`
```

### For OpenCode

Add to `.opencode/config.json`:

```json
{
  "tools": {
    "lazy_pool": {
      "command": "cd D:\\lazy-coding && python -m lazy_pool.cli",
      "description": "Git worktree pool manager"
    },
    "lazy_gate": {
      "command": "cd D:\\lazy-coding && python -m lazy_gate.cli",
      "description": "Git gate + pipeline validation"
    },
    "lazy_master": {
      "command": "cd D:\\lazy-coding && python -m lazy_master.cli",
      "description": "Multi-agent orchestrator"
    }
  }
}
```

## Agent Workflow

### Standard TDD Workflow

When user requests a task, follow this pattern:

```
User: "Fix login bug in auth module"

Agent actions:
1. cd D:\lazy-coding
2. set PYTHONPATH=lazy_core/src;lazy_pool/src;lazy_gate/src;lazy_master/src
3. python -m lazy_pool.cli get
   → Returns: C:\Users\user\.lazy-coding\pools\worktree-abc123

4. cd C:\Users\user\.lazy-coding\pools\worktree-abc123

5. Write test FIRST (RED phase)
   cat > tests/test_auth_fix.py << 'EOF'
   def test_login_with_valid_credentials():
       result = login("user", "pass")
       assert result.success is True
   EOF

6. Run test - expect FAIL
   python -m pytest tests/test_auth_fix.py
   → FAIL (RED)

7. Write implementation (GREEN phase)
   cat > src/auth.py << 'EOF'
   def login(username, password):
       return LoginResult(success=True)
   EOF

8. Run test - expect PASS
   python -m pytest tests/test_auth_fix.py
   → PASS (GREEN)

9. Push through gate
   cd D:\lazy-coding
   python -m lazy_gate.cli push
   → PR created

10. Return worktree
    python -m lazy_pool.cli return C:\Users\user\.lazy-coding\pools\worktree-abc123
```

### Fleet Management

```bash
# Check fleet status
python -m lazy_master.cli status

# Monitor liveness
python -m lazy_master.cli liveness

# Check busy state
python -m lazy_master.cli busy

# Run health checks
python -m lazy_master.cli guard

# Full snapshot
python -m lazy_master.cli snapshot
```

### Control Plane

```bash
# Interrupt a task
python -m lazy_master.cli control task-1 interrupt

# Exit a task
python -m lazy_master.cli control task-1 exit

# Relaunch a task
python -m lazy_master.cli control task-1 relaunch --harness claude
```

### Backlog Management

```bash
# Add task
python -m lazy_master.cli backlog add "Fix login bug" --priority high

# List tasks
python -m lazy_master.cli backlog list

# Get ready tasks
python -m lazy_master.cli backlog ready

# Complete task
python -m lazy_master.cli backlog complete task-1
```

## Python API (No CLI)

If you prefer importing directly:

```python
import sys
sys.path.insert(0, "D:\\lazy-coding\\lazy_core\\src")
sys.path.insert(0, "D:\\lazy-coding\\lazy_pool\\src")
sys.path.insert(0, "D:\\lazy-coding\\lazy_gate\\src")
sys.path.insert(0, "D:\\lazy-coding\\lazy_master\\src")

# Pool
from lazy_pool.pool import Pool
pool = Pool()
worktree = pool.get()

# Gate
from lazy_gate.gate import Gate
gate = Gate(worktree)
gate.push()

# Master
from lazy_master.watcher import Watcher
from lazy_master.control import ControlPlane
from lazy_master.fleet_snapshot import FleetSnapshot

watcher = Watcher(state_dir="~/.lazy-coding/master")
status = watcher.status()

cp = ControlPlane(state_dir="~/.lazy-coding/master")
await cp.interrupt("task-1")

fleet = FleetSnapshot(state_dir="~/.lazy-coding/master")
snapshot = fleet.generate()
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONPATH` | - | Must include src directories |
| `LAZY_STATE_DIR` | `~/.lazy-coding` | State directory |
| `LAZY_BACKEND` | `tmux` | Runtime backend |
| `LAZY_AGENT` | `claude` | Default agent |

## Troubleshooting

### "ModuleNotFoundError: No module named 'lazy_'"

```bash
# Ensure PYTHONPATH is set
echo $PYTHONPATH  # Should show src paths

# Or set it explicitly
export PYTHONPATH="D:/lazy-coding/lazy_core/src:D:/lazy-coding/lazy_pool/src:D:/lazy-coding/lazy_gate/src:D:/lazy-coding/lazy_master/src"
```

### "Command not found: lazy-master"

Use Python module syntax instead:
```bash
python -m lazy_master.cli status
```

### Permission denied on Windows

```powershell
# Run PowerShell as Administrator, or
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Example Agent Prompt

Use this prompt to configure your agent:

```
You are a lazy-coding agent. When working on code tasks:

1. Always use TDD (Test-Driven Development)
2. Get a worktree before making changes
3. Write tests first, then implement
4. Push through the gate, never directly
5. Return the worktree when done

Tools available:
- python -m lazy_pool.cli get/return/status
- python -m lazy_gate.cli push/status/pipeline
- python -m lazy_master.cli status/guard/control

Workflow:
1. cd D:\lazy-coding
2. set PYTHONPATH=lazy_core/src;lazy_pool/src;lazy_gate/src;lazy_master/src
3. Get worktree
4. Write test (RED)
5. Implement (GREEN)
6. Push through gate
7. Return worktree
```
