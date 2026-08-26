"""lazy-master fleet_snapshot - Read-only structured fleet snapshot.

Mirrors firstmate fm-fleet-snapshot.sh: read-only structured snapshot
of the firstmate fleet.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


@dataclass
class FleetSnapshot:
    """Read-only structured fleet snapshot.

    Mirrors firstmate fm-fleet-snapshot.sh:
    - schema: stable schema id
    - generated: UTC observation time
    - tasks[]: one row per state/<id>.meta
    - backlog: {path, present, records[]}
    """

    def generate(self, tasks: list[dict[str, Any]] | None = None,
                 backlog: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate fleet snapshot."""
        now = datetime.now(timezone.utc).isoformat()

        return {
            "schema": "fm-fleet-snapshot.v1",
            "generated": now,
            "tasks": tasks or [],
            "backlog": backlog or {"path": "", "present": False, "records": []},
            "main_inventory": {
                "valid": True,
                "reason": "",
                "orphan_in_flight": [],
                "unstructured_current_count": 0,
            },
        }
