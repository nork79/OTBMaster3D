# Third-party notices and bill of materials

## Remediation update — 2026-09-28

Current evidence: [docs/licensing/REMEDIATION.md](docs/licensing/REMEDIATION.md).
Full PyOpenGL 3.1.10 text is now retained in licenses/PyOpenGL/LICENSE.txt;
Qt/PySide and native source notices are inventoried in notice-inventory.json.
Packaging includes only Stockfish and Fairy-Stockfish engine resources. The maintainer confirmed original code/icon/sound/screenshot rights.
Earlier unresolved statements below are historical where superseded by this update.
Existing third-party attribution and licence texts remain applicable.

OTBMaster3D application source is GPL-3.0-only; see LICENSE.
Third-party files retain their original licences. The private Windows beta bundles
Python/Qt, engines and assets. The historical inventory below is not a complete
binary licence clearance; current findings and unresolved items are recorded in
[the open-source audit](docs/OPEN_SOURCE_AUDIT.md).

Machine-readable evidence: [third_party_bom.json](third_party_bom.json). It records versions,
installed metadata, import locations, licence-file hashes and redistribution intent.
Exact copied texts and explicitly labelled gaps: [licenses/README.md](licenses/README.md).

| Component | Version | Apparent licence | Category | Redistribution intent |
| --- | --- | --- | --- | --- |
| PySide6 | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | runtime | intended |
| PySide6_Essentials | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | runtime | intended |
| PySide6_Addons | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | runtime | Selected runtime files only; not whole Addons wheel |
| shiboken6 | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | runtime | intended |
| glfw | 2.10.2 | MIT | runtime | intended |
| PyOpenGL | 3.1.10 | requires verification before release | runtime | intended |
| Pillow | 12.3.0 | MIT-CMU | runtime | intended |
| chess | 1.11.2 | GPL-3.0+ | runtime | yes; GPL-3.0-or-later dependency |
| Qt runtime and plugins | 6.11.2 | LGPLv3 available for used modules; per-file third-party notices required | runtime | selected DLLs only |
| GLFW native library | 3.4.0 | zlib/libpng licence (upstream); bundled binary provenance requires verification before release | runtime | intended |
| CPython | 3.14.7 | PSF and bundled component licences; requires verification before release | runtime | intended |
| Tcl/Tk | requires verification before release | Tcl/Tk licence; requires verification before release | runtime | currently reachable through legacy UI imports |
| Windows VC runtimes | requires verification before release | Microsoft redistribution terms; requires verification before release | runtime | as required by native binaries; includes installed glfw msvcr120.dll |
| Pillow native codecs | requires verification before release | Multiple; requires verification before release | runtime | only exact wheel/deployed closure |
| OpenGL/GLU system drivers | OS/vendor supplied | OS/vendor terms; requires verification before release | runtime | not redistributed |
| PyOpenGL optional freeglut/GLE binaries | requires verification before release | See installed COPYING files; not needed by this app | runtime | exclude |
| Staunton models | 2014 source; converted meshes | MIT | asset | yes |
| ambientCG board maps | Marble012, Wood049, Fabric030; see assets/boards/sources.json | CC0-1.0 | asset | yes |
| Generated sounds / procedural geometry | application source | Application-owned; audit provenance of any replacement files | asset | yes; regenerate sounds in clean build |
| Stockfish 19 | official Windows x64 universal release | GPLv3; source, authors and licence in engines/stockfish-19/stockfish | runtime executable | downloaded separately by tools/install_stockfish.py |
| Lichess opening data | lichess-org/chess-openings | CC0; books/sources/COPYING.txt | three generated Polyglot repertoires | bundled |
| Additional user UCI engines and books | user supplied | varies | runtime | user selected |
| PyInstaller | 6.22.3 (local build tool) | GPL with bootloader exception; requires verification before release | build | bootloader only if draft adopted |
| black | 26.5.1 | MIT | development environment | no; not an application dependency |
| click | 8.5.0 | BSD-3-Clause | development environment | no; not an application dependency |
| mypy_extensions | 1.1.0 | MIT | development environment | no; not an application dependency |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | development environment | no; not an application dependency |
| pathspec | 1.1.1 | requires verification before release | development environment | no; not an application dependency |
| pip | 26.2.1 | MIT | development environment | no; not an application dependency |
| platformdirs | 4.11.8 | MIT | development environment | no; not an application dependency |
| pytokens | 0.4.1 | MIT License  Copyright (c) 2024 Tushar Sadhwani  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:  The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.  | development environment | no; not an application dependency |

## Evidence and limitations

Runtime Python imports are PySide6, OpenGL (PyOpenGL), PIL (Pillow), glfw and chess.
Shiboken6 and the PySide6 Essentials/Addons distributions are transitive installed dependencies.
The BOM includes installed development tools separately; they are not intended to ship.
QtTest is test-only; native QtOpenGL is a transitive runtime component.
Optional numpy / PyOpenGL_accelerate are not installed or required by this application.
Standard-library tkinter brings Tcl/Tk into the reachable legacy UI dependency graph.
Pillow/Qt embedded codecs and native support DLLs need a build-specific closure audit.
A private Windows beta has been built and smoke-tested; this is not licensing certification. Do not confuse wheel metadata
with a complete licence inventory for every binary inside it.

