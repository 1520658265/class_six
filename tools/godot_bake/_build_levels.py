"""Generate 7 demo level .tscn files from a config dict.

Each level has:
  - Background sprite (assets/art/scenes/p0/...)
  - Perimeter wall StaticBody2D
  - SpawnPoints node (children: Node2D with `facing` meta)
  - Doors (Area2D[SceneDoor]) to neighbor scenes
  - Optional NPC instances (Node from npc.tscn with character_id and dialogue line_id set)
  - LevelBase script with first_visit_event

Run: python tools/godot_bake/_build_levels.py
"""
from __future__ import annotations
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[2]
LEVELS_DIR = ROOT / "scenes/levels"


def perimeter_wall_subresources(w: int, h: int, thickness: int = 32) -> str:
	## 4 矩形（north/south/east/west）。每片是单独 RectangleShape2D。
	return textwrap.dedent(f"""
		[sub_resource type="RectangleShape2D" id="WallH"]
		size = Vector2({w}, {thickness})

		[sub_resource type="RectangleShape2D" id="WallV"]
		size = Vector2({thickness}, {h})
		""").strip()


def perimeter_wall_nodes(w: int, h: int, thickness: int = 32) -> str:
	half_t = thickness // 2
	return textwrap.dedent(f"""
		[node name="Walls" type="StaticBody2D" parent="."]
		collision_layer = 1
		collision_mask = 0

		[node name="WN" type="CollisionShape2D" parent="Walls"]
		position = Vector2({w / 2}, -{half_t})
		shape = SubResource("WallH")

		[node name="WS" type="CollisionShape2D" parent="Walls"]
		position = Vector2({w / 2}, {h + half_t})
		shape = SubResource("WallH")

		[node name="WE" type="CollisionShape2D" parent="Walls"]
		position = Vector2({w + half_t}, {h / 2})
		shape = SubResource("WallV")

		[node name="WW" type="CollisionShape2D" parent="Walls"]
		position = Vector2(-{half_t}, {h / 2})
		shape = SubResource("WallV")
		""").strip()


def spawn_points_block(spawns: dict) -> str:
	lines = ['[node name="SpawnPoints" type="Node2D" parent="."]\n']
	for name, info in spawns.items():
		x, y = info["pos"]
		facing = info.get("facing", "down")
		lines.append(f'[node name="{name}" type="Node2D" parent="SpawnPoints"]')
		lines.append(f'position = Vector2({x}, {y})')
		lines.append(f'metadata/facing = "{facing}"\n')
	return "\n".join(lines)


def door_block(doors: list[dict], door_script_path: str = "res://scripts/level/scene_door.gd") -> tuple[str, list[str], int]:
	"""Returns (text, sub_resource_ids, ext_resource_count_offset)"""
	if not doors:
		return "", [], 0
	out_subs = []
	out_nodes = []
	for i, d in enumerate(doors):
		shape_id = f"DoorShape_{i}"
		w, h = d.get("size", (48, 48))
		out_subs.append(f'[sub_resource type="RectangleShape2D" id="{shape_id}"]\nsize = Vector2({w}, {h})')
		x, y = d["pos"]
		out_nodes.append(f'[node name="Door_{d["target_scene_id"]}" type="Area2D" parent="."]')
		out_nodes.append(f'position = Vector2({x}, {y})')
		out_nodes.append(f'collision_layer = 0\ncollision_mask = 2')
		out_nodes.append(f'script = ExtResource("door_script")')
		out_nodes.append(f'target_scene_id = "{d["target_scene_id"]}"')
		out_nodes.append(f'target_spawn_point = "{d.get("target_spawn", "default")}"')
		out_nodes.append('')
		out_nodes.append(f'[node name="Shape" type="CollisionShape2D" parent="Door_{d["target_scene_id"]}"]')
		out_nodes.append(f'shape = SubResource("{shape_id}")')
		out_nodes.append('')
	return ("\n".join(out_subs) + "\n", out_nodes, 0)


