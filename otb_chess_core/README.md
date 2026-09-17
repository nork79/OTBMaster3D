# Internal chess core

This package owns chess data and a playable orthodox Board adapter. It has no UI,
rendering, clock, service or controller dependencies. Production OTBMaster3D
still uses its existing python-chess backend.

Public data uses a1=0 through h8=63, Boolean colours and piece codes 1 through 6.
Move and Piece are immutable; their checks validate representation, not legality.
Only `rules/cozy_backend.py` may load the candidate provider, lazily. Provider
objects must not escape that module. `requirements.txt` pins cozy-chess-py 0.1.1
alongside the unchanged production chess dependency. Importing the package is
lazy; constructing a Board requires the candidate wheel installed on Python 3.13.

## Board API and policies

- `Board()`, `Board(fen)`, `Board.from_fen(fen)`, `set_fen(fen)`, `fen()`.
  Successful loading clears history and establishes a new root; failed loading
  leaves the existing board intact. Input requires six fields and positive
  fullmove/nonnegative halfmove decimal counters.
- `legal_moves()` returns an immutable tuple of owned Moves; `is_legal(move)`
  checks membership. `push(move)` applies only legal owned moves and raises
  ValueError otherwise. Castles always use king destination c/g, never the rook
  square. Native conversion is centralized in the backend module.
- `pop()` restores the preceding snapshot and returns its Move, raising
  IndexError for empty history. `move_stack` is an immutable tuple. `copy()`
  includes independent history; `root()` returns an independent root Board with
  empty history. History consists of owned FEN snapshots and immutable Moves.
- `piece_at(square)`, `piece_map()`, `turn`, `halfmove_clock`, `fullmove_number`.
  Returned maps are detached dictionaries. Counters are read-only properties,
  maintained as Python integers outside the provider's 100/65535 limits.
- `is_capture(move)`, `is_castling(move)`, `is_en_passant(move)` return false for
  illegal moves. `is_check()`, `is_checkmate()`, `is_stalemate()` use provider
  legality/checkers, never its halfmove-driven terminal status.

Exported FEN uses **legal en passant**: the target is present only when at least
one legal capture exists (including king-safety restrictions). Internal snapshots
retain provider EP state for undo. Thus e2e4 normally exports `-`, not `e3`;
an imported irrelevant EP target is intentionally canonicalized. True counters
survive import, moves, copy, root and undo without provider truncation.

Scope is standard chess only, with KQkq castling rights; no Chess960, null moves,
SAN, PGN, UCI, Polyglot, repetition/material-draw or claim adjudication is exposed.
This is not a drop-in python-chess API: legal moves are a method, move history is
read-only, and only legal moves can be pushed. No draw policy is inferred from
the provider. Production callers have not been changed.

Target: Python 3.13 Windows x64. Candidate: cozy-chess-py 0.1.1 (MIT), wrapping
cozy-chess 0.3.4 (MIT). No third-party implementation is vendored here.
Preserve `licenses/cozy-chess-py-MIT.txt` when redistributing the candidate.
That notice does not license OTBMaster3D's own code under MIT.

Provenance:

- Wrapper: https://github.com/kaajjaak/cosy-chess-py
- Core: https://github.com/analog-hors/cozy-chess
- Wheel: `cozy_chess_py-0.1.1-cp313-cp313-win_amd64.whl`
- SHA-256: `09c98150e132175674b09ef2ed059326df49e7af772d7184a63da6e89c78cc2e`
- Notice copied verbatim from the installed wheel's `dist-info/licenses/LICENSE`.

Future distribution must inventory the actual binaries and transitive notices;
this scaffold does not establish release packaging or a stable public SDK.
