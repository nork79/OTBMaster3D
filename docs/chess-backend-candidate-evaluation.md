# Chess backend candidate evaluation

Date: 2026-09-17. Active target: OTBMaster3D 8.4.0, standard CPython 3.13 on Windows x64.
Companion: [repository audit and baseline](python-chess-replacement-audit.md).
This is a recommendation only. The original audit used source evidence without
installing candidates. Subsequent [Python 3.13 application tests](python-313-compatibility.md)
and [isolated cozy-chess-py wheel tests](cozy-chess-isolation-results.md) passed.
No candidate has been integrated into the application. Python 3.14 findings below
are retained as compatibility history, not the active runtime plan.

## Recommendation

Prefer **cozy-chess 0.3.4 as the legal-move core**, through the
published MIT `cozy-chess-py` 0.1.1 Python 3.13 Windows wheel, behind the existing
`chess_backend` package. Keep move generation, attacks, king safety, castling
legality and en-passant legality in the library. Own only compatibility records,
history, notation/protocol adapters and narrowly scoped adjudication glue.

This is a **conditional architecture choice**, not approval to replace the
dependency now. Python 3.13 is the explicitly selected runtime target; its
published wheel passed isolated rules checks without a custom Rust binding.
Counter preservation still needs deliberate adaptation. Future gates must prove
exact FEN/history semantics, application integration and frozen packaging.
If those fail, reconsider rschess behind a custom binding rather than introducing
a handwritten move generator.

This approach is simpler to contain than adopting a second library's entire game
lifecycle. It is not the smallest possible amount of notation code: rschess
supplies SAN and more adjudication helpers. However, neither candidate eliminates
the app's PGN-tree or UCI-process work, and rschess has its own terminal-state
semantics to reconcile. Do not combine two rules engines just to obtain SAN.

## Candidate comparison

The table records the original source audit, including its Python 3.14 concerns.
For the active Python 3.13 target, installation/import and 12 isolated rules tests
have now passed; upgrading the binding is no longer the planned integration step.

| Criterion | cozy-chess-py / cozy-chess | rschess |
| --- | --- | --- |
| Identity | PyPI `cozy-chess-py`, import `cozy_chess`; repository spelling is **cosy-chess-py**. Wrapper 0.1.1 uses Rust cozy-chess 0.3.4 | Rust crate `rschess` 2.0.5 by prawnydagrate; not a verified Python package |
| Licence | Wrapper MIT and Rust core MIT, confirmed in upstream licence files [1][2] | MIT in licence and Cargo metadata [7] |
| Maintenance | Wrapper releases 0.1.0/0.1.1 both 2026-03-16. Repository last push 2026-03-16; core last push 2024-04-05. Neither archived. Young wrapper; slower-moving core, not evidence of an SLA [3][4] | Release 2.0.5 dated 2025-07-27; repository last push same date, not archived. Limited recent activity; do not label abandoned solely from dates [4][8] |
| Windows | Published CPython 3.8–3.13 `win_amd64` wheels; upstream release workflow targets Windows x64 [3][5] | Rust source integration appears plausible with MSVC; no official Windows Python wheel/binding found in inspected upstream distribution. Not validated on Windows [7][8] |
| Python 3.14 | **No cp314 or abi3 Windows wheel in 0.1.1.** Requires-Python >=3.8 does not prove binary compatibility. Wrapper pins PyO3 0.23 and builds only through 3.13 [3][5] | No Python API/ABI claim. A new binding using a 3.14-capable PyO3 release would be required; compatibility remains unproven |
| Rules / FEN | Legal moves, validated position construction, play, copy, checkers, FEN and Chess960 support. Native counter limits and castling encoding differ [6] | Legal moves, FEN, move/undo, capture queries, board state; terminal positions suppress legal moves [9][10] |
| SAN / PGN | No SAN/PGN API found in the inspected wrapper stubs/core public API; adapters required [5][6] | SAN conversion/parsing and optional `pgn` feature exist, but PGN is not a compatible variation/comment tree [9][11] |
| Repetition / draws | Position-equivalence helper exists; caller owns history. Status omits repetition and material draws and treats 100 halfmoves as a draw [6] | Threefold/fivefold, 50/75-move, material, check/mate/stalemate helpers; API breadth is not independent correctness verification [9] |
| UCI / Polyglot | UCI move-format helpers in core, not process management; no book reader in inspected API [6] | UCI move parsing, not a UCI process client; no Polyglot reader found [9] |
| Integration effort | **large overall**: upgrade/maintain binding, Board compatibility, SAN/PGN, engine and books | **large overall**: create binding, adapt lifecycle and data types, PGN tree, engine and books; SAN/material helpers reduce some local code |

