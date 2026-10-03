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

## Opening bookmarks

Opening validates the authoritative FEN first, pauses clocks, disables board/game
controls briefly, and requests UCI stop. Existing search, analysis, and engine-load
workers finish before their pending results are discarded.

Restoration applies the saved position, move history, and semantic White/Black
facing. The current engine, difficulty, personality, engine side, time control,
clock mode, increment, and remaining times stay unchanged. Older engine snapshots
and saved time controls do not affect restoration. Saving no longer captures an
engine configuration; time-control metadata remains stored.

The board, move list, clocks, status, and session recovery refresh. Clocks remain
paused; Resume continues the loaded position/history. Analysis resumes only if
it was enabled before opening. Camera orbit/zoom and appearance are not restored.

## Verification

`tests/test_bookmark_ui.py` exercises destination rules, transactional edits and
save failures, rename validation, deletion, FEN/facing restoration, preserving
current engine and clock settings, legacy snapshots, native tree events,
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
properties, and multiple selection remain intentionally absent. Engine-family adapters beyond the current two-engine UCI setup remain outside this release.
