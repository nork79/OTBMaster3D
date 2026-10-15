[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Version = '',
    [string]$Python = '.\.venv-test\Scripts\python.exe',
    [string]$Compiler = '.\.build-tools\inno\ISCC.exe',
    [switch]$DryRun,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArguments
)
$ErrorActionPreference = 'Stop'

function Invoke-BuildStep([string]$Name, [string]$Executable, [string[]]$Arguments) {
    Write-Host "[BUILD] $Name" -ForegroundColor Cyan
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Name failed (exit code $LASTEXITCODE)." }
    Write-Host "[OK] $Name" -ForegroundColor Green
}

function Replace-VersionField([string]$Text, [string]$Pattern, [string]$Replacement) {
    $expression = [regex]::new($Pattern)
    if ($expression.Matches($Text).Count -ne 1) {
        throw "Expected exactly one version field matching: $Pattern"
    }
    return $expression.Replace($Text, $Replacement)
}

$buildExitCode = 0
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    # Interactive PowerShell treats --version differently from powershell -File.
    # Parse it explicitly and never bind stray arguments to Python or Compiler.
    if ($ExtraArguments.Count -gt 0) {
        if ($ExtraArguments.Count -ne 2 -or $ExtraArguments[0] -ne '--version') {
            throw 'Usage: build_installer.ps1 --version LABEL [-Python PATH] [-Compiler PATH] [-DryRun]'
        }
        if ($PSBoundParameters.ContainsKey('Version')) {
            throw 'Supply either --version or -Version, not both.'
        }
        $Version = $ExtraArguments[1]
    }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $appPath = Join-Path $PWD 'otb_chess/version.py'
    $installerPath = Join-Path $PWD 'packaging/windows-installer.iss'
    $metadataPath = Join-Path $PWD 'packaging/version-info.txt'
    $appText = [IO.File]::ReadAllText($appPath, $utf8)
    if (-not $Version) {
        $match = [regex]::Match($appText, '(?m)^__version__ = "([^"]+)"')
        if (-not $match.Success) { throw 'Cannot read the application version.' }
        $Version = $match.Groups[1].Value
    }
    # Accept release labels freely; keep them safe for filenames and source literals.
    $requestedVersion = $Version
    $Version = [regex]::Replace($Version.Trim(), '[^a-zA-Z0-9._+-]', '-')
    if (-not $Version) { $Version = 'build' }
    if ($Version -ne $requestedVersion) {
        Write-Host "[INFO] Using filename-safe version label: $Version"
    }
    # Windows resources require four unsigned 16-bit numbers, independently of
    # the display label. Pad missing numbers and clamp oversized components.
    $parts = @(0, 0, 0, 0)
    $numbers = [regex]::Matches($Version, '[0-9]+')
    for ($index = 0; $index -lt [Math]::Min(4, $numbers.Count); $index++) {
        $digits = $numbers[$index].Value.TrimStart([char]'0')
        if (-not $digits) { $digits = '0' }
        $parts[$index] = if ($digits.Length -gt 5) { 65535 } else { [Math]::Min(65535, [int]$digits) }
    }
    $windowsVersion = $parts -join '.'
    $tupleVersion = $parts -join ','

    # Validate every replacement before changing any source file.
    $appText = Replace-VersionField $appText '(?m)^__version__ = "[^"]+"' "__version__ = `"$Version`""
    $installerText = [IO.File]::ReadAllText($installerPath, $utf8)
    $installerText = Replace-VersionField $installerText '(?m)^#define AppVersion "[^"]+"' "#define AppVersion `"$Version`""
    $installerText = Replace-VersionField $installerText '(?m)^VersionInfoVersion=[^\r\n]+' "VersionInfoVersion=$windowsVersion"
    $metadataText = [IO.File]::ReadAllText($metadataPath, $utf8)
    foreach ($field in @('filevers', 'prodvers')) {
        $metadataText = Replace-VersionField $metadataText "$field=\([^)]*\)" "$field=($tupleVersion)"
    }
    foreach ($field in @('FileVersion', 'ProductVersion')) {
        $metadataText = Replace-VersionField $metadataText "StringStruct\('$field', '[^']+'\)" "StringStruct('$field', '$Version')"
    }
    $outputPath = Join-Path $PWD "installer-output/OTBMaster3D-$Version-Setup.exe"
    Write-Host "Building OTBMaster3D $Version"
    Write-Host "Windows numeric version: $windowsVersion"
    Write-Host "Installer: $outputPath"
    if ($DryRun) {
        Write-Host '[OK] Dry run: version fields validated; no files changed and no build started.' -ForegroundColor Green
    } else {
        foreach ($command in @($Python, $Compiler)) {
            if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
                throw "Build tool not found: $command"
            }
        }
        Invoke-BuildStep 'Python 3.13 runtime check' $Python @('-c', "import sys; assert sys.version_info[:2] == (3, 13), 'Build with Python 3.13'")
        Invoke-BuildStep 'Tcl/Tk initialization' $Python @('-c', 'import tkinter; tkinter.Tcl()')
        [IO.File]::WriteAllText($appPath, $appText, $utf8)
        [IO.File]::WriteAllText($installerPath, $installerText, $utf8)
        [IO.File]::WriteAllText($metadataPath, $metadataText, $utf8)
        Write-Host "[OK] Version files updated to $Version" -ForegroundColor Green
        Invoke-BuildStep 'Stockfish setup' $Python @('tools/install_stockfish.py')
        Invoke-BuildStep 'Fairy-Stockfish setup' $Python @('tools/install_fairy_stockfish.py')
        Invoke-BuildStep 'Rodent IV setup' $Python @('tools/install_rodent.py', '--ensure')
        Invoke-BuildStep 'Native GLFW build' $Python @('tools/build_native_runtime.py')
        Invoke-BuildStep 'Icon build' $Python @('tools/build_icon.py')
        Invoke-BuildStep 'Application build' $Python @('-m', 'PyInstaller', '--noconfirm', 'packaging/windows-folder.spec')
        Invoke-BuildStep 'Source and licence staging' $Python @('tools/prepare_installer_payload.py')
        Invoke-BuildStep 'External runtime policy check' $Python @('tools/check_external_runtime.py', 'dist/OTBMaster3D')
        Invoke-BuildStep 'Installer compilation' $Compiler @('packaging/windows-installer.iss')
        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            throw "Compiler completed but the installer was not found: $outputPath"
        }
        Write-Host "[SUCCESS] Installer created: $outputPath" -ForegroundColor Green
    }
} catch {
    $buildExitCode = 1
    [Console]::Error.WriteLine("[ERROR] Installer build failed: " + $_.Exception.Message)
} finally {
    Pop-Location
}
exit $buildExitCode
