@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "REPOSITORY=https://github.com/kooyoseb/hython.git"
set "MESSAGE=%~1"
if not defined MESSAGE set "MESSAGE=Update Hython"

if /I "%~1"=="--help" goto help
if /I "%~1"=="-h" goto help

where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git was not found.
    echo Install Git for Windows from https://git-scm.com/download/win
    exit /b 1
)

echo [1/6] Checking the local Git repository...
if not exist ".git\" (
    git init
    if errorlevel 1 goto failed
)

echo [2/6] Configuring the main branch and remote...
git branch -M main
if errorlevel 1 goto failed

git remote get-url origin >nul 2>nul
if errorlevel 1 (
    git remote add origin "%REPOSITORY%"
) else (
    git remote set-url origin "%REPOSITORY%"
)
if errorlevel 1 goto failed

echo [3/6] Staging changes...
git add -A
if errorlevel 1 goto failed

git diff --cached --quiet
if not errorlevel 1 (
    echo [INFO] There are no new changes to commit.
    goto push
)

echo [4/6] Creating commit: %MESSAGE%
git commit -m "%MESSAGE%"
if errorlevel 1 (
    echo.
    echo If your Git identity is missing, run these commands once:
    echo   git config --global user.name "Your Name"
    echo   git config --global user.email "your-github-email@example.com"
    goto failed
)

:push
echo [5/6] Checking the GitHub connection...
git ls-remote origin >nul
if errorlevel 1 (
    echo [ERROR] Could not connect to the GitHub repository.
    echo Complete the browser or Git Credential Manager sign-in.
    goto failed
)

echo [6/6] Pushing to the GitHub main branch...
git push -u origin main
if errorlevel 1 (
    echo.
    echo If the remote already contains a commit, run:
    echo   git pull --rebase origin main
    echo Then run upload-github.bat again.
    goto failed
)

echo.
echo [DONE] %REPOSITORY%
exit /b 0

:help
echo Usage:
echo   upload-github.bat
echo   upload-github.bat "Commit message"
echo.
echo Target:
echo   %REPOSITORY%
exit /b 0

:failed
echo.
echo [FAILED] GitHub upload did not complete.
exit /b 1
