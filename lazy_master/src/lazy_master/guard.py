"""lazy-master guard - Watcher liveness and worktree-tangle guard.

Mirrors firstmate fm-guard.sh: called by supervision scripts.
Warns if primary checkout is on non-default branch.
Warns if tasks in flight but supervision is not healthy.

Key concepts from fm-guard.sh:
- Pull-based: only warns when some other script runs
- Worktree-tangle check: primary checkout on non-default branch
- Watcher liveness check: tasks in flight but no live watcher
- Grace period for watcher downtime
- Always exits 0: guard warns, never blocks
"""

import os
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class Guard:
    """Guard - watcher liveness and worktree-tangle guard.

    Mirrors firstmate fm-guard.sh:
    - Always warns if primary checkout is on named non-default branch
    - Warns if tasks in flight but supervision not healthy
    - Always exits 0: guard warns, never blocks
    """

    def __init__(self, state_dir: str | None = None, grace: int = 300):
        """
        Args:
            state_dir: State directory path
            grace: Seconds before watcher is considered down
        """
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.grace = grace
        self.last_beat_file = self.state_dir / ".last-watcher-beat"

    def check_watcher_liveness(self) -> dict[str, Any]:
        """Check if watcher is alive.

        Mirrors firstmate: reads .last-watcher-beat timestamp.
        """
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
        """Check if primary checkout is on non-default branch.

        Mirrors firstmate: always warns if on named non-default branch.
        """
        if current_branch is None:
            # Try to detect current branch
            try:
                import subprocess
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

    def check(self, in_flight: int = 0, watcher_healthy: bool | None = None,
              current_branch: str | None = None,
              default_branch: str = "main") -> dict[str, Any]:
        """Run all guard checks.

        Returns dict with warnings and whether supervision is needed.
        """
        warnings = []

        # Worktree tangle check
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
                warnings.append({
                    "type": "watcher_down",
                    **liveness,
                })

        # Supervision needed if tasks in flight
        supervision_needed = in_flight > 0
        if supervision_needed and not watcher_healthy:
            warnings.append({
                "type": "supervision_needed",
                "message": f"{in_flight} task(s) in flight, but no live watcher holds this home lock",
                "action": "Start the watcher: lazy-master watcher start",
            })

        return {
            "supervision_needed": supervision_needed,
            "watcher_healthy": watcher_healthy,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        }
