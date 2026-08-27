"""lazy-pool CLI entry point."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="lazy-pool",
        description="Git worktree pool manager",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # get
    get_parser = subparsers.add_parser("get", help="Get a worktree")
    get_parser.add_argument("--lease", action="store_true", help="Durable lease")
    get_parser.add_argument("--repo", default=".", help="Repository path")

    # return
    return_parser = subparsers.add_parser("return", help="Return a worktree")
    return_parser.add_argument("path", nargs="?", help="Worktree path to return")
    return_parser.add_argument("--repo", default=".", help="Repository path")

    # status
    status_parser = subparsers.add_parser("status", help="Show pool status")
    status_parser.add_argument("--repo", default=".", help="Repository path")

    # prune
    prune_parser = subparsers.add_parser("prune", help="Prune idle worktrees")
    prune_parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    prune_parser.add_argument("--repo", default=".", help="Repository path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    from lazy_pool.pool import Pool

    pool = Pool(repo_path=args.repo)

    if args.command == "get":
        path = pool.get(lease=args.lease)
        if path:
            print(path)
        else:
            print("No worktrees available", file=sys.stderr)
            sys.exit(1)

    elif args.command == "return":
        pool.return_worktree(args.path)
        print("Worktree returned")

    elif args.command == "status":
        status = pool.status()
        import json
        print(json.dumps(status, indent=2))

    elif args.command == "prune":
        if not args.yes:
            confirm = input("Prune idle worktrees? [y/N] ")
            if confirm.lower() != "y":
                print("Aborted")
                sys.exit(0)
        pruned = pool.prune()
        print(f"Pruned {pruned} worktrees")


if __name__ == "__main__":
    main()
