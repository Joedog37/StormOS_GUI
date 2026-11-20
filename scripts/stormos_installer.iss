; StormOS Installer Script for Inno Setup
; ========================================
; Creates a professional one-click Windows installer for StormOS.
;
; Usage:
;   1. Build the executable: python scripts/build_exe.py
;   2. Run Inno Setup Compiler (ISCC.exe) on this script:
;      ISCC "scripts/stormos_installer.iss"
;
; Output: dist/StormOS-Setup.exe

#define AppName "StormOS"
#define AppVersion "0.1.0"
#define AppPublisher "Thunderhead Pictures"
#define AppURL "https://github.com/thunderhead-pictures/stormos"
#define AppExeName "StormOS.exe"
#define SourcePath "dist\StormOS\"

[Setup]
; Application identification
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Output settings
OutputDir=dist
OutputBaseFilename={#AppName}-Setup
SetupIconFile=assets\stormos.ico
WizardImageFile=assets\stormos_logo.png
WizardSmallImageFile=assets\stormos.ico

; Installation directory
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
ChangesAssociations=yes

; User and privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseS.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "autostart"; Description: "Launch StormOS on system startup"; GroupDescription: "Startup Options:"; Flags: unchecked

[Files]
; Main application directory
Source: "{#SourcePath}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Do not exclude "*.ico" or wizard will lack installation icon

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Ini]
; Auto-start entry
Filename: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\StormOS.lnk"; Section: "Internals"; Key: "Shortcut"; String: ""; Tasks: autostart

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{userappdata}\StormOS"

[Code]
function InitializeSetup(): Boolean;
var
  MinVersion: TWindowsVersion;
begin
  Result := True;
  // Check for Windows 10 or later
  if not GetWindowsVersionEx(MinVersion) then
  begin
    MsgBox('Cannot determine Windows version. Setup will abort.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  if (MinVersion.Major < 10) then
  begin
    if MsgBox('StormOS recommends Windows 10 or later. Do you want to continue anyway?', mbConfirmation, MB_YESNO) = idNo then
    begin
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ErrorCode: Integer;
begin
  Result := '';
  NeedsRestart := False;
  
  // Check if StormOS is currently running and ask user to close it
  if RegKeyExists(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\StormOS_is1') then
  begin
    if MsgBox('A previous version of StormOS may be installed. Setup will upgrade it. Continue?', mbInformation, MB_YESNO) = idNo then
    begin
      Result := 'User cancelled installation.';
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create startup shortcut if user selected auto-start
    if IsTaskSelected('autostart') then
    begin
      CreateShortcut(
        ExpandConstant('{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\StormOS.lnk'),
        ExpandConstant('{app}\{#AppExeName}'),
        '', '', 0, '', '', '', False
      );
    end;
  end;
end;
