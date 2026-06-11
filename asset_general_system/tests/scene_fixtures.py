from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_school_scene(scene: Path) -> Path:
    scene.mkdir(parents=True, exist_ok=True)
    _write_text(scene / "scene.md", "鼎埠县中心小学操场 1998\n")
    _write_json(scene / "map_spec.json", _school_map_spec())
    _write_json(scene / "style_profile.json", _school_style())
    _write_json(scene / "entities.json", _school_entities())
    _write_json(scene / "prompts.json", _school_prompts())
    return scene


def write_rice_scene(scene: Path) -> Path:
    scene.mkdir(parents=True, exist_ok=True)
    _write_text(scene / "scene.md", "一片金色的稻田，左下角是横穿的十字道路，右上角是一个环形跑道，跑道旁边有一个稻草人。\n标题是：稻田测试\n")
    _write_json(scene / "map_spec.json", _rice_map_spec())
    _write_json(scene / "style_profile.json", _rice_style())
    _write_json(scene / "entities.json", _rice_entities())
    _write_json(scene / "prompts.json", _rice_prompts())
    return scene


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _school_map_spec() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "id": "dingbu_primary_school_1998",
        "title": "鼎埠县中心小学操场 1998",
        "theme": "school_campus",
        "map": {"width": 64, "height": 64, "tile_width": 32, "tile_height": 32, "orientation": "orthogonal"},
        "regions": [
            {"id": "school_01", "type": "school", "position": "top", "size": "large", "priority": 95},
            {"id": "playground_01", "type": "playground", "position": "center", "size": "large", "priority": 90},
        ],
        "paths": [{"from": "school_01", "to": "playground_01", "kind": "dirt_road"}],
        "objects": [
            {
                "type": "building",
                "count": 1,
                "placement": "top",
                "label": "教学楼",
                "properties": {
                    "object_key": "school_building",
                    "display_name": "教学楼",
                    "source_clause": "教学楼在操场北侧",
                    "facing": "faces_south",
                    "footprint": "10x5",
                    "source_canvas": [320, 160],
                    "blocking": True,
                    "material": "aged brick",
                },
            },
            {
                "type": "large_prop",
                "count": 2,
                "placement": "playground",
                "label": "水泥乒乓球台",
                "properties": {
                    "object_key": "ping_pong_table",
                    "display_name": "水泥乒乓球台",
                    "source_clause": "操场东侧有两张水泥乒乓球台",
                    "facing": "east_west",
                    "footprint": "3x2",
                    "source_canvas": [128, 96],
                    "blocking": True,
                    "material": "weathered concrete",
                    "appearance": "faded green painted edge, cracked tabletop",
                },
            },
            {
                "type": "text_sign",
                "count": 1,
                "placement": "school_front",
                "label": "木质通知栏",
                "properties": {
                    "object_key": "notice_board",
                    "display_name": "木质通知栏",
                    "source_clause": "教学楼门口挂着一块旧木质通知栏",
                    "facing": "faces_south",
                    "footprint": "2x1",
                    "source_canvas": [96, 64],
                    "attached_to": "school_01",
                    "text": "通知",
                    "blocking": False,
                    "material": "weathered wood",
                    "appearance": "faded red frame, blank paper notices without readable text",
                },
            },
            {
                "type": "thin_prop",
                "count": 2,
                "placement": "playground",
                "label": "铁篮球架",
                "properties": {
                    "object_key": "basketball_hoop",
                    "display_name": "铁篮球架",
                    "source_clause": "操场北侧有两个生锈的铁篮球架",
                    "facing": "faces_south",
                    "footprint": "1x2",
                    "source_canvas": [64, 96],
                    "blocking": True,
                    "material": "rusted steel",
                    "appearance": "rusted frame, wooden backboard",
                },
            },
        ],
        "entities": [],
        "constraints": {
            "walkable_spawn": True,
            "connect_key_regions": True,
            "no_blocked_doors": True,
            "objects_require_walkable_neighbor": True,
        },
        "seed": 20260609,
        "tileset_id": "default_rpg_32",
    }


