@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\prepare_winget.ps1" %*
if errorlevel 1 (
  echo [FAILED] Winget manifest preparation failed.
  exit /b 1
)

echo [OK] Winget manifests are ready.
exit /b 0
