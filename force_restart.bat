@echo off
echo.
echo ============================================================
echo Force Clean Restart - Elmetron Launcher
echo ============================================================
echo.
echo This will:
echo 1. Kill ALL Python processes
echo 2. Wait for ports to be freed
echo 3. Restart the launcher fresh
echo.
echo IMPORTANT: Close the launcher GUI window first!
echo.
pause

echo.
echo [1/4] Killing all Python processes...
taskkill /F /IM python.exe /T 2>nul
if errorlevel 1 (
    echo No Python processes found to kill
) else (
    echo Python processes killed
)

echo.
echo [2/4] Waiting 3 seconds for cleanup...
timeout /t 3 /nobreak >nul

echo.
echo [3/4] Verifying ports are free...
netstat -ano | findstr ":8050" >nul
if errorlevel 1 (
    echo Port 8050 is free
) else (
    echo WARNING: Port 8050 still in use!
)

netstat -ano | findstr ":8051" >nul
if errorlevel 1 (
    echo Port 8051 is free
) else (
    echo WARNING: Port 8051 still in use!
)

echo.
echo [4/4] Starting launcher...
echo.

cd /d "%~dp0"
start "" run.bat

echo.
echo ============================================================
echo Launcher started! Wait 30 seconds for services to initialize.
echo ============================================================
echo.
pause
