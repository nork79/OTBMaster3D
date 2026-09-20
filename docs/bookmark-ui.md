# Bookmark panel

Open **Bookmarks → Manage Bookmarks** or press **Ctrl+Shift+B**. The panel is a modeless
PySide6 `QDialog` with the `Qt.Tool` flag. It floats over the board and does not
participate in the main splitter or change board dimensions. Close or Escape
hides it; the management action stays in sync. The shortcut also works while the tool
window has focus.

The panel defaults to 205 logical pixels wide, half the Time Control dialog width.
Default height is 80% of the main window, minimum size 205 ? 220. The first
opening is positioned immediately left of the main controls, clamped to the
current screen. Native movement and resizing are supported. Position and size
are saved with application preferences and restored across restarts, clamped
to the available screen. Existing settings without saved geometry use the defaults.

The top-level Bookmarks menu also offers Add Bookmark and New Folder through
the panel actions. Its nested folder menus rebuild from the authoritative model
on every opening, preserving child order and empty folders. Bookmark entries
use the same restoration path as the panel.

Inline editing uses a dedicated delegate with font-aware compact row heights
and no vertical input padding, avoiding the global dialog input padding that
clipped text.

## Actions

The `+` and `Folder` buttons create in the selected folder, the selected
bookmark's parent, or root if nothing is selected. Creation saves immediately,
selects/reveals the new item and enters inline naming. Enter commits a trimmed
nonblank name; Escape cancels. F2 and context menus also rename. Single click
only selects; double click or Enter opens a bookmark. Folders expand/collapse
normally. Tree items store UUIDs, preserve model child ordering, and use a
single selection. Long names elide without widening the window; the tree scrolls.

Click empty tree space to clear selection and create at the invisible root.
Drag items onto folders to append, between rows to insert/reorder, or onto empty
tree space to move to root. Moves save through the transactional model service
before rebuilding the tree; ordering survives restart and appears in the menu.
Bookmarks cannot contain children, and the model rejects folder cycles.

Right-click selects the target before offering the appropriate bookmark,
folder, or empty-area menu. Delete is available by menu or key. Nonempty folders
ask for explicit confirmation that their entire subtree will be removed.

`BookmarkActions` clones the existing collection, applies the model operation,
and publishes it only after the existing atomic store saves successfully. Failed
saves leave both the visible collection and previous file unchanged. A file that
could not load is not silently overwritten by a UI edit; an error explains that
the source needs recovery. All data continues to use `bookmarks.json` beside the
application configuration, with no bookmark schema redesign.

## Opening and engine restoration

Opening validates the authoritative FEN first, pauses clocks, disables board/game
controls briefly, and requests UCI stop. Existing search, analysis, and engine-load
workers are allowed to finish before their pending results are discarded. A
background worker prepares the saved engine, so the panel remains responsive.
The selected position is installed only after that worker completes. The
previous engine remains alive until a candidate engine is successfully verified.

The engine loader uses the saved stable family ID, exact Maia weights/model and
mistake rate, or UCI options. It verifies identity and, when supplied, the stable
configuration/profile fingerprint. It never chooses the nearest Maia rating.
Unsupported configuration systems, missing personality resources, changed
options, or mismatching fingerprints produce a nonfatal diagnostic. The current
engine is retained; if none exists, bundled Stockfish is tried explicitly as a
fallback. The message states the substitution. If neither exists, the chess
position remains usable with no engine.

On the UI thread, restoration uses the existing FEN/history restoration and
document loader, applies semantic White/Black facing, restores preset/custom
base and increment values and clock mode, and refreshes board, move list,
clocks, difficulty controls, status, and session recovery. Clocks remain paused;
Resume continues the loaded position/history rather than resetting the board.
Analysis resumes only if it was enabled before opening. A missing saved engine
does not prevent position, facing, or time restoration. No camera orbit/zoom,
theme, pieces, colours, or sound profile is copied from the bookmark. Flipping
the semantic side uses the existing board-flip operation.

Delay configurations can be stored by the data layer, but current application
clocks have no delay implementation; opening such a bookmark reports that limit.
Older bookmarks with no time-control snapshot retain current clock settings.

## Verification

`tests/test_bookmark_ui.py` exercises destination rules, transactional edits and
save failures, rename validation, deletion, FEN/facing/time restoration, missing
engines, exact Stockfish and Maia configuration round trips, native tree events,
inline edit/cancel, confirmation, selection-only clicks, double click/Enter,
scrolling, long names, context selection, stale search results, panel geometry,
and ordinary board interaction after restoring. Run the full suite in Python 3.13:

```powershell
.\.venv-test\Scripts\python.exe -m unittest discover -s tests -v
```

Native Tk/OpenGL tests need desktop access outside a restrictive sandbox. Native
Qt visual checks were also exercised in an isolated temporary configuration and
captured for both White- and Black-facing positions.

Search, metadata, tags, annotations, thumbnails,
properties, and multiple selection remain intentionally absent. Engine-family adapters beyond the current UCI/Maia setup remain outside this release.
