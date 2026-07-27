@echo off
setlocal
cd /d "%~dp0"

dotnet publish studio\HythonStudio\HythonStudio.csproj ^
  -c Release ^
  -r win-x64 ^
  --self-contained true ^
  -p:PublishSingleFile=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true ^
  -o studio\release

if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [OK] Hython Studio: studio\release\HythonStudio.exe
exit /b 0
