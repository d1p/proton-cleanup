"""Tests for framework-agnostic delete helpers in proton_manager.delete."""

from __future__ import annotations

from pathlib import Path

from proton_manager.delete import delete_entry, deleteable_path, entry_timestamps
from proton_manager.model import Confidence, GameEntry, GameKind

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_entry(
    kind: GameKind = GameKind.ORPHAN,
    prefix: Path | None = None,
    app_id: str = "9999",
    name: str = "Test Entry",
) -> GameEntry:
    return GameEntry(
        app_id=app_id,
        name=name,
        kind=kind,
        proton_tool=None,
        proton_version=None,
        prefix_path=prefix,
        prefix_exists=prefix is not None,
        tool_installed=False,
        confidence=Confidence.UNKNOWN,
    )


def _steam_entry(tmp_path: Path, app_id: str = "100") -> GameEntry:
    pfx = tmp_path / "compatdata" / app_id / "pfx"
    pfx.mkdir(parents=True)
    return GameEntry(
        app_id=app_id,
        name="My Steam Game",
        kind=GameKind.STEAM,
        proton_tool="Proton-8",
        proton_version="8.0-5",
        prefix_path=pfx,
        prefix_exists=True,
        tool_installed=True,
        confidence=Confidence.HIGH,
    )


# ---------------------------------------------------------------------------
# deleteable_path
# ---------------------------------------------------------------------------


def test_deleteable_path_pfx_subdir(tmp_path: Path) -> None:
    pfx = tmp_path / "compatdata" / "1234" / "pfx"
    pfx.mkdir(parents=True)
    entry = _make_entry(GameKind.STEAM, pfx)
    assert deleteable_path(entry) == pfx.parent  # compatdata/1234


def test_deleteable_path_orphan_no_pfx(tmp_path: Path) -> None:
    compat = tmp_path / "compatdata" / "9999"
    compat.mkdir(parents=True)
    entry = _make_entry(GameKind.ORPHAN, compat)
    assert deleteable_path(entry) == compat


def test_deleteable_path_unused_tool(tmp_path: Path) -> None:
    tool = tmp_path / "compatibilitytools.d" / "GE-Proton10"
    tool.mkdir(parents=True)
    entry = _make_entry(GameKind.UNUSED_TOOL, tool)
    assert deleteable_path(entry) == tool


def test_deleteable_path_none() -> None:
    entry = _make_entry(prefix=None)
    assert deleteable_path(entry) is None


# ---------------------------------------------------------------------------
# entry_timestamps
# ---------------------------------------------------------------------------


def test_entry_timestamps_no_path() -> None:
    entry = _make_entry(prefix=None)
    assert entry_timestamps(entry) == ("—", "—")


def test_entry_timestamps_missing_dir(tmp_path: Path) -> None:
    gone = tmp_path / "compatdata" / "0000"
    entry = _make_entry(GameKind.ORPHAN, gone)
    assert entry_timestamps(entry) == ("—", "—")


def test_entry_timestamps_returns_strings(tmp_path: Path) -> None:
    compat = tmp_path / "compatdata" / "1234"
    compat.mkdir(parents=True)
    (compat / "version").write_text("8.0-5\n")
    entry = _make_entry(GameKind.ORPHAN, compat)
    created, modified = entry_timestamps(entry)
    assert created != "—"
    assert modified != "—"
    assert len(created) == 17
    assert "-" in created


# ---------------------------------------------------------------------------
# delete_entry
# ---------------------------------------------------------------------------


def test_delete_entry_removes_directory(tmp_path: Path) -> None:
    compat = tmp_path / "compatdata" / "9999"
    compat.mkdir(parents=True)
    (compat / "pfx").mkdir()
    (compat / "version").write_text("8.0-5\n")
    entry = _make_entry(GameKind.ORPHAN, compat)

    ok, msg = delete_entry(entry)

    assert ok, msg
    assert not compat.exists()


def test_delete_entry_already_gone(tmp_path: Path) -> None:
    compat = tmp_path / "compatdata" / "9999"
    entry = _make_entry(GameKind.ORPHAN, compat)
    ok, _msg = delete_entry(entry)
    assert ok


def test_delete_entry_no_path() -> None:
    entry = _make_entry(prefix=None)
    ok, _msg = delete_entry(entry)
    assert not ok


def test_delete_entry_safety_check_fails(tmp_path: Path) -> None:
    """Refuse to delete a directory not parented by a known Steam sub-dir."""
    bad = tmp_path / "random_folder" / "9999"
    bad.mkdir(parents=True)
    entry = _make_entry(GameKind.ORPHAN, bad)
    ok, msg = delete_entry(entry)
    assert not ok
    assert "Safety check failed" in msg


def test_delete_entry_removes_tool(tmp_path: Path) -> None:
    tool = tmp_path / "compatibilitytools.d" / "GE-Proton10"
    tool.mkdir(parents=True)
    (tool / "proton").write_text("#!/bin/sh\n")
    entry = _make_entry(GameKind.UNUSED_TOOL, tool)
    ok, msg = delete_entry(entry)
    assert ok, msg
    assert not tool.exists()