Repository `pushed_at` values were fetched directly from the GitHub API [4]. They
are activity indicators, not release dates or proof of maintenance quality.
No candidate build/install was attempted during the original audit; the later
Python 3.13 wheel test is linked above. No Python 3.14 support is claimed
merely because a Rust crate itself is platform-independent.

## Compatibility findings that change the design

### cozy-chess

The core represents castling as king-to-rook; standard UCI e1g1/e1c1 conversion
must use board context. The Python stubs inspected do not expose the core's UCI
conversion helpers. Expose them in a future binding rather than scattering
conversion across UI, engine and book paths. [5][6]

Core source rejects FEN halfmove counters above 100, caps them during play, and
stores fullmove numbers in u16. Keep lossless counters in the application Board
adapter and normalize only the core's internal counters, or pursue a small
upstream change. Formatting must restore the real counters. Do not reject
previously accepted session/PGN roots or use capped FEN as an external identity.
This is a required compatibility feature, not an optional optimisation. [12]

Do not map `status() == Drawn` directly onto the current GUI policy. Determine
mate/stalemate through legal moves and checkers; material adjudication and
history-based outcomes require explicit handling. Preserve current controller
behaviour separately from PGN result inference. [6]

### rschess

Its Board API provides SAN, undo and detailed draw queries. However,
`gen_legal_moves` is gated by the board's ongoing flag; lifecycle transitions
include automatic fivefold/75-move endings. This differs from the current
controller's narrower automatic-end policy. A prototype must establish whether
the lower-level position API can preserve present semantics without forking
rules code. [9][10]

The inspected PGN model holds a tag map and a Board, and its tokenizer has no
comment/recursive-variation nodes. It therefore cannot replace the existing
annotated document round trip. Treat support for mainline PGN as a partial
capability; black-to-move roots, malformed input and multi-game behaviour also
need fixtures, not assumptions. [11]

## Proposed ownership and boundaries

| Boundary | Proposed responsibility |
| --- | --- |
| `values.py` | Retain existing square/colour/piece conventions unchanged |
| `rules.py` | Application Board wrapper, immutable Move/Piece records; convert to/from library values; core does all move legality. Keep root, full history, uncapped counters and copy/pop snapshots in this one adapter |
| `notation.py` | Original SAN implementation driven by legal moves and resulting check state; PGN tokenizer, tree, headers/comments/NAGs/variations and serializer. Delegate all position changes to Board |
| `uci.py` | Subprocess handshake/readiness, bounded searches, stop/quit/timeout handling, protocol parsing and plain SearchResult/Evaluation records |
| `books.py` | Polyglot binary lookup, verified hash semantics, castling/promotion conversion, legal filtering, move/weight records |
| Controller/UI | Keep clocks, selection, review, animation, game policy and stale-search rejection; consume application records rather than library-native types |

Board snapshots for undo and worker searches are intentional copies, not two
independently advancing rule engines. Preserve move histories when communicating
with UCI engines: root FEN plus moves lets the engine reason about repetition;
current FEN alone loses that information.

Implement SAN by filtering the provider's legal moves for disambiguation and
checking the resulting position, not by recreating movement rules. Material-draw
logic should be a small separately tested adjudication component derived from
rules/specifications. Preserve the distinction between claims and automatic
draws; introducing new UI claim behaviour is a separate product change.

PGN is the largest application-owned component. Use an actual recursive parser,
not line splitting or a regular-expression-only parser. Retain existing session
version 1 PGNs and unchanged imported comments/variations. Result generation must
not equate a paused session or an offered draw with a concluded game.

Polyglot requires its specified random-key table and precise en-passant/castling
hash behaviour; cozy's own Zobrist hash is not interchangeable. Before writing
the reader, obtain the format and constants from independently verified,
redistributable sources. No external Polyglot implementation or constants were
selected or copied in this audit.

## Packaging plan and gates

1. Use the published `cozy-chess-py==0.1.1` cp313 Windows x64 wheel for a future
   adapter prototype, recording its hash. No PyO3 upgrade or custom Rust binding
   is required for the tested Python 3.13 API. Do not add it to runtime requirements
   until migration work is separately authorized.
2. Qualify that wheel in the frozen application on clean Windows x64 hosts.
   A source rebuild with maturin/Rust/MSVC is a fallback, not the current plan. [14]
   Do not assume free-threaded Python, Windows ARM64 or Python 3.14 compatibility.
   Historically, PyO3 0.25 introduced 3.14 beta support; the wrapper's 0.23 pin
   remains a concern only if revisiting a 3.14 source build. [13]
