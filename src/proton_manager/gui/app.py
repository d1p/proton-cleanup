"""PySide6 application setup with Steam-inspired dark theme."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

# Steam-inspired colour palette
_COLORS = {
    "background": "#1b2838",
    "surface": "#2a475e",
    "surface_alt": "#213447",
    "accent": "#66c0f4",
    "accent2": "#57cbde",
    "text": "#c6d4df",
    "text_dim": "#8f98a0",
    "highlight": "#4d8bb5",
    "error": "#e05050",
    "warn": "#e0a840",
}

_STYLESHEET = """
QMainWindow, QWidget {
    background-color: %(background)s;
    color: %(text)s;
    font-size: 13px;
}

QMenuBar, QMenuBar::item {
    background-color: %(surface)s;
    color: %(text)s;
}
QMenuBar::item:selected {
    background-color: %(highlight)s;
}
QMenu {
    background-color: %(surface)s;
    color: %(text)s;
    border: 1px solid %(highlight)s;
}
QMenu::item:selected {
    background-color: %(highlight)s;
}

QToolBar {
    background-color: %(surface)s;
    border: none;
    spacing: 4px;
    padding: 2px 4px;
}
QToolButton {
    background-color: transparent;
    color: %(text)s;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 3px 8px;
}
QToolButton:hover {
    background-color: %(highlight)s;
    border-color: %(accent)s;
}

QLineEdit {
    background-color: %(surface_alt)s;
    color: %(text)s;
    border: 1px solid %(highlight)s;
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: %(highlight)s;
}
QLineEdit:focus {
    border-color: %(accent)s;
}

QTabWidget::pane {
    border: 1px solid %(highlight)s;
}
QTabBar::tab {
    background-color: %(surface)s;
    color: %(text_dim)s;
    border: 1px solid %(highlight)s;
    border-bottom: none;
    padding: 4px 14px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background-color: %(background)s;
    color: %(accent)s;
    border-bottom: 2px solid %(accent)s;
}
QTabBar::tab:hover {
    color: %(text)s;
}

QTableView {
    background-color: %(background)s;
    alternate-background-color: %(surface_alt)s;
    color: %(text)s;
    gridline-color: %(surface)s;
    selection-background-color: %(highlight)s;
    selection-color: %(text)s;
    border: none;
}
QTableView::item {
    padding: 4px 6px;
}
QHeaderView::section {
    background-color: %(surface)s;
    color: %(accent)s;
    border: none;
    border-right: 1px solid %(highlight)s;
    padding: 4px 6px;
    font-weight: bold;
}

QSplitter::handle {
    background-color: %(surface)s;
    height: 3px;
}

QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: %(highlight)s;
}

QLabel {
    color: %(text)s;
}

QStatusBar {
    background-color: %(surface)s;
    color: %(text_dim)s;
}
QStatusBar QLabel {
    color: %(text_dim)s;
}

QDialog {
    background-color: %(background)s;
}

QListWidget {
    background-color: %(surface_alt)s;
    color: %(text)s;
    border: 1px solid %(highlight)s;
    border-radius: 3px;
}
QListWidget::item:selected {
    background-color: %(highlight)s;
}

QDialogButtonBox QPushButton {
    background-color: %(surface)s;
    color: %(text)s;
    border: 1px solid %(highlight)s;
    border-radius: 3px;
    padding: 5px 14px;
    min-width: 72px;
}
QDialogButtonBox QPushButton:hover {
    background-color: %(highlight)s;
}
QPushButton#deleteButton {
    background-color: #7a2020;
    color: #ffcccc;
    border: 1px solid %(error)s;
}
QPushButton#deleteButton:hover {
    background-color: %(error)s;
    color: white;
}

QScrollBar:vertical {
    background-color: %(surface_alt)s;
    width: 10px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: %(highlight)s;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
""" % _COLORS


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the ``QApplication`` instance."""
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Proton Cleanup")
    app.setOrganizationName("io.github.protoncleanup")
    app.setStyleSheet(_STYLESHEET)
    return app
