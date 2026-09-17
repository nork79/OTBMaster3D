# Replacing python-chess

## Current state

The active runtime and migration target is **Python 3.13 on Windows x64**.
The [application baseline](python-313-compatibility.md) and
[isolated candidate-wheel tests](cozy-chess-isolation-results.md) passed on 3.13.
Use the published 3.13 wheel for future candidate work; a custom Python 3.14
Rust binding is not the current plan. No backend migration has begun.

Application code imports `otb_chess.chess_backend`, never `chess` directly.
An architecture test enforces this boundary. This is migration infrastructure,
not an alternative chess implementation or a licensing workaround. The shipped
dependency remains `chess==1.11.2` (python-chess), GPL-3.0-or-later:
https://python-chess.readthedocs.io/en/stable/

The provider is currently selected by the explicit bindings in these modules:

| Boundary | Required behaviour / outstanding coupling |
| --- | --- |
| `values.py` | Application-owned colours, piece codes and square indexing; no dependency |
| `rules.py` | Board/Move/Piece are still native objects. Preserve FEN, legal moves, SAN, push/pop, copy/root, history, captures, checks, mate, stalemate and material draws |
| `notation.py` | PGN document trees, headers, comments, variations, parsing errors and export still use native objects |
| `uci.py` | Engine process management, limits, play/analysis results and score objects still use native objects |
| `books.py` | Polyglot readers consume a native board and return entries with move/weight |

## Migration sequence

1. Replace the UCI boundary with an application-owned client. Convert positions
   to FEN and history to UCI strings at the boundary; return independent move and
   evaluation records. Update engine workers and UI score formatting together.
2. Replace Polyglot reading behind `books.py`, including its position hash and
   weighted move selection. Add known book-file/hash fixtures before switching.
3. Replace PGN parsing/export behind `notation.py`; introduce independent document
   nodes. Preserve SetUp/FEN roots, black-to-move numbering, comments, variations,
   results and multi-game files. Do not discard metadata silently.
4. Replace rules with an independently implemented or suitably licensed provider
   behind `rules.py`. Adapt its objects to the app's required interface. Do not
   copy or translate GPL implementation code into a proprietary replacement.
5. Remove `chess` from runtime dependencies only when none of these boundaries
   imports it. Migrate provider-specific test fixtures too, then run the full
   suite in a fresh environment without python-chess installed.

These stages are coupled through native objects today: replacing an import alone
does not make the libraries interchangeable. Convert data at each boundary as
that subsystem is replaced rather than maintaining two mutable game states.

## Verification

`tests/test_chess_backend.py` exercises basic rules contracts and import isolation.
`tests/test_documents.py` covers notation and history preservation. Desktop tests
include actual UCI subprocess interaction and native OpenGL rendering.

Before replacing rules, extend the contract suite with trusted perft positions,
pinned/en-passant legality, castling through check, all underpromotions, repetition,
50/75-move rules, draw claims and long-game push/pop consistency. The current
suite is a starting point, not certification of a new rules engine.

## Closed-source distribution preparation

This refactor does not make the existing dependency GPL-free. Review the complete
dependency and asset bill of materials before distribution, including Qt/PySide6
licensing and any bundled UCI engines. Asset provenance belongs beside each asset;
prefer CC0 or permissive assets with recorded source, licence and attribution.
Do not assume a separately launched engine has the same licence as this app.
