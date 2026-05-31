"""Generate tools/godot_bake/manifest.json for the demo.

Run: python tools/godot_bake/_build_manifest.py

Bakes:
  sprites: yuansheng + 11 NPC walksheets (一些是 _reference 版本, demo 内可接受)
  portraits: 13 角色立绘 sheet (1024x1024 当 2x2 / 1264x848 当 3x2)
  atlas: props_p0 (4 件 demo 道具)
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def first_existing(*paths: str) -> str | None:
	for p in paths:
		if (ROOT / p).is_file():
			return p
	return None


def asset_size(rel_path: str) -> tuple[int, int]:
	with Image.open(ROOT / rel_path) as im:
		return im.size


def make_walk_entry(rel_path: str) -> dict:
	w, h = asset_size(rel_path)
	assert w == h, f"walksheet not square: {rel_path} -> {(w, h)}"
	assert w % 4 == 0, f"walksheet width not divisible by 4: {rel_path}"
	tile = w // 4
	return {
		"sheet": "res://" + rel_path.replace("\\", "/"),
		"tile_w": tile,
		"tile_h": tile,
		"rows": 4,
		"cols": 4,
		"animations": {
			"walk_down":  {"row": 0, "frames": [0, 1, 2, 3], "fps": 6, "loop": True, "idle_frame": 0},
			"walk_left":  {"row": 1, "frames": [0, 1, 2, 3], "fps": 6, "loop": True, "idle_frame": 0},
			"walk_right": {"row": 2, "frames": [0, 1, 2, 3], "fps": 6, "loop": True, "idle_frame": 0},
			"walk_up":    {"row": 3, "frames": [0, 1, 2, 3], "fps": 6, "loop": True, "idle_frame": 0},
		},
	}


WALK_SOURCES: dict[str, list[str]] = {
	"yuansheng":     ["assets/art/characters/yuansheng/walk/char_yuansheng_walksheet.png"],
	"baoxianjin":    ["assets/art/characters/baoxianjin/raw/char_baoxianjin_walksheet_reference.png"],
	"baosimu":       ["assets/art/characters/baosimu/raw/char_baosimu_walksheet.png"],
	"wangyan":       ["assets/art/characters/wangyan/raw/char_wangyan_walksheet.png"],
	"zengjianming":  ["assets/art/characters/zengjianming/raw/char_zengjianming_walksheet_reference.png"],
	"caozhengdong":  ["assets/art/characters/caozhengdong/raw/char_caozhengdong_walksheet.png"],
	"huxiaodong":    ["assets/art/characters/huxiaodong/raw/char_huxiaodong_walksheet.png"],
	"zhanglei":      ["assets/art/characters/zhanglei/raw/char_zhanglei_walksheet_reference.png"],
	"lijing":        ["assets/art/characters/lijing/raw/char_lijing_walksheet_reference.png"],
	"fuqin":         ["assets/art/characters/fuqin/raw/char_fuqin_walksheet.png"],
	"muqin":         ["assets/art/characters/muqin/raw/char_muqin_walksheet_reference.png"],
	"menwei_daye":   ["assets/art/characters/menwei_daye/raw/char_menwei_daye_walksheet.png"],
	"jiejie":        ["assets/art/characters/jiejie/raw/char_jiejie_walksheet.png",
	                  "assets/art/characters/jiejie/raw/char_jiejie_walksheet_v1.jpg"],
}


def build_sprites() -> dict:
	out: dict = {}
	for cid, paths in WALK_SOURCES.items():
		path = first_existing(*paths)
		if path is None:
			print(f"[skip walk] {cid}: no usable walksheet")
			continue
		try:
			out[cid] = make_walk_entry(path)
		except AssertionError as e:
			print(f"[skip walk] {cid}: {e}")
	return out


PORTRAIT_SOURCES: dict[str, str] = {
	cid: f"assets/art/characters/{cid}/portrait/char_{cid}_portrait_sheet_source.png"
	for cid in [
		"yuansheng", "baoxianjin", "baosimu", "wangyan", "zengjianming",
		"caozhengdong", "huxiaodong", "zhanglei", "lijing",
		"fuqin", "muqin", "jiejie", "menwei_daye",
	]
}


def make_portrait_entry(rel_path: str) -> dict:
	"""1024x1024 -> 2x2 grid (4 expressions); 1264x848 -> 3x2 grid (6 expressions).

	Map to dialogue script's expression keys. Missing keys fall back to neutral
	in DialogueBox._set_portrait, so over-mapping is safer than under-mapping.
	"""
	w, h = asset_size(rel_path)
	sheet_url = "res://" + rel_path.replace("\\", "/")
	if (w, h) == (1024, 1024):
		tile = 512
		expressions = {
			"neutral":    {"row": 0, "col": 0},
			"smile":      {"row": 0, "col": 1},
			"thoughtful": {"row": 1, "col": 0},
			"worry":      {"row": 1, "col": 1},
			"sad":        {"row": 1, "col": 0},
			"angry":      {"row": 1, "col": 1},
			"stern":      {"row": 1, "col": 1},
			"smirk":      {"row": 1, "col": 1},
			"scared":     {"row": 1, "col": 1},
			"shy":        {"row": 0, "col": 0},
		}
		return {
			"sheet": sheet_url,
			"slice_mode": "grid",
			"tile_w": tile,
			"tile_h": tile,
			"rows": 2,
			"cols": 2,
			"expressions": expressions,
		}
	if (w, h) == (1264, 848):
		regions = {
			"r00": [0, 0, 421, 424],
			"r01": [421, 0, 421, 424],
			"r02": [842, 0, 422, 424],
			"r10": [0, 424, 421, 424],
			"r11": [421, 424, 421, 424],
			"r12": [842, 424, 422, 424],
		}
		expressions = {
			"neutral":    {"region": "r00"},
			"smile":      {"region": "r01"},
			"thoughtful": {"region": "r02"},
			"worry":      {"region": "r10"},
			"sad":        {"region": "r10"},
			"angry":      {"region": "r11"},
			"stern":      {"region": "r11"},
			"smirk":      {"region": "r11"},
			"scared":     {"region": "r10"},
			"shy":        {"region": "r12"},
		}
		return {
			"sheet": sheet_url,
			"slice_mode": "regions",
			"regions": regions,
			"expressions": expressions,
		}
	raise AssertionError(f"unexpected portrait sheet size: {rel_path} -> {(w, h)}")


def build_portraits() -> dict:
	out: dict = {}
	for cid, path in PORTRAIT_SOURCES.items():
		if not (ROOT / path).is_file():
			print(f"[skip portrait] {cid}: missing {path}")
			continue
		try:
			out[cid] = make_portrait_entry(path)
		except AssertionError as e:
			print(f"[skip portrait] {cid}: {e}")
	return out


def build_atlas() -> dict:
	"""Demo 范围内只接 props_p0（4 件道具图标）。

	现成 sheet `props_p0_core_icons_sheet_source.png` 实际尺寸不固定，
	bake_atlas 在 grid 模式做不到自适应；改用 regions 模式简化。
	先跳过 atlas，等真实尺寸/具体格子位置确定后再补。
	"""
	return {}


def main() -> None:
	manifest = {
		"version": 1,
		"sprites": build_sprites(),
		"portraits": build_portraits(),
		"vfx": {},
		"atlas": build_atlas(),
	}
	out_path = ROOT / "tools/godot_bake/manifest.json"
	out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
	print(f"[OK] manifest written: {out_path}")
	print(f"  sprites: {len(manifest['sprites'])} entries")
	print(f"  portraits: {len(manifest['portraits'])} entries")
	print(f"  atlas: {len(manifest['atlas'])} entries")


if __name__ == "__main__":
	main()
