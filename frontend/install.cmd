@echo off
REM Frontend Dependency Installation Script for Windows

echo ================================
echo API Optimizer - Frontend Setup
echo ================================
echo.

REM Check Node.js installation
echo Checking Node.js...
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo OK: Node.js %NODE_VERSION% found
echo.

REM Check npm installation
echo Checking npm...
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm is not installed
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm -v') do set NPM_VERSION=%%i
echo OK: npm %NPM_VERSION% found
echo.

REM Navigate to script directory
echo Navigating to frontend directory...
cd /d "%~dp0"
echo OK: Current directory: %cd%
echo.

REM Install dependencies
echo Installing dependencies...
echo This may take a few minutes...
echo.

call npm install

if %ERRORLEVEL% EQU 0 (
    echo.
    echo OK: Dependencies installed successfully!
    echo.
    echo ================================
    echo Setup Complete!
    echo ================================
    echo.
    echo To start the development server, run:
    echo   npm run dev
    echo.
    echo Frontend will be available at:
    echo   http://localhost:3000
    echo.
    echo Make sure the backend is running at:
    echo   http://localhost:8000
    echo.
) else (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please check the error message above
    pause
    exit /b 1
)

pause
