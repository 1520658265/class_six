"""按 5/25 丁埠小学地图 spec 把已有的 AI 资产组装成完整外景：

输入（已经过 postprocess.py 处理）：
  - assets/tilesets/dingbu/ground/*.png  8 张 ground tile（1024×1024 原尺寸）
  - assets/tilesets/dingbu/nature/*.png  16 张 nature tile
  - assets/tilesets/dingbu/buildings/{teaching,dormitory,shop,canteen,toilet}.png  整栋建筑（带 alpha）

输出：
  - assets/tilesets/dingbu/ground_32/*.png    缩到 32×32 的 ground tile
  - assets/tilesets/dingbu/nature_32/*.png    缩到 32×32 的 nature tile
  - assets/tilesets/dingbu/buildings_scaled/*.png  按地图占地比缩放的建筑
  - scenes/levels/school.tscn                丁埠小学外景，挂 LevelBase

Spec 引用：docs/superpowers/specs/2026-05-25-丁埠小学地图-spec.md
  - 地图：64×40 tiles × 32px = 2048×1280 px
  - 建筑：教学楼 10×3 / 宿舍 7×2 / 小卖部 3×2 / 食堂 4×2 / 厕所 2×2
  - 主泥巴马路：东西向 64×2，y=28
  - 操场：10×6，(24, 18)
  - 山林：3 tile 厚围合
"""
from __future__ import annotations
import random
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TILE = 32
MAP_W_TILES = 64
MAP_H_TILES = 40

GROUND_DIR = ROOT / "assets/tilesets/dingbu/ground"
NATURE_DIR = ROOT / "assets/tilesets/dingbu/nature"
BUILDINGS_DIR = ROOT / "assets/tilesets/dingbu/buildings"
GROUND_32_DIR = ROOT / "assets/tilesets/dingbu/ground_32"
NATURE_32_DIR = ROOT / "assets/tilesets/dingbu/nature_32"
BUILDINGS_SCALED_DIR = ROOT / "assets/tilesets/dingbu/buildings_scaled"

## ground tile 4×2 布局（按 spec）：
##  r0_c0=草地 r0_c1=泥土路 r0_c2=操场沙地 r0_c3=水泥小道
##  r1_c0=泥潭 r1_c1=石板路 r1_c2=杂草丛  r1_c3=水面
GROUND_GRASS = "ground_r0_c0.png"
GROUND_DIRT = "ground_r0_c1.png"
GROUND_SAND = "ground_r0_c2.png"

## 建筑实际 tile 占地（spec §地图布局）
BUILDINGS = {
	"teaching":  {"tiles": (10, 3), "topleft_tile": (24, 14), "label": "教学楼"},
	"dormitory": {"tiles": (7, 2),  "topleft_tile": (26, 9),  "label": "宿舍"},
	"shop":      {"tiles": (3, 2),  "topleft_tile": (33, 9),  "label": "小卖部"},
	"canteen":   {"tiles": (4, 2),  "topleft_tile": (33, 11), "label": "食堂"},
	"toilet":    {"tiles": (2, 2),  "topleft_tile": (52, 26), "label": "厕所"},
}


def downsample_dir(src_dir: Path, dst_dir: Path, target: int = TILE) -> None:
	dst_dir.mkdir(parents=True, exist_ok=True)
	for p in sorted(src_dir.glob("*.png")):
		im = Image.open(p).convert("RGBA").resize((target, target), Image.LANCZOS)
		im.save(dst_dir / p.name)
	print(f"[OK] {src_dir.name} → {dst_dir.name} ({target}×{target})")


def scale_buildings() -> None:
	BUILDINGS_SCALED_DIR.mkdir(parents=True, exist_ok=True)
	for key, cfg in BUILDINGS.items():
		w_tiles, h_tiles = cfg["tiles"]
		target_w = w_tiles * TILE
		target_h = h_tiles * TILE
		src = BUILDINGS_DIR / f"{key}.png"
		if not src.exists():
			print(f"[skip] missing {src}")
			continue
		im = Image.open(src).convert("RGBA").resize((target_w, target_h), Image.LANCZOS)
		out = BUILDINGS_SCALED_DIR / f"{key}.png"
		im.save(out)
		print(f"[OK] {key}.png {im.size}")


