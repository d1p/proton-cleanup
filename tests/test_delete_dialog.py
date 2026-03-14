"""Tests for the delete confirmation dialog and associated helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import DataTable, Input, Static

from proton_manager.model import Confidence, GameEntry, GameKind
from proton_manager.tui.app import ProtonManagerApp
from proton_manager.tui.delete_dialog import (
    DeleteConfirmScreen,
    delete_entry,
    deleteable_path,
    entry_timestamps,
)

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
    """A STEAM entry whose prefix lives inside a proper compatdata/ dir."""
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


def test_deleteable_path_pfx_subdir(tmp_path):
    pfx = tmp_path / "compatdata" / "1234" / "pfx"
    pfx.mkdir(parents=True)
    entry = _make_entry(GameKind.STEAM, pfx)
    assert deleteable_path(entry) == pfx.parent  # compatdata/1234


def test_deleteable_path_orphan_no_pfx(tmp_path):
    compat = tmp_path / "compatdata" / "9999"
    compat.mkdir(parents=True)
    entry = _make_entry(GameKind.ORPHAN, compat)
    assert deleteable_path(entry) == compat


def test_deleteable_path_unused_tool(tmp_path):
    tool = tmp_path / "compatibilitytools.d" / "GE-Proton10"
    tool.mkdir(parents=True)
    entry = _make_entry(GameKind.UNUSED_TOOL, tool)
    assert deleteable_path(entry) == tool


def test_deleteable_path_none():
    entry = _make_entry(prefix=None)
    assert deleteable_path(entry) is None


# ---------------------------------------------------------------------------
# entry_timestamps
# ---------------------------------------------------------------------------


def test_entry_timestamps_no_path():
    entry = _make_entry(prefix=None)
    assert entry_timestamps(entry) == ("—", "—")


def test_entry_timestamps_missing_dir(tmp_path):
    gone = tmp_path / "compatdata" / "0000"
    entry = _make_entry(GameKind.ORPHAN, gone)
    assert entry_timestamps(entry) == ("—", "—")


def test_entry_timestamps_returns_strings(tmp_path):
    compat = tmp_path / "compatdata" / "1234"
    compat.mkdir(parents=True)
    (compat / "version").write_text("8.0-5\n")
    entry = _make_entry(GameKind.ORPHAN, compat)
    created, modified = entry_timestamps(entry)
    assert created != "—"
    assert modified != "—"
    # Rough format check: "YYYY-MM-DD  HH:MM"
    assert len(created) == 17
    assert "-" in created


# ---------------------------------------------------------------------------
# delete_entry – unit tests (no filesystem required for some)
# ---------------------------------------------------------------------------


def test_delete_entry_removes_directory(tmp_path):
    compat = tmp_path / "compatdata" / "9999"
    compat.mkdir(parents=True)
    (compat / "pfx").mkdir()
    (compat / "version").write_text("8.0-5\n")
    entry = _make_entry(GameKind.ORPHAN, compat)

    ok, msg = delete_entry(entry)

    assert ok, msg
    assert not compat.exists()


def test_delete_entry_already_gone(tmp_path):
    compat = tmp_path / "compatdata" / "9999"
    # Do not create the directory.
    entry = _make_entry(GameKind.ORPHAN, compat)
    ok, msg = delete_entry(entry)
    assert ok


def test_delete_entry_no_path():
    entry = _make_entry(prefix=None)
    ok, msg = delete_entry(entry)
    assert not ok
    assert "no path" in msg.lower()


def test_delete_entry_safety_check_blocks_arbitrary_path(tmp_path):
    bad = tmp_path / "random" / "stuff"
    bad.mkdir(parents=True)
    entry = _make_entry(prefix=bad)
    ok, msg = delete_entry(entry)
    assert not ok
    assert "safety check" in msg.lower()


def test_delete_entry_unused_tool(tmp_path):
    tool = tmp_path / "compatibilitytools.d" / "GE-Proton10"
    tool.mkdir(parents=True)
    (tool / "compatibilitytool.vdf").write_text('"compatibilitytools" {}\n')
    entry = _make_entry(GameKind.UNUSED_TOOL, tool)
    ok, msg = delete_entry(entry)
    assert ok
    assert not tool.exists()


def test_delete_entry_refuses_symlink(tmp_path):
    real_dir = tmp_path / "compatdata" / "1234"
    real_dir.mkdir(parents=True)
    sym = tmp_path / "compatdata" / "link"
    sym.symlink_to(real_dir)
    entry = _make_entry(GameKind.ORPHAN, sym)
    ok, msg = delete_entry(entry)
    assert not ok
    assert "symbolic link" in msg.lower()


# ---------------------------------------------------------------------------
# DeleteConfirmScreen — dialog smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dialog_composes_shows_table(tmp_path):
    entry = _steam_entry(tmp_path)
    app = ProtonManagerApp(entries=[entry])
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(DeleteConfirmScreen(entry))
        await pilot.pause()
        # After push_screen the modal IS app.screen
        tbl = app.screen.query_one("#info-table", DataTable)
        assert tbl.row_count == 4  # Name, Path, Created, Last Modified


@pytest.mark.asyncio
async def test_dialog_escape_cancels(tmp_path):
    entry = _steam_entry(tmp_path)
    dismissed: list = []
    app = ProtonManagerApp(entries=[entry])
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(DeleteConfirmScreen(entry), dismissed.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert dismissed == [None]


@pytest.mark.asyncio
async def test_dialog_cancel_button(tmp_path):
    entry = _steam_entry(tmp_path)
    dismissed: list = []
    app = ProtonManagerApp(entries=[entry])
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(DeleteConfirmScreen(entry), dismissed.append)
        await pilot.pause()
        await pilot.click("#btn-cancel")
        await pilot.pause()
    assert dismissed == [None]


@pytest.mark.asyncio
async def test_dialog_empty_password_shows_error(tmp_path):
    entry = _steam_entry(tmp_path)
    dismissed: list = []
    app = ProtonManagerApp(entries=[entry])
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(DeleteConfirmScreen(entry), dismissed.append)
        await pilot.pause()
        # Click delete without a password
        await pilot.click("#btn-delete")
        await pilot.pause()
        error_lbl = app.screen.query_one("#error-label", Static)
        assert "required" in str(error_lbl.content).lower()
        assert dismissed == []  # dialog still open


@pytest.mark.asyncio
async def test_dialog_wrong_password_shows_error(tmp_path):
    entry = _steam_entry(tmp_path)
    dismissed: list = []
    with patch(
        "proton_manager.tui.delete_dialog.authenticate",
        return_value=(False, "Incorrect password"),
    ):
        app = ProtonManagerApp(entries=[entry])
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(DeleteConfirmScreen(entry), dismissed.append)
            await pilot.pause()
            app.screen.query_one("#password-input", Input).value = "wrongpass"
            await pilot.click("#btn-delete")
            await pilot.pause()
            error_lbl = app.screen.query_one("#error-label", Static)
            assert "incorrect" in str(error_lbl.content).lower()
            assert dismissed == []


@pytest.mark.asyncio
async def test_dialog_correct_password_dismisses_with_entry(tmp_path):
    entry = _steam_entry(tmp_path)
    dismissed: list = []
    with (
        patch("proton_manager.tui.delete_dialog.authenticate", return_value=(True, "")),
        patch("proton_manager.tui.delete_dialog.delete_entry", return_value=(True, "")) as mock_del,
    ):
        app = ProtonManagerApp(entries=[entry])
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(DeleteConfirmScreen(entry), dismissed.append)
            await pilot.pause()
            app.screen.query_one("#password-input", Input).value = "correctpass"
            await pilot.click("#btn-delete")
            await pilot.pause()
        assert dismissed == [entry]
        mock_del.assert_called_once_with(entry)


@pytest.mark.asyncio
async def test_dialog_delete_failure_shows_error(tmp_path):
    """delete_entry returning an error should keep the dialog open."""
    entry = _steam_entry(tmp_path)
    dismissed: list = []
    with (
        patch("proton_manager.tui.delete_dialog.authenticate", return_value=(True, "")),
        patch(
            "proton_manager.tui.delete_dialog.delete_entry",
            return_value=(False, "Permission denied: /some/path"),
        ),
    ):
        app = ProtonManagerApp(entries=[entry])
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(DeleteConfirmScreen(entry), dismissed.append)
            await pilot.pause()
            app.screen.query_one("#password-input", Input).value = "pass"
            await pilot.click("#btn-delete")
            await pilot.pause()
            error_lbl = app.screen.query_one("#error-label", Static)
            assert "permission" in str(error_lbl.content).lower()
            assert dismissed == []


# ---------------------------------------------------------------------------
# App-level integration: pressing 'd' opens dialog; confirm removes entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_delete_action_removes_entry(tmp_path):
    compat = tmp_path / "compatdata" / "9999"
    compat.mkdir(parents=True)
    entry = GameEntry(
        app_id="9999",
        name="Orphaned Prefix",
        kind=GameKind.ORPHAN,
        proton_tool=None,
        proton_version=None,
        prefix_path=compat,
        prefix_exists=True,
        tool_installed=False,
        confidence=Confidence.UNKNOWN,
    )
    from proton_manager.tui.widgets import GameTable

    with (
        patch("proton_manager.tui.delete_dialog.authenticate", return_value=(True, "")),
        patch("proton_manager.tui.delete_dialog.delete_entry", return_value=(True, "")),
    ):
        app = ProtonManagerApp(entries=[entry])
        async with app.run_test(size=(120, 40)) as pilot:
            assert app.query_one(GameTable).row_count == 1
            await pilot.press("d")
            await pilot.pause()
            # Dialog is open; app.screen is now the modal
            app.screen.query_one("#password-input", Input).value = "mypassword"
            await pilot.click("#btn-delete")
            await pilot.pause()
            assert app.query_one(GameTable).row_count == 0


@pytest.mark.asyncio
async def test_app_delete_no_entries_warns():
    """'d' on an empty table shows a warning, not a crash."""
    app = ProtonManagerApp(entries=[])
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("d")
        await pilot.pause()
        # App should still be running
        assert app.is_running
