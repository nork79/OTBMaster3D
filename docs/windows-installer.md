# Windows installer

The installer is built with Python 3.13, PyInstaller 6.22.3 and Inno Setup 6.4.3.
The revised packaging includes the application, Python/Qt runtime, assets, Stockfish 19,
Fairy-Stockfish 14 and all three
opening books. Users do not need to install Python separately.
The application and packaging version remains 1.6.0, while `main` contains changes
after the `v1.6.0` tag. Optional Rodent IV is built separately for the source
workspace and is not included by the frozen build specification. The retained
[1.6.0 source preparation](releases/1.6.0-source.md) describes a particular local
installer, not validation of current `main`. Historical installer
verification is recorded in [native remediation](licensing/NATIVE_RUNTIME_REMEDIATION.md).

Current packaging requires Microsoft Visual C++ x64 Redistributable 14.44.35211.0
or newer to be installed separately from Microsoft. Setup stops with the official
download address if it is missing, including during silent setup. No standalone
Microsoft runtime DLL or redistributable package is included in the planned payload.
For the prerequisite policy and remaining review items, see
[Microsoft remediation](licensing/MICROSOFT_RUNTIME_REMEDIATION.md).
Release remains blocked; these are review artifacts.

It installs for the current user under `%LOCALAPPDATA%\Programs\OTBMaster3D`,
adds a Start menu shortcut, and offers an optional desktop shortcut. Settings,
session recovery and generated sounds live in `%LOCALAPPDATA%\OTBMaster3D`.
Uninstalling removes program files and shortcuts while preserving that user data.

## Build

Use a complete Python 3.13 installation with Tkinter and native desktop access.
The build checks Tcl initialization before packaging; a restrictive sandbox can
prevent this even when Tcl files are installed.

Create a Python 3.13 virtual environment, install requirements.txt, then install
`pyinstaller==6.22.3`. Install Inno Setup separately. Native preparation also
requires a licensed VS2022 C++ toolchain/Windows SDK, the retained GLFW 3.4 source
archive under `release-materials/1.4.0-beta.2/sources/`, and the reviewed CRT
hashes in `docs/licensing/crt-selection.json`. `OTB_VS_ROOT` and `OTB_CRT_ROOT`
can select different installation locations while preserving the pinned inputs.
From the repository root:

```powershell
.\tools\build_installer.ps1 -Python .\.venv\Scripts\python.exe -Compiler 'C:\path\to\ISCC.exe'
```

The result is `installer-output/OTBMaster3D-1.6.0-Setup.exe`.
`dist/OTBMaster3D` is the complete standalone application folder; the executable
needs its neighbouring files. Do not copy just OTBMaster3D.exe.

The payload includes the application's source snapshot, Stockfish source and
licence, third-party licence evidence and exact runtime versions in build-info.json.
Qt libraries stay separate DLLs. The build excludes unused PDF, SVG, QML and
virtual-keyboard plugins, and explicitly includes GLFW's native DLLs.

## Verification

Run `OTBMaster3D.exe --smoke-test report.json` to verify native OpenGL rendering,
the app icon, menu order, engine loading/evaluation, opening books, a PGN file
roundtrip, the Windows sound API and shutdown. This check
uses temporary settings and exits after writing its JSON report.

The installer is unsigned. Windows may show an unknown-publisher warning.
Hardware OpenGL support remains required; testing on this development machine
does not replace testing on a clean Windows machine.

## Clean checkout procedure and source pairing

Public source downloads and clean Windows validation remain pending; see
[source preparation status](releases/1.6.0-source.md). The repository is private
and the final distribution channel is not selected.
Local builds are review artifacts. Before a release build, finish review, choose
one immutable source revision, and set the same version in otb_chess/version.py,
packaging/windows-installer.iss and packaging/version-info.txt. No version bump is
made automatically. The current target is 1.6.0 / Windows tuple 1.6.0.0.

```powershell
git clone https://github.com/norKI79/OTBMaster3D.git
cd OTBMaster3D
# Select the reviewed release commit, once the maintainer has created it.
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_installer.ps1 -Python .\.venv\Scripts\python.exe -Compiler 'C:\path\to\ISCC.exe'
```

The process-only execution policy option permits this reviewed local script to
run; it does not change machine policy. Engine setup requires network access on
a fresh checkout. Stockfish and Fairy-Stockfish are installed by this workflow. Preserve exact
download archives, dependency sources, wheel hashes, compiler version and build
options. Do not promise bit-for-bit reproducibility from version pins alone.

The build copies LICENSE, COPYRIGHT.md, THIRD_PARTY_LICENSES.md,
THIRD_PARTY_NOTICES.md, SOURCE_ACCESS.md and licences into the folder payload.
Per-asset and per-engine notices remain in their existing directories. The About
dialog reads them without network access. Installer metadata identifies norKI79
as publisher and GPLv3 as the application licence; no company or signing identity
is invented. The installer displays the GPL and source-access information.

`build-info.json` records the application version, dependency versions, base commit,
working-tree status and application archive SHA-256. `source/application-files.sha256.json`
records each archived application file. A dirty build's archive identifies its
actual source; the base commit alone does not. Build only a reviewed clean commit
for publication. The snapshot includes tracked files and new project documentation,
but excludes ignored user state. Inspect it before distribution.

The script also preserves installed python-chess Python source and its GPL text.
The source ZIP **does not include all dependency Corresponding Source**. Supply the
separate verified dependency source bundle described in [SOURCE_ACCESS.md](../SOURCE_ACCESS.md).
The current manifest explicitly marks publication BLOCKED.

For each public version, retain the installer, its SHA-256, build-info.json,
application ZIP, dependency source bundle, source hashes and a file-level native
component inventory. Put prominent links to the exact free source downloads beside
the installer download. Follow [source-access requirements](../SOURCE_ACCESS.md).

Test install, upgrade, uninstall, offline launch, offline licence access and
compatible Qt library replacement on a clean Windows machine. Source-level tests
and a local compiler success do not replace these checks. Never publish local
build logs containing personal paths.
