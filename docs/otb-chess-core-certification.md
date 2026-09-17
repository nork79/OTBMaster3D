# Rules adapter regression certification

2026-09-17; Windows x64, CPython 3.13.12, cozy-chess-py 0.1.1.
This certifies the exercised contracts, not exhaustive correctness of every
legal chess position or readiness for production migration.

## Results

- Core: **21/21 passed**, 1.962 seconds, in `.tmp/cozy-check`, where python-chess
  is absent. Command: `python -m unittest tests.test_otb_chess_core -v`.
- Full application suite: **58/58 passed**, 27.859 seconds, in the Python 3.13
  application environment (37 existing application tests plus 21 core tests).
  Command: `python -m unittest discover -s tests -v`. Native graphics/Tcl tests
  ran outside the restricted sandbox. Optional NumPy warning was non-fatal.
- Syntax: `python -m compileall -q main.py otb_chess otb_chess_core tests tools`
  passed. Existing production import-boundary test and core import tests passed.

| Position | Depths | Exact perft counts |
| --- | --- | --- |
| Initial | 1–4 | 20 / 400 / 8,902 / 197,281 |
| Kiwipete | 1–3 | 48 / 2,039 / 97,862 |
| Rook/pawn endgame | 1–4 | 14 / 191 / 2,812 / 43,238 |

Fixtures and expected counts reuse `tools/cozy_rules_probe.py`. The test traverses
the owned adapter using push/pop and checks state restoration at internal nodes.
No reference chess dependency or python-chess implementation code was used.

## Contract coverage

All four castles; check on origin/transit/destination; king/rook movement and
original-rook capture rights; rights restored on undo. Legal/pinned EP, expiry,
restoration and legal-only FEN canonicalization. Both colours' quiet/capture
promotions to all four piece types and restoration to the original position.
Check, double-check, mate, stalemate, pinned king exposure and rejected moves.
Starting/arbitrary roots, black turn, large counters, FEN stability, repeated
position cycles, copy branches, full unwind, piece maps, captures and turn changes.

The public-return test inventories every current public Board method/property
and checks returned values/containers against owned types and builtins. Provider
castling destinations never appear as public moves. Native state remains private
to the backend implementation; public API results contain no cozy-native objects.
Static import checks and the isolated core run confirm the core has no
python-chess dependency. The package also imports with site packages disabled.

## Defects and limits

No adapter defects were discovered; no adapter or production code changed in this
certification task. Two first-draft test setups were corrected: an off-turn king
was accidentally placed in rook check, and a cycle test attempted a Black move
after undoing to White's turn. These were fixture errors, not provider failures.

Remaining scope limitations: orthodox chess only; no repetition/material draw
adjudication, draw claims, Chess960 or null moves. SAN/PGN/UCI/Polyglot remain
unimplemented. This does not qualify frozen packaging, other CPUs/platforms or
all malformed FEN inputs. No new features or dependencies were introduced here.

Production OTBMaster3D remains unchanged and still uses its existing python-chess
backend. Changed files for this task: `tests/test_otb_chess_core.py` and this report.
