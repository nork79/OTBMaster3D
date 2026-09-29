# Licensing closure — OTBMaster3D 1.4.0-beta.2

## Current engine update

Engine support is now limited to Stockfish 19 and Fairy-Stockfish 14. The latter's
GPL notices, matching source archive and live-engine verification are recorded in
[Fairy-Stockfish evidence](FAIRY_STOCKFISH.md). Historical reports and test logs
for the obsolete engine configuration are archived unchanged in
`release-materials/retired-engine-records.zip`; they are not current test results.
No installer was rebuilt for this update.

Assessment date: 2026-09-29. This finite assessment supersedes the unresolved
provenance requirements in earlier reports. Those reports, hashes and archives
remain evidence; their conclusions are not silently reused as current blockers.
This is an engineering and licence-text review, not a professional legal opinion.

**Artifact boundary:** this matrix assesses retained component materials and the
current source candidate. Desktop-access requests for the final suite and build
were declined. The existing installer remains the earlier app-local-CRT build;
the external prerequisite policy and current difficulty/sound fixes have not yet
been incorporated into a rebuilt installer. See RELEASE-COMPLIANCE.md.

## Recorded release decisions

- The maintainer confirmed: **individual developing my own application**. This
  supplies the previously missing factual basis for VS Community section 1(a).
- The maintainer explicitly chose **retain software OpenGL fallback**.
- A clean Windows machine is **not yet available**. No clean-machine result is claimed.
- No commit, push, tag, upload, store edit or publication is authorized.

## How to read the matrix

PASS means the stated obligation has supporting local evidence. It does not mean
that the unpublished release has been cleared for distribution. FAIL identifies
a concrete unmet check. HUMAN REVIEW REQUIRED identifies a specific interpretation
or confirmation, not an invitation to restart the dependency investigation.
OPTIONAL ASSURANCE work is not a release licence requirement established here.
All local-source PASS entries remain subject to the separate publication row.

