"""Turn-end guard - detect blind stops."""


class TurnEndGuard:
    """Detect blind stops and force follow-up."""

    def __init__(self, max_block_budget: int = 3):
        self.max_block_budget = max_block_budget
        self.block_counts = {}

    async def check(self, hand_id: str, hand) -> dict:
        """Check if turn-end should be blocked."""
        if hand.status != "working":
            return {"blocked": False, "reason": "not-working"}

        alive = await hand.is_alive()
        if alive.get("alive") is not True:
            return {"blocked": False, "reason": "agent-not-alive"}

        busy = await hand.get_busy_state()
        if busy.get("state") == "busy":
            return {"blocked": True, "reason": "agent-busy", "action": "block"}

        if busy.get("state") == "idle":
            count = self.block_counts.get(hand_id, 0)
            if count < self.max_block_budget:
                self.block_counts[hand_id] = count + 1
                return {
                    "blocked": True,
                    "reason": "blind-stop",
                    "action": "follow-up",
                    "attempt": count + 1,
                }
            return {"blocked": False, "reason": "budget-exhausted"}

        return {"blocked": False, "reason": "unknown-state"}

    def acknowledge(self, hand_id: str):
        """Acknowledge a turn-end was handled."""
        self.block_counts.pop(hand_id, None)
