"""Discover installed Proton / Wine compatibility tool directories."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import vdf

from proton_manager.model import ProtonTool


def discover_proton_tools(steam_root: Path) -> dict[str, ProtonTool]:
    """Return a map of tool-name → :class:`ProtonTool` for every tool found.

    Searches:
    - ``<steam_root>/compatibilitytools.d/``
    - ``~/.steam/compatibilitytools.d/``       (custom tools, e.g. GE-Proton)
    - ``~/.local/share/Steam/compatibilitytools.d/``
    """
    tools: dict[str, ProtonTool] = {}

    search_dirs = _unique(
        [
            steam_root / "compatibilitytools.d",
            Path.home() / ".steam" / "compatibilitytools.d",
            Path.home() / ".local" / "share" / "Steam" / "compatibilitytools.d",
        ]
    )

    for compat_dir in search_dirs:
        if not compat_dir.is_dir():
            continue
        for tool_dir in sorted(compat_dir.iterdir()):
            if not tool_dir.is_dir():
                continue
            name, version = _extract_tool_identity(tool_dir)
            if name and name not in tools:
                tools[name] = ProtonTool(
                    name=name,
                    version=version,
                    install_path=tool_dir,
                )

    return tools


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        try:
            r = p.resolve()
        except OSError:
            r = p
        if r not in seen:
            seen.add(r)
            out.append(p)
    return out


def _extract_tool_identity(tool_dir: Path) -> tuple[str, str]:
    """Return ``(canonical_name, version)`` for *tool_dir*.

    Priority for name: ``compatibilitytool.vdf`` registered name → directory name.
    Priority for version: ``version`` file → ``toolmanifest.vdf`` field → "unknown".
    """
    name = ""
    version = ""

    # 1. Canonical name from compatibilitytool.vdf
    # Structure: "compatibilitytools" > "compat_tools" > "<tool_name>" > { ... }
    vdf_path = tool_dir / "compatibilitytool.vdf"
    if vdf_path.exists():
        try:
            with vdf_path.open(encoding="utf-8", errors="replace") as fh:
                data = vdf.load(fh)
            top = data.get("compatibilitytools") or data.get("CompatibilityTools") or {}
            # Dig one more level if the first key is the grouping key "compat_tools"
            inner = top
            for key in ("compat_tools", "CompatTools", "tools"):
                if key in top and isinstance(top[key], dict):
                    inner = top[key]
                    break
            for tool_key in inner:
                if isinstance(inner[tool_key], dict):
                    name = tool_key
                    break
        except Exception:
            pass

    if not name:
        name = tool_dir.name

    # 2. Version from plain-text version file
    ver_file = tool_dir / "version"
    if ver_file.exists():
        with suppress(Exception):
            version = ver_file.read_text(encoding="utf-8").strip().splitlines()[0]

    # 3. Fallback: toolmanifest.vdf
    if not version:
        manifest = tool_dir / "toolmanifest.vdf"
        if manifest.exists():
            try:
                with manifest.open(encoding="utf-8", errors="replace") as fh:
                    data = vdf.load(fh)
                version = data.get("manifest", {}).get("version", "")
            except Exception:
                pass

    return name, version or "unknown"
