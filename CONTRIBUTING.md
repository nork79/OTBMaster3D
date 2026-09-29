# Contributing

OTBMaster3D is a free, open-source application under GPL-3.0-only.
Contributions to application code are submitted under the same licence. Keep
third-party attribution and licence files with imported code or artwork.

Use Python 3.13 on Windows, install requirements.txt in a virtual environment,
and run `python -m unittest discover -s tests -v`. Rendering tests require native
OpenGL and Tk. The CI workflow runs tests that do not need a graphics context.

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
