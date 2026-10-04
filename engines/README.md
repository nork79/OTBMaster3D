# Supported engines

OTBMaster3D uses Stockfish 19 and Fairy-Stockfish 14 for its difficulty presets,
with Rodent IV personality opponents, bundled in Windows installers from 1.6.4.
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

## Rodent IV personality opponents

With MinGW-w64 `g++` on PATH, run:

```powershell
python tools/install_rodent.py
```

This builds Rodent IV 0.33 from pinned upstream source and installs it in
`engines/rodent-iv`. The helper verifies the source archive checksum and retains
the archive, GPL notice, build helper, compiler flags, resource checksums and
opening-book attribution files beside the engine. An existing archive can be
passed with `--archive PATH`, and a compiler with `--compiler PATH`.

In the app, choose **Engine → Difficulty → Personality opponents…**. Select
Tal, Kasparov, Morphy, Karpov, Petrosian or Default, then set a target Elo from
800 to 2800 or choose Full strength. Personality and rating are independent;
the historical names describe style inspirations. Elo values are approximate.

Opening choices are **No book**, **Personality repertoire** (the default), or
**Custom book**. Repertoire moves can exceed the selected strength. Custom
books use the app's existing Polyglot reader; Rodent's internal book is disabled
in that mode. Native Rodent personalities own move selection, so the app's
Active/Quiet adjustment is bypassed. Stockfish still supplies analysis.

Settings and bookmarks retain the personality, target Elo and opening choice.
Missing or changed bookmarked resources cause restoration to fail while retaining
the working engine. Changing an opponent loads a fresh Rodent process so settings
from the previous personality cannot carry over.

This installs the engine for running from the source workspace. Existing frozen
application folders and installers are not rebuilt by this command.
See [Rodent source and build details](../docs/licensing/RODENT_IV.md).
