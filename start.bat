@echo off
setlocal
cd /d "%~dp0" || exit /b 1

where py >nul 2>nul || (echo Python launcher not found. Install Python 3 and retry.&pause&exit /b 1)

py -3 launcher.py

endlocal
