# Engineering overview

This overview describes the current **1.8.0** source tree. OTBMaster3D is a
Windows desktop chess application built with Python, PySide6, and OpenGL. The
normal application host is Qt; the retained Tk/GLFW host is used by legacy
regression coverage, not as the standard launch path.

## Runtime architecture

```text
main.py or python -m otb_chess
    -> otb_chess.ui.desktop_ui.run()
    -> Qt desktop window and DesktopGame controller
        -> core game, clock, document, and appearance logic
        -> services for settings, engines, bookmarks, recovery, and Lichess
        -> graphics for 2D/3D board and piece rendering
        -> chess_backend adapters -> python-chess
```

`main.py` handles the normal launch and the packaged `--smoke-test` entry point.
`otb_chess/__main__.py` calls the same Qt `run()` function for module launches.
`DesktopGame` connects the UI to the shared `Chess3D` game controller. Focused
controller behavior is split across core mixins; those classes share the same
mutable game state rather than maintaining parallel copies.

## Packages and responsibilities

| Area | Main responsibilities |
| --- | --- |
| `otb_chess/ui/` | Qt desktop window, menus, dialogs, analysis, bookmarks, Lichess, and position setup |
| `otb_chess/core/` | Game lifecycle, clocks, input, documents, evaluation, and appearance state |
| `otb_chess/graphics/` | Board and piece rendering, board materials, 2D view, and picking support |
| `otb_chess/services/` | Engine processes, settings, session recovery, bookmarks, audio, and Lichess API access |
| `otb_chess/chess_backend/` | Production rules, notation, UCI, opening-book, position, and opening adapters |
| `otb_chess/bookmarks.py` and `document_state.py` | UI-independent bookmark data and application-owned document/history records |
| `otb_chess_core/` | Separate experimental cozy-chess-backed rules adapter; not used as the production rules provider |
| `assets/`, `books/`, `engines/` | Piece/board/audio resources, Polyglot books, and external UCI engine resources |

Production chess rules, PGN notation, UCI transport, and Polyglot reading still
use python-chess through `otb_chess/chess_backend`. The boundary reduces direct
provider access; it does not replace python-chess. The experimental
`otb_chess_core` package is not a drop-in replacement and has not been wired into
production play. See [the production boundary notes](chess_core_architecture.md)
and [migration status](chess-backend-migration.md).

## State, persistence, and integrations

- **Preferences:** `services/settings.py` saves `config.json` atomically. Source
  runs keep user data beside the checkout. Frozen Windows builds use
  `%LOCALAPPDATA%\OTBMaster3D` for preferences, Lichess credentials, session
  recovery, bookmarks, and generated sounds; application resources remain beside
  the installed program.
- **Session recovery:** `services/session.py` writes the current PGN/document,
  review position, and clock state to `session.json` with a backup. Clocks restore
  paused. This is local recovery, not a saved-game library.
- **Bookmarks:** `services/bookmarks.py` stores the nested bookmark collection
  in `bookmarks.json`; `services/bookmark_actions.py` validates and applies
  transactional UI edits. Opening a bookmark keeps the current engine and clock
  settings and pauses clocks.
- **Chess documents:** PGN/FEN parsing and export are routed through
  `core/documents.py`, `document_state.py`, and the notation adapter. PGN preserves
  move history and annotations; FEN represents only one position.
- **UCI engines:** `services/engine.py` starts separate engine processes and
  coordinates background move and analysis requests. Production presets use
  Stockfish and Fairy-Stockfish; Rodent IV supplies personality opponents.
- **Lichess:** `services/lichess.py` handles OAuth2 PKCE or personal access token
  authentication, online bot data, direct challenges, Quick Pairing seeks, and
  Board API game streams. `ui/lichess_dialog.py` provides login, challenge, and
  bot-profile UI; `desktop_ui.py` applies live events to the game controller.
  A live Lichess game disables local engine play and analysis.

Network work and engine searches run on worker threads. Results are handed back
to the Qt thread before changing UI state. Rendering calls require a live OpenGL
context; headless tests avoid those paths or use the configured native test
environment.

## Tests and CI

The test suite covers chess correctness, PGN/FEN handling, persistence,
bookmarks, engine contracts, Lichess service/UI behavior, settings, assets, and
desktop interactions. Some UI and rendering tests need a Windows desktop with
Tk and native OpenGL. Live engine tests additionally need installed Windows
engine binaries.

The Windows Actions workflow uses Python 3.13 and has two jobs:

- `test` installs `requirements.txt`, compiles the application and test modules,
  then runs tests selected to work without a graphics context.
- `engine-integration` installs Stockfish and Fairy-Stockfish and runs the live
  UCI integration classes. Rodent tests run when its separately built resources
  are present.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the local test setup. The workflow
configuration is not a claim that a particular checkout has passed; see a
version-specific validation record for recorded results.

## Windows build and packaging

`tools/build_installer.ps1` coordinates the Python 3.13 checks and build steps.
`packaging/windows-folder.spec` defines the PyInstaller onedir application
folder, including reviewed Qt/OpenGL runtime files, assets, engines, books,
notices, and staged corresponding source. `packaging/windows-installer.iss`
builds a per-user installer with Inno Setup. The setup checks for Microsoft
Visual C++ x64 Redistributable 14.44.35211.0 or newer; that runtime is installed
separately and is not bundled. The installer is not configured for signing.

Build prerequisites include Python 3.13 with Tkinter, PyInstaller 6.22.3, Inno
Setup, and the reviewed native build inputs described in
[the Windows installer instructions](windows-installer.md). The current package
configuration targets Windows 10 or later on x64. A source build or CI result
does not establish clean-machine install, upgrade, or uninstall behavior; check
the matching version's release notes for those results.

## Further reading

- [User guide](user-guide.md)
- [Bookmark model and storage](bookmarks.md) and [bookmark UI](bookmark-ui.md)
- [Windows installer build and validation](windows-installer.md)
- [Current changelog](../CHANGELOG.md)
- [Version-specific release records](releases/)
- [Maintenance policy](MAINTENANCE.md)
