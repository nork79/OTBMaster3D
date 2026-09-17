# Python 3.13 compatibility baseline

Date: 2026-09-17. Application: OTBMaster3D 8.4.0 at commit `e5ae410`,
with the Stage 0 renderer-cache expectation correction in the working tree.

**Result: 37/37 tests passed on CPython 3.13.12, Windows x64.**
No application, dependency-pin or chess-backend changes were needed.

## Environment

- Official [Python 3.13.12 Windows release](https://www.python.org/downloads/release/python-31312/),
  standard AMD64 build, MSC v.1944. Installer signature verified as valid,
  signed by the Python Software Foundation.
- Runtime installed under `.tmp/python313-check/runtime`, with Tcl/Tk and pip;
  no PATH, launcher or file-association changes requested.
- Separate virtual environment: `.tmp/python313-check/venv`.
  The existing Python 3.14 environment was retained.
- Existing `requirements.txt` installed successfully: glfw 2.10.2,
  PyOpenGL 3.1.10, chess 1.11.2, Pillow 12.3.0 and PySide6 6.11.2.
  `pip check` reported no broken requirements.
- Qt 6.11.2; Intel UHD Graphics; OpenGL 4.6.0, driver 32.0.101.6874.

## Checks

| Check | Result / evidence |
| --- | --- |
| Full suite | 37 tests in 26.610 seconds; OK, exit code 0; no skips |
| Application startup | Called actual `main.main()` with temporary settings and a smoke-test window subclass; Qt event loop started, valid nonempty framebuffer rendered, clean shutdown, exit code 0 |
| Qt | Full desktop integration tests passed, including controls, themes, layout, clocks and move animation |
| OpenGL | Qt and GLFW rendering tests passed; startup framebuffer check returned `GL_NO_ERROR` |
| PGN/FEN | Multiple games, FEN roots, black-to-move numbering, history, export and annotation/variation round trips passed |
| UCI fixture | Subprocess play/analysis and worker/stale-position tests passed using the existing fixture |
| Session recovery | History, review, clocks and backup recovery integration test passed |

The initial sandboxed suite ran 32 tests successfully but failed during legacy
Tk class setup: Tcl could not load its installed `init.tcl`, and the test's zip
fallback was unavailable in this installation. Repeating the unchanged suite
outside the sandbox passed all 37 tests. No Tcl paths, application code or tests
were changed to obtain that result. The optional NumPy OpenGL handler warning
was non-fatal.

Startup used an offscreen native widget (`WA_DontShowOnScreen`), real OpenGL
rendering and a timed close, rather than a manual visual inspection. Temporary
settings/session paths protected the user's saved state.

## Reproduction

From the repository root in PowerShell, using the retained local environment:

```powershell
.\.tmp\python313-check\venv\Scripts\python.exe -m pip install -r requirements.txt
.\.tmp\python313-check\venv\Scripts\python.exe -m pip check
.\.tmp\python313-check\venv\Scripts\python.exe -m unittest discover -s tests -v
.\.tmp\python313-check\venv\Scripts\python.exe main.py
```

Run the suite outside the restricted agent sandbox if Tcl loading fails as
described above. The final command launches the normal interactive application
and uses normal user settings. The automated startup helper and installation
logs remain local under ignored `.tmp/python313-check/`.

## Decision

Python 3.13 is a viable compatibility target for the current app on this Windows
machine. There is no observed application requirement to keep Python 3.14.
This supports evaluating the existing Python 3.13 replacement-library wheel
before committing to a custom Python 3.14 binding.

This stage did **not** install or test cozy-chess-py, validate its adapter API,
build a frozen distribution, or change the supported runtime in CI/docs/build
configuration. It therefore does not yet prove that a custom binding is entirely
unnecessary. Candidate-wheel and backend compatibility remain separate gates.

No chess migration was performed. Python-chess remains unchanged.
