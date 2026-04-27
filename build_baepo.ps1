# Dallae PC Agent 배포판 빌드 스크립트
# 실행: .\build_baepo.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "== Dallae Baepo PC Agent Build ==" -ForegroundColor Cyan

# 가상환경 확인
if (-not (Test-Path ".venv")) {
    Write-Host "가상환경 생성 중..." -ForegroundColor Gray
    python -m venv .venv
}

$pip = ".venv\Scripts\pip.exe"
$pyinstaller = ".venv\Scripts\pyinstaller.exe"
$python = ".venv\Scripts\python.exe"

Write-Host "의존성 설치..." -ForegroundColor Gray
& $pip install -r requirements.txt -q

Write-Host "PyInstaller 빌드..." -ForegroundColor Gray
& $pyinstaller baepo.spec --clean --noconfirm

$exe = Join-Path $root "dist\DallaePC.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "완료: dist\DallaePC.exe ($size MB)" -ForegroundColor Green
} else {
    Write-Host "빌드 실패: dist\DallaePC.exe 없음" -ForegroundColor Red
    exit 1
}

# 신규 설치용 ZIP 생성 (SmartScreen 우회)
$zipPath = Join-Path $root "dist\DallaePC.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $exe -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "완료: dist\DallaePC.zip" -ForegroundColor Green

# releases 폴더 복사
$releasesDir = Join-Path (Split-Path -Parent $root) "dallae-baepo-releases"
if (Test-Path $releasesDir) {
    Copy-Item $exe        (Join-Path $releasesDir "DallaePC.exe")  -Force
    Copy-Item $zipPath    (Join-Path $releasesDir "DallaePC.zip")  -Force
    Write-Host "복사 완료: dallae-baepo-releases\DallaePC.exe / .zip" -ForegroundColor Green
}
