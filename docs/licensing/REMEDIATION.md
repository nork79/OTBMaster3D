# Release remediation

**Release status: BLOCKED.** Engine support is limited to Stockfish 19 and
Fairy-Stockfish 14. Both retain GPL notices and corresponding source. See
[engine evidence](FAIRY_STOCKFISH.md) and [licensing closure](LICENSING-CLOSURE.md).

The standalone Microsoft runtime is now an external prerequisite in packaging
source and the 2026-09-30 rebuilt installer. Setup neither bundles nor downloads
it, and the rebuilt payload passed the exclusion check. The maintainer removed
the speculative embedded-code concern as a release blocker. See
[Microsoft remediation](MICROSOFT_RUNTIME_REMEDIATION.md).
The itch.io distribution plan has been withdrawn; its store-terms review is no
longer a release blocker.

The current source removes the obsolete model backend and replaces its stored
difficulty IDs with neutral IDs. Unsupported saved selections reset to the
default engine; unsupported bookmark engines are not launched. No installer was
created for this change. Existing frozen artifacts do not represent current source.

The previous reports and raw logs were archived unchanged in
`release-materials/retired-engine-records.zip`. They describe historical builds,
not the current engine configuration. Raw historical logs were not edited to
claim new test results.

The rebuilt application passed its smoke test on 2026-09-30. Remaining release
work includes clean Windows testing (no test machine is available yet) and
matching source publication. Historical native-runtime reports do not reinstate
the withdrawn speculative embedded-code blocker.
Public source download URL verification remains a separate publication prerequisite.
No publication, tag, push, upload or store change is authorized or performed.

## Current source verification

The affected regression suite passed **127 tests** (exit code 0), covering engine
loading, all built-in difficulty presets, persistence, bookmarks, both difficulty
selectors, clock labels and PGN metadata. New checks reject unsupported engine
identities, preserve a working engine on failed bookmark restoration and reset
obsolete saved selections safely. Exact command and raw results:
[command](evidence/supported-engine-tests.json),
[output](evidence/supported-engine-tests.txt).

`python tools/verify_fairy_stockfish.py` also passed all **nine** practice settings,
including legal moves for both sides, exact configuration roundtrips and native
dependency/source checks. These are source-checkout tests on the development
host, not clean Windows or current installer validation.