## Authoritative sources

- PySide6: https://doc.qt.io/qtforpython-6/licenses.html
- PySide6_Essentials: https://doc.qt.io/qtforpython-6/licenses.html
- PySide6_Addons: https://doc.qt.io/qt-6/licensing.html
- shiboken6: https://doc.qt.io/qtforpython-6/licenses.html
- glfw: https://github.com/FlorianRhiem/pyGLFW
- PyOpenGL: https://github.com/mcfletch/pyopengl
- Pillow: https://pillow.readthedocs.io/en/stable/about.html
- chess: https://python-chess.readthedocs.io/en/stable/
- Qt runtime and plugins: https://doc.qt.io/qt-6/licensing.html
- GLFW native library: https://www.glfw.org/license.html
- CPython: https://docs.python.org/3/license.html
- Tcl/Tk: https://www.tcl-lang.org/software/tcltk/license.html
- Windows VC runtimes: https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files
- Pillow native codecs: https://pillow.readthedocs.io/en/stable/installation/building-from-source.html
- OpenGL/GLU system drivers: https://learn.microsoft.com/en-us/windows/win32/opengl/opengl
- PyOpenGL optional freeglut/GLE binaries: https://github.com/mcfletch/pyopengl
- Staunton models: https://github.com/clarkerubber/Staunton-Pieces
- ambientCG board maps: https://docs.ambientcg.com/license/
- Generated sounds / procedural geometry: otb_chess/services/audio.py
- User UCI engines and books: docs/chess-backend-migration.md
- PyInstaller: https://pyinstaller.org/en/stable/license.html

## Additional chess artwork

- **Sci-fi Vehicles** by Drummyfish: CC0 1.0 Universal. Source:
  https://opengameart.org/content/sci-fi-chess. Extracted and converted from Blender
  to triangulated OBJ; coordinate conversion, centring/scaling and app materials.
  Full licence: [assets/pieces/scifi/LICENSE](assets/pieces/scifi/LICENSE).
- **Fantasy, Celtic, Spatial, Skulls and Eyes** by Maurizio Monge:
  copyright (c) Maurizio Monge, MIT licence. Source:
  https://github.com/maurimo/chess-art. Fantasy/Celtic/Spatial colours configured;
  SVGs rasterised to PNG. Each folder in assets/pieces_2d includes the full MIT
  licence, for example [Fantasy licence](assets/pieces_2d/fantasy/LICENSE).

See [Qt module audit](docs/qt-module-audit.md) and
[Windows distribution preparation](docs/windows-commercial-distribution.md) for module
restrictions, replacement instructions, matching-source obligations and release gates.

- **Textbook (Cburnett)** by Colin M. L. Burnett, BSD-3-Clause. Source: https://commons.wikimedia.org/wiki/File:Chess_nlt45.svg. Cburnett artwork extracted from the locally installed python-chess chess/svg.py artwork dictionary; wrapped as SVG and rasterised. No python-chess program code copied. Licence: [assets/pieces_2d/textbook/LICENSE](assets/pieces_2d/textbook/LICENSE).

- **Chessnut** by Alexis Luengas, Apache-2.0. Source: https://github.com/LexLuengas/chessnut-pieces. Original SVGs rasterised to PNG; no design changes. Licence: [assets/pieces_2d/chessnut/LICENSE](assets/pieces_2d/chessnut/LICENSE).

- **Firi** by James Faure (jfaure), CC-BY-4.0. Source: https://github.com/jfaure/Firi-pieceset. Standard chess SVGs from out/ rasterised to PNG; no design changes. Licence: [assets/pieces_2d/firi/LICENSE](assets/pieces_2d/firi/LICENSE).


## cozy-chess-py

Version 0.1.1 is a runtime dependency. Its installed distribution declares MIT;
the exact supplied licence is retained in [licenses/cozy-chess-py/LICENSE](licenses/cozy-chess-py/LICENSE).
Bundled runtime package versions are recorded in build-info.json.
# Native runtime update — 2026-09-29

The Windows build uses GLFW 3.4 rebuilt from the retained upstream source with
MSVC2022. The Python glfw wrapper remains 2.10.2. Microsoft CRT files are governed
by Microsoft's terms, separately from this application's GPL licence.

`PySide6/opengl32sw.dll` is Qt's software-rendering Mesa 11.2.2 build incorporating
LLVM 3.6.2. Retained upstream notices are under `licenses/software-opengl/` (or
their indexed installed paths). Native source/build and Microsoft distribution
review remains open; see `docs/licensing/NATIVE_RUNTIME_REMEDIATION.md` in the
source archive. This preparation build is not cleared for publication.

## Fairy-Stockfish 14

Fairy-Stockfish is distributed under GPL-3.0-or-later. Original authors and licence
texts are retained in `licenses/Fairy-Stockfish/`; the installed engine directory
contains `fairy-stockfish-14.zip` with corresponding upstream source and build
scripts. The selected standard-chess configuration disables NNUE and uses no
external model files. See [component evidence](docs/licensing/FAIRY_STOCKFISH.md).
