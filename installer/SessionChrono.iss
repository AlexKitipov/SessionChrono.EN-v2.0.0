; Inno Setup script for packaging the PyInstaller one-folder SessionChrono build.
; Build prerequisite from repository root:
;   python -m PyInstaller --clean --noconfirm sessionchrono.spec
; Then build this installer on Windows with:
;   ISCC.exe installer\SessionChrono.iss

#define MyAppName "SessionChrono"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "SessionChrono contributors"
#define MyAppExeName "SessionChrono.exe"
#define MyDistDir "..\dist\SessionChrono"
#define MyOutputDir "..\dist\installer"
#define MyOutputBaseFilename "SessionChrono-2.0.0-Setup"

#ifnexist MyDistDir + "\" + MyAppExeName
  #error "PyInstaller output was not found. Build dist\SessionChrono\SessionChrono.exe before running ISCC."
#endif

[Setup]
AppId={{5E37AEE0-6303-4D9B-9B0C-9AE8D9178EF1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}
SetupIconFile=..\SessionChrono.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

; Uninstall removes files and shortcuts installed by this script through Inno
; Setup's default uninstall registry. It intentionally does not delete the
; per-user data root (%APPDATA%\SessionChrono\), where ChronoNotes, settings,
; metadata, exports, and logs may contain user-created clipboard history.
