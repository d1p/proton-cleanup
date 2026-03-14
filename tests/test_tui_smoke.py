"""Textual TUI smoke tests: compose, populate, navigation, filter."""
from __future__ import annotations

from pathlib import Path

import pytest

from proton_manager.model import Confidence, GameEntry, GameKind
from proton_manager.tui.app import ProtonManagerApp
from proton_manager.tui.widgets import DetailPane, GameTable, StatusBar
from textual.widgets import Input


def _sample_entries() -> list[GameEntry]:
    return [
        GameEntry(
            app_id="100",
            name="Alpha Game",
            kind=GameKind.STEAM,
            proton_tool="Proton-8",
            proton_version="8.0-5",
            prefix_path=Path("/fake/100/pfx"),
            prefix_exists=True,
            tool_installed=True,
            confidence=Confidence.HIGH,
            evidence=["Explicit override"],
            warnings=[],
        ),
        GameEntry(
            app_id="200",
            name="Beta Shortcut",
            kind=GameKind.SHORTCUT,
            proton_tool=None,
            proton_version=None,
            prefix_path=None,
            prefix_exists=False,
            tool_installed=False,
            confidence=Confidence.UNKNOWN,
            evidence=[],
            warnings=["No compatdata"],
        ),
        GameEntry(
            app_id="300",
            name="Gamma Steam",
            kind=GameKind.STEAM,
            proton_tool="Proton-Exp",
            proton_version=None,
            prefix_path=Path("/fake/300/pfx"),
            prefix_exists=True,
            tool_installed=False,
            confidence=Confidence.MEDIUM,
            evidence=["Prefix exists"],
            warnings=["Tool not installed"],
        ),
    ]


@pytest.mark.asyncio
async def test_app_composes_without_error():
    """App should compose and mount without raising."""
    app = ProtonManagerApp(entries=_sample_entries())
    async with app.run_test(size=(120, 40)) as pilot:
        # Table should be rendered with rows
        table = app.query_one(GameTable)
        assert table.row_count == 3


@pytest.mark.asyncio
async def test_status_bar_shows_counts():
    app = ProtonManagerApp(entries=_sample_entries())
    async with app.run_test(size=(120, 40)) as pilot:
        status = app.query_one(StatusBar)
        assert "3" in str(status.content)


@pytest.mark.asyncio
async def test_filter_reduces_rows():
    app = ProtonManagerApp(entries=_sample_entries())
    async with app.run_test(size=(120, 40)) as pilot:
        # Open filter
        await pilot.press("/")
        await pilot.pause()
        # Set filter value directly and notify the app
        inp = app.query_one("#filter-input", Input)
        inp.value = "Alpha"
        app._filter_text = "Alpha"
        app._refresh_table()
        await pilot.pause()
        table = app.query_one(GameTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_escape_clears_filter():
    app = ProtonManagerApp(entries=_sample_entries())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("/")
        await pilot.pause()
        inp = app.query_one("#filter-input", Input)
        inp.value = "Alpha"
        app._filter_text = "Alpha"
        app._refresh_table()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        table = app.query_one(GameTable)
        assert table.row_count == 3


@pytest.mark.asyncio
async def test_only_steam_filter():
    app = ProtonManagerApp(entries=_sample_entries(), only_steam=True)
    async with app.run_test(size=(120, 40)) as pilot:
        table = app.query_one(GameTable)
        assert table.row_count == 2  # Alpha + Gamma


@pytest.mark.asyncio
async def test_only_shortcuts_filter():
    app = ProtonManagerApp(entries=_sample_entries(), only_shortcuts=True)
    async with app.run_test(size=(120, 40)) as pilot:
        table = app.query_one(GameTable)
        assert table.row_count == 1  # Beta only


@pytest.mark.asyncio
async def test_min_confidence_high():
    app = ProtonManagerApp(entries=_sample_entries(), min_confidence=Confidence.HIGH)
    async with app.run_test(size=(120, 40)) as pilot:
        table = app.query_one(GameTable)
        assert table.row_count == 1  # only Alpha (HIGH)


@pytest.mark.asyncio
async def test_detail_pane_updates_on_navigation():
    app = ProtonManagerApp(entries=_sample_entries())
    async with app.run_test(size=(120, 40)) as pilot:
        detail = app.query_one(DetailPane)
        # First row selected by default
        assert "Alpha Game" in str(detail.content)
        # Move down
        await pilot.press("down")
        await pilot.pause()
        assert "Beta Shortcut" in str(detail.content)


@pytest.mark.asyncio
async def test_empty_entries():
    """TUI with zero entries should not crash."""
    app = ProtonManagerApp(entries=[])
    async with app.run_test(size=(120, 40)) as pilot:
        table = app.query_one(GameTable)
        assert table.row_count == 0
