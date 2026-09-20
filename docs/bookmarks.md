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
    capture_position, capture_engine, capture_facing, capture_time_control,
)
from otb_chess.services.bookmarks import BookmarkStore

store = BookmarkStore()
collection = store.load()
# game is the current controller; manager is its EngineManager.
control = game.selected_time_control()
if control is not None:
    item_id = collection.create_bookmark(
        collection.root_id, "My position", capture_position(game.board),
        facing=capture_facing(game), engine=capture_engine(manager),
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
      "engine": {
        "engine_id": "maia", "name": "Lc0", "profile": "club_1500",
        "profile_id": "maia:profile:v1:<configuration SHA-256>",
        "executable": "<lc0 executable>", "elo": null, "rating": 1500,
        "style": "Balanced", "side": "Black",
        "settings": {"model": 1500, "weights_path": "<maia-1500.pb.gz>", "mistakes": 0.0,
                     "backend": "blas", "threads": 1, "minibatch_size": 1, "uci_options": {"Threads": 1}}
      },
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

Engine settings are an opaque JSON object, so personalities, profiles, model
files, UCI options, and future non-UCI configuration can differ between engines.
`engine_id` and `name` are required for a non-null engine; other engine fields
are optional. Capture records Maia's actual loaded model, even if the selected
difficulty has since changed, and persistent UCI options (not temporary analysis
overrides). Style, requested strength, rating, and engine side come from the
controller settings used for searches. Capture holds the manager lock and may
wait for an active search to finish.

`engine_identity.py` establishes fixed family IDs `stockfish`, `maia`, and
`rodent`. Stockfish/Rodent are recognized from the engine's UCI-reported family
name, not its executable filename. Maia is identified by its model loader.
Unrecognized engines use `uci:sha256:<binary digest>`; moving or renaming an
executable leaves its identity intact. An unknown engine binary upgrade creates
a new identity; callers with a registry can supply a persistent engine ID.

New captures include a `profile_id` of
`<engine_id>:profile:v1:<canonical-settings SHA-256>`. Model, mistakes, persistent
UCI options, requested Elo, and style determine this ID; display names, preset
labels, executable locations, and engine side do not. Standard Maia model IDs
exclude the weights location. Other existing resource files (such as Rodent
personalities) are hashed by content, so relocation preserves profile identity.
Changed settings produce a different profile ID. The full configuration is
still stored and is needed for recreation; the digest is only an identifier.
Saved IDs are preserved verbatim when resources are unavailable. Older bookmarks
without profile IDs still load without guessing an unavailable configuration.

The UI engine adapter restores persisted UCI options (including a Rodent
personality file when the engine exposes one); unsupported configuration systems
produce a nonfatal fallback. No engine-specific settings are applied by the model
itself. Stockfish styles
currently use the names Balanced, Active, and Quiet. Maia presets do not
currently include 1900, but the format permits any model/strength configuration.

Time controls preserve resolved base/increment values and preset/custom name,
plus clock mode and optional custom settings. Delay is supported by the model,
but current application clocks only implement increments. Optional future
remaining times can be added as a separate bookmark field (for example
`clock_snapshot`); this version neither captures nor resumes running clocks.

## Recovery and extensions

Missing optional engine/time-control values become null (unknown/unconfigured),
facing defaults to White, and absent timestamps are synthesized. Unknown fields
on valid nodes and the collection are retained across round trips, providing
room for future annotations, analysis, tags, and other extensions.

Malformed individual nodes, dangling edges, cycles, multiple parents, duplicate
nodes, and unreachable nodes are logged and discarded; valid reachable nodes
survive. The first valid UUID and first reachable parent win. A missing valid
root, malformed JSON, or unsupported schema returns an empty collection with
`store.error` and a warning. Loading never overwrites the source file. Callers
should surface that error before explicitly saving a replacement collection.

The default engine resolver checks executable and Maia weights paths. Missing
resources generate warnings but the complete engine configuration remains
saved. `load(engine_available=resolver)` allows a future registry to additionally
check profiles/personality resources. `None` disables checks. No fallback engine
is silently substituted. Future schema versions require an explicit migration;
this version does not guess their meaning.
