"""Delete confirmation modal screen for Proton environments."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

from proton_manager.model import GameEntry, GameKind

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def deleteable_path(entry: GameEntry) -> Path | None:
    """Return the directory that will be deleted for *entry*.

    * **UNUSED_TOOL** → the tool install directory inside ``compatibilitytools.d/``.
    * **Everything else** → the ``compatdata/<app_id>/`` directory.  If
      ``prefix_path`` already points at the ``pfx/`` sub-directory we step up
      one level to reach the ``compatdata/<id>/`` parent.
    """
    if entry.prefix_path is None:
        return None
    p = entry.prefix_path
    if entry.kind == GameKind.UNUSED_TOOL:
        return p
    # For game entries prefix_path may be pfx/ itself.
    if p.name == "pfx":
        return p.parent
    return p


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d  %H:%M")


def entry_timestamps(entry: GameEntry) -> tuple[str, str]:
    """Return ``(created, last_modified)`` human-readable strings.

    *created*:     inode birth time when available (Python 3.12+ on supported
                   filesystems), otherwise the inode-change time (``ctime``).
    *last_modified*: mtime of the ``version`` or ``toolmanifest.vdf`` file
                   inside the directory (updated by Steam/Proton on each
                   launch) with fallback to the directory's own mtime.
    """
    path = deleteable_path(entry)
    if path is None or not path.exists():
        return "—", "—"
    try:
        st = path.stat()
        # Birth time: Python 3.12+ may expose st_birthtime on ext4/btrfs.
        created = _fmt_ts(getattr(st, "st_birthtime", None) or st.st_ctime)
        # Last-used marker: version file mtime is updated on each game launch.
        for marker in ("version", "toolmanifest.vdf"):
            cand = path / marker
            if cand.exists():
                return created, _fmt_ts(cand.stat().st_mtime)
        return created, _fmt_ts(st.st_mtime)
    except OSError:
        return "—", "—"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def authenticate(password: str) -> tuple[bool, str]:
    """Verify *password* against the current unix account via ``sudo``.

    Uses ``sudo -kS /bin/true``:
    * ``-k`` invalidates any cached sudo timestamp so the password is always
      tested even if the user recently ran another sudo command.
    * ``-S`` reads the password from stdin instead of the TTY.

    Returns ``(True, "")`` on success or ``(False, reason)`` on failure.
    """
    try:
        proc = subprocess.run(
            ["sudo", "-kS", "/bin/true"],
            input=password + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return True, ""
        return False, "Incorrect password (or insufficient sudo rights for this account)"
    except FileNotFoundError:
        return False, "sudo not found — cannot authenticate on this system"
    except subprocess.TimeoutExpired:
        return False, "Authentication timed out"


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

_SAFE_PARENT_NAMES: frozenset[str] = frozenset({"compatdata", "compatibilitytools.d"})


def delete_entry(entry: GameEntry) -> tuple[bool, str]:
    """Delete the directory associated with *entry*.

    Includes a safety check: only directories whose immediate parent is named
    ``compatdata`` or ``compatibilitytools.d`` may be deleted.  This prevents
    accidental deletion if ``prefix_path`` were somehow set to an unexpected
    location.

    Returns ``(True, "")`` on success or ``(False, reason)`` on failure.
    """
    path = deleteable_path(entry)
    if path is None:
        return False, "No path is associated with this entry"
    if not path.exists():
        return True, ""  # already gone — treat as success
    if path.is_symlink():
        return False, f"Refusing to follow symbolic link: {path}"
    if not path.is_dir():
        return False, f"Expected a directory at: {path}"

    # Safety guard: only remove directories in expected Steam sub-directories.
    if path.parent.name not in _SAFE_PARENT_NAMES:
        return False, (
            f"Safety check failed: '{path.parent.name}' is not a recognised "
            "Steam sub-directory.  Expected parent name to be 'compatdata' "
            "or 'compatibilitytools.d'."
        )

    try:
        shutil.rmtree(path)
        return True, ""
    except PermissionError as exc:
        return False, f"Permission denied: {exc}"
    except OSError as exc:
        return False, f"Could not delete directory: {exc}"


# ---------------------------------------------------------------------------
# Modal screen
# ---------------------------------------------------------------------------

_KIND_TITLE: dict[GameKind, str] = {
    GameKind.STEAM: "◆  Delete Proton Prefix  —  Steam Game",
    GameKind.SHORTCUT: "◇  Delete Proton Prefix  —  Non-Steam Game",
    GameKind.ORPHAN: "◌  Delete Orphaned Prefix",
    GameKind.UNUSED_TOOL: "⚙  Delete Unused Proton Tool",
}

_KIND_OBJECT: dict[GameKind, str] = {
    GameKind.STEAM: "Proton prefix directory",
    GameKind.SHORTCUT: "Proton prefix directory",
    GameKind.ORPHAN: "orphaned prefix directory",
    GameKind.UNUSED_TOOL: "Proton tool directory",
}


class DeleteConfirmScreen(ModalScreen[GameEntry | None]):
    """Modal confirmation dialog for deleting a Proton environment.

    Dismisses with the deleted :class:`~proton_manager.model.GameEntry` on
    success, or ``None`` when the user cancels.
    """

    DEFAULT_CSS = """
    DeleteConfirmScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #dialog {
        width: 88;
        max-width: 100%;
        height: auto;
        max-height: 95%;
        background: $surface;
        border: round $error;
        padding: 1 2;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        color: $error;
        height: 1;
        margin-bottom: 1;
    }

    #info-table {
        height: 7;
        margin-bottom: 1;
        border: round $panel;
    }

    #warn-text {
        height: 3;
        margin-bottom: 1;
        padding: 0 1;
    }

    #password-section {
        height: auto;
        border: round $panel;
        padding: 0 1;
        margin-bottom: 0;
    }

    #password-label {
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }

    #password-input {
        margin-bottom: 0;
    }

    #error-label {
        color: $error;
        height: 1;
        margin-top: 0;
        margin-bottom: 1;
    }

    #buttons {
        align-horizontal: right;
        height: 3;
        margin-top: 1;
    }

    #btn-cancel {
        margin-right: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, entry: GameEntry) -> None:
        super().__init__()
        self._entry = entry

    def compose(self) -> ComposeResult:
        entry = self._entry
        title = _KIND_TITLE.get(entry.kind, "Delete Proton Environment")
        obj_label = _KIND_OBJECT.get(entry.kind, "directory")
        with Vertical(id="dialog"):
            yield Static(title, id="dialog-title")
            yield DataTable(id="info-table", show_cursor=False)
            yield Static(
                f"[yellow]⚠  This will permanently delete the {obj_label}.[/yellow]\n"
                "[dim]   This action cannot be undone.[/dim]",
                id="warn-text",
            )
            with Vertical(id="password-section"):
                yield Label("Enter your account password to confirm:", id="password-label")
                yield Input(
                    placeholder="Password",
                    password=True,
                    id="password-input",
                    tooltip="Your login password — used to verify your identity before deletion",
                )
                yield Static("", id="error-label")
            with Horizontal(id="buttons"):
                yield Button(
                    "Cancel",
                    id="btn-cancel",
                    variant="default",
                    tooltip="Close this dialog without deleting anything  (Escape)",
                )
                yield Button(
                    "⚠  Delete",
                    id="btn-delete",
                    variant="error",
                    tooltip="Permanently delete this environment after password verification",
                )

    def on_mount(self) -> None:
        entry = self._entry
        del_path = deleteable_path(entry)
        created, modified = entry_timestamps(entry)

        tbl = self.query_one("#info-table", DataTable)
        tbl.add_column("Field", width=14)
        tbl.add_column("Value", width=60)
        tbl.add_row("Name", entry.name)
        tbl.add_row("Path", str(del_path) if del_path else "—")
        tbl.add_row("Created", created)
        tbl.add_row("Last Modified", modified)

        self.query_one("#password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-delete":
            self._attempt_delete()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "password-input":
            self._attempt_delete()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _attempt_delete(self) -> None:
        pwd_input = self.query_one("#password-input", Input)
        error_lbl = self.query_one("#error-label", Static)

        password = pwd_input.value
        if not password:
            error_lbl.update("[red]Password is required.[/red]")
            return

        ok, msg = authenticate(password)
        if not ok:
            error_lbl.update(f"[red]{msg}[/red]")
            pwd_input.value = ""
            pwd_input.focus()
            return

        ok, msg = delete_entry(self._entry)
        if not ok:
            error_lbl.update(f"[red]{msg}[/red]")
            return

        self.dismiss(self._entry)
