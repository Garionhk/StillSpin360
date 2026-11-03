"""One dark theme for the whole app, matching EasyAI.

Near-black surfaces, a single warm orange accent, small uppercase letter-spaced
section labels, and a monospace face reserved for numbers the user reads back
(pixel sizes, frame counts, the engine address) so they don't shift as values change.
"""

from pathlib import Path

ACCENT = "#ff6b1a"
ACCENT_2 = "#ffa04a"
ACCENT_DOWN = "#e05a12"
ACCENT_INK = "#120800"

BG = "#070709"
SURFACE = "#0e0e11"
SURFACE_2 = "#15151a"
SURFACE_3 = "#1c1c22"
INPUT_BG = "#0b0b0e"

LINE = "#26262d"
LINE_2 = "#33333c"

TEXT = "#f3f3f5"
MUTED = "#8b8b96"
DIM = "#5f5f6a"
FAINT = "#4a4a55"

OK = "#4ac97e"
WARN = "#ffa04a"
BAD = "#ff5f56"

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

UI_FONT = "Segoe UI"
MONO_FONT = "Consolas"


def load_fonts() -> None:
    """Use Manrope / JetBrains Mono if dropped into app/assets/fonts, else Windows faces."""
    global UI_FONT, MONO_FONT
    from PySide6.QtGui import QFontDatabase

    if FONT_DIR.is_dir():
        for path in sorted(FONT_DIR.glob("*.[to]tf")):
            QFontDatabase.addApplicationFont(str(path))
    families = set(QFontDatabase.families())

    def first(*names):
        return next((n for n in names if n in families), names[-1])

    UI_FONT = first("Manrope", "Inter", "Segoe UI Variable Text", "Segoe UI", "Arial")
    MONO_FONT = first("JetBrains Mono", "Cascadia Mono", "Consolas", "Courier New")


def stylesheet() -> str:
    # Microsoft JhengHei is listed second so Traditional Chinese text gets a proper face.
    return f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "{UI_FONT}", "Microsoft JhengHei UI", "Microsoft JhengHei";
    font-size: 13px;
}}
QMainWindow, QDialog {{ background: {BG}; }}

QFrame#Panel {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 12px;
}}
QFrame#Panel QLabel, QWidget#Row, QFrame#Panel QCheckBox {{ background: transparent; }}
QLabel#Heading {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: {MUTED};
}}
QLabel#StepTitle {{ font-size: 15px; font-weight: 700; color: {TEXT}; }}
QLabel#StepNumber, QFrame#Panel QLabel#StepNumber {{
    font-family: "{MONO_FONT}";
    font-size: 12px;
    font-weight: 700;
    color: {ACCENT_INK};
    background: {ACCENT};
    border-radius: 11px;
    min-width: 22px; max-width: 22px;
    min-height: 22px; max-height: 22px;
    qproperty-alignment: AlignCenter;
}}
QLabel#Hint {{ color: {DIM}; font-size: 12px; }}
QLabel#Mono {{ font-family: "{MONO_FONT}"; font-size: 11px; color: {MUTED}; }}
QLabel#MonoAccent {{ font-family: "{MONO_FONT}"; font-size: 12px; color: {ACCENT}; font-weight: 600; }}
QLabel#Warning {{ color: {WARN}; font-size: 12px; }}
QLabel#Placeholder {{ color: {MUTED}; font-size: 13px; }}

QLabel#EnginePill {{
    font-family: "{MONO_FONT}";
    font-size: 11px;
    color: {MUTED};
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 11px;
    padding: 3px 11px;
}}
QLabel#EnginePill[state="down"] {{ color: {BAD}; border-color: {BAD}; }}
QLabel#EnginePill[state="starting"] {{ color: {WARN}; border-color: {WARN}; }}
QLabel#EnginePill[state="ready"] {{ color: {OK}; border-color: #23523a; }}

QFrame#DropZone {{
    background: {INPUT_BG};
    border: 1px dashed {LINE_2};
    border-radius: 12px;
}}
QFrame#DropZone:hover {{ border-color: {ACCENT}; }}
QFrame#DropZone[dragging="true"] {{ border: 1px solid {ACCENT}; background: #1a1013; }}

