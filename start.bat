@echo off

cd /d "%~dp0"

if exist "Elmetron.exe" (start "" "Elmetron.exe") else (python launcher.py)
