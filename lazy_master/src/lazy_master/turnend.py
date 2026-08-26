"""lazy-master turnend - Turn-end guard.

Mirrors firstmate fm-turnend-guard.sh: push-based guard that prevents
blind turn endings when supervision is off.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnEndGuard:
    """Turn-end guard - prevents blind turn endings.

    Mirrors firstmate fm-turnend-guard.sh:
    - Pull-based: fm-guard.sh only warns when some other script runs.
    - Push-based: verified harness turn-end hooks invoke it every time.
    - Blocks when tasks in flight but no live watcher holds home lock.
    """

    max_block_budget: int = 3
    block_counts: dict[str, int] = field(default_factory=dict)

    def should_block(self, hand_id: str, in_flight: int, watcher_healthy: bool) -> bool:
        """Determine if turn should be blocked.

        Mirrors firstmate: block when tasks in flight but no live watcher.
        """
        if in_flight == 0:
            return False
        if watcher_healthy:
            return False

        count = self.block_counts.get(hand_id, 0)
        if count >= self.max_block_budget:
            return False  # Allow one loud fail-open

        return True

    def acknowledge(self, hand_id: str) -> None:
        """Acknowledge a block for a hand."""
        if hand_id in self.block_counts:
            del self.block_counts[hand_id]

    def block(self, hand_id: str) -> None:
        """Record a block for a hand."""
        self.block_counts[hand_id] = self.block_counts.get(hand_id, 0) + 1
