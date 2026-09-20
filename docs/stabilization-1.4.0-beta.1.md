# 1.4.0-beta.1 stabilization report

## Scope and files changed in this pass

Existing uncommitted development work was preserved. No feature expansion,
UI redesign, broad refactoring, publishing, pushing or remote release was performed.

- `otb_chess/version.py`, `packaging/version-info.txt`, `packaging/windows-installer.iss`: consistent 1.4.0-beta.1 version metadata.
- `otb_chess/services/settings.py`, `otb_chess/core/appearance.py`, `otb_chess/ui/bookmark_panel.py`, `otb_chess/ui/desktop_ui.py`: atomic preference saves and bookmark geometry persistence.
- `otb_chess/services/session.py`, `otb_chess/ui/desktop_ui.py`: removed three clearly unused imports.
- `.gitignore`: ignore interrupted preference-save temporary files.
- `tools/prepare_installer_payload.py`: include new project source/documentation files in local source archives before Git staging.
- `otb_chess/packaging_smoke.py`: explicitly enable opt-in analysis before checking its result.
- `tools/build_installer.ps1`: fail early if Tcl cannot initialize instead of silently building an application missing Tkinter.
- `tests/test_settings.py`, `tests/test_bookmark_ui.py`: preference failure and restart regressions.
- `README.md`, `CHANGELOG.md`, `docs/windows-installer.md`, `docs/bookmark-ui.md`, `docs/releases/1.4.0-beta.1.md`, this report: current release and persistence documentation.

## Genuine defects corrected

1. Bookmark panel dimensions were retained only while the same window existed. Size and position now save in the existing preferences file, restore after restart, and clamp to the screen. Older preferences use the existing defaults, including 80% main-window height.
2. Preference saves directly truncated the existing file. They now flush a temporary file and atomically replace the destination; failures retain the old preferences and log a diagnostic.
3. Installer source archives used only Git-tracked paths, omitting newly added bookmark modules in an unstaged local build. New files in project source/documentation directories are now included without collecting personal settings, bookmarks or saved games.
4. PyInstaller could continue after excluding Tkinter when Tcl initialization failed. The normal build now checks this prerequisite first.

5. The packaging smoke test still assumed analysis started by default. It now explicitly requests analysis; the README was corrected without changing application defaults.

## Validation

- Python 3.13.12; pinned application dependencies. `pip check`: no broken requirements.
- Syntax compilation: passed for entry point, application, core, tests and tools.
- No missing local import targets, accidental application print/debug statements or stale TODO/FIXME markers found. `git diff --check` passed.
- Focused tests: atomic-save success/failure, legacy preference compatibility, bookmark window restart and ordered tree/menu restoration passed. The new restart test initially compared the unordered node table directly; its assertion was corrected to compare nodes by UUID while retaining child-order checks.
- Full suite run **once**: `python -m unittest discover -s tests -v`. 161 tests passed; one additional test-class setup errored because the sandbox blocked Tcl initialization. No assertion failures.
- Focused rerun outside sandbox: all 5 `tests.test_piece_sets.LiveSwitchTests` passed. **166 tests passed in aggregate, zero outstanding test failures.** The full suite was not repeated.
- Existing tests cover bookmark root/nested folders, moves/reordering and disk reload, corrupt/failed saves, menu/tree agreement, restoration from menu and panel, keyboard shortcut, inline editing, appearance, sound profiles, session recovery, clocks and game controls.
- Local full-suite log: `.tmp/regression-1.4.0-beta.1.log`; focused Tk log: `.tmp/tk-regression-1.4.0-beta.1.log`.

## Build/package

The first sandboxed build compiled an installer but excluded Tkinter; its packaged
smoke test failed at startup. Tcl initialization succeeded outside the sandbox,
confirming the environment restriction. The clean rebuild uses the same pinned
PyInstaller 6.22.3/Inno Setup 6.4.3 process with native desktop access.
Final packaged smoke test: **passed** (`.tmp/packaged-smoke-final-1.4.0-beta.1.json`).
The exact 1.4.0-beta.1 executable renders a 1226 x 969 framebuffer, loads bundled
Stockfish, produces a scored analysis, displays the expected menus and icon,
and reads all three opening books. The source smoke test also passed.

The payload contains all application assets, sounds, licences, Stockfish and
Maia resources, Tcl/Tk and cozy_chess. The source ZIP includes the new bookmark
modules and corrected smoke test, and excludes personal config/bookmark/session
files. A non-runtime book-placement instruction text file is intentionally not
part of the runtime payload.

Installer compilation: **passed**, normal `tools/build_installer.ps1` process.
Artifact: `installer-output/OTBMaster3D-1.4.0-beta.1-Setup.exe`.
Authorized metadata-cleaned rebuild: **passed** (2026-09-20).
New SHA-256: `0ec3097808e047fb1e0b8c3756a6359982695eee1b6947016af27d1a67b55bd6` (160,503,274 bytes).
New packaged smoke test: **passed**, `.tmp/private-release-smoke.json`.
Required resources and all 60 cleaned SVGs verified in the package and source archive.
The previous checksum is superseded; only this rebuilt installer is intended for the private release.
Standalone folder: `dist/OTBMaster3D`.
Build log: `.tmp/private-release-build.log`.
This report records final results after source-archive creation; the archive
contains the report's earlier checkpoint. Application source matches the final build.

## Deliberately unchanged and manual verification

- Retained legacy UI paths, public compatibility exports, historical release notes/source archives, old assets and local temporary research files where removal was not demonstrably safe. Existing build/cache directories are already ignored.
- Preserved all personal settings, bookmark data and saved games. Persistence tests use temporary configuration directories. Bookmark/session schemas are unchanged; geometry is an optional preference key.
- No broad validation rewrite for manually corrupted preference values, dependency upgrades, engine redesign or packaging redesign.
- The installer remains unsigned. Clean-machine installation, upgrade/uninstall preservation of real user data, multi-monitor/DPI placement and subjective sound/visual appearance need manual verification.
- OpenGL reports missing optional NumPy acceleration in this environment; rendering tests pass without it. No unnecessary dependency was added to silence the diagnostic.
- The stabilization pass left feature work uncommitted. The subsequent authorized private release preparation includes that validated work; no application functionality changed during release preparation.