def npc_block(npcs: list[dict]) -> tuple[str, list[str]]:
	"""Each npc: {name, character_id, pos, dialogue_line_id (optional), facing (optional)}"""
	if not npcs:
		return "", []
	nodes = []
	for npc in npcs:
		name = npc["name"]
		x, y = npc["pos"]
		facing = npc.get("facing", "down")
		dlg = npc.get("dialogue_line_id", "")
		cid = npc["character_id"]
		nodes.append(f'[node name="{name}" parent="." instance=ExtResource("npc_scene")]')
		nodes.append(f'position = Vector2({x}, {y})')
		nodes.append(f'character_id = "{cid}"')
		nodes.append(f'dialogue_line_id = "{dlg}"')
		nodes.append('')
	return "", nodes


def make_level(scene_id: str, bg_path: str, w: int, h: int, spawns: dict,
		doors: list[dict] | None = None, npcs: list[dict] | None = None,
		first_visit_event: str = "", ch1_events: list[str] | None = None,
		save_point: dict | None = None,
		obstacles: list[dict] | None = None,
		polygons: list[list[tuple[float, float]]] | None = None,
		level_script: str = "res://scripts/level/level_base.gd") -> str:
	doors = doors or []
	npcs = npcs or []
	ch1_events = ch1_events or []
	obstacles = obstacles or []
	polygons = polygons or []

	header = f'[gd_scene load_steps=20 format=3 uid="uid://b1lvl_{scene_id}"]\n'

	ext_resources = [
		f'[ext_resource type="Script" path="{level_script}" id="level_script"]',
		f'[ext_resource type="Texture2D" path="res://{bg_path}" id="bg_tex"]',
	]
	if doors:
		ext_resources.append(f'[ext_resource type="Script" path="res://scripts/level/scene_door.gd" id="door_script"]')
	if npcs:
		ext_resources.append(f'[ext_resource type="PackedScene" path="res://scenes/characters/npc.tscn" id="npc_scene"]')
	if save_point:
		ext_resources.append(f'[ext_resource type="Script" path="res://scripts/level/save_point.gd" id="save_script"]')

	## ---- Collect ALL sub_resources up front ----
	sub_resources: list[str] = []
	sub_resources.append(perimeter_wall_subresources(w, h))
	door_subs_text, door_node_lines, _ = door_block(doors)
	if door_subs_text:
		sub_resources.append(door_subs_text.rstrip())
	## obstacles: 每块一个 RectangleShape2D
	obstacle_node_lines: list[str] = []
	for i, o in enumerate(obstacles):
		shape_id = f"ObsShape_{i}"
		ow, oh = o["size"]
		sub_resources.append(f'[sub_resource type="RectangleShape2D" id="{shape_id}"]\nsize = Vector2({ow}, {oh})')
		ox, oy = o["pos"]
		obstacle_node_lines.append(f'[node name="Obstacle_{i}" type="StaticBody2D" parent="."]')
		obstacle_node_lines.append(f'position = Vector2({ox}, {oy})')
		obstacle_node_lines.append(f'collision_layer = 1\ncollision_mask = 0')
		obstacle_node_lines.append('')
		obstacle_node_lines.append(f'[node name="Shape" type="CollisionShape2D" parent="Obstacle_{i}"]')
		obstacle_node_lines.append(f'shape = SubResource("{shape_id}")')
		obstacle_node_lines.append('')
	save_node_lines: list[str] = []
	if save_point:
		x, y = save_point["pos"]
		w_sz, h_sz = save_point.get("size", (64, 64))
		sub_resources.append(f'[sub_resource type="RectangleShape2D" id="SaveShape"]\nsize = Vector2({w_sz}, {h_sz})')
		save_node_lines = [
			f'[node name="SavePoint" type="Area2D" parent="."]',
			f'position = Vector2({x}, {y})',
			f'collision_layer = 0',
			f'collision_mask = 2',
			f'script = ExtResource("save_script")',
			f'slot = {save_point.get("slot", 0)}',
			'',
			f'[node name="Shape" type="CollisionShape2D" parent="SavePoint"]',
			f'shape = SubResource("SaveShape")',
			'',
			f'[node name="Glow" type="ColorRect" parent="SavePoint"]',
			f'offset_left = {-w_sz/2}',
			f'offset_top = {-h_sz/2}',
			f'offset_right = {w_sz/2}',
			f'offset_bottom = {h_sz/2}',
			f'color = Color(0.95, 0.85, 0.45, 0.45)',
			f'mouse_filter = 2',
			'',
		]

	parts: list[str] = [header]
	parts.append("\n".join(ext_resources) + "\n")
	parts.append("\n\n".join(sub_resources) + "\n")

	ch1_events_str = "PackedStringArray(" + ", ".join(f'"{e}"' for e in ch1_events) + ")"
	root = textwrap.dedent(f"""
		[node name="Level" type="Node2D"]
		y_sort_enabled = true
		script = ExtResource("level_script")
		scene_id = "{scene_id}"
		level_size = Vector2i({w}, {h})
		first_visit_event = "{first_visit_event}"
		ch1_events = {ch1_events_str}
		""").strip()
	parts.append(root + "\n")

	bg_node = textwrap.dedent(f"""
		[node name="Background" type="Sprite2D" parent="."]
		texture = ExtResource("bg_tex")
		centered = false
		position = Vector2(0, 0)
		""").strip()
	parts.append(bg_node + "\n")

	parts.append(perimeter_wall_nodes(w, h) + "\n")
	parts.append(spawn_points_block(spawns) + "\n")

	if door_node_lines:
		parts.append("\n".join(door_node_lines))

	_, npc_node_lines = npc_block(npcs)
	if npc_node_lines:
		parts.append("\n".join(npc_node_lines))

	if obstacle_node_lines:
		parts.append("\n".join(obstacle_node_lines))

	## ---- Polygons：手描多边形 collision，配套半透明 Polygon2D 用于调试可视化 ----
	if polygons:
		poly_root = '\n[node name="Polygons" type="Node2D" parent="."]\n'
		parts.append(poly_root)
		for i, points in enumerate(polygons):
			pts_str = ", ".join(f"Vector2({x}, {y})" for x, y in points)
			parts.append(
				f'[node name="Poly_{i}" type="StaticBody2D" parent="Polygons"]\n'
				f'collision_layer = 1\n'
				f'collision_mask = 0\n'
			)
			parts.append(
				f'[node name="Shape" type="CollisionPolygon2D" parent="Polygons/Poly_{i}"]\n'
				f'polygon = PackedVector2Array({pts_str})\n'
			)
			## 调试可视化：半透明红色多边形，用 group 控制显隐
			parts.append(
				f'[node name="Debug" type="Polygon2D" parent="Polygons/Poly_{i}" groups=["debug_collision"]]\n'
				f'polygon = PackedVector2Array({pts_str})\n'
				f'color = Color(1, 0.3, 0.3, 0.35)\n'
				f'visible = false\n'
			)

	if save_node_lines:
		parts.append("\n".join(save_node_lines))

	return "\n".join(parts)


