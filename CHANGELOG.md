# Changelog

## Unreleased

- Keep captured white piece symbols on the left and black symbols on the right.
- Show the detected opening name and ECO code below move navigation, using bundled
  opening data. Follow move review and leave the label blank when no opening matches.
- Replace the full-width engine button with a microchip icon beside Switch Sides;
  the icon is crossed out when engine play is off.
- Refresh application screenshots with Rounded Oak, Polished Marble, Marble & Brass
  and Canvas boards, and Forest, Midnight Ocean, Amethyst and Warm Paper themes.

## 1.4.0-beta.1 - 2026-09-19

- Stabilization snapshot with bookmark folders, ordering, restoration and the Bookmarks menu.
- Preserve bookmark panel size and position across restarts.
- Write preferences atomically and include new project source files in local build archives.
- Retain the compact game controls, switch-sides action and timeout flag styling.
- See [release notes](docs/releases/1.4.0-beta.1.md).

## 1.2.0-beta.1 - 2026-09-18

- Add Maia difficulty presets, custom engine settings and persistent analysis state.
- Add position setup with live FEN and click-to-move editing, plus an interactive evaluation graph.
- Add eight sound profiles, improved pre-game clock editing, viewport-fitting Reset View and revised defaults.
- Update installer build support. See [release notes](docs/releases/1.2.0-beta.1.md).

## 1.0.0-beta.1 - 2026-09-18

First official public beta. Version numbering restarts at 1.0; earlier tags remain development history.
Application source is now GPL-3.0-or-later.

- Add instant static evaluation of the displayed position and an Engine Output start/stop analysis button.

- Queue New Game during engine startup/search so the first click starts the game when ready.

- Offer Queen/Rook/Bishop/Knight promotion choices and preserve engine/book underpromotions.

- Prepare installer scaffolding, an original gold-knight icon and per-user paths. Installer compilation remains paused; this release is source-only.
- Place Game before File in the menu bar.
- Add verified Stockfish 19 setup and three bundled Lichess-based opening books, with remembered engine selection.
- Add approximate Elo targets, Active/Quiet playing styles, and automatic current-position evaluation.
- Highlight selection, hover and completed moves; hide move dots on occupied squares.

## 8.6.0 - 2026-09-17

- Set Python 3.13 as the supported runtime and migration target in Windows CI,
  setup instructions and distribution planning.
- Add an independent cozy-chess-py 0.1.1 core with owned moves, FEN/history,
  special-move handling and material-only insufficient-material detection.
- Isolate PGN/SAN transfers using owned document/history snapshots while retaining
  the existing parser/writer, annotations, review and session recovery behaviour.
- Expand rules and integration coverage: all 69 tests pass. Production rules
  still use python-chess; UCI and Polyglot implementations remain unchanged.

## 8.4.0 - 2026-09-17

- Recover games, positions, move review and clocks automatically using atomic
  session saves and a backup; restored clocks always remain paused.
- Add compact move-history navigation, subtle legal-move dots controlled by the
  move-indicator setting, and right-click cancellation of selected pieces.
- Add saved movement animation speed, from Instant to 1.5 seconds, in 2D and 3D.
- Add eight built-in background options, including gradients, studio glow,
  textures and matching board colours.
- Add Sci-fi Vehicles in 3D and independent 2D selections: Fantasy, Celtic,
  Spatial, Skulls, Eyes, Textbook (Cburnett), Chessnut and Firi, with licence credits.
- Add Windows CI using Python 3.14 for syntax checks and non-graphics tests.
- Clarify preferences, automatic session recovery, PGN/FEN support and the absence
  of a built-in saved-game library in the README.

## 8.3.0 - 2026-09-16

- Add an auditable dependency BOM, copied third-party licence evidence, and explicit
  unresolved licence/source verification notices.
- Add Help → Open Source Licences and support notice/asset paths in folder builds.
- Add a draft dynamic Qt folder deployment, module audit and commercial distribution
  preparation guide. Python-chess remains a separate proprietary-release blocker.

## 8.2.0 - 2026-09-16

- Add seven interface themes: Forest, Midnight Ocean, Amethyst, Ember, Nordic Frost,
  Warm Paper and High Contrast.
- Add ten board colour themes: Ivory & Onyx, Walnut & Maple, Rosewood, Sage,
  Ocean, Amethyst, Terracotta, Slate & Silver, Honey & Espresso and Blush.
- Centralise board colour presets so menus and rendering use the same definitions.

## 8.1.0 - 2026-09-16

- Rename Board theme to Board Color Theme and add a separate remembered Board Type menu.
- Add Polished Marble, Rounded Oak, Tournament Wood, Canvas Roll-up and Marble & Brass,
  using original board geometry and bundled CC0 ambientCG material maps.
