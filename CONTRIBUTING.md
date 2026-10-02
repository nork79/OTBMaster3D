# Contributing

OTBMaster3D is a free, open-source application under GPL-3.0-only.
Contributions to application code are submitted under the same licence. Keep
third-party attribution and licence files with imported code or artwork.

Use Python 3.13 on Windows, install requirements.txt in a virtual environment,
and run `python -m unittest discover -s tests -v`. Rendering tests require native
OpenGL and Tk. The CI workflow runs tests that do not need a graphics context.

Windows CI has two jobs, both using Python 3.13:

- `test` installs only Python dependencies, compiles the application, owned chess
  core, tests and tools, and runs the existing headless suite. It selects
  `tests.test_difficulty.DifficultyTests` and
  `tests.test_engine_features.EngineFeatureTests` for engine contracts without
  launching downloaded executables.
- `engine-integration` runs `tools/install_stockfish.py` and
  `tools/install_fairy_stockfish.py`, checks that all difficulty executables are
  present, then runs only the live engine classes and optional Rodent tests.

To run the live tests locally on Windows after [installing the engines](engines/README.md):

```powershell
python -m unittest -v tests.test_difficulty.DifficultyIntegrationTests tests.test_engine_features.EngineIntegrationTests tests.test_bookmark_ui.BookmarkEngineIntegrationTests tests.test_rodent
```

These tests check real UCI options, legal moves, strength/style handling and
bookmark restoration. Discovery skips them when their Windows executables are
unavailable. Rodent tests require its separate MinGW build and installed resources;
CI does not build or download Rodent.

On Windows, create a dedicated test environment with
`powershell -File tools/setup_test_env.ps1 -Python C:\path\to\Python313\python.exe`
(omit `-Python` to discover a registered 3.13 installation). Then run
`.\.venv-test\Scripts\python.exe -m unittest discover -s tests -v`.
The existing `.venv` may use Python 3.14, which cannot load the pinned
`cozy-chess-py` 3.13 wheel; use `.venv-test` for the complete suite.

Please describe the problem, changed behaviour, and checks in pull requests.
Include a small regression test for game, engine or persistence bugs. Never commit
personal settings, game recovery files, virtual environments or downloaded engines.

For bugs, include reproduction steps, the version, board mode and relevant PGN/FEN.
See docs/windows-installer.md for the installer build and verification process.

You must have the right to submit your work. Original application contributions
are submitted under GPL-3.0-only; imported material must have compatible terms
and retain its provenance, notices and full required licence texts. Contributors
generally retain copyright in their original contributions. No copyright assignment
is required. Review and acceptance are discretionary; see docs/MAINTENANCE.md.