def render_school_png() -> None:
	"""把 32×32 ground tile + scaled 建筑拼成一张预览 PNG，方便肉眼确认布局。"""
	canvas = Image.new("RGBA", (MAP_W_TILES * TILE, MAP_H_TILES * TILE), (40, 40, 40, 255))
	grass = Image.open(GROUND_32_DIR / GROUND_GRASS).convert("RGBA")
	dirt = Image.open(GROUND_32_DIR / GROUND_DIRT).convert("RGBA")
	sand = Image.open(GROUND_32_DIR / GROUND_SAND).convert("RGBA")

	## 第 1 步：草地铺满
	for r in range(MAP_H_TILES):
		for c in range(MAP_W_TILES):
			canvas.paste(grass, (c * TILE, r * TILE))

	## 第 2 步：操场（10×6 sand at (24, 18)）
	for r in range(18, 24):
		for c in range(24, 34):
			canvas.paste(sand, (c * TILE, r * TILE))

	## 第 3 步：主泥巴马路（64×2 dirt at y=28）
	for r in range(28, 30):
		for c in range(0, 64):
			canvas.paste(dirt, (c * TILE, r * TILE))

	## 第 4 步：教学楼右侧泥巴小路（1×8 dirt at (34, 14)）
	for r in range(14, 22):
		canvas.paste(dirt, (34 * TILE, r * TILE))

	## 第 5 步：建筑
	for key, cfg in BUILDINGS.items():
		bldg_path = BUILDINGS_SCALED_DIR / f"{key}.png"
		if not bldg_path.exists():
			continue
		bldg = Image.open(bldg_path).convert("RGBA")
		x, y = cfg["topleft_tile"]
		canvas.alpha_composite(bldg, (x * TILE, y * TILE))

	## 第 6 步：山林边界（3 tile 厚，r0..2 / r37..39 / c0..2 / c61..63）
	## 用 nature_32 中的随机一个作为树/岩石；70% 树 30% 岩石
	rng = random.Random(42)
	natures = sorted(NATURE_32_DIR.glob("*.png"))
	if natures:
		## 假设 nature_32 16 张里前 12 张是树/灌木，后 4 张是岩石（顺序无所谓，只要随机分布看起来自然）
		tree_imgs = [Image.open(p).convert("RGBA") for p in natures[:12]]
		rock_imgs = [Image.open(p).convert("RGBA") for p in natures[12:]] if len(natures) > 12 else tree_imgs[-4:]
		def at(c: int, r: int) -> None:
			pool = tree_imgs if rng.random() < 0.7 else rock_imgs
			img = rng.choice(pool)
			canvas.alpha_composite(img, (c * TILE, r * TILE))
		for r in range(0, 3):
			for c in range(0, MAP_W_TILES):
				at(c, r)
		for r in range(MAP_H_TILES - 3, MAP_H_TILES):
			for c in range(0, MAP_W_TILES):
				at(c, r)
		for r in range(3, MAP_H_TILES - 3):
			for c in range(0, 3):
				at(c, r)
			for c in range(MAP_W_TILES - 3, MAP_W_TILES):
				at(c, r)

	out = ROOT / "tools/godot_bake/_school_preview.png"
	canvas.save(out)
	print(f"[OK] preview → {out}")


def main() -> None:
	downsample_dir(GROUND_DIR, GROUND_32_DIR)
	downsample_dir(NATURE_DIR, NATURE_32_DIR)
	scale_buildings()
	render_school_png()
	print("\n下一步：")
	print("  1. 看 tools/godot_bake/_school_preview.png 确认布局对不对")
	print("  2. 跑 build_school_scene.py 生成 scenes/levels/school.tscn")


if __name__ == "__main__":
	main()
