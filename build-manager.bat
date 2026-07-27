@echo off
setlocal
chcp 65001 >nul
dotnet publish manager\HythonManager\HythonManager.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o manager\release
if errorlevel 1 exit /b %errorlevel%
echo.
echo [OK] Hython Manager: manager\release\HythonManager.exe
