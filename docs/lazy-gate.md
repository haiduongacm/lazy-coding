# lazy-gate

Git gate + pipeline validation with step-based executor.

## Usage

```python
from lazy_gate.gate import Gate
from lazy_gate.pipeline import Pipeline, Executor, StepName, StepContext, StepOutcome

# Gate
gate = Gate("/path/to/repo")
result = gate.push()

# Pipeline (high-level)
pipeline = Pipeline(stages=["review", "test", "lint"])
result = pipeline.run("/path/to/repo", branch="main")

# Executor (low-level)
from lazy_gate.pipeline import BaseStep
steps = [BaseStep(StepName.TEST, commands={"test": ["python", "-m", "pytest"]})]
executor = Executor(steps=steps)
result = executor.execute(work_dir="/path/to/repo", run_id="run-1")
```

## CLI

```bash
# Push through gate
lazy-gate push

# Push specific branch
lazy-gate push main
```

## Pipeline Architecture

### Step Protocol

Each pipeline step implements the `Step` protocol:

```python
class Step(Protocol):
    def name(self) -> StepName: ...
    def execute(self, ctx: StepContext) -> StepOutcome: ...
```

### Built-in Steps

| Step | Description |
|------|-------------|
| `ReviewStep` | Code review |
| `RunTestStep` | Run tests |
| `LintStep` | Lint code |
| `DocumentStep` | Documentation check |

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
    needs_approval: bool      # Pause for user action
    auto_fixable: bool        # Can auto-fix
    findings: list[Finding]   # Code review findings
    error: Optional[str]      # Error message
    skip_remaining: bool      # Skip all remaining steps
    restart_from: Optional[StepName]  # Restart from earlier step
    fix_summary: Optional[str]        # Commit summary for fix
```

### Finding

```python
@dataclass
class Finding:
    id: str
    file: str
    line: int
    message: str
    severity: str = "warning"   # warning, error, info
    action: str = "ask-user"    # ask-user, auto-fix
```

### Events

Executor emits events via callback:

```python
def on_event(event: dict):
    if event["type"] == "step_completed":
        print(f"Step {event['step']}: {event['status']}")

executor = Executor(steps=steps, on_event=on_event)
```

Event types:
- `run_started` / `run_completed`
- `step_started` / `step_completed` / `step_skipped`
- `step_awaiting_approval`

## Configuration

Default stages: `["review", "test", "lint"]`

Default commands:
- review: `python -c "print('Review passed')"`
- test: `python -m pytest --tb=short`
- lint: `python -m ruff check .`
- document: `python -c "print('Docs check passed')"`
