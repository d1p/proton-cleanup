"""Tabbed interface — one tab per GameKind group."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget

from proton_manager.gui.game_table import GameTableView
from proton_manager.model import GameEntry, GameKind


class TabView(QTabWidget):
    """Three-tab view: Steam Games, Shortcuts, Orphans & Tools.

    Exposes a unified ``entry_selected`` and ``delete_requested`` signal
    that aggregates across all tabs.
    """

    entry_selected: Signal = Signal(object)  # GameEntry | None
    delete_requested: Signal = Signal(list)  # list[GameEntry]

    def __init__(self) -> None:
        super().__init__()
        self._steam_table = GameTableView()
        self._shortcuts_table = GameTableView()
        self._orphans_table = GameTableView()

        self.addTab(self._steam_table, "Steam Games")
        self.addTab(self._shortcuts_table, "Shortcuts")
        self.addTab(self._orphans_table, "Orphans & Tools")

        for table in self._all_tables():
            table.entry_selected.connect(self.entry_selected)
            table.delete_requested.connect(self.delete_requested)

        self.currentChanged.connect(self._on_tab_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_entries(self, entries: list[GameEntry]) -> None:
        steam = [e for e in entries if e.kind == GameKind.STEAM]
        shortcuts = [e for e in entries if e.kind == GameKind.SHORTCUT]
        orphans = [e for e in entries if e.kind in (GameKind.ORPHAN, GameKind.UNUSED_TOOL)]
        self._steam_table.set_entries(steam)
        self._shortcuts_table.set_entries(shortcuts)
        self._orphans_table.set_entries(orphans)
        self._update_tab_titles(steam, shortcuts, orphans)

    def update_size(self, app_id: str, kind_value: str, size_bytes: int) -> None:
        for table in self._all_tables():
            table.update_size(app_id, kind_value, size_bytes)

    def apply_filter(self, text: str) -> None:
        for table in self._all_tables():
            table.apply_filter(text)

    def selected_entries(self) -> list[GameEntry]:
        return self._current_table().selected_entries()

    def current_entry(self) -> GameEntry | None:
        return self._current_table().current_entry()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _all_tables(self) -> list[GameTableView]:
        return [self._steam_table, self._shortcuts_table, self._orphans_table]

    def _current_table(self) -> GameTableView:
        idx = self.currentIndex()
        return self._all_tables()[idx] if 0 <= idx < 3 else self._steam_table

    def _update_tab_titles(
        self,
        steam: list,
        shortcuts: list,
        orphans: list,
    ) -> None:
        self.setTabText(0, f"Steam Games ({len(steam)})")
        self.setTabText(1, f"Shortcuts ({len(shortcuts)})")
        self.setTabText(2, f"Orphans & Tools ({len(orphans)})")

    def _on_tab_changed(self, _index: int) -> None:
        self.entry_selected.emit(self._current_table().current_entry())
