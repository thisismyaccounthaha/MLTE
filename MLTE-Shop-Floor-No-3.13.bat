@echo off


:: 3. Run Python using the full path to the script on that drive
python "Z:\Shared-Scripts\MLTE.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [LAUNCH ERROR] Python failed. Current Dir: %cd%
    pause
)

