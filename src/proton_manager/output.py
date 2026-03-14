"""JSON serialisation and table-row adapters shared by CLI and TUI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proton_manager.model import Confidence, GameEntry, GameKind

# Ordered column headers for the table
COLUMNS: list[tuple[str, int]] = [
    ("Game",        30),
    ("Kind",        14),
    ("App ID",      12),
    ("Tool",        22),
    ("Version",     14),
    ("Prefix",      40),
    ("Confidence",  10),
    ("Status",      10),
]


def entry_to_row(entry: GameEntry) -> tuple[str, ...]:
    """Return a tuple of display strings matching :data:`COLUMNS` order."""
    status = _status(entry)
    prefix_display = ""
    if entry.prefix_path:
        try:
            prefix_display = str(entry.prefix_path.relative_to(Path.home()))
            prefix_display = "~/" + prefix_display
        except ValueError:
            prefix_display = str(entry.prefix_path)

    return (
        entry.name,
        entry.kind.value,
        entry.app_id,
        entry.proton_tool or "—",
        entry.proton_version or "—",
        prefix_display or "—",
        entry.confidence.value,
        status,
    )


def _status(entry: GameEntry) -> str:
    if entry.kind == GameKind.ORPHAN:
        return "ORPHAN"
    if entry.kind == GameKind.UNUSED_TOOL:
        return "UNUSED"
    if entry.warnings:
        return "WARN"
    if entry.prefix_exists:
        return "OK"
    if entry.proton_tool:
        return "NO PFX"
    return "—"


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def entries_to_json(entries: list[GameEntry], *, indent: int = 2) -> str:
    return json.dumps([_entry_to_dict(e) for e in entries], indent=indent)


def _entry_to_dict(entry: GameEntry) -> dict[str, Any]:
    return {
        "app_id": entry.app_id,
        "name": entry.name,
        "kind": entry.kind.value,
        "proton_tool": entry.proton_tool,
        "proton_version": entry.proton_version,
        "prefix_path": str(entry.prefix_path) if entry.prefix_path else None,
        "prefix_exists": entry.prefix_exists,
        "tool_installed": entry.tool_installed,
        "confidence": entry.confidence.value,
        "evidence": entry.evidence,
        "warnings": entry.warnings,
    }
