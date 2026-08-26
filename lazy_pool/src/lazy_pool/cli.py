"""lazy-pool CLI."""

import sys
import json
from .pool import Pool
from .state import State


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] == "help":
        show_help()
        return

    pool = Pool()

    if args[0] == "get":
        lease = "--lease" in args
        path = pool.get(lease=lease)
        print(json.dumps({"path": str(path)}, indent=2))
    elif args[0] == "return":
        path = args[1] if len(args) > 1 else None
        pool.return_worktree(path)
        print(json.dumps({"returned": True}))
    elif args[0] == "status":
        status = pool.status()
        print(json.dumps(status, indent=2))
    elif args[0] == "prune":
        dry_run = "--yes" not in args
        pruned = pool.prune(dry_run=dry_run)
        print(json.dumps({"pruned": pruned}))
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)


def show_help():
    print("""
lazy-pool - Git worktree pool manager

Usage:
  lazy-pool get             Get a worktree
  lazy-pool get --lease     Get with durable lease
  lazy-pool return [path]   Return a worktree
  lazy-pool status          Show pool status
  lazy-pool prune           Dry-run prune
  lazy-pool prune --yes     Actually prune
  lazy-pool help            Show this help
""")
