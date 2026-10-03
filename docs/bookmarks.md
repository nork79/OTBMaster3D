# Bookmark model and persistence

This model layer is UI-independent; the floating panel and live restoration are
described in [bookmark-ui.md](bookmark-ui.md).
`otb_chess.bookmarks.BookmarkCollection` owns the tree and exposes
`create_folder`, `create_bookmark`, `rename`, `delete`, `move`, and `reorder`.
Creation returns a UUID string. `get` and `to_dict` return independent copies.
The root UUID is available as `root_id`; root deletion and movement are forbidden.
Deleting a folder deletes its subtree. Move indices refer to the final child list
after removing the source. Reorder requires an exact permutation of the children.
Tree traversal and storage are iterative, without a folder-depth limit.

## Capture and storage

```python
from otb_chess.bookmarks import (
    capture_position, capture_facing, capture_time_control,
)
from otb_chess.services.bookmarks import BookmarkStore

store = BookmarkStore()
collection = store.load()
# game is the current controller.
control = game.selected_time_control()
if control is not None:
    item_id = collection.create_bookmark(
        collection.root_id, "My position", capture_position(game.board),
        facing=capture_facing(game),
        time_control=capture_time_control(control, game.clock_mode),
    )
    saved = store.save(collection)  # bool; store.error contains any failure
```

Storage is `settings.CONFIG_PATH.with_name("bookmarks.json")`: the project
directory when running from source, or `%LOCALAPPDATA%/OTBMaster3D/bookmarks.json`
for packaged Windows builds. Mutations are explicit in-memory operations; call
`save` to commit them. Save writes a uniquely named temporary file in the same
directory, flushes and fsyncs it, then atomically replaces the destination.
Failed writes leave the old collection intact. This is a single-writer store;
concurrent writers are not merged.

## JSON schema 1

The flat node table avoids JSON nesting limits while child UUID arrays preserve
folder ordering. Example (UUIDs and FEN abbreviated for readability):

```json
{
  "schema_version": 1,
  "root_id": "<root UUID>",
  "nodes": [
    {"id": "<root UUID>", "type": "folder", "name": "Bookmarks", "children": ["<bookmark UUID>"]},
    {
      "id": "<bookmark UUID>", "type": "bookmark", "name": "My position",
      "created_at": "2026-09-19T00:00:00+00:00",
      "modified_at": "2026-09-19T00:00:00+00:00",
      "position": {"representation": "fen-history", "fen": "<six-field FEN>", "root_fen": "<root FEN>", "moves": ["e2e4"]},
      "facing": "white",
      "time_control": {"preset_name": "Custom", "base_seconds": 300,
                       "increment_seconds": 2, "delay_seconds": 0,
                       "clock_mode": "Online", "settings": {}}
    }
  ]
}
```

FEN carries side to move, castling rights, raw en-passant target, and both move
counters. FEN is authoritative and validated first. Root FEN plus UCI moves are
optional and preserve repetition history only if replay matches the complete
FEN, including raw en-passant and counters. Missing, malformed, illegal, or
mismatching history logs a diagnostic and falls back to the FEN-only board;
it does not discard an otherwise valid bookmark. Invalid FEN is rejected even
if history is valid. `restore_position` constructs an independent board; it never changes
live state or starts clocks. The UI restoration coordinator explicitly pauses
game clocks before changing the live position. The production provider is currently python-chess, behind
`chess_backend.rules`; the separate `otb_chess_core.Board` has a different FEN API
and is not the live provider. A provider migration must adapt these two helpers.

Only semantic White/Black facing is captured through `BoardInput.board_facing`.
In 2D this uses `two_d_flipped`; in 3D a separate `_three_d_facing` value is
changed by Flip/Reset. Free camera orbit never changes that selection, including
when it crosses either side of the board. `set_board_facing` changes the semantic
side idempotently using the existing flip operation. Each view retains its own
facing across mode changes, as before. No yaw or other camera/appearance state
is serialized; 3D starts facing White, matching existing startup behavior.

Bookmarks do not capture or restore engines or engine settings. Opening a bookmark
keeps the current engine, difficulty, personality, and engine side. Legacy engine
snapshots are ignored on load and omitted on the next save.

Time-control snapshots remain stored as metadata, but opening a bookmark keeps
the current time control, clock mode, increment, and remaining times. Clocks pause
when the position is opened.

## Recovery and extensions

Missing optional time-control values become null (unknown/unconfigured),
facing defaults to White, and absent timestamps are synthesized. Unknown fields
on valid nodes and the collection are retained across round trips, providing
room for future annotations, analysis, tags, and other extensions.

Malformed individual nodes, dangling edges, cycles, multiple parents, duplicate
nodes, and unreachable nodes are logged and discarded; valid reachable nodes
survive. The first valid UUID and first reachable parent win. A missing valid
root, malformed JSON, or unsupported schema returns an empty collection with
`store.error` and a warning. Loading never overwrites the source file. Callers
should surface that error before explicitly saving a replacement collection.

Engine availability is not checked when loading bookmarks. Future schema versions
require an explicit migration; this version does not guess their meaning.
