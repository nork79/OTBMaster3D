# Chess core architecture preparation

## Current boundary

Preparation is complete; physical extraction and provider replacement have not
been performed. Production flow is:

```text
Qt / legacy UI / rendering
    -> Chess3D and application-controller mixins
    -> chess_backend.position.ChessPosition
    -> rules / notation adapters
    -> python-chess
```

Some consumers still use the native-board compatibility paths listed below.
The separate `otb_chess_core.Board` remains an unused experimental cozy-backed
implementation. Only its existing owned `Move`/`Piece` vocabulary is used by the
production facade. No production rules provider or dependency was replaced.

## Responsibilities and ownership

`ChessPosition` provides legal moves/targets, move validation and application,
undo, promotion choices, capture/castling move details, turn, owned piece values,
check/checkmate/stalemate/material status, castling/en-passant state, SAN/UCI,
FEN, PGN-compatible history and annotation-preserving PGN import/export. It also
supplies independent variation positions and captured-material data.

`termination()` delegates to the `rules.py` application policy: automatic
checkmate, stalemate, insufficient material, threefold repetition and 50-move
draws. Draws depend on the position reached by actual moves, not a possible next
move. There is no claim-draw action. `loss_outcome()` centralizes resignation/timeout
material adjudication; the application still decides when those events occur.

`GameDocuments.position` holds the facade for the currently displayed controller
board. Its `board` property aliases exactly `position.legacy_board`; assigning a
replacement board rebinds the facade. `from_board(copy=False)` borrows, rather
than clones, an existing board. There is no second mutable position/history.
`from_fen()`/`set_fen()` validate imported positions; the constructor and explicit
legacy bridge retain the provider's ability to represent incomplete positions.

During review, `_review_live` retains the authoritative live board while the
controller displays a copy at an earlier ply. `history_position()` uses that live
board for export. Variation previews also use independent copies. Board identity
remains significant for animation, stale-result checks and clock restoration.

Rule-derived outcomes are calculated from the board. Application fields
`game_started`, `game_over`, `_declared_result` and `result_text` remain outside
the facade for claims, imported results, resignation, timeout and UI status.
TODO: eventually consolidate them in a game-session record; replacing them with
board termination alone would lose valid application outcomes.

## FEN and transfer contracts

- Engine play/analysis calls use `history()` with normalized FEN: the en-passant
  field is present only when a legal capture exists (`en_passant='legal'`). The
  snapshot includes root FEN and every move, preserving repetition context.
- Bookmarks use `history(raw_ep=True)` and `from_history(..., raw_ep=True)`:
  raw en-passant targets (`en_passant='fen'`), castling rights and counters are
  preserved. Stored current FEN is authoritative. Missing or damaged optional
  history falls back to that position, as before.
- `History` does not carry a FEN-mode tag; the caller must use the matching mode
  when validating a replay. Replacing root plus moves with final FEN alone would
  discard repetition history. No saved schema was changed.
- PGN/session recovery retains the existing normalized notation/history path,
  annotated PGN snapshot, headers, nonstandard roots and result behavior.
  `History`, move/piece records and outcomes are immutable; `Document.headers`
  retains its existing mutable dictionary semantics.

## Dependency rules

The facade may import standard-library helpers, owned chess vocabulary,
`document_state` records, and rules/notation adapters. It must not import Qt, Tk,
GLFW/OpenGL, UI/rendering, clocks, audio, preferences, filesystems/platform setup,
engine processes, bookmark/session stores or application controllers. Runtime
import isolation and a static allowlist (including deferred imports) enforce
that direction. No new circular application/domain dependency was found.

Direct production python-chess imports remain confined to four existing files:

| File under `otb_chess/chess_backend/` | Dependency and role |
| --- | --- |
| `rules.py` | `chess.Board/Move/Piece`: native provider and ending/claim rules |
| `notation.py` | `chess`, `chess.pgn`: SAN and annotated PGN parsing/export |
| `uci.py` | `chess`, `chess.engine`: internal board reconstruction and UCI transport |
| `books.py` | `chess.polyglot`: native Polyglot reader |

Direct imports outside this production boundary were already zero and remain
zero. This phase reduces native-object usage rather than claiming to remove
python-chess. Tests may still use provider-specific fixtures.

## Remaining native-board exposure and extraction blockers

