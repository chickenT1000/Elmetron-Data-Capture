@echo off
REM Simple test script to diagnose startup issues

echo.
echo ============================================================
echo TEST SCRIPT - Diagnosing startup issues
echo ============================================================
echo.
echo Step 1: Script started successfully
echo.

cd /d "%~dp0"
echo Step 2: Changed to directory: %CD%
echo.

echo Step 3: Checking for Python...
where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher 'py' not found
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 'python' command not found
        echo.
        echo [ERROR] Python is NOT installed or not in PATH
        echo.
    ) else (
        echo Python command found: python
        python --version
    )
) else (
    echo Python launcher found: py
    py -3 --version
)
echo.

echo Step 4: Checking for launcher.py...
if exist "launcher.py" (
    echo launcher.py found in current directory
) else (
    echo [ERROR] launcher.py NOT FOUND
)
echo.

echo Step 5: Checking for virtual environment...
if exist ".venv\Scripts\python.exe" (
    echo Virtual environment exists at .venv
    echo Python version in venv:
    ".venv\Scripts\python.exe" --version
) else (
    echo Virtual environment NOT found at .venv
)
echo.

echo ============================================================
echo Test complete. Analyzing results...
echo ============================================================
echo.
echo If you see this message, the batch script execution works fine.
echo.
echo Next step: Try running start.bat or run.bat
echo.
pause
