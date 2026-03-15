"""Main application window for Proton Cleanup."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from proton_manager.model import GameEntry
from proton_manager.gui.tabs import TabView
from proton_manager.gui.detail_panel import DetailPanel
from proton_manager.gui.delete_dialog import DeleteDialog
from proton_manager.gui.workers import ScanWorker, SizeWorker

_ICON_PATH = Path(__file__).parent.parent.parent.parent / (
    "data/icons/io.github.protoncleanup.ProtonCleanup.png"
)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self, steam_root_override: Path | None = None) -> None:
        super().__init__()
        self._steam_root = steam_root_override
        self._entries: list[GameEntry] = []
        self._scan_worker: ScanWorker | None = None
        self._size_worker: SizeWorker | None = None

        self.setWindowTitle("Proton Cleanup")
        self.resize(1100, 720)

        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))

        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_status_bar()

        # Kick off initial scan
        self._start_scan()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        rescan_act = QAction("&Rescan", self)
        rescan_act.setShortcut(QKeySequence("F5"))
        rescan_act.triggered.connect(self._start_scan)
        file_menu.addAction(rescan_act)

        export_act = QAction("&Export JSON…", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self._export_json)
        file_menu.addAction(export_act)

        file_menu.addSeparator()
        quit_act = QAction("&Quit", self)
        quit_act.setShortcut(QKeySequence("Ctrl+Q"))
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        help_menu = menu.addMenu("&Help")
        about_act = QAction("&About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main toolbar")
        bar.setMovable(False)
        self.addToolBar(bar)

        rescan_act = QAction("⟳  Rescan", self)
        rescan_act.setShortcut(QKeySequence("F5"))
        rescan_act.setToolTip("Re-run the full scan (F5)")
        rescan_act.triggered.connect(self._start_scan)
        bar.addAction(rescan_act)

        bar.addSeparator()

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Filter…")
        self._search_box.setMaximumWidth(260)
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._on_filter_changed)
        bar.addWidget(self._search_box)

        delete_act = QAction("🗑  Delete", self)
        delete_act.setShortcut(QKeySequence("Delete"))
        delete_act.setToolTip("Delete selected entries (Del)")
        delete_act.triggered.connect(self._delete_selected)
        bar.addSeparator()
        bar.addAction(delete_act)

    def _build_central(self) -> None:
        self._tabs = TabView()
        self._tabs.entry_selected.connect(self._on_entry_selected)
        self._tabs.delete_requested.connect(self._open_delete_dialog)

        self._detail = DetailPanel()

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._tabs)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_label = QLabel("Scanning…")
        sb.addPermanentWidget(self._status_label)

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        self._status_label.setText("Scanning…")
        self.setEnabled(False)

        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.quit()
            self._scan_worker.wait()

        self._scan_worker = ScanWorker(self._steam_root)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_scan_finished(self, entries: list[GameEntry], warnings: list[str]) -> None:
        self._entries = entries
        self.setEnabled(True)
        self._tabs.set_entries(entries)
        self._detail.show_entry(None)

        warn_txt = f"  ⚠ {len(warnings)} warning(s)" if warnings else ""
        self._status_label.setText(
            f"{len(entries)} entries{warn_txt}  —  Calculating sizes…"
        )
        self._start_size_worker()

    def _on_scan_error(self, message: str) -> None:
        self.setEnabled(True)
        self._status_label.setText(f"Scan error: {message}")
        QMessageBox.critical(self, "Scan Error", message)

    # ------------------------------------------------------------------
    # Size worker
    # ------------------------------------------------------------------

    def _start_size_worker(self) -> None:
        if self._size_worker and self._size_worker.isRunning():
            self._size_worker.quit()
            self._size_worker.wait()

        self._size_worker = SizeWorker(self._entries)
        self._size_worker.size_ready.connect(self._on_size_ready)
        self._size_worker.all_done.connect(self._on_sizes_done)
        self._size_worker.start()

    def _on_size_ready(self, app_id: str, kind_value: str, size_bytes: int) -> None:
        # Update model entry
        for entry in self._entries:
            if entry.app_id == app_id and entry.kind.value == kind_value:
                entry.prefix_size = size_bytes
                break
        self._tabs.update_size(app_id, kind_value, size_bytes)
        # Refresh detail panel if this is the selected entry
        current = self._tabs.current_entry()
        if current and current.app_id == app_id and current.kind.value == kind_value:
            self._detail.show_entry(current)

    def _on_sizes_done(self) -> None:
        total = sum(e.prefix_size or 0 for e in self._entries)
        self._status_label.setText(
            f"{len(self._entries)} entries  —  Total: {self._human(total)}"
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _on_filter_changed(self, text: str) -> None:
        self._tabs.apply_filter(text)

    # ------------------------------------------------------------------
    # Selection / deletion
    # ------------------------------------------------------------------

    def _on_entry_selected(self, entry: GameEntry | None) -> None:
        self._detail.show_entry(entry)

    def _delete_selected(self) -> None:
        entries = self._tabs.selected_entries()
        if not entries:
            entry = self._tabs.current_entry()
            if entry:
                entries = [entry]
        if entries:
            self._open_delete_dialog(entries)

    def _open_delete_dialog(self, entries: list[GameEntry]) -> None:
        dlg = DeleteDialog(entries, parent=self)
        if dlg.exec() == DeleteDialog.DialogCode.Accepted:
            deleted = dlg.deleted_entries
            if deleted:
                # Remove deleted entries from the list and refresh
                deleted_keys = {(e.app_id, e.kind) for e in deleted}
                self._entries = [
                    e for e in self._entries if (e.app_id, e.kind) not in deleted_keys
                ]
                self._tabs.set_entries(self._entries)
                self._detail.show_entry(None)
                self._status_label.setText(
                    f"{len(self._entries)} entries  —  Deleted {len(deleted)} item(s)"
                )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON",
            "proton-cleanup-export.json",
            "JSON files (*.json)",
        )
        if not path:
            return
        data = [self._entry_to_dict(e) for e in self._entries]
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._status_label.setText(f"Exported {len(data)} entries to {path}")

    @staticmethod
    def _entry_to_dict(entry: GameEntry) -> dict:
        return {
            "app_id": entry.app_id,
            "name": entry.name,
            "kind": entry.kind.value,
            "proton_tool": entry.proton_tool,
            "proton_version": entry.proton_version,
            "prefix_path": str(entry.prefix_path) if entry.prefix_path else None,
            "prefix_exists": entry.prefix_exists,
            "tool_installed": entry.tool_installed,
            "confidence": entry.confidence.value,
            "prefix_size": entry.prefix_size,
            "evidence": entry.evidence,
            "warnings": entry.warnings,
        }

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        from proton_manager import __version__

        QMessageBox.about(
            self,
            "About Proton Cleanup",
            f"<b>Proton Cleanup</b> v{__version__}<br/><br/>"
            "Scan and manage Steam Proton compatibility environments.<br/><br/>"
            "© Debashis Dip — MIT License",
        )

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
