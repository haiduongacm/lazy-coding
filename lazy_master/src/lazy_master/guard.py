"""lazy-master guard - Watcher liveness and worktree-tangle guard.

Mirrors lazy-master's guard: called by supervision scripts.
Warns if primary checkout is on non-default branch.
Warns if tasks in flight but supervision is not healthy.

Key concepts from lazy-master guard:
- Pull-based: only warns when some other script runs
- Worktree-tangle check: primary checkout on non-default branch
- Watcher liveness check: tasks in flight but no live watcher
- Episode dedup for stale banner
- Queued wakes warning
- Always exits 0: guard warns, never blocks
"""

import os
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import subprocess


class Guard:
    """Guard - watcher liveness and worktree-tangle guard.

    Mirrors lazy-master's guard:
    - Always warns if primary checkout is on named non-default branch
    - Warns if tasks in flight but supervision not healthy
    - Episode dedup for stale banner
    - Always exits 0: guard warns, never blocks
    """

    def __init__(self, state_dir: str | None = None, grace: int = 300):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.grace = grace
        self.last_beat_file = self.state_dir / ".last-watcher-beat"
        self.stale_banner_marker = self.state_dir / ".guard-watcher-stale-banner"
        self.wake_queue = self.state_dir / ".wake-queue"

    def check_watcher_liveness(self) -> dict[str, Any]:
        """Check if watcher is alive."""
        if not self.last_beat_file.exists():
            return {
                "alive": False,
                "reason": "no_beat_file",
                "action": "Start the watcher: lazy-master watcher start",
            }

        try:
            age = time.time() - self.last_beat_file.stat().st_mtime
            is_alive = age < self.grace

            return {
                "alive": is_alive,
                "reason": "healthy" if is_alive else "stale",
                "age_seconds": age,
                "grace": self.grace,
                "beacon_desc": f"{int(age)}s ago" if not is_alive else "fresh",
                "action": None if is_alive else (
                    f"Watcher last beat {int(age)}s ago (grace: {self.grace}s). "
                    "Restart with: lazy-master watcher start"
                ),
            }
        except Exception as e:
            return {
                "alive": False,
                "reason": "error",
                "error": str(e),
                "action": "Check watcher status and restart if needed",
            }

    def check_worktree_tangle(self, current_branch: str | None = None,
                              default_branch: str = "main") -> dict[str, Any]:
        """Check if primary checkout is on non-default branch."""
        if current_branch is None:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    current_branch = result.stdout.strip()
            except Exception:
                pass

        if current_branch is None:
            return {
                "tangled": False,
                "reason": "cannot_detect_branch",
            }

        if current_branch == default_branch:
            return {
                "tangled": False,
                "reason": "on_default_branch",
                "branch": current_branch,
            }

        return {
            "tangled": True,
            "reason": "on_non_default_branch",
            "branch": current_branch,
            "default_branch": default_branch,
            "action": (
                f"You are on branch '{current_branch}', not '{default_branch}'. "
                f"Switch with: git checkout {default_branch}"
            ),
        }

    def _episode_key(self, reason: str) -> str:
        """Generate episode key from reason."""
        return reason

    def _claim_stale_banner(self, key: str) -> bool:
        """Claim stale banner for this episode.

        Returns True if full banner should be printed (new episode).
        Returns False if same episode already announced.
        """
        if not self.stale_banner_marker.exists():
            self.stale_banner_marker.write_text(key)
            return True

        try:
            seen = self.stale_banner_marker.read_text().strip()
            if seen == key:
                return False
            self.stale_banner_marker.write_text(key)
            return True
        except Exception:
            return True

    def _banner_seen(self, key: str) -> bool:
        """Check if banner was already seen for this episode."""
        if not self.stale_banner_marker.exists():
            return False
        try:
            seen = self.stale_banner_marker.read_text().strip()
            return seen == key
        except Exception:
            return False

    def _clear_stale_banner(self) -> None:
        """Clear stale banner marker."""
        self.stale_banner_marker.unlink(missing_ok=True)

    def _queue_pending(self) -> bool:
        """Check if wake queue has pending items."""
        if not self.wake_queue.exists():
            return False
        try:
            return self.wake_queue.stat().st_size > 0
        except Exception:
            return False

    def check(self, in_flight: int = 0, watcher_healthy: bool | None = None,
              current_branch: str | None = None,
              default_branch: str = "main",
              sources: int = 0,
              read_only: bool = False) -> dict[str, Any]:
        """Run all guard checks.

        Returns dict with warnings and whether supervision is needed.
        """
        warnings = []

        # Worktree tangle check (independent of in-flight)
        tangle = self.check_worktree_tangle(current_branch, default_branch)
        if tangle["tangled"]:
            warnings.append({
                "type": "tangle",
                **tangle,
            })

        # Watcher liveness check
        if watcher_healthy is None:
            liveness = self.check_watcher_liveness()
            watcher_healthy = liveness["alive"]
            if not watcher_healthy:
                # Episode dedup for stale banner
                episode_key = self._episode_key(liveness.get("reason", "unknown"))
                if read_only:
                    is_new = not self._banner_seen(episode_key)
                else:
                    is_new = self._claim_stale_banner(episode_key)

                if is_new:
                    warnings.append({
                        "type": "watcher_down",
                        "new_episode": True,
                        **liveness,
                    })
                else:
                    warnings.append({
                        "type": "watcher_down",
                        "new_episode": False,
                        "reminder": f"Watcher still down (same episode; last beat: {liveness.get('beacon_desc', 'unknown')}, grace {self.grace}s)",
                    })

        # Supervision needed if tasks in flight or sources registered
        supervision_needed = in_flight > 0 or sources > 0
        if supervision_needed and not watcher_healthy:
            warnings.append({
                "type": "supervision_needed",
                "message": f"{in_flight} task(s) in flight, but no live watcher holds this home lock",
                "action": "Start the watcher: lazy-master watcher start",
            })

        # Queued wakes warning (independent hazard)
        queue_pending = self._queue_pending()
        if queue_pending:
            if read_only:
                warnings.append({
                    "type": "queued_wakes",
                    "message": "Queued wakes pending - left untouched because this session lacks verified fleet-lock ownership.",
                })
            else:
                warnings.append({
                    "type": "queued_wakes",
                    "message": "Queued wakes pending - drain them before anything else.",
                })

        # Clear stale banner if healthy again
        if watcher_healthy and not read_only:
            self._clear_stale_banner()

        return {
            "supervision_needed": supervision_needed,
            "watcher_healthy": watcher_healthy,
            "queue_pending": queue_pending,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        }
