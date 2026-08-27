"""lazy-master watcher - Zero-token fleet monitoring daemon.

Mirrors lazy-master's watch script: the watcher polls fleet state without
consuming tokens, detects stale workers, and triggers wake events.

Key concepts from lazy-master watch:
- Singleton lock to prevent duplicate watchers
- Poll cycle with configurable interval
- Heartbeat scans for fleet health
- Wake queue for durable events
- Stale detection with wedge escalation
- AFK mode awareness
- Steering-inbox loss detection
- lazy-master2 wake-loop stall detection
"""

import os
import time
import json
import subprocess
import signal
from pathlib import Path
from typing import Any, Callable, Optional
from datetime import datetime, timezone


# Constants matching lazy-master watch
POLL_DEFAULT = 15
HEARTBEAT_DEFAULT = 600
HEARTBEAT_MAX = 7200
CHECK_INTERVAL = 300
CHECK_TIMEOUT = 30
SIGNAL_GRACE = 30
STALE_ESCALATE_SECS = 240
BUSY_TURN_MAX_SECS = 3600
SECONDMATE_WAKE_STALL_SECS = 60
PAUSE_RESURFACE_SECS = 1800
FM_WEDGE_DEMAND_INSPECT_COUNT = 3
EVENT_CAP_FAIL_MAX = 3


