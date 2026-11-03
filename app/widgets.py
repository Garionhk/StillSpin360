"""Small building blocks for the EasyAI-style layout: headings, hints, chips, drop zone."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .i18n import t

IMAGE_FILTER = "*.png *.jpg *.jpeg *.webp *.bmp"


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


def hint(text: str) -> QLabel:
    """The always-visible beginner explanation under a control."""
    lab = label(text, "Hint", wrap=True)
    lab.setTextInteractionFlags(Qt.NoTextInteraction)
    return lab


def heading(text: str, more: str = "", parent: QWidget | None = None) -> QWidget:
    """Uppercase section label, with an optional (?) button that explains it in more depth."""
    row = QWidget()
    row.setObjectName("Row")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lay.addWidget(label(text.upper(), "Heading"))
    if more:
        btn = QPushButton("?")
        btn.setObjectName("Help")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(more)
        btn.clicked.connect(lambda: QMessageBox.information(parent or row, text, more))
        lay.addWidget(btn)
    lay.addStretch(1)
    return row


def step_header(number: int, title: str) -> QWidget:
    row = QWidget()
    row.setObjectName("Row")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 4)
    lay.setSpacing(10)
    lay.addWidget(label(str(number), "StepNumber"))
    lay.addWidget(label(title, "StepTitle"))
    lay.addStretch(1)
    return row


def panel() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Panel")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 14, 16, 16)
    lay.setSpacing(8)
    return frame, lay


class Switch(QCheckBox):
    """A tick box drawn as a sliding switch (the look comes from the theme)."""

    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)


class Chips(QWidget):
    """A row of pick-one buttons, like EasyAI's shape picker."""
    changed = Signal(object)

    def __init__(self, options: list[tuple[object, str]], tooltips: dict | None = None):
        super().__init__()
        self.setObjectName("Row")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[object, QPushButton] = {}
        for value, text in options:
            btn = QPushButton(text)
            btn.setObjectName("Chip")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            if tooltips and value in tooltips:
                btn.setToolTip(tooltips[value])
            btn.clicked.connect(lambda _=False, v=value: self.changed.emit(v))
            self.group.addButton(btn)
            self.buttons[value] = btn
            lay.addWidget(btn)
        lay.addStretch(1)

    def value(self):
        return next((v for v, b in self.buttons.items() if b.isChecked()), None)

    def set_value(self, value) -> None:
        if value in self.buttons:
            self.buttons[value].setChecked(True)


class DropZone(QFrame):
    """Click or drop photos here; shows the selected photo once there is one."""
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(210)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background: transparent;")
        self.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.text = label(t("Drop photos here\nor click to choose"), "Placeholder")
        self.text.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.preview, 1)
        lay.addWidget(self.text)
        self._path = ""

    def mousePressEvent(self, _):
        files, _ = QFileDialog.getOpenFileNames(self, t("Choose photos"), "",
                                                f"{t('Photos')} ({IMAGE_FILTER})")
        if files:
            self.files_dropped.emit(files)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self._set_dragging(True)
            e.acceptProposedAction()

    def dragLeaveEvent(self, _):
        self._set_dragging(False)

    def dropEvent(self, e):
        self._set_dragging(False)
        files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if files:
            self.files_dropped.emit(files)

    def _set_dragging(self, on: bool):
        self.setProperty("dragging", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def show_image(self, path: str) -> None:
        self._path = path
        pix = QPixmap(path) if path else QPixmap()
        if pix.isNull():
            self.preview.clear()
            self.text.setText(t("Drop photos here\nor click to choose"))
            return
        self.text.setText(t("Click or drop to add more photos"))
        self._fit()

    def _fit(self):
        pix = QPixmap(self._path) if self._path else QPixmap()
        if not pix.isNull():
            size = self.preview.size()
            self.preview.setPixmap(pix.scaled(max(size.width(), 40), max(size.height(), 40),
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()
