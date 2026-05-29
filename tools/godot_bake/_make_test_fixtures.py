"""One-shot generator for unit test fixture sheets. Run once, commit results.

Usage: python tools/godot_bake/_make_test_fixtures.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / "tests/fixtures/sheets"
OUT.mkdir(parents=True, exist_ok=True)


def grid_4x4():
    img = Image.new("RGBA", (128, 128), (255, 0, 255, 255))
    draw = ImageDraw.Draw(img)
    for r in range(4):
        for c in range(4):
            color = ((r * 64 + 30) % 256, (c * 64 + 60) % 256, ((r + c) * 32) % 256, 255)
            draw.rectangle([c * 32, r * 32, c * 32 + 31, r * 32 + 31], fill=color)
            draw.text((c * 32 + 4, r * 32 + 4), f"{r}{c}", fill=(255, 255, 255, 255))
    img.save(OUT / "grid_4x4_32px.png")


def single_96():
    img = Image.new("RGBA", (96, 96), (255, 200, 64, 255))
    img.save(OUT / "single_96px.png")


def regions_irregular():
    img = Image.new("RGBA", (1264, 848), (40, 40, 40, 255))
    draw = ImageDraw.Draw(img)
    rects = [
        (0, 0, 421, 424), (421, 0, 842, 424), (842, 0, 1264, 424),
        (0, 424, 421, 848), (421, 424, 842, 848), (842, 424, 1264, 848),
    ]
    for i, (x0, y0, x1, y1) in enumerate(rects):
        color = ((i * 50) % 255, 100, (255 - i * 30) % 255, 255)
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=color)
    img.save(OUT / "regions_1264x848.png")


if __name__ == "__main__":
    grid_4x4()
    single_96()
    regions_irregular()
    print(f"[OK] fixtures written to {OUT}")
