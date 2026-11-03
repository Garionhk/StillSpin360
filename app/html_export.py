"""Export an orbit as an interactive HTML viewer (slider / drag / auto-rotate both ways)."""

import base64
import html
import json
import shutil
from pathlib import Path

from .postprocess import loop_frames
from .i18n import N, t
from .settings import FAVICON, FPS, TEMPLATE_DIR

VIEWER_LABELS = {
    "loading": N("Loading frames…"),
    "ccw": N("Rotate counter-clockwise (←)"),
    "cw": N("Rotate clockwise (→)"),
    "play": N("▶ Auto-rotate"),
    "pause": N("❚❚ Pause"),
    "playTip": N("Auto-rotate (Space)"),
    "dirCw": N("Clockwise"),
    "dirCcw": N("Counter-clockwise"),
    "speed": N("Speed"),
    "reverse": N("Reverse direction"),
    "hint": N("Drag the image or the slider to rotate · ← → step · Space toggles auto-rotate"),
}


def _render(title: str, sources: list[str], fps: int, reverse: bool) -> str:
    template = (TEMPLATE_DIR / "viewer.html").read_text(encoding="utf-8")
    start, end = template.index("/*__CONFIG__*/"), template.index("/*__END__*/") + len("/*__END__*/")
    config = json.dumps({"title": title, "frames": sources, "fps": fps, "reverse": reverse,
                         "labels": {k: t(v) for k, v in VIEWER_LABELS.items()}})
    # Keep a "</script>" inside a title from closing the script tag early.
    config = config.replace("</", "<\\/")
    favicon = "data:image/png;base64," + base64.b64encode(FAVICON.read_bytes()).decode("ascii") \
        if FAVICON.exists() else ""
    head = template[:start].replace("__TITLE__", html.escape(title)).replace("__FAVICON__", favicon)
    return head + config + template[end:]


def export_folder(frames: list[Path], dest_dir: Path, title: str,
                  fps: int = FPS, reverse: bool = False) -> Path:
    """dest_dir/index.html + dest_dir/frames/frame_000.png ... (lossless PNGs)."""
    frames = loop_frames(frames)
    frames_dir = dest_dir / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    sources = []
    for i, src in enumerate(frames):
        name = f"frame_{i:03d}.png"
        shutil.copyfile(src, frames_dir / name)
        sources.append(f"frames/{name}")
    index = dest_dir / "index.html"
    index.write_text(_render(title, sources, fps, reverse), encoding="utf-8")
    return index


def export_single_file(frames: list[Path], dest: Path, title: str,
                       fps: int = FPS, reverse: bool = False) -> Path:
    """One self-contained .html with every PNG frame embedded as a data URI."""
    sources = ["data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
               for p in loop_frames(frames)]
    dest.write_text(_render(title, sources, fps, reverse), encoding="utf-8")
    return dest


def estimate_single_file_mb(frames: list[Path]) -> float:
    return sum(p.stat().st_size for p in loop_frames(frames)) * 4 / 3 / 1e6
