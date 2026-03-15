"""Framework-agnostic delete helpers for Proton environments.

These helpers contain no UI-framework imports so they can be used from
both the PySide6 GUI and the test suite.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from proton_manager.model import GameEntry, GameKind

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def deleteable_path(entry: GameEntry) -> Path | None:
    """Return the directory that will be deleted for *entry*.

    * **UNUSED_TOOL** → the tool install directory inside ``compatibilitytools.d/``.
    * **Everything else** → the ``compatdata/<app_id>/`` directory.  If
      ``prefix_path`` already points at the ``pfx/`` sub-directory we step up
      one level to reach the ``compatdata/<id>/`` parent.
    """
    if entry.prefix_path is None:
        return None
    p = entry.prefix_path
    if entry.kind == GameKind.UNUSED_TOOL:
        return p
    # For game entries prefix_path may be pfx/ itself.
    if p.name == "pfx":
        return p.parent
    return p


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d  %H:%M")


def entry_timestamps(entry: GameEntry) -> tuple[str, str]:
    """Return ``(created, last_modified)`` human-readable strings.

    *created*:       inode birth time when available (Python 3.12+ on supported
                     filesystems), otherwise the inode-change time (``ctime``).
    *last_modified*: mtime of the ``version`` or ``toolmanifest.vdf`` file
                     inside the directory (updated by Steam/Proton on each
                     launch) with fallback to the directory's own mtime.
    """
    path = deleteable_path(entry)
    if path is None or not path.exists():
        return "—", "—"
    try:
        st = path.stat()
        created = _fmt_ts(getattr(st, "st_birthtime", None) or st.st_ctime)
        for marker in ("version", "toolmanifest.vdf"):
            cand = path / marker
            if cand.exists():
                return created, _fmt_ts(cand.stat().st_mtime)
        return created, _fmt_ts(st.st_mtime)
    except OSError:
        return "—", "—"


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

_SAFE_PARENT_NAMES: frozenset[str] = frozenset({"compatdata", "compatibilitytools.d"})


def delete_entry(entry: GameEntry) -> tuple[bool, str]:
    """Delete the directory associated with *entry*.

    Includes a safety check: only directories whose immediate parent is named
    ``compatdata`` or ``compatibilitytools.d`` may be deleted.  This prevents
    accidental deletion if ``prefix_path`` were somehow set to an unexpected
    location.

    Returns ``(True, "")`` on success or ``(False, reason)`` on failure.
    """
    path = deleteable_path(entry)
    if path is None:
        return False, "No path is associated with this entry"
    if not path.exists():
        return True, ""  # already gone — treat as success
    if path.is_symlink():
        return False, f"Refusing to follow symbolic link: {path}"
    if not path.is_dir():
        return False, f"Expected a directory at: {path}"

    if path.parent.name not in _SAFE_PARENT_NAMES:
        return False, (
            f"Safety check failed: '{path.parent.name}' is not a recognised "
            "Steam sub-directory.  Expected parent name to be 'compatdata' "
            "or 'compatibilitytools.d'."
        )

    try:
        shutil.rmtree(path)
        return True, ""
    except PermissionError as exc:
        return False, f"Permission denied: {exc}"
    except OSError as exc:
        return False, f"Could not delete directory: {exc}"
