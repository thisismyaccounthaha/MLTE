@echo off
title SEARCH ALL REFERENCE
color 0B

:: Set the directory path
set "SCRIPT_DIR=%~dp0"
set "LOCK_FILE=%temp%\crib_instructions.lock"

:: Try to delete the lock file. If it fails, the file is in use by another window.
if exist "%LOCK_FILE%" (
    del "%LOCK_FILE%" >nul 2>nul
)

:: Check if the delete failed (meaning the file is locked/open)
if exist "%LOCK_FILE%" (
    echo [INFO] Instructions are already open in another window.
    timeout /t 2 > nul
    exit
)

:: Create the lock file by writing the current time to it
echo %time% > "%LOCK_FILE%"


echo.

if exist "%SCRIPT_DIR%searchallinstructions.txt" (
    type "%SCRIPT_DIR%searchallinstructions.txt"
) else (
    echo [ERROR] searchallinstructions.txt not found.
    echo Path: "%SCRIPT_DIR%searchallinstructions.txt"
    pause
    exit
)

echo.


pause > nul

:: Clean up the lock when the window is closed
del "%LOCK_FILE%" >nul 2>nul
exit