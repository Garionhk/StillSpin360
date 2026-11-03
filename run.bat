@echo off
rem Launch StillSpin360 with ComfyUI Portable's embedded Python.
set "ROOT=%~dp0"
set "PY=%ROOT%ComfyUI_windows_portable\python_embeded\python.exe"
if not exist "%PY%" (
    echo ComfyUI Portable is not installed. Run installer\install.bat first.
    pause
    exit /b 1
)
rem The embedded Python ignores PYTHONPATH and the script folder, so put the project root on sys.path by hand.
"%PY%" -s -c "import sys; sys.path.insert(0, r'%ROOT:~0,-1%'); from app.main import main; main()"
if errorlevel 1 pause
