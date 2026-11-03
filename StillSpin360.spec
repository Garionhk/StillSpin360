# -*- mode: python ; coding: utf-8 -*-
"""StillSpin360.exe - one windowed file, no console.

Built by "Build EXE.bat". The exe must live in the project folder: it starts the AI engine from
ComfyUI_windows_portable next to it and keeps prefs.json and outputs\ there too.

This machine's Python also carries torch, numpy, OpenCV and friends. PyInstaller follows any
importable module, so the big ones are excluded by name. None of them is imported by the app
(checked by loading the window, encoding a video frame and writing a GIF, then reading
sys.modules) - if that ever changes, remove the name here, or the windowed exe fails silently.
"""
import json
import sys

sys.path.insert(0, SPECPATH)
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
)

VERSION = json.load(open(SPECPATH + "/installer/versions.json", encoding="utf-8"))["app_version"]
NUMBERS = tuple(int(p) for p in VERSION.split(".")[:3]) + (0,)

EXCLUDES = [
    "numpy", "torch", "torchvision", "torchaudio", "transformers", "cv2", "scipy", "pandas",
    "matplotlib", "tkinter", "sklearn", "tensorflow", "yaml", "cryptography", "IPython", "jedi",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtPdf",
    "PySide6.QtPdfWidgets", "PySide6.Qt3DCore", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.QtOpenGLWidgets",
    "PIL.AvifImagePlugin",
]
# PySide6's hook copies these DLLs whether or not the Python module is imported.
UNUSED_QT_LIBRARIES = ("qt6quick", "qt6qml", "qt6pdf", "qt6webengine", "qt63d")

a = Analysis(
    ["StillSpin360.py"],
    pathex=[SPECPATH],
    binaries=[],
    datas=[
        ("app/templates", "app/templates"),
        ("app/lang", "app/lang"),
        ("app/assets/icons", "app/assets/icons"),
    ],
    hiddenimports=["PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
before = len(a.binaries)
a.binaries = [b for b in a.binaries
              if not str(b[0]).replace("\\", "/").rsplit("/", 1)[-1].lower().startswith(UNUSED_QT_LIBRARIES)]
print(f"[StillSpin360.spec] left out {before - len(a.binaries)} unused Qt libraries")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="StillSpin360",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=["app/assets/icons/stillspin360.ico"],
    version=VSVersionInfo(
        ffi=FixedFileInfo(filevers=NUMBERS, prodvers=NUMBERS, mask=0x3F, flags=0x0, OS=0x40004,
                          fileType=0x1, subtype=0x0, date=(0, 0)),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "Garion Lab"),
                StringStruct("FileDescription", "StillSpin360 - photo to 360 spin"),
                StringStruct("FileVersion", VERSION),
                StringStruct("InternalName", "StillSpin360"),
                StringStruct("OriginalFilename", "StillSpin360.exe"),
                StringStruct("ProductName", "StillSpin360"),
                StringStruct("ProductVersion", VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    ),
)
