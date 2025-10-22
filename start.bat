@echo off
REM ============================================================
REM Elmetron Launch Monitor - Startup Script (v2.0 Fixed)
REM ============================================================

echo.
echo ============================================================
echo SCRIPT STARTING - If you see this, the batch file is working
echo ============================================================
echo.

REM Change to script directory
cd /d "%~dp0"
if errorlevel 1 (
    echo ERROR: Failed to change directory
    pause
    exit /b 1
)

echo Current directory: %CD%
echo.

REM Now enable delayed expansion AFTER initial checks
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

echo [INFO] Checking Node.js and npm...
set "NODE_AVAILABLE=0"
where node >nul 2>nul
if errorlevel 1 (
    echo [WARN] Node.js not found - UI will not be available
) else (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo [WARN] npm not found - UI will not be available
    ) else (
        set "NODE_AVAILABLE=1"
        for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo [OK] Node.js %%v found
        for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo [OK] npm %%v found
    )
)
echo.

REM Find Python
echo [INFO] Checking for Python...
set "PYTHON_CMD="
where py >nul 2>nul
if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 (
        echo.
        echo ====================================================
        echo ERROR: Python 3 not found in PATH!
        echo ====================================================
        echo Please install Python 3.9+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation
        echo.
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python"
    )
) else (
    set "PYTHON_CMD=py -3"
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PYTHON_VERSION=%%v"
if defined PYTHON_VERSION (
    echo [OK] Python %PYTHON_VERSION% found
) else (
    echo [OK] Python found
)
echo.

REM Create virtual environment
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

if not exist "%VENV_PY%" (
    echo [INFO] Creating virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment exists
)

REM Upgrade pip
echo [INFO] Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip >"captures\setup_pip.log" 2>&1
if errorlevel 1 (
    echo [WARN] pip upgrade failed, continuing anyway
) else (
    echo [OK] pip ready
)
echo.

REM Install Python dependencies
if exist "requirements.txt" (
    echo [INFO] Installing Python dependencies...
    "%VENV_PIP%" install -r requirements.txt >"captures\setup_python.log" 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to install Python packages
        echo See captures\setup_python.log for details
        pause
        exit /b 1
    )
    echo [OK] Python packages installed
) else (
    echo [WARN] No requirements.txt found
)
echo.

REM Check FTDI drivers
echo [INFO] Checking FTDI drivers...
if exist "%SystemRoot%\System32\ftd2xx.dll" (
    echo [OK] FTDI drivers found
) else (
    if exist "ftd2xx.dll" (
        echo [OK] FTDI drivers found in app directory
    ) else (
        echo [WARN] FTDI drivers not found - hardware capture unavailable
    )
)
echo.

REM Install UI dependencies if Node.js available
if exist "ui\package.json" (
    if "%NODE_AVAILABLE%"=="1" (
        if not exist "ui\node_modules" (
            echo [INFO] Installing UI dependencies...
            pushd "ui"
            npm install >"..captures\setup_ui.log" 2>&1
            set "NPM_RESULT=!ERRORLEVEL!"
            popd
            if "!NPM_RESULT!"=="0" (
                echo [OK] UI packages installed
            ) else (
                echo [WARN] UI installation failed
                set "NODE_AVAILABLE=0"
            )
        ) else (
            echo [INFO] UI node_modules already exists
        )
    ) else (
        echo [WARN] Node.js not available - UI will not start
    )
)
echo.

REM Start launcher
echo ============================================================
echo Starting Elmetron Launch Monitor...
echo ============================================================
echo.

if exist "launcher.py" (
    echo Found launcher.py, starting...
    "%VENV_PY%" launcher.py
    set "EXITCODE=!ERRORLEVEL!"
) else (
    echo ERROR: launcher.py not found in current directory!
    set "EXITCODE=1"
)
echo.

if "%EXITCODE%"=="0" (
    echo [OK] Launcher exited cleanly
) else (
    echo [ERROR] Launcher exited with code %EXITCODE%
)

echo.
echo ============================================================
echo Script complete. Press any key to close...
echo ============================================================
pause
endlocal
exit /b %EXITCODE%
