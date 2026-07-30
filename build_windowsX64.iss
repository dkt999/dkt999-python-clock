#define AppName "AikaMessenger"
#define AppVersion "1.0.0"
#define AppPublisher "Aika"
#define AppExeName "AikaMessenger.exe"

; Dùng cho tên file .exe đầu ra: aikamessenger_<version>_amd64.exe
; PackageId/Arch cố định, BuildVersion truyền từ dòng lệnh (ISCC /DBuildVersion=...) khi build từ
; build_windowsX64.ps1 - nếu build tay không truyền /D thì dùng giá trị mặc định bên dưới.
#define PackageId "aikamessenger"
#define Arch "amd64"
#ifndef BuildVersion
  #define BuildVersion "1.0.0"
#endif

[Setup]
AppId={{AikaMessenger}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; lowest = cài cho riêng user hiện tại, KHÔNG hiện popup UAC xin quyền admin - {autopf}/{group}/
; {autodesktop} phía trên tự động trỏ sang thư mục riêng của user (%LOCALAPPDATA%\Programs...)
; khi chạy ở chế độ này, không cần sửa gì thêm ở [Files]/[Icons].
PrivilegesRequired=lowest
OutputDir=installer\windows
OutputBaseFilename={#PackageId}_{#BuildVersion}_{#Arch}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

SetupIconFile=assets\image\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent