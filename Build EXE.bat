@echo off
REM ===================================================================
REM  Builds StillSpin360.exe - one windowed file, no console window - and
REM  assembles the release\ folder: everything someone needs to install and
REM  run StillSpin360, and nothing else.
REM
REM    release\StillSpin360.exe
REM    release\README.md, README.zh-Hant.md
REM    release\installer\       install.bat, install.ps1, versions.json
REM    release\comfy_workflows\ the generation workflow
REM
REM  Give someone the release folder; they run installer\install.bat there,
REM  which downloads the AI engine and models next to the exe.
REM  Run this again whenever the code, the viewer or the translations change.
REM
REM  "Build EXE.bat nopause" skips the Press-any-key at the end.
REM ===================================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Building StillSpin360

set "HOLD=pause"
if /i "%~1"=="nopause" set "HOLD=rem"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :no_python

%PY% -c "import PyInstaller, PySide6, av, PIL, websocket" >nul 2>nul
if errorlevel 1 (
    echo Installing the build tools, this happens once...
    %PY% -m pip install pyinstaller PySide6 av Pillow websocket-client
    if errorlevel 1 goto :pip_failed
)

tasklist /fi "imagename eq StillSpin360.exe" | find /i "StillSpin360.exe" >nul
if not errorlevel 1 (
    echo StillSpin360.exe is running. Close it and run this again.
    %HOLD%
    exit /b 1
)

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Building StillSpin360.exe ...
%PY% -m PyInstaller --noconfirm --clean "StillSpin360.spec"
if errorlevel 1 goto :build_failed

REM --- assemble release\ ------------------------------------------------
REM  Only the release's own files are replaced. Anything else in release\ -
REM  for example an engine installed there for testing - is left alone.
echo Assembling release\ ...
set "REL=release"
if not exist "%REL%\installer" mkdir "%REL%\installer"
if not exist "%REL%\comfy_workflows" mkdir "%REL%\comfy_workflows"
copy /y "dist\StillSpin360.exe" "%REL%\StillSpin360.exe" >nul || goto :build_failed
for %%F in (README.md README.zh-Hant.md) do (
    copy /y "%%F" "%REL%\%%F" >nul || goto :build_failed
)
for %%F in (install.bat install.ps1 versions.json) do (
    copy /y "installer\%%F" "%REL%\installer\%%F" >nul || goto :build_failed
)
del /q "%REL%\comfy_workflows\*.json" 2>nul
copy /y "comfy_workflows\*.json" "%REL%\comfy_workflows\" >nul || goto :build_failed

rmdir /s /q "build"
rmdir /s /q "dist"

echo.
echo Done: %~dp0%REL%
dir /b /s "%REL%\StillSpin360.exe" "%REL%\README*.md" "%REL%\installer\*" "%REL%\comfy_workflows\*"
echo.
echo Share the whole release folder. On the new PC, run installer\install.bat
echo inside it first - that downloads the AI engine and models next to the exe.
echo.
%HOLD%
exit /b 0

:build_failed
echo.
echo Build failed. The messages above say why.
echo Common causes: antivirus holding a file open, or StillSpin360.exe still running.
%HOLD%
exit /b 1

:pip_failed
echo.
echo Could not install the build tools. Try:  %PY% -m pip install pyinstaller PySide6 av Pillow websocket-client
%HOLD%
exit /b 1

:no_python
echo.
echo Python is not installed, so nothing can be built.
echo Get it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
%HOLD%
exit /b 1
