"""lazy-master - The orchestrator."""

import asyncio
from typing import Optional, Any
from datetime import datetime

from .hand import LazyHand
from .watcher import Watcher
from .control import ControlPlane
from .turnend import TurnEndGuard
from .dispatcher import parse_request


class LazyMaster:
    """Multi-agent orchestrator."""

    def __init__(
        self,
        backend: Optional[Any] = None,
        agent: str = "claude",
        max_hands: int = 4,
    ):
        self.backend = backend
        self.agent = agent
        self.max_hands = max_hands
        self.hands = {}
        self.secondmates = {}
        self.watcher = Watcher()
        self.control = ControlPlane(self)
        self.turn_end_guard = TurnEndGuard()

    async def init(self):
        """Initialize the master."""
        if self.backend and hasattr(self.backend, "init"):
            await self.backend.init()
        return {"initialized": True}

    async def dispatch(self, task: dict, **opts) -> dict:
        """Dispatch a task to a lazy-hand."""
        if len(self.hands) >= self.max_hands:
            return {
                "error": True,
                "code": "CONFLICT",
                "message": f"Maximum hands ({self.max_hands}) reached",
            }

        hand_id = f"hand-{id(task) % 100000}"
        agent = opts.get("agent", self.agent)

        hand = LazyHand(id=hand_id, agent=agent, backend=self.backend)
        hand.worktree = opts.get("worktree")
        self.hands[hand_id] = hand

        await hand.assign(task)

        return {
            "success": True,
            "hand_id": hand_id,
            "task": task.get("description"),
            "agent": agent,
            "endpoint": hand.endpoint,
        }

    async def send_to_hand(self, hand_id: str, text: str) -> dict:
        """Send text to a hand's agent."""
        hand = self.hands.get(hand_id)
        if not hand:
            return {"error": True, "code": "NOT_FOUND"}
        return await hand.send(text)

    async def control_hand(self, hand_id: str, action: str, **opts) -> dict:
        """Control a hand's lifecycle."""
        return await self.control.control(hand_id, action, **opts)

    async def check_turn_end(self, hand_id: str) -> dict:
        """Check turn-end guard."""
        hand = self.hands.get(hand_id)
        if not hand:
            return {"blocked": False, "reason": "hand-not-found"}
        return await self.turn_end_guard.check(hand_id, hand)

    async def guard_check(self) -> dict:
        """Run guard check."""
        # Simplified guard check
        checks = []

        # Check primary checkout
        import subprocess
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            branch = result.stdout.strip()
            checks.append({
                "name": "primary_checkout",
                "status": "ok" if branch in ("main", "master") else "warning",
                "branch": branch,
            })
        except Exception:
            checks.append({"name": "primary_checkout", "status": "ok"})

        return {
            "healthy": all(c["status"] == "ok" for c in checks),
            "checks": checks,
        }

    async def add_secondmate(self, **opts) -> dict:
        """Add a secondmate."""
        from .master2 import LazyMaster2

        master2 = LazyMaster2(
            id=f"master2-{id(opts) % 100000}",
            backend=self.backend,
            **opts,
        )
        self.secondmates[master2.id] = master2
        return master2.get_status()

    def list_secondmates(self) -> list:
        """List secondmates."""
        return [m.get_status() for m in self.secondmates.values()]

    def status(self) -> dict:
        """Get fleet status."""
        hands = list(self.hands.values())
        return {
            "backend": self.backend.name if self.backend else None,
            "agent": self.agent,
            "total": len(hands),
            "assigned": sum(1 for h in hands if h.status == "assigned"),
            "working": sum(1 for h in hands if h.status == "working"),
            "done": sum(1 for h in hands if h.status == "done"),
            "failed": sum(1 for h in hands if h.status == "failed"),
            "hands": [h.get_status() for h in hands],
            "secondmates": self.list_secondmates(),
        }

    async def liveness(self) -> list:
        """Get liveness status."""
        results = []
        for hand_id, hand in self.hands.items():
            alive = await hand.is_alive()
            results.append({"id": hand_id, **alive})
        return results

    async def busy_states(self) -> list:
        """Get busy states."""
        results = []
        for hand_id, hand in self.hands.items():
            busy = await hand.get_busy_state()
            results.append({
                "id": hand_id,
                "task": hand.task.get("description") if hand.task else None,
                **busy,
            })
        return results

    async def teardown_all(self) -> list:
        """Teardown all endpoints."""
        self.watcher.stop()
        results = []
        for hand_id, hand in self.hands.items():
            result = await hand.teardown()
            results.append({"id": hand_id, **result})
        self.hands.clear()
        self.secondmates.clear()
        return results
