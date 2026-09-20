param([string]$Python = "")
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $Python) {
    $installation = Get-ItemProperty 'HKCU:\Software\Python\PythonCore\3.13\InstallPath' -ErrorAction SilentlyContinue
    if (-not $installation) {
        $installation = Get-ItemProperty 'HKLM:\Software\Python\PythonCore\3.13\InstallPath' -ErrorAction SilentlyContinue
    }
    $Python = $installation.ExecutablePath
}
if (-not $Python) { throw 'Supply -Python with the path to a Python 3.13 interpreter.' }
& $Python -c "import sys; assert sys.version_info[:2] == (3, 13), 'Tests require Python 3.13 for cozy-chess-py'"
if ($LASTEXITCODE) { throw 'Unsupported Python interpreter.' }
$environment = Join-Path $root '.venv-test'
& $Python -m venv $environment
if ($LASTEXITCODE) { throw 'Could not create test environment.' }
$testPython = Join-Path $environment 'Scripts\python.exe'
& $testPython -m pip install -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE) { throw 'Could not install test dependencies.' }
& $testPython -m pip check
if ($LASTEXITCODE) { throw 'Dependency check failed.' }
Write-Output "Test environment ready: $testPython"
