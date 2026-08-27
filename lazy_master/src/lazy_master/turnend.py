"""lazy-master turnend - Turn-end guard.

Mirrors lazy-master's turnend guard: push-based guard that prevents
blind turn endings when supervision is off.

Key concepts from lazy-master turnend guard:
- Push-based: verified harness turn-end hooks invoke it every time
- Loop-guard: never block twice in the same turn
- Block budget: bounded consecutive blocks per session
- Claude-mode auto-arm cooperation
- Cursor-mode support
- Epoch budget tracking
"""

import os
import json
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


# Constants matching lazy-master turnend guard
BLOCK_BUDGET_DEFAULT = 3
SYNC_WAIT_MS_DEFAULT = 800
EPOCH_FRESH_DEFAULT = 15


class TurnEndGuard:
    """Turn-end guard - prevents blind turn endings.

    Mirrors lazy-master's turnend guard:
    - Push-based: verified harness turn-end hooks invoke it every time
    - Blocks when tasks in flight but no live watcher holds home lock
    - Claude-mode: cooperates with Stop-owned auto-arm
    - Cursor-mode: renders exit 2 as one bounded follow-up
    """

    def __init__(self, state_dir: str | None = None, grace: int = 300,
                 block_budget: int = BLOCK_BUDGET_DEFAULT,
                 sync_wait_ms: int = SYNC_WAIT_MS_DEFAULT,
                 epoch_fresh: int = EPOCH_FRESH_DEFAULT):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.grace = grace
        self.block_budget = block_budget
        self.sync_wait_ms = sync_wait_ms
        self.epoch_fresh = epoch_fresh
        self.block_counts: dict[str, int] = {}
        self.last_block_times: dict[str, float] = {}

        # Claude auto-arm state files
        self.budget_file = self.state_dir / ".turnend-claude-blocks"
        self.budget_lock = self.state_dir / ".turnend-claude-blocks.lock"
        self.owner_lock = self.state_dir / ".claude-autoarm.lock"
        self.failure_notice = self.state_dir / ".claude-autoarm-failure-notified"
        self.failure_alarm = self.state_dir / ".claude-autoarm-failure-alarmed"
        self.epoch_file = self.state_dir / ".claude-autoarm-epoch"

    def should_block(self, task_id: str, watcher_healthy: bool,
                     hook_active: bool = False, claude_mode: bool = False,
                     cursor_mode: bool = False) -> dict[str, Any]:
        """Determine if turn should be blocked.

        Mirrors lazy-master: block when tasks in flight but no live watcher.
        """
        # Cursor mode: render exit 2 as one bounded follow-up
        if cursor_mode:
            return {
                "blocked": False,
                "reason": "cursor_mode",
            }

        # Loop-guard for non-Claude: if hook already active, allow
        if not claude_mode and hook_active:
            return {
                "blocked": False,
                "reason": "hook_already_active",
            }

        # Check watcher health
        if watcher_healthy:
            if claude_mode:
                # Claude mode: reset failure episode if watcher healthy
                self._failure_episode_reset(task_id)
                return {
                    "blocked": False,
                    "reason": "watcher_healthy",
                }
            return {
                "blocked": False,
                "reason": "watcher_healthy",
            }

        # Claude mode: cooperative path with auto-arm
        if claude_mode:
            return self._claude_cooperative_block(task_id)

        # Non-Claude: direct block
        return self._direct_block(task_id)

    def _claude_cooperative_block(self, task_id: str) -> dict[str, Any]:
        """Claude-mode cooperative blocking path.

        Mirrors lazy-master turnend guard --claude mode: cooperates with Stop-owned
        auto-arm, gives it bounded window to claim recovery.
        """
        # Brief bounded wait for auto-arm to claim
        start = time.time()
        wait_secs = self.sync_wait_ms / 1000.0
        while time.time() - start < wait_secs:
            if self._autoarm_owns_recovery():
                self._failure_episode_reset(task_id)
                return {
                    "blocked": False,
                    "reason": "autoarm_claimed",
                }
            time.sleep(0.1)

        # Check again after wait
        if self._autoarm_owns_recovery():
            self._failure_episode_reset(task_id)
            return {
                "blocked": False,
                "reason": "autoarm_claimed",
            }

        # Auto-arm genuinely failed: consume budget before fail-open
        self._budget_account_current_epoch(task_id)
        count = self.block_counts.get(task_id, 0)

        # Check for terminal fail-open
        if self._terminal_fail_open():
            return {
                "blocked": False,
                "reason": "terminal_fail_open",
                "warning": "Supervision is genuinely down. Keep this session attended.",
            }

        # Block with budget
        return self._direct_block(task_id)

    def _direct_block(self, task_id: str) -> dict[str, Any]:
        """Direct blocking path."""
        count = self.block_counts.get(task_id, 0)
        if count >= self.block_budget:
            return {
                "blocked": False,
                "reason": "budget_exceeded",
                "warning": f"Block budget ({self.block_budget}) exceeded, failing open",
            }

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

    def _autoarm_owns_recovery(self) -> bool:
        """Check if auto-arm owns recovery.

        Mirrors lazy-master turnend guard autoarm_owns_recovery.
        """
        # Check if watcher is healthy
        if self._is_watcher_healthy():
            return True

        # Check if auto-arm lock is held
        if self.owner_lock.exists():
            try:
                age = time.time() - self.owner_lock.stat().st_mtime
                if age < self.grace:
                    # Check if claim is abandoned
                    if not self._autoarm_claim_abandoned():
                        return True
            except Exception:
                pass

        # Check epoch file for recent outcomes
        if self.epoch_file.exists():
            try:
                content = self.epoch_file.read_text()
                for line in content.split("\n"):
                    if line.startswith("outcome="):
                        outcome = line.split("=", 1)[1]
                        if outcome in ("rewake", "failed", "failed-suppressed"):
                            age = time.time() - self.epoch_file.stat().st_mtime
                            if age < self.epoch_fresh:
                                return True
            except Exception:
                pass

        return False

    def _is_watcher_healthy(self) -> bool:
        """Check if watcher is healthy."""
        beat_file = self.state_dir / ".last-watcher-beat"
        if not beat_file.exists():
            return False
        age = time.time() - beat_file.stat().st_mtime
        return age < self.grace

    def _autoarm_claim_abandoned(self) -> bool:
        """Check if auto-arm claim is abandoned."""
        # Simplified: check if lock file is stale
        if self.owner_lock.exists():
            age = time.time() - self.owner_lock.stat().st_mtime
            return age > self.grace
        return True

    def _budget_account_current_epoch(self, task_id: str) -> None:
        """Account budget for current epoch."""
        count = self.block_counts.get(task_id, 0)
        self.block_counts[task_id] = count + 1

        # Write budget file
        try:
            self.budget_file.write_text(json.dumps({
                "session": task_id,
                "count": count + 1,
                "epoch": self._get_current_epoch(),
            }))
        except Exception:
            pass

    def _get_current_epoch(self) -> str:
        """Get current epoch from epoch file."""
        if self.epoch_file.exists():
            try:
                content = self.epoch_file.read_text()
                for line in content.split("\n"):
                    if line.startswith("epoch="):
                        return line.split("=", 1)[1]
            except Exception:
                pass
        return "0"

    def _terminal_fail_open(self) -> bool:
        """Check for terminal fail-open condition.

        Mirrors lazy-master turnend guard terminal_fail_open: verified one-time
        attended fail-open for exhausted budget + verified failure episode.
        """
        # Check if already alarmed
        if self.failure_alarm.exists():
            return False

        # Check failure episode
        if not self._failure_episode_verified():
            return False

        # Check budget exceeded
        for task_id, count in self.block_counts.items():
            if count > self.block_budget:
                return True

        return False

    def _failure_episode_verified(self) -> bool:
        """Check if failure episode is verified."""
        if self.state_dir / ".afk".exists():
            return False
        if not self.failure_notice.exists():
            return False

        if self.epoch_file.exists():
            try:
                content = self.epoch_file.read_text()
                for line in content.split("\n"):
                    if line.startswith("outcome="):
                        outcome = line.split("=", 1)[1]
                        return outcome in ("failed", "failed-suppressed")
            except Exception:
                pass

        return False

    def _failure_episode_reset(self, task_id: str) -> bool:
        """Reset failure episode."""
        try:
            if self.budget_file.exists():
                self.budget_file.unlink()
            if self.failure_notice.exists():
                self.failure_notice.unlink()
            return True
        except Exception:
            return False

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
            "sync_wait_ms": self.sync_wait_ms,
            "epoch_fresh": self.epoch_fresh,
        }

    def reset_all(self) -> None:
        """Reset all block counts."""
        self.block_counts.clear()
        self.last_block_times.clear()
        self._failure_episode_reset("all")
