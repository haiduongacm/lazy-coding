# lazy-pool

Git worktree pool manager.

## Usage

```python
from lazy_pool import Pool

pool = Pool()
path = pool.get()
pool.return_worktree(path)
```

## CLI

```bash
# Get a worktree
lazy-pool get

# Get with durable lease
lazy-pool get --lease

# Return a worktree
lazy-pool return /path/to/worktree

# Show pool status
lazy-pool status

# Prune idle worktrees
lazy-pool prune --yes
```

## API

### `Pool(repo_path=None, state_dir=None)`

Create a pool manager.

### `pool.get(lease=False)`

Acquire a worktree from the pool.

### `pool.return_worktree(path=None)`

Return a worktree to the pool.

### `pool.status()`

Get pool status.
