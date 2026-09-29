# Public repository privacy and security audit

2026-09-28; baseline f6c9852 with existing local changes. **Publication requires
maintainer review.** No files were deleted, history rewritten or remote settings changed.

## Coverage and method

Enumerated 474 tracked files and 27 commits reachable from all local Git refs.
Scanned all 728 unique reachable historical file blobs and current tracked text
for credential formats (AWS/GitHub/OpenAI), private-key headers, literal secret/
password assignments, email addresses, user-home paths and monetisation references.
Reviewed Git authors, ignored local state, build/source collection and CI permissions.
Raw local evidence is in ignored `.tmp/release-audit/scan.json` and imports.json;
do not publish raw diagnostic logs containing local paths.

Pattern scans are not proof that no secrets exist. Binary/image content, encoded
credentials, unreachable objects, reflogs, remote-only branches, releases, issues,
Actions logs/artifacts and third-party forks were not exhaustively audited.

## Findings

| Area | Finding | Action before public release |
| --- | --- | --- |
| Credentials/signing keys | No tested credential/private-key pattern matched current tracked text or reachable historical text | Run an independent secret scan before changing visibility; revoke/rotate any real credential discovered later, even if deleted at HEAD |
| Commit identity | All 27 commits use one maintainer identity with a personal Gmail address | Maintainer decides whether publishing that address is acceptable. Future noreply configuration does not remove history. History rewriting or a new public export needs separate approval |
| Historical SVG metadata | 70 user-path matches across historical versions of 48 Eyes/Fantasy/Skulls/Spatial SVG paths | Latest tracked files have no tested home-path matches. Historical paths remain; review and explicitly accept disclosure or approve remediation |
| Current email matches | Two matches in Pillow's third-party licence | Preserve attribution; these are not project credentials |
| Local state | config/session/bookmarks, saved games, venvs, engines, build outputs and temporary logs exist locally but are ignored | Do not publish a ZIP of the entire working directory. Use reviewed source collection and inspect its file manifest |
| Tracked binaries | Piece/board media, screenshots and three Lichess Polyglot books are intentional | Verify rights and screenshot content. No tracked EXE/DLL/signing material found in initial inventory |
| Internal documents | Historical migration/commercial research, private release review and earlier release notes are tracked | Preserved as requested. Review content before publication; current commercial research has a superseded banner |
| BOM | Development inventory has stale Python 3.14 values; exact release uses build-info.json | Regenerate final binary inventory; no legal clearance inferred from metadata |
| CI | Windows tests only; contents: read; no publishing job or funding configuration | Maintainer may pin action commit SHAs; check repository settings and remote logs independently |
| Build logs/executable debugging paths | Local verification logs contain user paths; frozen binaries may retain build paths | Keep logs private; inspect final binary metadata and public attachments separately |

`.gitignore` now also excludes common local credential files, signing files, logs
and editor configuration. Ignore rules do not untrack files or erase history.
No exposed credential was identified for rotation by this scan.

## Monetisation review

No active Patreon, donation, Sponsors, activation service, licence-key generator,
subscription plan or paid feature gate was found. No `.github/FUNDING.yml` exists.
“Premium Wood” is an available sound style, not a paid edition; it is preserved.
Upstream licence text, a saved upstream asset page and historical research retain
their original wording. Active README, About, notices and audit generation now
describe free GPLv3 source and the sole official commercial channel, itch.io.
Historical GPL-3.0-or-later release records are retained because they describe
earlier grants, not this release's current licence designation.
