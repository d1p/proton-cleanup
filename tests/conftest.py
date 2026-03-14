"""Pytest fixtures: synthetic Steam directory trees for scan tests."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers for building fake VDF content
# ---------------------------------------------------------------------------


def make_acf(app_id: int, name: str, compat_tool: str | None = None) -> str:
    compat_section = ""
    if compat_tool:
        compat_section = f'\t\t"CompatTools"\t\t"{compat_tool}"\n'
    return (
        '"AppState"\n'
        "{\n"
        f'\t"appid"\t\t"{app_id}"\n'
        f'\t"name"\t\t"{name}"\n'
        f'\t"StateFlags"\t\t"4"\n' + compat_section + "}\n"
    )


def make_libraryfolders(extra_paths: list[Path]) -> str:
    """Build a minimal libraryfolders.vdf pointing at *extra_paths*."""
    entries = ""
    for i, p in enumerate(extra_paths, start=1):
        entries += f'\t"{i}"\n\t{{\n\t\t"path"\t\t"{p.parent}"\n\t}}\n'
    return '"libraryfolders"\n{\n' + entries + "}\n"


def make_compatibilitytool_vdf(name: str) -> str:
    return f'"compatibilitytools"\n{{\n\t"{name}"\n\t{{\n\t\t"install_path"\t\t"."\n\t}}\n}}\n'


def make_binary_shortcuts_vdf(shortcuts: list[dict]) -> bytes:
    """Build a minimal binary shortcuts.vdf with given shortcut dicts.

    Each dict should have keys: appid (int), appname (str), exe (str),
    optionally compattool (str).
    """
    # Binary VDF format:
    # \x00 "shortcuts" \x00
    #   \x00 "0" \x00
    #     ... key-value pairs ...
    #     \x08 (end of object)
    #   \x08 (end of object for root)

    def null_str(s: str) -> bytes:
        return s.encode("utf-8") + b"\x00"

    def encode_string(key: str, value: str) -> bytes:
        return b"\x01" + null_str(key) + null_str(value)

    def encode_int(key: str, value: int) -> bytes:
        return b"\x02" + null_str(key) + struct.pack("<I", value & 0xFFFFFFFF)

    body = b"\x00" + null_str("shortcuts")
    for i, sc in enumerate(shortcuts):
        obj = b""
        obj += encode_int("appid", sc.get("appid", i))
        obj += encode_string("AppName", sc.get("appname", f"Game {i}"))
        obj += encode_string("Exe", sc.get("exe", "/usr/bin/game"))
        obj += encode_string("StartDir", sc.get("startdir", "/usr/bin/"))
        if "compattool" in sc:
            obj += encode_string("CompatTool", sc["compattool"])
        obj += b"\x08"  # end sub-object
        body += b"\x00" + null_str(str(i)) + obj

    body += b"\x08"  # end "shortcuts" object
    body += b"\x08"  # end root

    return body


# ---------------------------------------------------------------------------
# Fixtures: native Steam root tree
# ---------------------------------------------------------------------------


@pytest.fixture()
def steam_root(tmp_path: Path) -> Path:
    """A minimal native Steam root with one game, one Proton tool, one shortcut."""
    root = tmp_path / "steam"

    # steamapps + one app manifest
    steamapps = root / "steamapps"
    steamapps.mkdir(parents=True)

    acf = make_acf(1234, "Test Game", compat_tool="Proton-8-Test")
    (steamapps / "appmanifest_1234.acf").write_text(acf, encoding="utf-8")

    # compatdata for that game
    compat = steamapps / "compatdata" / "1234"
    pfx = compat / "pfx" / "drive_c"
    pfx.mkdir(parents=True)
    (compat / "version").write_text("8.0-5\n", encoding="utf-8")

    # Proton tool
    tool_dir = root / "compatibilitytools.d" / "Proton-8-Test"
    tool_dir.mkdir(parents=True)
    (tool_dir / "version").write_text("8.0-3\n", encoding="utf-8")
    (tool_dir / "compatibilitytool.vdf").write_text(
        make_compatibilitytool_vdf("Proton-8-Test"), encoding="utf-8"
    )

    # libraryfolders.vdf (primary only, no extra)
    (steamapps / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n}\n', encoding="utf-8")

    # Non-Steam shortcut
    user_dir = root / "userdata" / "99999" / "config"
    user_dir.mkdir(parents=True)

    sc_data = make_binary_shortcuts_vdf(
        [
            {
                "appid": 2147483649,  # 0x80000001
                "appname": "My External Game",
                "exe": "/home/deck/games/mygame",
                "compattool": "Proton-8-Test",
            }
        ]
    )
    (user_dir / "shortcuts.vdf").write_bytes(sc_data)

    # compatdata for the shortcut
    sc_compat = steamapps / "compatdata" / "2147483649" / "pfx" / "drive_c"
    sc_compat.mkdir(parents=True)

    return root


@pytest.fixture()
def flatpak_steam_root(tmp_path: Path) -> Path:
    """Minimal Flatpak-style Steam root (same structure, different path)."""
    root = tmp_path / "flatpak_steam"
    steamapps = root / "steamapps"
    steamapps.mkdir(parents=True)

    acf = make_acf(5678, "Flatpak Game")
    (steamapps / "appmanifest_5678.acf").write_text(acf, encoding="utf-8")

    # compatdata with no pfx (never launched under Proton)
    compat = steamapps / "compatdata" / "5678"
    compat.mkdir(parents=True)
    (compat / "version").write_text("9.0-1\n", encoding="utf-8")

    # Proton tool
    tool_dir = root / "compatibilitytools.d" / "Proton-9-Flat"
    tool_dir.mkdir(parents=True)
    (tool_dir / "version").write_text("9.0-1\n", encoding="utf-8")

    (root / "userdata").mkdir()

    return root
