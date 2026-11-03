"""StillSpin360 - entry point for StillSpin360.exe (and `python StillSpin360.py`).

The exe is built windowed, so there is no console: a startup failure would otherwise
just mean the window never appears. _report_fatal puts it in a dialog instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _report_fatal(error: BaseException) -> None:
    import traceback

    details = "".join(traceback.format_exception(error))
    message = ("StillSpin360 could not start.\n\n"
               f"{type(error).__name__}: {error}\n\n"
               "If this keeps happening, start run.bat to see the full message.")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        box = QMessageBox(QMessageBox.Critical, "StillSpin360", message)
        box.setDetailedText(details)
        box.exec()
    except Exception:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message + "\n\n" + details[-1500:], "StillSpin360", 0x10)


if __name__ == "__main__":
    try:
        from app.main import main

        main()
    except SystemExit:
        raise
    except BaseException as e:
        _report_fatal(e)
        sys.exit(1)
