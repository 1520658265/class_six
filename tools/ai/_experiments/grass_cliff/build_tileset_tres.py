"""Generate Godot 4 TileSet (.tres) for village grass+cliff source.

References res://assets/tilesets/opengameart/16x16-rpg-tileset/tilesets_edit/7_grass_cliff.png
as a single TileSetAtlasSource at 16x16 cells. Only the user-confirmed cells are declared
as tiles; the rest of the source image is left undeclared (Godot ignores them).

Confirmed picks (atlas coords are (col,row) on the 35x12 source grid):
  - Grass blob:    cols 0-5, rows 2-6   (30 cells)
  - Dirt patch:    cols 0-5, rows 7-10  (24 cells)
  - Rock pile A:   cols 8-11, rows 2-6  (20 cells)
Total: 74 tiles.

Output: D:/Claude/godot/assets/tilesets/village_grass_cliff_tileset.tres
"""
from pathlib import Path

OUT = Path(r"D:/Claude/godot/assets/tilesets/village_grass_cliff_tileset.tres")
TEX_RES_PATH = "res://assets/tilesets/opengameart/16x16-rpg-tileset/tilesets_edit/7_grass_cliff.png"

# stable, hand-picked uids/ids (Godot regenerates uids on first load if missing,
# but using explicit ones keeps the file diff-stable)
RES_UID = "uid://b7grasscliff7vil"
TEX_EXT_ID = "1_gcliff"
ATLAS_SRC_ID = "TileSetAtlasSource_gcliff"

PICKS = []
# grass blob 6x5
for r in range(2, 7):
    for c in range(0, 6):
        PICKS.append((c, r))
# dirt patch 6x4
for r in range(7, 11):
    for c in range(0, 6):
        PICKS.append((c, r))
# rock pile A 4x5
for r in range(2, 7):
    for c in range(8, 12):
        PICKS.append((c, r))

print(f"total tiles: {len(PICKS)}")

lines = []
# load_steps = 1 (TileSet itself) + 1 (atlas sub-resource) + 1 (texture ext-resource) = 3
lines.append(f'[gd_resource type="TileSet" load_steps=3 format=3 uid="{RES_UID}"]')
lines.append("")
lines.append(f'[ext_resource type="Texture2D" path="{TEX_RES_PATH}" id="{TEX_EXT_ID}"]')
lines.append("")
lines.append(f'[sub_resource type="TileSetAtlasSource" id="{ATLAS_SRC_ID}"]')
lines.append(f'texture = ExtResource("{TEX_EXT_ID}")')
lines.append("texture_region_size = Vector2i(16, 16)")
for (c, r) in PICKS:
    lines.append(f"{c}:{r}/0 = 0")
lines.append("")
lines.append("[resource]")
lines.append("tile_size = Vector2i(16, 16)")
lines.append(f'sources/0 = SubResource("{ATLAS_SRC_ID}")')
lines.append("")

content = "\n".join(lines)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(content, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(lines)} lines)")
