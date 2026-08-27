"""lazy-gate CLI entry point."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="lazy-gate",
        description="Git gate + pipeline validation",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize gate")
    init_parser.add_argument("path", nargs="?", default=".", help="Repository path")

    # push
    push_parser = subparsers.add_parser("push", help="Push through gate")
    push_parser.add_argument("branch", nargs="?", help="Branch to push")
    push_parser.add_argument("--path", default=".", help="Repository path")

    # status
    status_parser = subparsers.add_parser("status", help="Show gate status")
    status_parser.add_argument("--path", default=".", help="Repository path")

    # eject
    eject_parser = subparsers.add_parser("eject", help="Remove gate")
    eject_parser.add_argument("--path", default=".", help="Repository path")

    # pipeline
    pipeline_parser = subparsers.add_parser("pipeline", help="Run pipeline")
    pipeline_parser.add_argument("--path", default=".", help="Repository path")
    pipeline_parser.add_argument("--branch", help="Branch to validate")
    pipeline_parser.add_argument("--stages", nargs="+", default=["review", "test", "lint"], help="Stages to run")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    from lazy_gate.gate import Gate
    from lazy_gate.pipeline import Pipeline

    if args.command == "init":
        gate = Gate(args.path)
        result = gate.init()
        if result:
            print("Gate initialized")
        else:
            print("Gate already initialized")

    elif args.command == "push":
        gate = Gate(args.path)
        result = gate.push(branch=args.branch)
        import json
        print(json.dumps(result, indent=2))

    elif args.command == "status":
        gate = Gate(args.path)
        status = gate.status()
        import json
        print(json.dumps(status, indent=2))

    elif args.command == "eject":
        gate = Gate(args.path)
        result = gate.eject()
        print("Gate ejected")

    elif args.command == "pipeline":
        pipeline = Pipeline(stages=args.stages)
        result = pipeline.run(args.path, branch=args.branch)
        import json
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
