@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [Hython] Python launcher ^(py.exe^) was not found.
  exit /b 1
)

py -3.14 -c "import nuitka" >nul 2>nul
if errorlevel 1 (
  echo [Hython] Installing C build dependencies...
  py -3.14 -m pip install -e ".[native]"
  if errorlevel 1 exit /b 1
)

echo [Hython] Running full regression tests...
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
py -3.14 -m unittest discover -s tests -q
if errorlevel 1 exit /b 1

echo [Hython] Compiling standalone hython.exe through C...
py -3.14 scripts\build_hython_native.py %*
if errorlevel 1 exit /b 1

echo [Hython] Build complete: release\hython.exe
exit /b 0
