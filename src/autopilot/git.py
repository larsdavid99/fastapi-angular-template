"""The branch checked out, read through the `git` CLI. The only place that runs git."""

from __future__ import annotations

import subprocess


def changed_paths(cwd: str) -> list[str] | None:
    """What the branch changes since it left main, as its PR shows it.

    None when git can't tell, for example without `origin/main` fetched.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "origin/main...HEAD", "--name-only"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.split()
