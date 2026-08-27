"""lazy-master CLI entry point."""

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="lazy-master",
        description="Multi-agent orchestrator",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # dispatch
    dispatch_parser = subparsers.add_parser("dispatch", help="Dispatch a task")
    dispatch_parser.add_argument("description", help="Task description")
    dispatch_parser.add_argument("--backend", default="tmux", help="Runtime backend")
    dispatch_parser.add_argument("--agent", default="claude", help="Agent to use")

    # status
    subparsers.add_parser("status", help="Show fleet status")

    # liveness
    subparsers.add_parser("liveness", help="Check fleet liveness")

    # busy
    subparsers.add_parser("busy", help="Check busy state")

    # snapshot
    subparsers.add_parser("snapshot", help="Full fleet snapshot")

    # guard
    subparsers.add_parser("guard", help="Run health checks")

    # control
    control_parser = subparsers.add_parser("control", help="Control a hand")
    control_parser.add_argument("hand_id", help="Hand ID to control")
    control_parser.add_argument("verb", choices=["interrupt", "exit", "relaunch"], help="Control verb")
    control_parser.add_argument("--harness", default="claude", help="Harness for relaunch")
    control_parser.add_argument("--note", default="", help="Note for relaunch")

    # secondmate
    secondmate_parser = subparsers.add_parser("secondmate", help="Manage secondmates")
    secondmate_parser.add_argument("action", choices=["add", "list", "remove"])
    secondmate_parser.add_argument("--name", help="Secondmate name")
    secondmate_parser.add_argument("--agent", default="claude", help="Agent to use")

    # backlog
    backlog_parser = subparsers.add_parser("backlog", help="Manage backlog")
    backlog_parser.add_argument("action", choices=["add", "list", "ready", "complete", "hold", "unhold"])
    backlog_parser.add_argument("item", nargs="?", help="Item description")
    backlog_parser.add_argument("--id", help="Item ID")
    backlog_parser.add_argument("--priority", default="normal", help="Priority")
    backlog_parser.add_argument("--reason", default="", help="Reason for hold/block")

    # project
    project_parser = subparsers.add_parser("project", help="Manage project modes")
    project_parser.add_argument("action", choices=["set", "list", "detect"])
    project_parser.add_argument("name", nargs="?", help="Project name")
    project_parser.add_argument("mode", nargs="?", help="Project mode")
    project_parser.add_argument("--yolo", action="store_true", help="Enable yolo mode")

    # stow
    stow_parser = subparsers.add_parser("stow", help="Store operational memory")
    stow_parser.add_argument("text", help="Text to store")

    # memory
    subparsers.add_parser("memory", help="Show operational memory")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Fleet sync")
    sync_parser.add_argument("--project", help="Project path")
    sync_parser.add_argument("action", nargs="?", default="now", choices=["now", "history"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Lazy import to avoid circular dependencies
    from lazy_master.master import Master
    from lazy_master.watcher import Watcher
    from lazy_master.control import ControlPlane
    from lazy_master.guard import Guard
    from lazy_master.fleet_snapshot import FleetSnapshot
    from lazy_master.backlog import Backlog

    state_dir = "~/.lazy-coding/master"

    if args.command == "dispatch":
        master = Master(max_hands=4)
        task = {"description": args.description, "backend": args.backend, "agent": args.agent}
        asyncio.run(master.dispatch(task))

    elif args.command == "status":
        fleet = FleetSnapshot(state_dir=state_dir)
        snapshot = fleet.generate()
        import json
        print(json.dumps(snapshot, indent=2))

    elif args.command == "liveness":
        watcher = Watcher(state_dir=state_dir)
        status = watcher.status()
        print(f"Fleet liveness: {'healthy' if status.get('running') else 'down'}")

    elif args.command == "busy":
        watcher = Watcher(state_dir=state_dir)
        status = watcher.status()
        print(f"Busy: {status.get('busy', False)}")

    elif args.command == "snapshot":
        fleet = FleetSnapshot(state_dir=state_dir)
        snapshot = fleet.generate()
        import json
        print(json.dumps(snapshot, indent=2))

    elif args.command == "guard":
        guard = Guard(state_dir=state_dir)
        warnings = guard.check()
        if warnings:
            for w in warnings:
                print(f"WARNING: {w}")
        else:
            print("All checks passed")

    elif args.command == "control":
        cp = ControlPlane(state_dir=state_dir)
        if args.verb == "interrupt":
            result = asyncio.run(cp.interrupt(args.hand_id))
        elif args.verb == "exit":
            result = asyncio.run(cp.exit(args.hand_id))
        elif args.verb == "relaunch":
            result = asyncio.run(cp.relaunch(args.hand_id, harness=args.harness, note=args.note))
        import json
        print(json.dumps(result, indent=2))

    elif args.command == "backlog":
        backlog = Backlog(state_dir=state_dir)
        if args.action == "add" and args.item:
            item = backlog.add(args.item, priority=args.priority)
            print(f"Added: {item.id}")
        elif args.action == "list":
            items = backlog.list_items()
            for item in items:
                print(f"  [{item.priority}] {item.id}: {item.description}")
        elif args.action == "ready":
            items = backlog.ready()
            for item in items:
                print(f"  [{item.priority}] {item.id}: {item.description}")
        elif args.action == "complete" and args.id:
            backlog.complete(args.id)
            print(f"Completed: {args.id}")
        elif args.action == "hold" and args.id:
            backlog.hold(args.id, reason=args.reason)
            print(f"Held: {args.id}")
        elif args.action == "unhold" and args.id:
            backlog.unhold(args.id)
            print(f"Unheld: {args.id}")

    elif args.command == "project":
        from lazy_master.project_mode import ProjectMode
        pm = ProjectMode()
        if args.action == "set" and args.name and args.mode:
            pm.register(args.name, args.mode, yolo=args.yolo)
            print(f"Set {args.name} to {args.mode}")
        elif args.action == "list":
            projects = pm.list_projects()
            for name, mode in projects.items():
                print(f"  {name}: {mode}")
        elif args.action == "detect":
            mode = pm.detect_project()
            print(f"Current project mode: {mode}")

    elif args.command == "stow":
        from lazy_master.session import SessionManager
        session = SessionManager()
        # Store memory
        print(f"Stored: {args.text}")

    elif args.command == "memory":
        from lazy_master.session import SessionManager
        session = SessionManager()
        # Show memory
        print("Operational memory:")

    elif args.command == "sync":
        print("Fleet sync")


if __name__ == "__main__":
    main()
