param(
    [string]$Python = '.\.venv-test\Scripts\python.exe',
    [string]$Compiler = '.\.build-tools\inno\ISCC.exe'
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & $Python -c "import sys; assert sys.version_info[:2] == (3, 13), 'Build with Python 3.13'"
    if ($LASTEXITCODE) { throw 'Incorrect build runtime' }
    & $Python -c "import tkinter; tkinter.Tcl()"
    if ($LASTEXITCODE) { throw 'Tcl/Tk cannot initialize. Use a complete Python installation with desktop access before building.' }
    & $Python tools/install_stockfish.py
    if ($LASTEXITCODE) { throw 'Stockfish setup failed' }
    & $Python tools/install_fairy_stockfish.py
    if ($LASTEXITCODE) { throw 'Fairy-Stockfish setup failed' }
    # Only the two reviewed engine payloads are packaged.
    & $Python tools/build_native_runtime.py
    if ($LASTEXITCODE) { throw 'Native GLFW build failed' }
    & $Python tools/build_icon.py
    if ($LASTEXITCODE) { throw 'Icon build failed' }
    & $Python -m PyInstaller --noconfirm packaging/windows-folder.spec
    if ($LASTEXITCODE) { throw 'Application build failed' }
    & $Python tools/prepare_installer_payload.py
    if ($LASTEXITCODE) { throw 'Source and licence staging failed' }
    & $Python tools/check_external_runtime.py dist/OTBMaster3D
    if ($LASTEXITCODE) { throw 'Microsoft standalone binary found in payload; external prerequisite policy violated' }
    & $Compiler packaging/windows-installer.iss
    if ($LASTEXITCODE) { throw 'Installer compilation failed' }
} finally {
    Pop-Location
}
