@echo off
setlocal
cd /d "%~dp0"

call build-studio.bat
if errorlevel 1 exit /b %ERRORLEVEL%

py -3.14 scripts\build_studio_installer.py
exit /b %ERRORLEVEL%
