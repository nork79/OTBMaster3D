# Contributing

OTBMaster3D is a free, open-source application under GPL-3.0-or-later.
Contributions to application code are submitted under the same licence. Keep
third-party attribution and licence files with imported code or artwork.

Use Python 3.13 on Windows, install requirements.txt in a virtual environment,
and run `python -m unittest discover -s tests -v`. Rendering tests require native
OpenGL and Tk. The CI workflow runs tests that do not need a graphics context.

Please describe the problem, changed behaviour, and checks in pull requests.
Include a small regression test for game, engine or persistence bugs. Never commit
personal settings, game recovery files, virtual environments or downloaded engines.

For bugs, include reproduction steps, the version, board mode and relevant PGN/FEN.
Installer development is paused for the source beta; packaging files are unfinished.
