# Private 1.4.0-beta.1 release review

The destination is the existing `norKI79/OTBMaster3D` private GitHub repository.
No visibility, ownership, Pages, package or public-mirror change is authorized.

## Privacy and metadata

Non-runtime export filenames, editor document paths/names and export-DPI attributes
were removed from 60 bundled SVGs. XML elements and drawing attributes were checked;
all 96 runtime piece PNGs are byte-identical. Application code and behaviour were
not changed. Existing upstream copyright/licence and attribution were retained.
The installer is rebuilt and smoke-tested after this cleanup; the previous checksum
is superseded. The exact new checksum is recorded in the release notes and stabilization report.

Four genuine screenshots use only demonstration data in temporary preferences.
Settings, bookmarks, sessions, saved games, logs, caches, build intermediates and
local research remain ignored. Third-party author attribution is intentionally retained.

## Licence evidence and outstanding review

- Application: root GPL-3.0-or-later licence; README makes no all-assets-same-licence claim.
- Stockfish: bundled official source, authors and GPL text are present.
- Lc0/Maia: runtime and repository licence texts and installation manifest are present.
  Model-specific redistribution terms remain unresolved in the existing inventory.
- cozy-chess-py 0.1.1: exact installed MIT licence copied into `licenses/cozy-chess-py`.
- Python dependencies: available distribution licence files and CPython licence are
  copied by the existing build. Qt wheel metadata contains a commercial-reference
  text, not proof of a commercial entitlement or complete LGPL/GPL compliance.
- Artwork: model, board-map, piece-set and opening-book credits/licences are present
  in their asset/source directories. The app icon is documented as original artwork;
  sounds are documented as generated assets. No new fonts or third-party media added.
- Remaining gaps: Qt corresponding-source/component notices, PyOpenGL evidence,
  native codec/VC/Tcl-Tk closure and Maia model terms need a distribution review
  before any future public release. Existing verification placeholders are not
  substitutes for licence texts. No legal clearance is claimed by this private release.

## Checks

The prior 166 passing automated tests remain the application validation baseline.
No executable application code changed for release preparation, so the full suite
was not rerun. Asset XML/PNG integrity, screenshot inspection, Git whitespace and
privacy checks accompany the new build/resource checks and packaged smoke test.

## Rebuilt artifact verification

The 2026-09-20 rebuild and packaged smoke test passed. Cleaned SVGs, engines,
books, runtime libraries and assets were verified. SHA-256: `0ec3097808e047fb1e0b8c3756a6359982695eee1b6947016af27d1a67b55bd6`.
The exact installer will be attached only to the private repository pre-release.
