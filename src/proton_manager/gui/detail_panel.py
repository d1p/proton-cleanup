"""Detail panel widget showing evidence and warnings for a selected entry."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from proton_manager.model import Confidence, GameEntry, GameKind

_CONF_SYMBOLS = {
    Confidence.HIGH: "●",
    Confidence.MEDIUM: "◑",
    Confidence.LOW: "○",
    Confidence.UNKNOWN: "·",
}

_KIND_ICONS = {
    GameKind.STEAM: "◆",
    GameKind.SHORTCUT: "◇",
    GameKind.ORPHAN: "◌",
    GameKind.UNUSED_TOOL: "⚙",
}


class DetailPanel(QFrame):
    """Shows name, path, timestamps, evidence and warnings for a ``GameEntry``."""

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._label)

        self.show_entry(None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_entry(self, entry: GameEntry | None) -> None:
        if entry is None:
            self._label.setText(
                "<span style='color:#888;font-style:italic;'>Select a row to view details.</span>"
            )
            return

        from proton_manager.delete import entry_timestamps

        icon = _KIND_ICONS.get(entry.kind, "?")
        conf_sym = _CONF_SYMBOLS.get(entry.confidence, "?")
        created, modified = entry_timestamps(entry)
        size_str = entry.human_size()

        path_str = str(entry.prefix_path) if entry.prefix_path else "—"

        html = (
            f"<b>{icon} {self._esc(entry.name)}</b>"
            f"  <span style='color:#888;'>({entry.kind.value})</span>"
            f"  &nbsp; {conf_sym} <span style='color:#aaa;'>{entry.confidence.value}</span>"
            "<br/>"
            f"<span style='color:#aaa;font-size:small;'>"
            f"App ID: {entry.app_id}"
            f"  &nbsp;|&nbsp;  Size: <b>{self._esc(size_str)}</b>"
            f"  &nbsp;|&nbsp;  Created: {self._esc(created)}"
            f"  &nbsp;|&nbsp;  Last used: {self._esc(modified)}"
            "</span><br/>"
            f"<span style='color:#aaa;font-size:small;'>Path: {self._esc(path_str)}</span>"
        )

        if entry.evidence:
            html += "<br/><span style='color:#80c880;font-size:small;'><b>Evidence:</b>"
            for item in entry.evidence:
                html += f"<br/>  • {self._esc(item)}"
            html += "</span>"

        if entry.warnings:
            html += "<br/><span style='color:#e0a840;font-size:small;'><b>Warnings:</b>"
            for item in entry.warnings:
                html += f"<br/>  ⚠ {self._esc(item)}"
            html += "</span>"

        self._label.setText(html)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
