@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

if not exist "release\Hython-2.0.5-x64.msi" call build-installer.bat
if errorlevel 1 exit /b 1

py -3.14 scripts\build_setup.py
exit /b %ERRORLEVEL%
