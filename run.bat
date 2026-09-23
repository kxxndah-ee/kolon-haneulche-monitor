@echo off
chcp 65001 > nul
echo =====================================================================
echo  코오롱글로벌·하늘채 커뮤니티 통합 모니터링 시스템을 시작합니다...
echo =====================================================================

set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    "%USERPROFILE%\.local\bin\uv.exe" run python app.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)

pause
