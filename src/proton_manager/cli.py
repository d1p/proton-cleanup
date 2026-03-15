"""Entry point for Proton Cleanup — launches the PySide6 GUI."""

from __future__ import annotations

import sys
from pathlib import Path



def _run_scan(steam_root_override: Path | None) -> tuple[list, list[str]]:
    """Execute the full scan pipeline and return (entries, global_warnings)."""
    from proton_manager.scan.config import load_compat_tool_mapping
    from proton_manager.scan.libraries import enumerate_library_paths
    from proton_manager.scan.orphans import scan_orphans
    from proton_manager.scan.proton_tools import discover_proton_tools
    from proton_manager.scan.shortcuts import scan_shortcuts
    from proton_manager.scan.steam_games import scan_steam_games
    from proton_manager.scan.steam_roots import discover_steam_roots

    global_warnings: list[str] = []

    # 1. Discover Steam roots
    try:
        roots = discover_steam_roots(override=steam_root_override)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not roots:
        global_warnings.append(
            "No Steam installation found. Use --steam-root to specify one manually."
        )
        return [], global_warnings

    all_entries = []

    for root in roots:
        # 2. Libraries
        steamapps_paths = enumerate_library_paths(root)

        # 3. Proton tools
        proton_tools = discover_proton_tools(root)

        # 4. Per-game compat tool mapping from config.vdf
        compat_mapping = load_compat_tool_mapping(root)

        # 5. Steam games
        for steamapps in steamapps_paths:
            entries = scan_steam_games(steamapps, proton_tools, compat_mapping)
            all_entries.extend(entries)

        # 6. Non-Steam shortcuts
        shortcut_entries = scan_shortcuts(root, steamapps_paths, proton_tools, compat_mapping)
        all_entries.extend(shortcut_entries)

        # 7. Orphaned prefixes + unused tools (uses all entries so far per root)
        orphan_entries = scan_orphans(steamapps_paths, all_entries, proton_tools)
        all_entries.extend(orphan_entries)

    # Deduplicate by (app_id, kind) — in case multiple roots expose the same game
    seen: set[tuple] = set()
    deduped = []
    for e in all_entries:
        key = (e.app_id, e.kind)
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    return deduped, global_warnings


def main() -> None:
    """Launch the Proton Cleanup PySide6 GUI."""
    from proton_manager.gui.app import create_application
    from proton_manager.gui.main_window import MainWindow

    app = create_application()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
