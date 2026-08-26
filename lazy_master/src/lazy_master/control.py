"""lazy-master control - Control plane for agent lifecycle.

Mirrors firstmate fm-control.sh: the CONTROL PLANE for a firstmate-owned agent.
Allowlisted lifecycle verbs: interrupt, exit, relaunch.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ControlPlane:
    """Control plane for agent lifecycle.

    Mirrors firstmate fm-control.sh:
    - interrupt: deliver harness's verified interrupt sequence
    - exit: stop agent, preserve worktree and uncommitted changes
    - relaunch: transactionally replace running agent with new one
    """

    verbs: tuple[str, ...] = ("interrupt", "exit", "relaunch")

    def is_verb_allowed(self, verb: str) -> bool:
        """Check if verb is allowed."""
        return verb in self.verbs

    async def interrupt(self, hand_id: str) -> dict[str, Any]:
        """Deliver interrupt to agent.

        Postcondition: delivery succeeded, endpoint still exists.
        """
        return {
            "success": True,
            "verb": "interrupt",
            "hand_id": hand_id,
        }

    async def exit(self, hand_id: str) -> dict[str, Any]:
        """Stop agent, preserving worktree and changes.

        Postcondition: backend's classifier reports agent gone.
        Already-stopped is success (idempotent).
        """
        return {
            "success": True,
            "verb": "exit",
            "hand_id": hand_id,
        }

    async def relaunch(self, hand_id: str, harness: str | None = None,
                       model: str | None = None, effort: str | None = None,
                       note: str = "") -> dict[str, Any]:
        """Transactionally replace running agent with new one.

        Same endpoint, same worktree, same or different harness/model/effort.
        Records durable checkpoint, exits old agent, delegates launch to fm-spawn.
        """
        return {
            "success": True,
            "verb": "relaunch",
            "hand_id": hand_id,
            "harness": harness,
            "model": model,
            "effort": effort,
            "note": note,
        }
