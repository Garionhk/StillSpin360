"""Paths, generation presets and persisted user preferences."""

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# StillSpin360.exe sits in the project folder next to ComfyUI_windows_portable; its own files
# (templates, translations, icons) are unpacked by PyInstaller and found relative to __file__.
FROZEN = getattr(sys, "frozen", False)
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
PORTABLE_DIR = ROOT / "ComfyUI_windows_portable"
COMFY_DIR = PORTABLE_DIR / "ComfyUI"
EMBEDDED_PYTHON = PORTABLE_DIR / "python_embeded" / "python.exe"
WORKFLOW_DIR = ROOT / "comfy_workflows"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"
APP_ICON = ICON_DIR / "stillspin360.ico"
FAVICON = ICON_DIR / "favicon.png"
OUTPUT_DIR = ROOT / "outputs"
VERSIONS_FILE = ROOT / "installer" / "versions.json"
PREFS_FILE = ROOT / "prefs.json"
ENGINE_FILE = ROOT / "engine.json"      # written by the installer: which ComfyUI to use, and its model names

FPS = 24

# The single caption every training clip of the orbit LoRA used. The model card says to use it verbatim.
ORBIT_PROMPT = (
    "One frozen instant. Only the camera moves. In a continuous 360 orbit. Preserve every person and "
    "object in exactly the same world position, orientation, shape and pose throughout the shot. "
    "Airborne objects remain suspended at the captured height and angle: no wobbling, shaking, "
    "spinning, drifting, falling or continued action. Keep faces, hands, clothing, liquids and the "
    "background motionless while retaining their natural appearance. Camera parallax is the only source "
    "of apparent movement. No cuts, zoom, morphing or added objects."
)

# MiniMax-H3's video VAE decodes 17*n + 5 frames. 73 is what the LoRA was trained on.
FRAME_CHOICES = [56, 73, 90, 107]


def snap_frames(frames: int) -> int:
    frames = max(5, int(frames))
    while frames % 17 != 5:
        frames += 1
    return frames


@dataclass
class Preset:
    size: int         # pixel budget: the photo keeps its aspect ratio at about size x size pixels
    frames: int
    steps: int
    turbo: bool


PRESETS = {
    "quality": Preset(size=768, frames=73, steps=28, turbo=False),
    "balanced": Preset(size=640, frames=73, steps=28, turbo=False),
    "fast": Preset(size=512, frames=73, steps=8, turbo=True),
}
SIZE_CHOICES = [512, 640, 768]


@dataclass
class Prefs:
    preset: str = "quality"
    language: str = ""            # "" = follow Windows on first run
    seed: int = 904231
    random_seed: bool = False
    lora_strength: float = 1.0
    extra_comfy_args: list = field(default_factory=list)
    viewer_reverse: bool = False
    viewer_fps: int = 24

    @classmethod
    def load(cls) -> "Prefs":
        try:
            data = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        prefs = cls(**known)
        if prefs.preset not in PRESETS:
            prefs.preset = "quality"
        return prefs

    def save(self) -> None:
        PREFS_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def load_versions() -> dict:
    return json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))


@dataclass
class Engine:
    """The ComfyUI that StillSpin360 drives: the bundled portable copy, or one the user already had."""
    kind: str                 # "bundled" | "existing"
    comfy_dir: Path           # the folder that holds ComfyUI's main.py
    python: Path
    portable: bool            # Windows portable layout (adds --windows-standalone-build)
    port: int
    models: dict              # role -> model name as ComfyUI lists it, e.g. "minimax h3\\file.safetensors"

    @property
    def existing(self) -> bool:
        return self.kind == "existing"


def load_engine(versions: dict) -> Engine:
    models = {m["role"]: Path(m["dest"]).name for m in versions["models"]}
    bundled = Engine("bundled", COMFY_DIR, EMBEDDED_PYTHON, True, versions["ports"]["bundled"], models)
    try:
        data = json.loads(ENGINE_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return bundled          # installs from before engine.json existed are bundled ones
    models.update({k: v for k, v in data.get("models", {}).items() if v})
    if data.get("kind") != "existing":
        bundled.models = models
        return bundled
    return Engine("existing", Path(data["comfy_dir"]), Path(data["python"]), bool(data.get("portable")),
                  int(data.get("port", versions["ports"]["existing"])), models)


def version_tuple(text: str) -> tuple:
    return tuple(int(p) for p in text.lstrip("v").split("-")[0].split(".")[:3] if p.isdigit())
