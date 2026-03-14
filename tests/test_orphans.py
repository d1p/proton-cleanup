"""Tests for orphaned prefix and unused tool detection."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from proton_manager.model import Confidence, GameEntry, GameKind
from proton_manager.scan.orphans import scan_orphans
from proton_manager.scan.proton_tools import discover_proton_tools
from proton_manager.scan.steam_games import scan_steam_games
from proton_manager.scan.libraries import enumerate_library_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _steam_entry(app_id: str) -> GameEntry:
    return GameEntry(
        app_id=app_id,
        name=f"Game {app_id}",
        kind=GameKind.STEAM,
        proton_tool="Proton-8-Test",
        proton_version=None,
        prefix_path=None,
        prefix_exists=False,
        tool_installed=True,
        confidence=Confidence.HIGH,
    )


# ---------------------------------------------------------------------------
# Orphaned prefix detection
# ---------------------------------------------------------------------------

def test_orphaned_prefix_detected(tmp_path):
    steamapps = tmp_path / "steamapps"
    compat = steamapps / "compatdata"

    # Known game (has manifest)
    (steamapps).mkdir(parents=True)
    (compat / "1111" / "pfx" / "drive_c").mkdir(parents=True)
    (compat / "1111" / "version").write_text("8.0-5\n")

    # Orphaned — no manifest, no shortcut
    (compat / "9999" / "pfx" / "drive_c").mkdir(parents=True)
    (compat / "9999" / "version").write_text("9.0-1\n")

    known = [_steam_entry("1111")]
    results = scan_orphans([steamapps], known, {})

    orphans = [e for e in results if e.kind == GameKind.ORPHAN]
    assert len(orphans) == 1
    assert orphans[0].app_id == "9999"
    assert orphans[0].proton_version == "9.0-1"
    assert orphans[0].prefix_exists is True
    assert orphans[0].confidence == Confidence.UNKNOWN
    assert any("No game manifest" in w for w in orphans[0].warnings)


def test_orphaned_prefix_no_pfx(tmp_path):
    """A compatdata dir without pfx/ is still reported (prefix never initialised)."""
    steamapps = tmp_path / "steamapps"
    compat = steamapps / "compatdata" / "7777"
    compat.mkdir(parents=True)
    # No pfx/ subdirectory

    results = scan_orphans([steamapps], [], {})
    orphans = [e for e in results if e.kind == GameKind.ORPHAN]
    assert len(orphans) == 1
    assert orphans[0].prefix_exists is False


def test_no_orphans_when_all_known(tmp_path):
    steamapps = tmp_path / "steamapps"
    compat = steamapps / "compatdata" / "1234" / "pfx" / "drive_c"
    compat.mkdir(parents=True)

    known = [_steam_entry("1234")]
    results = scan_orphans([steamapps], known, {})
    assert not any(e.kind == GameKind.ORPHAN for e in results)


def test_orphan_config_info_inference(tmp_path):
    """config_info present → proton_tool inferred for orphan."""
    steamapps = tmp_path / "steamapps"
    compat = steamapps / "compatdata" / "5555"
    (compat / "pfx" / "drive_c").mkdir(parents=True)
    ci = (
        b"9.0-1\n"
        b"/home/deck/.local/share/Steam/steamapps/common/Proton 9.0/files/share/fonts/\n"
    )
    (compat / "config_info").write_bytes(ci)

    results = scan_orphans([steamapps], [], {})
    orphans = [e for e in results if e.kind == GameKind.ORPHAN]
    assert orphans[0].proton_tool == "Proton 9.0"


# ---------------------------------------------------------------------------
# Unused tool detection
# ---------------------------------------------------------------------------

def test_unused_tool_detected(tmp_path):
    from proton_manager.model import ProtonTool
    tools = {
        "GE-Proton10-25": ProtonTool("GE-Proton10-25", "10.25", tmp_path / "tool1"),
        "UnusedTool":     ProtonTool("UnusedTool", "1.0",   tmp_path / "tool2"),
    }
    # Make tool directories exist
    (tmp_path / "tool1").mkdir()
    (tmp_path / "tool2").mkdir()

    known = [
        GameEntry(
            app_id="100", name="My Game", kind=GameKind.STEAM,
            proton_tool="GE-Proton10-25", proton_version=None,
            prefix_path=None, prefix_exists=False, tool_installed=True,
            confidence=Confidence.HIGH,
        )
    ]
    results = scan_orphans([], known, tools)
    unused = [e for e in results if e.kind == GameKind.UNUSED_TOOL]
    assert len(unused) == 1
    assert unused[0].proton_tool == "UnusedTool"
    assert unused[0].tool_installed is True
    assert "unused" in unused[0].warnings[0].lower()


def test_all_tools_used_no_unused(tmp_path):
    from proton_manager.model import ProtonTool
    tools = {"GE-Proton10-25": ProtonTool("GE-Proton10-25", "10.25", tmp_path / "t")}
    (tmp_path / "t").mkdir()
    known = [
        GameEntry(
            app_id="1", name="G", kind=GameKind.STEAM,
            proton_tool="GE-Proton10-25", proton_version=None,
            prefix_path=None, prefix_exists=False, tool_installed=True,
            confidence=Confidence.HIGH,
        )
    ]
    results = scan_orphans([], known, tools)
    assert not any(e.kind == GameKind.UNUSED_TOOL for e in results)


def test_no_tools_no_unused():
    results = scan_orphans([], [], {})
    assert results == []


# ---------------------------------------------------------------------------
# Full pipeline integration (fixture-based)
# ---------------------------------------------------------------------------

def test_full_scan_includes_orphans(steam_root):
    """End-to-end: the steam_root fixture has no orphans, but adding one surfaces it."""
    steamapps = steam_root / "steamapps"
    # Add an orphaned prefix
    orphan_dir = steamapps / "compatdata" / "88888" / "pfx" / "drive_c"
    orphan_dir.mkdir(parents=True)

    tools = discover_proton_tools(steam_root)
    known = scan_steam_games(steamapps, tools)

    from proton_manager.scan.shortcuts import scan_shortcuts
    from proton_manager.scan.config import load_compat_tool_mapping
    mapping = load_compat_tool_mapping(steam_root)
    known += scan_shortcuts(steam_root, [steamapps], tools, mapping)

    orphans = scan_orphans([steamapps], known, tools)
    orphan_ids = [e.app_id for e in orphans if e.kind == GameKind.ORPHAN]
    assert "88888" in orphan_ids


# ---------------------------------------------------------------------------
# CLI --hide-orphans flag
# ---------------------------------------------------------------------------

def test_cli_json_includes_orphans_by_default(steam_root, capsys):
    # Add orphan prefix
    orphan_dir = steam_root / "steamapps" / "compatdata" / "77777" / "pfx" / "drive_c"
    orphan_dir.mkdir(parents=True)

    with patch("sys.argv", ["proton-manager", "--json", f"--steam-root={steam_root}"]):
        from proton_manager.cli import main
        main()

    data = json.loads(capsys.readouterr().out)
    kinds = {row["kind"] for row in data}
    assert "Orphan" in kinds


def test_cli_json_hide_orphans(steam_root, capsys):
    orphan_dir = steam_root / "steamapps" / "compatdata" / "77777" / "pfx" / "drive_c"
    orphan_dir.mkdir(parents=True)

    with patch(
        "sys.argv",
        ["proton-manager", "--json", "--hide-orphans", f"--steam-root={steam_root}"],
    ):
        from proton_manager.cli import main
        main()

    data = json.loads(capsys.readouterr().out)
    assert not any(row["kind"] in ("Orphan", "Unused Tool") for row in data)
