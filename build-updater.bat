@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
py -3.14 scripts\build_updater.py
exit /b %ERRORLEVEL%
