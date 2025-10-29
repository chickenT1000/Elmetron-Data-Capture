@echo off
echo.
echo ============================================================
echo CX-505 Device Diagnostic Tool
echo ============================================================
echo.
echo This tool will check if your CX-505 device is properly
echo connected and accessible.
echo.
echo Make sure to CLOSE the launcher before running this tool!
echo.
pause

cd /d "%~dp0"
.venv\Scripts\python.exe diagnose_cx505.py

pause
