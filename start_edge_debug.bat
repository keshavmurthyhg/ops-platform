@echo off
:: =====================================================
::  Start Edge in Remote Debug Mode for PTC Download
:: =====================================================

echo Stopping any existing Edge processes...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo Starting Edge in debug mode...
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="C:\EdgeDebug" ^
    --no-first-run ^
    --no-default-browser-check ^
    --new-window ^
    "https://www.ptc.com/en/support/cstracker/casetracker#"

echo.
echo Edge started on port 9222 with PTC Case Tracker.
echo Log in to PTC if prompted, then click Refresh PTC Cases.
timeout /t 5
