#define AppName "OTBMaster3D"
#define AppVersion "1.6.5"

[Setup]
AppId={{5E090E3F-4FD2-4E88-B0BE-81A3C7347D19}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=nork79
AppCopyright=Copyright (C) 2026 nork79
AppPublisherURL=https://github.com/nork79/OTBMaster3D
InfoBeforeFile=..\SOURCE_ACCESS.md
LicenseFile=..\LICENSE
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\OTBMaster3D.exe
SetupIconFile=..\assets\app-icon.ico
OutputDir=..\installer-output
OutputBaseFilename=OTBMaster3D-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.6.5.0

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\OTBMaster3D\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\OTBMaster3D.exe"; WorkingDir: "{app}"; AppUserModelID: "OTBMaster3D.Desktop"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\OTBMaster3D.exe"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "OTBMaster3D.Desktop"

[InstallDelete]
; Remove the ten previous application-local CRT copies only after the central
; prerequisite has passed PrepareToInstall. No wildcard runtime deletion.
Type: files; Name: "{app}\VCRUNTIME140.dll"
Type: files; Name: "{app}\VCRUNTIME140_1.dll"
Type: files; Name: "{app}\PySide6\MSVCP140.dll"
Type: files; Name: "{app}\PySide6\MSVCP140_1.dll"
Type: files; Name: "{app}\PySide6\MSVCP140_2.dll"
Type: files; Name: "{app}\PySide6\VCRUNTIME140.dll"
Type: files; Name: "{app}\PySide6\VCRUNTIME140_1.dll"
Type: files; Name: "{app}\shiboken6\MSVCP140.dll"
Type: files; Name: "{app}\shiboken6\VCRUNTIME140.dll"
Type: files; Name: "{app}\shiboken6\VCRUNTIME140_1.dll"

[Run]
Filename: "{app}\OTBMaster3D.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function RuntimeInView(Root: Integer): Boolean;
var Installed, Major, Minor, Build, Revision: Cardinal;
    Key: String;
begin
  Result := False;
  Key := 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
  if not RegQueryDWordValue(Root, Key, 'Installed', Installed) then exit;
  if Installed <> 1 then exit;
  if not RegQueryDWordValue(Root, Key, 'Major', Major) then exit;
  if not RegQueryDWordValue(Root, Key, 'Minor', Minor) then exit;
  if not RegQueryDWordValue(Root, Key, 'Bld', Build) then exit;
  if not RegQueryDWordValue(Root, Key, 'Rbld', Revision) then exit;
  // Microsoft's compatibility guarantee applies within the v14 runtime family.
  Result := (Major = 14) and ((Minor > 44) or
    ((Minor = 44) and (Build >= 35211)));
end;

function RuntimeInstalled(): Boolean;
begin
  Result := RuntimeInView(HKLM64) or RuntimeInView(HKLM32);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if RuntimeInstalled() then begin
    Log('External Microsoft x64 runtime >= 14.44.35211.0 detected.');
    exit;
  end;
  // The runtime is obtained separately from Microsoft. This installer neither
  // bundles nor downloads it. Apply the same prerequisite check in silent mode.
  Result := 'Microsoft Visual C++ x64 Redistributable 14.44.35211.0 or newer is required.' + #13#10 +
    'Download and install the x64 package directly from Microsoft, then retry Setup:' + #13#10 +
    'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist';
end;
