# Building sources and replacing LGPL components

The runtime staging policy and review results below record an earlier preparation
build. Current packaging requires the Microsoft runtime to be installed separately;
it does not stage the redistributable. See [current build instructions](../windows-installer.md),
[runtime remediation](MICROSOFT_RUNTIME_REMEDIATION.md) and
[1.6.0 source preparation](../releases/1.6.0-source.md). The historical cache and
bundle names below remain inputs to the retained tooling, not the current app version.

Current status: [finite licensing closure](LICENSING-CLOSURE.md).
The following central-runtime policy is prepared in source; the existing
installer predates it because desktop-access approval for rebuilding was declined.
`tools/build_native_runtime.py` builds the retained GLFW 3.4 archive with MSVC2022.
The spec requires this output and validates imports against the hash-pinned CRT
set in crt-selection.json. The installer now stages Microsoft's official x64
redistributable and requires version 14.44.35211.0 or newer centrally; it omits
the ten prior app-local CRT copies after checking their dependencies. Folder
builds require this prerequisite too. Newer installed runtimes are retained.
The shared Qt binaries remain replaceable. An independent Qt rebuild is an
optional stronger verification exercise; bit-identical output is not a blanket
source-licence requirement. No local Qt patches are applied. Actual preferred
sources, upstream scripts, patches and notices are retained in the source bundle.

Latest evidence: [blocker recheck](BLOCKER_RECHECK.md). Exact libyuv source is now collected;
Visual Studio Community 2022 and its C++ toolset were found. Earlier download and
PATH-only findings below are superseded by that report.

## Source bundle

Run with the pinned Python 3.13 environment:

```powershell
.\.venv-test\Scripts\python.exe tools/prepare_corresponding_source.py
```

The default output is `release-materials/1.4.0-beta.2/`. It contains the application
snapshot, dependency source ZIP, per-file hashes and source-release-manifest.json.
All source archive hashes are checked against source-inventory.json. `--fetch`
retrieves missing upstream archives and rejects changed bytes. The locally
assembled Staunton STL archive must be restored from the supplied source bundle.
Source packaging requires no installer build and performs no publication.

The dependency ZIP is a **review bundle, not a claim of complete Corresponding
Source**. See the remaining issues in source-inventory.json and REMEDIATION.md.
The exact libyuv source is retained from its official Git commit. Upstream URL
availability and local source completeness are independently recorded.

## Matching build material collected

| Component | Build material in the source bundle | Remaining verification |
| --- | --- | --- |
| Qt 6.11.2 | Official qtbase-everywhere source, CMake/configure scripts, embedded third-party sources, module licences and attribution files | QtCore/Gui/Widgets/OpenGL/OpenGLWidgets and qwindows/qico are in qtbase. Installed binaries identify MSVC 2022; exact upstream compiler patch level, options and reproducible build comparison remain unverified |
| PySide/Shiboken 6.11.2 | Official pyside-setup source, setup.py/CMake, binding type systems and build documentation | Build against the same Qt version, x64 architecture and Python limited API. Shiboken generator/Clang are build tools; do not bundle them merely to build the runtime |
| python-chess 1.11.2 | PyPI sdist with source/build metadata and GPL | No native rebuild needed; retain original notices |
| cozy-chess-py 0.1.1 | sdist, Cargo.toml/Cargo.lock and every registry crate in that lock with matching checksum | Use the manifest's pinned versions and upstream maturin build recipe; verify compiler/target provenance for the actual wheel |
| PyOpenGL 3.1.10 / GLFW 3.4 | Exact PyPI sdist and native GLFW source/CMake | Wrapper source is present. Native GLFW reports VisualC DLL; verify original toolchain options. Keep Windows graphics drivers external |
| Pillow 12.3.0 | PyPI sdist plus complete upstream archive, winbuild/build_prepare.py, dependency version pins and codec source releases | Upstream Windows patches/options are retained. libavif's libaom 3.14.1 and dav1d 1.5.3 collected; libyuv commit 644251f25 failed twice with HTTP 503. Audit exact static codec configuration before claiming closure |
| CPython 3.13.12 | Official source, PCbuild build files, required identified OpenSSL/libffi/Tcl/Tk/bzip2/xz/zlib/mpdecimal source versions | Build with a compatible supported MSVC environment; exact native binary provenance and Microsoft entitlement remain separate checks |
| Stockfish 19 | Exact sf_19 upstream source and supplied src/Makefile; required nn-1a298aa575a0.nnue | Network bytes match the official Git LFS SHA-256; source includes universal build scripts. Reproduce/review the official universal build recipe, rather than claiming a generic single-architecture build is byte-identical |
| Artwork | Original Blender file, Staunton STL files, retained Monge/Chessnut/Firi imports, plus project SVG/TSV sources | Existing conversion scripts are in the application source archive; original permissive notices remain |

Follow the build documentation inside each pinned archive. A generic command such
as `cmake --build` is not evidence of the flags used for the actual shipped binary.
MSVC2022 was located outside PATH and used for the recorded GLFW build. No native
Qt source rebuild was performed; that is optional additional verification.

## Installed library replacement procedure

1. Close OTBMaster3D and back up its installation folder.
2. Build a compatible x64 Qt 6.11.2 and PySide/Shiboken set for the application's
   Python ABI. Keep the five selected Qt modules and the Windows platform plugin.
3. Replace `PySide6/Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, `Qt6OpenGL.dll`,
   `Qt6OpenGLWidgets.dll`, the matching Qt `.pyd` modules and PySide support DLL,
   `PySide6/plugins/platforms/qwindows.dll`, `PySide6/plugins/imageformats/qico.dll`,
   and matching `shiboken6/` support files as required by your modifications.
   Keep module/plugin versions compatible. The exact deployed list is qt-components.json.
4. Start the app and run its smoke test. Test normal play, rendering, licences,
   engine operation and affected library functionality. Restore the backup if the
   replacement is ABI-incompatible. No vendor signature or application key is needed.

The application does not prohibit modification or reverse engineering needed to
debug LGPL library modifications. Keep the relevant notices and source with your
distribution. See [Qt's obligations](https://www.qt.io/development/open-source-lgpl-obligations)
and the included LGPLv3/GPLv3 texts.

## Executed replacement test and its limit

`tools/check_lgpl_replacement.py` copies the frozen payload to an isolated directory,
adds a harmless PE overlay to each applicable Qt/PySide/Shiboken DLL/PYD, verifies
changed hashes, and runs the existing hidden smoke test. **16 byte-distinct
replacements loaded successfully**, including rendering and Stockfish operation.
Sanitised evidence: [lgpl-replacement-result.json](lgpl-replacement-result.json).

This establishes that the existing packaged app accepts replaced libraries without
a content-hash lock. The overlay does not change exported interfaces or compiled
Qt behaviour; it is **not a separately rebuilt or functionally modified Qt test**.
That older test used the pre-remediation binary. Current evidence is
evidence/closure-lgpl-replacement.json, testing the 15 covered files and excluding
Mesa/Microsoft components. A compatible source-built replacement is optional
additional assurance, not a requirement inferred from nonidentical binaries.
