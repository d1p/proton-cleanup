"""Scan for Proton environments that have no linked game.

Two categories are detected:

* **Orphaned prefix** — a ``compatdata/<app_id>/`` directory exists on disk
  but no ``appmanifest_<app_id>.acf`` or shortcut entry corresponds to it.
  Happens when a game is uninstalled without Steam cleaning up its prefix.

* **Unused tool** — a Proton compatibility tool installed under
  ``compatibilitytools.d/`` that is referenced by no known game entry.
"""

from __future__ import annotations

from pathlib import Path

from proton_manager.model import Confidence, GameEntry, GameKind, ProtonTool


def scan_orphans(
    steamapps_paths: list[Path],
    known_entries: list[GameEntry],
    proton_tools: dict[str, ProtonTool],
) -> list[GameEntry]:
    """Return unlinked environment entries.

    Parameters
    ----------
    steamapps_paths:
        All ``steamapps`` directories already enumerated for this Steam root.
    known_entries:
        All :class:`GameEntry` objects produced by the Steam-game and shortcut
        scanners.  Used to build the set of already-accounted-for IDs.
    proton_tools:
        Installed tools map from :func:`discover_proton_tools`.
    """
    results: list[GameEntry] = []
    results.extend(_orphaned_prefixes(steamapps_paths, known_entries))
    results.extend(_unused_tools(proton_tools, known_entries))
    return results


# ---------------------------------------------------------------------------
# Orphaned prefixes
# ---------------------------------------------------------------------------


def _orphaned_prefixes(
    steamapps_paths: list[Path],
    known_entries: list[GameEntry],
) -> list[GameEntry]:
    known_ids: set[str] = {e.app_id for e in known_entries}

    results: list[GameEntry] = []
    seen_prefix_dirs: set[Path] = set()

    for steamapps in steamapps_paths:
        compat_root = steamapps / "compatdata"
        if not compat_root.is_dir():
            continue

        for prefix_dir in sorted(compat_root.iterdir()):
            if not prefix_dir.is_dir():
                continue

            real = prefix_dir.resolve()
            if real in seen_prefix_dirs:
                continue
            seen_prefix_dirs.add(real)

            app_id = prefix_dir.name
            if app_id in known_ids:
                continue  # already accounted for

            evidence: list[str] = [f"Compatdata directory: {prefix_dir}"]
            warnings: list[str] = ["No game manifest or shortcut found for this App ID"]

            pfx_path = prefix_dir / "pfx"
            prefix_exists = pfx_path.is_dir()
            if prefix_exists:
                evidence.append(f"Wine prefix exists: {pfx_path}")
            else:
                evidence.append("No pfx/ sub-directory (prefix not yet initialised)")

            proton_version: str | None = None
            ver_file = prefix_dir / "version"
            if ver_file.exists():
                try:
                    proton_version = ver_file.read_text(encoding="utf-8").strip().splitlines()[0]
                    evidence.append(f"Prefix version file: {proton_version}")
                except Exception:
                    pass

            # Best-effort tool inference from config_info
            proton_tool: str | None = None
            config_info = prefix_dir / "config_info"
            if config_info.exists():
                try:
                    import re as _re

                    ci_str = config_info.read_bytes().decode("utf-8", errors="replace")
                    m = _re.search(
                        r"steamapps/common/((?:Proton|GE-Proton)[^\n/]+?)(?:/|\n)",
                        ci_str,
                    )
                    if m:
                        proton_tool = m.group(1).strip()
                        evidence.append(f"Proton tool inferred from config_info: {proton_tool!r}")
                except Exception:
                    pass

            results.append(
                GameEntry(
                    app_id=app_id,
                    name=f"[Orphaned Prefix]  App ID {app_id}",
                    kind=GameKind.ORPHAN,
                    proton_tool=proton_tool,
                    proton_version=proton_version,
                    prefix_path=pfx_path if prefix_exists else prefix_dir,
                    prefix_exists=prefix_exists,
                    tool_installed=False,
                    confidence=Confidence.UNKNOWN,
                    evidence=evidence,
                    warnings=warnings,
                )
            )

    return results


# ---------------------------------------------------------------------------
# Unused tools
# ---------------------------------------------------------------------------


def _unused_tools(
    proton_tools: dict[str, ProtonTool],
    known_entries: list[GameEntry],
) -> list[GameEntry]:
    used_tools: set[str] = {
        e.proton_tool
        for e in known_entries
        if e.proton_tool is not None and e.kind != GameKind.ORPHAN
    }

    results: list[GameEntry] = []
    for tool_name, tool in proton_tools.items():
        if tool_name in used_tools:
            continue
        # Also skip partial fuzzy matches already covered
        if any(
            tool_name.lower() in ut.lower() or ut.lower() in tool_name.lower() for ut in used_tools
        ):
            continue

        results.append(
            GameEntry(
                app_id=f"tool:{tool_name}",
                name=f"[Unused Tool]  {tool_name}",
                kind=GameKind.UNUSED_TOOL,
                proton_tool=tool_name,
                proton_version=tool.version or None,
                prefix_path=tool.install_path,
                prefix_exists=tool.install_path.is_dir(),
                tool_installed=True,
                confidence=Confidence.UNKNOWN,
                evidence=[
                    f"Tool installed at: {tool.install_path}",
                    f"Version: {tool.version}",
                    "No game entry currently references this tool",
                ],
                warnings=["Tool is installed but unused"],
            )
        )

    return results
