"""lazy-master watcher - Zero-token fleet monitoring.

Mirrors firstmate fm-watch.sh: the watcher polls fleet state without
consuming tokens, detects stale workers, and triggers wake events.
"""

from dataclasses import dataclass, field
from typing import Any, Callable
import time


@dataclass
class Watcher:
    """Fleet watcher - monitors worker liveness.

    Mirrors firstmate's watcher: zero-token monitoring, detects stale workers,
    triggers wake events for the supervision protocol.
    """

    interval: int = 10  # seconds
    running: bool = False
    last_activity: dict[str, float] = field(default_factory=dict)
    _callbacks: dict[str, list[Callable]] = field(default_factory=dict)

    def status(self) -> dict[str, Any]:
        """Get watcher status."""
        return {
            "running": self.running,
            "interval": self.interval,
            "hands_watching": len(self.last_activity),
        }

    def record_activity(self, hand_id: str) -> None:
        """Record activity for a hand."""
        self.last_activity[hand_id] = time.time()

    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def emit(self, event: str, data: dict) -> None:
        """Emit event to callbacks."""
        for callback in self._callbacks.get(event, []):
            callback(data)