def _school_style() -> dict[str, Any]:
    return {
        "version": "1.0",
        "inherits": "../../style_defaults.json",
        "view": "top_down_3_4",
        "art_style": "pixel_art_32",
        "palette_mood": "dingbu_county_90s",
        "lighting": "midday_bright",
        "weather_tags": ["clear_sky"],
        "era_tags": ["late_1990s", "rural_china_county", "school_campus"],
        "atmosphere": "nostalgic",
        "forbidden": ["text_in_image", "watermark", "white_background", "scene_background"],
    }


def _school_entities() -> dict[str, Any]:
    return {
        "version": "1.0",
        "scene": "鼎埠县中心小学操场 1998",
        "entities": [
            _entity("school_building_01", "school_building", "教学楼", "building", [10, 5], [320, 160], "教学楼在操场北侧", "school_01"),
            _entity("ping_pong_table_01", "ping_pong_table", "水泥乒乓球台", "large_prop", [3, 2], [128, 96], "操场东侧有两张水泥乒乓球台", "playground_01"),
            _entity("ping_pong_table_02", "ping_pong_table", "水泥乒乓球台", "large_prop", [3, 2], [128, 96], "操场东侧有两张水泥乒乓球台", "playground_01"),
            {
                **_entity("notice_board_01", "notice_board", "木质通知栏", "text_sign", [2, 1], [96, 64], "教学楼门口挂着一块旧木质通知栏", "school_01"),
                "attached_to": "school_01",
                "text": "通知",
            },
            _entity("basketball_hoop_01", "basketball_hoop", "铁篮球架", "thin_prop", [1, 2], [64, 96], "操场北侧有两个生锈的铁篮球架", "playground_01"),
            _entity("basketball_hoop_02", "basketball_hoop", "铁篮球架", "thin_prop", [1, 2], [64, 96], "操场北侧有两个生锈的铁篮球架", "playground_01"),
        ],
    }


def _school_prompts() -> dict[str, Any]:
    prompt_data = [
        ("school_building_01", "1998 年县城小学操场北侧的旧教学楼，砖墙略旧，正面朝向操场，门窗清晰，适合 32px tile 网格的 RPG 地图建筑素材。"),
        ("ping_pong_table_01", "1998 年县城小学操场里的水泥乒乓球台，绿色边框已经褪色，台面有细裂纹和灰尘，整体厚重结实，适合 32px tile 网格的 RPG 地图物件。"),
        ("ping_pong_table_02", "另一张旧水泥乒乓球台，绿色边框褪色，厚重水泥桌腿，台面有裂纹和灰尘，适合 32px tile 网格的 RPG 地图物件。"),
        ("notice_board_01", "1998 年县城小学教学楼门口的旧木质通知栏，褪色红色木框，几张泛黄空白纸和抽象色块贴在板面上，适合 RPG 地图正面贴附物件。"),
        ("basketball_hoop_01", "1998 年小学操场北侧的生锈铁篮球架，铁管支架斑驳，旧木质篮板，正面朝向操场，适合 32px tile 网格的 RPG 地图瘦高物件。"),
        ("basketball_hoop_02", "另一座生锈铁篮球架，旧木质篮板，铁管支架略歪，轮廓清晰，适合 32px tile 网格的 RPG 地图瘦高物件。"),
    ]
    return {
        "version": "1.0",
        "prompts": [
            {
                "target_id": target_id,
                "body": body,
                "emphasis": ["pixel_art", "tilemap_asset"],
                "negative": ["readable text", "Chinese characters", "letters", "watermark", "background", "photorealistic"]
                if target_id == "notice_board_01"
                else ["text", "watermark", "background", "photorealistic"],
            }
            for target_id, body in prompt_data
        ],
    }


