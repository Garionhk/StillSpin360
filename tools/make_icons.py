"""Build the StillSpin360 icon pack from the master PNG.

    python tools/make_icons.py [master.png]

Writes to app/assets/icons/:
    stillspin360.ico              Windows icon, 16-256 px (window, taskbar, shortcuts)
    stillspin360_<size>.png       16 ... 1024 px PNGs
    favicon.png                   64 px, embedded into exported HTML viewers
"""

import sys
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "StillSpin360.png"
OUT = ROOT / "app" / "assets" / "icons"

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
PNG_SIZES = [16, 24, 32, 48, 64, 128, 256, 512, 1024]


def render(master: Image.Image, size: int) -> Image.Image:
    img = master.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 48:
        # Small sizes lose the ring's edge contrast; a light unsharp mask keeps it crisp.
        img = img.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))
    return img


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else MASTER
    master = Image.open(src).convert("RGBA")
    if master.width != master.height:
        raise SystemExit(f"{src} must be square, got {master.size}")
    OUT.mkdir(parents=True, exist_ok=True)

    for size in PNG_SIZES:
        render(master, size).save(OUT / f"stillspin360_{size}.png", optimize=True)
    render(master, 64).save(OUT / "favicon.png", optimize=True)

    frames = [render(master, s) for s in ICO_SIZES]
    frames[-1].save(OUT / "stillspin360.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES],
                    append_images=frames[:-1])
    print(f"icon pack written to {OUT}")


if __name__ == "__main__":
    main()