| Users | Remaining dependency |
| --- | --- |
| `core/documents.py`, `core/game.py` | `board`, `history_board()`, `read_fen()` and native load/replacement inputs; lifecycle, animation and stale-position identity |
| `ui/position_setup.py` | Native scratch board/pieces; editing turn, castling rights and placement; deliberate reset of EP/counters even for pasted setup FEN |
| `graphics/rendering.py`, `core/board_input.py` | Native piece maps, occupied-square reads, turn/history and board identity; checked-king selection now comes from the facade |
| `ui/desktop_ui.py`, `ui/legacy_ui.py`, `ui/evaluation_graph.py` | Native history replay for move labels/graphs, FEN and move-stack reads; legacy move-list replay still assumes the standard root |
| `ui/document_actions.py` | Native-board FEN reads at clipboard/file/UI boundaries |
| `ui/variation_preview.py` | Facade validates variations, then exposes copied native boards for the existing renderer; preview/clock tokens retain board identity |
| `core/evaluation.py`, `ui/material.py` | Accept native boards at their public compatibility entry points, then query the facade internally |
| `bookmarks.py`, `services/bookmark_actions.py`, `services/session.py` | Native position inputs/restore return values and controller history-length access; serialization and adjudication now use the facade |
| `services/engine.py`, `chess_backend/uci.py` | Service borrows the controller board to produce owned `History`; UCI reconstructs native boards privately |
| `core/game.py`, `chess_backend/books.py` | Polyglot consumes a native board and returns native move entries |
| `chess_backend/rules.py` and existing tests | Native type aliases and legacy history helpers remain supported |

The bridge intentionally allows mutations that bypass the facade. Do not remove
it until readers, setup editing, history/preview identity, book entries and test
fixtures have been migrated. Imported PGN annotations and application outcomes
also need explicit contracts before physical extraction. This is a preparation
boundary, not an assertion that native leakage has already been eliminated.

## Files changed in this phase

Paths below are relative to `otb_chess/` unless otherwise specified.

| Files | Change |
| --- | --- |
| `chess_backend/position.py` (new), `chess_backend/rules.py` | Facade, owned move/outcome data and compatibility guidance |
| `core/documents.py`, `core/game.py`, `core/clocks.py` | Canonical facade alias, moves/undo, history/PGN and game outcome integration |
| `core/evaluation.py`, `graphics/rendering.py` | Owned evaluation piece queries and domain-supplied checked-king square |
| `ui/desktop_ui.py`, `ui/engine_analysis.py`, `ui/variation_preview.py`, `ui/material.py` | Snapshots, check status, domain PV validation and material accounting |
| `bookmarks.py`, `services/engine.py`, `services/session.py` | Raw bookmark restoration, normalized engine snapshots and recovery outcomes |
| Repository `tests/test_chess_position.py` (new) | 18 facade/architecture regressions |
| Repository `docs/chess_core_architecture.md` (new) | Boundary, residual dependencies and verification record |

## Verification and local test environment

Verified on 2026-09-26 with `.venv-test` Python **3.13.12**:

- Previously failing legacy tests first: `tests.test_piece_sets`, **8 passed**.
- Complete discovery: **233 passed**, **0 failures**, **0 errors**, **0 skipped**,
  133.905 seconds. This includes Qt/Tk launch, native OpenGL, setup/flipping,
  clocks/history, engine subprocesses, bookmarks, PGN and the experimental core.
- Focused review of state aliasing, ending policy, raw/normalized FEN, snapshot
  ownership and domain dependency direction found no blocking refactor issues.

From the repository root, use process-local Tcl/Tk paths:

```powershell
$env:TCL_LIBRARY = (Resolve-Path '.tmp/python313-check/runtime/tcl/tcl8.6').Path
$env:TK_LIBRARY = (Resolve-Path '.tmp/python313-check/runtime/tcl/tk8.6').Path
.venv-test/Scripts/python.exe -m unittest tests.test_piece_sets -q
.venv-test/Scripts/python.exe -m unittest discover -s tests -v
```

The copied virtual environment still references the old Downloads runtime in
`pyvenv.cfg`. Explicit library paths plus execution outside the Codex sandbox
were required for Tcl initialization. No application code, tracked environment
configuration or installed runtime was changed to work around this. Recreating
the local test environment with `tools/setup_test_env.ps1` is the durable local
maintenance option if the old runtime is removed. `.venv` Python 3.14 lacks the
experimental core's `cozy_chess` dependency; use the documented 3.13 environment.
The optional PyOpenGL NumPy-handler warning remains and did not fail any tests.

## Recommended next task (not started)

Introduce an owned read-only position/history view for rendering and move-list /
evaluation-graph consumers, then migrate those consumers without changing setup
or persistence. Preserve black-to-move roots, preview/live identity and legal
highlighting. Next, separately isolate setup editing and Polyglot entry values,
then remove the native compatibility properties after their callers are gone.
Only after that should the facade/adapters and transfer vocabulary be physically
extracted. Provider replacement and python-chess removal are separate tasks.

This preparation phase is complete. No next phase, commit or push was performed.
