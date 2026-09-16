# OTBMaster3D

**Version 8.0.0** - desktop chess with a tournament-style 3D board,
a flat 2D view, UCI engine support and over-the-board clock controls. The main
interface uses PySide6 and an embedded OpenGL board.

The previous zoom/pan release is available on GitHub as **v7.3.1**.

## New single-window interface

- The board fills the main area; a resizable sidebar keeps the clocks and moves visible.
- Large clock cards show the active player and can be pressed in OTB mode.
- Game, View, Engine and Settings menus keep occasional controls out of the way.
- Engine output collapses below the move table; it shows evaluation, depth and the best line.
- Focus mode keeps just the board and clocks. The sidebar can also be hidden entirely.
- Window size, sidebar width, Focus mode and engine-panel visibility are remembered.
- Five interface themes: Light, Dark, Blue, Cyberpunk and Pink/Lollipop.
- New-game clocks wait for the first move; paused clocks can be adjusted independently.

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Run on Windows

Install Python 3.14 with Tkinter support and use a graphics driver that supports
OpenGL 2.1. From the project folder:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

This is a source release; a standalone Windows installer is not included.
The app opens one window. When upgrading from 7.3.x, rerun the requirements
installation to add PySide6.

## Board and pieces

Use **View ? 3D board / 2D board** to change views instantly.
The 2D board initially fits the window and supports clicking, dragging and flipping.
Scroll up to zoom in or down to zoom out in either view. Left-drag an empty area
to reposition the board. Each view remembers its own zoom and pan; Reset View
restores the current view's defaults without changing the game.
Switching back restores your 3D camera. View, piece set and appearance preferences
are saved locally in `config.json`.

**View ? Piece set** changes the whole set immediately:

| Set | Appearance |
| --- | --- |
| Tournament Staunton | Sourced 3D Staunton models in satin ivory and black; the default. |
| Wooden Staunton | The same models in boxwood and rosewood colours. |
| Classic Club | Procedural pieces with traditional silhouettes. |

In 2D, all sets use flat chess symbols with the selected set's colours.
Light/dark squares, frame colour, background colour and background images are
shared between views. Board presets include Wood, Tournament Green, Blue and Grey.
The previous Original option has been removed; saved selections migrate automatically.

## Controls

| Action | Control |
| --- | --- |
| Move a piece | Click source then destination, or drag and drop. |
| Rotate the 3D board | Right-drag or Ctrl + left-drag. |
| Pan the board (2D or 3D) | Left-drag an empty area; dragging a movable piece moves that piece. |
| Zoom the board (2D or 3D) | Mouse wheel up to zoom in; down to zoom out. |
| Flip the board | View ? Flip board or Ctrl + F. |
| Take back a move | Game ? Take back or U. |
| Restore the view | View ? Reset view or Ctrl + R; the chess position is preserved. |
| Show/hide sidebar | View ? Show sidebar or Ctrl + B. |
| Focus mode | View ? Focus mode or Ctrl + Shift + F. |
| Fullscreen | F11; Escape leaves fullscreen. |
| Start/pause | Sidebar button or Ctrl + P. |
| Close the app | Game ? Quit or Ctrl + Q. |

## Engines and opening books

Open **Engine ? Engine and opening book**. Choose a compatible Windows UCI engine
from `engines/` or browse for one, choose its side, and Save. Loading runs in the
background. Leave the engine path empty to unload it. Engine side and opening
book selections apply to the next game.

Choose a Polyglot `.bin` book from `books/` or browse for one in the same dialog.
Engines and books are not bundled; check their licences before distributing them.

**Engine ? Analyse position** enables short background searches. The expandable
Engine output panel shows the evaluation from White's perspective, depth and a
SAN best line. Completed engine-move searches are labelled **Last search** so they
are not mistaken for analysis of the current position. Analysis yields to engine
moves and ignores results belonging to an older position.

## Clocks

Open **Settings ? Time control and clock** to choose a preset from hyperbullet
through classical, or a custom initial time and increment in seconds. Saved
settings update idle clocks immediately. During a game (including while paused),
settings apply to the next game; Reset clock applies the selected time control.

- **Online** clock mode switches clocks automatically after moves. This name
  describes clock behaviour; the app does not provide online multiplayer.
- **OTB** mode requires the human player to move and then press the configured
  clock input: Spacebar, middle mouse, Mouse Button 4 or Mouse Button 5.
- Clicking the active clock card also completes the turn in OTB mode.
- While paused, click either clock to adjust its minutes and seconds. Save changes
  only that clock and leaves the game paused; Cancel keeps its previous time.
- Engine moves complete their clock action automatically.
- The sidebar Start/Pause button controls play; Game ? Reset clock resets the timers.
- Colours, board themes, backgrounds and sound are in Settings.
- **Settings → Interface theme** switches instantly between Light, Dark, Blue,
  Cyberpunk and Pink/Lollipop. Your choice is remembered independently of board colours.
- Colour dialogs preview changes live on the board. Cancel restores the original
  colour and keeps any background image; OK saves the new colour.

Game export/import and saved-game restoration are not implemented. `config.json`
saves preferences, not the current game.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The 15 tests cover assets, complete-set loading, view switching, persistence,
2D input, zoom/pan, native Qt menus and layout, clock dialogs, clickable OTB clocks,
and UCI play/analysis through a deterministic subprocess fixture. Rendering tests
use invisible native OpenGL surfaces and require a working graphics environment.
The older renderer regression tests use GLFW/Tk; the normal app launch uses Qt.
Tests never write to the user's configuration.

## Assets and licences

The bundled Staunton meshes are by
[clarkerubber](https://github.com/clarkerubber/Staunton-Pieces), copyright 2014,
and distributed under the [MIT licence](assets/pieces/tournament/LICENSE).
See [asset documentation](assets/pieces/README.md) for provenance, conversion
instructions and the format for adding complete custom sets.

Dependency licences are separate from the model licence. In particular,
[python-chess](https://python-chess.readthedocs.io/en/latest/#license) is
GPLv3-or-later. The models' MIT licence is not a licence for the whole application;
redistribution must account for the applicable dependency obligations.
PySide6/Qt also have their own licences; see the installed packages and
[Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).

Local configuration, temporary files, virtual environments and engine/book
binaries are excluded from Git.
