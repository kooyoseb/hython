@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

call build-manager-installer.bat
if errorlevel 1 exit /b %ERRORLEVEL%

dotnet publish manager\HythonManagerSetup\HythonManagerSetup.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o manager\setup-release
if errorlevel 1 exit /b %ERRORLEVEL%

copy /y manager\setup-release\HythonManagerSetup.exe release\HythonManager-1.1.0-setup.exe >nul
echo [OK] Hython Manager Setup: release\HythonManager-1.1.0-setup.exe
