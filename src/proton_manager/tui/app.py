"""Main Textual application for Proton Cleanup."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import DataTable, Footer, Header, Input, Label, Static

from proton_manager.model import Confidence, GameEntry
from proton_manager.tui.widgets import DetailPane, GameTable, StatusBar


# ---------------------------------------------------------------------------
# Steam-inspired dark theme
# ---------------------------------------------------------------------------

_STEAM_THEME = Theme(
    name="steam",
    primary="#66c0f4",       # Steam light blue  — titles, headings, focus rings
    secondary="#a4c2d8",     # muted slate blue  — secondary text
    accent="#57cbde",        # cyan              — accents, icons
    warning="#f0a500",       # amber             — warning indicators
    error="#e74655",         # red               — errors, destructive actions
    success="#5dc963",       # green             — success / OK state
    background="#1b2838",    # Steam dark navy   — screen background
    surface="#2a475e",       # Steam card blue   — detail pane, dialog surfaces
    panel="#171a21",         # Steam sidebar     — filter bar, status bar, footer
    boost="#3d566e",         # row hover         — subtle highlight
    dark=True,
)

# ---------------------------------------------------------------------------
# Help screen: key → description reference
# ---------------------------------------------------------------------------

_HELP_ENTRIES: list[tuple[str, str]] = [
    ("↑ / ↓",   "Move selection up or down"),
    ("/",        "Open inline name-search bar"),
    ("Escape",   "Close search filter  ·  close any modal overlay"),
    ("s",        "Cycle column sort  (ascending → descending → next column)"),
    ("o",        "Toggle display of orphaned prefixes and unused tools"),
    ("d",        "Delete the highlighted environment  (opens confirmation)"),
    ("r",        "Re-run the full environment scan"),
    ("e",        "Export currently-visible entries to JSON file"),
    ("Tab",      "Move keyboard focus between widgets"),
    ("q",        "Quit Proton Cleanup"),
    ("?",        "Show this keyboard shortcuts reference"),
]


class HelpScreen(ModalScreen[None]):
    """Keyboard shortcuts reference overlay.  Press Escape or ? to close."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-dialog {
        width: 72;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        height: 1;
        margin-bottom: 1;
    }
    #help-table {
        height: auto;
        max-height: 20;
        margin-bottom: 1;
    }
    #help-hint {
        text-align: center;
        color: $text-muted;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close_help", "Close", show=False),
        Binding("?", "close_help", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("⌨   Keyboard Shortcuts", id="help-title")
            yield DataTable(id="help-table", show_cursor=False)
            yield Static("[dim]Escape or ?  to close[/dim]", id="help-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#help-table", DataTable)
        tbl.add_column("Key", width=12)
        tbl.add_column("Description", width=52)
        for key, desc in _HELP_ENTRIES:
            tbl.add_row(f"[bold]{key}[/bold]", desc)

    def action_close_help(self) -> None:
        self.dismiss(None)


class ProtonManagerApp(App):
    """Interactive TUI for browsing Proton environment mappings."""

    TITLE = "Proton Cleanup"
    SUB_TITLE = "Steam Proton Environment Scanner"

    CSS = """
    /* ── Layout ────────────────────────────────────────────── */
    Screen {
        layout: vertical;
    }

    /* ── Filter bar ─────────────────────────────────────── */
    #filter-row {
        height: 3;
        display: none;
        background: $panel;
        border-bottom: solid $primary;
    }

    #filter-row.visible {
        display: block;
    }

    #filter-label {
        content-align: center middle;
        width: auto;
        padding: 0 1;
        color: $accent;
        text-style: bold;
    }

    #filter-input {
        width: 1fr;
    }

    /* ── Game table ─────────────────────────────────────── */
    GameTable {
        height: 1fr;
    }

    GameTable.hidden {
        display: none;
    }

    /* ── Empty state ────────────────────────────────────── */
    #empty-state {
        height: 1fr;
        display: none;
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
    }

    #empty-state.active {
        display: block;
    }

    /* ── Detail section header ───────────────────────────── */
    #detail-heading {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $primary;
        text-style: bold;
        border-top: solid $primary;
    }

    /* ── Detail pane ─────────────────────────────────────── */
    DetailPane {
        height: 10;
    }

    /* ── Status bar ─────────────────────────────────────── */
    StatusBar {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "rescan", "Rescan"),
        Binding("/", "toggle_filter", "Filter"),
        Binding("escape", "clear_filter", "Clear"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("o", "toggle_orphans", "Orphans"),
        Binding("d", "delete_entry", "Delete"),
        Binding("e", "export_json", "Export JSON"),
        Binding("?", "help", "Help"),
    ]

    def __init__(
        self,
        entries: list[GameEntry],
        rescan_fn: Callable[[], list[GameEntry]] | None = None,
        min_confidence: Confidence | None = None,
        only_steam: bool = False,
        only_shortcuts: bool = False,
        hide_orphans: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._all_entries = entries
        self._rescan_fn = rescan_fn
        self._min_confidence = min_confidence
        self._only_steam = only_steam
        self._only_shortcuts = only_shortcuts
        self._hide_orphans = hide_orphans
        self._filter_text = ""
        self._current_entries: list[GameEntry] = []

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="filter-row"):
            yield Label("🔍 Search", id="filter-label")
            yield Input(
                placeholder="Filter by name…  (Esc to close)",
                id="filter-input",
                tooltip="Type to filter the game list by name",
            )
        yield GameTable(
            id="game-table",
            show_cursor=True,
            cursor_type="row",
            zebra_stripes=True,
        )
        yield Static(
            "No entries match the current filters.\n"
            "[dim]Press / to change the search, or o to show orphaned environments.[/dim]",
            id="empty-state",
        )
        yield Label(" ◈  Details", id="detail-heading")
        yield DetailPane(id="detail-pane")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(_STEAM_THEME)
        self.theme = "steam"
        self._refresh_table()

    # ------------------------------------------------------------------
    # Table / detail helpers
    # ------------------------------------------------------------------

    def _visible_entries(self) -> list[GameEntry]:
        entries = self._all_entries

        if self._only_steam:
            from proton_manager.model import GameKind
            entries = [e for e in entries if e.kind == GameKind.STEAM]
        if self._only_shortcuts:
            from proton_manager.model import GameKind
            entries = [e for e in entries if e.kind == GameKind.SHORTCUT]
        if self._hide_orphans:
            from proton_manager.model import GameKind
            entries = [e for e in entries if e.kind not in (GameKind.ORPHAN, GameKind.UNUSED_TOOL)]

        if self._min_confidence is not None:
            order = [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW, Confidence.UNKNOWN]
            threshold = order.index(self._min_confidence)
            entries = [e for e in entries if order.index(e.confidence) <= threshold]

        if self._filter_text:
            needle = self._filter_text.lower()
            entries = [e for e in entries if needle in e.name.lower()]

        return entries

    def _refresh_table(self) -> None:
        visible = self._visible_entries()
        table = self.query_one(GameTable)
        self._current_entries = visible
        table.populate(visible)

        # Toggle table vs empty-state visibility
        empty = self.query_one("#empty-state", Static)
        if visible:
            table.remove_class("hidden")
            empty.remove_class("active")
        else:
            table.add_class("hidden")
            empty.add_class("active")

        from proton_manager.model import GameKind
        total_warnings = sum(bool(e.warnings) for e in visible)
        orphan_count = sum(
            1 for e in self._all_entries
            if e.kind in (GameKind.ORPHAN, GameKind.UNUSED_TOOL)
        )
        self.query_one(StatusBar).set_counts(
            total=len(self._all_entries),
            shown=len(visible),
            warnings=total_warnings,
            orphans=orphan_count,
            hide_orphans=self._hide_orphans,
        )
        # Reset detail pane
        self.query_one(DetailPane).show_entry(visible[0] if visible else None)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(GameTable.RowHighlighted)
    def on_row_highlighted(self, event: GameTable.RowHighlighted) -> None:
        try:
            entry = self._current_entries[event.cursor_row]
        except (IndexError, AttributeError):
            entry = None
        self.query_one(DetailPane).show_entry(entry)

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._filter_text = event.value
        self._refresh_table()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_filter(self) -> None:
        row = self.query_one("#filter-row")
        inp = self.query_one("#filter-input", Input)
        if "visible" in row.classes:
            row.remove_class("visible")
            self._filter_text = ""
            inp.value = ""
            self._refresh_table()
        else:
            row.add_class("visible")
            inp.focus()

    def action_clear_filter(self) -> None:
        row = self.query_one("#filter-row")
        inp = self.query_one("#filter-input", Input)
        if "visible" in row.classes:
            row.remove_class("visible")
            self._filter_text = ""
            inp.value = ""
            self._refresh_table()

    def action_toggle_orphans(self) -> None:
        self._hide_orphans = not self._hide_orphans
        state = "hidden" if self._hide_orphans else "shown"
        self.notify(f"Orphaned environments: {state}")
        self._refresh_table()

    def action_cycle_sort(self) -> None:
        self.query_one(GameTable).cycle_sort()

    def action_rescan(self) -> None:
        if self._rescan_fn is None:
            self.notify("No rescan function registered.", severity="warning")
            return
        self.notify("Scanning…")
        self._all_entries = self._rescan_fn()
        self._refresh_table()
        self.notify(f"Done — {len(self._all_entries)} entries.")

    def action_export_json(self) -> None:
        from proton_manager.output import entries_to_json

        out_path = Path("proton-cleanup-export.json")
        out_path.write_text(entries_to_json(self._visible_entries()), encoding="utf-8")
        self.notify(f"Exported {len(self._visible_entries())} entries → {out_path}")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_delete_entry(self) -> None:
        if not self._current_entries:
            self.notify("No entries available.", severity="warning")
            return
        table = self.query_one(GameTable)
        try:
            entry = self._current_entries[table.cursor_row]
        except IndexError:
            self.notify("No entry selected.", severity="warning")
            return

        from proton_manager.tui.delete_dialog import DeleteConfirmScreen, deleteable_path

        if deleteable_path(entry) is None:
            self.notify("This entry has no path to delete.", severity="warning")
            return

        def _on_deleted(deleted: GameEntry | None) -> None:
            if deleted is None:
                return
            key = (deleted.app_id, deleted.kind)
            self._all_entries = [
                e for e in self._all_entries if (e.app_id, e.kind) != key
            ]
            self._refresh_table()
            self.notify(f"Deleted: {deleted.name}")

        self.push_screen(DeleteConfirmScreen(entry), _on_deleted)
