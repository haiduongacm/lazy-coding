"""lazy-master turnend - Turn-end guard.

Mirrors firstmate fm-turnend-guard.sh: push-based guard that prevents
blind turn endings when supervision is off.

Key concepts from fm-turnend-guard.sh:
- Push-based: verified harness turn-end hooks invoke it every time
- Loop-guard: never block twice in the same turn
- Block budget: bounded consecutive blocks per session
- Primary scope detection: main home or secondmate home
- Fail-closed on unverified harnesses
"""

import os
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class TurnEndGuard:
    """Turn-end guard - prevents blind turn endings.

    Mirrors firstmate fm-turnend-guard.sh:
    - Pull-based: fm-guard.sh only warns when some other script runs
    - Push-based: verified harness turn-end hooks invoke it every time
    - Blocks when tasks in flight but no live watcher holds home lock
    """

    def __init__(self, state_dir: str | None = None, grace: int = 300,
                 block_budget: int = 3):
        """
        Args:
            state_dir: State directory path
            grace: Seconds before stale detection
            block_budget: Max consecutive blocks before fail-open
        """
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.grace = grace
        self.block_budget = block_budget
        self.block_counts: dict[str, int] = {}
        self.last_block_times: dict[str, float] = {}

    def should_block(self, task_id: str, watcher_healthy: bool,
                     hook_active: bool = False) -> dict[str, Any]:
        """Determine if turn should be blocked.

        Mirrors firstmate: block when tasks in flight but no live watcher.

        Returns:
            Dict with should_block, reason, and optional repair instructions
        """
        # Loop-guard: if hook already active, allow (codex/Grok default mode)
        if hook_active:
            return {
                "blocked": False,
                "reason": "hook_already_active",
            }

        # Check watcher health
        if watcher_healthy:
            return {
                "blocked": False,
                "reason": "watcher_healthy",
            }

        # Check block budget
        count = self.block_counts.get(task_id, 0)
        if count >= self.block_budget:
            # Fail-open after budget exceeded
            return {
                "blocked": False,
                "reason": "budget_exceeded",
                "warning": f"Block budget ({self.block_budget}) exceeded, failing open",
            }

        # Block with repair instructions
        self.block_counts[task_id] = count + 1
        self.last_block_times[task_id] = time.time()

        return {
            "blocked": True,
            "reason": "watcher_unhealthy",
            "count": count + 1,
            "budget": self.block_budget,
            "repair": (
                "The watcher is not running. Start it with:\n"
                "  lazy-master watcher start\n"
                "Or check watcher status with:\n"
                "  lazy-master watcher status"
            ),
        }

    def acknowledge(self, task_id: str) -> None:
        """Acknowledge a successful turn (reset block count)."""
        if task_id in self.block_counts:
            del self.block_counts[task_id]
        if task_id in self.last_block_times:
            del self.last_block_times[task_id]

    def get_status(self, task_id: str | None = None) -> dict[str, Any]:
        """Get guard status."""
        if task_id:
            return {
                "task_id": task_id,
                "block_count": self.block_counts.get(task_id, 0),
                "last_block": self.last_block_times.get(task_id),
                "budget": self.block_budget,
            }

        return {
            "total_blocked": len(self.block_counts),
            "tasks": list(self.block_counts.keys()),
            "budget": self.block_budget,
            "grace": self.grace,
        }

    def reset_all(self) -> None:
        """Reset all block counts (e.g., on watcher restart)."""
        self.block_counts.clear()
        self.last_block_times.clear()