def _rice_map_spec() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "id": "rice_field_test",
        "title": "稻田测试_real_test",
        "theme": "golden_rice_field",
        "art_tile_size": 64,
        "map": {"width": 64, "height": 64, "tile_width": 64, "tile_height": 64, "orientation": "orthogonal"},
        "regions": [
            {"id": "crossroad_01", "type": "crossroad", "position": "bottom_left", "size": "medium", "priority": 90},
            {"id": "track_01", "type": "track", "position": "top_right", "size": "medium", "priority": 85},
        ],
        "paths": [],
        "objects": [
            {
                "type": "thin_prop",
                "count": 1,
                "placement": "track_01",
                "label": "稻草人",
                "properties": {
                    "object_key": "scarecrow",
                    "display_name": "稻草人",
                    "source_clause": "跑道旁边有一个稻草人",
                    "facing": "faces_south",
                    "footprint": "1x2",
                    "source_canvas": [128, 192],
                    "blocking": True,
                    "appearance": "straw scarecrow with bamboo pole, old cloth hat, standing beside the track",
                },
            }
        ],
        "base_terrain": {
            "object_key": "wheat_field",
            "display_name": "金色麦田",
            "tile": "wheat_field",
            "source_clause": "一片金色的麦田，整张地图背景都是麦田",
            "source_canvas": [64, 64],
            "properties": {"appearance": "golden wheat field tile, harvest season, seamless tileable background"},
        },
        "composites": [_road_cross(), _oval_track()],
        "entities": [],
        "constraints": {
            "walkable_spawn": True,
            "connect_key_regions": True,
            "no_blocked_doors": True,
            "objects_require_walkable_neighbor": True,
        },
        "seed": 202606091,
        "tileset_id": "default_rpg_32",
    }


def _road_cross() -> dict[str, Any]:
    parts = [
        ("road_center", "道路中心", "十字道路的中心铺面，没有边缘", "packed dirt road center tile without grass edge"),
        ("road_edge_top", "道路上边缘", "道路上边缘，顶部接麦田", "packed dirt road tile with wheat field edge on top"),
        ("road_edge_bottom", "道路下边缘", "道路下边缘，底部接麦田", "packed dirt road tile with wheat field edge on bottom"),
        ("road_edge_left", "道路左边缘", "道路左边缘，左侧接麦田", "packed dirt road tile with wheat field edge on left"),
        ("road_edge_right", "道路右边缘", "道路右边缘，右侧接麦田", "packed dirt road tile with wheat field edge on right"),
    ]
    layout = []
    for x in range(9):
        layout.append({"part": "road_edge_top" if x in (0, 8) else "road_center", "x": x, "y": 3})
        layout.append({"part": "road_center", "x": x, "y": 4})
        layout.append({"part": "road_edge_bottom" if x in (0, 8) else "road_center", "x": x, "y": 5})
    for y in (0, 1, 2, 6, 7, 8):
        layout.extend(
            [
                {"part": "road_edge_left", "x": 3, "y": y},
                {"part": "road_center", "x": 4, "y": y},
                {"part": "road_edge_right", "x": 5, "y": y},
            ]
        )
    return {
        "id": "road_cross_01",
        "type": "road_cross",
        "placement": "crossroad_01",
        "display_name": "十字道路",
        "footprint": [9, 9],
        "source_clause": "左下角是横穿的十字道路",
        "parts": [_part(*part) for part in parts],
        "layout": layout,
        "properties": {"shape": "cross", "tilemap_rule": "center plus four directional edge tile assets"},
    }


