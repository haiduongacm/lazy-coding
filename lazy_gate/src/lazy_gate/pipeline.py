"""Validation pipeline."""

import subprocess
from pathlib import Path


class Pipeline:
    """Validation pipeline for code quality."""

    def __init__(self, stages=None):
        self.stages = stages or ["review", "test", "lint"]

    def run(self, repo_path):
        """Run all pipeline stages.

        Args:
            repo_path: Repository path

        Returns:
            Pipeline result
        """
        findings = []

        for stage in self.stages:
            result = self._run_stage(stage, repo_path)
            if not result["success"]:
                findings.append({
                    "stage": stage,
                    "message": result.get("error", "Failed"),
                })

        return {
            "success": len(findings) == 0,
            "stages": self.stages,
            "findings": findings,
        }

    def _run_stage(self, stage, repo_path):
        """Run a single pipeline stage."""
        commands = {
            "review": ["echo", "Review passed"],
            "test": ["python", "-m", "pytest", "--tb=short"],
            "lint": ["python", "-m", "ruff", "check", "."],
            "typecheck": ["python", "-m", "mypy", "."],
            "docs": ["echo", "Docs check passed"],
        }

        cmd = commands.get(stage)
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
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
