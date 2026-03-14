"""Smoke tests for the JSON CLI output mode."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from proton_manager.model import Confidence, GameEntry, GameKind
from proton_manager.output import COLUMNS, entries_to_json, entry_to_row

# ---------------------------------------------------------------------------
# output.py unit tests
# ---------------------------------------------------------------------------


def _make_entry(**kwargs) -> GameEntry:
    defaults = dict(
        app_id="42",
        name="Test Game",
        kind=GameKind.STEAM,
        proton_tool="Proton-8",
        proton_version="8.0-5",
        prefix_path=Path("/home/deck/.steam/root/steamapps/compatdata/42/pfx"),
        prefix_exists=True,
        tool_installed=True,
        confidence=Confidence.HIGH,
        evidence=["Explicit compat-tool override: 'Proton-8'"],
        warnings=[],
    )
    defaults.update(kwargs)
    return GameEntry(**defaults)


def test_entry_to_row_column_count():
    e = _make_entry()
    row = entry_to_row(e)
    assert len(row) == len(COLUMNS)


def test_entry_to_row_values():
    e = _make_entry()
    row = entry_to_row(e)
    assert row[0] == "Test Game"
    assert row[1] == "Steam"
    assert row[2] == "42"
    assert "Proton-8" in row[3]
    assert row[6] == "HIGH"
    assert row[7] == "OK"


def test_entry_to_row_status_warn():
    e = _make_entry(warnings=["Something is wrong"])
    row = entry_to_row(e)
    assert row[7] == "WARN"


def test_entry_to_row_status_no_pfx():
    e = _make_entry(prefix_exists=False, prefix_path=None, warnings=[])
    row = entry_to_row(e)
    assert row[7] == "NO PFX"


def test_entry_to_row_no_tool():
    e = _make_entry(proton_tool=None, prefix_exists=False, prefix_path=None, warnings=[])
    row = entry_to_row(e)
    assert row[3] == "—"
    assert row[7] == "—"


def test_entries_to_json_valid():
    entries = [_make_entry(), _make_entry(app_id="99", name="Another Game")]
    out = entries_to_json(entries)
    data = json.loads(out)
    assert len(data) == 2
    assert data[0]["app_id"] == "42"
    assert data[1]["name"] == "Another Game"


def test_entries_to_json_schema():
    e = _make_entry()
    data = json.loads(entries_to_json([e]))
    row = data[0]
    required_keys = {
        "app_id",
        "name",
        "kind",
        "proton_tool",
        "proton_version",
        "prefix_path",
        "prefix_exists",
        "tool_installed",
        "confidence",
        "evidence",
        "warnings",
    }
    assert required_keys.issubset(row.keys())


def test_entries_to_json_empty():
    out = entries_to_json([])
    assert json.loads(out) == []


# ---------------------------------------------------------------------------
# cli.py --json mode (integration)
# ---------------------------------------------------------------------------


def test_cli_json_flag(steam_root, capsys):
    """--json should print valid JSON and exit 0."""
    with patch("sys.argv", ["proton-manager", "--json", f"--steam-root={steam_root}"]):
        from proton_manager.cli import main

        main()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    # Our fixture has 1 steam game + 1 shortcut
    assert len(data) >= 1


def test_cli_json_only_steam(steam_root, capsys):
    with patch(
        "sys.argv",
        ["proton-manager", "--json", "--only-steam", f"--steam-root={steam_root}"],
    ):
        from proton_manager.cli import main

        main()

    data = json.loads(capsys.readouterr().out)
    assert all(row["kind"] == "Steam" for row in data)


def test_cli_json_only_shortcuts(steam_root, capsys):
    with patch(
        "sys.argv",
        ["proton-manager", "--json", "--only-shortcuts", f"--steam-root={steam_root}"],
    ):
        from proton_manager.cli import main

        main()

    data = json.loads(capsys.readouterr().out)
    assert all(row["kind"] == "Shortcut" for row in data)


def test_cli_json_min_confidence(steam_root, capsys):
    with patch(
        "sys.argv",
        [
            "proton-manager",
            "--json",
            "--min-confidence",
            "HIGH",
            f"--steam-root={steam_root}",
        ],
    ):
        from proton_manager.cli import main

        main()

    data = json.loads(capsys.readouterr().out)
    # All returned rows must be HIGH confidence
    assert all(row["confidence"] == "HIGH" for row in data)


def test_cli_missing_steam_root(tmp_path):
    bad_path = tmp_path / "does_not_exist"
    with patch("sys.argv", ["proton-manager", "--json", f"--steam-root={bad_path}"]):
        from proton_manager.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0


def test_cli_no_steam_install(tmp_path, capsys):
    """When steam root exists but is empty, should return no games and not crash.

    System-wide Proton tools (e.g. GE-Proton from ~/.local/share/Steam) may
    appear as unused-tool entries, so we use --hide-orphans to isolate the
    empty-root assertion to actual game entries only.
    """
    empty_root = tmp_path / "empty_steam"
    empty_root.mkdir()
    with patch(
        "sys.argv",
        ["proton-manager", "--json", "--hide-orphans", f"--steam-root={empty_root}"],
    ):
        from proton_manager.cli import main

        main()

    data = json.loads(capsys.readouterr().out)
    assert data == []
