# OTBMaster3D

An open-source Windows chess desktop application built with Python, PySide6 and
OpenGL. OTBMaster3D combines a rendered 3D board, chess-engine integration and
persistent study tools in a complete, packaged application.

[Download 1.6.5](https://github.com/nork79/OTBMaster3D/releases/tag/v1.6.5) ·
[Engineering overview](docs/engineering.md) · [User guide](docs/user-guide.md) ·
[Build from source](#run-and-build-from-source) · [Changelog](CHANGELOG.md)

![Ruy Lopez on Rounded Oak with the Forest interface and opening name below navigation](docs/images/3d-middlegame.png)

## Engineering highlights

This is an independent portfolio project by [nork79](https://github.com/nork79),
with working software, source code, tests and release artifacts available for review.

- **Desktop graphics:** a Qt interface with an OpenGL chessboard, 2D/3D views,
  piece picking, camera controls, animation and configurable materials.
- **Engine orchestration:** UCI integration with Stockfish, Fairy-Stockfish and
  Rodent IV; analysis, strength controls and personality opponents.
- **State and persistence:** PGN/FEN workflows, atomic session recovery and
  hierarchical bookmarks that restore positions while preserving play settings.
- **Architecture and verification:** application services, a chess-backend boundary,
  an isolated candidate rules adapter and separate headless/live-engine CI jobs.
- **Windows delivery:** PyInstaller/Inno Setup packaging, bundled engine resources,
  offline licence notices and hash-paired application/dependency source archives.

Start with the [engineering overview](docs/engineering.md) for a guided code tour,
design tradeoffs and verification scope. Production rules use python-chess;
the independent cozy-chess adapter remains an evaluated candidate.

## Download and source

**[Windows x64 installer](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/OTBMaster3D-1.6.5-Setup.exe)** ·
**[Exact application source](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/OTBMaster3D-1.6.5-application-source.zip)** ·
**[Dependency sources](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/OTBMaster3D-1.6.5-dependency-sources.zip)** ·
**[SHA-256 checksums](https://github.com/nork79/OTBMaster3D/releases/download/v1.6.5/SHA256SUMS.txt)**

Version **1.6.5** includes Rodent IV, bookmark reset and updated clock controls.
See [release details and validation](docs/releases/1.6.5-source.md). The packaged
smoke test passed; clean Windows installation, upgrade and uninstall testing
remain pending. The installer is unsigned.

Source is public under **GPL-3.0-only**. There are no licence keys, activation,
application accounts or paid feature unlocks. Matching release archives preserve
the installer source even as `main` develops.

## Play, analyse and organize

- Interactive 3D board and flat 2D view, with click/drag moves, rotation, zoom and pan.
- Automatic or over-the-board clocks, configurable time controls, takeback, resign,
  draw and switch sides with clocks paused.
- Stockfish analysis, Stockfish/Fairy-Stockfish practice levels and Rodent IV opponents.
- Hierarchical bookmarks for positions: nested folders, drag/drop ordering, a
  floating organizer and matching Bookmarks menu. Opening a bookmark preserves
  current engine and clock settings, restores board facing, and pauses the clocks.
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
for the board and theme combinations.

## Install on Windows

Download the installer above, run Setup, and launch OTBMaster3D from the Start
menu. Python is not required. The installer includes Stockfish 19, Fairy-Stockfish
14, Rodent IV personalities and three opening books.
Fairy-Stockfish presets cover 500–1500; Stockfish presets cover 1600–2500 and full
strength. Rodent offers Tal, Kasparov, Morphy, Karpov, Petrosian and Default
personalities with independent target strength. Ratings are approximate.
See [engine setup](engines/README.md) for details and source-workspace setup.

Requirements: Windows 10 or later, x64-compatible hardware and an OpenGL 2.1-capable
graphics driver. Source builds require Python 3.13 (64-bit), including Tkinter.

Current installer configuration requires Microsoft Visual C++ x64 Redistributable 14.44.35211.0
or newer, installed separately from
[Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
Setup checks this prerequisite and gives instructions if it is missing.

The pinned cozy-chess-py wheel requires Python 3.13. Disk and RAM minimums beyond
these requirements have not been measured. Engine ratings are approximate.

Installer signing is not configured. Windows SmartScreen may show an
unknown-publisher or reputation warning. Verify the download against the release SHA-256 checksums; no publisher
verification is claimed.

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
.\.venv\Scripts\python.exe tools/install_fairy_stockfish.py
.\.venv\Scripts\python.exe main.py
```

Engine setup is optional when using an existing supported engine or playing without one.
See the [user guide](docs/user-guide.md), [installer build instructions](docs/windows-installer.md),
[bookmark guide](docs/bookmark-ui.md) and [contribution/testing instructions](CONTRIBUTING.md).

## Automated tests

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q main.py otb_chess otb_chess_core tests tools
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The complete suite needs a Windows desktop with OpenGL and Tk. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the dedicated Python 3.13 test environment
and which tests require installed engines.
To compile an installer, follow [the Windows build procedure](docs/windows-installer.md).

## Licensing, source access and acknowledgements

Copyright (C) 2026 nork79 for original project material. Application source is
licensed under **GPL-3.0-only**; see [LICENSE](LICENSE) and [COPYRIGHT.md](COPYRIGHT.md).
Third-party engines, libraries and artwork retain their own terms. See
[third-party licences](THIRD_PARTY_LICENSES.md) and [source access](SOURCE_ACCESS.md).
Complete licence texts are available offline in Help > Open Source Licences.

Every public installer must link to its exact application and dependency source
archives at no additional charge. See [SOURCE_ACCESS.md](SOURCE_ACCESS.md) for the
installed source snapshot, build manifest and matching dependency sources.
A repository homepage alone is not the matching source distribution.

## Bugs, contributions and maintenance

Report reproducible bugs in [GitHub issues](https://github.com/nork79/OTBMaster3D/issues),
including version, Windows version, steps and a sanitised PGN/FEN when useful.
Use [SECURITY.md](SECURITY.md) for private security reports. Read
[CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

OTBMaster3D is intended as a substantially finished application. Future features,
updates and technical support are not guaranteed.
See [the maintenance policy](docs/MAINTENANCE.md). [Changelog](CHANGELOG.md).
