# Native runtime remediation — 2026-09-29

**Later Microsoft packaging decision:** current source requires a separately
installed runtime and excludes standalone Microsoft runtime files. The original
build below is unchanged. See [Microsoft remediation](MICROSOFT_RUNTIME_REMEDIATION.md)
for current policy, checks and the remaining embedded-code question.

Current disposition: [LICENSING-CLOSURE.md](LICENSING-CLOSURE.md) and
[RELEASE-COMPLIANCE.md](RELEASE-COMPLIANCE.md) supersede the blocker assessment
below. This report remains the historical record for the unchanged installer
with SHA-256 a785b63b0857743d9dbdf664846032752cc22a298909e4b22d7da410b29ac8fc.

**Release status: BLOCKED.** No publication, push, tag or store change was made.
This report supersedes earlier native-runtime status statements. Historical
inventories are preserved. Public source URL verification is a separate
publication prerequisite.

## Resolved engineering issues

- GLFW 3.4 was rebuilt from the hash-verified retained upstream archive with
  MSVC 14.44.35207 and Windows SDK 10.0.26100.0, x64, `/O2 /MD /DNDEBUG`.
  No upstream source patches were applied. Both Win32 and null backends remain;
  WGL, EGL and OSMesa support remain in the version string. The generated resource
  uses the upstream template. Exact commands and compiler/linker hashes are in
  [glfw-build.json](evidence/glfw-build.json); compiler output is in
  [glfw-build.txt](evidence/glfw-build.txt).
- Original and rebuilt GLFW passed the same hidden-window/context, clear,
  pixel-readback, swap, event-poll and destruction probe. Both returned
  `[64,128,191,255]`. This is a targeted behaviour comparison, not exhaustive
  coverage of input devices or every GLFW API.
- The rebuilt GLFW imports VCRUNTIME140 and Windows UCRT API sets, without
  MSVCR120. The Python wrapper's fallback explicitly preloads MSVCR120;
  installing the rebuilt DLL beside the executable uses its first supported
  lookup and avoids that fallback without patching the wrapper.
- Packaging selects five reviewed CRT DLLs from the installed VS2022
  `VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT` directory. **Their file
  version is 14.44.35211.0**; the folder name is not the DLL version.
  [crt-selection.json](crt-selection.json) pins hashes, architecture, versions
  and imports. Windows signature validation returned Valid for these inputs;
  see [signature evidence](evidence/crt-signatures.json).
- The build rejects changed CRT hashes, version downgrades, missing imported
  CRT exports and residual MSVCR100/MSVCR120 imports. Duplicate CRT destinations
  use the same reviewed bytes. Qt itself was not rebuilt.

On another build machine, `OTB_VS_ROOT` selects the licensed VS installation and
`OTB_CRT_ROOT` selects its reviewed CRT directory; hashes must still match.
Run `tools/build_installer.ps1 -Python .\.venv-test\Scripts\python.exe` with
Python 3.13 and a working Tcl/Tk installation. The spec fails if required
Tcl/Tk binaries disappear from freezer output.

## Inventory and provenance

Run `tools/audit_native_runtime.py` with the Python 3.13 build environment.
[Before](native-runtime-before.json) and [after](native-runtime-after.json)
records cover every DLL, PYD and EXE, including engine executables: SHA-256,
architecture, version resources, normal/delay imports and imported symbols.
Final records include installed-wheel RECORD matches and freezer input paths.
An installed RECORD match establishes local package mapping, not independent
publisher authentication. Dynamic loading and static incorporation require
the additional evidence below; absence from the import table is insufficient.

| Payload family | Identified origin and corresponding material |
| --- | --- |
| GLFW | Native 3.4 source; Python wrapper glfw 2.10.2; separate zlib/libpng and MIT notices |
| Qt/PySide/Shiboken | Wheels 6.11.2, x64 shared release MSVC2022; official QtBase and PySide setup archives with published checksum matches |
| Software OpenGL | PySide6_Essentials wheel; Qt's Mesa 11.2.2 prebuilt with embedded LLVM 3.6.2 |
| Pillow | Wheel 12.3.0; sdist, complete upstream tag, winbuild recipes/patches and codec archives |
| cozy-chess-py | Wheel 0.1.1; matching sdist, Cargo.lock and checksum-verified crate sources |
| CPython/native dependencies | 3.13.12 Windows installation; CPython PCbuild and previously collected native sources; exact source paths in inventory |
| Stockfish | 19 universal x64 executable; sf_19 source, Makefile and matching required NNUE |
| Application | Current source snapshot and PyInstaller 6.22.3 bootloader |
| CRT | Microsoft components governed separately; exact selected VS Redist files, not inferred entitlement from filenames |

### Software OpenGL

The packaged DLL contains Mesa 11.2.2 and LLVM 3.6.2 version strings. Qt's
official `opengl32sw-64-mesa_11_2_2-signed_sha256.7z` archive matches its published
SHA-256. Every extracted PE section matches the wheel DLL, including code and
read-only data. Whole-file hashes differ; no claim of whole-file equality is made.
See [section evidence](evidence/software-opengl-provenance.json).

Mesa 11.2.2 source was obtained with a published SHA-256 match; LLVM 3.6.2
source was obtained from its official archive and locally hashed. Both now
appear in source-inventory.json. Original notice files are retained beneath
`licenses/software-opengl/`. Qt's current Mesa build wiki describes later
versions and additional patches. It does **not** establish the exact patches,
configuration or incorporated static Microsoft runtime for this older DLL.
That provenance review remains open. Removing software rendering would change
supported behaviour, so the DLL remains in the payload.

