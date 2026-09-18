# Windows installer

The installer is built with Python 3.13, PyInstaller 6.22.3 and Inno Setup 6.4.3.
It contains the application, Python/Qt runtime, assets, Stockfish 19 and all three
opening books. Users do not need to install Python separately.

It installs for the current user under `%LOCALAPPDATA%\Programs\OTBMaster3D`,
adds a Start menu shortcut, and offers an optional desktop shortcut. Settings,
session recovery and generated sounds live in `%LOCALAPPDATA%\OTBMaster3D`.
Uninstalling removes program files and shortcuts while preserving that user data.

## Build

Create a Python 3.13 virtual environment, install requirements.txt, then install
`pyinstaller==6.22.3`. Install Inno Setup separately. From the repository root:

```powershell
.\tools\build_installer.ps1 -Python .\.venv\Scripts\python.exe -Compiler 'C:\path\to\ISCC.exe'
```

The result is `installer-output/OTBMaster3D-1.2.0-beta.1-Setup.exe`.
`dist/OTBMaster3D` is the complete standalone application folder; the executable
needs its neighbouring files. Do not copy just OTBMaster3D.exe.

The payload includes the application's source snapshot, Stockfish source and
licence, third-party licence evidence and exact runtime versions in build-info.json.
Qt libraries stay separate DLLs. The build excludes unused PDF, SVG, QML and
virtual-keyboard plugins, and explicitly includes GLFW's native DLLs.

## Verification

Run `OTBMaster3D.exe --smoke-test report.json` to verify native OpenGL rendering,
the app icon, menu order, engine loading/evaluation and opening books. This check
uses temporary settings and exits after writing its JSON report.

The installer is unsigned. Windows may show an unknown-publisher warning.
Hardware OpenGL support remains required; testing on this development machine
does not replace testing on a clean Windows machine.
