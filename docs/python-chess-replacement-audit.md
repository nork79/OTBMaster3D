# Python-chess replacement audit

Audited 2026-09-17 against OTBMaster3D **8.4.0**, commit
`214935a44588cadfaaa0ec4c56d62127dac06e46`. This is a read-only design audit:
no migration, dependency removal, or application behaviour changes were made.
See [candidate evaluation](chess-backend-candidate-evaluation.md) for sources,
candidate limitations and the recommended architecture.

## Scope and findings

The runtime requirement is `chess==1.11.2`. Direct third-party imports in
application code are confined to four modules in `otb_chess/chess_backend/`:
`rules.py`, `notation.py`, `uci.py`, and `books.py`. These re-export provider
objects; they are import boundaries, not independent interfaces. The existing
import-isolation test passes but cannot detect native objects crossing the boundary.

The inventory below covers application callers, tests, build tooling and
distribution metadata. Difficulty describes replacing the behaviour, not merely
changing an import. Paths are relative to the repository root.

## Usage inventory

| Area | Where used | Behaviour needed | Difficulty | Likely replacement |
| --- | --- | --- | --- | --- |
| Rules / legal move generation | `chess_backend/rules.py`; `core/game.py`: initialization, `legal_targets`, `try_move`, takeback/reset/start, pending engine moves; `core/board_input.py`: selection/drag; `graphics/rendering.py`: pieces and castling animation; `core/documents.py`: history navigation | Legal-move iteration and membership, source/destination/promotion, piece lookup and maps, side to move, captures including en passant, orthodox castling, all promotion moves at the provider boundary, push/pop/reset/copy/root and full move stack | large | cozy-chess legal core behind an application Board adapter; retain snapshots/history in the adapter, never implement move generation locally |
| FEN | `core/documents.py`: `read_fen`, root comparisons; `ui/document_actions.py`: open/save/copy/paste; `core/game.py`: stale engine result checks and animation identity; `services/engine.py`: search positions; `ui/desktop_ui.py`: analysis, PV replay, tick; `graphics/rendering.py`: animation invalidation; `services/session.py`: PGN-embedded FEN roots | Validate positions, preserve side/castling/en-passant and both counters, represent arbitrary roots, use consistent canonical FEN for comparisons; preserve valid long-game counters | medium | cozy-chess parsing/formatting plus counter and canonicalization adapter; upstream limits require explicit handling |
| SAN | `ui/desktop_ui.py`: `refresh_moves`, `show_engine_info`; `ui/legacy_ui.py`: `refresh_move_list`; PGN parsing/export via `core/documents.py` | Correct disambiguation, captures, check/mate suffixes, castling, promotion and SAN parsing for imports; render from the position before each move | medium | Application notation adapter using the legal core; rschess has native SAN if selected instead |
| PGN | `chess_backend/notation.py`; `core/documents.py`: `read_pgn`, `load_document`, `export_pgn`; `ui/document_actions.py`: multi-game selection and named PGN files; `services/session.py`: save/decode/restore | Headers, comments, recursive variations, main line, parser errors, results, SetUp/FEN roots, black-to-move numbering, multiple games; lossless semantic round trips of unchanged imported documents | large | Independent document tree and PGN parser/writer, using SAN adapter for legality; neither candidate is a verified full substitute |
| UCI engine handling | `chess_backend/uci.py`; `services/engine.py`: load/unload/request worker; `ui/desktop_ui.py`: `DesktopGame.request_analysis`, engine output and settings; `core/game.py`: scheduling and pending move application | Start external executable, handshake/readiness, finite play and analysis limits (currently 0.12/0.25 seconds), result moves, PV, depth, centipawn/mate scores with White POV, worker locking, stale-result rejection, errors and process cleanup | large | Application-owned UCI process adapter with plain move/evaluation records; candidate UCI move notation APIs are not engine-process clients |
| Polyglot books | `chess_backend/books.py`; `core/game.py`: `pick_book_move`, `maybe_request_engine_move` | Context-managed binary book lookup by board, legal matching entries with move/weight; preserve weighted selection and silent no-book/invalid-book fallback | medium | Independent Polyglot reader/hash adapter based on a separately verified specification and permissive data provenance |
| Draw/check/mate logic | `core/game.py`: check sound and `update_game_end`, `resign`, `offer_draw`; `core/clocks.py`: timeout; PGN result inference in `notation.Game.from_board` | Current automatic endings are checkmate, stalemate and insufficient material; check detection for audio; resignation/timeout are app state. Preserve export results separately from GUI status | medium | Legal core for check/mate/stalemate; narrowly scoped material/repetition adjudication adapter where needed; preserve existing policy |
| Shared types/constants | `chess_backend/rules.py`, `values.py`; `core/game.py`, `documents.py`; `ui/desktop_ui.py`, `legacy_ui.py`; indirect objects in `board_input.py`, `clocks.py`, `graphics/rendering.py`, `piece_sets.py`, `board_2d.py` | Board/Move/Piece API and equality; square integers a1=0..h8=63, Boolean colours, piece codes 1..6; renderers only need colour/type | small | Keep application-owned `values.py`; introduce small immutable Move/Piece records and a Board wrapper; no native Rust/PyO3 objects in UI |
| Tests | `tests/test_chess_backend.py`, `test_documents.py`, `test_desktop_ui.py`, `test_piece_sets.py`, `fixtures/uci_stub.py` | Contract, import isolation, notation, rendering, history, persistence, engine worker and protocol regression coverage | large | Convert fixtures to application records, add independent expected-position/protocol fixtures and legality/perft coverage before switching |

