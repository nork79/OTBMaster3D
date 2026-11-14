# OTBMaster3D user guide

## Practice difficulty

The difficulty menu and engine settings show only installed levels.
Fairy-Stockfish provides practice targets from 500 through 1500; Stockfish
provides higher targets and full strength. Labels show approximate difficulty.
These settings are not measured human Elo ratings. No external models are needed.
See [engine setup](../engines/README.md) for the complete list.

## Game details and player names

Use **Game → Edit Game Details** to edit Event, Site, Date, White, Black and Round.
Save applies the fields to PGN export and session recovery; Cancel discards edits.
Comments, variations, moves and results are preserved.

New games use today's local date and place the loaded engine's name on its colour.
The name includes its configured strength, for example `Stockfish 19 (1900 Elo)`,
and the PGN includes the matching `WhiteElo` or `BlackElo` tag. Unlimited engines
show `Full strength` without an invented rating. Practice ratings are approximate.
Saving an edited human name remembers it automatically, including after restarting
the app. Against an engine, your name goes on the opposite colour. In a two-human
game, the remembered name identifies your colour, defaulting to White. Editing
other details leaves the remembered name unchanged. Switching sides before moves
have been played swaps PGN names and Elo tags. Details edited before starting are
kept when play begins. Imported names and dates are retained until you edit them.
Dates use `YYYY.MM.DD`; unknown parts can use `?`,
for example `2026.??.??`. Empty text fields become PGN's unknown value `?`.

## Untimed play

In the time-control settings, select **Infinite (clocks disabled)**. Both clocks
show ∞, there is no countdown or timeout, and manual clock presses are unnecessary.
Engines still make moves normally. The Start/Pause/Resume button sits directly
below the Black clock; in untimed games it pauses or resumes play. Session recovery
preserves untimed mode and restores the game paused.

## Automatic draws

The game ends automatically on threefold repetition, the fifty-move rule
(100 half-moves without a pawn move or capture), stalemate or insufficient
material. Repetition uses the played move history; a FEN alone cannot restore it.
Draw conditions apply after the move is played, with checkmate taking precedence.
There is no Claim draw button or menu action.

## Run on Windows

