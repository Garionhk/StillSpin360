@echo off
rem Double-click entry point for the StillSpin360 installer.
rem Extra arguments are passed through, e.g.  install.bat -SkipOptional
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
