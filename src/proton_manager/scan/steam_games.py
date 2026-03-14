"""Parse appmanifest_*.acf files and map Steam games to Proton environments."""
from __future__ import annotations

from pathlib import Path

import vdf

from proton_manager.model import Confidence, GameEntry, GameKind, ProtonTool
from proton_manager.scan.libraries import collect_app_manifests, compatdata_root


def scan_steam_games(
    steamapps: Path,
    proton_tools: dict[str, ProtonTool],
    compat_tool_mapping: dict[str, str] | None = None,
) -> list[GameEntry]:
    """Return a :class:`GameEntry` for every app manifest found in *steamapps*.

    Parameters
    ----------
    compat_tool_mapping:
        Per-game override map from ``config.vdf`` (app_id → tool_name).  When
        provided, takes precedence over manifest-level keys.
    """
    compat_root = compatdata_root(steamapps)
    mapping = compat_tool_mapping or {}
    return [
        entry
        for path in collect_app_manifests(steamapps)
        for entry in [_parse_manifest(path, compat_root, proton_tools, mapping)]
        if entry is not None
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_manifest(
    manifest_path: Path,
    compat_root: Path,
    proton_tools: dict[str, ProtonTool],
    compat_tool_mapping: dict[str, str],
) -> GameEntry | None:
    try:
        with manifest_path.open(encoding="utf-8", errors="replace") as fh:
            data = vdf.load(fh)
    except Exception as exc:
        app_id = manifest_path.stem.replace("appmanifest_", "")
        return GameEntry(
            app_id=app_id,
            name="<parse error>",
            kind=GameKind.STEAM,
            proton_tool=None,
            proton_version=None,
            prefix_path=None,
            prefix_exists=False,
            tool_installed=False,
            confidence=Confidence.UNKNOWN,
            evidence=[],
            warnings=[f"Failed to parse {manifest_path.name}: {exc}"],
        )

    state = data.get("AppState") or data.get("appstate") or {}
    app_id = str(state.get("appid") or manifest_path.stem.replace("appmanifest_", ""))
    name = str(state.get("name") or state.get("Name") or f"App {app_id}")

    evidence: list[str] = []
    warnings: list[str] = []

    # --- Compat tool detection ---
    # 1. Authoritative: config.vdf CompatToolMapping (highest priority)
    tool_name = compat_tool_mapping.get(app_id)
    if tool_name:
        evidence.append(f"Compat-tool from config.vdf CompatToolMapping: {tool_name!r}")
    else:
        # 2. Fallback: manifest-level keys
        tool_name = _find_compat_tool(state)
        if tool_name:
            evidence.append(f"Compat-tool from app manifest: {tool_name!r}")

    # --- Prefix / compatdata ---
    prefix_dir = compat_root / app_id
    pfx_path = prefix_dir / "pfx"
    prefix_exists = pfx_path.is_dir()

    if prefix_exists:
        evidence.append(f"Wine prefix exists: {pfx_path}")
    elif prefix_dir.is_dir():
        evidence.append(f"Compatdata dir present (no pfx/ yet): {prefix_dir}")
    else:
        warnings.append(
            "No compatdata directory — game may be native Linux or never launched under Proton"
        )

    # --- Prefix version file ---
    proton_version: str | None = None
    ver_file = prefix_dir / "version"
    if ver_file.exists():
        try:
            proton_version = ver_file.read_text(encoding="utf-8").strip().splitlines()[0]
            evidence.append(f"Prefix version file: {proton_version}")
        except Exception:
            warnings.append("Could not read prefix version file")

    # --- config_info: may contain the exact Proton install path ---
    config_info_tool: str | None = None
    config_info = prefix_dir / "config_info"
    if config_info.exists() and not tool_name:
        try:
            ci_text = config_info.read_bytes()
            ci_str = ci_text.decode("utf-8", errors="replace")
            # Look for a path fragment ending in 'Proton X.Y' or 'GE-ProtonX-Y'
            import re as _re
            m = _re.search(
                r"steamapps/common/((?:Proton|GE-Proton)[^\n/]+?)(?:/|\n)",
                ci_str,
            )
            if m:
                config_info_tool = m.group(1).strip()
                evidence.append(f"Proton tool from config_info: {config_info_tool!r}")
        except Exception:
            pass

    # --- Skip games with no Proton data at all (native Linux titles) ---
    if not tool_name and not prefix_dir.is_dir():
        return None

    # Merge config_info discovery into tool_name if still unset
    if not tool_name and config_info_tool:
        tool_name = config_info_tool

    # --- Resolve tool name to an installed tool ---
    resolved_tool, tool_installed = _resolve_tool(tool_name, proton_version, proton_tools, evidence, warnings)

    confidence = _compute_confidence(
        has_explicit_tool=bool(tool_name),
        prefix_exists=prefix_exists,
        tool_installed=tool_installed,
        has_version_file=proton_version is not None,
    )

    return GameEntry(
        app_id=app_id,
        name=name,
        kind=GameKind.STEAM,
        proton_tool=resolved_tool,
        proton_version=proton_version,
        prefix_path=pfx_path if prefix_exists else (prefix_dir if prefix_dir.is_dir() else None),
        prefix_exists=prefix_exists,
        tool_installed=tool_installed,
        confidence=confidence,
        evidence=evidence,
        warnings=warnings,
    )


def _find_compat_tool(state: dict) -> str | None:
    """Extract explicit compat-tool name from AppState dict, checking all known locations."""
    # AppState-level keys used by different Steam versions
    for key in ("CompatTools", "compattools", "SelectedCompatTool"):
        val = state.get(key)
        if val and isinstance(val, str):
            return val

    # UserConfig sub-section
    user_config = state.get("UserConfig") or state.get("userconfig") or {}
    if isinstance(user_config, dict):
        for key in ("proton_version", "CompatTool", "compattools", "PROTON_VERSION"):
            val = user_config.get(key)
            if val and isinstance(val, str):
                return val

    return None


def _resolve_tool(
    tool_name: str | None,
    proton_version: str | None,
    proton_tools: dict[str, ProtonTool],
    evidence: list[str],
    warnings: list[str],
) -> tuple[str | None, bool]:
    """Return ``(resolved_name, is_installed)`` for the given tool hint."""
    if tool_name:
        if tool_name in proton_tools:
            evidence.append(f"Tool installed locally: {proton_tools[tool_name].install_path}")
            return tool_name, True
        # Fuzzy case-insensitive substring match
        for key in proton_tools:
            if tool_name.lower() in key.lower() or key.lower() in tool_name.lower():
                evidence.append(f"Tool matched (fuzzy) to installed: {key}")
                return key, True
        warnings.append(f"Compat tool {tool_name!r} not found in local installations")
        return tool_name, False

    # No tool name — try to infer from prefix version string
    if proton_version:
        for key, pt in proton_tools.items():
            if pt.version and proton_version.startswith(pt.version):
                evidence.append(f"Tool inferred from prefix version match: {key}")
                return key, True

    return None, False


def _compute_confidence(
    *,
    has_explicit_tool: bool,
    prefix_exists: bool,
    tool_installed: bool,
    has_version_file: bool,
) -> Confidence:
    score = (
        (3 if has_explicit_tool else 0)
        + (2 if prefix_exists else 0)
        + (2 if tool_installed else 0)
        + (1 if has_version_file else 0)
    )
    if score >= 7:
        return Confidence.HIGH
    if score >= 4:
        return Confidence.MEDIUM
    if score >= 1:
        return Confidence.LOW
    return Confidence.UNKNOWN