Install 64-bit Python 3.13 and use a graphics driver that supports OpenGL 2.1.
Tkinter is needed for the full test suite and installer build, not for the normal
Qt app launch. From the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools/install_stockfish.py
.\.venv\Scripts\python.exe tools/install_fairy_stockfish.py
.\.venv\Scripts\python.exe main.py
```

Python 3.13 is the supported source and test runtime. The pinned `cozy-chess-py`
wheel is built for Python 3.13 on Windows; use a fresh 3.13 environment if your
existing `.venv` uses another version. See the dated
[Python 3.13 compatibility baseline](python-313-compatibility.md) for that
specific test run.

For an installed copy, use the [GitHub Releases page](https://github.com/nork79/OTBMaster3D/releases)
and choose the installer and matching source files for the same version. Check
the version in **Help > About** against the download. The current source tree is
version 1.8.0; clean installation, upgrade, and uninstall results must be taken
from the selected release's own validation record. The app opens one window.
The optional Stockfish setup downloads the official Windows x64 release,
verifies its SHA-256 hash, and preserves its source and licence. Unavailable
difficulty levels are hidden. Skip engine setup to play without an engine.

## Reset a study position

Use **Reset board and clocks** beside the engine toggle to return to the last
opened bookmark and reset both clocks. If that bookmark is unavailable, the board
returns to the initial chess position. Clocks remain paused.

## Board and pieces

**Settings → Board Type** offers Classic, Polished Marble, Rounded Oak,
Tournament Wood, Canvas Roll-up and Marble & Brass. These use distinct board
profiles and bundled ambientCG CC0 material maps. They switch immediately and
the choice is remembered. Textures also appear in 2D.

**Settings → Board Color Theme** controls square/frame colours independently
of board type. Marble veining, wood grain and fabric weave are tinted by those
colours. See [board material sources and licences](../assets/boards/README.md).

Use **View → 3D board / 2D board** to change views instantly.
The 2D board initially fits the window and supports clicking, dragging and flipping.
Scroll up to zoom in or down to zoom out in either view. Left-drag an empty area
to reposition the board. Each view remembers its own zoom and pan; Reset View
restores the current view's defaults without changing the game.
Switching back restores your 3D camera. View, piece set and appearance preferences
are saved locally in `config.json`.

**View → 3D piece set** changes the 3D pieces immediately:

| Set | Appearance |
| --- | --- |
| Tournament Staunton | Sourced 3D Staunton models in satin ivory and black; the default. |
| Wooden Staunton | The same models in boxwood and rosewood colours. |
| Classic Club | Procedural pieces with traditional silhouettes. |
| Sci-fi Vehicles | Drummyfish's CC0 tanks, vehicles and towers. |

**View → 2D piece set** independently selects Classic, Textbook (Cburnett),
Chessnut, Firi, Fantasy, Celtic, Spatial, Skulls or Eyes. Textbook provides
traditional black-and-white diagram pieces. Classic matches the 3D set's
colours. Both choices are remembered; see assets/pieces_2d for artwork credits.
Light/dark squares, frame colour, background colour and background images are
shared between views. Board presets include Wood, Tournament Green, Blue and Grey.
The previous Original option has been removed; saved selections migrate automatically.

**Settings → Colours → White pieces / Black pieces** changes each side's colour
in both 2D and 3D, with live preview. Accept saves the choice; Cancel restores
the previous appearance. Custom colours remain when switching piece sets.
**Reset piece colours** restores the selected sets' original colours.

## Controls

**View → Energetic overlay**, directly below Move indicator, colours squares
with translucent yellow for White influence, green for Black influence, and red
for both. Yellow and green use 35% opacity; shared-influence red uses 60% to
stand out while preserving the underlying texture.
Each piece is evaluated in isolation: sliding rays ignore all blockers,
pawns influence their capture diagonals, and kings influence adjacent squares.
A piece does not influence its own square, though another piece may influence
that square. The overlay follows the displayed position in 2D and 3D, including
review and variation previews, and the setting is remembered.

Sessions are recovered automatically on reopening, including the full game or
loaded position, move-review position and remaining clock times. Clocks always
restore paused. Moves and menu actions are saved immediately, clocks are
checkpointed every second, and quitting saves once more. Atomic local snapshots
and a previous-save backup protect against interrupted writes. A crash can lose
up to about one second of clock time. Use New game or Reset board to start fresh.
Session files live beside config.json and are excluded from Git.

**Settings → Piece movement speed** adjusts animation from Instant (the default)
to 1.5 seconds per move in both 2D and 3D. The choice is saved; game clocks and
move timing remain unchanged.

| Action | Control |
| --- | --- |
| Move a piece | Click source then destination, or drag and drop. |
| Promote a pawn | Choose Queen, Rook, Bishop or Knight. Cancel leaves the pawn in place. |
| Rotate the 3D board | Right-drag or Ctrl + left-drag. |
| Pan the board (2D or 3D) | Left-drag an empty area; dragging a movable piece moves that piece. |
| Zoom the board (2D or 3D) | Mouse wheel up to zoom in; down to zoom out. |
| Flip the board | View → Flip board or Ctrl + F. |
| Switch playing sides | Game → Switch sides or → beside Take Back; clocks pause. |
| Manage bookmarks | Bookmarks → Manage Bookmarks or Ctrl + Shift + B. |
| Take back a move | Game → Take back or U. |
| Restore the view | View → Reset view or Ctrl + R; the chess position is preserved. |
| Show/hide sidebar | View → Show sidebar or Ctrl + B. |
| Focus mode | View → Focus mode or Ctrl + Shift + F. |
| Fullscreen | F11; Escape leaves fullscreen. |
| Start/pause | Sidebar button or Ctrl + P. |
| Close the app | Game → Quit or Ctrl + Q. |

## Sidebar and opening recognition

The opening name and ECO code appear directly below the move navigation icons,
above **MOVE LIST**. Detection uses the bundled Lichess opening lines and works
offline. It follows the displayed move history, including move review and takeback,
and retains the most specific matched line as play continues. The label stays blank
when no line matches. Recognition uses the recorded move order from the normal
starting position; a standalone FEN does not supply opening history.

Captured white piece symbols always appear on the left and captured black piece
symbols on the right, regardless of board orientation. These show pieces lost by
each colour. The number beside them is White's material minus Black's material.

Use the microchip icon beside **Switch Sides** to enable or disable engine play.
A cross through the icon means the engine is off; the tooltip also reports the state.
This control is separate from **Start analysis / Stop analysis** in Engine Analysis.

## Engines and opening books

Open **Engine → Engine and opening book**. Choose a supported Windows UCI engine
from `engines/` or browse for one, choose its side, and Save. Loading runs in the
background. Leave the engine path empty to unload it. Engine side and opening
book selections apply to the next game.

The current Windows packaging configuration includes Stockfish, Fairy-Stockfish,
and Rodent IV. Source workspaces can install the first two with the commands in
[engine setup](../engines/README.md); Rodent is built separately and offers Tal,
Kasparov, Morphy, Karpov, Petrosian, and Default personalities, independently of
target Elo. Engine availability depends on the installation and selected build.

The setup command installs Stockfish 19 for Windows x64 under `engines/stockfish-19/`, with its
source and GPLv3 licence. It loads automatically on first use and plays Black;
subsequent launches load the previously selected engine. An explicit unload is remembered.
Choose a Polyglot `.bin` book from the dropdown or browse for one. Three bundled
books use Lichess's CC0 opening data: all openings (default), 1.e4, and 1.d4.
These are repertoire collections, with weights based on the number of named
lines, not game-result statistics. See [book provenance](../books/README.md).

The engine dialog offers **Full strength** or an approximate Elo target within
the loaded engine's supported range (1320–3190 for this Stockfish build).
**Balanced** uses the engine's chosen move. **Active** favours checks and captures;
**Quiet** favours other moves among candidates evaluated within 0.35 pawns of
the original choice. These app-level preferences require MultiPV support, use
extra search time, and can affect the effective rating. Book moves bypass strength
and style controls; select an empty book entry to use the engine on every move.
Strength and style are remembered and apply to subsequent engine searches.

Analysis is off by default; **Engine → Analyse position** enables or disables it.
The choice is remembered. The expandable
Engine output panel shows the evaluation from White's perspective, depth and a
SAN best line. Completed engine-move searches are labelled **Last search** so they
are not mistaken for analysis of the current position. Analysis yields to engine
moves and ignores results belonging to an older position.

**Start analysis / Stop analysis** in Engine Output also controls line calculation.
Stopping analysis lets the current short search finish and leaves engine moves enabled.
The separate **Position evaluation** sits inside Engine Output and hides when it is collapsed
unless **Engine → Always show static evaluation** is enabled, which moves it beside
the **MOVE LIST** heading. This preference is remembered. The evaluation
updates immediately for moves, imports and history navigation. It estimates
material, piece placement and pawn structure without searching moves or using
Stockfish; tactical engine evaluations can differ. Both scores use pawn units,
with positive values favouring White and negative values favouring Black.

## Lichess online play

Lichess play needs a working internet connection and a Lichess account. Open the
**Lichess** menu and choose **Login / Account Settings**. Sign in in the browser
with OAuth (PKCE), or create and paste a Lichess personal access token. The token
needs these scopes: `board:play`, `challenge:read`, and `challenge:write`. The
optional username must match the account returned by Lichess. Use **Verify
Connection** after saving a token if the menu still shows it as unverified.

The app stores the bearer token in `lichess_auth.json` under its user-data
directory. This file is ordinary JSON and is not encrypted by the app. Keep it
private. **Logout** removes the local credentials and asks Lichess to revoke the
token. In a source run, user data is beside the checkout; in a packaged Windows
run, it is under `%LOCALAPPDATA%\OTBMaster3D`.

### Challenge a player or bot

Choose **Lichess > New Challenge / Seek**. In **Challenge a Player by Username**:

1. Select a listed online bot, or type a Lichess username. Use **Refresh** to
   fetch the current online bot list. The app shows profile text and available
   ratings; avatar, flair, and flag images are displayed when Lichess provides
   usable data or assets.
2. Online bots are ordered from lower to higher by the average of their available
   ratings. Bots with no ratings are listed last, alphabetically.
3. Choose a listed time control or **Custom**, a colour (random, White, or Black),
   and Casual or Rated. Direct challenges support the listed Hyperbullet through
   Classical controls; custom initial time is 1-180 minutes with a 0-180 second
   increment.
4. Select **Send Challenge**. The dialog waits for the Lichess event stream. It
   reports when the opponent accepts, declines, or cancels. While waiting, use
   **Cancel** to cancel the pending outgoing challenge.

Incoming challenges are not presented or accepted in this app. Accept or decline
them in the Lichess website or another Lichess client. The app only manages the
outgoing challenge it sends from this dialog.

### Quick Pairing

Select **Quick Pairing (Lobby Seek)** to search the public Lichess lobby. This
Board API flow supports Rapid and Classical controls with an estimated duration
of at least eight minutes (for example, 10+0). Choose colour and Casual or Rated,
then select **Find Opponent (Seek)**. Use **Cancel** to stop searching. When
Lichess matches the seek, the app opens the live game.

### Live game controls

Moves and clocks synchronize with Lichess. The menu shows the opponent and game
state and provides **Offer / Accept Draw**, **Request / Accept Takeback**, and
**Resign / Abort Online Game**. Resigning or aborting requires confirmation.
Post-game ratings are refreshed for rated games when Lichess makes them
available. Local engine play and analysis are disabled during live Lichess play
and restored when that game ends.

### Game history

Select **Lichess > Game History…** (`Ctrl+Shift+H`) to browse your recent
Lichess games with date, variant/speed, opponent, result, opening, and move
count. Select any game and click **Load into Board** (or double-click a row) to
import its PGN into the local 3D board for replay and analysis, or open it on
Lichess in your browser.

### Troubleshooting and limits

- If browser sign-in does not finish, allow the local `127.0.0.1` callback and
  return to the app. If that is blocked, use a personal access token instead.
- If token login or an API action is denied, check that the token is current and
  includes all three required scopes. **Verify Connection** checks the saved
  account; **Logout** followed by a new sign-in replaces a stale token.
- If no bots appear, check the connection and press **Refresh**. A profile image
  can be missing even when the bot can still be challenged.
- A listed bot may go offline before a challenge is sent. Lichess can reject a
  challenge if the user is unavailable or the chosen mode or time control is not
  accepted.
- If a live game stream is interrupted, the app reports the connection error
  but does not automatically restore the stream. The Lichess server remains
  authoritative; use the Lichess website or client to check and manage that game.

Lichess integration is separate from the local **Online** clock mode described
below. That clock-mode label means the app switches clocks automatically after
a move; it does not mean a game is connected to the internet.

## Clocks

Use **File** to open PGN games or FEN positions, save PGN/FEN, copy either format,
or paste a FEN. Multi-game PGNs offer a game chooser. Imports leave clocks stopped.
Unchanged imported PGNs retain headers, comments and variations when saved;
the move list displays the main line. PGN saves the full game, while FEN saves
the position currently displayed.

When clocks are paused or inactive, click a move to view its position. Browsing
preserves the full game and does not change the clocks. Use **Game → Go to starting
position** or **Return to latest move** to navigate. Resuming an active game's clock
returns to its latest position automatically. Earlier positions are read-only.

Open **Settings → Time control and clock** to choose a preset from hyperbullet
through classical, or a custom initial time and increment in seconds. Saved
settings immediately reset both clocks to the selected time control and pause them.
Resume when ready to continue.

- **Online** clock mode switches clocks automatically after moves. It is a local
  clock setting; Lichess online games are started from the separate **Lichess** menu.
- **OTB** mode requires the human player to move and then press the configured
  clock input: Spacebar, Right Mouse, middle mouse, Mouse Button 4 or Mouse Button 5.
  With Right Mouse selected, use Ctrl+left-drag to rotate the 3D board.
- Clicking the active clock card also completes the turn in OTB mode.
- While paused, click either clock to adjust its minutes and seconds. Save changes
  only that clock and leaves the game paused; Cancel keeps its previous time.
- Engine moves complete their clock action automatically.
- The sidebar Start/Pause button controls play; Game → Reset clock resets the timers.
- Colours, board themes, backgrounds and sound are in Settings.
- **Settings → Interface theme** switches instantly between Light, Dark, Blue,
  Cyberpunk, Pink/Lollipop, Forest, Midnight Ocean, Amethyst, Ember, Nordic Frost,
  Warm Paper and High Contrast. Your choice is remembered independently of board colours.
- Colour dialogs preview changes live on the board. Cancel restores the original
  colour and keeps any background image; OK saves the new colour.

`config.json` stores preferences, while `session.json` stores automatic game
recovery. The packaged app stores these files under
`%LOCALAPPDATA%\OTBMaster3D`; source runs keep them beside the checkout. PGN/FEN
import and export are supported. A built-in saved-game library is not
implemented; use [Bookmarks](bookmarks.md) to organize positions and
[session recovery](bookmarks.md#recovery-and-extensions) to understand saved state.

## Tests

The Windows CI workflow runs on pushes, pull requests, and manual dispatches.
It uses Python 3.13, installs the pinned dependencies, checks Python syntax,
then runs selected tests without a graphics context. A second job installs
Stockfish and Fairy-Stockfish for engine integration coverage. Other native
Qt/OpenGL and Tk tests are part of the local suite.

```powershell
powershell -NoProfile -File tools/setup_test_env.ps1 -Python C:\path\to\Python313\python.exe
.\.venv-test\Scripts\python.exe -m unittest discover -s tests -v
```

The suite includes rules and en-passant/repetition correctness, documents,
bookmarks, assets, settings, engine contracts, Lichess behavior, UI input and
clock interactions. Rendering and some desktop tests need a working Windows
graphics environment. Refer to a dated report before treating any test result as
evidence for a particular release.

## Code structure

Production chess-library integration lives in `otb_chess/chess_backend/`.
Python-chess remains a runtime dependency; the separate `otb_chess_core`
candidate is not used for production rules. See the [engineering overview](engineering.md)
and [migration status](chess-backend-migration.md).

`main.py` and `otb_chess/__main__.py` both launch the same Qt application.
The UI imports the controller directly; application modules do not import either
launcher.

```text
main.py                 # Normal launch: python main.py
otb_chess/
    __main__.py         # Or python -m otb_chess
    version.py
    core/               # Game controller, clocks, documents, input and appearance
    graphics/           # Board rendering and 2D/3D pieces
    ui/                 # Qt desktop window, feature dialogs, themes, legacy host
    services/           # Settings, engines, bookmarks, sessions, Lichess and audio
    chess_backend/      # Production python-chess adapters
