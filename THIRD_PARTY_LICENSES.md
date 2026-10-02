# Third-party licences and acknowledgements

## Component acknowledgements

The current component assessment is docs/licensing/LICENSING-CLOSURE.md in the
source archive. Qt/PySide/Shiboken 6.11.2 are used under LGPLv3; their exact
sources, notices and practical replacement instructions are retained. Mesa
11.2.2/LLVM 3.6.2 remain included under their permissive licences. GLFW 3.4 is
rebuilt from retained source. The frozen Windows runtime uses CPython 3.13.12;
`build-info.json`, when present, identifies the installed build. Supported engines
are Stockfish, Fairy-Stockfish and optional Rodent IV personality opponents.
The frozen build includes Stockfish and Fairy-Stockfish; Rodent IV is installed
separately in the source workspace. Original per-component grants remain in effect.

This software is based in part on the work of the Independent JPEG Group.
It uses the FreeType Project (https://freetype.org/), copyright its authors and
contributors; original years and notices are preserved in the FreeType texts.

Microsoft Visual C++ x64 Redistributable is an external prerequisite obtained
directly from Microsoft under its own terms. Current packaging excludes its
installer and standalone DLLs. Those terms do not apply to the
application's GPL-covered source. See licenses/Microsoft/DISTRIBUTION.md.

Third-party material retains its own copyright and licence. The application's
GPL-3.0-only designation does not relicense these components. Full existing credits,
modification descriptions and upstream links are preserved in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). That older inventory includes a
Python 3.14 development environment; `build-info.json` identifies an actual build.

| Component / copyright holder or source | Terms and offline text |
| --- | --- |
| python-chess 1.11.2, Niklas Fiekas and contributors | GPL-3.0-or-later; [full GPL](licenses/chess/LICENSE.txt). Preserve source-file notices; build staging copies the installed Python sources to source/python-chess. |
| cozy-chess-py 0.1.1, Copyright (c) 2026 akina; cozy-chess, Copyright (c) 2021 analog-hors | MIT; [complete notice](licenses/cozy-chess-py/LICENSE). Retained native dependency sources and notices are listed in the component assessment. |
| PySide6, Shiboken and Qt, The Qt Company and contributors | LGPLv3 for the selected Qt components; [LGPLv3](licenses/Qt/LGPL-3.0.txt) and [GPLv3](LICENSE). Version-specific sources and notices are retained. |
| pyGLFW, Florian Rhiem and contributors | MIT; [notice](licenses/glfw/LICENSE.txt). Native GLFW has separate zlib/libpng terms and is rebuilt from retained source. |
| Pillow, Secret Labs AB, Fredrik Lundh and contributors | HPND/MIT-CMU and bundled component terms; [complete supplied notice](licenses/Pillow/LICENSE). Check actual codec payload. |
| PyOpenGL, upstream contributors | BSD-style upstream terms; [complete 3.1.10 notice](licenses/PyOpenGL/LICENSE.txt). |
| CPython, Python Software Foundation and contributors | PSF and included historical/component terms; staging copies runtime LICENSE.txt to licenses/build/CPython-LICENSE.txt. |
| Stockfish team and contributors | GPLv3; downloaded payload retains stockfish/Copying.txt, AUTHORS, source and build documents. Verify NNUE inputs. |
| Staunton, Copyright (c) 2014 clarkerubber | MIT; [complete notice](assets/pieces/tournament/LICENSE). Converted to compressed application meshes. |
| Sci-fi Vehicles, Drummyfish | CC0-1.0; [full text](assets/pieces/scifi/LICENSE). Blender geometry converted and scaled to OBJ; original Blender source retained. |
| Fantasy, Celtic, Spatial, Skulls, Eyes, Maurizio Monge | MIT; full notices in each assets/pieces_2d set, e.g. [Fantasy](assets/pieces_2d/fantasy/LICENSE). Configured colours and rasterised SVGs; historical editor metadata cleaned. |
| Textbook, Colin M. L. Burnett | BSD-3-Clause; [complete notice](assets/pieces_2d/textbook/LICENSE). Extracted artwork and rasterised SVGs; source artwork and notices retained. |
| Chessnut, Copyright 2015 Alexis Luengas | Apache-2.0; [licence](assets/pieces_2d/chessnut/LICENSE) and [copyright](assets/pieces_2d/chessnut/COPYRIGHT.txt). Rasterised, designs unchanged. |
| Firi, James Faure (jfaure) | CC-BY-4.0; [full text](assets/pieces_2d/firi/LICENSE). Standard SVGs rasterised; attribution and modification notice retained. |
| ambientCG, Marble012 / Wood049 / Fabric030 | CC0-1.0; [source URLs and hashes](assets/boards/sources.json), [CC0 text](assets/pieces/scifi/LICENSE). |
| Lichess opening data contributors | CC0; [notice](books/sources/COPYING.txt); original TSV data and conversion script included. |
| PyInstaller and Inno Setup authors | Build tools; PyInstaller bootloader is distributed with its GPL exception. Full installed PyInstaller notices are copied to licenses/build/pyinstaller; [Inno Setup licence](licenses/InnoSetup/LICENSE.txt) retained; preserve its existing notices. |

No fonts are bundled in the tracked asset tree. UI fonts come from Windows.
Original icon, procedural geometry and synthesised sounds are documented in the
project; the maintainer has confirmed rights to these original materials.

For source access and build-specific release status, see [SOURCE_ACCESS.md](SOURCE_ACCESS.md)
and the component assessment in `docs/licensing/LICENSING-CLOSURE.md`.
Offline documents, including per-asset and per-engine notices, are readable in
Help > Open Source Licences. Preserve these files in every redistribution.

## Fairy-Stockfish 14

Fairy-Stockfish is distributed under GPL-3.0-or-later. Original authors and licence
texts are retained in `licenses/Fairy-Stockfish/`; the installed engine directory
contains `fairy-stockfish-14.zip` with corresponding upstream source and build
scripts. The selected standard-chess configuration disables NNUE and uses no
external model files. See [component evidence](docs/licensing/FAIRY_STOCKFISH.md).

## Rodent IV (optional)

Rodent IV 0.33 is GPL-3.0-or-later. Upstream credits include Pawel Koziol,
Bernhard C. Maerz and Pablo Vazquez (Sungorus). The installer helper retains
upstream licence text, source, build instructions and opening-book attributions
beside the engine. See [integration details](docs/licensing/RODENT_IV.md).
