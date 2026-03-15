"""Directory size calculation utility."""

from __future__ import annotations

from pathlib import Path


def calc_dir_size(path: Path) -> int:
    """Return total disk usage of *path* in bytes.

    Recursively sums ``st_size`` for all regular files.
    Symbolic links are skipped to avoid double-counting and infinite loops.
    Individual ``OSError`` exceptions are silently ignored.
    Returns 0 if *path* does not exist or is not a directory.
    """
    if not path.is_dir():
        return 0
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_symlink():
                continue
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return total
