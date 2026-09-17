# Production rules switch: stopped at integration boundary

The requested switch has **not** been performed. Inspection found that the
strict owned-object boundary requires more than changing rules.py and converting
FEN at four entry points. Following the instruction to stop rather than broaden
the redesign, this task leaves production and the certified core unchanged.
This is an integration scope assessment, not a finding that cozy cannot supply
the rules engine.

## Coupling requiring explicit adapter contracts

| Location | Current dependency | Required work before switching |
| --- | --- | --- |
| `chess_backend/rules.py`, controller, move-list UI | Re-exported native Board/Move; iterable `legal_moves`, `san`, `reset`, `is_valid`; material queries in `core/game.py` | Application facade over core plus SAN conversion; define material adjudication without retaining python-chess as a production rules oracle |
| `core/documents.py` | Native PGN nodes return native root/end Boards and mainline Moves; unchanged-document detection compares these moves to the live history | Preserve opaque original PGN tree for export, expose owned board/history views, and compare owned moves; otherwise annotation-preserving export can silently choose the reconstruction path |
| `ui/document_actions.py`, `services/session.py` | `document.end().board()` becomes the game or recovered position | Conversion must reconstruct the root plus complete move history, not just current FEN, before state reaches these consumers |
| `services/engine.py`, `ui/desktop_ui.py` | Native SimpleEngine receives Board and returns Move/PV/Score objects directly into controller/UI | Wrap results and evaluation records as well as input positions; preserve root plus moves for engine repetition context; protocol implementation can remain unchanged |
| `chess_backend/books.py`, `core/game.py` | Native Polyglot entries contain moves returned to the controller | Own entry/move view and explicit board conversion; retain existing lookup and weighting behaviour |

The core's immutable tuple history also differs from python-chess's list. Its
`legal_moves()` is a method, not an iterable property. These are small facade
changes individually; they do not solve native objects arriving via the other
boundaries. A current-FEN-only shim would lose history and cannot satisfy the
session, review, FEN-root and UCI requirements.

The most important additional rules gap is `is_insufficient_material()`, used by
the production controller to end games. It is intentionally absent from the
certified core. Removing that query changes behaviour; implementing it by calling
python-chess would retain a rules responsibility beyond the four permitted
temporary integrations. It needs its own owned implementation and fixtures.

## Bounded follow-up needed

Agree and implement the small application Board facade, owned PGN board/history
views, owned engine result/evaluation records, and book-entry conversions before
the production flip. Keep the existing PGN tree/parser/writer and UCI/Polyglot
implementations behind those views. Add material-draw parity fixtures separately
from repetition and move-count draw policies. Then switch and run integration
tests that assert owned types, rather than continuing to inject native Boards
as some current test fixtures do.

No conversion shim, production feature, dependency, packaging or application
logic was changed in this task. Existing native Board/Move/Piece objects still
reach the controller/renderers, native PGN documents reach document/session code,
and native engine scores/PV moves reach the UI. Those leaks remain visible rather
than being hidden behind a partial rules migration.
