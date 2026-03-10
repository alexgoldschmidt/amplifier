"""Amplifier bundle for parallel git worktree orchestration."""

from pathlib import Path


def get_bundle_path() -> Path:
    """Return the path to the bundle root directory."""
    return Path(__file__).parent.parent
