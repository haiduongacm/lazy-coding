"""lazy-master master - Orchestrator.

Mirrors lazy-coding AGENTS.md section 1: identity and prime directives.
Hard rules:
1. Never write to a project directly.
2. Never merge a PR without operator's explicit word.
3. Never tear down unlanded work.
4. Hands never address the operator.
5. Report outcomes faithfully.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import uuid

from .hand import LazyHand
from .dispatcher import parse_request


@dataclass
class LazyMaster:
    """Multi-agent orchestrator.

Mirrors lazy-master: operator's only point of contact for all software work.
Delegates coding, investigation, planning to hands or lazy-master2s.
    """

    agent: str = "claude"
    max_hands: int = 4
    backend: str = "tmux"
    session: str = "lazy-coding"
    hands: dict[str, LazyHand] = field(default_factory=dict)
    secondmates: dict[str, Any] = field(default_factory=dict)

    async def init(self) -> None:
        """Initialize the master."""
        pass

    def status(self) -> dict[str, Any]:
        """Get fleet status."""
        working = sum(1 for h in self.hands.values() if h.status in ("working", "assigned"))
        done = sum(1 for h in self.hands.values() if h.status == "done")
        failed = sum(1 for h in self.hands.values() if h.status == "failed")

        return {
            "total": len(self.hands),
            "working": working,
            "done": done,
            "failed": failed,
            "agent": self.agent,
            "backend": self.backend,
        }

    async def dispatch(self, task: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a task to a hand.

        Mirrors lazy-coding AGENTS.md section 7: spawn only through spawn script.
        """
        if len(self.hands) >= self.max_hands:
            return {
                "error": True,
                "code": "CONFLICT",
                "message": f"Max hands ({self.max_hands}) reached",
                "help": ["Wait for a hand to complete", "Increase max_hands"],
            }

        hand_id = str(uuid.uuid4())[:8]
        hand = LazyHand(
            id=hand_id,
            agent=self.agent,
            task=task,
        )
        hand.status = "working"
        self.hands[hand_id] = hand

        return {
            "success": True,
            "hand_id": hand_id,
            "task": task,
        }

    async def teardown_all(self) -> list[dict[str, Any]]:
        """Teardown all hands.

        Mirrors lazy-master: teardown owns the complete landed-work test.
        Never force teardown without explicit discard authority.
        """
        results = []
        for hand_id, hand in list(self.hands.items()):
            results.append({
                "hand_id": hand_id,
                "status": "teardown",
                "result": hand.result,
            })
            del self.hands[hand_id]
        return results
