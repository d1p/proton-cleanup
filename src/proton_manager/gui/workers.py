"""Background worker threads for scan and size computation."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from proton_manager.model import GameEntry


class ScanWorker(QThread):
    """Run the full scan pipeline off the main thread.

    Emits ``finished(entries, warnings)`` when done or
    ``error(message)`` on fatal failure.
    """

    finished: Signal = Signal(list, list)
    error: Signal = Signal(str)

    def __init__(self, steam_root_override: Path | None = None) -> None:
        super().__init__()
        self._steam_root = steam_root_override

    def run(self) -> None:
        try:
            from proton_manager.cli import _run_scan

            entries, warnings = _run_scan(self._steam_root)
            self.finished.emit(entries, warnings)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class SizeWorker(QThread):
    """Calculate disk sizes for a list of entries in the background.

    Emits ``size_ready(app_id, kind_value, size_bytes)`` for each entry
    as computation completes, allowing the table to update progressively.
    """

    size_ready: Signal = Signal(str, str, int)
    all_done: Signal = Signal()

    def __init__(self, entries: list[GameEntry]) -> None:
        super().__init__()
        self._entries = list(entries)

    def run(self) -> None:
        from proton_manager.delete import deleteable_path
        from proton_manager.scan.sizes import calc_dir_size

        for entry in self._entries:
            path = deleteable_path(entry)
            size = calc_dir_size(path) if path is not None else 0
            self.size_ready.emit(entry.app_id, entry.kind.value, size)
        self.all_done.emit()
