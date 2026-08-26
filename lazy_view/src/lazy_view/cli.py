"""lazy-view CLI."""

import sys
import json
from .viewer import Viewer


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] == "help":
        show_help()
        return

    viewer = Viewer()

    if args[0] == "open":
        if len(args) < 2:
            print("error: Specify HTML file", file=sys.stderr)
            sys.exit(1)
        result = viewer.open(args[1])
        print(json.dumps(result, indent=2))
    elif args[0] == "stop":
        viewer.stop()
        print(json.dumps({"stopped": True}))
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)


def show_help():
    print("""
lazy-view - HTML artifact review tool

Usage:
  lazy-view open <file.html>   Open HTML file
  lazy-view stop               Stop viewer server
  lazy-view help               Show this help
""")
