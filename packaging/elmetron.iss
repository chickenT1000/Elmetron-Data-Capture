#define AppVersion "1.0.0-beta.1"
[Setup]
AppId={{9E32288A-D9B1-40B5-939C-F4A8D7706480}
AppName=Elmetron Data Capture
AppVersion={#AppVersion}
AppPublisher=Elmetron Data Capture contributors
AppPublisherURL=https://github.com/chickenT1000/Elmetron-Data-Capture
DefaultDirName={localappdata}\Programs\Elmetron
DefaultGroupName=Elmetron
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installers
OutputBaseFilename=Elmetron-{#AppVersion}-windows-x64-setup
LicenseFile=..\LICENSE
InfoAfterFile=installer-notes.txt
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=Local\ElmetronDataCapture
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Files]
Source: "..\dist\Elmetron\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\Elmetron"; Filename: "{app}\Elmetron.exe"
Name: "{group}\Configuration and customization guide"; Filename: "{app}\_internal\docs\CONFIGURATION.md"
Name: "{autodesktop}\Elmetron"; Filename: "{app}\Elmetron.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Elmetron.exe"; Description: "Open Elmetron"; Flags: nowait postinstall skipifsilent

; No data-home files are installed or removed here. Updates preserve user config/data.
