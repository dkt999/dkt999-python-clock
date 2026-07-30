<#
.SYNOPSIS
    build_win.ps1 - Dong goi ung dung thanh file thuc thi .exe tren Windows bang PowerShell.

.DESCRIPTION
    Script nay tu dong kiem tra moi truong, don dep cac tep build cu va goi PyInstaller
    voi day du cac cau hinh tai nguyen (assets), icon va tuy chon an cua so terminal.

.CACH DUNG:
    1. Dat file nay cung cap voi main.py va thu muc assets.
    2. Chay PowerShell voi quyen phu hop (neu bi chan policy, chay: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process)
    3. Chay lenh: .\build_win.ps1
#>

$ErrorActionPreference = "Stop"

$AppName = "AikaMessenger"
$EntryPoint = "main.py"
$IconPath = "assets\image\icon.ico"
$AssetsDir = "assets"

Write-Host "==> [1/4] Kiem tra thu muc goc du an..." -ForegroundColor Cyan
if (-not (Test-Path $EntryPoint)) {
    Write-Host "Khong tim thay $EntryPoint. Hay chac chan ban chay script nay tu thu muc goc cua project." -ForegroundColor Red
    exit 1
}

Write-Host "==> [2/4] Kiem tra va cap nhat cac thu vien can thiet (PyInstaller, Pillow)..." -ForegroundColor Cyan
python -m pip install --upgrade pip -q
python -m pip install pyinstaller Pillow -q

Write-Host "==> [3/4] Don dep cac tep build cu..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "$AppName.spec") { Remove-Item -Force "$AppName.spec" }

Write-Host "==> [4/4] Dang tien hanh build $AppName.exe bang PyInstaller..." -ForegroundColor Cyan
pyinstaller `
    --name "$AppName" `
    --onefile `
    --windowed `
    --icon="$IconPath" `
    --add-data "$AssetsDir;$AssetsDir" `
    "$EntryPoint"

Write-Host ""
Write-Host "Build hoan tat! File thuc thi nam tai: dist\$AppName.exe" -ForegroundColor Green
Write-Host ""
Write-Host "==> [5/5] Dong goi thanh Setup.exe..." -ForegroundColor Cyan

$ProgramFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
$ISCC = Join-Path $ProgramFilesX86 'Inno Setup 6\ISCC.exe'

if (-not (Test-Path $ISCC)) {
    $ISCC = Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'
}

if (-not (Test-Path $ISCC)) {
    Write-Host ""
    Write-Host "Khong tim thay Inno Setup 6." -ForegroundColor Yellow
    Write-Host "Hay cai Inno Setup roi chay lai."
    exit 1
}

# VERSION: uu tien lay tu bien moi truong (vd truyen tu CI: $env:VERSION = "2026.07.23.1502"),
# neu chua co thi tu sinh theo thoi diem build hien tai - dinh dang giong ben ban .deb (Ubuntu):
# yyyy.MM.dd.HHmm
$Version = if ($env:VERSION) { $env:VERSION } else { Get-Date -Format "yyyy.MM.dd.HHmm" }
$PackageId = "aikamessenger"
$Arch = "amd64"
$OutDir = "installer\windows"

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

& $ISCC "/DBuildVersion=$Version" build_windowsX64.iss

$SetupFileName = "${PackageId}_${Version}_${Arch}.exe"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "BUILD THANH CONG" -ForegroundColor Green
Write-Host ""
Write-Host "Portable EXE :" -NoNewline
Write-Host " dist\$AppName.exe" -ForegroundColor Yellow
Write-Host ""
Write-Host "Setup EXE    :" -NoNewline
Write-Host " $OutDir\$SetupFileName" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Green