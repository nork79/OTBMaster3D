# Fairy-Stockfish 14

Stockfish 19 and Fairy-Stockfish 14 provide the built-in difficulty presets.
Current source also supports optional [Rodent IV opponents](RODENT_IV.md),
built separately for the source workspace.
Fairy-Stockfish supplies the lower standard-chess difficulty targets. These
settings are not independently calibrated human Elo ratings.

## Retained materials

- Official release: https://github.com/fairy-stockfish/Fairy-Stockfish/releases/tag/fairy_sf_14
- Executable SHA-256: `28d5c18fd7352d66800d13e1fdd57ba7d64d95c38d93642fd12cbd89e9d0ed73`
- Source archive SHA-256: `ba21ae5681cfa365293abe34301e7e645f3ce6a49db00d42cf2830585879e2d8`
- Source: https://codeload.github.com/fairy-stockfish/Fairy-Stockfish/zip/refs/tags/fairy_sf_14
- Original GPL-3.0-or-later notices, authors and README are in
  `licenses/Fairy-Stockfish/`. The engine directory also contains the complete
  upstream source archive, including Makefile and CI build instructions.

The hashes pin official HTTPS downloads locally; no publisher checksum or
signature authentication is claimed. `tools/install_fairy_stockfish.py` verifies
the pinned files and restores the source and notice files for packaging.

## Configuration and verification

The selected x64 executable exposes UCI_Elo 500–2850. Standard chess is used,
with `Use NNUE=false`; no external model is downloaded or required. Its PE imports
are Windows system libraries ADVAPI32.dll, KERNEL32.dll and msvcrt.dll. No copied
Microsoft runtime is supplied for this executable.

Run `python tools/verify_fairy_stockfish.py` to verify hashes, source materials,
PE imports, accepted strength settings, legal moves for both sides and exact
bookmark configuration roundtrips. Results are recorded in
[verification evidence](evidence/fairy-stockfish-verification.json).

The component's GPL grant is compatible with the application's GPLv3 route.
This component review does not clear the application's other release blockers.
No installer was rebuilt for this change; clean Windows validation and public
source download verification remain outstanding.
