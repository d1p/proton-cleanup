"""Delete confirmation dialog for Proton environments."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from proton_manager.delete import delete_entry, deleteable_path, entry_timestamps
from proton_manager.model import GameEntry, GameKind

_KIND_TITLE = {
    GameKind.STEAM: "Delete Proton Prefix — Steam Game",
    GameKind.SHORTCUT: "Delete Proton Prefix — Non-Steam Game",
    GameKind.ORPHAN: "Delete Orphaned Prefix",
    GameKind.UNUSED_TOOL: "Delete Unused Proton Tool",
}

_KIND_OBJECT = {
    GameKind.STEAM: "Proton prefix directory",
    GameKind.SHORTCUT: "Proton prefix directory",
    GameKind.ORPHAN: "orphaned prefix directory",
    GameKind.UNUSED_TOOL: "Proton tool directory",
}


class DeleteDialog(QDialog):
    """Confirmation dialog for deleting one or more entries.

    On acceptance the dialog has already performed the deletions.
    Check ``deleted_entries`` for the list of successfully removed items.
    """

    def __init__(self, entries: list[GameEntry], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries = entries
        self.deleted_entries: list[GameEntry] = []

        self.setModal(True)
        self.setMinimumWidth(500)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        if len(entries) == 1:
            self.setWindowTitle(_KIND_TITLE.get(entries[0].kind, "Delete Entry"))
        else:
            self.setWindowTitle(f"Delete {len(entries)} Environments")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        if len(entries) == 1:
            self._build_single(layout, entries[0])
        else:
            self._build_multi(layout, entries)

        # Total size section
        total = sum(e.prefix_size or 0 for e in entries)
        total_label = QLabel()
        if any(e.prefix_size is not None for e in entries):
            total_label.setText(
                f"<b style='color:#e05050;'>Total space freed: {self._human(total)}</b>"
            )
        else:
            total_label.setText(
                "<span style='color:#888;'>Calculating sizes…</span>"
            )
        total_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(total_label)

        # Warning
        warn = QLabel(
            "<span style='color:#e0a840;'>⚠  This action is "
            "<b>permanent</b> and cannot be undone.</span>"
        )
        warn.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(warn)

        # Error label (shown only on failure)
        self._error_label = QLabel()
        self._error_label.setTextFormat(Qt.TextFormat.RichText)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # Buttons
        btn_box = QDialogButtonBox()
        cancel_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setAutoDefault(False)
        self._delete_btn = QPushButton("⚠  Delete")
        self._delete_btn.setObjectName("deleteButton")
        btn_box.addButton(self._delete_btn, QDialogButtonBox.ButtonRole.DestructiveRole)
        btn_box.rejected.connect(self.reject)
        self._delete_btn.clicked.connect(self._attempt_delete)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _build_single(self, layout: QVBoxLayout, entry: GameEntry) -> None:
        path = deleteable_path(entry)
        created, modified = entry_timestamps(entry)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("<b>Name:</b>", QLabel(entry.name))
        form.addRow("<b>Path:</b>", QLabel(str(path) if path else "—"))
        form.addRow("<b>Size:</b>", QLabel(entry.human_size()))
        form.addRow("<b>Created:</b>", QLabel(created))
        form.addRow("<b>Last used:</b>", QLabel(modified))
        for label in form.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.RichText)
        container = QWidget()
        container.setLayout(form)
        layout.addWidget(container)

    def _build_multi(self, layout: QVBoxLayout, entries: list[GameEntry]) -> None:
        layout.addWidget(QLabel(f"<b>Entries to delete ({len(entries)}):</b>"))
        lst = QListWidget()
        lst.setMaximumHeight(150)
        for entry in entries:
            path = deleteable_path(entry)
            size_str = entry.human_size()
            lst.addItem(f"{entry.name}  [{size_str}]  —  {path}")
        layout.addWidget(lst)

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def _attempt_delete(self) -> None:
        errors: list[str] = []
        for entry in self._entries:
            ok, msg = delete_entry(entry)
            if ok:
                self.deleted_entries.append(entry)
            else:
                errors.append(f"{entry.name}: {msg}")

        if errors:
            self._error_label.setText(
                "<span style='color:#e05050;'>"
                + "<br/>".join(errors)
                + "</span>"
            )
            self._error_label.setVisible(True)
        else:
            self.accept()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _human(size: int) -> str:
        n: float = size
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
            n /= 1024
        return "—"
