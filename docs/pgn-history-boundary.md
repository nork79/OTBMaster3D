# Owned PGN/history boundary

Production rules remain python-chess. This change isolates notation transfers;
it does not replace the parser/writer or select OTBChessCore as the live engine.

`otb_chess/document_state.py` defines two owned transfer records:

- `History`: root FEN, immutable tuple of OTBChessCore Moves, final FEN.
- `Document`: ordinary header dictionary, History and serialized annotated PGN.

These are import/export snapshots, not a second live game state. The application
does not edit variations today, so preserving serialized PGN avoids introducing
a parallel annotation tree. Comments, NAGs and recursive variations remain under
the existing python-chess parser/writer. Header edits use the owned dictionary.

`chess_backend/notation.py` alone holds transient native PGN Game/GameNode/Headers,
StringExporter, and the native Boards/Moves needed for parsing, serialization and
SAN. Its public functions accept/return owned records, strings and lists. Native
PGN objects are not stored in `_pgn_document` or returned by session decoding.

`chess_backend/rules.py` adds `owned_move`, `snapshot_history`, and
`restore_history` for the currently selected rules provider. Restoration replays
root plus moves and checks final FEN; it never reconstructs from final FEN alone.
This preserves black-to-move roots, move numbers and full review history.
The native live Board still reaches controller/input/rendering through the
unchanged production rules backend, as explicitly required for this stage.
It is not a PGN-returned board. UCI/Polyglot native types remain unchanged.

Document/session/UI import paths consume `document.history`; loading materializes
it through the rules boundary. Review still uses the existing live/review board
mechanism. Saving snapshots the complete live history even during review. Session
JSON stays version 1 and retains its existing PGN field and recovery policy.

Unchanged mainlines reparse the retained annotation snapshot and use the same
StringExporter options. Changed mainlines retain the previous header-copy/result
policy and rebuild only the mainline, as before. PGN text is normalized by the
existing writer, not promised byte-identical to the original input. There is an
extra parse on unchanged exports; no user-visible behaviour difference was found.

SAN in desktop and legacy move lists now uses the explicit `san(fen, owned_move)`
boundary. SAN itself, UCI, Polyglot, clocks, rendering and promotion/adjudication
policies were not reimplemented or changed.

## Validation

- Core: 26/26 passed in the isolated Python 3.13 environment without python-chess.
- New boundary tests: 6/6 passed (simple/multi-game, recursive comments/variations,
  headers, FEN/black roots, move conversions, review/live, imported reviewed session).
- Full suite: 69/69 passed in 29.024 seconds on Python 3.13 Windows x64.
- Syntax compilation and existing production/core import-boundary tests passed.

Files changed in this stage: `otb_chess/document_state.py`,
`otb_chess/chess_backend/{notation,rules}.py`, `otb_chess/core/documents.py`,
`otb_chess/services/session.py`, `otb_chess/ui/{document_actions,desktop_ui,legacy_ui}.py`,
`tests/test_documents.py`, `tests/test_notation_boundary.py`, and this document.
No dependency or packaging changes were made.
