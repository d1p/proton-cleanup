"""Parse binary shortcuts.vdf and map non-Steam games to Proton environments."""
from __future__ import annotations

import binascii
from pathlib import Path

import vdf

from proton_manager.model import Confidence, GameEntry, GameKind, ProtonTool
from proton_manager.scan.libraries import compatdata_root


def scan_shortcuts(
    steam_root: Path,
    all_steamapps: list[Path],
    proton_tools: dict[str, ProtonTool],
    compat_tool_mapping: dict[str, str] | None = None,
) -> list[GameEntry]:
    """Return a :class:`GameEntry` for every non-Steam shortcut found in any user dir."""
    mapping = compat_tool_mapping or {}
    entries: list[GameEntry] = []

    userdata_dir = steam_root / "userdata"
    if not userdata_dir.is_dir():
        return entries

    # Collect Steam app IDs already accounted for by scan_steam_games
    known_ids: set[str] = {
        m.stem.replace("appmanifest_", "")
        for steamapps in all_steamapps
        for m in steamapps.glob("appmanifest_*.acf")
    }

    # Determine compatdata root (use first steamapps / steam root)
    compat_roots: list[Path] = [compatdata_root(sa) for sa in all_steamapps]
    if not compat_roots:
        compat_roots = [steam_root / "steamapps" / "compatdata"]

    for user_dir in sorted(userdata_dir.iterdir()):
        if not user_dir.is_dir():
            continue
        shortcuts_path = user_dir / "config" / "shortcuts.vdf"
        if not shortcuts_path.exists():
            continue

        try:
            raw = shortcuts_path.read_bytes()
            data = vdf.binary_loads(raw)
        except Exception as exc:
            entries.append(
                GameEntry(
                    app_id="?",
                    name=f"<shortcuts.vdf parse error — user {user_dir.name}>",
                    kind=GameKind.SHORTCUT,
                    proton_tool=None,
                    proton_version=None,
                    prefix_path=None,
                    prefix_exists=False,
                    tool_installed=False,
                    confidence=Confidence.UNKNOWN,
                    evidence=[],
                    warnings=[f"Failed to parse shortcuts.vdf: {exc}"],
                )
            )
            continue

        shortcuts_map = data.get("shortcuts") or {}
        for idx, shortcut in shortcuts_map.items():
            if not isinstance(shortcut, dict):
                continue
            entry = _parse_shortcut(
                shortcut, idx, known_ids, compat_roots, proton_tools, mapping
            )
            if entry is not None:
                entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _key(d: dict, *names: str) -> object:
    """Case-insensitive multi-name key lookup on a dict."""
    lower = {k.lower(): v for k, v in d.items()}
    for name in names:
        v = lower.get(name.lower())
        if v is not None:
            return v
    return None


