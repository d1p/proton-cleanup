"""PySide6 GUI smoke tests — widget instantiation with offscreen platform."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Force offscreen rendering so tests work in headless CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from proton_manager.model import Confidence, GameEntry, GameKind  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _sample_entries() -> list[GameEntry]:
    return [
        GameEntry(
            app_id="100",
            name="Alpha Game",
            kind=GameKind.STEAM,
            proton_tool="Proton-8",
            proton_version="8.0-5",
            prefix_path=Path("/fake/compatdata/100/pfx"),
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
            name="Orphan Prefix",
            kind=GameKind.ORPHAN,
            proton_tool=None,
            proton_version=None,
            prefix_path=Path("/fake/compatdata/300"),
            prefix_exists=True,
            tool_installed=False,
            confidence=Confidence.UNKNOWN,
            evidence=[],
            warnings=[],
        ),
    ]


# ---------------------------------------------------------------------------
# GameTableModel
# ---------------------------------------------------------------------------


def test_game_table_model_row_count(qapp) -> None:
    from proton_manager.gui.game_table import GameTableModel

    entries = _sample_entries()
    model = GameTableModel(entries)
    assert model.rowCount() == len(entries)


def test_game_table_model_column_count(qapp) -> None:
    from proton_manager.gui.game_table import GameTableModel, _COLUMNS

    model = GameTableModel(_sample_entries())
    assert model.columnCount() == len(_COLUMNS)


def test_game_table_model_display_data(qapp) -> None:
    from PySide6.QtCore import Qt

    from proton_manager.gui.game_table import GameTableModel

    model = GameTableModel(_sample_entries())
    idx = model.index(0, 0)
    assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "Alpha Game"


def test_game_table_model_set_entries(qapp) -> None:
    from proton_manager.gui.game_table import GameTableModel

    model = GameTableModel([])
    assert model.rowCount() == 0
    model.set_entries(_sample_entries())
    assert model.rowCount() == 3


def test_game_table_model_update_size(qapp) -> None:
    from proton_manager.gui.game_table import GameTableModel, _COL_NAMES
    from PySide6.QtCore import Qt

    model = GameTableModel(_sample_entries())
    model.update_size("100", GameKind.STEAM.value, 1024 * 1024 * 500)
    size_col = _COL_NAMES.index("Size")
    idx = model.index(0, size_col)
    text = model.data(idx, Qt.ItemDataRole.DisplayRole)
    assert "500" in text or "MB" in text


# ---------------------------------------------------------------------------
# GameTableView
# ---------------------------------------------------------------------------


def test_game_table_view_constructs(qapp) -> None:
    from proton_manager.gui.game_table import GameTableView

    view = GameTableView(_sample_entries())
    assert view is not None


def test_game_table_view_filter(qapp) -> None:
    from proton_manager.gui.game_table import GameTableView

    view = GameTableView(_sample_entries())
    view.apply_filter("Alpha")
    assert view.model().rowCount() == 1


# ---------------------------------------------------------------------------
# DetailPanel
# ---------------------------------------------------------------------------


def test_detail_panel_show_none(qapp) -> None:
    from proton_manager.gui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_entry(None)  # should not raise


def test_detail_panel_show_entry(qapp) -> None:
    from proton_manager.gui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_entry(_sample_entries()[0])


# ---------------------------------------------------------------------------
# TabView
# ---------------------------------------------------------------------------


def test_tab_view_three_tabs(qapp) -> None:
    from proton_manager.gui.tabs import TabView

    tabs = TabView()
    assert tabs.count() == 3


def test_tab_view_set_entries(qapp) -> None:
    from proton_manager.gui.tabs import TabView

    tabs = TabView()
    tabs.set_entries(_sample_entries())
    # Steam tab should show "Steam Games (1)"
    assert "1" in tabs.tabText(0)
    assert "1" in tabs.tabText(1)
    assert "1" in tabs.tabText(2)


# ---------------------------------------------------------------------------
# human_size helper on GameEntry
# ---------------------------------------------------------------------------


def test_human_size_none() -> None:
    e = _sample_entries()[0]
    assert e.human_size() == "—"


def test_human_size_bytes() -> None:
    e = _sample_entries()[0]
    e.prefix_size = 512
    assert e.human_size() == "512 B"


def test_human_size_megabytes() -> None:
    e = _sample_entries()[0]
    e.prefix_size = 1024 * 1024 * 256
    result = e.human_size()
    assert "MB" in result or "GB" in result
