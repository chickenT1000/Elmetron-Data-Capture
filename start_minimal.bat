@echo off
echo MINIMAL TEST - Line 1
pause
echo MINIMAL TEST - Line 2
pause
echo MINIMAL TEST - Line 3
cd /d "%~dp0"
echo Changed directory to: %CD%
pause
echo About to run setlocal
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
echo Setlocal completed
pause
echo Script ending normally
pause
