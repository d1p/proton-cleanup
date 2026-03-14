"""Tests for the scan layer: roots, libraries, tools, Steam games, shortcuts."""

from __future__ import annotations

import pytest

from proton_manager.model import Confidence, GameKind
from proton_manager.scan.libraries import collect_app_manifests, enumerate_library_paths
from proton_manager.scan.proton_tools import discover_proton_tools
from proton_manager.scan.shortcuts import _compute_shortcut_id, scan_shortcuts
from proton_manager.scan.steam_games import scan_steam_games
from proton_manager.scan.steam_roots import discover_steam_roots

# ---------------------------------------------------------------------------
# steam_roots
# ---------------------------------------------------------------------------


def test_discover_override_valid(tmp_path):
    result = discover_steam_roots(override=tmp_path)
    assert result == [tmp_path]


def test_discover_override_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_steam_roots(override=tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# libraries
# ---------------------------------------------------------------------------


def test_enumerate_library_paths_primary_only(steam_root):
    paths = enumerate_library_paths(steam_root)
    assert len(paths) == 1
    assert paths[0] == steam_root / "steamapps"


def test_enumerate_library_paths_extra(tmp_path):
    root = tmp_path / "steam"
    primary = root / "steamapps"
    primary.mkdir(parents=True)

    extra = tmp_path / "extra_lib" / "steamapps"
    extra.mkdir(parents=True)

    lf_content = f'"libraryfolders"\n{{\n\t"1"\n\t{{\n\t\t"path"\t\t"{extra.parent}"\n\t}}\n}}\n'
    (primary / "libraryfolders.vdf").write_text(lf_content, encoding="utf-8")

    paths = enumerate_library_paths(root)
    assert extra in paths


def test_collect_app_manifests(steam_root):
    manifests = collect_app_manifests(steam_root / "steamapps")
    names = [m.name for m in manifests]
    assert "appmanifest_1234.acf" in names


# ---------------------------------------------------------------------------
# proton_tools
# ---------------------------------------------------------------------------


def test_discover_proton_tools(steam_root):
    tools = discover_proton_tools(steam_root)
    assert "Proton-8-Test" in tools
    tool = tools["Proton-8-Test"]
    assert tool.version == "8.0-3"
    assert tool.install_path.is_dir()


def test_discover_proton_tools_no_tools_in_root(tmp_path):
    """An empty steam root contributes no tools (system-wide tools may still appear)."""
    root = tmp_path / "steam"
    root.mkdir()
    tools = discover_proton_tools(root)
    # No tool should have an install_path under our fake root
    for tool in tools.values():
        assert not str(tool.install_path).startswith(str(root))


# ---------------------------------------------------------------------------
# steam_games
# ---------------------------------------------------------------------------


def test_scan_steam_games_basic(steam_root):
    tools = discover_proton_tools(steam_root)
    entries = scan_steam_games(steam_root / "steamapps", tools)

    assert len(entries) == 1
    e = entries[0]
    assert e.app_id == "1234"
    assert e.name == "Test Game"
    assert e.kind == GameKind.STEAM
    assert e.proton_tool == "Proton-8-Test"
    assert e.prefix_exists is True
    assert e.tool_installed is True
    assert e.confidence == Confidence.HIGH


def test_scan_steam_games_no_tools(steam_root):
    # Without tools dict, game should still appear but with lower confidence
    entries = scan_steam_games(steam_root / "steamapps", {})
    assert len(entries) == 1
    e = entries[0]
    assert e.confidence in (Confidence.MEDIUM, Confidence.LOW)
    assert e.tool_installed is False


def test_scan_steam_games_parse_error(tmp_path):
    steamapps = tmp_path / "steamapps"
    steamapps.mkdir()
    compat = steamapps / "compatdata" / "9999"
    compat.mkdir(parents=True)
    # Write a broken manifest (vdf returns {} on malformed content — no hard crash)
    bad = steamapps / "appmanifest_9999.acf"
    bad.write_text("{{{{broken VDF", encoding="utf-8")

    entries = scan_steam_games(steamapps, {})
    # Broken manifests still produce an entry (with empty AppState → UNKNOWN confidence)
    assert any(e.app_id == "9999" for e in entries)
    assert all(e.confidence == Confidence.UNKNOWN for e in entries)


def test_scan_skips_native_games(tmp_path):
    steamapps = tmp_path / "steamapps"
    steamapps.mkdir()
    # A game with no compatdata at all and no compat tool override → skip
    from tests.conftest import make_acf

    (steamapps / "appmanifest_777.acf").write_text(
        make_acf(777, "Native Game"),  # no compat_tool arg
        encoding="utf-8",
    )
    entries = scan_steam_games(steamapps, {})
    assert entries == []


# ---------------------------------------------------------------------------
# shortcuts
# ---------------------------------------------------------------------------


def test_compute_shortcut_id_deterministic():
    id1 = _compute_shortcut_id("/usr/bin/game", "My Game")
    id2 = _compute_shortcut_id("/usr/bin/game", "My Game")
    assert id1 == id2
    assert id1.isdigit()


def test_scan_shortcuts_basic(steam_root):
    tools = discover_proton_tools(steam_root)
    steamapps = [steam_root / "steamapps"]
    entries = scan_shortcuts(steam_root, steamapps, tools)

    assert len(entries) == 1
    e = entries[0]
    assert e.name == "My External Game"
    assert e.kind == GameKind.SHORTCUT
    assert e.proton_tool == "Proton-8-Test"
    assert e.prefix_exists is True


def test_scan_shortcuts_no_userdata(tmp_path):
    root = tmp_path / "steam"
    root.mkdir()
    entries = scan_shortcuts(root, [], {})
    assert entries == []


def test_scan_shortcuts_corrupt_vdf(tmp_path):
    root = tmp_path / "steam"
    user_dir = root / "userdata" / "12345" / "config"
    user_dir.mkdir(parents=True)
    (user_dir / "shortcuts.vdf").write_bytes(b"\xff\xfe corrupt binary data !!")

    entries = scan_shortcuts(root, [], {})
    assert len(entries) == 1
    assert "parse error" in entries[0].name.lower()
    assert entries[0].confidence == Confidence.UNKNOWN


# ---------------------------------------------------------------------------
# Flatpak root scenario
# ---------------------------------------------------------------------------


def test_flatpak_root_scan(flatpak_steam_root):
    tools = discover_proton_tools(flatpak_steam_root)
    steamapps = enumerate_library_paths(flatpak_steam_root)
    entries = []
    for sa in steamapps:
        entries.extend(scan_steam_games(sa, tools))

    assert len(entries) == 1
    e = entries[0]
    assert e.app_id == "5678"
    assert e.prefix_exists is False  # pfx/ not created yet
    assert e.confidence in (Confidence.MEDIUM, Confidence.LOW, Confidence.HIGH)