QPlainTextEdit {{
    background: {INPUT_BG};
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 10px 12px;
    font-family: "{MONO_FONT}";
    font-size: 11px;
    color: {MUTED};
}}

QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {SURFACE_2};
    border: 1px solid {LINE};
    border-radius: 9px;
    padding: 7px 10px;
    min-height: 20px;
    color: {TEXT};
    font-family: "{MONO_FONT}";
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {LINE_2}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {LINE};
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_INK};
}}

QPushButton {{
    height: 34px;
    padding: 0 14px;
    border-radius: 9px;
    border: 1px solid {LINE};
    background: {SURFACE_2};
    color: {MUTED};
    font-size: 12.5px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {SURFACE_3}; color: {TEXT}; border-color: {LINE_2}; }}
QPushButton:pressed {{ background: {SURFACE}; }}
QPushButton:disabled {{ color: #3f3f49; border-color: #1e1e24; background: {SURFACE}; }}

QPushButton#Primary {{
    background: {ACCENT};
    border: none;
    color: {ACCENT_INK};
    font-size: 15px;
    font-weight: 800;
    height: 52px;
    border-radius: 12px;
}}
QPushButton#Primary:hover {{ background: {ACCENT_2}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_DOWN}; }}
QPushButton#Primary:disabled {{ background: {SURFACE_3}; color: #55555f; }}

QPushButton#Danger {{ border-color: {BAD}; color: {BAD}; }}
QPushButton#Danger:hover {{ background: #2a1614; color: {BAD}; }}
QPushButton#Danger:disabled {{ color: #3f3f49; border-color: #1e1e24; background: {SURFACE}; }}

QPushButton#Chip {{
    height: 30px;
    padding: 0 12px;
    border-radius: 8px;
    border: 1px solid {LINE};
    background: {SURFACE_2};
    color: {MUTED};
    font-family: "{MONO_FONT}", "Microsoft JhengHei UI";
    font-size: 11.5px;
    font-weight: 600;
}}
QPushButton#Chip:hover {{ border-color: {LINE_2}; color: {TEXT}; }}
QPushButton#Chip:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: {ACCENT_INK}; }}

QPushButton#Help {{
    height: 18px; width: 18px; min-width: 18px; max-width: 18px;
    padding: 0; border-radius: 9px;
    font-size: 11px; font-weight: 700;
    color: {DIM}; background: transparent; border: 1px solid {LINE_2};
}}
QPushButton#Help:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 10px;
    margin-bottom: 6px;
    padding: 6px;
    color: {TEXT};
}}
QListWidget::item:hover {{ border-color: {LINE_2}; }}
QListWidget::item:selected {{ border: 1px solid {ACCENT}; background: #1a1013; color: {TEXT}; }}

QProgressBar {{
    background: {SURFACE_3};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #2a2a32; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3b3b46; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #2a2a32; border-radius: 5px; min-width: 30px; }}

QMenuBar {{ background: {BG}; color: {MUTED}; border-bottom: 1px solid {LINE}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ color: {TEXT}; }}
QMenu {{ background: {SURFACE_2}; border: 1px solid {LINE}; padding: 6px; }}
QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {SURFACE_3}; color: {TEXT}; }}
QMenu::item:checked {{ color: {ACCENT}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 5px 8px; }}

QStatusBar {{ background: {BG}; color: {DIM}; border-top: 1px solid {LINE}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ font-size: 11px; color: {DIM}; }}

QToolTip {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {LINE};
    padding: 7px 9px;
    border-radius: 8px;
}}

QCheckBox {{ color: {MUTED}; font-size: 13px; spacing: 10px; }}
QCheckBox:hover {{ color: {TEXT}; }}
QCheckBox::indicator {{
    width: 34px; height: 19px; border-radius: 10px;
    border: 1px solid {LINE_2}; background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QSplitter::handle {{ background: transparent; width: 10px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QMessageBox QLabel {{ font-size: 13px; }}
"""


def apply(app) -> None:
    load_fonts()
    app.setStyleSheet(stylesheet())
