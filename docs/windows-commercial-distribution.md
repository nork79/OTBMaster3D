> Historical research only. The current release strategy is GPL-3.0-only source
> and a Windows installer; its distribution channel is not yet selected.
> See [release preparation](OPEN_SOURCE_RELEASE_READINESS.md).
> The proprietary migration and paused-build statements below are superseded.

# Historical proprietary-distribution research

**Superseded for the public beta:** OTBMaster3D 1.0.0 Beta 1 is a free, open-source
GPL-3.0-or-later source release. There is no current proprietary release plan.
The material below is preserved as historical engineering research; installer
compilation is paused. See [current release notes](releases/1.0.0-beta.1.md).

# Windows commercial distribution preparation

**NOT READY FOR PROPRIETARY RELEASE.** python-chess 1.11.2 remains GPL-3.0-or-later
and must be removed/replaced before the intended proprietary commercial release.
Qt licensing work does not solve this separate issue. Follow
[the existing migration plan](chess-backend-migration.md); no migration architecture
is changed by this task. This is engineering preparation, not a legal opinion.

## Dynamic folder deployment

The active runtime and migration target is standard CPython 3.13 on Windows x64.
Use a fresh 3.13 build environment with the existing dependency pins. The
[compatibility baseline](python-313-compatibility.md) validates the source app;
it does not qualify a frozen distribution. Existing notices/BOM runtime versions
describe the earlier audited environment and must be regenerated and verified
against the actual 3.13 release build before shipping.

`packaging/windows-folder.spec` is an unbuilt PyInstaller onedir draft, not an
installer or a validated redistribution configuration. No Qt source or library
is statically linked by this plan. PySide6 stays the UI framework. All Qt DLLs,
plugins and binding extension modules remain ordinary separate deployed files.
PySide6/shiboken Python support modules are also collected externally, not hidden
in the application PYZ. No one-file extraction, DLL encryption, replacement
signature lock or proprietary native blob containing Qt is intended.

Expected folder layout (actual hook output must be inspected):

```text
OTBMaster3D/
  OTBMaster3D.exe
  python313.dll and audited runtime dependencies
  PySide6/Qt6Core.dll, Qt6Gui.dll, Qt6Widgets.dll
  PySide6/Qt6OpenGL.dll, Qt6OpenGLWidgets.dll
  PySide6/*.pyd and supporting Python files
  PySide6/plugins/platforms/qwindows.dll
  shiboken6/ (binding support DLL/PYD and Python files)
  assets/
  sounds/ (regenerated from application code in a clean staging build)
  licenses/
  THIRD_PARTY_NOTICES.md
  third_party_bom.json
```

Image loading currently uses Pillow. No Qt imageformats plugins are explicitly
required; add only audited ones if clean-machine testing demonstrates a need.
The draft rejects unknown Qt6 DLLs, PySide6 binding modules and plugins, including
GPL-only modules. A rejection is a request to investigate, not to blindly extend
the allowlist. OS OpenGL drivers are not copied. Legacy imports currently make
GLFW and Tcl/Tk reachable; preserve functionality, inventory any files the freezer
collects, and review their licences. This task deliberately does not remove them.

## Notices, sources and replacement

Help → Open Source Licences identifies the installed notices directory. Ship the
full THIRD_PARTY_NOTICES.md, JSON inventory and licenses/ files alongside the EXE.
Before distribution replace unresolved notice placeholders with verified licence
texts and applicable notices. Archive exact wheel/source hashes, compiler/build
options, Qt/PySide/Shiboken versions, local modifications and native dependencies.
Implement an appropriate corresponding-source delivery/offer mechanism for the
covered components, reviewed against LGPLv3/GPLv3; generic links alone are not
assumed sufficient. Provide required installation/relinking information.

Users should close the application, back up its folder, and replace the relevant
PySide6 Qt DLLs/plugins/bindings (and Shiboken support where necessary) with an
ABI-compatible build of the same architecture and supported Python ABI. Keep
plugin and Qt versions compatible. Document the exact locations and build recipe
from the final distribution and demonstrate that a modified compatible build
loads. Do not require an application rebuild or vendor approval for replacement.
Do not prohibit reverse engineering needed to debug those modifications in the
application EULA. Do not claim arbitrary Qt versions will be compatible.

Static linking is intentionally avoided because it complicates relinking and
delivery of the materials users need to exercise LGPL rights. Dynamic deployment
does not by itself satisfy all LGPL obligations.

## Before release

1. Resolve python-chess and verify no GPL-only runtime dependency is packaged.
2. Select and pin a packaging tool version compatible with Python 3.13; audit
   PyInstaller's bootloader exception and its dependency licences. It is not
   installed or executed by this preparation task.
3. Complete the exact binary SBOM, native dependency closure and source archives:
   Qt third-party code, Pillow codecs, CPython, Tcl/Tk, GLFW and MSVC runtimes.
   Resolve every “requires verification before release” entry.
4. Test the onedir draft on a clean Windows VM, including normal startup, assets,
   GL rendering, clocks, PGN/FEN, engine subprocesses, notice paths, and Qt replacement.
   The current config/sound path expects a writable portable application folder;
   a Program Files installer requires a later user-data path design and testing.
5. Supply all notices, texts and covered-source access, and review the EULA and
   installation-information obligations. Retain MIT asset copyright notices and
   CC0 provenance. Do not silently bundle user-supplied engines/books/backgrounds.
6. Obtain final legal review, then design/sign/test an installer separately.

Official references: [Qt obligations](https://www.qt.io/development/open-source-lgpl-obligations),
[Qt module licensing](https://doc.qt.io/qt-6/licensing.html),
[Qt for Python notices](https://doc.qt.io/qtforpython-6/licenses.html),
[PyInstaller deployment](https://pyinstaller.org/en/stable/usage.html).
