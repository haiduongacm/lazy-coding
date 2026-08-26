"""lazy-master guard - Watcher liveness and worktree-tangle guard.

Mirrors firstmate fm-guard.sh: called by supervision scripts.
Warns if primary checkout is on non-default branch.
Warns if tasks in flight but supervision is not healthy.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Guard:
    """Guard - watcher liveness and worktree-tangle guard.

    Mirrors firstmate fm-guard.sh:
    - Always warns if primary checkout is on named non-default branch
    - Warns if tasks in flight but supervision not healthy
    - Always exits 0: guard warns, never blocks
    """

    grace: int = 300  # seconds

    def check(self, in_flight: int = 0, watcher_healthy: bool = True,
              tangle_branch: str | None = None) -> dict[str, Any]:
        """Check guard conditions.

        Returns dict with warnings and whether supervision is needed.
        """
        warnings = []

        # Worktree tangle check
        if tangle_branch:
            warnings.append({
                "type": "tangle",
                "message": f"Primary checkout is on feature branch '{tangle_branch}', not default branch",
                "action": "git checkout <default-branch>",
            })

        # Supervision health check
        supervision_needed = in_flight > 0
        if supervision_needed and not watcher_healthy:
            warnings.append({
                "type": "watcher_down",
                "message": f"{in_flight} task(s) in flight, but no live watcher holds this home lock",
                "action": "Repair missing watcher supervision",
            })

        return {
            "supervision_needed": supervision_needed,
            "watcher_healthy": watcher_healthy,
            "warnings": warnings,
        }