def _oval_track() -> dict[str, Any]:
    parts = [
        ("track_center", "跑道中心段", "环形跑道的直线或中段泥土跑道，没有外边缘", "reddish packed earth track center tile"),
        ("track_curve_top_left", "跑道左上弧形", "环形跑道左上角弧形跑道块", "top-left curved reddish running track tile"),
        ("track_curve_top_right", "跑道右上弧形", "环形跑道右上角弧形跑道块", "top-right curved reddish running track tile"),
        ("track_curve_bottom_left", "跑道左下弧形", "环形跑道左下角弧形跑道块", "bottom-left curved reddish running track tile"),
        ("track_curve_bottom_right", "跑道右下弧形", "环形跑道右下角弧形跑道块", "bottom-right curved reddish running track tile"),
    ]
    layout = [{"part": "track_curve_top_left", "x": 0, "y": 0}, {"part": "track_curve_top_right", "x": 8, "y": 0}]
    layout.extend({"part": "track_center", "x": x, "y": 0} for x in range(1, 8))
    for y in range(1, 6):
        layout.extend([{"part": "track_center", "x": 0, "y": y}, {"part": "track_center", "x": 8, "y": y}])
    layout.extend([{"part": "track_curve_bottom_left", "x": 0, "y": 6}, {"part": "track_curve_bottom_right", "x": 8, "y": 6}])
    layout.extend({"part": "track_center", "x": x, "y": 6} for x in range(1, 8))
    return {
        "id": "oval_track_01",
        "type": "oval_track",
        "placement": "track_01",
        "display_name": "环形跑道",
        "footprint": [9, 7],
        "source_clause": "右上角是一个环形跑道",
        "parts": [_part(*part) for part in parts],
        "layout": layout,
        "properties": {"shape": "oval", "tilemap_rule": "track center plus four corner curve tile assets"},
    }


def _part(key: str, display_name: str, source_clause: str, appearance: str) -> dict[str, Any]:
    return {
        "key": key,
        "display_name": display_name,
        "source_clause": source_clause,
        "source_canvas": [32, 32],
        "blocking": False,
        "properties": {"appearance": appearance},
    }


def _rice_style() -> dict[str, Any]:
    return {
        "version": "1.0",
        "inherits": "../../style_defaults.json",
        "view": "top_down_3_4",
        "art_style": "pixel_art_32",
        "palette_mood": "golden_harvest_field",
        "lighting": "warm_late_afternoon",
        "weather_tags": ["clear_sky", "dry_harvest_season"],
        "era_tags": ["rural", "harvest_time"],
        "atmosphere": "quiet_warm_field",
        "forbidden": ["text_in_image", "watermark", "white_background", "scene_background"],
    }


def _rice_entities() -> dict[str, Any]:
    return {
        "version": "1.0",
        "scene": "稻田测试",
        "entities": [
            _entity("wheat_field_01", "wheat_field", "金色麦田", "terrain_tile", [1, 1], [64, 64], "一片金色的麦田，整张地图背景都是麦田", None),
            _entity("scarecrow_01", "scarecrow", "稻草人", "thin_prop", [1, 2], [128, 192], "跑道旁边有一个稻草人", "track_01"),
        ],
    }


def _rice_prompts() -> dict[str, Any]:
    return {
        "version": "1.0",
        "prompts": [
            {
                "target_id": "wheat_field_01",
                "body": "Seamless 64x64 golden wheat field terrain tile for a top-down 3/4 RPG tilemap, mature harvest wheat filling the whole tile, no other ground type.",
                "emphasis": ["golden_wheat", "seamless_tile", "base_terrain"],
                "negative": ["text", "watermark", "background", "photorealistic", "white background"],
            },
            {
                "target_id": "scarecrow_01",
                "body": "Slim scarecrow sprite standing beside a track in a golden wheat field, bamboo pole frame, straw body, old cloth shirt and simple straw hat, clear silhouette for 32px tile RPG map.",
                "emphasis": ["scarecrow", "straw", "bamboo_pole", "rural_field"],
                "negative": ["text", "watermark", "background", "photorealistic", "white background"],
            },
        ],
    }


def _entity(
    target_id: str,
    object_key: str,
    display_name: str,
    category: str,
    footprint: list[int],
    source_canvas: list[int],
    source_clause: str,
    region_id: str | None,
) -> dict[str, Any]:
    return {
        "target_id": target_id,
        "object_key": object_key,
        "display_name": display_name,
        "category": category,
        "region_id": region_id,
        "footprint": footprint,
        "source_canvas": source_canvas,
        "facing": "faces_south",
        "context": source_clause,
        "source_clause": source_clause,
        "style_tags": ["test_fixture"],
    }
