# cozy-chess-py isolated rules-core test

Date: 2026-09-17. **Verdict: viable as the rules core on Python 3.13 Windows
x64, with application adapters. No custom Rust binding was needed for the
operations tested. This is not a drop-in python-chess replacement.**

## Installation and isolation

Created a fresh environment at `.tmp/cozy-check` using CPython 3.13.12 on
Windows 11 build 26200. Installed only `cozy-chess-py==0.1.1` with
`--only-binary=:all:`. The published
`cozy_chess_py-0.1.1-cp313-cp313-win_amd64.whl` installed and imported successfully;
no Rust compiler, source build or patched binding was used. `pip check` passed.

Wheel SHA-256 from pip's installation report:
`09c98150e132175674b09ef2ed059326df49e7af772d7184a63da6e89c78cc2e`.
Local installation evidence: `.tmp/cozy-install.json`.
The probe verifies that `chess` is not importable in this environment, and imports
no OTBMaster3D modules. The application environments and requirements are unchanged.

The [published wrapper](https://pypi.org/project/cozy-chess-py/0.1.1/) and
[Rust core](https://github.com/analog-hors/cozy-chess) are MIT licensed; see the
[candidate evaluation](chess-backend-candidate-evaluation.md) for licence evidence.

## Executed checks

The original standalone [probe](../tools/cozy_rules_probe.py) ran **12/12 tests
successfully in 0.026 seconds**, exit code 0. This is a targeted feasibility
probe, not an exhaustive rules certification or a performance benchmark.

| Area | Observed result |
| --- | --- |
| Initial-position perft, depths 1–4 | 20 / 400 / 8,902 / 197,281 |
| Kiwipete perft, depths 1–3 | 48 / 2,039 / 97,862 |
| Rook/pawn endgame perft, depths 1–4 | 14 / 191 / 2,812 / 43,238 |
| Piece access | Square numbering a1=0/h8=63, occupancy, piece/color lookup and side to move worked |
| Copy and mutation | Shallow/deep copies preserve position; playing on a copy leaves the original unchanged; rejected illegal move leaves board unchanged |
| Castling | Both white castles generated; kingside execution places king/rook correctly and clears rights; castling through check rejected |
| En passant | Capture removes the correct pawn; pinned en-passant capture rejected |
| Promotions | All four promotion choices generated and applied, for both quiet and capture promotions |
| Check/mate/stalemate | Checkers, no-legal-move state and terminal status distinguish tested mate/stalemate positions |
| FEN | Tested roots round-trip; malformed/missing-king positions rejected; counter limits confirmed |
| Repetition | Repeated knight cycle gives equivalent position/hash; no automatic repetition tracking |

Exact FEN fixtures and expected counts are embedded in the probe. No python-chess
implementation was copied or translated, and no reference engine was installed.

## Adapter requirements confirmed at runtime

1. **Castling conversion:** native moves use `e1h1` / `e1a1`, not standard UCI
   `e1g1` / `e1c1`. Centralize conversion using board context. This is a format
   adapter; the library still decides whether castling is legal.
2. **Uncapped counters:** halfmove 100 is accepted, 101 rejected; fullmove 65,535
   is accepted, 65,536 rejected. Halfmove remains capped at 100 after a quiet
   move. Keep true counters in the application adapter and normalize only the
   internal core position. Exact long-game FEN compatibility remains to implement.
3. **FEN en-passant policy:** after e2e4, native FEN includes `e3`, even without a
   legal capture. Match the application's existing canonical-FEN convention in
   the adapter; do not use raw provider FEN interchangeably in stale-result checks.
4. **History/undo:** copies work, but no `pop` exists. Own root/move history and
   snapshots, including repetition history. `same_position` is useful; do not
   treat a hash alone as collision-free position identity.
5. **Adjudication:** bare kings report `Ongoing`; repeated positions also remain
   ongoing. At 100 halfmoves, status is `Drawn` but legal moves are still generated
   and playable. Do not map provider status directly onto application game policy.
   Material draws and claim/automatic draw distinctions need separate handling.
6. **Other python-chess responsibilities:** SAN/PGN, UCI subprocess handling,
   Polyglot and application-owned Move/Piece/Board records remain adapter work.
   The runtime confirms no Board SAN/parser/material helper methods inspected by
   the probe; the broader API gaps are detailed in the earlier audit.

These gaps do not require recreating legal move generation. For standard chess,
the exposed API appears sufficient to implement the necessary adapters in Python
without modifying the Rust binding. That conclusion still needs confirmation
through future adapter contract and application integration tests.

## Reproduce

From the repository root, with the retained Stage 1 runtime:

```powershell
.\.tmp\python313-check\runtime\python.exe -m venv .tmp\cozy-check
.\.tmp\cozy-check\Scripts\python.exe -m pip install --only-binary=:all: cozy-chess-py==0.1.1
.\.tmp\cozy-check\Scripts\python.exe -m pip check
.\.tmp\cozy-check\Scripts\python.exe tools\cozy_rules_probe.py
```

The probe is outside `tests/`, so normal application test discovery does not
acquire an optional candidate dependency. The existing application baseline is
still the [Stage 1 result of 37/37](python-313-compatibility.md); that suite was
not rerun here because this stage changed no application code or dependencies.

## Recommendation and remaining gates

Proceed with the **published Python 3.13 wheel** as the preferred candidate for a
separately authorized adapter prototype. The earlier Python 3.14 custom-binding
plan is unnecessary for this tested Python 3.13 route.

Not tested here: frozen packaging, older CPUs/other machines, ARM64, Python 3.14,
Chess960, exhaustive malformed input, all draw/material cases, memory stress or
full application integration. Wheel portability and adapter fidelity must be
verified before selecting it for a release.

**No migration was implemented. Python-chess remains the application's backend.**