- Isolate python-chess behind rules, notation, UCI and opening-book boundaries,
  with application-owned rendering values, contract tests and a staged migration plan.
- Add PGN/FEN open, save and clipboard actions, including multi-game PGN selection.
- Add non-destructive move-list navigation while clocks are paused or inactive.
- Add Right Mouse as an OTB clock binding, keeping Ctrl+left-drag for rotation.
- Organise application code into the `otb_chess` package with `core`, `graphics`,
  `ui` and `services` directories; support `python -m otb_chess`.
- Refactor the main application into focused game, clock, rendering, input,
  appearance, engine, settings and audio modules.
- Isolate the legacy Tk UI and reduce `main.py` to the application launcher.
- Update Qt imports and regression tests to use the modules that own each API.

## 8.0.0 - 2026-09-16

- Add remembered Light, Dark, Blue, Cyberpunk and Pink/Lollipop interface themes.
- Keep both new-game clocks stopped until the first legal move is played.
- Restore live colour previews, with Cancel restoring the previous appearance.
- Apply saved clock settings immediately when no game is running.
- Allow either paused clock to be clicked and adjusted independently.
- Use whole minutes and seconds with separate, larger minus/plus buttons in the paused clock editor.
- Replace the two-window launch with a single PySide6 window and an embedded OpenGL board.
- Prioritise the board, large clickable clocks, move table and collapsible engine output.
- Move game, view, engine and appearance settings into menus and compact dialogs.
- Add a resizable/hideable sidebar, Focus mode, fullscreen and remembered layout preferences.
- Add background UCI position analysis with White-relative evaluation, depth and best line.
- Show the last engine move search separately from current-position analysis.
- Keep 2D/3D input, colours, piece sets, clock bindings, themes and backgrounds.
- Fit the 3D board to narrower viewports and reject engine moves from stale positions.
- Add native Qt interaction tests and a deterministic UCI subprocess integration test.
- Add PySide6 6.11.2; run the requirements installation when upgrading.

## 7.3.1 - 2026-09-16

- Enable wheel zoom in 2D as well as 3D: up zooms in, down zooms out.
- Enable left-drag panning on empty areas in 2D, with accurate picking after zooming and panning.
- Remember separate 2D zoom/pan preferences; Reset View restores the fitted board.
- Preserve the board's screen position when flipping a panned 2D view.

## 7.3.0 - 2026-09-16

### Added

- Switch instantly between a 3D board and a flat 2D board with chess symbols.
- Preserve square, frame, background and piece colours across both views.
- Remember the chosen view and retain the 3D camera when switching back.
- Live piece-set selector: Tournament Staunton, Wooden Staunton and Classic Club.
- Bundle all six MIT-licensed Staunton models, with attribution and a reproducible conversion tool.
- Discover complete custom OBJ sets from local asset folders.
- Cache piece geometry and 2D textures; add fill lighting for 3D pieces.
- Scroll the controls panel to keep settings accessible on smaller screens.
- Show the release version in both application window titles.
- Add seven tests covering assets, set switching, persistence, 2D moves and board picking.

### Fixed

- Align file labels, piece positions, square highlights and mouse selection.
- Display kings on E1/E8 and queens on D1/D8 in the starting position.
- Correct square colours: A1 is dark and queens start on their own colour.
- Account for framebuffer scaling when mapping the pointer to the board.

### Changed

- Tournament Staunton is the default set.
- Remove the Original set and its obsolete renderer; migrate saved selections to Tournament Staunton.
- Fall back to Classic Club if a saved set cannot be loaded.
- Replace the README's accumulated release notes with setup, controls and asset documentation.

## Earlier versions

The notes below retain the project's existing version history; dates were not recorded.

## 6.0

- rank numbers moved to visual left edge
- left-drag on empty board pans the whole board in-plane
- left-drag on a piece still moves that piece
- board pan offsets persist between sessions

## 6.1

- corrected board panning: only the board moves; the camera stays fixed
- left-drag on empty space now visibly pans the board
- pan follows the mouse direction

## 7.0

- full hyperbullet/bullet/blitz/rapid/classical time-control presets
- Custom time control in seconds + increment
- Online clock mode (automatic switch)
- OTB clock mode: move first, then hit the clock
- selectable OTB clock input: Spacebar, Middle Mouse, Mouse Button 4, Mouse Button 5
- human clock keeps running until the configured clock button is pressed
- engine automatically completes its clock action after moving
- opponent is blocked until the human hits the clock
- OTB clock mode/binding/custom time control persist between sessions

## 7.1

- added Reset Clock button
- custom time fields are hidden unless Custom is selected
- simple left clicks no longer nudge/pan the board
- board panning begins only after a real left-drag threshold is crossed

## 7.2

- Ctrl + left-drag rotates the board exactly like right-drag
- added Reset View button
- Reset View restores default rotation, pitch, pan and zoom without resetting the chess position
