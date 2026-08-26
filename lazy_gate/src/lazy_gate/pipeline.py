"""Validation pipeline.

Mirrors no-mistakes pipeline stages: review, test, lint, document.
"""

import subprocess
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class Pipeline:
    """Validation pipeline for code quality.

    Mirrors no-mistakes pipeline with configurable stages.
    """

    def __init__(self, stages: Optional[list[str]] = None, commands: Optional[dict[str, list[str]]] = None):
        self.stages = stages if stages is not None else ["review", "test", "lint"]
        self.commands = commands or {
            "review": ["echo", "Review passed"],
            "test": ["python", "-m", "pytest", "--tb=short"],
            "lint": ["python", "-m", "ruff", "check", "."],
            "typecheck": ["python", "-m", "mypy", "."],
            "document": ["echo", "Docs check passed"],
        }

    def run(self, repo_path: str, branch: Optional[str] = None) -> dict[str, Any]:
        """Run all pipeline stages.

        Args:
            repo_path: Repository path
            branch: Branch to validate (optional)

        Returns:
            Pipeline result with success status and findings
        """
        findings = []
        results = []

        for stage in self.stages:
            result = self._run_stage(stage, repo_path)
            results.append({
                "stage": stage,
                **result,
            })

            if not result["success"]:
                findings.append({
                    "stage": stage,
                    "message": result.get("error", "Failed"),
                    "action": "ask-user",
                })

        return {
            "success": len(findings) == 0,
            "stages": self.stages,
            "results": results,
            "findings": findings,
            "timestamp": datetime.now().isoformat(),
        }

    def _run_stage(self, stage: str, repo_path: str) -> dict[str, Any]:
        """Run a single pipeline stage."""
        cmd = self.commands.get(stage)
        if not cmd:
            return {"success": True, "error": None}

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "success": result.returncode == 0,
                "error": result.stderr if result.returncode != 0 else None,
                "output": result.stdout[:1000] if result.stdout else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"success": False, "error": f"Command not found: {cmd[0]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_stage(self, stage: str, command: list[str]) -> None:
        """Add a custom stage to the pipeline."""
        if stage not in self.stages:
            self.stages.append(stage)
        self.commands[stage] = command

    def remove_stage(self, stage: str) -> None:
        """Remove a stage from the pipeline."""
        if stage in self.stages:
            self.stages.remove(stage)
        self.commands.pop(stage, None)
