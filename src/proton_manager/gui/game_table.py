"""Reusable game-entry table widget backed by a Qt item model."""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
)

from proton_manager.model import Confidence, GameEntry, GameKind

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

_COLUMNS = [
    ("Game", 240),
    ("App ID", 80),
    ("Tool", 180),
    ("Version", 110),
    ("Size", 90),
    ("Confidence", 90),
    ("Status", 80),
]
_COL_NAMES = [c[0] for c in _COLUMNS]

_CONFIDENCE_COLORS = {
    Confidence.HIGH: QColor("#a3e3a3"),
    Confidence.MEDIUM: QColor("#f0d060"),
    Confidence.LOW: QColor("#f08060"),
    Confidence.UNKNOWN: QColor("#888888"),
}

_KIND_COLORS = {
    GameKind.ORPHAN: QColor("#c080c0"),
    GameKind.UNUSED_TOOL: QColor("#80a8c0"),
}

_STATUS_TEXT = {
    GameKind.ORPHAN: "Orphan",
    GameKind.UNUSED_TOOL: "Unused",
}


def _entry_status(entry: GameEntry) -> str:
    if entry.kind in _STATUS_TEXT:
        return _STATUS_TEXT[entry.kind]
    if entry.warnings:
        return "Warn"
    if entry.prefix_exists:
        return "OK"
    if entry.proton_tool:
        return "No Pfx"
    return "—"


# ---------------------------------------------------------------------------
# Table model
# ---------------------------------------------------------------------------


class GameTableModel(QAbstractTableModel):
    """Qt item model wrapping a list of ``GameEntry`` objects."""

    def __init__(self, entries: list[GameEntry] | None = None) -> None:
        super().__init__()
        self._entries: list[GameEntry] = list(entries or [])

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return len(self._entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return len(_COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _COL_NAMES[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self._entries):
            return None
        entry = self._entries[row]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._cell_text(entry, col)

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._cell_foreground(entry, col)

        if role == Qt.ItemDataRole.FontRole and col == 5:  # Confidence
            f = QFont()
            f.setBold(True)
            return f

        if role == Qt.ItemDataRole.UserRole:
            # Expose the GameEntry so views can retrieve it
            return entry

        return None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_entries(self, entries: list[GameEntry]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def update_size(self, app_id: str, kind_value: str, size_bytes: int) -> None:
        """Update the size field for the matching entry and refresh its cell."""
        for i, entry in enumerate(self._entries):
            if entry.app_id == app_id and entry.kind.value == kind_value:
                entry.prefix_size = size_bytes
                size_col = _COL_NAMES.index("Size")
                idx = self.index(i, size_col)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])
                break

    def entry_at(self, row: int) -> GameEntry | None:
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cell_text(self, entry: GameEntry, col: int) -> str:
        match col:
            case 0:
                return entry.name
            case 1:
                return entry.app_id
            case 2:
                return entry.proton_tool or "—"
            case 3:
                return entry.proton_version or "—"
            case 4:
                return entry.human_size()
            case 5:
                return entry.confidence.value
            case 6:
                return _entry_status(entry)
            case _:
                return ""

    def _cell_foreground(self, entry: GameEntry, col: int) -> QBrush | None:
        if col == 5:
            color = _CONFIDENCE_COLORS.get(entry.confidence)
            if color:
                return QBrush(color)
        if col == 0 and entry.kind in _KIND_COLORS:
            return QBrush(_KIND_COLORS[entry.kind])
        return None


# ---------------------------------------------------------------------------
# Table view
# ---------------------------------------------------------------------------


class GameTableView(QTableView):
    """Styled QTableView with sort support and entry-selection signal."""

    entry_selected: Signal = Signal(object)  # GameEntry | None
    delete_requested: Signal = Signal(list)  # list[GameEntry]

    def __init__(self, entries: list[GameEntry] | None = None) -> None:
        super().__init__()
        self._source_model = GameTableModel(entries)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModel(self._proxy)

        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        for i, (_name, width) in enumerate(_COLUMNS):
            if i > 0:
                self.setColumnWidth(i, width)

        self.selectionModel().currentRowChanged.connect(self._on_current_row_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_entries(self, entries: list[GameEntry]) -> None:
        self._source_model.set_entries(entries)

    def update_size(self, app_id: str, kind_value: str, size_bytes: int) -> None:
        self._source_model.update_size(app_id, kind_value, size_bytes)

    def selected_entries(self) -> list[GameEntry]:
        rows = {idx.row() for idx in self.selectionModel().selectedRows()}
        result = []
        for proxy_row in sorted(rows):
            src_idx = self._proxy.mapToSource(self._proxy.index(proxy_row, 0))
            entry = self._source_model.entry_at(src_idx.row())
            if entry is not None:
                result.append(entry)
        return result

    def current_entry(self) -> GameEntry | None:
        cur = self.currentIndex()
        if not cur.isValid():
            return None
        src = self._proxy.mapToSource(cur)
        return self._source_model.entry_at(src.row())

    def apply_filter(self, text: str) -> None:
        self._proxy.setFilterKeyColumn(-1)  # search all columns
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterFixedString(text)

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            entries = self.selected_entries()
            if entries:
                self.delete_requested.emit(entries)
                return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_current_row_changed(self, current, _previous) -> None:
        if not current.isValid():
            self.entry_selected.emit(None)
            return
        src = self._proxy.mapToSource(current)
        self.entry_selected.emit(self._source_model.entry_at(src.row()))