3. Use baseline CPU features: no `target-cpu=native`/mandatory BMI2 for general
   distribution. Pin Rust dependencies and audit transitive licences. Bundle the
   MIT notices and rebuildable source/patch provenance. [2][6]
4. Verify wheel import and rule contracts on a clean Windows host, then a frozen
   folder build including the `.pyd` and any required runtime libraries. Existing
   CI currently tests only the installed Python dependencies, not native wheel
   production or packaging.
5. Accept only after perft, castling-through-check, pinned en passant, all
   promotions, FEN counter extremes, history/pop, PGN trees/results, session
   recovery, known Polyglot hashes, UCI failure modes and UI tests pass.
6. Remove python-chess only in a separately authorized migration after every
   boundary, fixture and build-time dependency is replaced; run a clean suite
   without it installed. This audit performs none of those steps.

## Highest risks and baseline

- Silent notation loss would also corrupt session recovery.
- Castling encodings, en-passant canonicalization and counter bounds affect
  legal moves, engine matching, animation and books.
- Draw policies differ between provider state, GUI state and exported PGN.
- The small Python wrapper still carries maintenance and binary-portability
  risk; its 3.13 wheel has passed isolation tests, but application/frozen-build
  qualification remains outstanding. rschess has not been runtime-qualified.
- Existing test coverage is insufficient for certifying a rules engine.

Historical audit baseline: **37 tests, 36 passed, 1 failed** on Windows/CPython 3.14.7. The failing
legacy renderer test expects two geometry caches but observes three; see the
[exact command, traceback and diagnosis](python-chess-replacement-audit.md#full-baseline-test-result).
No failing test was edited or suppressed during that audit. Stage 0 subsequently
corrected the stale cache expectation; Stage 1 passed **37/37 on Python 3.13.12**.

## Authoritative evidence

Sources checked 2026-09-17; links to moving branches describe the inspected state,
not a promise about future releases. Pin exact commits during a later prototype.

1. [Python wrapper MIT licence](https://github.com/kaajjaak/cosy-chess-py/blob/master/LICENSE).
2. [cozy-chess MIT licence](https://raw.githubusercontent.com/analog-hors/cozy-chess/master/LICENSE).
3. [PyPI 0.1.1 files](https://pypi.org/project/cozy-chess-py/0.1.1/#files) and
   [machine-readable release metadata](https://pypi.org/pypi/cozy-chess-py/json).
4. GitHub repository metadata: [wrapper](https://api.github.com/repos/kaajjaak/cosy-chess-py),
   [core](https://api.github.com/repos/analog-hors/cozy-chess),
   [rschess](https://api.github.com/repos/prawnydagrate/rschess).
5. Wrapper [Cargo.toml](https://raw.githubusercontent.com/kaajjaak/cosy-chess-py/master/Cargo.toml),
   [API stubs](https://raw.githubusercontent.com/kaajjaak/cosy-chess-py/master/cozy_chess.pyi),
   [release workflow](https://raw.githubusercontent.com/kaajjaak/cosy-chess-py/master/.github/workflows/release.yml).
6. [cozy-chess Board API](https://docs.rs/cozy-chess/latest/cozy_chess/struct.Board.html)
   and [core README](https://github.com/analog-hors/cozy-chess).
7. rschess [MIT licence](https://raw.githubusercontent.com/prawnydagrate/rschess/master/LICENSE)
   and [Cargo features/dependencies](https://raw.githubusercontent.com/prawnydagrate/rschess/master/Cargo.toml).
8. [rschess 2.0.5 release documentation/history](https://docs.rs/crate/rschess/2.0.5).
9. [rschess Board API](https://docs.rs/rschess/latest/rschess/struct.Board.html).
10. [rschess Board implementation](https://raw.githubusercontent.com/prawnydagrate/rschess/master/src/board.rs).
11. [rschess PGN data model/parser](https://raw.githubusercontent.com/prawnydagrate/rschess/master/src/pgn.rs).
12. cozy-chess [FEN parser](https://raw.githubusercontent.com/analog-hors/cozy-chess/master/cozy-chess/src/board/parse.rs)
    and [Board counter/status implementation](https://raw.githubusercontent.com/analog-hors/cozy-chess/master/cozy-chess/src/board/mod.rs).
13. [PyO3 0.25 changelog](https://pyo3.rs/v0.25.1/changelog.html).
14. [Maturin distribution guide](https://www.maturin.rs/distribution.html).

No GPL replacement is recommended. No python-chess implementation was copied
or translated. No migration implementation was performed, and python-chess
remains installed and required by the unchanged application.
