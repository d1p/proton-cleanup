# Proton Cleanup

A desktop app for **Steam Deck** and any **Linux desktop** that answers one question:

> *Which Proton compatibility layer is each of my games actually using — and is everything set up correctly?*

It scans your Steam library, non-Steam shortcuts, installed Proton tools, and Wine
prefixes, then shows everything in a Qt GUI with an OLED dark theme — search, sort,
filter by tab, and delete entries you no longer need.

---

## Contents

1. [What is Proton?](#what-is-proton)
2. [What does this tool do?](#what-does-this-tool-do)
3. [Quick Start: Download Pre-built Releases](#quick-start-download-pre-built-releases)
4. [Installation](#installation)
5. [Flatpak package (no Python setup)](#flatpak-package-no-python-setup)
6. [Launching the app](#launching-the-app)
7. [Understanding the table](#understanding-the-table)
8. [Using the GUI](#using-the-gui)
9. [Deleting an environment](#deleting-an-environment)
10. [Confidence levels explained](#confidence-levels-explained)
11. [Row types explained](#row-types-explained)
12. [Frequently asked questions](#frequently-asked-questions)
13. [For developers](#for-developers)

---

## What is Proton?

Proton is a compatibility layer built into Steam that lets Windows-only games run on
Linux.  It is built on top of Wine and includes a collection of patches and
performance improvements.

Each game can use a different version of Proton, and you can also install community
builds such as **GE-Proton** (Glorious Eggroll) that add extra fixes not yet in the
official release.

Every time a game is launched through Proton, Steam creates a personal **Wine prefix**
for it — a small folder that mimics a Windows file system and holds the game's own
registry, save-game locations, and runtime files.  By default these live at:

```
~/.steam/root/steamapps/compatdata/<AppID>/
```

Over time you can end up with dozens of these folders, some for games you no longer
own, some pointing at tools you have since deleted.  Proton Cleanup helps you see all
of that at a glance.

---

## What does this tool do?

Proton Cleanup scans your system and builds a complete picture of every Proton
environment:

| What it finds | How |
|---|---|
| Every Steam game | Reads `appmanifest_*.acf` files from all library folders |
| Non-Steam shortcuts (e.g. GOG, itch.io games) | Parses the binary `shortcuts.vdf` file |
| Which Proton tool each game uses | Reads `config.vdf` CompatToolMapping — the authoritative source Steam itself uses |
| Whether the Wine prefix exists on disk | Checks the `compatdata/<id>/pfx/` directory |
| Orphaned prefixes | `compatdata/` folders with no matching game (game was uninstalled but prefix left behind) |
| Unused tools | Proton tools installed in `compatibilitytools.d/` that no game currently uses |
| Prefix creation and last-used dates | File-system timestamps on the prefix directory |

Results are shown in a desktop GUI with tabbed views for Steam games, shortcuts, and
orphans.  You can search, sort, and delete entries you no longer need — all without
opening a file manager or running manual `rm` commands.

---

## Quick Start: Download Pre-built Releases

**For most users: Download the ready-to-use Flatpak bundle** — no Python or command line needed.

### Option 1: Download from GitHub Releases (Easiest)

1. Visit the [Releases page](https://github.com/d1p/proton-cleanup/releases)
2. Find the latest release (top of the list)
3. Scroll down to **Assets** and download `proton-cleanup.flatpak`
4. Open your file manager and double-click the `.flatpak` file to install
5. Launch from your application menu — no terminal required

That's it! The app is ready to use.

### Option 2: Build from Source

If you prefer installing from the repository or need to customize the build, follow the [Installation](#installation) section below.

---

## Installation

### Prerequisites

- Python 3.10 or newer (`python3 --version`)
- pip

On **Steam Deck**, open the desktop and launch a terminal (Konsole).

### Using pip (recommended)

```bash
# Clone the repository
git clone https://github.com/d1p/proton-cleanup.git
cd proton-cleanup

# Create an isolated Python environment (keeps your system Python clean)
python3 -m venv .venv
source .venv/bin/activate

# Install the app and its dependencies
pip install -e .

# Or use make (installs dev dependencies too)
make dev
```

### Verify the installation

```bash
proton-cleanup --version
# → proton-cleanup 0.1.0
```

`proton-manager` is still available as a compatibility alias.

## Flatpak package (no Python setup)

If you want a user-runnable build with no Python/venv setup, build a Flatpak bundle:

```bash
# From the repository root
./scripts/build-flatpak.sh
```

The script creates:

- `dist/proton-cleanup.flatpak` (single-file bundle to share/install)

Install and run locally:

```bash
flatpak --user install --bundle -y dist/proton-cleanup.flatpak
flatpak run io.github.protoncleanup.ProtonCleanup
```

This is the recommended distribution format for non-developer users.

---

## Launching the app

```bash
# Make sure the virtual environment is active first:
source .venv/bin/activate

# Then launch:
proton-cleanup
```

If installed as Flatpak:

```bash
flatpak run io.github.protoncleanup.ProtonCleanup
```

The app opens immediately and begins scanning.  On a typical Steam Deck
with 50–100 games the scan finishes in under a second.

To exit, close the window or press **Ctrl+Q**.

---

## Understanding the table

Each row represents one game, shortcut, orphaned prefix, or unused tool.  The columns are:

| Column | What it shows |
|---|---|
| **Game** | Game name from Steam or your shortcuts file |
| **App ID** | Steam's numeric identifier for the game |
| **Tool** | Name of the Proton build being used (e.g. `GE-Proton10-25`, `Proton 9.0`) |
| **Version** | Version tag read from the prefix `version` file |
| **Size** | On-disk size of the Wine prefix directory |
| **Confidence** | How certain we are about the tool mapping — see [Confidence levels](#confidence-levels-explained) |
| **Status** | OK · Warn · No Pfx · Orphan · Unused |

### Status values at a glance

| Status | Meaning |
|---|---|
| **OK** | Prefix exists and tool is installed — everything is healthy |
| **Warn** | Something needs attention (check the details panel below for specifics) |
| **No Pfx** | Proton tool is set but the Wine prefix folder has not been created yet (game has never been launched) |
| **Orphan** | A prefix folder exists but no matching game is installed — likely left over from an uninstalled game |
| **Unused** | A Proton tool is installed but no game is configured to use it |

The **details panel** at the bottom of the window shows the full evidence list and any
warnings for the currently highlighted row.

---

## Using the GUI

The interface is built with PySide6 (Qt) and features an OLED dark theme with true
black backgrounds.

### Tabs

Entries are grouped into three tabs:

- **Steam Games** — games from your Steam library
- **Shortcuts** — non-Steam games added through Steam (GOG, itch.io, emulators, etc.)
- **Orphans & Tools** — orphaned prefixes and unused Proton tools

### Toolbar

The toolbar at the top provides quick access to common actions:

- **⟳ Rescan** — re-run the full scan (also available via **F5**)
- **🔍 Filter** — type in the search box to filter rows by game name
- **🗑 Delete** — delete the selected entries (also available via **Delete** key)

### Menu bar

| Menu | Action | Shortcut |
|---|---|---|
| File | Rescan | F5 |
| File | Export JSON… | Ctrl+E |
| File | Quit | Ctrl+Q |
| Help | About | — |

### Keyboard shortcuts

| Key | What it does |
|---|---|
| **F5** | Re-run the full scan |
| **Ctrl+E** | Export currently visible entries to a JSON file |
| **Delete** | Delete the selected entry or entries |
| **Ctrl+Q** | Quit the application |

> **Steam Deck tip:** In desktop mode you can use the touch screen to interact with
> the table and buttons.

---

## Deleting an environment

Proton Cleanup can permanently remove a Wine prefix or an unused Proton tool.

**When would you want to do this?**

- A game is uninstalled but its prefix folder is still taking up space (marked **ORPHAN**)
- You have removed a custom Proton build but its folder in `compatibilitytools.d/` is
  still there (marked **UNUSED**)
- You want to reset a broken game environment so it gets rebuilt fresh next launch

### Deleting a single entry

1. Click on the row you want to remove in the table
2. Press **Delete** or click **🗑 Delete** in the toolbar
3. A confirmation dialog opens showing the game name, full path, and timestamps
4. Read the warning carefully — **this cannot be undone**
5. Click **Delete** to confirm
6. The row disappears from the table and the directory is gone

### Deleting multiple entries at once

1. Select multiple rows by holding **Ctrl** or **Shift** while clicking
2. Press **Delete** or click **🗑 Delete** in the toolbar
3. The confirmation dialog lists all selected entries
4. Click **Delete** to remove all of them in one go

Click **Cancel** to close the dialog without deleting anything.

### Safety limits

The deletion code includes a built-in safety check.  It will only delete directories
whose parent folder is named `compatdata` or `compatibilitytools.d`.  This prevents
any accidental deletion outside of the expected Steam directories, even if a
configuration file were somehow corrupted.

---

## Confidence levels explained

Because Steam stores tool assignments in several places (and some of those places are
optional), Proton Cleanup assigns a confidence score to each mapping:

| Level | Symbol | Meaning |
|---|---|---|
| **HIGH** | ● | The tool was set via an explicit CompatToolMapping override in `config.vdf` **and** the Wine prefix exists **and** the tool is installed locally |
| **MEDIUM** | ◑ | The tool was detected, but either the prefix does not exist yet or the tool isn't installed as a local directory (e.g. it is a stock Proton build managed by Steam) |
| **LOW** | ○ | The tool name was inferred from indirect evidence (e.g. a `config_info` binary file) with no explicit override |
| **UNKNOWN** | · | No Proton information found at all — the game may run natively on Linux, or it has simply never been launched |

Low confidence does **not** mean something is wrong; it just means less evidence was
available.  Many Linux-native games will correctly show **UNKNOWN** because they never
need Proton at all.

---

## Row types explained

| Icon | Type | Description |
|---|---|---|
| ◆ | **Steam** | A normal Steam library game read from an `appmanifest_*.acf` file |
| ◇ | **Shortcut** | A non-Steam game added manually through Steam (GOG, itch.io, emulators, etc.) |
| ◌ | **Orphan** | A Wine prefix directory in `compatdata/` with no matching installed game.  Usually left behind after uninstalling a game through Steam without letting Steam clean up. |
| ⚙ | **Unused Tool** | A Proton compatibility tool installed in `compatibilitytools.d/` that no currently-installed game is configured to use.  Safe to delete if you no longer need it. |

---

## Frequently asked questions

**Q: A game shows as ORPHAN but I still have it installed.  What happened?**

The App ID in the prefix folder does not match anything in your `steamapps/` manifests.
This can happen if you moved the game to a different library drive — the manifest is now
on the other drive, but the prefix stayed in the original location.  Re-running after
pointing Steam at all drives (press **F5** to rescan) should resolve it.

---

**Q: GE-Proton shows as UNUSED even though I use it for some games.**

The game is likely configured to use the tool by its internal registration name rather
than the directory name.  Check the **Details** pane for that game's row — the
evidence section will show exactly which name was resolved.  If the names differ
slightly (e.g. `GE-Proton10` vs `GE-Proton10-25`) the matching logic may not have
connected them.

---

**Q: The tool column shows `—` for a game I know uses Proton.**

The game's CompatToolMapping entry is missing or the tool was set globally rather than
per-game.  Try launching the game once through Steam, then press **F5** to rescan —
Steam writes the override when the game starts.

---

**Q: Is it safe to delete an ORPHAN prefix?**

Yes, in almost all cases.  The prefix is a self-contained folder that Steam will
recreate automatically if you reinstall the game.  Any game-specific save data stored
*inside* the prefix (rare — most games use Steam Cloud or your home folder instead)
would be lost, so check the evidence pane for warnings first.

---

**Q: Does this work with Heroic, Lutris, or other launchers?**

Partially.  If those launchers add the game as a non-Steam shortcut it will appear as
a **Shortcut** row.  Prefixes managed outside Steam entirely (in
`~/.wine` or a custom Heroic location) are not scanned.

---

**Q: Does this work on a regular Linux desktop (not Steam Deck)?**

Yes.  It works wherever Steam Linux is installed — native packages, Flatpak, or the
Steam Deck runtime.  Both install locations are detected automatically.

---

**Q: Can I export data for scripting?**

Yes — use **File → Export JSON** (Ctrl+E) to save the currently visible entries as a
JSON file.  You can then process it with `jq`, `python3`, or any other tool.

---

## For developers

### Project layout

```
proton-cleanup/
├── .github/
│   ├── agents/                        # GitHub Copilot custom agents
│   │   ├── coder.agent.md             # Coding agent (project-aware)
│   │   └── release-manager.agent.md  # Release manager agent
│   └── workflows/                     # CI and automated release
│       ├── ci.yml
│       └── release.yml
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
├── data/                          # Linux desktop integration assets
│   ├── io.github.protoncleanup.ProtonCleanup.desktop
│   ├── io.github.protoncleanup.ProtonCleanup.metainfo.xml
│   └── icons/
│       └── io.github.protoncleanup.ProtonCleanup.png
├── flatpak/                       # Flatpak build recipe
│   └── io.github.protoncleanup.ProtonCleanup.yaml
├── scripts/
│   └── build-flatpak.sh
├── src/proton_manager/            # Application source
│   ├── __init__.py
│   ├── __main__.py                # python -m proton_manager entry point
│   ├── cli.py                     # Entry point, scan pipeline, GUI launch
│   ├── delete.py                  # Deletion logic and safety checks
│   ├── model.py                   # Shared dataclasses (GameEntry, etc.)
│   ├── gui/                       # PySide6 (Qt) desktop GUI
│   │   ├── app.py                 # QApplication setup & OLED dark theme
│   │   ├── delete_dialog.py       # Confirmation dialog for deletions
│   │   ├── detail_panel.py        # Bottom panel: evidence & warnings
│   │   ├── game_table.py          # Table model & view for game entries
│   │   ├── main_window.py         # Top-level window, toolbar, menus
│   │   ├── tabs.py                # Tabbed view (Steam / Shortcuts / Orphans)
│   │   └── workers.py             # Background threads (scan, size calc)
│   └── scan/                      # Steam environment scanning modules
│       ├── config.py
│       ├── libraries.py
│       ├── orphans.py
│       ├── proton_tools.py
│       ├── shortcuts.py
│       ├── sizes.py
│       ├── steam_games.py
│       └── steam_roots.py
└── tests/                         # pytest suite
```

### Make targets

```bash
make dev       # Install in editable mode with dev dependencies
make test      # Run the test suite
make lint      # Run ruff linter
make format    # Auto-format with ruff
make flatpak   # Build a distributable Flatpak bundle
make clean     # Remove build artifacts
make help      # Show all available targets
```

### Running tests

```bash
make test
# or directly:
pytest -q          # run all 69 tests
pytest -v          # verbose output
pytest tests/test_delete_dialog.py   # one module only
```

### Building a distributable Flatpak

```bash
make flatpak
# or directly:
./scripts/build-flatpak.sh
```

The generated bundle is written to `dist/proton-cleanup.flatpak` and can be installed with:

```bash
flatpak --user install --bundle -y dist/proton-cleanup.flatpak
```

### Dependencies

| Package | Purpose |
|---|---|
| `PySide6-Essentials >= 6.7` | Qt desktop GUI framework (widgets, layouts, threading) |
| `vdf >= 3.4` | Parse Valve Data Format (`.acf`, `config.vdf`, `shortcuts.vdf`) |
| `pytest` | Testing (dev only) |

### Key data sources

| File | What we read from it |
|---|---|
| `steamapps/appmanifest_*.acf` | Game name, App ID, installed state |
| `config/config.vdf` → `CompatToolMapping` | **Authoritative** per-game Proton tool override |
| `compatibilitytools.d/*/compatibilitytool.vdf` | Names and versions of installed tools |
| `userdata/<uid>/config/shortcuts.vdf` | Non-Steam shortcut names and IDs (`binary_loads`) |
| `steamapps/compatdata/<id>/version` | Prefix Proton version string |
| `steamapps/compatdata/<id>/config_info` | Binary blob — Proton path regex extracted as fallback |
| `steamapps/libraryfolders.vdf` | Additional Steam library paths |

### Releasing a new version

1. Bump the version in `pyproject.toml`
2. Update `data/io.github.protoncleanup.ProtonCleanup.metainfo.xml` with a new `<release>` entry
3. Commit, tag, and push:

```bash
git commit -am "release: bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

The [release workflow](.github/workflows/release.yml) will automatically:
- Verify the tag matches the `pyproject.toml` version
- Run the test suite
- Build a Flatpak bundle in CI
- Create a GitHub Release with the `.flatpak` bundle attached

> **Tip:** Use the `@release-manager` Copilot agent in VS Code — it knows the full
> checklist and can run each step for you.
