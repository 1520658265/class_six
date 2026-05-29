"""Extract road clusters from 7_grass_cliff.png and produce clean previews.

Outputs (all in _slice_preview/):
  cluster_grass.png     - grass blob (cols 0-5, rows 2-6) at 1x
  cluster_grass_x6.png  - 6x upscaled
  cluster_dirtpatch.png - dirt blob on grass (cols 0-5, rows 7-10)
  cluster_road_a.png    - horizontal road system (cols 18-22, rows 2-9)
  cluster_road_b.png    - vertical road system (cols 26-31, rows 0-11)
  cluster_road_b_full.png - cluster B + its dead-end stub at cols 22-23 rows 0-11
  *_x6.png              - same regions upscaled 6x for inspection
"""
from pathlib import Path
from PIL import Image

SRC = Path(r"D:/Claude/godot/assets/tilesets/opengameart/16x16-rpg-tileset/tilesets_edit/7_grass_cliff.png")
OUT = Path(__file__).parent
TILE = 16
SCALE = 6

img = Image.open(SRC).convert("RGBA")

# (label, col0, row0, col1, row1)  -- inclusive of col0/row0, exclusive of col1/row1
REGIONS = [
    ("grass",         0, 2,  6, 7),
    ("dirtpatch",     0, 7,  6, 11),
    ("road_a",       18, 2, 23, 10),
    ("road_b",       26, 0, 32, 12),
    ("road_b_stub",  22, 0, 24, 12),  # the small dead-end column next to A/B
    ("rocks",         8, 2, 12, 10),
]

for label, c0, r0, c1, r1 in REGIONS:
    box = (c0 * TILE, r0 * TILE, c1 * TILE, r1 * TILE)
    crop = img.crop(box)
    out1 = OUT / f"cluster_{label}.png"
    crop.save(out1)
    big = crop.resize((crop.width * SCALE, crop.height * SCALE), Image.NEAREST)
    out2 = OUT / f"cluster_{label}_x{SCALE}.png"
    big.save(out2)
    print(f"{label:14s} cols {c0}-{c1-1} rows {r0}-{r1-1}  -> {crop.size}  / x{SCALE} {big.size}")
