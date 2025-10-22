@echo off
echo.
echo ============================================================
echo Elmetron Data Capture - Launcher Wrapper
echo ============================================================
echo This wrapper ensures the window stays open
echo.

cd /d "%~dp0"
if errorlevel 1 (
    echo ERROR: Failed to change to script directory
    pause
    exit /b 1
)

echo Running from: %CD%
echo.

REM Run the actual startup script
call start.bat
set "RESULT=%ERRORLEVEL%"

echo.
if "%RESULT%"=="0" (
    echo ============================================================
    echo SUCCESS: Application started successfully
    echo ============================================================
) else (
    echo ============================================================
    echo ERROR: Startup failed with code: %RESULT%
    echo ============================================================
    echo Check the messages above for details
)

echo.
echo Press any key to close...
pause
exit /b %RESULT%
