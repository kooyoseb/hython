@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

call build-manager.bat
if errorlevel 1 exit /b %ERRORLEVEL%

py -3.14 scripts\build_manager_installer.py
exit /b %ERRORLEVEL%
