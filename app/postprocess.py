"""Input preparation and video/GIF export. Uses Pillow and PyAV, both shipped with ComfyUI Portable."""

import math
from dataclasses import dataclass
from pathlib import Path

import av
from PIL import Image, ImageOps

from .settings import FPS


# MiniMax-H3 accepts keyframes with an aspect ratio between 0.4 and 2.5, on a 32-pixel grid.
MIN_RATIO, MAX_RATIO, GRID = 0.4, 2.5, 32


@dataclass
class Canvas:
    gen_w: int        # size the model renders at (multiple of 32)
    gen_h: int
    out_w: int        # final frame size, matching the photo's aspect ratio (even, for H.264)
    out_h: int
    ratio: float      # aspect ratio the output keeps (the photo's, unless clamped)
    clamped: bool     # photo was wider/taller than the model allows and had to be cropped


def open_photo(src: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(src)).convert("RGB")


def canvas_for(photo_w: int, photo_h: int, budget: int) -> Canvas:
    """Fit the photo's aspect ratio into a budget x budget pixel area, so every shape costs about
    the same VRAM and time as the square preset."""
    ratio = photo_w / photo_h
    kept = min(max(ratio, MIN_RATIO), MAX_RATIO)
    area = budget * budget
    gen_w = max(GRID, round(math.sqrt(area * kept) / GRID) * GRID)
    gen_h = max(GRID, round(math.sqrt(area / kept) / GRID) * GRID)
    # The 32-pixel grid can't hit every ratio exactly; the output is resized back to it (a few pixels).
    if kept >= 1:
        out_w, out_h = gen_w, round(gen_w / kept / 2) * 2
    else:
        out_w, out_h = round(gen_h * kept / 2) * 2, gen_h
    return Canvas(gen_w, gen_h, out_w, out_h, kept, kept != ratio)


def prepare_input(src: Path, canvas: Canvas, dest: Path) -> Path:
    """Resize the photo to the generation canvas, center-cropping only the sliver the grid needs."""
    img = ImageOps.fit(open_photo(src), (canvas.gen_w, canvas.gen_h), Image.Resampling.LANCZOS,
                       centering=(0.5, 0.5))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def restore_ratio(frames: list[Path], canvas: Canvas) -> None:
    """Resize generated frames in place to the photo's exact aspect ratio."""
    for path in frames:
        img = Image.open(path)
        if img.size != (canvas.out_w, canvas.out_h):
            img.convert("RGB").resize((canvas.out_w, canvas.out_h), Image.Resampling.LANCZOS).save(path)


def loop_frames(frames: list[Path]) -> list[Path]:
    """Drop the last frame: FL2VA pins it to the first one, so keeping it stutters on every loop."""
    return frames[:-1] if len(frames) > 1 else frames


def write_mp4(frames: list[Path], dest: Path, fps: int = FPS) -> Path:
    with av.open(str(dest), mode="w") as container:
        first = Image.open(frames[0])
        stream = container.add_stream("libx264", rate=fps)
        stream.width, stream.height = first.size
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "16", "preset": "slow"}
        for path in frames:
            frame = av.VideoFrame.from_image(Image.open(path).convert("RGB"))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return dest


def write_gif(frames: list[Path], dest: Path, fps: int = FPS, max_size: int = 512) -> Path:
    images = []
    for path in frames:
        img = Image.open(path).convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        images.append(img)
    # One shared palette keeps colors from flickering between frames.
    palette = images[len(images) // 2].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    quantized = [img.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for img in images]
    quantized[0].save(dest, save_all=True, append_images=quantized[1:], loop=0,
                      duration=round(1000 / fps), optimize=False, disposal=1)
    return dest