class Watcher:
    """Fleet watcher daemon - monitors worker liveness.

    Mirrors lazy-master's watcher: zero-token monitoring, detects stale workers,
    triggers wake events for the supervision protocol.
    """

    def __init__(self, state_dir: str | None = None, poll_interval: int = POLL_DEFAULT,
                 heartbeat_interval: int = HEARTBEAT_DEFAULT, stale_grace: int = 300):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.stale_grace = stale_grace
        self.lock_file = self.state_dir / ".watch.lock"
        self.wake_queue = self.state_dir / ".wake-queue"
        self.watcher_down_marker = self.state_dir / ".watcher-down"
        self.last_beat_file = self.state_dir / ".last-watcher-beat"
        self.afk_file = self.state_dir / ".afk"
        self.running = False
        self.last_activity: dict[str, float] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._wake_count = 0
        self._wedge_escalations: dict[str, int] = {}
        self._hash_cache: dict[str, str] = {}
        self._stale_since: dict[str, float] = {}
        self._pause_resurface: dict[str, float] = {}
        self._event_cap_fails = 0
        self._event_cap_key = ""
        self._event_cap_ok = False

    def acquire_lock(self) -> bool:
        """Acquire singleton watcher lock."""
        try:
            self.lock_file.touch(exist_ok=False)
            return True
        except FileExistsError:
            if self.lock_file.exists():
                age = time.time() - self.lock_file.stat().st_mtime
                if age > self.stale_grace:
                    self.lock_file.unlink(missing_ok=True)
                    return self.acquire_lock()
            return False

    def release_lock(self) -> None:
        """Release watcher lock."""
        self.lock_file.unlink(missing_ok=True)

    def record_activity(self, worker_id: str) -> None:
        """Record activity timestamp for a worker."""
        self.last_activity[worker_id] = time.time()

    def is_afk(self) -> bool:
        """Check if away mode is active."""
        return self.afk_file.exists()

    def touch_beat(self) -> None:
        """Touch watcher liveness beacon."""
        self.last_beat_file.touch()

    def check_worker_liveness(self, worker_id: str) -> dict[str, Any]:
        """Check if a worker is still alive."""
        last = self.last_activity.get(worker_id)
        if last is None:
            return {
                "alive": False,
                "reason": "no_activity_recorded",
                "worker_id": worker_id,
            }

        age = time.time() - last
        is_stale = age > self.stale_grace

        return {
            "alive": not is_stale,
            "reason": "stale" if is_stale else "active",
            "worker_id": worker_id,
            "age_seconds": age,
            "stale_threshold": self.stale_grace,
        }

    def append_wake(self, kind: str, key: str, payload: str) -> None:
        """Append a wake event to the durable queue."""
        self._wake_count += 1
        epoch = int(time.time())
        row = f"{epoch}\t{self._wake_count}\t{kind}\t{key}\t{payload}\n"

        with open(self.wake_queue, "a") as f:
            f.write(row)

    def drain_wakes(self) -> list[dict[str, Any]]:
        """Drain the wake queue."""
        if not self.wake_queue.exists():
            return []

        wakes = []
        with open(self.wake_queue, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 5:
                    wakes.append({
                        "epoch": int(parts[0]),
                        "seq": int(parts[1]),
                        "kind": parts[2],
                        "key": parts[3],
                        "payload": parts[4],
                    })

        return wakes

    def acknowledge_wakes(self) -> None:
        """Acknowledge all drained wakes."""
        if self.wake_queue.exists():
            self.wake_queue.unlink()

    def get_fleet_status(self) -> dict[str, Any]:
        """Get fleet status from state files."""
        tasks = []
        for meta_file in self.state_dir.glob("*.meta"):
            if meta_file.is_file():
                task_id = meta_file.stem
                try:
                    with open(meta_file, "r") as f:
                        meta = {}
                        for line in f:
                            if "=" in line:
                                key, _, value = line.partition("=")
                                meta[key.strip()] = value.strip()
                    tasks.append({
                        "id": task_id,
                        "status": meta.get("status", "unknown"),
                        "backend": meta.get("backend", "tmux"),
                        "harness": meta.get("harness", "claude"),
                        "kind": meta.get("kind", "ship"),
                    })
                except Exception:
                    pass

        return {
            "tasks": tasks,
            "total": len(tasks),
            "active": sum(1 for t in tasks if t["status"] == "working"),
            "afk": self.is_afk(),
        }

    def scan_signals(self) -> list[dict[str, Any]]:
        """Scan for status/turn-end signal files.

Mirrors lazy-master watch signal scanning: checks *.status files for
user-relevant verbs and no-verb signals.
        """
        signals = []
        for meta_file in self.state_dir.glob("*.meta"):
            if not meta_file.is_file():
                continue
            task_id = meta_file.stem

            # Check for turn-end signal
            turn_end = self.state_dir / f"{task_id}.turn-ended"
            if turn_end.exists():
                age = time.time() - turn_end.stat().st_mtime
                if age < SIGNAL_GRACE:
                    signals.append({
                        "type": "turn-end",
                        "task_id": task_id,
                        "age": age,
                    })

            # Check for status signal
            status_file = self.state_dir / f"{task_id}.status"
            if status_file.exists():
                try:
                    with open(status_file, "r") as f:
                        lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        # Check for user-relevant verbs
                        captain_verbs = ["done:", "failed:", "blocked:", "needs-decision:"]
                        is_captain_relevant = any(last_line.startswith(v) for v in captain_verbs)
                        if is_captain_relevant:
                            signals.append({
                                "type": "status",
                                "task_id": task_id,
                                "line": last_line,
                                "captain_relevant": True,
                            })
                except Exception:
                    pass

        return signals

    def wedge_timer_check(self, window: str) -> dict[str, Any] | None:
        """Check if a stale worker should be escalated.

        Mirrors lazy-master watch wedge_timer_check: escalation count tracking
        and demand-deep-inspection at threshold.
        """
        stale_since = self._stale_since.get(window)
        if stale_since is None:
            return None

        age = time.time() - stale_since
        if age < STALE_ESCALATE_SECS:
            return None

        # Increment escalation count
        count = self._wedge_escalations.get(window, 0) + 1
        self._wedge_escalations[window] = count

        reason = f"stale: {window} (escalation {count})"
        if count >= FM_WEDGE_DEMAND_INSPECT_COUNT:
            reason += " demand-deep-inspection"

        return {
            "window": window,
            "escalation": count,
            "demand_inspect": count >= FM_WEDGE_DEMAND_INSPECT_COUNT,
            "reason": reason,
        }

    def busy_turn_bound_check(self, task_id: str) -> dict[str, Any] | None:
        """Check if a busy pane has exceeded BUSY_TURN_MAX_SECS.

        Mirrors lazy-master watch busy_turn_bound_check: bounds how long any
        busy pane may go with no completed turn.
        """
        turn_ended = self.state_dir / f"{task_id}.turn-ended"
        if not turn_ended.exists():
            # Check spawn record
            spawn_record = self.state_dir / f"{task_id}.spawn-record"
            if not spawn_record.exists():
                return None
            age = time.time() - spawn_record.stat().st_mtime
        else:
            age = time.time() - turn_ended.stat().st_mtime

        if age < BUSY_TURN_MAX_SECS:
            return None

        return {
            "task_id": task_id,
            "age": age,
            "reason": f"busy turn bound exceeded: {task_id} ({int(age)}s)",
        }

    def secondmate_wake_stall_tick(self) -> list[dict[str, Any]]:
        """Check for stalled lazy-master2 wake queues.

        Mirrors lazy-master watch secondmate_wake_stall_tick: read-only observation
        of local lazy-master2's foreign queue.
        """
        stalls = []
        for meta_file in self.state_dir.glob("*.meta"):
            if not meta_file.is_file():
                continue

            try:
                with open(meta_file, "r") as f:
                    meta = {}
                    for line in f:
                        if "=" in line:
                            key, _, value = line.partition("=")
                            meta[key.strip()] = value.strip()

                if meta.get("kind") != "secondmate":
                    continue
                if meta.get("remote_host"):
                    continue

                home = meta.get("home")
                if not home:
                    continue

                queue_path = Path(home) / "state" / ".wake-queue"
                if not queue_path.exists():
                    continue

                # Find oldest valid row
                oldest = None
                with open(queue_path, "r") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 5 and parts[0].isdigit() and parts[1].isdigit():
                            epoch = int(parts[0])
                            seq = int(parts[1])
                            if oldest is None or seq < oldest[1]:
                                oldest = (epoch, seq, parts[2], parts[3], parts[4])

                if oldest is None:
                    continue

                age = int(time.time()) - oldest[0]
                if age < SECONDMATE_WAKE_STALL_SECS:
                    continue

                task_id = meta_file.stem
                stalls.append({
                    "task_id": task_id,
                    "row_seq": oldest[1],
                    "age": age,
                    "reason": f"lazy-master2 wake-loop stalled: mate={task_id} row={oldest[1]} age={age}s",
                })
            except Exception:
                pass

        return stalls

    def heartbeat_scan(self) -> list[dict[str, Any]]:
        """Heartbeat scan for fleet health.

        Mirrors lazy-master watch heartbeat: scans all tasks for user-relevant
        status that hasn't been surfaced.
        """
        actionable = []
        for meta_file in self.state_dir.glob("*.meta"):
            if not meta_file.is_file():
                continue

            task_id = meta_file.stem
            status_file = self.state_dir / f"{task_id}.status"
            if not status_file.exists():
                continue

            try:
                with open(status_file, "r") as f:
                    lines = f.readlines()
                if not lines:
                    continue

                last_line = lines[-1].strip()
                captain_verbs = ["done:", "failed:", "blocked:", "needs-decision:"]
                if any(last_line.startswith(v) for v in captain_verbs):
                    # Check if already surfaced
                    surfaced_marker = self.state_dir / f".hb-surfaced-{task_id}"
                    if not surfaced_marker.exists():
                        actionable.append({
                            "task_id": task_id,
                            "line": last_line,
                            "reason": "heartbeat",
                        })
                        surfaced_marker.touch()
            except Exception:
                pass

        return actionable

    def inbox_steer_check(self, window: str, task_id: str) -> dict[str, Any] | None:
        """Check steering-inbox for unacknowledged instructions.

        Mirrors lazy-master watch inbox_steer_check: cheap check per window per poll.
        """
        inbox_dir = self.state_dir / f"{task_id}.inbox"
        if not inbox_dir.exists():
            return None

        # Check for unhandled messages
        handled_dir = inbox_dir / "handled"
        unhandled = []
        for msg_file in inbox_dir.glob("*.msg"):
            if not handled_dir.exists() or not (handled_dir / msg_file.name).exists():
                unhandled.append(msg_file)

        if not unhandled:
            return None

        return {
            "window": window,
            "task_id": task_id,
            "unhandled_count": len(unhandled),
            "reason": f"stale: {window} (unread lazy-master instruction: {len(unhandled)} unhandled messages)",
        }

    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def emit(self, event: str, data: dict) -> None:
        """Emit event to callbacks."""
        for callback in self._callbacks.get(event, []):
            callback(data)

    def status(self) -> dict[str, Any]:
        """Get watcher status."""
        return {
            "running": self.running,
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "stale_grace": self.stale_grace,
            "workers_watching": len(self.last_activity),
            "wake_count": self._wake_count,
            "afk": self.is_afk(),
        }

    def _classify_wake(self, wake: dict[str, Any]) -> str:
        """Classify a wake as actionable or benign.

        Mirrors lazy-master watch wake classification: most wakes during a long
        crew validation are benign and absorbed.
        """
        kind = wake.get("kind", "")
        payload = wake.get("payload", "")

        # Captain-relevant verbs are always actionable
        captain_verbs = ["done:", "failed:", "blocked:", "needs-decision:"]
        if any(payload.startswith(v) for v in captain_verbs):
            return "actionable"

        # Check signals are actionable
        if kind == "signal":
            return "actionable"

        # Stale wakes where crew is not provably working are actionable
        if kind == "stale":
            return "actionable"

        # Check wakes are actionable
        if kind == "check":
            return "actionable"

        # Heartbeat wakes are actionable
        if kind == "heartbeat":
            return "actionable"

        # Default: absorb benign
        return "absorb"

    def run_cycle(self) -> dict[str, Any]:
        """Run one poll cycle.

        Returns summary of cycle activity.
        """
        self.touch_beat()

        # AFK mode: one-shot (enqueue + exit on every wake)
        if self.is_afk():
            wakes = self.drain_wakes()
            return {"afk": True, "wakes": len(wakes), "action": "queue_and_exit"}

        # Scan for signals
        signals = self.scan_signals()

        # Check lazy-master2 stalls
        stalls = self.secondmate_wake_stall_tick()

        # Heartbeat scan (periodic)
        heartbeat = []
        beat_file = self.state_dir / ".last-heartbeat"
        if not beat_file.exists() or \
           time.time() - beat_file.stat().st_mtime > self.heartbeat_interval:
            heartbeat = self.heartbeat_scan()
            beat_file.touch()

        # Classify and queue actionable wakes
        actionable = 0
        absorbed = 0

        for sig in signals:
            self.append_wake("signal", sig.get("task_id", ""), json.dumps(sig))
            actionable += 1

        for stall in stalls:
            self.append_wake("check", stall["task_id"], stall["reason"])
            actionable += 1

        for hb in heartbeat:
            self.append_wake("heartbeat", hb["task_id"], hb["reason"])
            actionable += 1

        return {
            "afk": False,
            "signals": len(signals),
            "stalls": len(stalls),
            "heartbeat": len(heartbeat),
            "actionable": actionable,
            "absorbed": absorbed,
        }

    def main_loop(self) -> None:
        """Run the main watcher daemon loop.

        Mirrors lazy-master watch main entry: poll cycle with signal handling.
        """
        if not self.acquire_lock():
            return

        self.running = True

        # Set up signal handlers
        def handle_signal(signum, frame):
            self.running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        try:
            while self.running:
                try:
                    result = self.run_cycle()
                    self.emit("cycle", result)
                except Exception as e:
                    self.emit("error", {"error": str(e)})

                time.sleep(self.poll_interval)
        finally:
            self.release_lock()
            self.running = False
