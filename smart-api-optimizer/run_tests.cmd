@echo off
REM Run tests script for Windows

setlocal enabledelayedexpansion

echo ================================
echo API Optimizer - Test Suite
echo ================================
echo.

REM Run unit tests
echo Running unit tests...
pytest tests\unit\ -v --tb=short
if %ERRORLEVEL% NEQ 0 exit /b 1
echo OK: Unit tests passed
echo.

REM Run integration tests
echo Running integration tests...
pytest tests\integration\ -v --tb=short
if %ERRORLEVEL% NEQ 0 exit /b 1
echo OK: Integration tests passed
echo.

REM Run all tests with coverage
echo Running all tests with coverage...
pytest tests\ -v --cov=app --cov-report=html --cov-report=term
if %ERRORLEVEL% NEQ 0 exit /b 1
echo OK: Coverage report generated
echo.

echo ================================
echo All tests passed!
echo ================================

endlocal
