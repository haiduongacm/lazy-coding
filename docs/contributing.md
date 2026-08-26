# Contributing

## Development Setup

```bash
# Clone repo
git clone https://github.com/haiduongacm/lazy-coding.git
cd lazy-coding

# Install with uv
uv pip install -e lazy_core -e lazy_pool -e lazy_gate -e lazy_master -e lazy_view

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy .
```

## Code Style

- Python 3.10+
- Type hints required
- Docstrings for all public functions
- TOON format for output

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lazy_core --cov=lazy_pool --cov=lazy_gate --cov=lazy_master

# Run specific test
pytest tests/test_lazy_core/test_toon.py
```
