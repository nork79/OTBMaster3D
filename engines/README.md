# Supported engines

OTBMaster3D uses Stockfish 19 and Fairy-Stockfish 14 for standard chess.
Run these commands from the project folder with Python 3.13:

```powershell
python tools/install_stockfish.py
python tools/install_fairy_stockfish.py
```

Both helpers download pinned official releases and retain corresponding source,
build scripts, authors and GPL notices. Generated engine directories are ignored
by Git. Fairy-Stockfish runs with NNUE disabled and needs no model files.

## Difficulties

Fairy-Stockfish provides targets 500, 600, 700, 800, 900, 1100, 1300, 1400 and
1500. Stockfish provides 1600, 1700, 1800, 1900, 2000, 2200, 2500 and full
strength. These are engine settings, not certified human Elo ratings.
Both selectors hide levels whose executable is unavailable. Menu labels describe
difficulty without including engine brand names.

Saved selections with unsupported IDs reset to the default engine. Unsupported
bookmark engine configurations remain stored, but are not launched. A working
engine is retained if restoring a bookmark engine fails.

Sources: [Stockfish 19](https://github.com/official-stockfish/Stockfish/tree/sf_19)
and [Fairy-Stockfish 14](https://github.com/fairy-stockfish/Fairy-Stockfish/tree/fairy_sf_14).
See [component evidence](../docs/licensing/FAIRY_STOCKFISH.md).
