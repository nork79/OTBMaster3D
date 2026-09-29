# Third-party licences and acknowledgements

## Current closure — 2026-09-29

The current component assessment is docs/licensing/LICENSING-CLOSURE.md in the
source archive. It supersedes unresolved statements below where evidence has
since been collected. Qt/PySide/Shiboken 6.11.2 are used under LGPLv3; their exact
sources, notices and practical replacement instructions are retained. Mesa
11.2.2/LLVM 3.6.2 remain included under their permissive licences. GLFW 3.4 is
rebuilt from retained source. CPython in this build is 3.13.12. Only Stockfish and Fairy-Stockfish are supported. Original per-component grants below remain in effect.

This software is based in part on the work of the Independent JPEG Group.
It uses the FreeType Project (https://freetype.org/), copyright its authors and
contributors; original years and notices are preserved in the FreeType texts.

Microsoft Visual C++ x64 Redistributable is an external prerequisite obtained
directly from Microsoft under its own terms. Current packaging excludes its
installer and standalone DLLs. Those terms do not apply to the
application's GPL-covered source. See licenses/Microsoft/DISTRIBUTION.md.

## Remediation update — 2026-09-28

Current evidence: [docs/licensing/REMEDIATION.md](docs/licensing/REMEDIATION.md).
Full PyOpenGL 3.1.10 text is now retained in licenses/PyOpenGL/LICENSE.txt;
Qt/PySide and native source notices are inventoried in notice-inventory.json.
Packaging includes only Stockfish and Fairy-Stockfish engine resources. The maintainer confirmed original code/icon/sound/screenshot rights.
Earlier unresolved statements below are historical where superseded by this update.
Existing third-party attribution and licence texts remain applicable.

Third-party material retains its own copyright and licence. The application's
GPL-3.0-only designation does not relicense these components. Full existing credits,
modification descriptions and upstream links are preserved in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). That older inventory includes a
Python 3.14 development environment; `build-info.json` identifies an actual build.

| Component / copyright holder or source | Terms and offline text |
| --- | --- |
| python-chess 1.11.2, Niklas Fiekas and contributors | GPL-3.0-or-later; [full GPL](licenses/chess/LICENSE.txt). Preserve source-file notices; build staging copies the installed Python sources to source/python-chess. |
| cozy-chess-py 0.1.1, Copyright (c) 2026 akina; cozy-chess, Copyright (c) 2021 analog-hors | MIT; [complete notice](licenses/cozy-chess-py/LICENSE). Native Rust dependency closure needs review. |
| PySide6, Shiboken and Qt, The Qt Company and contributors | Selected components offer LGPLv3/GPLv3 routes; [LGPLv3](licenses/Qt/LGPL-3.0.txt) and [GPLv3](LICENSE). Existing commercial-reference files are evidence only, not an entitlement. Complete version-specific notices and source are still missing. |
| pyGLFW, Florian Rhiem and contributors | MIT; [notice](licenses/glfw/LICENSE.txt). Native GLFW has separate zlib/libpng terms; full binary provenance/notice remains pending. |
| Pillow, Secret Labs AB, Fredrik Lundh and contributors | HPND/MIT-CMU and bundled component terms; [complete supplied notice](licenses/Pillow/LICENSE). Check actual codec payload. |
| PyOpenGL, upstream contributors | BSD-style upstream terms; exact 3.1.10 complete notice requires verification. Existing placeholder remains explicitly unresolved. |
| CPython, Python Software Foundation and contributors | PSF and included historical/component terms; staging copies runtime LICENSE.txt to licenses/build/CPython-LICENSE.txt. |
| Stockfish team and contributors | GPLv3; downloaded payload retains stockfish/Copying.txt, AUTHORS, source and build documents. Verify NNUE inputs. |
| Staunton, Copyright (c) 2014 clarkerubber | MIT; [complete notice](assets/pieces/tournament/LICENSE). Converted to compressed application meshes. |
| Sci-fi Vehicles, Drummyfish | CC0-1.0; [full text](assets/pieces/scifi/LICENSE). Blender geometry converted and scaled to OBJ; original source file provenance needs retention review. |
| Fantasy, Celtic, Spatial, Skulls, Eyes, Maurizio Monge | MIT; full notices in each assets/pieces_2d set, e.g. [Fantasy](assets/pieces_2d/fantasy/LICENSE). Configured colours and rasterised SVGs; historical editor metadata cleaned. |
| Textbook, Colin M. L. Burnett | BSD-3-Clause; [complete notice](assets/pieces_2d/textbook/LICENSE). Extracted artwork and rasterised SVGs; verify the selected upstream grant against exact artwork. |
| Chessnut, Copyright 2015 Alexis Luengas | Apache-2.0; [licence](assets/pieces_2d/chessnut/LICENSE) and [copyright](assets/pieces_2d/chessnut/COPYRIGHT.txt). Rasterised, designs unchanged. |
| Firi, James Faure (jfaure) | CC-BY-4.0; [full text](assets/pieces_2d/firi/LICENSE). Standard SVGs rasterised; attribution and modification notice retained. |
| ambientCG, Marble012 / Wood049 / Fabric030 | CC0-1.0; [source URLs and hashes](assets/boards/sources.json), [CC0 text](assets/pieces/scifi/LICENSE). |
| Lichess opening data contributors | CC0; [notice](books/sources/COPYING.txt); original TSV data and conversion script included. |
| PyInstaller and Inno Setup authors | Build tools; PyInstaller bootloader is distributed with its GPL exception. Full installed PyInstaller notices are copied to licenses/build/pyinstaller; [Inno Setup licence](licenses/InnoSetup/LICENSE.txt) retained; preserve its existing notices. |

No fonts are bundled in the tracked asset tree. UI fonts come from Windows.
Original icon, procedural geometry and synthesised sounds are documented in the
project; maintainer confirmation remains required for their provenance.

**Not cleared for public distribution:** generic licence texts alone do not supply
all required component notices or Corresponding Source. Tcl/Tk, VC runtimes,
OpenBLAS, allocator libraries, Qt third-party code and native Rust dependencies
need the final payload audit in [OPEN_SOURCE_AUDIT.md](docs/OPEN_SOURCE_AUDIT.md).
Offline documents, including per-asset and per-engine notices, are readable in
Help > Open Source Licences. Preserve these files in every redistribution.

## Fairy-Stockfish 14

Fairy-Stockfish is distributed under GPL-3.0-or-later. Original authors and licence
texts are retained in `licenses/Fairy-Stockfish/`; the installed engine directory
contains `fairy-stockfish-14.zip` with corresponding upstream source and build
scripts. The selected standard-chess configuration disables NNUE and uses no
external model files. See [component evidence](docs/licensing/FAIRY_STOCKFISH.md).
