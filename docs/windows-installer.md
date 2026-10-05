# Windows installer

The installer is built with Python 3.13, PyInstaller 6.22.3 and Inno Setup 6.4.3.
The revised packaging includes the application, Python/Qt runtime, assets, Stockfish 19,
Fairy-Stockfish 14, Rodent IV with its personalities and repertoire books, and all three
opening books. Users do not need to install Python separately.
The current release is [1.6.5](releases/1.6.5-source.md), built from commit
`4e1ba003c85bf10d3c238aa4ef791d081af55209`. Rodent IV is required by the frozen
build specification; packaging verifies its executable, resources, source archive
and notices. Historical verification reports describe their named builds only.

Current packaging requires Microsoft Visual C++ x64 Redistributable 14.44.35211.0
or newer to be installed separately from Microsoft. Setup stops with the official
download address if it is missing, including during silent setup. No standalone
Microsoft runtime DLL or redistributable package is included in the payload.
For the prerequisite policy and remaining review items, see
[Microsoft remediation](licensing/MICROSOFT_RUNTIME_REMEDIATION.md).
Clean Windows installation, upgrade and uninstall validation remain pending.

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
requires MinGW-w64 `g++` on PATH to build Rodent IV on a fresh checkout. An existing
Rodent installation is reused only after its resource manifest is verified. It also
requires a licensed VS2022 C++ toolchain/Windows SDK, the retained GLFW 3.4 source
archive under `release-materials/1.4.0-beta.2/sources/`, and the reviewed CRT
hashes in `docs/licensing/crt-selection.json`. `OTB_VS_ROOT` and `OTB_CRT_ROOT`
can select different installation locations while preserving the pinned inputs.
From the repository root:

```powershell
.\tools\build_installer.ps1 -Python .\.venv\Scripts\python.exe -Compiler 'C:\path\to\ISCC.exe'
```

The result is `installer-output/OTBMaster3D-1.6.5-Setup.exe`.
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

The public [1.6.5 release](https://github.com/nork79/OTBMaster3D/releases/tag/v1.6.5)
provides the installer and matching source bundles. For its exact application
snapshot, use the application archive or check out `v1.6.5`. Documentation on
`main` can contain subsequent updates. Keep otb_chess/version.py,
packaging/windows-installer.iss and packaging/version-info.txt synchronized when
preparing a new release; version bumps are not automatic.

```powershell
git clone https://github.com/nork79/OTBMaster3D.git
cd OTBMaster3D
git checkout v1.6.5
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_installer.ps1 -Python .\.venv\Scripts\python.exe -Compiler 'C:\path\to\ISCC.exe'
```

The process-only execution policy option permits this reviewed local script to
run; it does not change machine policy. Engine setup requires network access on
a fresh checkout. Stockfish, Fairy-Stockfish and Rodent IV are installed by this workflow. Preserve exact
download archives, dependency sources, wheel hashes, compiler version and build
options. Do not promise bit-for-bit reproducibility from version pins alone.

The build copies LICENSE, COPYRIGHT.md, THIRD_PARTY_LICENSES.md,
THIRD_PARTY_NOTICES.md, SOURCE_ACCESS.md and licences into the folder payload.
Per-asset and per-engine notices remain in their existing directories. The About
dialog reads them without network access. Installer metadata identifies nork79
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
The original build metadata retains its pre-publication status; the version-specific
release manifest records the published artifact pairing.

For each public version, retain the installer, its SHA-256, build-info.json,
application ZIP, dependency source bundle, source hashes and a file-level native
component inventory. Put prominent links to the exact free source downloads beside
the installer download. Follow [source-access requirements](../SOURCE_ACCESS.md).

Test install, upgrade, uninstall, offline launch, offline licence access and
compatible Qt library replacement on a clean Windows machine. Source-level tests
and a local compiler success do not replace these checks. Never publish local
build logs containing personal paths.
