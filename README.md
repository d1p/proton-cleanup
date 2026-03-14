# Proton Cleanup

A terminal app for **Steam Deck** and any **Linux desktop** that answers one question:

> *Which Proton compatibility layer is each of my games actually using — and is everything set up correctly?*

It scans your Steam library, non-Steam shortcuts, installed Proton tools, and Wine
prefixes, then shows everything in an interactive table you can search, sort, and act on.

---

## Contents

1. [What is Proton?](#what-is-proton)
2. [What does this tool do?](#what-does-this-tool-do)
3. [Quick Start: Download Pre-built Releases](#quick-start-download-pre-built-releases)
4. [Installation](#installation)
5. [Flatpak package (no Python setup)](#flatpak-package-no-python-setup)
6. [Launching the app](#launching-the-app)
7. [Understanding the table](#understanding-the-table)
8. [Using the TUI (keyboard guide)](#using-the-tui-keyboard-guide)
9. [Deleting an environment](#deleting-an-environment)
10. [Command-line flags](#command-line-flags)
11. [JSON output for scripting](#json-output-for-scripting)
12. [Confidence levels explained](#confidence-levels-explained)
13. [Row types explained](#row-types-explained)
14. [Frequently asked questions](#frequently-asked-questions)
15. [For developers](#for-developers)

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

Results are shown in an interactive full-screen table.  You can search, sort, filter
by type, and delete entries you no longer need — all without opening a file manager or
running manual `rm` commands.

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

The full-screen TUI opens immediately and begins scanning.  On a typical Steam Deck
with 50–100 games the scan finishes in under a second.

To exit cleanly, press **`q`** or **`Ctrl+C`**.

---

## Understanding the table

Each row represents one game, shortcut, orphaned prefix, or unused tool.  The columns are:

| Column | What it shows |
|---|---|
| **Game** | Game name from Steam or your shortcuts file |
| **Kind** | ◆ Steam · ◇ Shortcut · ◌ Orphan · ⚙ Unused Tool |
| **App ID** | Steam's numeric identifier for the game |
| **Tool** | Name of the Proton build being used (e.g. `GE-Proton10-25`, `Proton 9.0`) |
| **Version** | Version tag read from the prefix `version` file |
| **Prefix** | Path to the Wine prefix directory (`~/` paths are shortened) |
| **Confidence** | How certain we are about the tool mapping — see [Confidence levels](#confidence-levels-explained) |
| **Status** | ✓ OK · ⚠ WARN · □ NO PFX · ? ORPHAN · ⊘ UNUSED |

### Status icons at a glance

| Icon | Status | Meaning |
|---|---|---|
| ✓ | **OK** | Prefix exists and tool is installed — everything is healthy |
| ⚠ | **WARN** | Something needs attention (check the details pane below for specifics) |
| □ | **NO PFX** | Proton tool is set but the Wine prefix folder has not been created yet (game has never been launched) |
| ? | **ORPHAN** | A prefix folder exists but no matching game is installed — likely left over from an uninstalled game |
| ⊘ | **UNUSED** | A Proton tool is installed but no game is configured to use it |

The **details pane** at the bottom of the screen shows the full evidence list and any
warnings for the currently highlighted row.

---

## Using the TUI (keyboard guide)

You do not need a mouse.  Every action is a single key press.

| Key | What it does |
|---|---|
| **↑ / ↓** | Move the selection up or down one row |
| **Space** | Toggle selection on the highlighted row (for multi-select deletion) |
| **/** | Open the search bar — start typing a game name to filter |
| **Escape** | Close the search bar (and clear it) · also closes any open dialog |
| **s** | Cycle sort: press once to sort ascending, again for descending, again for the next column |
| **o** | Toggle the display of orphaned prefixes and unused tools on/off |
| **d** | Delete the highlighted row, or all selected rows if any are marked with Space |
| **r** | Re-run the full scan (useful after installing or removing a game) |
| **e** | Export the currently visible rows to `proton-cleanup-export.json` in the current folder |
| **?** | Open the on-screen keyboard shortcut reference |
| **q** | Quit |

> **Steam Deck tip:** In desktop mode you can use the touch screen to scroll the table.
> The on-screen keyboard works for the search bar.

---

## Deleting an environment

Proton Cleanup can permanently remove a Wine prefix or an unused Proton tool.

**When would you want to do this?**

- A game is uninstalled but its prefix folder is still taking up space (marked **ORPHAN**)
- You have removed a custom Proton build but its folder in `compatibilitytools.d/` is
  still there (marked **UNUSED**)
- You want to reset a broken game environment so it gets rebuilt fresh next launch

### Deleting a single entry

1. Use **↑ / ↓** to highlight the row you want to remove
2. Press **`d`**
3. A confirmation dialog opens showing the game name, full path, and timestamps
4. Read the warning carefully — **this cannot be undone**
5. Click **⚠ Delete** (or press **Enter**) to confirm
6. The row disappears from the table and the directory is gone

### Deleting multiple entries at once

1. Navigate to a row and press **`Space`** to mark it — a `☑` appears in the Game column
2. Move to other rows and press **`Space`** to mark them too
3. Press **`d`** — the confirmation dialog lists all marked entries
4. Click **⚠ Delete** to remove all of them in one go

Marked rows show `☑`; unmarked rows show `☐`.  Pressing **`Space`** again on a marked
row deselects it.  If no rows are marked when you press **`d`**, the highlighted row is
used (single-entry behaviour).

Press **Escape** or click **Cancel** to close the dialog without deleting anything.

### Safety limits

The deletion code includes a built-in safety check.  It will only delete directories
whose parent folder is named `compatdata` or `compatibilitytools.d`.  This prevents
any accidental deletion outside of the expected Steam directories, even if a
configuration file were somehow corrupted.

---

## Command-line flags

You can customise behaviour without entering the TUI by passing flags to
`proton-cleanup`:

| Flag | Description |
|---|---|
| `--steam-root PATH` | Override the auto-detected Steam root (useful for non-standard install locations) |
| `--json` | Print results as JSON and exit — no TUI opened |
| `--only-steam` | Show only Steam library games (hide shortcuts, orphans, unused tools) |
| `--only-shortcuts` | Show only non-Steam shortcuts |
| `--hide-orphans` | Hide orphaned prefixes and unused Proton tools |
| `--min-confidence LEVEL` | Hide entries with a confidence below `HIGH`, `MEDIUM`, or `LOW` |
| `--version` | Print the version number and exit |
| `--help` | Print a brief help message and exit |

### Examples

```bash
# Just see your Steam games with HIGH confidence
proton-cleanup --only-steam --min-confidence HIGH

# Find all orphaned prefixes without opening the TUI
proton-cleanup --json | python3 -m json.tool | grep -A5 '"kind": "Orphan"'

# Use a custom Steam root (e.g. external drive)
proton-cleanup --steam-root /run/media/deck/SSD/Steam
```

---

## JSON output for scripting

`--json` prints a JSON array to stdout.  Each object has these fields:

```jsonc
{
  "app_id": "1091500",               // Steam App ID (or "tool:<name>" for unused tools)
  "name": "Cyberpunk 2077",
  "kind": "Steam",                   // "Steam" | "Shortcut" | "Orphan" | "Unused Tool"
  "proton_tool": "GE-Proton10-25",   // null if unknown
  "proton_version": "10-25",         // null if not found
  "prefix_path": "/home/deck/.steam/root/steamapps/compatdata/1091500",
  "prefix_exists": true,
  "tool_installed": true,
  "confidence": "HIGH",              // "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
  "evidence": [                      // list of strings explaining how the mapping was found
    "CompatToolMapping override: GE-Proton10-25",
    "Prefix exists: /home/deck/..."
  ],
  "warnings": []                     // non-fatal issues found during scanning
}
```

Combine with `jq` for easy filtering:

```bash
# List all games not using GE-Proton
proton-cleanup --json | jq '.[] | select(.kind=="Steam") | select(.proton_tool | test("GE") | not) | .name'

# Find every orphaned prefix and how big it is
proton-cleanup --json | jq -r '.[] | select(.kind=="Orphan") | .prefix_path' \
  | xargs -I{} du -sh {}
```

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
pointing Steam at all drives (`r`) should resolve it.

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
per-game.  Try launching the game once through Steam, then press **`r`** to rescan —
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

**Q: Can I run this without the TUI (e.g. in a script or cron job)?**

Yes — use `--json` and pipe the output to `jq`, `python3`, or whatever you like.
No terminal interaction is needed, no interactive input is required.

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
│   ├── cli.py                     # argparse entry point + scan pipeline
│   ├── model.py                   # Shared dataclasses
│   ├── output.py                  # Table-row adapter and JSON serialisation
│   ├── scan/                      # Steam environment scanning modules
│   │   ├── config.py
│   │   ├── libraries.py
│   │   ├── orphans.py
│   │   ├── proton_tools.py
│   │   ├── shortcuts.py
│   │   ├── steam_games.py
│   │   └── steam_roots.py
│   └── tui/                       # Interactive terminal UI (Textual)
│       ├── app.py
│       ├── delete_dialog.py
│       └── widgets.py
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
| `textual >= 0.82.0` | Full-screen TUI framework (widgets, CSS, themes) |
| `vdf >= 3.4` | Parse Valve Data Format (`.acf`, `config.vdf`, `shortcuts.vdf`) |
| `pytest` + `pytest-asyncio` | Testing (dev only) |

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