### Static codecs and other embedded libraries

[Static build evidence](evidence/static-build-review.json) records runtime
features and hashes of upstream Windows recipes and CI scripts.

- Pillow `_imaging` embeds JPEG-turbo 3.1.4.1, OpenJPEG 2.5.4, TIFF 4.7.1 and
  zlib-ng 2.3.3; `_webp` uses WebP 1.6.0; `_imagingcms` reports LittleCMS 2.19
  (the source pin is 2.19.1); `_imagingft` reports FreeType 2.14.3. The aggregate
  notice/build recipe identifies supporting PNG, Brotli, HarfBuzz, bzip2 and xz.
- `_avif` reports libavif 1.4.2. The pinned Windows recipe selects static
  libavif, local AOM encoding, dav1d decoding, libyuv and libsharpyuv, MinSizeRel
  and interprocedural optimization. Its flags and text patches are retained in
  `winbuild/build_prepare.py`. The exact libyuv commit is already collected.
- RAQM, libimagequant and XCB are unavailable in the inspected Pillow runtime;
  a dependency pin alone does not establish that they were incorporated.
- QtBase retains embedded sources and third-party attribution for its codecs,
  compression, font and text libraries. Exact enabled-feature configuration for
  the wheel build remains unconfirmed. CPython's PCbuild and cozy's Cargo.lock
  provide their static-dependency build materials; compiler-build provenance
  is not independently authenticated by matching a wheel RECORD.
- No FFmpeg DLL was found. Pillow's MPEG format plugin is not evidence of a
  bundled MPEG decoder. PE imports cannot enumerate static libraries reliably.

### Required source versus optional reproducibility

GPLv3 section 1 describes preferred source and scripts needed to generate,
install, run and modify the covered work, with its stated exclusions. Preserve
needed patches, configuration and notices. A different timestamp, signature,
compiler patch level or non-bit-identical rebuild alone does not establish a
licence violation. Exact bit reproduction and rebuilding all of Qt are not
blanket requirements. Permissively licensed components also have their own
notice obligations; do not assign GPL source obligations solely from adjacency.

The retained sources and recipes substantially narrow the review. They do not
prove that unknown upstream patches were absent. The full dependency bundle
therefore remains a review bundle pending those specific provenance questions.
The LGPL overlay smoke checks replacement loading; it does not demonstrate a
separately source-built Qt or arbitrary ABI compatibility.

## Microsoft entitlement and distribution conditions

The [official REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)
covers unmodified files in `VC/redist`, subject to its exclusions and licence
terms. The selected files are in the release x64 CRT directory, and their
signatures and hashes were checked. The [compatibility guidance](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017?view=msvc-170)
requires a runtime at least as recent as the relevant build tools; version and
export checks support this selection. They do not replace clean-machine tests.

The retained Community terms permit individual development for sale and the
specified organizational open-source work. Section 4 also imposes conditions
on distribution, including protective terms for distributors/end users.
The existing GPL-only installer acceptance does not establish compliance with
that separate requirement. **End-user/distributor terms for the Microsoft
components and the applicable licensed-user basis remain to be settled before
release.** Do not add Microsoft restrictions to the application's GPL source,
and do not describe presence in an installation as unconditional entitlement.
App-local deployment also requires maintaining the CRT in future installers.

## Verification and remaining blockers

Exact commands/results are recorded in [native-verification.json](native-verification.json).
The final folder has **64 native files (29 DLLs)** and no unresolved normal/delay
import edges. All 64 native hashes match the installed copy; the installer adds
its own Inno Setup uninstaller. See [installer verification](installer-verification.json)
and [installed inventory](native-installed-inventory.json). GLFW retains all
134 original exported names; [export comparison](evidence/glfw-export-comparison.json).

The rebuilt folder and installed copy both passed hidden startup, board
framebuffer/OpenGL checks, Stockfish evaluation, opening-book checks, current
position PGN file roundtrip, synchronous PlaySound and window/event-loop shutdown.
The process exit code was 0. Loaded-module paths confirm app-local selected CRT
files and the rebuilt GLFW. The LGPL overlay test passed for 15 Qt/PySide/Shiboken
files; Mesa and Microsoft DLLs were excluded from that LGPL-specific test.

The installer is `installer-output/OTBMaster3D-1.4.0-beta.2-Setup.exe`, SHA-256
`a785b63b0857743d9dbdf664846032752cc22a298909e4b22d7da410b29ac8fc`.
These are development-host results, not clean Windows validation.

The complete regression run executed 241 tests: **2 failures and 4 errors**.
[Full output](evidence/native-regression-tests.txt) is retained, unchanged.
Two errors reference removed engine APIs, one fixture lacks `clocks_disabled`,
and the remaining failures concern OpenGL context creation. The two affected
graphics modules passed all 15 tests when rerun unchanged in a fresh process;
the full-suite failure remains unresolved. Tests were neither removed nor
weakened to produce a passing result.

The host is a development machine with VS and Python installed. Windows Sandbox
and the Hyper-V service were unavailable. The maintainer asked to wait on the
clean-environment check. A local installation or sanitized PATH is not a clean
Windows test. Audible output also needs listening confirmation; successful
PlaySound API completion alone does not prove sound reached the speakers.

Remaining local blockers are the failed regression suite, clean Windows
verification, Microsoft distribution conditions, and the specific native
source/configuration provenance gaps above. Public archive URL verification
remains separate and is not evidence that a local source archive is missing.
