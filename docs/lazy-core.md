# lazy-core

TOON format encoder/decoder and shared utilities.

## Usage

```python
from lazy_core import encode, decode

# Encode dict to TOON
data = {"name": "test", "items": [1, 2, 3]}
toon = encode(data)

# Decode TOON to dict
result = decode(toon)
```

## CLI

```bash
# Encode JSON to TOON
echo '{"name":"test"}' | lazy-core encode

# Decode TOON to JSON
echo "name: test" | lazy-core decode

# Show AXI principles
lazy-core principles
```

## API

### `encode(data)`

Encode Python object to TOON format.

### `decode(toon_str)`

Decode TOON format to Python object.

### `PRINCIPLES`

List of 10 AXI design principles.
