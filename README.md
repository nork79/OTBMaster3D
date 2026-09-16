# OTBMaster3D

**Version 7.3.1** - desktop chess with a tournament-style 3D board, a flat 2D view,
UCI engine support and over-the-board clock controls. Built for Windows with
Python, GLFW, OpenGL, Tkinter and python-chess.

## What's new in 7.3.0

- Switch between **3D and 2D** without resetting the game or clocks.
- Use **Tournament Staunton**, **Wooden Staunton** or **Classic Club** pieces.
- Keep your board colours, backgrounds and piece colours in either view.
- Correct starting-square orientation and pointer mapping.
- Access every setting through the scrollable controls panel.

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
The app opens a board window and a separate controls window.

## Board and pieces

Use **Board view: 3D / 2D** above the Piece set dropdown to change views instantly.
The 2D board initially fits the window and supports clicking, dragging and flipping.
Scroll up to zoom in or down to zoom out in either view. Left-drag an empty area
to reposition the board. Each view remembers its own zoom and pan; Reset View
restores the current view's defaults without changing the game.
Switching back restores your 3D camera. View, piece set and appearance preferences
are saved locally in `config.json`.

The Piece set dropdown changes the whole set immediately:

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
| Flip the board | Flip Board button or Ctrl + F. |
| Take back a move | Takeback button or U. |
| Restore the view | Reset View button; the chess position is preserved. |
| Close the board | Escape. |

## Engines and opening books

Place a compatible Windows UCI engine in `engines/`, or use **Browse** in the
engine controls. Choose the engine side and use **Load**. Engines are not bundled.

Place Polyglot `.bin` books in `books/`, or browse for one in the book controls.
Opening books are not bundled. Check the licences of any engines or books you distribute.

## Clocks

Choose a preset from hyperbullet through classical, or enter a custom initial
time and increment in seconds.

- **Online** clock mode switches clocks automatically after moves. This name
  describes clock behaviour; the app does not provide online multiplayer.
- **OTB** mode requires the human player to move and then press the configured
  clock input: Spacebar, middle mouse, Mouse Button 4 or Mouse Button 5.
- Engine moves complete their clock action automatically.
- Stop Clock and Reset Clock operate independently of Reset Board.

Game export/import and saved-game restoration are not implemented. `config.json`
saves preferences, not the current game.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The eight tests cover complete assets, custom-set loading, live switching,
configuration persistence, 2D click/drag moves and all 64 squares in both
orientations and landscape/portrait windows, plus wheel zoom and 2D panning. Rendering tests create hidden
OpenGL and Tk windows and require a working graphics environment. They do not
write to the user's configuration.

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

Local configuration, temporary files, virtual environments and engine/book
binaries are excluded from Git.
