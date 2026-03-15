"""PySide6 application setup with OLED dark theme."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

# OLED dark colour palette
_COLORS = {
    "background": "#000000",
    "surface": "#0a0a0a",
    "surface_alt": "#111111",
    "accent": "#66c0f4",
    "accent2": "#57cbde",
    "text": "#e0e0e0",
    "text_dim": "#808080",
    "highlight": "#1a1a2e",
    "error": "#cf6679",
    "warn": "#e0a840",
}

_STYLESHEET = """
QMainWindow, QWidget {{
    background-color: {background};
    color: {text};
    font-size: 13px;
}}

QMenuBar, QMenuBar::item {{
    background-color: {surface};
    color: {text};
}}
QMenuBar::item:selected {{
    background-color: {highlight};
}}
QMenu {{
    background-color: {surface};
    color: {text};
    border: 1px solid {highlight};
}}
QMenu::item:selected {{
    background-color: {highlight};
}}

QToolBar {{
    background-color: {surface};
    border: none;
    spacing: 4px;
    padding: 2px 4px;
}}
QToolButton {{
    background-color: transparent;
    color: {text};
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 3px 8px;
}}
QToolButton:hover {{
    background-color: {highlight};
    border-color: {accent};
}}

QLineEdit {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {highlight};
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: {highlight};
}}
QLineEdit:focus {{
    border-color: {accent};
}}

QTabWidget::pane {{
    border: 1px solid {highlight};
}}
QTabBar::tab {{
    background-color: {surface};
    color: {text_dim};
    border: 1px solid {highlight};
    border-bottom: none;
    padding: 4px 14px;
    min-width: 120px;
}}
QTabBar::tab:selected {{
    background-color: {background};
    color: {accent};
    border-bottom: 2px solid {accent};
}}
QTabBar::tab:hover {{
    color: {text};
}}

QTableView {{
    background-color: {background};
    alternate-background-color: {surface_alt};
    color: {text};
    gridline-color: {surface};
    selection-background-color: {highlight};
    selection-color: {text};
    border: none;
}}
QTableView::item {{
    padding: 4px 6px;
}}
QHeaderView::section {{
    background-color: {surface};
    color: {accent};
    border: none;
    border-right: 1px solid {highlight};
    padding: 4px 6px;
    font-weight: bold;
}}

QSplitter::handle {{
    background-color: {surface};
    height: 3px;
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {highlight};
}}

QLabel {{
    color: {text};
}}

QStatusBar {{
    background-color: {surface};
    color: {text_dim};
}}
QStatusBar QLabel {{
    color: {text_dim};
}}

QDialog {{
    background-color: {background};
}}

QListWidget {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {highlight};
    border-radius: 3px;
}}
QListWidget::item:selected {{
    background-color: {highlight};
}}

QDialogButtonBox QPushButton {{
    background-color: {surface};
    color: {text};
    border: 1px solid {highlight};
    border-radius: 3px;
    padding: 5px 14px;
    min-width: 72px;
}}
QDialogButtonBox QPushButton:hover {{
    background-color: {highlight};
}}
QPushButton#deleteButton {{
    background-color: #7a2020;
    color: #ffcccc;
    border: 1px solid {error};
}}
QPushButton#deleteButton:hover {{
    background-color: {error};
    color: white;
}}

QScrollBar:vertical {{
    background-color: {surface_alt};
    width: 10px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {highlight};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
""".format(**_COLORS)


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the ``QApplication`` instance."""
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Proton Cleanup")
    app.setOrganizationName("io.github.protoncleanup")
    app.setStyleSheet(_STYLESHEET)
    return app
