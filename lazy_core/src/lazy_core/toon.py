"""TOON (Token-Optimized Object Notation) format encoder/decoder.

TOON uses ~40% fewer tokens than JSON by using:
- Minimal delimiters
- Compact list notation
- Inline key-value pairs
- No quotes around strings
"""


def encode(data, indent=0):
    """Encode Python dict/list to TOON format.

    Args:
        data: Python object to encode
        indent: Indentation level

    Returns:
        TOON-formatted string
    """
    if data is None:
        return "null"
    if isinstance(data, bool):
        return "true" if data else "false"
    if isinstance(data, (int, float)):
        return str(data)
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return encode_list(data, indent)
    if isinstance(data, dict):
        return encode_dict(data, indent)
    return str(data)


def encode_list(items, indent=0):
    """Encode list to TOON format."""
    if not items:
        return "[]"

    prefix = "  " * indent
    lines = []

    for item in items:
        if isinstance(item, dict):
            # Inline simple dicts
            values = []
            for k, v in item.items():
                if isinstance(v, (str, int, float, bool)):
                    values.append(f"{k},{v}")
                else:
                    values.append(f"{k}:{encode(v, indent + 1)}")
            lines.append(f"{prefix}  {','.join(values)}")
        elif isinstance(item, list):
            lines.append(f"{prefix}  {encode_list(item, indent + 1)}")
        else:
            lines.append(f"{prefix}  {encode(item, indent + 1)}")

    return f"[{len(items)}]:\n" + "\n".join(lines)


def encode_dict(data, indent=0):
    """Encode dict to TOON format."""
    if not data:
        return "{}"

    prefix = "  " * indent
    lines = []

    for key, value in data.items():
        if isinstance(value, (str, int, float, bool)):
            lines.append(f"{prefix}{key}: {encode(value)}")
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: {encode_list(value, indent)}")
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}: {encode_dict(value, indent + 1)}")
        else:
            lines.append(f"{prefix}{key}: {encode(value)}")

    return "\n".join(lines)


def decode(toon_str):
    """Decode TOON format to Python object.

    Args:
        toon_str: TOON-formatted string

    Returns:
        Python object (dict, list, or scalar)
    """
    if not toon_str or not toon_str.strip():
        return None

    toon_str = toon_str.strip()

    # Try to parse as list
    if toon_str.startswith("[") and "[]:" in toon_str:
        return decode_list(toon_str)

    # Try to parse as dict
    if "\n" in toon_str or ": " in toon_str:
        return decode_dict(toon_str)

    # Scalar
    return decode_scalar(toon_str)


def decode_list(toon_str):
    """Decode TOON list format."""
    lines = toon_str.split("\n")
    items = []

    for line in lines[1:]:  # Skip header line
        line = line.strip()
        if not line:
            continue

        # Check if it's a nested structure
        if line.startswith("[") or line.startswith("{"):
            items.append(decode(line))
        else:
            # Inline dict or scalar
            parts = line.split(",")
            if len(parts) > 1:
                item = {}
                for part in parts:
                    if "," in part:
                        k, v = part.split(",", 1)
                        item[k.strip()] = decode_scalar(v.strip())
                    else:
                        item[part.strip()] = True
                items.append(item)
            else:
                items.append(decode_scalar(line))

    return items


def decode_dict(toon_str):
    """Decode TOON dict format."""
    result = {}
    lines = toon_str.split("\n")

    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        # Check if value is a nested structure
        if value.startswith("[") or value.startswith("{"):
            result[key] = decode(value)
        else:
            result[key] = decode_scalar(value)

    return result


def decode_scalar(value):
    """Decode scalar value."""
    if not value:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
