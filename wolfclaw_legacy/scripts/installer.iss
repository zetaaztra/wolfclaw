; scripts/installer.iss
; Professional Windows Installer for Wolfclaw AI Command Center

#define MyAppName "Wolfclaw AI (Legacy Win 7/8)"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Wolfclaw"
#define MyAppExeName "Wolfclaw_Legacy.exe"

[Setup]
AppId={{C8E6D38F-F7D2-4E2F-A047-EA0E95E01A2B}-LEGACY
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Specify the output folder for the setup .exe
OutputDir=..\dist
OutputBaseFilename=Wolfclaw_Legacy_Setup_v1.0
SetupIconFile=..\static\img\wolfclaw-logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Wolfclaw_Legacy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
