"""Zero-token watcher daemon."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable


class Watcher:
    """Monitor fleet without consuming LLM tokens."""

    def __init__(self, interval: int = 10, state_dir: Optional[str] = None):
        self.interval = interval
        self.state_dir = Path(state_dir or ".")
        self.running = False
        self.hands = {}
        self.last_activity = {}
        self.stale_threshold = 300  # 5 minutes
        self.callbacks = {}

    def on(self, event: str, callback: Callable):
        """Register event callback."""
        self.callbacks.setdefault(event, []).append(callback)

    def emit(self, event: str, data: dict):
        """Emit event to callbacks."""
        for cb in self.callbacks.get(event, []):
            cb(data)

    async def start(self, hands: dict):
        """Start watching the fleet."""
        if self.running:
            return
        self.running = True
        self.hands = hands

        while self.running:
            await self.poll()
            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop watching."""
        self.running = False

    async def poll(self):
        """Poll fleet state."""
        for hand_id, hand in self.hands.items():
            if hand.status in ("done", "failed"):
                self.emit("terminal", {"id": hand_id, "status": hand.status})
                continue

            if hand.status == "working" and hand.endpoint:
                alive = await hand.is_alive()
                busy = await hand.get_busy_state()

                if alive.get("alive") is False:
                    self.emit("agent-died", {"id": hand_id, "task": hand.task})
                    continue

                if busy.get("state") == "idle":
                    last = self.last_activity.get(hand_id, 0)
                    if asyncio.get_event_loop().time() - last > self.stale_threshold:
                        self.emit("stale", {"id": hand_id, "task": hand.task})

                elif busy.get("state") == "busy":
                    self.last_activity[hand_id] = asyncio.get_event_loop().time()

    def record_activity(self, hand_id: str):
        """Record activity for a hand."""
        self.last_activity[hand_id] = asyncio.get_event_loop().time()

    def status(self) -> dict:
        """Get watcher status."""
        return {
            "running": self.running,
            "interval": self.interval,
            "hands_watching": len(self.hands),
        }
