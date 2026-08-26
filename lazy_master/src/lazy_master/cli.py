"""lazy-master CLI."""

import sys
import json
import asyncio
from .master import LazyMaster
from .dispatcher import parse_request
from .session import create_session, list_sessions


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] == "help":
        show_help()
        return

    if args[0] == "dispatch":
        asyncio.run(handle_dispatch(args[1:]))
    elif args[0] == "status":
        handle_status(args[1:])
    elif args[0] == "liveness":
        asyncio.run(handle_liveness())
    elif args[0] == "busy":
        asyncio.run(handle_busy())
    elif args[0] == "control":
        asyncio.run(handle_control(args[1:]))
    elif args[0] == "guard":
        asyncio.run(handle_guard())
    elif args[0] == "teardown":
        asyncio.run(handle_teardown())
    elif args[0] == "sessions":
        handle_sessions()
    else:
        show_dashboard()


async def handle_dispatch(args):
    """Handle dispatch command."""
    task_str = " ".join(a for a in args if not a.startswith("--"))
    if not task_str:
        print("error: Specify a task description", file=sys.stderr)
        sys.exit(1)

    tasks = parse_request(task_str)
    session = create_session()
    master = LazyMaster()
    await master.init()

    print(f"session: {session['id']}")
    print(f"tasks: {len(tasks)}")
    print()

    for task in tasks:
        result = await master.dispatch(task)
        if result.get("error"):
            print(f"error: {result['message']}")
        else:
            print(f"dispatched: {result['hand_id']} → {task['description']}")
            if result.get("endpoint"):
                print(f"  endpoint: {result['endpoint'].get('window')}")


def handle_status(args):
    """Handle status command."""
    master = LazyMaster()
    status = master.status()

    if "--json" in args:
        print(json.dumps(status, indent=2))
    else:
        print(f"backend: {status.get('backend')}")
        print(f"agent: {status['agent']}")
        print(f"total: {status['total']}")
        print(f"working: {status['working']}")
        print(f"done: {status['done']}")
        print(f"failed: {status['failed']}")


async def handle_liveness():
    """Handle liveness command."""
    master = LazyMaster()
    results = await master.liveness()
    print(json.dumps({"liveness": results}, indent=2))


async def handle_busy():
    """Handle busy command."""
    master = LazyMaster()
    results = await master.busy_states()
    print(json.dumps({"busy": results}, indent=2))


async def handle_control(args):
    """Handle control command."""
    if len(args) < 2:
        print("error: Specify handId and action", file=sys.stderr)
        sys.exit(1)

    hand_id = args[0]
    action = args[1]

    master = LazyMaster()
    result = await master.control_hand(hand_id, action)
    print(json.dumps(result, indent=2))


async def handle_guard():
    """Handle guard command."""
    master = LazyMaster()
    result = await master.guard_check()
    print(json.dumps(result, indent=2))


async def handle_teardown():
    """Handle teardown command."""
    master = LazyMaster()
    results = await master.teardown_all()
    print(json.dumps({"teardown": results}, indent=2))


def handle_sessions():
    """Handle sessions command."""
    sessions = list_sessions()
    print(json.dumps(sessions, indent=2))


def show_dashboard():
    print("""package: lazy-master
version: 1.0.0
role: orchestrator
help:
  Use "lazy-master dispatch <task>" to assign work
  Use "lazy-master status" to monitor fleet""")


def show_help():
    print("""
lazy-master - Multi-agent orchestrator

Usage:
  lazy-master dispatch "<task>"   Dispatch task
  lazy-master status              Show fleet status
  lazy-master liveness            Check agent liveness
  lazy-master busy                Check busy states
  lazy-master control <id> <cmd>  Control hand
  lazy-master guard               Run guard check
  lazy-master teardown            Teardown all
  lazy-master sessions            List sessions
  lazy-master help                Show this help
""")
