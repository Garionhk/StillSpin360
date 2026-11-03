"""StillSpin360 GUI: photo in, frozen-time 360° spin out. Laid out for beginners in three steps."""

import os
import random
import re
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QDialog, QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QStackedLayout, QStatusBar, QVBoxLayout, QWidget,
)

from . import html_export, i18n, postprocess, theme
from .comfy_client import ComfyClient, ComfyError
from .comfy_server import ComfyServer
from .i18n import N, t
from .settings import (
    APP_ICON, FPS, FRAME_CHOICES, OUTPUT_DIR, PRESETS, SIZE_CHOICES, Prefs, load_engine, load_versions,
    snap_frames, version_tuple,
)
from .widgets import Chips, DropZone, Switch, heading, hint, label, panel, step_header
from .workflow import build_orbit

# What each workflow node means, in words a beginner understands.
STAGES = {
    "Diffusion Model": N("Loading the AI model…"),
    "Orbit LoRA": N("Loading the 360° spin add-on…"),
    "Turbo LoRA": N("Loading the Turbo add-on…"),
    "Text Encoder": N("Loading the photo reader…"),
    "Video VAE": N("Loading the video decoder…"),
    "Input Image": N("Reading your photo…"),
    "Orbit Conditioning": N("Studying your photo…"),
    "Sample": N("Creating the spin… (this is the longest step)"),
    "Decode": N("Turning it into frames…"),
    "Save Frames": N("Saving the frames…"),
}

PRESET_LABELS = {"quality": N("Best quality"), "balanced": N("Balanced"), "fast": N("Fast")}
PRESET_HINTS = {
    "quality": N("Sharpest result at the size the spin add-on was trained on. "
                 "Needs a 16 GB graphics card and takes the longest."),
    "balanced": N("A little smaller and quicker than Best quality. Good for trying ideas on a 16 GB card."),
    "fast": N("Smallest and quickest, using Turbo mode. The best choice for 12 GB graphics cards."),
}


class Job:
    def __init__(self, image: Path, size: int, frames: int, steps: int, seed: int, lora: float, turbo: bool):
        self.image, self.size, self.frames, self.steps = image, size, frames, steps
        self.seed, self.lora, self.turbo = seed, lora, turbo


class Worker(QObject):
    log = Signal(str)
    stage = Signal(str)                 # workflow node title
    job_started = Signal(int, int, str)
    progress = Signal(int, int)
    job_done = Signal(str)
    failed = Signal(str, str)           # beginner message (English, translated by the GUI), detail
    finished = Signal()

    def __init__(self, base_url: str, jobs: list[Job], models: dict):
        super().__init__()
        self.client = ComfyClient(base_url)
        self.jobs = jobs
        self.models = models
        self.cancelled = False

    def run(self):
        try:
            for i, job in enumerate(self.jobs, 1):
                if self.cancelled:
                    break
                self.job_started.emit(i, len(self.jobs), job.image.name)
                self._run_job(job)
        except ComfyError as e:
            detail = str(e)
            self.log.emit(f"ComfyUI error: {detail}")
            if detail in ("cancelled", "interrupted"):
                return
            if "out of memory" in detail.lower() or "outofmemory" in detail.lower():
                self.failed.emit(N("Your graphics card ran out of memory. Choose Fast, or a lower Detail, "
                                   "close other programs that use the graphics card, and try again."), detail)
            elif f"'{self.models.get('turbo_lora')}' not in" in detail:
                self.failed.emit(N("The Turbo add-on is not installed. Turn off Turbo mode, or run the "
                                   "installer again without -SkipOptional."), detail)
            elif "value not in list" in detail.lower():
                self.failed.emit(N("A model file the spin needs was not found in the AI engine. "
                                   "Run installer\\install.bat again to fetch it."), detail)
            else:
                self.failed.emit(N("The AI engine stopped with an error. The details are in AI engine → "
                                   "Show engine log."), detail)
        except Exception:
            detail = traceback.format_exc()
            self.log.emit(detail)
            self.failed.emit(N("Something went wrong. The details are in AI engine → Show engine log."), detail)
        finally:
            self.finished.emit()

    def _run_job(self, job: Job):
        name = f"{job.image.stem}_{time.strftime('%Y%m%d_%H%M%S')}"
        job_dir = OUTPUT_DIR / name
        canvas = postprocess.canvas_for(*postprocess.open_photo(job.image).size, job.size)
        if canvas.clamped:
            self.log.emit(f"{job.image.name}: aspect ratio is outside the model's 0.4-2.5 range, "
                          f"center-cropping to {canvas.ratio:.2f}")
        prepared = postprocess.prepare_input(job.image, canvas, job_dir / "input.png")
        uploaded = self.client.upload_image(prepared, f"stillspin360_{name}.png")
        graph = build_orbit(uploaded, canvas.gen_w, canvas.gen_h, job.frames, job.steps, job.seed, job.lora,
                            job.turbo, prefix=f"StillSpin360/{name}", models=self.models)
        self.log.emit(f"Queued {name}: {canvas.gen_w}x{canvas.gen_h} -> {canvas.out_w}x{canvas.out_h}, "
                      f"{job.frames} frames, {job.steps} steps, seed {job.seed}{', turbo' if job.turbo else ''}")
        started = time.time()
        history = self.client.run(graph, on_progress=self.progress.emit, on_status=self.stage.emit,
                                  should_cancel=lambda: self.cancelled)
        frames = self.client.download_images(history, job_dir / "frames")
        if not frames:
            raise ComfyError("the workflow finished without returning any frames")
        postprocess.restore_ratio(frames, canvas)
        postprocess.write_mp4(postprocess.loop_frames(frames), job_dir / "orbit.mp4")
        self.log.emit(f"Done {name} in {time.time() - started:.0f}s -> {job_dir}")
        self.job_done.emit(str(job_dir))


