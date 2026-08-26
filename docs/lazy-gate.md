# lazy-gate

Git gate + pipeline validation.

## Usage

```python
from lazy_gate import Gate

gate = Gate()
result = gate.push()
```

## CLI

```bash
# Push through gate
lazy-gate push

# Push specific branch
lazy-gate push main
```

## Pipeline Stages

| Stage | Description |
|-------|-------------|
| review | Code review |
| test | Run tests |
| lint | Lint code |
| docs | Check documentation |
| typecheck | Type checking |
