"""Data model: shared types consumed by scan modules, GUI, and JSON output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Confidence(str, Enum):
    """Evidence quality for a Proton mapping."""

    HIGH = "HIGH"
    """Explicit compat-tool override + prefix exists + tool installed locally."""
    MEDIUM = "MEDIUM"
    """Tool detected but prefix missing or tool not installed locally."""
    LOW = "LOW"
    """Tool name inferred only; no prefix or version file evidence."""
    UNKNOWN = "UNKNOWN"
    """No Proton data; game likely native Linux or never launched under Proton."""

    # Ordering for --min-confidence comparisons (highest → lowest)
    _order_ = "HIGH MEDIUM LOW UNKNOWN"

    def __lt__(self, other: Confidence) -> bool:
        order = [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW, Confidence.UNKNOWN]
        return order.index(self) > order.index(other)


class GameKind(str, Enum):
    STEAM = "Steam"
    SHORTCUT = "Shortcut"
    ORPHAN = "Orphan"
    """A Wine prefix in compatdata with no matching game manifest or shortcut."""
    UNUSED_TOOL = "Unused Tool"
    """A Proton tool installed in compatibilitytools.d not used by any game."""


@dataclass
class ProtonTool:
    """An installed Proton / Wine compatibility tool."""

    name: str
    """Canonical tool name as registered in compatibilitytool.vdf (e.g. 'Proton-8.0-5')."""
    version: str
    """Version string from the 'version' file or toolmanifest.vdf."""
    install_path: Path
    """Directory containing the tool files."""


@dataclass
class GameEntry:
    """A single game row in the scanner output."""

    app_id: str
    """Steam AppID (numeric string) or shortcut-derived pseudo-ID."""
    name: str
    """Game name from manifest or shortcut."""
    kind: GameKind

    proton_tool: str | None
    """Resolved tool name (may be inferred)."""
    proton_version: str | None
    """Version string from the prefix version file, if available."""

    prefix_path: Path | None
    """Path to the Wine prefix (pfx/ directory or compatdata/ root)."""
    prefix_exists: bool
    """True when the prefix directory actually exists on disk."""

    tool_installed: bool
    """True when the named tool directory exists locally."""

    confidence: Confidence
    evidence: list[str] = field(default_factory=list)
    """Human-readable evidence items explaining the mapping."""
    warnings: list[str] = field(default_factory=list)
    """Non-fatal anomalies (missing prefix, uninstalled tool, etc.)."""
    prefix_size: int | None = None
    """Disk usage in bytes of the prefix/tool directory.  None until calculated."""

    def human_size(self) -> str:
        """Return a human-readable size string, or '—' if not yet calculated."""
        if self.prefix_size is None:
            return "—"
        n: float = self.prefix_size
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
            n /= 1024
        return "—"  # unreachable
