"""lazy-gate CLI."""

import sys
import json
from .gate import Gate


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] == "help":
        show_help()
        return

    gate = Gate()

    if args[0] == "push":
        branch = args[1] if len(args) > 1 else None
        result = gate.push(branch)
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)


def show_help():
    print("""
lazy-gate - Git gate + pipeline validation

Usage:
  lazy-gate push [branch]   Push through gate
  lazy-gate help            Show this help
""")
