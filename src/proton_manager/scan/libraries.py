"""Parse libraryfolders.vdf and enumerate game manifests across all Steam libraries."""

from __future__ import annotations

from pathlib import Path

import vdf


def enumerate_library_paths(steam_root: Path) -> list[Path]:
    """Return all steamapps directories known to *steam_root*, including remote libraries."""
    libraries: list[Path] = []

    primary = steam_root / "steamapps"
    if primary.is_dir():
        libraries.append(primary)

    # libraryfolders.vdf can live in two locations depending on Steam version
    for vdf_path in (
        steam_root / "steamapps" / "libraryfolders.vdf",
        steam_root / "config" / "libraryfolders.vdf",
    ):
        if not vdf_path.exists():
            continue
        try:
            with vdf_path.open(encoding="utf-8", errors="replace") as fh:
                data = vdf.load(fh)
            # Top-level key is "libraryfolders" or "LibraryFolders"
            root_key = data.get("libraryfolders") or data.get("LibraryFolders") or {}
            for key, val in root_key.items():
                if not key.isdigit():
                    continue
                path_str = val.get("path", "") if isinstance(val, dict) else str(val)
                if path_str:
                    lib = Path(path_str) / "steamapps"
                    if lib.is_dir() and lib not in libraries:
                        libraries.append(lib)
        except Exception:
            pass
        break  # stop after first found vdf

    return libraries


def collect_app_manifests(steamapps: Path) -> list[Path]:
    """Return sorted list of appmanifest_*.acf files under *steamapps*."""
    return sorted(steamapps.glob("appmanifest_*.acf"))


def compatdata_root(steamapps: Path) -> Path:
    """Return the compatdata directory sibling to *steamapps*."""
    return steamapps / "compatdata"
