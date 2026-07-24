@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

py -3.14 -c "import build,twine" >nul 2>nul
if errorlevel 1 py -3.14 -m pip install -e ".[publish]"
if errorlevel 1 exit /b 1

if /I "%~1"=="testpypi" goto upload_test
if /I "%~1"=="pypi" goto upload_real
py -3.14 scripts\build_pypi.py
exit /b %ERRORLEVEL%

:upload_test
py -3.14 scripts\build_pypi.py --upload --repository testpypi
exit /b %ERRORLEVEL%

:upload_real
py -3.14 scripts\build_pypi.py --upload --repository pypi --allow-prerelease
exit /b %ERRORLEVEL%
