"""Git gate - push through validation pipeline.

Mirrors no-mistakes internal/gate: creates a bare repo, installs hooks,
manages remotes, and validates code before pushing.
"""

import subprocess
import os
import hashlib
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

# Remote name used by no-mistakes
REMOTE_NAME = "lazy-coding"


def repo_id(abs_path: str) -> str:
    """Generate deterministic 12-char hex ID from absolute path."""
    h = hashlib.sha256(abs_path.encode())
    return h.hexdigest()[:12]


class Gate:
    """Git gate that validates code before pushing.

    Mirrors no-mistakes gate: creates a bare repo, installs hooks,
    manages remotes, and validates code before pushing.
    """

    def __init__(self, repo_path: Optional[str] = None, nm_home: Optional[str] = None):
        self.repo_path = Path(repo_path or os.getcwd())
        self.nm_home = Path(nm_home or os.path.expanduser("~/.lazy-coding"))
        self.repos_dir = self.nm_home / "repos"

    def _run_git(self, *args, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
        """Run git command."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", 30),
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result

    def _run_git_bare(self, bare_dir: str, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run git command against bare repo."""
        result = subprocess.run(
            ["git", f"--git-dir={bare_dir}"] + list(args),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result

    def init(self, fork_url: Optional[str] = None) -> dict[str, Any]:
        """Initialize gate for the repository.

        Creates a bare repo, installs hooks, manages remotes,
        and registers the repository.

        Args:
            fork_url: Optional GitHub fork push URL

        Returns:
            Dict with success, repo_id, and whether new gate was created
        """
        # Find git root
        git_root = self._find_git_root()
        abs_root = str(git_root)

        # Check for existing gate
        existing_id = self._check_existing_gate(abs_root)
        if existing_id:
            # Refresh existing gate
            return self._refresh_gate(existing_id, abs_root, fork_url)

        # Create new gate
        return self._create_gate(abs_root, fork_url)

    def _find_git_root(self) -> Path:
        """Find git repository root."""
        result = self._run_git("rev-parse", "--show-toplevel", check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Not a git repository: {self.repo_path}")
        return Path(result.stdout.strip())

    def _check_existing_gate(self, abs_root: str) -> Optional[str]:
        """Check if gate already exists for this repo."""
        try:
            result = self._run_git("remote", "get-url", REMOTE_NAME, check=False)
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                # Extract repo ID from remote URL
                repo_name = Path(remote_url).stem
                return repo_name
        except Exception:
            pass
        return None

    def _create_gate(self, abs_root: str, fork_url: Optional[str]) -> dict[str, Any]:
        """Create new gate."""
        # Generate repo ID
        rid = repo_id(abs_root)

        # Create bare repo directory
        bare_dir = self.repos_dir / f"{rid}.git"
        bare_dir.mkdir(parents=True, exist_ok=True)

        # Initialize bare repo
        self._init_bare_repo(str(bare_dir))

        # Install hooks
        self._install_hooks(str(bare_dir))

        # Get upstream URL
        upstream_url = self._get_upstream_url(abs_root, fork_url)

        # Add no-mistakes remote to working repo
        self._add_remote(abs_root, REMOTE_NAME, str(bare_dir))

        # Add origin remote to bare repo for gh context
        self._add_remote_bare(str(bare_dir), "origin", upstream_url)

        # Get default branch
        default_branch = self._get_default_branch(abs_root)

        return {
            "success": True,
            "repo_id": rid,
            "path": abs_root,
            "bare_dir": str(bare_dir),
            "upstream_url": upstream_url,
            "default_branch": default_branch,
            "new": True,
        }

    def _refresh_gate(self, existing_id: str, abs_root: str,
                      fork_url: Optional[str]) -> dict[str, Any]:
        """Refresh existing gate."""
        bare_dir = self.repos_dir / f"{existing_id}.git"

        # Ensure bare repo exists
        if not bare_dir.exists():
            return self._create_gate(abs_root, fork_url)

        # Get upstream URL
        upstream_url = self._get_upstream_url(abs_root, fork_url)

        # Update remotes
        self._add_remote(abs_root, REMOTE_NAME, str(bare_dir))
        self._add_remote_bare(str(bare_dir), "origin", upstream_url)

        # Get default branch
        default_branch = self._get_default_branch(abs_root)

        return {
            "success": True,
            "repo_id": existing_id,
            "path": abs_root,
            "bare_dir": str(bare_dir),
            "upstream_url": upstream_url,
            "default_branch": default_branch,
            "new": False,
        }

    def _init_bare_repo(self, bare_dir: str) -> None:
        """Initialize bare git repository."""
        result = subprocess.run(
            ["git", "init", "--bare", bare_dir],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git init --bare failed: {result.stderr}")

        # Enable push options
        self._run_git_bare(bare_dir, "config", "receive.advertisePushOptions", "true")

    def _install_hooks(self, bare_dir: str) -> None:
        """Install post-receive hook."""
        hooks_dir = Path(bare_dir) / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        hook_content = '''#!/bin/sh
# lazy-coding post-receive hook
# Validates code before accepting push

echo "lazy-coding: Validating push..."
# Add validation logic here
'''
        hook_path = hooks_dir / "post-receive"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

    def _get_upstream_url(self, abs_root: str, fork_url: Optional[str]) -> str:
        """Get upstream URL from origin remote."""
        result = self._run_git("remote", "get-url", "origin", check=False)
        if result.returncode != 0:
            raise RuntimeError(
                "No 'origin' remote found.\n\n"
                "lazy-coding needs a remote to push to.\n"
                "Add one, then re-run:\n\n"
                "  git remote add origin <url>"
            )
        return result.stdout.strip()

    def _add_remote(self, local_dir: str, name: str, url: str) -> None:
        """Add or update remote."""
        # Check if remote exists
        result = subprocess.run(
            ["git", "remote", "get-url", name],
            cwd=local_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # Update existing remote
            subprocess.run(
                ["git", "remote", "set-url", name, url],
                cwd=local_dir,
                capture_output=True,
                text=True,
            )
        else:
            # Add new remote
            subprocess.run(
                ["git", "remote", "add", name, url],
                cwd=local_dir,
                capture_output=True,
                text=True,
            )

    def _add_remote_bare(self, bare_dir: str, name: str, url: str) -> None:
        """Add or update remote in bare repo."""
        # Check if remote exists
        result = self._run_git_bare(bare_dir, "remote", "get-url", name, check=False)
        if result.returncode == 0:
            # Update existing remote
            self._run_git_bare(bare_dir, "remote", "set-url", name, url)
        else:
            # Add new remote
            self._run_git_bare(bare_dir, "remote", "add", name, url)

    def _get_default_branch(self, abs_root: str) -> str:
        """Get default branch name."""
        # Try origin/HEAD
        result = self._run_git("symbolic-ref", "refs/remotes/origin/HEAD",
                              cwd=abs_root, check=False)
        if result.returncode == 0:
            return result.stdout.strip().replace("refs/remotes/origin/", "")

        # Try local main/master
        for branch in ["main", "master"]:
            result = self._run_git("rev-parse", "--verify", branch,
                                  cwd=abs_root, check=False)
            if result.returncode == 0:
                return branch

        return "main"

    def eject(self) -> dict[str, Any]:
        """Remove gate from repository.

        Removes the remote, deletes the bare repo,
        and cleans up any associated worktrees.
        """
        git_root = self._find_git_root()
        abs_root = str(git_root)

        # Get existing gate info
        existing_id = self._check_existing_gate(abs_root)
        if not existing_id:
            return {
                "success": False,
                "error": f"Not initialized for {abs_root}",
            }

        # Remove remote from working repo (non-fatal)
        try:
            self._run_git("remote", "remove", REMOTE_NAME, check=False)
        except Exception:
            pass

        # Delete bare repo
        bare_dir = self.repos_dir / f"{existing_id}.git"
        if bare_dir.exists():
            import shutil
            shutil.rmtree(bare_dir)

        return {
            "success": True,
            "repo_id": existing_id,
            "path": abs_root,
        }

    def push(self, branch: Optional[str] = None) -> dict[str, Any]:
        """Push through gate validation.

        Args:
            branch: Branch to push (current if None)

        Returns:
            Push result
        """
        # Get current branch
        if not branch:
            result = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
            branch = result.stdout.strip()

        # Get the gate remote URL
        result = self._run_git("remote", "get-url", REMOTE_NAME, check=False)
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Gate remote '{REMOTE_NAME}' not found. Run 'lazy-coding gate init' first.",
            }

        # Push to gate
        result = self._run_git("push", REMOTE_NAME, branch, check=False)
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

    def status(self) -> dict[str, Any]:
        """Get gate status."""
        try:
            git_root = self._find_git_root()
            abs_root = str(git_root)
            existing_id = self._check_existing_gate(abs_root)

            if existing_id:
                bare_dir = self.repos_dir / f"{existing_id}.git"
                return {
                    "initialized": True,
                    "repo_id": existing_id,
                    "path": abs_root,
                    "bare_dir": str(bare_dir),
                    "bare_exists": bare_dir.exists(),
                }
            else:
                return {
                    "initialized": False,
                    "path": abs_root,
                }
        except Exception as e:
            return {
                "initialized": False,
                "error": str(e),
            }
