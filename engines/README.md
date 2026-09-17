# Stockfish setup

Run `python tools/install_stockfish.py` from the project folder to download and
verify the pinned release. The downloaded engine directory is ignored by Git.
The script preserves the original source, build scripts and GPL licence.

Stockfish 19, official Windows x86-64 universal release:
https://github.com/official-stockfish/Stockfish/releases/tag/sf_19

Downloaded 2026-09-18 from:
https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip

The original release contents are preserved under `stockfish-19/stockfish/`,
including `Copying.txt` (GPLv3), AUTHORS, source, build scripts, and documentation.
Upstream source: https://github.com/official-stockfish/Stockfish/tree/sf_19
The universal executable selects instructions appropriate for the CPU.

The app discovers this executable recursively and uses it as the initial engine.
Users can select another UCI executable, whose path is then remembered.
