# PowerShell Runner for Kolon Global & Haneulche Monitor
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " 코오롱글로벌·하늘채 커뮤니티 통합 모니터링 시스템을 시작합니다..." -ForegroundColor Green
Write-Host " 대시보드 주소: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan

$uvPath = "$HOME\.local\bin\uv.exe"
if (Test-Path $uvPath) {
    & $uvPath run python app.py
} elseif (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    & "$ScriptDir\.venv\Scripts\python.exe" app.py
} else {
    python app.py
}