def _parse_shortcut(
    shortcut: dict,
    idx: str,
    known_ids: set[str],
    compat_roots: list[Path],
    proton_tools: dict[str, ProtonTool],
    compat_tool_mapping: dict[str, str] | None = None,
) -> GameEntry | None:
    name = str(_key(shortcut, "AppName", "appname") or f"Shortcut #{idx}")
    exe = str(_key(shortcut, "Exe", "exe") or "").strip('"')
    launch_opts = str(_key(shortcut, "LaunchOptions", "launchoptions") or "")

    evidence: list[str] = []
    warnings: list[str] = []

    # --- App ID resolution ---
    # Newer Steam stores the computed AppId directly in the binary VDF
    raw_app_id = _key(shortcut, "AppId", "appid")
    if raw_app_id is not None:
        app_id = str(int(raw_app_id) & 0xFFFFFFFF)
        evidence.append(f"AppId from shortcuts.vdf: {app_id}")
    else:
        # Compute CRC-based pseudo-ID (Steam's formula)
        app_id = _compute_shortcut_id(exe, name)
        evidence.append(f"AppId computed from exe+name CRC: {app_id}")

    # Skip if this ID matches a known real Steam game
    if app_id in known_ids:
        return None

    # --- Compat tool detection ---
    # 1. config.vdf CompatToolMapping (authoritative)
    mapping = compat_tool_mapping or {}
    tool_name = mapping.get(app_id)
    if tool_name:
        evidence.append(f"Compat-tool from config.vdf CompatToolMapping: {tool_name!r}")
    else:
        # 2. Field inside shortcuts.vdf entry
        tool_name = str(_key(shortcut, "CompatTool", "compattool") or "").strip() or None
        if not tool_name and launch_opts:
            for part in launch_opts.split():
                if part.startswith("PROTON_VERSION="):
                    tool_name = part.split("=", 1)[1]
                    evidence.append(f"Tool found in LaunchOptions: {tool_name!r}")
                    break
        if tool_name:
            evidence.append(f"Compat-tool from shortcuts.vdf entry: {tool_name!r}")

    # --- Prefix / compatdata ---
    prefix_dir, pfx_path, prefix_exists = _find_prefix(app_id, compat_roots)

    if prefix_exists:
        evidence.append(f"Wine prefix exists: {pfx_path}")
    elif prefix_dir is not None:
        evidence.append(f"Compatdata dir present (no pfx/ yet): {prefix_dir}")
    else:
        warnings.append("No compatdata directory found for this shortcut")

    # Skip shortcuts with no Proton data AND no explicit tool (native/unconfigured)
    if not tool_name and not prefix_exists and prefix_dir is None:
        return None

    # --- Prefix version file ---
    proton_version: str | None = None
    if prefix_dir is not None:
        ver_file = prefix_dir / "version"
        if ver_file.exists():
            try:
                proton_version = ver_file.read_text(encoding="utf-8").strip().splitlines()[0]
                evidence.append(f"Prefix version file: {proton_version}")
            except Exception:
                warnings.append("Could not read prefix version file")

    # --- Resolve tool ---
    resolved_tool, tool_installed = _resolve_tool(
        tool_name, proton_version, proton_tools, evidence, warnings
    )

    confidence = _compute_confidence(
        has_explicit_tool=bool(tool_name),
        prefix_exists=prefix_exists,
        tool_installed=tool_installed,
        has_version_file=proton_version is not None,
        is_shortcut=True,
    )

    return GameEntry(
        app_id=app_id,
        name=name,
        kind=GameKind.SHORTCUT,
        proton_tool=resolved_tool,
        proton_version=proton_version,
        prefix_path=pfx_path if prefix_exists else prefix_dir,
        prefix_exists=prefix_exists,
        tool_installed=tool_installed,
        confidence=confidence,
        evidence=evidence,
        warnings=warnings,
    )


def _compute_shortcut_id(exe: str, name: str) -> str:
    """Compute Steam's CRC32-based shortcut App ID from exe path + app name."""
    key = exe + name
    crc = binascii.crc32(key.encode("utf-8")) & 0xFFFFFFFF
    return str(crc | 0x80000000)


def _find_prefix(app_id: str, compat_roots: list[Path]) -> tuple[Path | None, Path | None, bool]:
    """Search all compat_roots for a compatdata/<app_id> directory."""
    for root in compat_roots:
        prefix_dir = root / app_id
        pfx_path = prefix_dir / "pfx"
        if pfx_path.is_dir():
            return prefix_dir, pfx_path, True
        if prefix_dir.is_dir():
            return prefix_dir, None, False
    return None, None, False


def _resolve_tool(
    tool_name: str | None,
    proton_version: str | None,
    proton_tools: dict[str, ProtonTool],
    evidence: list[str],
    warnings: list[str],
) -> tuple[str | None, bool]:
    if tool_name:
        if tool_name in proton_tools:
            evidence.append(f"Tool installed locally: {proton_tools[tool_name].install_path}")
            return tool_name, True
        for key in proton_tools:
            if tool_name.lower() in key.lower() or key.lower() in tool_name.lower():
                evidence.append(f"Tool matched (fuzzy) to installed: {key}")
                return key, True
        warnings.append(f"Compat tool {tool_name!r} not found in local installations")
        return tool_name, False

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
    is_shortcut: bool,
) -> Confidence:
    score = (
        (3 if has_explicit_tool else 0)
        + (2 if prefix_exists else 0)
        + (2 if tool_installed else 0)
        + (1 if has_version_file else 0)
    )
    # Shortcuts start with a slight penalty: same score = one level lower
    if is_shortcut:
        if score >= 8:
            return Confidence.HIGH
        if score >= 5:
            return Confidence.MEDIUM
        if score >= 1:
            return Confidence.LOW
        return Confidence.UNKNOWN

    if score >= 7:
        return Confidence.HIGH
    if score >= 4:
        return Confidence.MEDIUM
    if score >= 1:
        return Confidence.LOW
    return Confidence.UNKNOWN