Authoritative references: [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html),
[LGPLv3](https://www.gnu.org/licenses/lgpl-3.0.html),
[VS Community terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/),
[VS2022 REDIST](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution),
and the original component texts retained under `licenses/` and in the exact
archives named in [source-inventory.json](source-inventory.json). The original
licence grants, rather than package classifiers, govern this matrix.

## Component obligations and closure

| Component / shipped version | Applicable licence and exact obligation | Existing evidence | Exact gap / smallest action | Status |
| --- | --- | --- | --- | --- |
| OTBMaster3D 1.4.0-beta.2 | GPL-3.0-only §§4–6: notices, preferred source, needed build/install scripts; §10 no additional restrictions | LICENSE; snapshot generator includes Python, assets, tests, build/install scripts; original asset rights previously confirmed | Local source preparation verified separately; publish matching free archives under §6(d) before sale | PASS (local materials) |
| python-chess 1.11.2 | GPL-3.0-or-later §§4–6,10 | Exact sdist hash; Python source staged beside app snapshot; full GPL notice | No new local gap; same publication prerequisite | PASS |
| Stockfish 19 + nn-1a298aa575a0 | GPLv3 for engine; CC0 network grant; source, notices and needed network/build inputs | sf_19 source/Makefile, official universal build materials and checksum-verified NNUE already retained | No concrete new gap; previous verification retained | PASS |
| Qt Core, Gui, Widgets, OpenGL, OpenGLWidgets; qwindows/qico 6.11.2 | LGPLv3 §4(a–c) notice and licence copies; §4(d)(1) compatible shared replacement; GPLv3 §6 for library object-code source | Exact official QtBase archive/checksum, embedded sources/CMake; GPL/LGPL texts and module notices; 15-file replacement smoke; About now explicitly names Qt/PySide/Shiboken LGPL use | Publish corresponding archives. Historical compiler patch level and bit reproduction are not established requirements | PASS (local materials/mechanism) |
| PySide6 Essentials / Shiboken 6.11.2 runtime | LGPLv3, same combined-work/source conditions | Official pyside-setup source, binding type systems, setup/CMake scripts, exact wheel mapping, support DLL/PYD replacement | Same public source prerequisite; preserve compatible x64 Python limited API | PASS (local materials/mechanism) |
| Mesa 11.2.2 / LLVM 3.6.2 software OpenGL | Mesa MIT-style licences and LLVM University of Illinois/NCSA; binary copyright, conditions, disclaimer and no endorsement; see original notices | Matching-version source archives; Qt official prebuilt archive checksum and identical PE sections; original Mesa/LLVM notices under licenses/software-opengl | No identified mandatory source/patch/configuration item absent under these permissive binary grants | PASS (identified open-source obligations) |
| Mesa historical compiler, patches and static CRT attribution | No exact-reproduction obligation identified in MIT/NCSA | Known Qt prebuilt origin; no proof identifying every statically incorporated compiler support byte | Review the specific Microsoft binary redistribution question below; obtaining the old compiler recipe is optional unless a concrete contrary grant is found | OPTIONAL ASSURANCE (reproduction) |
| GLFW 3.4 / Python glfw 2.10.2 | Native zlib/libpng, wrapper MIT: retain notices; mark modified source if any | Exact source; no native patches; recorded MSVC rebuild; both probes and 134 exports match; no MSVCR120 imports | None; preserve existing build evidence | PASS |
| cozy-chess-py 0.1.1 / cozy-chess 0.3.4 and types 0.2.2 | MIT plus crate-specific MIT/Apache alternatives: retain copyright, permission and selected licence notices | sdist, Cargo.lock, all checksum-verified crate sources and notices | No new concrete gap; build-only crates are not automatically shipped runtime components | PASS |
| Pillow 12.3.0 | MIT-CMU: copyright/permission in copies and supporting documentation; no unauthorized endorsement | Complete aggregate licence; sdist/upstream tag; Windows recipes, flags and patches | None for identified Pillow code | PASS |
| JPEG-turbo 3.1.4.1 (Pillow) | IJG + BSD-3-Clause + zlib portions: applicable notices, attribution, disclaimer, no endorsement | Aggregate Pillow licence and full source notices/recipe | Preserve the IJG acknowledgment below | PASS |
| OpenJPEG 2.5.4; TIFF 4.7.1 | BSD-2-Clause; libtiff permissive terms: copyright/conditions/disclaimer | Sources, aggregate licence, exact Windows recipe | None identified | PASS |
| zlib-ng 2.3.3; libpng 1.6.58 | zlib; libpng grants: no misrepresentation, mark altered source, retain licence notices | Sources, aggregate notices, retained build patches | No independent bit-for-bit build required | PASS |
| WebP/libsharpyuv 1.6.0 | BSD-3-Clause and upstream PATENTS grant: retain notices/disclaimers | WebP archive includes sharpyuv; Pillow aggregate licence, build recipe | Preserve original PATENTS text | PASS |
| LittleCMS 2.19 runtime / 2.19.1 source pin | MIT: copyright and permission | Runtime feature report, upstream pinned recipe, source and notices | Version API truncation alone is not a different-source finding | PASS |
| FreeType 2.14.3 | FTL route; redistribution §2 binary acknowledgment and source change notices | FTL and archive; Pillow/Qt notices; explicit FreeType acknowledgment below | Do not substitute GPL-2.0-only route for FTL | PASS |
| HarfBuzz 14.2.1; Brotli 1.2.0 (Pillow recipe) | MIT-family notices, attribution and no endorsement as stated | Upstream pinned source, aggregate licence and recipe | Recipe/notice identifies supporting static inputs; not inferred from DLL imports | PASS |
| libavif 1.4.2 | BSD-2-Clause and incorporated component grants | Source and Windows static build flags/patches retained | None identified | PASS |
| AOM 3.14.1; dav1d 1.5.3 | BSD-2-Clause plus AOM patent terms; dav1d BSD-2-Clause | Sources, COPYRIGHT/LICENSE/PATENTS retained; AVIF recipe | No patent clearance beyond the actual upstream grants is claimed | PASS (licence materials) |
| libyuv commit 644251f252a84bf8ce91ff0aca86a9b16b069ab8 | BSD-3-Clause and PATENTS: retain conditions/notice | Official Git exact revision, reproducible git archive, LICENSE/PATENTS/AUTHORS | Archive endpoint failure does not negate retained source | PASS |
| CPython 3.13.12 | PSF and historical component licences: retain texts, notices and required change summaries | Official complete source including embedded Expat, PCbuild and licence; installed CPython notice | No application patches to CPython | PASS |
| OpenSSL 3.0.18; libffi 3.4.4 | Apache-2.0 §4 licence/notices/change identification; libffi MIT | Official sources and native notices, imports identify DLLs | Preserve upstream NOTICE where supplied | PASS |
| Tcl/Tk 8.6.15 | Tcl/Tk permissive copyright/permission/disclaimer | Exact source trees, licences, tcl86t/tk86t inventory | None identified | PASS |
| bzip2 1.0.8; xz 5.2.5 (CPython), xz 5.8.3 (Pillow recipe); zlib 1.3.1; mpdecimal 4.0.0 | Respective bzip2, liblzma public-domain/0BSD portions, zlib, BSD-style mpdecimal terms; preserve notices and source modifications where required | Pinned complete sources and native-source notices | GPL build utilities in source archives do not establish GPL static runtime incorporation | PASS |
| PyOpenGL 3.1.10 | Upstream BSD-style notices, copyright/disclaimer | Full version-specific licence and sdist retained | No optional freeglut/GLE DLL redistributed | PASS |
| Qt embedded libraries | Individual original grants; see separate detailed table below | Complete QtBase source and third-party attribution/licence files retained | Exact compiler feature list is optional assurance where both code/notices are already supplied; no claim all QtBase candidates are shipped | PASS (materials) |
| Microsoft standalone x64 VC++ runtime | External prerequisite; no standalone runtime redistributed by current packaging | Individual build licence basis confirmed; reviewed import/export baseline retained; package and DLL exclusion checks added | Users obtain x64 runtime 14.44.35211.0 or newer directly from Microsoft. Verify the next actual build and clean-machine installation | ADDRESSED IN SOURCE; BUILD VALIDATION PENDING |
| Microsoft support code possibly static in upstream native libraries | Microsoft grant relevant to upstream distribution, not GPL relicensing | Legitimate Qt/Python/Pillow upstream distributions; no identified prohibited component | Ask reviewer whether these unmodified upstream binaries plus supplied notices need any additional Microsoft pass-through terms; no speculative demand for entire historical build ecosystem | HUMAN REVIEW REQUIRED (same Microsoft review) |
| PyInstaller 6.22.3 bootloader | GPL with bootloader exception; retain licence/exception; source provided | Exact sdist, staged build-tool licence texts | No bootloader patches | PASS |
| Inno Setup 6.4.3 uninstaller | Original Inno Setup licence, attribution and no misrepresentation | Installer tool/retained licence; uninstaller separately inventoried | No upstream source changes | PASS |
| Original code, icon, procedural meshes and sounds | Application GPL; author owns/authorizes original material | Prior maintainer confirmation; generators and asset sources retained | None; seven active sound profiles tested, profile 2 removed from menu | PASS |
| Staunton 2014 models; Monge 2D sets | MIT copyright/permission | Original STL/import archives; conversion tools; per-set notices | None | PASS |
| Sci-fi Blender original; ambientCG Marble012/Wood049/Fabric030; Lichess opening TSVs | CC0 | Original Blender, map source hashes, TSVs/converter and full CC0 notices | None | PASS |
| Textbook/Burnett; Chessnut; Firi | BSD-3-Clause; Apache-2.0; CC-BY-4.0 §3 attribution/licence/change indication | Retained grants, source artwork, copyright and conversion notices | Retain artist attribution and rasterization/modification statements | PASS |
| Free public release archives | GPLv3 §6(d): equivalent free source access beside object-code offer | Local version-matched archives and manifest prepared | Authorized publication then signed-out download/hash check of exact links; no upload authorized here | FAIL (publication prerequisite only) |
| itch.io proposed paid distribution | GPLv3 §§6,10 and platform publisher obligations | Explicit GPL rights/source notice; no DRM, activation or purchase checks | Review platform §4 publisher grant for third-party GPL/Microsoft material; preserve independent GPL grant and free source links in listing | HUMAN REVIEW REQUIRED |

### Qt embedded component detail

The authoritative inventory is
[qt-embedded-source-attributions.json](evidence/qt-embedded-source-attributions.json).
It supplies source versions, original grant IDs, copyright holders and source
paths. It deliberately includes candidates whose Windows incorporation is not
asserted. Windows-relevant entries include double-conversion 3.4.0 (BSD-3),
HarfBuzz 14.3.0 (MIT), FreeType 2.14.3 (FTL), JPEG-turbo 3.2.0 (IJG/BSD),
PNG 1.6.58 (libpng), PCRE2 10.47 (BSD with its supplied exception), zlib 1.3.2
(zlib), TinyCBOR 7.0 (MIT), MD4C 0.5.3 (MIT), Pixman 0.17.12 (MIT),
hash implementations (CC0/BSD), D3D12/Vulkan memory allocators (MIT), sRGB
profile (ICC permission text), and Wintab (its supplied permission text).
Copyright, attribution, conditions and disclaimers are preserved byte-for-byte.
Any Public Suffix List data under MPL-2.0 is also retained in preferred source
form in QtBase; it is not evidence that QtNetwork is shipped. Android, Wayland,
SQLite plugin and build-tool entries do not establish their presence in this
five-module Windows payload. No new source gap is identified by that uncertainty.

### Required acknowledgments

This software is based in part on the work of the Independent JPEG Group.
Portions of this software use the FreeType Project, copyright its authors and
contributors; see the full FreeType notices and https://freetype.org/.
Original copyright years and holders remain in the unmodified component texts.

## Microsoft deployment decision

Current packaging requires a separately installed Microsoft x64 runtime. Setup
does not bundle, download or launch Microsoft's redistributable. Both interactive
and silent setup stop before changing files when the runtime is absent or too old,
and provide Microsoft's download-page address. An equal/newer runtime is reused.
Ten old app-local copies are removed only after prerequisite validation; imports
and exports remain checked. A folder build also requires the runtime installed.

Direct redistribution of the standalone runtime is removed from the planned
payload. The separate embedded-code question remains open. No Microsoft terms
are added to GPL-covered source. See [Microsoft remediation](MICROSOFT_RUNTIME_REMEDIATION.md)
for five passing safeguard tests, the read-only payload audit, official references
and limitations. No installer was rebuilt; clean Windows testing remains pending.

## Mesa decision and limits

The app uses a QOpenGLWidget and requests OpenGL 2.1 compatibility. Qt can load
its software renderer when suitable hardware OpenGL is unavailable; removing
the DLL removes that fallback for affected driver/VM configurations. See
[Qt's Windows graphics documentation](https://doc.qt.io/qt-6/windows-graphics.html).
The maintainer chose retention. Retention alone does not prove that PyOpenGL's
native calls and every target driver work with Mesa; a forced-software probe
and clean-machine graphics checks must report actual results separately.

Mesa/LLVM's identified permissive binary grants require notices, not delivery
of the exact historical compiler configuration or patches. Matching sources and
the upstream Qt prebuilt are retained as assurance. No missing mandatory Mesa
source file is identified. Earlier reports' blanket provenance blocker is
therefore narrowed to the Microsoft interpretation above and actual runtime
validation; no conclusion about unknown copyrighted code is fabricated.

## Source and LGPL replacement

The full upstream archives contain the preferred source and build systems for
the covered components. App source includes required packaging and installation
scripts. No evidence of omitted local Qt patches was found; no Qt source changes
are made here. Shared libraries are replaceable without signature/content locks.
The overlay smoke proves loading byte-distinct libraries, not that an arbitrary
modified Qt is ABI-compatible. A separately built Qt is OPTIONAL ASSURANCE;
working compatible replacement remains an LGPL obligation.

GPL/LGPL notices and texts are installed and reachable through Help. About now
gives prominent LGPL library notice alongside the application copyright notice
(LGPL §4(c)). There are no activation keys, locked installation mechanisms or
contracts prohibiting debugging modified LGPL libraries. See
[BUILD_AND_REPLACE.md](BUILD_AND_REPLACE.md) for replacement instructions.

## itch.io and publication

Selling GPL software is permitted. The reviewed
[itch.io terms](https://itch.io/docs/legal/terms) §4 includes publisher grants
and a service-based user licence; §8 permits paid downloads. This does not
independently prove authority to grant every requested right over third-party
code. The listing must retain the explicit GPL grant and free exact source
links. Ask a qualified reviewer about §4's sublicensing/derivative-work grant
for third-party GPL and Microsoft material; do not add a restrictive product
EULA. Nothing was published or changed on itch.io.

An unavailable upstream URL is recorded separately from a verified local file.
Local files are hashed again; independently downloaded upstream archives are
compared against retained hashes. Exact release archive URLs cannot pass until
publication is authorized and completed. See
[closure-source-url-checks.json](evidence/closure-source-url-checks.json).
