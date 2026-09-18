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

## Difficulty presets

Use **Engine > Difficulty** or the Difficulty selector in engine settings. Maia runs locally on CPU through Lc0 with a one-node limit. Presets use Maia 1100/1300/1400/1500/1600/1800; the 300/600/900 practice levels add random legal mistakes (80%/55%/30%) to Maia 1100 and are uncalibrated labels. Stockfish handles 2000, 2200, 2500 and full strength. All ratings are approximate and model training ratings are not measured playing strength. Presets disable opening books and use Balanced style.

Install/reproduce Maia assets with `.venv/Scripts/python.exe tools/install_maia.py`. Lc0 archive version and checksum are pinned in the installer; downloaded model hashes are recorded in `maia/installation.json`. Saved difficulty and engine paths are restored at launch. Choose Custom settings for a different UCI engine or opening book.
