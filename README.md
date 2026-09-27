# OTBMaster3D

A customizable 3D desktop chess application focused on natural over-the-board play,
engine analysis and organized position study.

**1.4.0-beta.1 ? Windows ? Beta / pre-release**

![Ruy Lopez on Rounded Oak with the Forest interface and opening name below navigation](docs/images/3d-middlegame.png)

This repository and its screenshots, source and release downloads are **private**.
Access is limited to authorized collaborators; no public distribution is implied.

## Play, analyse and organize

- Interactive 3D board and flat 2D view, with click/drag moves, rotation, zoom and pan.
- Automatic or over-the-board clocks, configurable time controls, takeback, resign,
  draw and switch sides with clocks paused.
- Stockfish analysis, compatible UCI engines and Maia-based difficulty presets.
- Hierarchical bookmarks for positions: nested folders, drag/drop ordering, a
  floating organizer and matching Bookmarks menu.
- PGN/FEN import and export, move review, static evaluation and session recovery.
- Offline opening recognition below the move navigation controls, with the opening
  name and ECO code following the displayed move history.
- Captured white pieces on the left and black pieces on the right, plus a compact
  engine icon beside Switch Sides that is crossed out when the engine is off.
- Board materials, 3D/2D piece sets, interface themes and eight sound profiles.
  Preferences and bookmark panel geometry are remembered.

| Stockfish analysis: Midnight Ocean | Bookmarks: Marble & Brass, Amethyst |
| --- | --- |
| ![Stockfish evaluation and principal variation](docs/images/engine-analysis.png) | ![Nested bookmark folders](docs/images/bookmark-organization.png) |

<details>
<summary>More board styles and themes</summary>

![Polished Marble with Ocean board colours and the Midnight Ocean interface](docs/images/3d-marble.png)

![2D Canvas Roll-up with Sage colours, Textbook pieces and Warm Paper; engine switched off](docs/images/2d-study.png)

</details>

Screenshots show the current source version. See [capture details](docs/images/README.md)
for the board and theme combinations; the published beta installer predates these sidebar changes.

## Install on Windows

Authorized collaborators can download **OTBMaster3D-1.4.0-beta.1-Setup.exe** from
[the private beta release](https://github.com/norKI79/OTBMaster3D/releases/tag/v1.4.0-beta.1).
Run the installer and launch OTBMaster3D from the Start menu. Python is not required.
The installer bundles Stockfish, Maia resources and three opening books.

The installer is **unsigned**. Windows may display a security or reputation warning.
Compare the download's SHA-256 with the [release notes](docs/releases/1.4.0-beta.1.md).
A working OpenGL 2.1 graphics driver is required.

## Beta validation and limitations

**166 automated tests passed** across the stabilization run and focused rerun.
The packaged smoke test passed, including application launch, OpenGL rendering,
Stockfish analysis and all three opening books. See the
[stabilization report](docs/stabilization-1.4.0-beta.1.md).

Clean-machine installation/upgrade/uninstall and multi-monitor/DPI checks remain
manual. Engine ratings are approximate. Public redistribution requires resolution
of the documented [third-party licence review gaps](docs/private-release-review.md).

## Useful controls

| Action | Control |
| --- | --- |
| Move | Click source and destination, or drag a piece |
| Rotate 3D / zoom | Right-drag or Ctrl+left-drag / mouse wheel |
| Start or pause clocks | Ctrl+P |
| Press OTB clock | Space |
| Take back / switch sides | U / Game > Switch sides or the switch-arrows button |
| Enable or disable engine play | Microchip icon beside Switch Sides; crossed out means off |
| Flip board / reset view | Ctrl+F / Ctrl+R |
| Manage bookmarks | Ctrl+Shift+B |
| Sidebar / focus mode | Ctrl+B / Ctrl+Shift+F |
| Fullscreen | F11 |

## Run and build from source

Use **Python 3.13 (64-bit)** with Tkinter on Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools/install_stockfish.py
.\.venv\Scripts\python.exe tools/install_maia.py
.\.venv\Scripts\python.exe main.py
```

Engine setup is optional when using your own UCI engine or playing without one.
See the [user guide](docs/user-guide.md), [installer build instructions](docs/windows-installer.md),
[bookmark guide](docs/bookmark-ui.md) and [contribution/testing instructions](CONTRIBUTING.md).

## Licensing and acknowledgements

Application source is licensed under **GPL-3.0-or-later**; see [LICENSE](LICENSE).
Third-party engines, libraries and artwork retain their own licences. Repository
privacy does not change those licences or establish redistribution clearance.
See [third-party notices](THIRD_PARTY_NOTICES.md), [licence evidence](licenses/README.md)
and the [private release review](docs/private-release-review.md).

[Release notes](docs/releases/1.4.0-beta.1.md) ? [Changelog](CHANGELOG.md)
