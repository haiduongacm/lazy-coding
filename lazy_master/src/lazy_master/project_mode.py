"""lazy-master project_mode - Project delivery posture.

Mirrors firstmate fm-project-mode.sh: resolve registered delivery posture
from data/projects.md registry.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ProjectMode:
    """Project delivery posture.

    Mirrors firstmate:
    - no-mistakes: full pipeline -> PR -> configured merge authority
    - direct-PR: push + PR via gh-axi, no pipeline
    - local-only: local branch, no remote/PR, guarded local merge
    """

    VALID_MODES = ("no-mistakes", "direct-PR", "local-only", "no-mistakes-prod-only")

    def resolve(self, project_name: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
        """Resolve project's registered delivery posture.

        Returns mode and yolo merge posture.
        """
        if not registry or project_name not in registry:
            return {"mode": "no-mistakes", "yolo": "off", "warning": f"Project {project_name} not in registry"}

        entry = registry[project_name]
        mode = entry.get("mode", "no-mistakes")
        yolo = entry.get("yolo", "off")

        if mode not in self.VALID_MODES:
            return {"mode": "no-mistakes", "yolo": "off", "warning": f"Unknown mode {mode}"}

        # Map conditional policy to most rigorous leg
        if mode == "no-mistakes-prod-only":
            mode = "no-mistakes"

        return {"mode": mode, "yolo": yolo}
