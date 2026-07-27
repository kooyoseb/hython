@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
if not exist release\hython.exe call build-hython.bat
if errorlevel 1 exit /b 1
call build-updater.bat
if errorlevel 1 exit /b 1
call build-studio.bat
if errorlevel 1 exit /b 1
py -3.14 scripts\build_installer.py
exit /b %ERRORLEVEL%