## ============================================================
## 关卡配置
## ============================================================

LEVELS = {
	"home": {
		"bg": "assets/art/scenes/p0/scene_p0_yuansheng_home_main_room_source.png",
		"size": (512, 512),
		"first_visit_event": "prologue/01_father_send_off",
		"spawns": {
			"default": {"pos": (256, 256), "facing": "down"},
			"from_mountain": {"pos": (256, 256), "facing": "down"},
		},
		"doors": [
			{"target_scene_id": "mountain_road_autumn", "target_spawn": "from_home",
			 "pos": (256, 470), "size": (96, 24)},
		],
		"npcs": [
			{"name": "Muqin", "character_id": "muqin", "pos": (180, 320),
			 "dialogue_line_id": ""},
		],
	},
	"mountain_road_autumn": {
		"bg": "assets/art/scenes/p0/scene_p0_mountain_road_autumn_source.png",
		"size": (512, 512),
		"first_visit_event": "",
		"spawns": {
			"default": {"pos": (256, 256), "facing": "down"},
			"from_home": {"pos": (256, 140), "facing": "down"},
			"from_school": {"pos": (256, 380), "facing": "up"},
		},
		"doors": [
			{"target_scene_id": "school_gate", "target_spawn": "from_mountain",
			 "pos": (256, 470), "size": (96, 24)},
			{"target_scene_id": "home", "target_spawn": "from_mountain",
			 "pos": (256, 42), "size": (96, 24)},
		],
		"npcs": [],
	},
	"school_gate": {
		"bg": "assets/art/scenes/p0/scene_p0_school_gate_source.png",
		"size": (512, 512),
		"first_visit_event": "",
		"spawns": {
			"default": {"pos": (256, 256), "facing": "down"},
			"from_mountain": {"pos": (256, 140), "facing": "down"},
			"from_corridor": {"pos": (256, 380), "facing": "up"},
		},
		"doors": [
			{"target_scene_id": "corridor_stairs", "target_spawn": "from_gate",
			 "pos": (256, 470), "size": (96, 24)},
			{"target_scene_id": "mountain_road_autumn", "target_spawn": "from_school",
			 "pos": (256, 42), "size": (96, 24)},
		],
		"npcs": [
			{"name": "Menwei", "character_id": "menwei_daye", "pos": (380, 240),
			 "dialogue_line_id": "ch1/16_sanlu_classmeeting/05"},
		],
	},
	"corridor_stairs": {
		"bg": "assets/art/scenes/p0/scene_p0_corridor_stairs_interior_source.png",
		"size": (1376, 768),
		"first_visit_event": "prologue/03_corridor_overhear",
		"ch1_events": ["ch1/12_yuekao_ranking", "ch1/14_caozhengdong_robbery"],
		"spawns": {
			"default": {"pos": (300, 380), "facing": "right"},
			"from_gate": {"pos": (300, 380), "facing": "right"},
			"from_classroom": {"pos": (1080, 380), "facing": "left"},
			"from_xiaomaibu": {"pos": (700, 600), "facing": "up"},
			"from_dorm": {"pos": (300, 600), "facing": "up"},
			"from_cafeteria": {"pos": (1100, 600), "facing": "up"},
		},
		"doors": [
			{"target_scene_id": "school_gate", "target_spawn": "from_corridor",
			 "pos": (40, 380), "size": (24, 96)},
			{"target_scene_id": "classroom_2b", "target_spawn": "from_corridor",
			 "pos": (1336, 380), "size": (24, 96)},
			{"target_scene_id": "xiaomaibu", "target_spawn": "from_corridor",
			 "pos": (700, 750), "size": (96, 24)},
			{"target_scene_id": "dorm", "target_spawn": "from_corridor",
			 "pos": (300, 750), "size": (96, 24)},
			{"target_scene_id": "cafeteria_steam", "target_spawn": "from_corridor",
			 "pos": (1100, 750), "size": (96, 24)},
		],
		"npcs": [
			{"name": "Huxiaodong", "character_id": "huxiaodong", "pos": (520, 380),
			 "dialogue_line_id": ""},
			{"name": "Zhanglei", "character_id": "zhanglei", "pos": (600, 380),
			 "dialogue_line_id": ""},
			{"name": "Lijing", "character_id": "lijing", "pos": (680, 380),
			 "dialogue_line_id": ""},
		],
	},
	"classroom_2b": {
		"bg": "assets/art/scenes/p0/scene_p0_classroom_2b_interior_source.png",
		"size": (1376, 768),
		"first_visit_event": "prologue/02_classroom_arrival",
		"ch1_events": ["ch1/15_shenzhou7_evening", "ch1/16_sanlu_classmeeting", "ch1/_demo_end"],
		"spawns": {
			"default": {"pos": (200, 400), "facing": "right"},
			"from_corridor": {"pos": (200, 400), "facing": "right"},
			"window_seat_3": {"pos": (1080, 400), "facing": "down"},
		},
		"doors": [
			{"target_scene_id": "corridor_stairs", "target_spawn": "from_classroom",
			 "pos": (40, 400), "size": (24, 96)},
		],
		"npcs": [
			{"name": "Baoxianjin", "character_id": "baoxianjin", "pos": (700, 250),
			 "dialogue_line_id": ""},
			{"name": "Zengjianming", "character_id": "zengjianming", "pos": (900, 400),
			 "dialogue_line_id": "ch1/sub_zengjianming_eraser/01"},
			{"name": "Wangyan", "character_id": "wangyan", "pos": (980, 480),
			 "dialogue_line_id": ""},
		],
		"save_point": {"pos": (1080, 400), "size": (96, 96), "slot": 0},
	},
	"xiaomaibu": {
		"bg": "assets/art/scenes/p0/scene_p0_school_shop_interior_source.png",
		"size": (1376, 768),
		"first_visit_event": "prologue/04_xiaomaibu_first_pass",
		"spawns": {
			"default": {"pos": (700, 600), "facing": "up"},
			"from_corridor": {"pos": (700, 600), "facing": "up"},
		},
		"doors": [
			{"target_scene_id": "corridor_stairs", "target_spawn": "from_xiaomaibu",
			 "pos": (700, 750), "size": (96, 24)},
		],
		"npcs": [
			{"name": "Baosimu", "character_id": "baosimu", "pos": (700, 360),
			 "dialogue_line_id": "ch1/13_xiaomaibu_first_buy/01"},
		],
	},
	"dorm": {
		"bg": "assets/art/scenes/p0/scene_p0_boys_dorm_interior_source.png",
		"size": (1376, 768),
		"first_visit_event": "prologue/05_dorm_assigned",
		"spawns": {
			"default": {"pos": (700, 600), "facing": "up"},
			"from_corridor": {"pos": (700, 600), "facing": "up"},
			"yuansheng_bed": {"pos": (300, 400), "facing": "down"},
		},
		"doors": [
			{"target_scene_id": "corridor_stairs", "target_spawn": "from_dorm",
			 "pos": (700, 750), "size": (96, 24)},
		],
		"npcs": [
			{"name": "Wangyan_Dorm", "character_id": "wangyan", "pos": (300, 460),
			 "dialogue_line_id": "ch1/sub_jiejie_letter/01"},
		],
	},
	"cafeteria_steam": {
		"bg": "assets/art/scenes/p0/scene_p0_canteen_steam_room_interior_source.png",
		"size": (1376, 768),
		"first_visit_event": "ch1/11_zhengfanhe_help",
		"spawns": {
			"default": {"pos": (700, 600), "facing": "up"},
			"from_corridor": {"pos": (700, 600), "facing": "up"},
		},
		"doors": [
			{"target_scene_id": "corridor_stairs", "target_spawn": "from_cafeteria",
			 "pos": (700, 750), "size": (96, 24)},
		],
		"npcs": [
			{"name": "Wangyan_Cafe", "character_id": "wangyan", "pos": (700, 360),
			 "dialogue_line_id": "ch1/11_zhengfanhe_help/01"},
		],
	},
}


def main() -> None:
	LEVELS_DIR.mkdir(parents=True, exist_ok=True)
	for sid, cfg in LEVELS.items():
		w, h = cfg["size"]
		text = make_level(
			scene_id=sid,
			bg_path=cfg["bg"],
			w=w, h=h,
			spawns=cfg["spawns"],
			doors=cfg.get("doors", []),
			npcs=cfg.get("npcs", []),
			first_visit_event=cfg.get("first_visit_event", ""),
			ch1_events=cfg.get("ch1_events", []),
			save_point=cfg.get("save_point"),
			obstacles=cfg.get("obstacles", []),
			polygons=cfg.get("polygons", []),
		)
		out = LEVELS_DIR / f"{sid}.tscn"
		out.write_text(text, encoding="utf-8")
		print(f"  [OK] {out.relative_to(ROOT)}")
	print(f"[OK] {len(LEVELS)} level scenes generated.")


if __name__ == "__main__":
	main()
