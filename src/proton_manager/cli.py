"""CLI entry point for Proton Cleanup."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from proton_manager import __version__
from proton_manager.model import Confidence


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="proton-cleanup",
        description=(
            "Scan all Proton environments and display which game uses which "
            "compatibility tool. Defaults to an interactive TUI; use --json "
            "for machine-readable output."
        ),
    )
    p.add_argument(
        "--steam-root",
        metavar="PATH",
        type=Path,
        default=None,
        help="Override auto-detected Steam root directory.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print JSON to stdout and exit (no TUI).",
    )
    p.add_argument(
        "--only-steam",
        action="store_true",
        help="Show only Steam library games (exclude shortcuts).",
    )
    p.add_argument(
        "--only-shortcuts",
        action="store_true",
        help="Show only non-Steam shortcuts (exclude library games).",
    )
    p.add_argument(
        "--min-confidence",
        metavar="LEVEL",
        choices=[c.value for c in Confidence],
        default=None,
        help="Hide entries with confidence below this level (HIGH/MEDIUM/LOW/UNKNOWN).",
    )
    p.add_argument(
        "--hide-orphans",
        action="store_true",
        help="Hide orphaned prefixes and unused Proton tools from output.",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def _run_scan(steam_root_override: Path | None) -> tuple[list, list[str]]:
    """Execute the full scan pipeline and return (entries, global_warnings)."""
    from proton_manager.scan.steam_roots import discover_steam_roots
    from proton_manager.scan.libraries import enumerate_library_paths
    from proton_manager.scan.proton_tools import discover_proton_tools
    from proton_manager.scan.config import load_compat_tool_mapping
    from proton_manager.scan.steam_games import scan_steam_games
    from proton_manager.scan.shortcuts import scan_shortcuts
    from proton_manager.scan.orphans import scan_orphans

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
    args = _build_parser().parse_args()

    entries, global_warnings = _run_scan(args.steam_root)

    # Apply CLI-level filters for JSON mode (TUI applies them interactively)
    filtered = entries
    if args.only_steam:
        from proton_manager.model import GameKind
        filtered = [e for e in filtered if e.kind == GameKind.STEAM]
    if args.only_shortcuts:
        from proton_manager.model import GameKind
        filtered = [e for e in filtered if e.kind == GameKind.SHORTCUT]
    if args.hide_orphans:
        from proton_manager.model import GameKind
        filtered = [e for e in filtered if e.kind not in (GameKind.ORPHAN, GameKind.UNUSED_TOOL)]
    if args.min_confidence:
        from proton_manager.model import Confidence
        order = [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW, Confidence.UNKNOWN]
        threshold = order.index(Confidence(args.min_confidence))
        filtered = [e for e in filtered if order.index(e.confidence) <= threshold]

    if global_warnings:
        for w in global_warnings:
            print(f"warning: {w}", file=sys.stderr)

    if args.json:
        from proton_manager.output import entries_to_json
        print(entries_to_json(filtered))
        return

    # Launch TUI
    from proton_manager.model import Confidence as Conf
    from proton_manager.tui.app import ProtonManagerApp

    min_conf = Conf(args.min_confidence) if args.min_confidence else None

    def rescan() -> list:
        new_entries, new_warnings = _run_scan(args.steam_root)
        for w in new_warnings:
            print(f"warning: {w}", file=sys.stderr)
        return new_entries

    app = ProtonManagerApp(
        entries=entries,
        rescan_fn=rescan,
        min_confidence=min_conf,
        only_steam=args.only_steam,
        only_shortcuts=args.only_shortcuts,
        hide_orphans=args.hide_orphans,
    )
    app.run()


if __name__ == "__main__":
    main()
