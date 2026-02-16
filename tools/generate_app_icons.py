from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = ROOT / "build" / "icons"
PNG_PATH = ICONS_DIR / "app_icon.png"
ICO_PATH = ICONS_DIR / "app_icon.ico"
ICNS_PATH = ICONS_DIR / "app_icon.icns"
ICONSET_DIR = ICONS_DIR / "app_icon.iconset"


def make_base_image(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), (8, 12, 28, 255))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (64, 64, size - 64, size - 64),
        radius=190,
        fill=(14, 32, 74, 255),
        outline=(0, 229, 255, 255),
        width=18,
    )

    draw.rounded_rectangle(
        (128, 128, size - 128, size - 128),
        radius=150,
        fill=(11, 19, 44, 255),
        outline=(124, 77, 255, 240),
        width=8,
    )

    points = [
        (size * 0.30, size * 0.63),
        (size * 0.46, size * 0.42),
        (size * 0.56, size * 0.53),
        (size * 0.70, size * 0.36),
    ]
    draw.line(points, fill=(50, 255, 180, 255), width=52, joint="curve")

    draw.ellipse((size * 0.25, size * 0.20, size * 0.35, size * 0.30), fill=(0, 229, 255, 150))
    draw.ellipse((size * 0.67, size * 0.68, size * 0.78, size * 0.79), fill=(124, 77, 255, 140))

    return image


def generate_png_and_ico() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    base = make_base_image()
    base.save(PNG_PATH, format="PNG")

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(ICO_PATH, format="ICO", sizes=sizes)


def generate_icns_if_possible() -> bool:
    iconutil = shutil.which("iconutil")
    if not iconutil:
        return False

    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    base = Image.open(PNG_PATH)
    required_sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in required_sizes:
        resized = base.resize((size, size), Image.Resampling.LANCZOS)
        if size == 1024:
            resized.save(ICONSET_DIR / "icon_512x512@2x.png", format="PNG")
        elif size >= 32:
            half = size // 2
            resized_half = base.resize((half, half), Image.Resampling.LANCZOS)
            resized_half.save(ICONSET_DIR / f"icon_{half}x{half}.png", format="PNG")
            resized.save(ICONSET_DIR / f"icon_{half}x{half}@2x.png", format="PNG")
        else:
            resized.save(ICONSET_DIR / "icon_16x16.png", format="PNG")

    result = subprocess.run(
        [iconutil, "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_PATH)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and ICNS_PATH.exists()


def main() -> int:
    generate_png_and_ico()
    created_icns = generate_icns_if_possible()

    print(f"PNG: {PNG_PATH}")
    print(f"ICO: {ICO_PATH}")
    if created_icns:
        print(f"ICNS: {ICNS_PATH}")
    else:
        print("ICNS: não gerado (iconutil indisponível)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
