#define AppName "OTBMaster3D"
#define AppVersion "1.4.0-beta.1"

[Setup]
AppId={{5E090E3F-4FD2-4E88-B0BE-81A3C7347D19}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=OTBMaster3D
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
VersionInfoVersion=1.4.0.1

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\OTBMaster3D\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\OTBMaster3D.exe"; WorkingDir: "{app}"; AppUserModelID: "OTBMaster3D.Desktop"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\OTBMaster3D.exe"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "OTBMaster3D.Desktop"

[Run]
Filename: "{app}\OTBMaster3D.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