class LogDialog(QDialog):
    def __init__(self, parent, lines: list[str]):
        super().__init__(parent)
        self.setWindowTitle(t("Engine log"))
        self.resize(900, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(hint(t("Technical messages from the AI engine (ComfyUI). "
                             "Useful when something goes wrong or when asking for help.")))
        self.text = QPlainTextEdit(readOnly=True, maximumBlockCount=5000)
        self.text.setPlainText("\n".join(lines))
        lay.addWidget(self.text)

    def append(self, line: str):
        self.text.appendPlainText(line)


class MainWindow(QMainWindow):
    server_log = Signal(str)

    def __init__(self, prefs: Prefs):
        super().__init__()
        self.prefs = prefs
        self.versions = load_versions()
        self.resize(1400, 900)
        self.setMinimumSize(1100, 720)
        self.engine = load_engine(self.versions)
        self.comfy_version = ""
        self.server = ComfyServer(self.engine, prefs.extra_comfy_args, on_log=self.server_log.emit)
        self.engine_state = "down"
        self.engine_detail = ""
        self.backend_ready = False
        self.job_thread: QThread | None = None
        self.worker: Worker | None = None
        self.log_lines: list[str] = []
        self.log_dialog: LogDialog | None = None
        self.queue_paths: list[str] = []
        self.status_msg: tuple[str, dict] = ("", {})

        self.player = QMediaPlayer(self)
        self.player.setLoops(QMediaPlayer.Infinite)
        self.server_log.connect(self._append_log)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._generate)

        self._build()
        self._load_settings_from_prefs()
        self._refresh_results()

        self.poll = QTimer(self, interval=1500, timeout=self._poll_backend)
        self.poll.start()
        QTimer.singleShot(0, self._start_backend)

    # ================================================================== building
    def _build(self):
        """Build menus and every widget in the current language. Called again on a language switch."""
        self.setWindowTitle(f"StillSpin360 — {t('photo to 360° spin')} · v{self.versions['app_version']}")
        self._build_menus()

        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 10, 16, 8)
        outer.setSpacing(10)

        top = QHBoxLayout()
        self.engine_pill = label("", "EnginePill")
        self.engine_pill.setToolTip(t("The AI engine runs in the background on your computer. "
                                      "It must be ready (green) before you can create a spin."))
        top.addWidget(self.engine_pill)
        top.addStretch(1)
        self.results_count = label("", "Mono")
        top.addWidget(self.results_count)
        outer.addLayout(top)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        cols.addWidget(self._build_photos_column(), 3)
        cols.addWidget(self._build_settings_column(), 4)
        cols.addWidget(self._build_result_column(), 5)
        outer.addLayout(cols, 1)
        self.setCentralWidget(root)

        self.status_left = QLabel()
        self.status_right = QLabel()
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.addWidget(self.status_left, 1)
        sb.addPermanentWidget(self.status_right)
        self._show_engine()

    def _build_menus(self):
        mb = self.menuBar()
        mb.clear()

        def act(menu, text, fn, shortcut=None):
            a = QAction(text, self)
            a.triggered.connect(fn)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            menu.addAction(a)
            return a

        m = mb.addMenu(t("File"))
        act(m, t("Add photos…"), self._browse_photos, "Ctrl+O")
        act(m, t("Open results folder"), lambda: self._open_path(OUTPUT_DIR))
        m.addSeparator()
        act(m, t("Exit"), self.close)

        m = mb.addMenu(t("AI engine"))
        self.engine_action = act(m, t("Stop engine"), self._toggle_backend)
        act(m, t("Show engine log"), self._show_log)

        # Always bilingual, so someone in the wrong language can still find it.
        m = mb.addMenu("Language / 語言")
        group = QActionGroup(self)
        for code, name in i18n.LANGUAGES.items():
            lang = QAction(name, self, checkable=True, checked=(code == i18n.current()))
            lang.triggered.connect(lambda _=False, c=code: self._set_language(c))
            group.addAction(lang)
            m.addAction(lang)

        m = mb.addMenu(t("Help"))
        act(m, t("How to use StillSpin360"), self._show_help, "F1")
        act(m, t("About StillSpin360"), self._show_about)

    def _build_photos_column(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(step_header(1, t("Choose your photos")))
        lay.addWidget(hint(t("Pick one or more photos. A clear photo of one person, with the whole body or "
                             "upper body visible, works best. Each photo becomes its own 360° spin.")))
        self.drop = DropZone()
        self.drop.setToolTip(t("Click to choose photos, or drag them here from File Explorer."))
        self.drop.files_dropped.connect(self._add_files)
        lay.addWidget(self.drop, 2)

        lay.addWidget(heading(t("Photos to spin"), t(
            "These photos will be turned into spins, one after another, when you press Create. "
            "Click a photo to preview it and to see the size of its spin.")))
        self.queue = QListWidget()
        self.queue.currentRowChanged.connect(self._queue_selected)
        lay.addWidget(self.queue, 2)
        self.queue_empty = hint(t("No photos yet."))
        lay.addWidget(self.queue_empty)

        row = QHBoxLayout()
        self.remove_btn = QPushButton(t("Remove"), clicked=self._remove_photo)
        self.remove_btn.setToolTip(t("Take the selected photo off the list. The photo file itself is not deleted."))
        clear_btn = QPushButton(t("Clear all"), clicked=self._clear_photos)
        clear_btn.setToolTip(t("Empty the list. Your photo files are not deleted."))
        row.addWidget(self.remove_btn)
        row.addWidget(clear_btn)
        lay.addLayout(row)
        return frame

    def _build_settings_column(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(step_header(2, t("Choose settings")))
        lay.addWidget(hint(t("If you are not sure, just pick a preset and press Create. "
                             "The presets set everything below for you.")))

        body = QWidget()
        body.setObjectName("Row")
        b = QVBoxLayout(body)
        b.setContentsMargins(0, 4, 6, 0)
        b.setSpacing(6)

        # --- preset
        b.addWidget(heading(t("Preset"), t(
            "A preset is a ready-made combination of Detail, Spin length, Steps and Turbo.\n\n"
            "Best quality – sharpest, needs a 16 GB graphics card.\n"
            "Balanced – a bit quicker.\n"
            "Fast – quickest, best for 12 GB graphics cards.")))
        self.preset_chips = Chips([(k, t(v)) for k, v in PRESET_LABELS.items()],
                                  {k: t(v) for k, v in PRESET_HINTS.items()})
        self.preset_chips.changed.connect(self._apply_preset)
        b.addWidget(self.preset_chips)
        self.preset_hint = hint("")
        b.addWidget(self.preset_hint)
        b.addSpacing(8)

        # --- detail
        b.addWidget(heading(t("Detail"), t(
            "How many pixels the spin has. Higher numbers are sharper but slower and need more "
            "graphics memory.\n\nYour photo's shape (portrait, landscape or square) is always kept: "
            "the number sets the total amount of detail, not the width.")))
        self.size_chips = Chips([(s, str(s)) for s in SIZE_CHOICES])
        self.size_chips.changed.connect(lambda _: (self._mark_custom(), self._update_canvas_info()))
        b.addWidget(self.size_chips)
        self.canvas_info = label("", "MonoAccent")
        b.addWidget(self.canvas_info)
        b.addWidget(hint(t("Higher is sharper but slower. The spin keeps the same shape as your photo.")))
        b.addSpacing(8)

        # --- length
        b.addWidget(heading(t("Spin length"), t(
            "How many frames one full turn has, and so how long it lasts at 24 frames per second. "
            "More frames give a smoother, slower turn but take longer to create.\n\n"
            "73 frames (3 seconds) is what the spin add-on was trained on and gives the most reliable result.")))
        self.frame_chips = Chips([(f, f"{f / FPS:.1f}s") for f in FRAME_CHOICES],
                                 {f: t("{n} frames", n=f) for f in FRAME_CHOICES})
        self.frame_chips.changed.connect(lambda _: self._mark_custom())
        b.addWidget(self.frame_chips)
        b.addWidget(hint(t("How long one full turn lasts. 3.0s is recommended.")))
        b.addSpacing(8)

        # --- advanced
        self.adv_btn = QPushButton()
        self.adv_btn.setCheckable(True)
        self.adv_btn.toggled.connect(self._toggle_advanced)
        b.addWidget(self.adv_btn)
        self.adv = QWidget()
        a = QVBoxLayout(self.adv)
        a.setContentsMargins(0, 6, 0, 0)
        a.setSpacing(6)

        a.addWidget(heading(t("Steps"), t(
            "How many times the AI refines the picture. More steps give a cleaner result but take longer. "
            "28 is recommended; with Turbo mode use 8.")))
        self.steps = QSpinBox()
        self.steps.setRange(4, 60)
        self.steps.valueChanged.connect(lambda _: self._mark_custom())
        a.addWidget(self.steps)
        a.addWidget(hint(t("More steps = cleaner but slower. Recommended: 28 (8 with Turbo).")))

        self.turbo = Switch(t("Turbo mode"))
        self.turbo.setToolTip(t("Uses a speed-up add-on: about 3× faster with slightly softer detail."))
        self.turbo.toggled.connect(self._turbo_toggled)
        a.addSpacing(4)
        a.addWidget(self.turbo)
        a.addWidget(hint(t("About 3× faster with slightly softer detail. Sets Steps to 8.")))

        a.addSpacing(4)
        a.addWidget(heading(t("Spin strength"), t(
            "How strongly the 360° add-on steers the camera around your subject. Keep it at 1.0. "
            "If the person warps or melts, try 0.9; if the camera barely moves, try 1.1.")))
        self.lora = QDoubleSpinBox(singleStep=0.05, decimals=2)
        self.lora.setRange(0.0, 2.0)
        a.addWidget(self.lora)
        a.addWidget(hint(t("Keep 1.0 unless the spin looks wrong.")))

        a.addSpacing(4)
        a.addWidget(heading(t("Variation"), t(
            "The AI starts from a random number (the 'seed'). The same photo, settings and number always "
            "give the same spin.\n\nTurn on 'Repeat the same result' to keep the number fixed, so you can "
            "change one setting and compare. Turn it off to get a different variation every time.")))
        self.repeat = Switch(t("Repeat the same result, so I can compare changes"))
        self.repeat.toggled.connect(lambda on: self.seed.setEnabled(on))
        a.addWidget(self.repeat)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2**31 - 1)
        a.addWidget(self.seed)
        a.addWidget(hint(t("Off: a new variation every time. On: the same number gives the same spin.")))
        b.addWidget(self.adv)
        b.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)

        # --- create
        self.create_btn = QPushButton(t("Create 360° Spin"))
        self.create_btn.setObjectName("Primary")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self._generate)
        lay.addWidget(self.create_btn)
        shortcut = label("CTRL + ENTER  " + t("to run"), "Mono")
        shortcut.setAlignment(Qt.AlignCenter)
        lay.addWidget(shortcut)

        row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        row.addWidget(self.progress, 1)
        self.cancel_btn = QPushButton(t("Stop"), clicked=self._cancel)
        self.cancel_btn.setObjectName("Danger")
        self.cancel_btn.setToolTip(t("Stop creating. Spins that are already finished are kept."))
        row.addWidget(self.cancel_btn)
        lay.addLayout(row)
        self.stage_label = label("", "Hint", wrap=True)
        lay.addWidget(self.stage_label)
        return frame

    def _build_result_column(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(step_header(3, t("Watch and save your spin")))

        stage = QWidget()
        stage.setObjectName("Row")
        stage.setMinimumHeight(320)
        self.video_stack = QStackedLayout(stage)
        placeholder = label(t("Your spin will appear here"), "Placeholder")
        placeholder.setAlignment(Qt.AlignCenter)
        self.video = QVideoWidget()
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.player.setVideoOutput(self.video)
        self.video_stack.addWidget(placeholder)
        self.video_stack.addWidget(self.video)
        lay.addWidget(stage, 3)

        lay.addWidget(heading(t("Save and share"), t(
            "Your spin is already saved as a looping video (orbit.mp4). These buttons make other "
            "versions of the result selected in the list below.")))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(2)
        exports = [
            (t("Save as GIF"), self._export_gif,
             t("A small looping picture for chats and websites.")),
            (t("Interactive viewer"), self._export_html_folder,
             t("A web page you can spin with a slider or your mouse. Saves every frame as a PNG.")),
            (t("Single-file viewer"), self._export_html_single,
             t("The same viewer in one .html file, easy to send (bigger file).")),
            (t("Open folder"), self._open_folder,
             t("Show all files of this spin in File Explorer.")),
        ]
        self.export_buttons = []
        for i, (text, fn, tip) in enumerate(exports):
            btn = QPushButton(text, clicked=fn)
            btn.setToolTip(tip)
            self.export_buttons.append(btn)
            grid.addWidget(btn, (i // 2) * 2, i % 2)
            grid.addWidget(hint(tip), (i // 2) * 2 + 1, i % 2, Qt.AlignTop)
        lay.addLayout(grid)
        self.reverse = Switch(t("Reverse the spin direction in the viewer"))
        self.reverse.setToolTip(t("Turn this on if the viewer turns the opposite way you expect."))
        lay.addWidget(self.reverse)

        lay.addWidget(heading(t("Your results"), t(
            "Every spin you create is kept here, newest first. Click one to watch it again or to save it "
            "in another format. Files are in the 'outputs' folder.")))
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self._show_result)
        lay.addWidget(self.results, 2)
        self.results_empty = hint(t("Nothing yet — add a photo and press Create to make your first spin."))
        lay.addWidget(self.results_empty)
        return frame

    # ================================================================== language
    def _set_language(self, code: str):
        if code == i18n.current():
            return
        state = self._capture_state()
        i18n.load(code)
        self.prefs.language = code
        self.prefs.save()
        self._build()
        self._restore_state(state)

    def _capture_state(self) -> dict:
        item = self.results.currentItem()
        return {
            "preset": self.preset_chips.value(), "size": self.size_chips.value(), "frames": self.frame_chips.value(),
            "steps": self.steps.value(), "turbo": self.turbo.isChecked(), "lora": self.lora.value(),
            "repeat": self.repeat.isChecked(), "seed": self.seed.value(), "reverse": self.reverse.isChecked(),
            "advanced": self.adv_btn.isChecked(), "queue_row": self.queue.currentRow(),
            "result": item.data(Qt.UserRole) if item else None, "progress": (self.progress.value(),
                                                                             self.progress.maximum()),
        }

    def _restore_state(self, s: dict):
        self._set_controls(s["preset"], s["size"], s["frames"], s["steps"], s["turbo"])
        if s["preset"] is None:
            self._mark_custom()
        self.lora.setValue(s["lora"])
        self.repeat.setChecked(s["repeat"])
        self.seed.setValue(s["seed"])
        self.seed.setEnabled(s["repeat"])
        self.reverse.setChecked(s["reverse"])
        self.adv_btn.setChecked(s["advanced"])
        self._toggle_advanced(s["advanced"])
        self._fill_queue(s["queue_row"])
        self._refresh_results(select=s["result"])
        self.progress.setMaximum(max(1, s["progress"][1]))
        self.progress.setValue(s["progress"][0])
        self._set_status(self.status_msg[0], **self.status_msg[1])
        self._update_buttons()

    # ================================================================== settings
    def _load_settings_from_prefs(self):
        p = PRESETS[self.prefs.preset]
        self._set_controls(self.prefs.preset, p.size, p.frames, p.steps, p.turbo)
        self.lora.setValue(self.prefs.lora_strength)
        self.repeat.setChecked(not self.prefs.random_seed)
        self.seed.setValue(self.prefs.seed)
        self.seed.setEnabled(not self.prefs.random_seed)
        self.reverse.setChecked(self.prefs.viewer_reverse)
        self._toggle_advanced(False)
        self._fill_queue(-1)
        self._update_buttons()

    def _set_controls(self, preset, size, frames, steps, turbo):
        self._applying = True
        self.preset_chips.set_value(preset)
        self.size_chips.set_value(size)
        self.frame_chips.set_value(frames)
        self.steps.setValue(steps)
        self.turbo.setChecked(turbo)
        self._applying = False
        self._update_preset_hint(preset)
        self._update_canvas_info()

    def _apply_preset(self, key: str):
        p = PRESETS[key]
        self.prefs.preset = key
        self._set_controls(key, p.size, p.frames, p.steps, p.turbo)

    def _mark_custom(self):
        """A hand-changed setting no longer matches the preset: show that, like a 'custom' state."""
        if getattr(self, "_applying", False):
            return
        self.preset_chips.group.setExclusive(False)
        for btn in self.preset_chips.buttons.values():
            btn.setChecked(False)
        self.preset_chips.group.setExclusive(True)
        self.preset_hint.setText(t("Custom settings. Pick a preset to go back to recommended values."))

    def _update_preset_hint(self, key: str):
        self.preset_hint.setText(t(PRESET_HINTS[key]) if key in PRESET_HINTS else "")

    def _turbo_toggled(self, on: bool):
        if getattr(self, "_applying", False):
            return
        self._applying = True
        self.steps.setValue(8 if on else 28)
        self._applying = False
        self._mark_custom()

    def _toggle_advanced(self, on: bool):
        self.adv.setVisible(on)
        self.adv_btn.setText(t("Hide advanced settings ▲") if on else t("Show advanced settings ▼"))

    # ================================================================== photos
    def _browse_photos(self):
        self.drop.mousePressEvent(None)

    def _add_files(self, files: list[str]):
        known = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        added = [f for f in files if Path(f).suffix.lower() in known]
        if len(added) < len(files):
            QMessageBox.information(self, "StillSpin360",
                                    t("Some files were skipped because they are not photos (PNG, JPG, WEBP, BMP)."))
        self.queue_paths.extend(added)
        self._fill_queue(len(self.queue_paths) - 1)

    def _fill_queue(self, select_row: int):
        self.queue.blockSignals(True)
        self.queue.clear()
        for path in self.queue_paths:
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            self.queue.addItem(item)
        self.queue.blockSignals(False)
        self.queue_empty.setVisible(not self.queue_paths)
        if self.queue_paths:
            self.queue.setCurrentRow(min(max(select_row, 0), len(self.queue_paths) - 1))
        else:
            self._queue_selected(-1)
        self._update_buttons()

    def _remove_photo(self):
        row = self.queue.currentRow()
        if 0 <= row < len(self.queue_paths):
            del self.queue_paths[row]
            self._fill_queue(row)

    def _clear_photos(self):
        self.queue_paths.clear()
        self._fill_queue(-1)

    def _queue_selected(self, row: int):
        self.drop.show_image(self.queue_paths[row] if 0 <= row < len(self.queue_paths) else "")
        self._update_canvas_info()

    def _update_canvas_info(self):
        row = self.queue.currentRow()
        size = self.size_chips.value() or 768
        if not (0 <= row < len(self.queue_paths)):
            self.canvas_info.setText(t("about {n} × {n} px", n=size))
            return
        try:
            w, h = postprocess.open_photo(Path(self.queue_paths[row])).size
        except OSError:
            self.canvas_info.setText(t("Can't read this photo"))
            return
        c = postprocess.canvas_for(w, h, size)
        text = f"{c.out_w} × {c.out_h} px"
        if c.clamped:
            text += "   " + t("(very wide or tall photo: edges trimmed)")
        self.canvas_info.setText(text)

    # ================================================================== engine
    def _show_engine(self):
        texts = {
            "down": ("down", t("engine down")),
            "starting": ("starting", t("engine starting…")),
            "ready": ("ready", t("engine ready")),
            "missing": ("down", t("engine not installed")),
            "stopped": ("down", t("engine stopped")),
            "mismatch": ("down", t("wrong engine version")),
        }
        prop, text = texts[self.engine_state]
        pill = f"{text} · 127.0.0.1:{self.engine.port}"
        if self.engine.existing:
            pill += " · " + t("your ComfyUI")
        if self.engine_detail:
            pill += f" · {self.engine_detail}"
        self.engine_pill.setText(pill)
        self.engine_pill.setProperty("state", prop)
        self.engine_pill.style().unpolish(self.engine_pill)
        self.engine_pill.style().polish(self.engine_pill)
        short = {"down": N("not running"), "starting": N("starting…"), "ready": N("ready"),
                 "missing": N("not installed"), "stopped": N("stopped"), "mismatch": N("wrong version")}
        dot = {"ready": theme.OK, "starting": theme.WARN}.get(self.engine_state, theme.BAD)
        self.status_right.setText(
            f"{t('AI engine')}: {t(short[self.engine_state])}  <span style='color:{dot}'>●</span>")
        self.engine_action.setText(t("Stop engine") if self.server.running() else t("Start engine"))

    def _set_engine(self, state: str, detail: str = ""):
        self.engine_state, self.engine_detail = state, detail
        self._show_engine()
        self._update_buttons()

    def _start_backend(self):
        try:
            self.server.start()
            self.poll.start()
            self._set_engine("starting")
            self._set_status(N("Starting the AI engine. The first start can take a minute…"))
        except RuntimeError as e:
            self._append_log(str(e))
            self._set_engine("missing")
            self._set_status(N("The AI engine is not installed. Run installer\\install.bat first."))

    def _toggle_backend(self):
        if self.server.running():
            self.server.stop()
            self.backend_ready = False
            self._set_engine("stopped")
        else:
            self._start_backend()

    def _poll_backend(self):
        if not self.server.running():
            if self.engine_state in ("ready", "starting"):
                self._set_engine("stopped")
            self.backend_ready = False
            self._update_buttons()
            return
        if self.backend_ready:
            return
        stats = self.server.system_stats()
        if stats is None:
            return
        version = stats.get("system", {}).get("comfyui_version", "?").lstrip("v")
        if self.engine.existing:
            minimum = self.versions["comfyui"]["min_existing_version"]
            if version_tuple(version) < version_tuple(minimum):
                self._append_log(f"Your ComfyUI is v{version}; StillSpin360 needs v{minimum} or newer.")
                self._set_engine("mismatch", f"v{version} < v{minimum}")
                self._set_status(N("Your ComfyUI is too old. Update it, or run installer\\install.bat "
                                   "and choose to install a new copy."))
                self.poll.stop()
                return
        else:
            wanted = self.versions["comfyui"]["version"]
            if version != wanted:
                self._append_log(f"Version lock: StillSpin360 requires ComfyUI v{wanted}, found v{version}. "
                                 f"Re-run the installer.")
                self._set_engine("mismatch", f"v{version} ≠ v{wanted}")
                self._set_status(N("The AI engine has the wrong version. Run installer\\install.bat again."))
                self.poll.stop()
                return
        self.comfy_version = version
        dev = (stats.get("devices") or [{}])[0]
        # ComfyUI reports e.g. "cuda:0 NVIDIA GeForce RTX 4080 : cudaMallocAsync".
        gpu = re.sub(r"^\w+:\d+\s+|\s+:\s+\w+$", "", dev.get("name", "GPU")).replace("NVIDIA GeForce ", "")
        vram = dev.get("vram_total", 0) / 2**30
        self.backend_ready = True
        self._set_engine("ready", f"v{version} · {gpu} {vram:.0f} GB")
        if not self.job_thread:
            self._set_status(N("Ready. Add a photo and press Create 360° Spin."))

    # ================================================================== jobs
    def _set_status(self, text: str, **fields):
        """`text` is the English message; it is translated here so a language switch can redo it."""
        self.status_msg = (text, fields)
        self.status_left.setText(t(text, **fields) if text else "")

    def _update_buttons(self):
        busy = self.job_thread is not None
        self.create_btn.setEnabled(self.backend_ready and not busy and bool(self.queue_paths))
        if not self.backend_ready:
            self.create_btn.setToolTip(t("Waiting for the AI engine to be ready."))
        elif not self.queue_paths:
            self.create_btn.setToolTip(t("Add at least one photo first."))
        else:
            self.create_btn.setToolTip(t("Turn every photo in the list into a 360° spin."))
        self.cancel_btn.setEnabled(busy)
        self.remove_btn.setEnabled(bool(self.queue_paths))

    def _generate(self):
        if not self.create_btn.isEnabled():
            return
        self._save_prefs()
        jobs = []
        for path in self.queue_paths:
            seed = self.seed.value() if self.repeat.isChecked() else random.randint(0, 2**31 - 1)
            jobs.append(Job(Path(path), self.size_chips.value(), snap_frames(self.frame_chips.value()),
                            self.steps.value(), seed, self.lora.value(), self.turbo.isChecked()))
        self.job_thread = QThread(self)
        self.worker = Worker(self.server.url, jobs, self.engine.models)
        self.worker.moveToThread(self.job_thread)
        self.job_thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append_log)
        self.worker.stage.connect(self._on_stage)
        self.worker.job_started.connect(self._on_job_started)
        self.worker.progress.connect(self._on_progress)
        self.worker.job_done.connect(self._job_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._worker_finished)
        self.job_thread.start()
        self.progress.setMaximum(0)          # busy animation until the first step arrives
        self._update_buttons()

    def _on_job_started(self, i: int, n: int, name: str):
        self.current_job = (i, n, name)
        self._set_status(N("Creating spin {i} of {n}: {name}"), i=i, n=n, name=name)
        self.stage_label.setText(t("Getting ready…"))

    def _on_stage(self, title: str):
        self.stage_label.setText(t(STAGES.get(title, N("Working…"))))
        if title != "Sample":
            self.progress.setMaximum(0)

    def _on_progress(self, value: int, maximum: int):
        self.progress.setMaximum(maximum)
        self.progress.setValue(value)
        self.stage_label.setText(t(STAGES["Sample"]) + f"   {value}/{maximum}")

    def _on_failed(self, message: str, detail: str):
        box = QMessageBox(QMessageBox.Warning, "StillSpin360", t(message), parent=self)
        box.setDetailedText(detail)
        box.exec()

    def _cancel(self):
        if self.worker:
            self.worker.cancelled = True
            self._set_status(N("Stopping…"))

    def _job_done(self, job_dir: str):
        self._refresh_results(select=job_dir)

    def _worker_finished(self):
        cancelled = self.worker.cancelled
        self.job_thread.quit()
        self.job_thread.wait()
        self.job_thread = self.worker = None
        self.progress.setMaximum(1)
        self.progress.setValue(0)
        self.stage_label.setText("")
        self._set_status(N("Stopped.") if cancelled else N("Finished. Your spins are in the list on the right."))
        self._update_buttons()

    # ================================================================== results & export
    def _refresh_results(self, select: str | None = None):
        self.results.blockSignals(True)
        self.results.clear()
        dirs = []
        if OUTPUT_DIR.exists():
            dirs = sorted((d for d in OUTPUT_DIR.iterdir() if (d / "frames").is_dir()),
                          key=lambda d: d.stat().st_mtime, reverse=True)
        chosen = None
        for d in dirs:
            item = QListWidgetItem(d.name)
            item.setData(Qt.UserRole, str(d))
            item.setToolTip(str(d))
            self.results.addItem(item)
            if select and Path(select) == d:
                chosen = item
        self.results.blockSignals(False)
        self.results_empty.setVisible(not dirs)
        self.results_count.setText(t("{n} spins created", n=len(dirs)))
        for b in self.export_buttons:
            b.setEnabled(bool(dirs))
        if chosen:
            self.results.setCurrentItem(chosen)
        elif dirs and select is None and self.results.currentRow() < 0:
            self.results.setCurrentRow(0)

    def _current_job(self) -> Path | None:
        item = self.results.currentItem()
        if not item:
            QMessageBox.information(self, "StillSpin360", t("Select a spin in Your results first."))
            return None
        return Path(item.data(Qt.UserRole))

    def _show_result(self, item, _prev=None):
        if not item:
            return
        mp4 = Path(item.data(Qt.UserRole)) / "orbit.mp4"
        if mp4.exists():
            self.player.setSource(QUrl.fromLocalFile(str(mp4)))
            self.player.play()
            self.video_stack.setCurrentIndex(1)

    def _frames(self, job: Path) -> list[Path]:
        return sorted((job / "frames").glob("*.png"))

    def _export_gif(self):
        job = self._current_job()
        if job:
            out = postprocess.write_gif(postprocess.loop_frames(self._frames(job)), job / "orbit.gif")
            self._append_log(f"Wrote {out}")
            self._set_status(N("Saved {file}"), file=out.name)
            self._open_path(job)

    def _export_html_folder(self):
        job = self._current_job()
        if job:
            self._save_prefs()
            index = html_export.export_folder(self._frames(job), job / "viewer", job.name,
                                              self.prefs.viewer_fps, self.reverse.isChecked())
            self._append_log(f"Wrote {index}")
            self._set_status(N("Saved {file}"), file="viewer\\index.html")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(index)))

    def _export_html_single(self):
        job = self._current_job()
        if not job:
            return
        frames = self._frames(job)
        mb = html_export.estimate_single_file_mb(frames)
        if mb > 25 and QMessageBox.question(
                self, "StillSpin360", t("The single-file viewer will be about {mb} MB. Continue?",
                                        mb=f"{mb:.0f}")) != QMessageBox.Yes:
            return
        self._save_prefs()
        out = html_export.export_single_file(frames, job / f"{job.name}_viewer.html", job.name,
                                             self.prefs.viewer_fps, self.reverse.isChecked())
        self._append_log(f"Wrote {out}")
        self._set_status(N("Saved {file}"), file=out.name)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out)))

    def _open_folder(self):
        job = self._current_job()
        if job:
            self._open_path(job)

    def _open_path(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    # ================================================================== log & help
    def _append_log(self, line: str):
        self.log_lines.append(line)
        del self.log_lines[:-5000]
        if self.log_dialog:
            self.log_dialog.append(line)

    def _show_log(self):
        if self.log_dialog is None:
            self.log_dialog = LogDialog(self, self.log_lines)
            self.log_dialog.finished.connect(lambda _: setattr(self, "log_dialog", None))
        self.log_dialog.show()
        self.log_dialog.raise_()

    def _show_help(self):
        QMessageBox.information(self, t("How to use StillSpin360"), t(
            "StillSpin360 turns one photo into a short video where the camera flies all the way around "
            "the subject, while everything stays frozen in time.\n\n"
            "1. Choose your photos – click the box on the left or drag photos into it.\n"
            "2. Choose settings – pick a preset. Best quality needs a 16 GB graphics card; "
            "choose Fast for a 12 GB card.\n"
            "3. Press Create 360° Spin and wait. One spin takes a few minutes; the first one is "
            "slower because the AI loads.\n\n"
            "When it is done, the spin plays on the right. Use Save and share to make a GIF or an "
            "interactive viewer you can spin with your mouse.\n\n"
            "Tips:\n"
            "• Photos of one person work best.\n"
            "• Hover over anything, or press a (?) button, for an explanation.\n"
            "• If it runs out of memory, choose Fast."))

    def _show_about(self):
        QMessageBox.about(self, t("About StillSpin360"), t(
            "StillSpin360 v{version}\n\n"
            "Runs the MiniMax-H3 video model with the 360° Orbit LoRA by pablodawson, "
            "on the ComfyUI v{comfy} AI engine.\n\n"
            "Everything runs on your own computer.",
            version=self.versions["app_version"],
            comfy=self.comfy_version or self.versions["comfyui"]["version"]))

    # ================================================================== lifecycle
    def _save_prefs(self):
        if self.preset_chips.value():
            self.prefs.preset = self.preset_chips.value()
        self.prefs.seed = self.seed.value()
        self.prefs.random_seed = not self.repeat.isChecked()
        self.prefs.lora_strength = self.lora.value()
        self.prefs.viewer_reverse = self.reverse.isChecked()
        self.prefs.save()

    def closeEvent(self, e):
        if self.worker:
            self.worker.cancelled = True
        if self.job_thread:
            self.job_thread.quit()
            self.job_thread.wait(20000)
        self._save_prefs()
        self.player.stop()
        self.server.stop()
        super().closeEvent(e)


def main():
    if sys.platform == "win32":
        # Without its own AppUserModelID the taskbar groups the window under python.exe and shows its icon.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StillSpin360.App")
    app = QApplication(sys.argv)
    app.setApplicationName("StillSpin360")
    app.setWindowIcon(QIcon(str(APP_ICON)))
    app.setStyle("Fusion")
    theme.apply(app)
    prefs = Prefs.load()
    prefs.language = i18n.load(prefs.language or i18n.detect())
    win = MainWindow(prefs)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