otb_chess_core/         # Experimental, separate chess rules adapter
assets/                 # Bundled piece models and licences
tests/                  # Regression tests and UCI fixture
tools/                  # Setup, build, verification and asset tools
```

Source runs store settings, auth, bookmarks, and recovery files in the project
folder. Frozen builds use `%LOCALAPPDATA%/OTBMaster3D` for user data; engines and
books live beside the application. Both launch commands work from the project
folder.

| Module | Responsibility |
| --- | --- |
| `otb_chess/ui/desktop_ui.py` | Qt window, widgets, menus, dialogs and event loop |
| `otb_chess/core/game.py` | `Chess3D` controller, game state, legal moves and game lifecycle |
| `otb_chess/core/clocks.py` | Timing, increments, pauses and manual clock presses |
| `otb_chess/services/engine.py` | UCI process lifecycle and background move requests |
| `otb_chess/services/lichess.py` | Lichess auth, challenges, bot data and Board API streams |
| `otb_chess/services/session.py`, `bookmarks.py` | Session recovery and atomic bookmark persistence |
| `otb_chess/graphics/rendering.py` | Board drawing, camera projection and picking |
| `otb_chess/core/board_input.py` | Pointer gestures, camera movement and GLFW callbacks |
| `otb_chess/core/appearance.py` | Board appearance, texture lifecycle and preference persistence |
| `otb_chess/graphics/gl_primitives.py` | OpenGL setup, geometry, materials and coordinate glyphs |
| `otb_chess/services/settings.py` | Paths, defaults, time controls and configuration storage |
| `otb_chess/services/audio.py` | Sound generation and playback |
| `otb_chess/ui/legacy_ui.py` | Previous Tk host, retained for regression coverage |
| `otb_chess/graphics/piece_sets.py`, `otb_chess/graphics/board_2d.py` | 3D models and flat piece rendering |
| `otb_chess/ui/interface_themes.py` | Qt interface palettes |

`Chess3D` owns the shared mutable game state. Its focused behaviour classes are
mixins, not independent copies of that state. The Qt `DesktopGame` subclass
supplies UI-specific hooks. Rendering methods require a current OpenGL context;
engine workers publish results for the UI thread to apply. Settings and audio
do not depend on the controller or UI. Keep new features in the module that owns
their responsibility rather than adding application logic to `main.py`.

## Assets and licences

**Help > Open Source Licences** displays the full GPL, third-party notices and
source-access instructions offline. **Help > About** shows the version, copyright
and repository link. See [THIRD_PARTY_LICENSES.md](../THIRD_PARTY_LICENSES.md).
The application is GPL-3.0-only; recipients retain redistribution rights.
Each installer must be paired with its exact source snapshot. Use the release
archive for the version installed; the current 1.8.0 source branch is not a
substitute for an older binary's corresponding source. See
[source access](../SOURCE_ACCESS.md) and
[CONTRIBUTING.md](../CONTRIBUTING.md).

The bundled Staunton meshes are by
[clarkerubber](https://github.com/clarkerubber/Staunton-Pieces), copyright 2014,
and distributed under the [MIT licence](../assets/pieces/tournament/LICENSE).
See [asset documentation](../assets/pieces/README.md) for provenance, conversion
instructions and the format for adding complete custom sets.

Dependency licences are separate from the model licence. In particular,
[python-chess](https://python-chess.readthedocs.io/en/latest/#license) is
GPLv3-or-later. The models' MIT licence is not a licence for the whole application;
redistribution must account for the applicable dependency obligations.
PySide6/Qt also have their own licences; see the installed packages and
[Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).

Local configuration, saved games, build outputs, virtual environments and downloaded
engine binaries are excluded from Git. The three small CC0 opening books are tracked.