All unqualified runtime paths in this table begin with `otb_chess/`.

## Native types leaking out of the boundary

- **Board:** `Chess3D.board`, `GameDocuments._review_live`, history copies,
  engine-worker snapshots, animation tuples, and PGN node `.board()` results.
  Controller, input, rendering, clocks, session and UI call native methods or
  inspect `turn`, `fullmove_number`, and `move_stack` directly.
- **Move:** `legal_moves`, `move_stack`, pending engine/book moves, PV entries and
  PGN `mainline_moves()` expose native instances. Membership/equality and
  `from_square`, `to_square`, `promotion` are implicit contracts.
- **Piece:** `piece_at`/`piece_map` results flow directly into both renderers and
  pointer logic; consumers inspect `.color` and `.piece_type`.
- **PGN Game/GameNode/Headers/exporter:** `read_pgn` returns native documents;
  `_pgn_document` stores them. UI reads headers and calls `end().board()`;
  documents use `errors`, `root board`, `mainline_moves`, `accept`, and exporter
  flags. Session recovery relies on this tree and its mainline reconstruction.
- **Engine:** `EngineManager.engine` is a native `SimpleEngine`; play results
  carry `.move` and `.info`. UI uses native `Limit` and `PovScore`/`Score`
  methods (`white`, `is_mate`, `mate`, `score`). Engine info dictionaries also
  contain native moves in `pv`.
- **Books:** `open_reader()` accepts a native board; entries with `.move` and
  `.weight` escape directly into `core/game.py`.
- **Not a leak:** `values.py` defines its own integers/Booleans/functions.
  Importing it as `chess` in graphics and clocks does not import python-chess,
  although native Board/Piece objects still reach those modules as arguments.

## Behaviour traps to preserve, not silently fix

1. `try_move` currently automatically queens a last-rank pawn. Pending engine
   moves are reapplied using only source/destination, losing underpromotion
   identity. Provider tests exercise underpromotion, but the UI path differs.
   Record this as a separate future bug; a replacement must not conceal it.
2. The controller does not call repetition, fifty/seventy-five-move, fivefold or
   claim-draw APIs. `offer_draw` only changes a message. Python-chess PGN result
   inference can nevertheless observe board outcomes, so export semantics need
   explicit fixtures rather than assuming the controller is the entire policy.
3. Qt move-list reconstruction uses `history.root()` and respects FEN roots;
   legacy `refresh_move_list` starts from the ordinary initial board. Do not
   treat the legacy method as the specification for loaded positions.
4. Review must leave the complete live history intact. Session version 1 stores
   PGN, reviewed ply, clocks and status; existing session files must remain readable.
5. Board validity and canonical FEN equality affect imports, engine-result
   rejection and animation. A different en-passant formatting policy can change
   behaviour even when piece placement is identical.

## Tests and non-runtime dependencies

- `test_chess_backend.py` imports only the boundary but still exercises native
  objects. Its AST test finds direct imports, not transitive coupling.
- `test_documents.py` directly constructs `chess.Board`, uses square/FEN constants
  and pushes UCI moves.
- `test_desktop_ui.py` imports `chess` and `chess.engine`, constructs native
  boards/moves and score objects, and starts `SimpleEngine` against the fixture.
- `test_piece_sets.py` directly uses Board, Piece, Move, square constants and
  collections for rendering/input tests.
- `fixtures/uci_stub.py` imports chess for position reconstruction and legal move
  selection. A test-only dependency remains a dependency to remove from a future
  clean migration test environment; do not ship this as the replacement engine.
- `tools/import_diagram_pieces.py` reads the local `chess/svg.py` artwork
  dictionary through AST extraction. This is build-time asset provenance, not
  rules code. The Cburnett artwork has separately recorded BSD licensing; verify
  that chain independently and later source artwork without a python-chess install.
- `requirements.txt`, `tools/audit_dependencies.py`, `third_party_bom.json`,
  `THIRD_PARTY_NOTICES.md`, `licenses/chess/LICENSE.txt`, distribution docs and
  CI installation all need review at eventual removal. No dependency or notice
  was removed in this audit.

## Full baseline test result

Command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Environment: Windows 11 build 26200, AMD64; CPython **3.14.7**, MSC v.1944;
existing project virtual environment and native OpenGL display. Run date:
2026-09-17. **37 tests run in 29.975 seconds: 36 passed, 1 failed, no errors or
skips reported; exit code 1.** This was the full suite, not the 11-test CI subset.

Failure: `test_piece_sets.LiveSwitchTests.test_switching_renders_and_preserves_game_and_persists`,
`tests/test_piece_sets.py:151`: expected `len(app.piece_renderer.cache) == 2`,
observed `3`. Inspection shows the test cycles through all sets but still assumes
only two geometry caches. The added Sci-fi Vehicles set explains the extra cache;
this is an evidence-based diagnosis, not a fix performed here.

Non-fatal warnings: optional NumPy OpenGL handler unavailable; python-chess engine
uses `asyncio.iscoroutinefunction`, deprecated for removal in Python 3.16.

Missing migration assurance: broad perft/legality corpus, long-counter FEN cases,
repetition/claim semantics, Polyglot known hashes, adversarial PGN trees, UCI
timeouts/malformed output and a clean Windows wheel/frozen-build test. The current
passing tests alone cannot certify a replacement.
