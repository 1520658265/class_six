"""Slice 7_grass_cliff.png into 16x16 atoms with coordinate labels.

Output:
  grid_labeled_x4.png  - 4x upscaled tilesheet with row/col labels for inspection
  atoms/r{rr}_c{cc}.png - each 16x16 tile as a separate file (4x upscaled for visibility)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(r"D:/Claude/godot/assets/tilesets/opengameart/16x16-rpg-tileset/tilesets_edit/7_grass_cliff.png")
OUT = Path(__file__).parent
ATOMS_DIR = OUT / "atoms_grass_cliff"
ATOMS_DIR.mkdir(parents=True, exist_ok=True)

TILE = 16
SCALE = 4  # upscale factor for visibility
LABEL_GUTTER = 24  # px reserved for row/col labels in the labeled overview

img = Image.open(SRC).convert("RGBA")
W, H = img.size
cols = W // TILE
rows = H // TILE
print(f"source {W}x{H} -> grid {cols}cols x {rows}rows ({cols*rows} atoms)")

# 1. Per-atom dump (4x upscaled for easy viewing)
for r in range(rows):
    for c in range(cols):
        atom = img.crop((c * TILE, r * TILE, (c + 1) * TILE, (r + 1) * TILE))
        atom_big = atom.resize((TILE * SCALE, TILE * SCALE), Image.NEAREST)
        atom_big.save(ATOMS_DIR / f"r{r:02d}_c{c:02d}.png")

# 2. Labeled overview: 4x upscaled with red gridlines + row/col numbers
big_w = cols * TILE * SCALE
big_h = rows * TILE * SCALE
canvas = Image.new("RGBA", (big_w + LABEL_GUTTER, big_h + LABEL_GUTTER), (32, 32, 32, 255))
upscaled = img.resize((big_w, big_h), Image.NEAREST)
canvas.paste(upscaled, (LABEL_GUTTER, LABEL_GUTTER))

draw = ImageDraw.Draw(canvas)
# gridlines
for c in range(cols + 1):
    x = LABEL_GUTTER + c * TILE * SCALE
    draw.line([(x, LABEL_GUTTER), (x, big_h + LABEL_GUTTER)], fill=(255, 64, 64, 200), width=1)
for r in range(rows + 1):
    y = LABEL_GUTTER + r * TILE * SCALE
    draw.line([(LABEL_GUTTER, y), (big_w + LABEL_GUTTER, y)], fill=(255, 64, 64, 200), width=1)

# labels
try:
    font = ImageFont.truetype("arial.ttf", 14)
except Exception:
    font = ImageFont.load_default()

for c in range(cols):
    x = LABEL_GUTTER + c * TILE * SCALE + (TILE * SCALE) // 2 - 6
    draw.text((x, 4), f"{c}", fill=(255, 255, 255, 255), font=font)
for r in range(rows):
    y = LABEL_GUTTER + r * TILE * SCALE + (TILE * SCALE) // 2 - 8
    draw.text((4, y), f"{r}", fill=(255, 255, 255, 255), font=font)

out_path = OUT / "grid_labeled_x4.png"
canvas.save(out_path)
print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
print(f"wrote {rows*cols} atom files to {ATOMS_DIR}")
