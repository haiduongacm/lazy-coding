"""Control plane for hand lifecycle management."""

from typing import Optional


class ControlPlane:
    """Control plane for interrupt/exit/relaunch."""

    def __init__(self, master):
        self.master = master
        self.journals = {}

    async def control(self, hand_id: str, action: str, **opts) -> dict:
        """Send control command to a hand."""
        hand = self.master.hands.get(hand_id)
        if not hand:
            return {"error": True, "code": "NOT_FOUND", "message": "Hand not found"}

        if action == "interrupt":
            return await self._interrupt(hand)
        elif action == "exit":
            return await self._exit(hand)
        elif action == "relaunch":
            return await self._relaunch(hand, **opts)
        else:
            return {"error": True, "code": "INVALID_ACTION", "message": f"Unknown: {action}"}

    async def _interrupt(self, hand):
        """Interrupt a running hand."""
        if hand.status != "working":
            return {"error": True, "code": "NOT_WORKING"}

        result = await hand.send("C-c")
        return {"success": True, "action": "interrupt", "hand_id": hand.id}

    async def _exit(self, hand):
        """Exit a hand."""
        if hand.status not in ("working", "assigned"):
            return {"error": True, "code": "NOT_ACTIVE"}

        alive = await hand.is_alive()
        if alive.get("alive"):
            await hand.send("C-c")
            await asyncio.sleep(0.5)

        await hand.teardown()
        return {"success": True, "action": "exit", "hand_id": hand.id}

    async def _relaunch(self, hand, **opts):
        """Relaunch a hand."""
        self._journal(hand.id, {
            "action": "relaunch",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "previous_status": hand.status,
        })

        if hand.endpoint:
            await hand.teardown()

        agent = opts.get("agent", hand.agent)
        endpoint = await hand.backend.spawn(hand.id, {
            "agent": agent,
            "cwd": hand.worktree or ".",
        })

        hand.endpoint = endpoint
        hand.status = "working"

        return {"success": True, "action": "relaunch", "hand_id": hand.id, "agent": agent}

    def _journal(self, hand_id: str, entry: dict):
        """Journal a control action."""
        self.journals.setdefault(hand_id, []).append(entry)
