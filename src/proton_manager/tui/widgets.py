"""Reusable Textual widgets for the Proton Cleanup TUI."""
from __future__ import annotations

from textual.widgets import DataTable, Static
from textual.reactive import reactive

from proton_manager.model import Confidence, GameEntry, GameKind
from proton_manager.output import COLUMNS, entry_to_row

# ── Colour maps ─────────────────────────────────────────────────────────────
# Confidence → Rich colour tag
_CONF_COLOUR: dict[Confidence, str] = {
    Confidence.HIGH:    "green",
    Confidence.MEDIUM:  "yellow",
    Confidence.LOW:     "red",
    Confidence.UNKNOWN: "dim",
}

# Confidence → symbol  (colour alone must never be the sole indicator — WCAG 1.4.1)
_CONF_SYMBOL: dict[Confidence, str] = {
    Confidence.HIGH:    "●",   # solid circle
    Confidence.MEDIUM:  "◑",   # half circle
    Confidence.LOW:     "○",   # empty circle
    Confidence.UNKNOWN: "·",   # dim dot
}

_STATUS_COLOUR: dict[str, str] = {
    "OK":     "green",
    "WARN":   "yellow",
    "NO PFX": "cyan",
    "ORPHAN": "magenta",
    "UNUSED": "blue",
    "—":      "dim",
}

# Status → symbol  (colour alone must never be the sole indicator — WCAG 1.4.1)
_STATUS_SYMBOL: dict[str, str] = {
    "OK":     "✓",   # checkmark — healthy prefix
    "WARN":   "⚠",   # warning triangle
    "NO PFX": "□",   # empty box — prefix directory absent
    "ORPHAN": "?",   # question mark — no linked game
    "UNUSED": "⊘",   # circled slash — tool not in use
    "—":      "·",   # dim dot
}

# ── Kind icons and row tints ──────────────────────────────────────────────────
# Kind → single-character icon prefix for the Kind column
_KIND_ICON: dict[GameKind, str] = {
    GameKind.STEAM:       "◆",   # filled diamond   — installed Steam game
    GameKind.SHORTCUT:    "◇",   # open diamond     — non-Steam shortcut
    GameKind.ORPHAN:      "◌",   # dotted circle    — prefix without a game
    GameKind.UNUSED_TOOL: "⚙",   # gear             — tool without a game
}

# Kind → row colour override  (None = default foreground)
_KIND_COLOUR: dict[GameKind, str | None] = {
    GameKind.STEAM:       None,
    GameKind.SHORTCUT:    None,
    GameKind.ORPHAN:      "magenta",
    GameKind.UNUSED_TOOL: "blue",
}


class GameTable(DataTable):
    """Sortable DataTable pre-configured with Proton Cleanup columns."""

    TOOLTIP = "↑ ↓  navigate   ·   d  delete   ·   /  search   ·   s  sort   ·   ?  help"

    # Index of the column currently used for sort, -1 = unsorted
    _sort_col: reactive[int] = reactive(-1)
    _sort_asc: reactive[bool] = reactive(True)

    def populate(self, entries: list[GameEntry]) -> None:
        """Clear and re-fill the table from *entries*."""
        self.clear(columns=True)
        for label, width in COLUMNS:
            self.add_column(label, width=width)

        for entry in entries:
            cells = entry_to_row(entry)
            conf = entry.confidence
            status = cells[7]  # "Status" column index
            coloured = list(cells)
            kind_colour = _KIND_COLOUR.get(entry.kind)
            if kind_colour:
                # Tint all cells for special-kind rows
                coloured = [f"[{kind_colour}]{c}[/]" for c in coloured]

            # Kind column (index 1) — icon + text; symbol not just colour (WCAG 1.4.1)
            icon = _KIND_ICON.get(entry.kind, "")
            if kind_colour:
                coloured[1] = f"[{kind_colour}]{icon} {cells[1]}[/]"
            else:
                coloured[1] = f"{icon} {cells[1]}"

            # Confidence column (index 6) — colour + symbol
            sym = _CONF_SYMBOL[conf]
            coloured[6] = f"[{_CONF_COLOUR[conf]}]{sym} {cells[6]}[/]"

            # Status column (index 7) — colour + symbol
            ssym = _STATUS_SYMBOL.get(status, "")
            coloured[7] = f"[{_STATUS_COLOUR.get(status, '')}]{ssym} {status}[/]"

            self.add_row(*coloured, key=entry.app_id + entry.kind.value)

    def cycle_sort(self) -> None:
        """Advance sort to the next column (wraps around, then clears)."""
        total = len(COLUMNS)
        if self._sort_col == -1:
            self._sort_col = 0
            self._sort_asc = True
        elif self._sort_asc:
            self._sort_asc = False
        else:
            self._sort_col = (self._sort_col + 1) % total
            self._sort_asc = True
            if self._sort_col == 0:
                self._sort_col = -1
        if self._sort_col >= 0:
            self.sort(COLUMNS[self._sort_col][0], reverse=not self._sort_asc)


class DetailPane(Static):
    """Displays evidence + warnings for the currently selected GameEntry."""

    DEFAULT_CSS = """
    DetailPane {
        padding: 0 1;
        height: 10;
        overflow-y: auto;
        background: $surface;
    }
    """

    def show_entry(self, entry: GameEntry | None) -> None:
        if entry is None:
            self.update("[dim]  Select a row to view details.[/dim]")
            return

        lines: list[str] = []
        conf_col = _CONF_COLOUR[entry.confidence]
        conf_sym = _CONF_SYMBOL[entry.confidence]
        kind_icon = _KIND_ICON.get(entry.kind, "")

        lines.append(
            f"  [bold]{entry.name}[/bold]  "
            f"[dim]{kind_icon} {entry.kind.value} · {entry.app_id}[/dim]  "
            f"[{conf_col}]{conf_sym} {entry.confidence.value}[/]"
        )
        lines.append("")

        if entry.evidence:
            lines.append("  [bold green]Evidence[/bold green]")
            for item in entry.evidence:
                lines.append(f"    [green]✓[/green]  {item}")

        if entry.warnings:
            lines.append("")
            lines.append("  [bold yellow]Warnings[/bold yellow]")
            for w in entry.warnings:
                lines.append(f"    [yellow]⚠[/yellow]  {w}")

        if not entry.evidence and not entry.warnings:
            lines.append("  [dim]No evidence or warnings recorded.[/dim]")

        self.update("\n".join(lines))


class StatusBar(Static):
    """One-line segmented status bar at the bottom of the screen."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def set_counts(self, total: int, shown: int, warnings: int,
                   orphans: int = 0, hide_orphans: bool = False) -> None:
        sep = "  [dim]│[/dim]  "
        parts: list[str] = [f"◈  {shown} of {total} entries"]
        if warnings:
            s = "s" if warnings != 1 else ""
            parts.append(f"[yellow]⚠  {warnings} warning{s}[/yellow]")
        if orphans:
            sym = "◌" if hide_orphans else "○"
            state = "hidden" if hide_orphans else "visible"
            parts.append(
                f"[magenta]{sym}  {orphans} unlinked — {state}  "
                f"([bold]o[/bold] to toggle)[/magenta]"
            )
        self.update(" " + sep.join(parts))
