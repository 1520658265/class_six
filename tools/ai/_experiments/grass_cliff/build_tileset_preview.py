"""Render a PNG preview of the village_grass_cliff_tileset.tres contents.

Two panels stacked vertically:
  TOP    - source image at 6x with non-picked cells dimmed to 25% and picked cells
           outlined in green; gives a "where do these tiles come from" overview.
  BOTTOM - clean palette: 3 groups (Grass / Dirt / Rocks) at 6x with their atlas
           coords labeled, just like the Godot atlas inspector.

Output: tileset_preview.png  (next to the .tres file)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(r"D:/PersonalProject/class_six/assets/tilesets/opengameart/16x16-rpg-tileset/tilesets_edit/7_grass_cliff.png")
OUT = Path(r"D:/PersonalProject/class_six/tools/ai/_experiments/grass_cliff/village_grass_cliff_tileset_preview.png")
TILE = 16
SCALE = 6

# picks: (col, row) sets per group
GROUPS = [
    ("Grass blob (30 tiles)",     [(c, r) for r in range(2, 7)  for c in range(0, 6)],  6, 5),
    ("Dirt patch (24 tiles)",     [(c, r) for r in range(7, 11) for c in range(0, 6)],  6, 4),
    ("Rock pile A (20 tiles)",    [(c, r) for r in range(2, 7)  for c in range(8, 12)], 4, 5),
]

img = Image.open(SRC).convert("RGBA")
src_w, src_h = img.size
src_cols = src_w // TILE
src_rows = src_h // TILE

try:
    font_h    = ImageFont.truetype("arial.ttf", 22)
    font_grp  = ImageFont.truetype("arial.ttf", 18)
    font_lbl  = ImageFont.truetype("arial.ttf", 11)
    font_foot = ImageFont.truetype("arial.ttf", 14)
except Exception:
    font_h = font_grp = font_lbl = font_foot = ImageFont.load_default()

# --- TOP panel: dimmed source with picked cells outlined ---
top_img = img.resize((src_w * SCALE, src_h * SCALE), Image.NEAREST).convert("RGBA")
# build a dim layer everywhere except picked cells
dim = Image.new("RGBA", top_img.size, (0, 0, 0, 180))
mask = Image.new("L", top_img.size, 255)  # 255 = apply dim
mdraw = ImageDraw.Draw(mask)
all_picks = set()
for _, picks, _, _ in GROUPS:
    for cr in picks:
        all_picks.add(cr)
for (c, r) in all_picks:
    x0 = c * TILE * SCALE
    y0 = r * TILE * SCALE
    x1 = x0 + TILE * SCALE
    y1 = y0 + TILE * SCALE
    mdraw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=0)  # 0 = no dim

dimmed = Image.composite(dim, Image.new("RGBA", top_img.size, (0,0,0,0)), mask)
top_img = Image.alpha_composite(top_img, dimmed)

# outline picked cells in green
od = ImageDraw.Draw(top_img)
GREEN = (90, 255, 110, 255)
for (c, r) in all_picks:
    x0 = c * TILE * SCALE
    y0 = r * TILE * SCALE
    x1 = x0 + TILE * SCALE - 1
    y1 = y0 + TILE * SCALE - 1
    od.rectangle([x0, y0, x1, y1], outline=GREEN, width=2)

# --- BOTTOM panel: clean palette ---
LABEL_H = 16
GROUP_GAP = 28
PAD = 16
HEADER_H = 30  # per group title

tile_px = TILE * SCALE
group_widths = [g[2] * tile_px for g in GROUPS]
group_heights = [HEADER_H + g[3] * (tile_px + LABEL_H) for g in GROUPS]
palette_w = PAD * 2 + sum(group_widths) + GROUP_GAP * (len(GROUPS) - 1)
palette_h = PAD * 2 + max(group_heights)

palette = Image.new("RGBA", (palette_w, palette_h), (24, 24, 28, 255))
pd = ImageDraw.Draw(palette)
cursor_x = PAD
for (title, picks, gcols, grows), gw in zip(GROUPS, group_widths):
    pd.text((cursor_x, PAD), title, fill=(255, 220, 130, 255), font=font_grp)
    # picks are listed row-major (r outer, c inner) — same order they were generated
    for i, (c, r) in enumerate(picks):
        gr = i // gcols
        gc = i % gcols
        atom = img.crop((c * TILE, r * TILE, (c + 1) * TILE, (r + 1) * TILE))
        big = atom.resize((tile_px, tile_px), Image.NEAREST)
        x = cursor_x + gc * tile_px
        y = PAD + HEADER_H + gr * (tile_px + LABEL_H) + LABEL_H
        palette.paste(big, (x, y))
        pd.rectangle([x, y, x + tile_px - 1, y + tile_px - 1], outline=(70, 70, 75, 255), width=1)
        pd.text((x + 2, y - LABEL_H + 1), f"{c}:{r}", fill=(200, 200, 200, 255), font=font_lbl)
    cursor_x += gw + GROUP_GAP

# --- combine ---
TOP_TITLE_H = 28
FOOT_H = 26
COMBINE_PAD = 16
total_w = max(top_img.width, palette.width) + COMBINE_PAD * 2
total_h = COMBINE_PAD + TOP_TITLE_H + top_img.height + COMBINE_PAD + palette.height + COMBINE_PAD + FOOT_H

canvas = Image.new("RGBA", (total_w, total_h), (16, 16, 20, 255))
cd = ImageDraw.Draw(canvas)
cd.text((COMBINE_PAD, COMBINE_PAD),
        f"Source overview - 35x12 grid - 74 tiles picked (highlighted)",
        fill=(255, 255, 255, 255), font=font_h)
top_x = (total_w - top_img.width) // 2
canvas.alpha_composite(top_img, (top_x, COMBINE_PAD + TOP_TITLE_H))

pal_y = COMBINE_PAD + TOP_TITLE_H + top_img.height + COMBINE_PAD
pal_x = (total_w - palette.width) // 2
canvas.alpha_composite(palette, (pal_x, pal_y))

cd.text((COMBINE_PAD, total_h - FOOT_H + 6),
        "village_grass_cliff_tileset.tres   tile_size=16x16   Atlas mode",
        fill=(170, 170, 175, 255), font=font_foot)

canvas.save(OUT)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes), size={canvas.size}")
