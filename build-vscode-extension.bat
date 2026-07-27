@echo off
setlocal
cd /d "%~dp0vscode-extension"

call npm install
if errorlevel 1 exit /b %ERRORLEVEL%

call npm run check
if errorlevel 1 exit /b %ERRORLEVEL%

call npm run package
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [OK] VS Code extension: vscode-extension\hython-development-1.0.1.vsix
exit /b 0
