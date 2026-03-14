"""Auto-detect Steam root directories for native and Flatpak installs."""
from __future__ import annotations

import os
from pathlib import Path

# Ordered candidate paths; first readable match(es) are used.
_CANDIDATE_ROOTS: list[Path] = [
    # Native Steam
    Path.home() / ".steam" / "root",
    Path.home() / ".local" / "share" / "Steam",
    # Flatpak Steam
    Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "root",
    Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
]


def discover_steam_roots(override: Path | None = None) -> list[Path]:
    """Return all readable Steam root directories found on this system.

    Parameters
    ----------
    override:
        When provided, skip auto-detection and use exactly this path.
        Raises ``FileNotFoundError`` if the path does not exist.
    """
    if override is not None:
        resolved = override.resolve()
        if not resolved.is_dir():
            raise FileNotFoundError(
                f"Provided --steam-root does not exist or is not a directory: {override}"
            )
        return [resolved]

    seen: set[Path] = set()
    found: list[Path] = []
    for candidate in _CANDIDATE_ROOTS:
        try:
            real = candidate.resolve()
            if real in seen:
                continue
            if real.is_dir() and os.access(real, os.R_OK):
                seen.add(real)
                found.append(real)
        except (PermissionError, OSError):
            pass

    return found
