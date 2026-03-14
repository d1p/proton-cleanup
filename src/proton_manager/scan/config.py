"""Parse Steam's global config.vdf to obtain per-game compat tool mappings."""
from __future__ import annotations

from pathlib import Path

import vdf


def load_compat_tool_mapping(steam_root: Path) -> dict[str, str]:
    """Return a map of app_id (str) → tool_name (str) from CompatToolMapping.

    Reads ``<steam_root>/config/config.vdf``.
    Returns an empty dict on any error so callers never need to handle exceptions.
    """
    cfg_path = steam_root / "config" / "config.vdf"
    if not cfg_path.exists():
        return {}

    try:
        with cfg_path.open(encoding="utf-8", errors="replace") as fh:
            data = vdf.load(fh)
    except Exception:
        return {}

    try:
        mapping: dict = (
            data["InstallConfigStore"]["Software"]["Valve"]["Steam"]["CompatToolMapping"]
        )
    except (KeyError, TypeError):
        return {}

    result: dict[str, str] = {}
    for app_id, val in mapping.items():
        if isinstance(val, dict):
            name = val.get("name", "").strip()
        else:
            name = str(val).strip()
        if name:
            result[str(app_id)] = name

    return result
