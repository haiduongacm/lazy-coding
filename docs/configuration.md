# Configuration

## lazy-coding.toml

```toml
[core]
version = "1.0.0"

[pool]
max_trees = 16
root = "~/.lazy-coding/pools"

[gate]
pipeline = ["review", "test", "lint", "docs", "typecheck"]
auto_fix = true
open_pr = true

[master]
max_hands = 4
backend = "tmux"
agent = "claude"
max_lines = 200
liveness_interval = 10000

[tmux]
session = "lazy-coding"

[view]
port = 4387
auto_open = true
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| LAZY_BACKEND | tmux | Runtime backend |
| LAZY_AGENT | claude | Default agent |
| LAZY_SESSION | lazy-coding | tmux session name |
