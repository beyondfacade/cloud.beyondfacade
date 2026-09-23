"""Convert the original offline Blender renders into lightweight web assets."""

import os
from pathlib import Path

from PIL import Image


source = Path(os.environ.get("METABOLE_RENDER_DIR", "/tmp/metabole-landing-renders"))
destination = Path(__file__).resolve().parents[2] / "public" / "landing"
destination.mkdir(parents=True, exist_ok=True)

for name, dimensions in [("seoul-diorama", (1600, 1400)), ("location-pin", (256, 320))]:
    with Image.open(source / f"{name}.png") as image:
        if image.size != dimensions or image.mode != "RGBA":
            raise ValueError(f"{name}: expected {dimensions} RGBA, got {image.size} {image.mode}")
        path = destination / f"{name}.webp"
        image.save(path, "WEBP", quality=88, method=6, exact=True)
        print(f"{path.name}: {path.stat().st_size:,} bytes, {dimensions[0]}×{dimensions[1]}")
