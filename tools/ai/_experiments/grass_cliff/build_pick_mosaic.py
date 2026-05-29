"""Build a labeled mosaic of the picked cells from 7_grass_cliff.png so the user can confirm.

Layout (from left to right, with 16px black gutter between groups, all cells 6x upscaled):
  Group 1: Grass blob   - 6 cols x 5 rows (atoms cols 0-5 rows 2-6)
  Group 2: Dirt patch   - 6 cols x 4 rows (atoms cols 0-5 rows 7-10)
  Group 3: Rocks deco A - 4 cols x 5 rows (atoms cols 8-11 rows 2-6)
  Group 4: Rocks deco B - 4 cols x 3 rows (atoms cols 8-11 rows 7-9)

For each tile we label with its source (c,r) coord on the original 7_grass_cliff.png grid,
plus a role tag (TL/T/TR/L/F/R/BL/B/BR for blob templates).

Output: pick_mosaic.png  (in this same directory)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(r"D:/Claude/godot/assets/tilesets/opengameart/16x16-rpg-tileset/tilesets_edit/7_grass_cliff.png")
OUT = Path(__file__).parent / "pick_mosaic.png"
TILE = 16
SCALE = 6           # upscale tiles
LABEL_H = 18        # px above each cell for coord/role label
GROUP_GAP = 24      # px between groups
HEADER = 32         # px reserved at top for group title
PAD = 12

img = Image.open(SRC).convert("RGBA")

def role_grid_blob(cols, rows):
    """Return [[role,...]] for a rectangular outside-corner blob template."""
    g = []
    for r in range(rows):
        row = []
        for c in range(cols):
            top    = (r == 0)
            bot    = (r == rows - 1)
            left   = (c == 0)
            right  = (c == cols - 1)
            if top and left:    row.append("TL")
            elif top and right: row.append("TR")
            elif bot and left:  row.append("BL")
            elif bot and right: row.append("BR")
            elif top:           row.append("T")
            elif bot:           row.append("B")
            elif left:          row.append("L")
            elif right:         row.append("R")
            else:               row.append("F")
        g.append(row)
    return g

def role_grid_deco(cols, rows):
    return [["·" for _ in range(cols)] for _ in range(rows)]

GROUPS = [
    # title, atom-c0, atom-r0, cols, rows, role-fn
    ("Grass blob (terrain)",      0, 2, 6, 5, role_grid_blob),
    ("Dirt patch (terrain)",      0, 7, 6, 4, role_grid_blob),
    ("Rock pile A (decoration)",  8, 2, 4, 5, role_grid_deco),
    ("Rock pile B (decoration)",  8, 7, 4, 3, role_grid_deco),
]

# layout
TILE_PX = TILE * SCALE                       # 96
CELL_BLOCK_H = LABEL_H + TILE_PX             # tile + label above
group_widths = [g[3] * TILE_PX for g in GROUPS]
group_heights = [g[4] * CELL_BLOCK_H for g in GROUPS]

canvas_w = PAD * 2 + sum(group_widths) + GROUP_GAP * (len(GROUPS) - 1)
canvas_h = PAD * 2 + HEADER + max(group_heights)

canvas = Image.new("RGBA", (canvas_w, canvas_h), (24, 24, 28, 255))
draw = ImageDraw.Draw(canvas)

try:
    font_title = ImageFont.truetype("arial.ttf", 18)
    font_small = ImageFont.truetype("arial.ttf", 11)
except Exception:
    font_title = ImageFont.load_default()
    font_small = ImageFont.load_default()

cursor_x = PAD
for (title, c0, r0, cols, rows, role_fn), gw, gh in zip(GROUPS, group_widths, group_heights):
    # group title at top
    draw.text((cursor_x, PAD), title, fill=(255, 230, 130, 255), font=font_title)
    roles = role_fn(cols, rows)
    for rr in range(rows):
        for cc in range(cols):
            atom = img.crop(((c0 + cc) * TILE, (r0 + rr) * TILE,
                             (c0 + cc + 1) * TILE, (r0 + rr + 1) * TILE))
            big = atom.resize((TILE_PX, TILE_PX), Image.NEAREST)
            x = cursor_x + cc * TILE_PX
            y = PAD + HEADER + rr * CELL_BLOCK_H + LABEL_H
            canvas.paste(big, (x, y))
            # cell border
            draw.rectangle([x, y, x + TILE_PX - 1, y + TILE_PX - 1], outline=(80, 80, 80, 255), width=1)
            # label "(c,r) ROLE"
            label = f"({c0+cc},{r0+rr}) {roles[rr][cc]}"
            draw.text((x + 2, y - LABEL_H + 2), label, fill=(220, 220, 220, 255), font=font_small)
    cursor_x += gw + GROUP_GAP

canvas.save(OUT)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes), size={canvas.size}")
