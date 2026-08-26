"""Git gate - push through validation pipeline."""

import subprocess
from pathlib import Path


class Gate:
    """Git gate that validates code before pushing."""

    def __init__(self, repo_path=None, pipeline=None):
        self.repo_path = Path(repo_path or Path.cwd())
        self.pipeline = pipeline or ["review", "test", "lint"]

    def _run(self, *args, **kwargs):
        """Run command."""
        result = subprocess.run(
            list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result

    def push(self, branch=None):
        """Push through gate validation.

        Args:
            branch: Branch to push (current if None)

        Returns:
            Push result
        """
        # Get current branch
        if not branch:
            result = self._run("git", "rev-parse", "--abbrev-ref", "HEAD")
            branch = result.stdout.strip()

        # Run pipeline
        pipeline_result = self.pipeline.run(self.repo_path)
        if not pipeline_result["success"]:
            return {
                "success": False,
                "error": "Pipeline failed",
                "findings": pipeline_result.get("findings", []),
            }

        # Push to origin
        result = self._run("git", "push", "origin", branch)
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Push failed: {result.stderr}",
            }

        return {
            "success": True,
            "branch": branch,
            "message": f"Pushed {branch} through gate",
        }
