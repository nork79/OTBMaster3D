# Corresponding source and your rights

See [1.6.3 source preparation](docs/releases/1.6.3-source.md) for the retained
local build and proposed archive locations. The repository is private and public
archive links remain pending. The dated [component assessment](docs/licensing/LICENSING-CLOSURE.md)
records earlier review evidence, not clearance of current `main`.

OTBMaster3D is licensed under GPL-3.0-only. You may copy, modify and redistribute
it under GPLv3, including redistribution without charge. Each Windows installer
must be paired with its exact source snapshot; current `main` may contain later
changes. The application has no licence key, activation or purchase verification.

Project repository: https://github.com/nork79/OTBMaster3D

Installer distribution channel: not yet selected.

## Find the source for an installed version

Open Help > About for the version, and Help > Open Source Licences for this
document and `build-info.json`. The installed `source/OTBMaster3D-source.zip`
contains the application snapshot, assets, tests and build/installation scripts.
Extract it and follow README.md and docs/windows-installer.md. The manifest records
the base Git commit, working-tree status and archive SHA-256; a dirty build is
identified by the archived bytes, not by the base commit alone.

Public releases must also provide the exact application archive and a matching
dependency source bundle at no additional charge. The binary download
page must prominently link those exact archives and their hashes on the public
GitHub release for the same version, with equivalent downloading facilities.
Source access must not require purchasing the installer. Keep those sources
available for as long as the binary is offered and meet any continuing obligations.

## Dependency sources and historical preparation build

The commands and beta version below describe the retained 1.4.0-beta.2
preparation build. For the current installed version, consult `build-info.json`
and its matching source manifest. The 1.6.4 frozen build includes Rodent IV's
`rodent-iv-source.zip`, build helper, manifest and notices beside the engine in
`engines/rodent-iv`; see `docs/licensing/RODENT_IV.md`. Stockfish and
Fairy-Stockfish remain included.

The application archive alone is **not complete Corresponding Source for the whole
installer**. Stockfish source is under `engines/stockfish-19/stockfish/src` in the
installed payload; verify the matching NNUE inputs and build instructions too.
The separately prepared dependency bundle must include the matching python-chess,
Qt/PySide/Shiboken sources, necessary submodules, build scripts, patches,
and other covered dependencies. Engine packaging includes Stockfish, Fairy-Stockfish and Rodent IV.

Run `python tools/prepare_corresponding_source.py` with the inventoried archives
in `release-materials/1.4.0-beta.2/sources/` to produce the application archive,
`OTBMaster3D-1.4.0-beta.2-dependency-sources.zip` and `source-release-manifest.json`.
The manifest identifies the exact bytes. See docs/licensing/source-inventory.json
and docs/licensing/BUILD_AND_REPLACE.md for source URLs, hashes and build information.

**This preparation build is blocked for public distribution.** Exact dependency
public source download locations have not yet been established. Clean Windows
verification remains pending. See the retained build's manifest for its exact
installer hash. Historical compiler reproduction is optional assurance
unless a specific licence requirement is identified.
Do not present the repository homepage or upstream project links as a substitute
for the matching source bundle. Replace this preparation notice with the verified
version-specific source URLs before building an approved public release.

The proposed online distribution method is GPLv3 section 6(d); see LICENSE.
This document adds no restrictions to GPL rights and is not a written source offer
under section 6(b). Licence texts and acknowledgements are readable offline through
Help > Open Source Licences, or directly from LICENSE and licenses/.
