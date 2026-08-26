"""lazy-core CLI."""

import sys
import json
from .toon import encode, decode
from .principles import PRINCIPLES


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] == "help":
        show_help()
        return

    if args[0] == "encode":
        # Read JSON from stdin, output TOON
        data = json.load(sys.stdin)
        print(encode(data))
    elif args[0] == "decode":
        # Read TOON from stdin, output JSON
        toon = sys.stdin.read()
        data = decode(toon)
        print(json.dumps(data, indent=2))
    elif args[0] == "principles":
        print(encode(PRINCIPLES))
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)


def show_help():
    print("""
lazy-core - TOON format utilities

Usage:
  lazy-core encode          Convert JSON to TOON
  lazy-core decode          Convert TOON to JSON
  lazy-core principles      Show AXI principles
  lazy-core help            Show this help
""")
