"""lazy-master watcher - Zero-token fleet monitoring.

Mirrors firstmate fm-watch.sh: the watcher polls fleet state without
consuming tokens, detects stale workers, and triggers wake events.

Key concepts from fm-watch.sh:
- Singleton lock to prevent duplicate watchers
- Poll cycle with configurable interval
- Heartbeat scans for fleet health
- Wake queue for durable events
- Stale detection with wedge escalation
- AFK mode awareness
"""

import os
import time
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional
from datetime import datetime, timezone


class Watcher:
    """Fleet watcher - monitors worker liveness.

    Mirrors firstmate's watcher: zero-token monitoring, detects stale workers,
    triggers wake events for the supervision protocol.
    """

    def __init__(self, state_dir: str | None = None, poll_interval: int = 15,
                 heartbeat_interval: int = 600, stale_grace: int = 300):
        """
        Args:
            state_dir: State directory path
            poll_interval: Seconds between poll cycles
            heartbeat_interval: Seconds between heartbeat scans
            stale_grace: Seconds before declaring a worker stale
        """
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.stale_grace = stale_grace
        self.lock_file = self.state_dir / ".watch.lock"
        self.wake_queue = self.state_dir / ".wake-queue"
        self.watcher_down_marker = self.state_dir / ".watcher-down"
        self.last_beat_file = self.state_dir / ".last-watcher-beat"
        self.running = False
        self.last_activity: dict[str, float] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._wake_count = 0

    def acquire_lock(self) -> bool:
        """Acquire singleton watcher lock.

        Mirrors firstmate: only one watcher instance per home.
        """
        try:
            self.lock_file.touch(exist_ok=False)
            return True
        except FileExistsError:
            # Check if lock is stale
            if self.lock_file.exists():
                age = time.time() - self.lock_file.stat().st_mtime
                if age > self.stale_grace:
                    # Stale lock, remove it
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
        """Check if away mode is active.

        Mirrors firstmate: while state/.afk exists, daemon owns triage.
        """
        return (self.state_dir / ".afk").exists()

    def touch_beat(self) -> None:
        """Touch watcher liveness beacon.

        Mirrors firstmate: .last-watcher-beat is touched every poll.
        """
        self.last_beat_file.touch()

    def check_worker_liveness(self, worker_id: str) -> dict[str, Any]:
        """Check if a worker is still alive.

        Returns:
            Dict with alive status, last_activity, and staleness info
        """
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
        """Append a wake event to the durable queue.

        Mirrors firstmate: wake queue is epoch<TAB>seq<TAB>kind<TAB>key<TAB>payload
        """
        self._wake_count += 1
        epoch = int(time.time())
        row = f"{epoch}\t{self._wake_count}\t{kind}\t{key}\t{payload}\n"

        with open(self.wake_queue, "a") as f:
            f.write(row)

    def drain_wakes(self) -> list[dict[str, Any]]:
        """Drain the wake queue.

        Returns:
            List of wake events
        """
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
        """Acknowledge all drained wakes by clearing the queue."""
        if self.wake_queue.exists():
            self.wake_queue.unlink()

    def get_fleet_status(self) -> dict[str, Any]:
        """Get fleet status from state files.

        Mirrors firstmate: reads *.meta files for task metadata.
        """
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
                    })
                except Exception:
                    pass

        return {
            "tasks": tasks,
            "total": len(tasks),
            "active": sum(1 for t in tasks if t["status"] == "working"),
            "afk": self.is_afk(),
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
