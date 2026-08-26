"""Worktree layout management.

Mirrors no-mistakes internal/worktrees: resolves where a repository's
pipeline run worktrees live.

By default a run worktree is created at <NM_HOME>/worktrees/<repoID>/<runID>,
which is deliberately outside every checkout. The worktree_roots map in the
global config lets an operator name the directory a repository's run worktrees
are created in.
"""

from pathlib import Path
from typing import Optional
import os


def canonical(path: str) -> str:
    """Canonical path for comparison.

    Resolves symlinks and normalizes for cross-platform compatibility.
    macOS reports /private/var for a /var path, so a single spelling
    is not enough to recognize the same checkout.
    """
    cleaned = os.path.normpath(path)
    if os.path.isabs(cleaned):
        # Resolve deepest existing ancestor
        current = cleaned
        rest = ""
        while True:
            try:
                resolved = os.path.realpath(current)
                return os.path.normpath(os.path.join(resolved, rest))
            except (OSError, ValueError):
                parent = os.path.dirname(current)
                if parent == current:
                    return cleaned
                rest = os.path.join(os.path.basename(current), rest)
                current = parent
    return cleaned


def contains(dir_path: str, path: str) -> bool:
    """Check if path is inside dir_path.

    Uses both spelling comparison and filesystem identity check
    for case-insensitive volumes.
    """
    return _contains_by_spelling(dir_path, path) or _contains_by_identity(dir_path, path)


def _contains_by_spelling(dir_path: str, path: str) -> bool:
    """Check containment by path spelling."""
    try:
        rel = os.path.relpath(canonical(path), canonical(dir_path))
        return rel == "." or (not rel.startswith("..") and not os.path.isabs(rel))
    except ValueError:
        return False


def _contains_by_identity(dir_path: str, path: str) -> bool:
    """Check containment by filesystem identity.

    Walks upward to handle paths that don't exist yet.
    """
    try:
        dir_info = os.stat(dir_path)
    except (OSError, ValueError):
        return False

    current = canonical(path)
    while True:
        try:
            info = os.stat(current)
            if os.path.samestat(dir_info, info):
                return True
        except (OSError, ValueError):
            pass

        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


def check_placement(nm_home: str, checkout: str, root: str,
                    other_checkouts: Optional[list[str]] = None) -> Optional[str]:
    """Validate worktree root placement.

    Returns error message if placement is invalid, None if valid.

    Policy:
    - A root inside NM_HOME collides with daemon state
    - A root inside ANY checkout puts an untracked directory there
    """
    if contains(nm_home, root):
        return (f'"{root}" is inside no-mistakes\' own state directory "{nm_home}", '
                f'where it would collide with the daemon\'s worktrees, logs, or gates')

    if checkout and contains(checkout, root):
        return (f'"{root}" is inside the checkout whose runs it would hold, '
                f'which leaves that checkout with an untracked run worktree')

    if other_checkouts:
        own = canonical(checkout)
        others = sorted(other_checkouts)
        for other in others:
            if not other or canonical(other) == own:
                continue
            if contains(other, root):
                return (f'"{root}" is inside the checkout "{other}", '
                        f'which every run placed there would leave with an untracked run worktree')

    return None


class Layout:
    """Layout maps a repository to the directory holding its run worktrees."""

    def __init__(self, nm_home: str, roots: Optional[dict[str, str]] = None):
        """
        Args:
            nm_home: Path to NM_HOME directory
            roots: Mapping of checkout path to custom worktree root
        """
        self.nm_home = nm_home
        self.roots: dict[str, str] = {}
        if roots:
            for checkout, root in roots.items():
                self.roots[canonical(checkout)] = os.path.normpath(root)

    def dir(self, repo_id: str, run_id: str, working_path: Optional[str] = None) -> str:
        """Resolve where a NEW run's worktree belongs.

        This is the only placement decision made from configuration,
        made once at run creation.
        """
        if working_path:
            custom_root = self.custom_root(working_path)
            if custom_root:
                return os.path.join(custom_root, run_id)

        # Default placement
        return os.path.join(self.nm_home, "worktrees", repo_id, run_id)

    def recorded_dir(self, recorded: str, repo_id: str, run_id: str) -> str:
        """Return the worktree directory of an EXISTING run.

        Reads back the placement resolved at run creation rather than
        re-deriving it, so mid-flight config edits are inert.
        """
        if recorded and recorded.strip():
            return os.path.normpath(recorded)

        # Default placement for legacy rows
        return os.path.join(self.nm_home, "worktrees", repo_id, run_id)

    def custom_root(self, working_path: str) -> Optional[str]:
        """Get configured worktree root for a checkout, if any."""
        if not self.roots or not working_path.strip():
            return None
        return self.roots.get(canonical(working_path))

    def checkouts(self) -> list[str]:
        """Get canonical checkout paths of all configured entries."""
        return list(self.roots.keys())

    def validate(self, known: Optional[list[str]] = None) -> Optional[str]:
        """Validate all configured entries.

        Returns error message if any entry is invalid, None if valid.
        """
        checkouts = sorted(self.checkouts())
        for checkout in checkouts:
            err = self._validate_entry(checkout, known)
            if err:
                return err
        return None

    def _validate_entry(self, checkout: str, known: Optional[list[str]] = None) -> Optional[str]:
        """Validate one canonical entry."""
        root = self.roots.get(checkout)
        if not root:
            return None

        protected = list(known or [])
        protected.extend(self.checkouts())

        return check_placement(self.nm_home, checkout, root, protected)
