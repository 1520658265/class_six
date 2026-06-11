from __future__ import annotations

import os
import uuid
from pathlib import Path

from generator.config import TILE_ID_BY_NAME
from generator.models.base import read_json
from generator.assets.image_generation import TransparencyMode
from generator.scene.images import _generated_prompt_for, _image_request, generate_scene_images
from generator.scene.map_build import build_scene_map
from generator.scene.pack import pack_scene
from scene_fixtures import write_rice_scene
from scene_fixtures import _entity


ROOT = Path(__file__).resolve().parents[1]
TEST_WORK = ROOT / "tmp" / "test_scene_composites"


def copy_rice_scene() -> Path:
    scene = TEST_WORK / f"rice_field_{os.getpid()}_{uuid.uuid4().hex}"
    return write_rice_scene(scene)


def test_scene_composites_are_tile_parts_not_large_images():
    scene = copy_rice_scene()

    build_scene_map(scene, force=True)
    art_request = read_json(scene / "art_request.json")
    map_data = read_json(scene / "map_data.json")

    object_target_ids = {item["id"] for item in art_request["objects"]}
    generation_target_ids = {item["id"] for item in art_request["generation_targets"]}
    assert "wheat_field_01" in object_target_ids
    assert "scarecrow_01" in object_target_ids
    assert "road_center_01" not in object_target_ids
    assert "road_cross_01_source" in generation_target_ids
    assert "oval_track_01_source" in generation_target_ids
    assert art_request["art_tile_size"] == [64, 64]
    assert set(map_data["layers"]["terrain"]) == {33}

    instances = [
        item for item in map_data["objects"]
        if item["properties"].get("is_map_instance")
    ]
    assert len(instances) == 73
    assert all(item["width"] == 1 and item["height"] == 1 for item in instances)
    assert any(item["properties"].get("asset_id") == "road_cross_01_road_center_01" for item in instances)
    assert any(item["properties"].get("asset_id") == "oval_track_01_track_curve_top_left_01" for item in instances)
    assert all(item["properties"].get("render_mode") == "tile_layer" for item in instances)


def test_scene_image_requests_use_tile_contracts():
    scene = copy_rice_scene()

    build_scene_map(scene, force=True)
    art_request = read_json(scene / "art_request.json")
    prompts = read_json(scene / "prompts.json")
    prompt_by_id = {item["target_id"]: item for item in prompts["prompts"]}
    objects = {item["id"]: item for item in art_request["objects"]}
    generation_targets = {item["id"]: item for item in art_request["generation_targets"]}

    wheat = _image_request(objects["wheat_field_01"], prompt_by_id["wheat_field_01"], art_request)
    road_source_prompt = _generated_prompt_for(generation_targets["road_cross_01_source"])
    road_source = _image_request(generation_targets["road_cross_01_source"], road_source_prompt, art_request)
    track_source_prompt = _generated_prompt_for(generation_targets["oval_track_01_source"])
    track_source = _image_request(generation_targets["oval_track_01_source"], track_source_prompt, art_request)
    scarecrow = _image_request(objects["scarecrow_01"], prompt_by_id["scarecrow_01"], art_request)

    assert wheat.transparency == TransparencyMode.OPAQUE
    assert "opaque seamless terrain tile" in wheat.prompt
    assert wheat.size == (64, 64)
    assert road_source.transparency == TransparencyMode.OPAQUE
    assert road_source.size == (576, 576)
    assert "coherent full-source image" in road_source.prompt
    assert "grid (4,4) = road_center" in road_source.prompt
    assert track_source.transparency == TransparencyMode.OPAQUE
    assert track_source.size == (576, 448)
    assert scarecrow.transparency == TransparencyMode.REQUIRED
    assert scarecrow.size == (128, 192)


def test_scene_pack_replaces_composite_slices_in_tile_layer():
    scene = copy_rice_scene()

    build_scene_map(scene, force=True)
    generated = generate_scene_images(scene, force=True)
    manifest = pack_scene(scene, force=True)
    applied = read_json(scene / "final" / "map_data_applied.json")

    assert "road_cross_01_source" in generated
    assert "oval_track_01_source" in generated
    assert (scene / "images" / "road_cross_01_road_center_01.png").exists()
    assert manifest["metadata"]["failed_count"] == 0
    assert manifest["metadata"]["generated_count"] == manifest["metadata"]["total_objects"]
    assert max(applied["layers"]["path"]) > 33
    assert applied["tileset"]["image"] == "tilesets/scene_tileset.png"
    assert Path(scene / "final" / "preview_applied.png").exists()


def test_scene_pack_prefers_reviewed_background_tiles():
    scene = copy_rice_scene()

    build_scene_map(scene, force=True)
    background_tiles = scene / "background_tiles"
    images = scene / "images"
    background_tiles.mkdir(parents=True)
    images.mkdir(parents=True)

    from PIL import Image

    Image.new("RGBA", (64, 64), (210, 40, 30, 255)).save(background_tiles / "wheat_field_01.png")
    Image.new("RGBA", (64, 64), (10, 20, 30, 255)).save(images / "wheat_field_01.png")
    Image.new("RGBA", (64, 64), (30, 180, 80, 255)).save(background_tiles / "road_cross_01_road_center.png")
    Image.new("RGBA", (64, 64), (5, 5, 5, 255)).save(images / "road_cross_01_road_center_01.png")

    manifest = pack_scene(scene, force=True)
    applied = read_json(scene / "final" / "map_data_applied.json")
    mappings = {item["target_id"]: item for item in manifest["mappings"]}

    assert mappings["wheat_field_01"]["asset_source"] == "background_tiles"
    assert mappings["road_cross_01_road_center_01"]["asset_source"] == "background_tiles"
    assert manifest["metadata"]["generated_count"] > 2
    assert max(applied["layers"]["path"]) > 33

    tile_id = TILE_ID_BY_NAME["wheat_field"]
    tile_w = applied["map"]["tile_width"]
    tile_h = applied["map"]["tile_height"]
    columns = applied["tileset"]["columns"]
    x = ((tile_id - 1) % columns) * tile_w + tile_w // 2
    y = ((tile_id - 1) // columns) * tile_h + tile_h // 2
    with Image.open(scene / "final" / "tilesets" / "scene_tileset.png").convert("RGBA") as tileset:
        assert tileset.getpixel((x, y)) == (210, 40, 30, 255)


def test_scene_images_sprite_sheet_group_expands_target_and_slices_members():
    scene = TEST_WORK / f"group_scene_{os.getpid()}_{uuid.uuid4().hex}"
    scene.mkdir()
    from scene_fixtures import _write_json, _write_text

    _write_text(scene / "scene.md", "group test")
    _write_json(
        scene / "map_spec.json",
        {
            "version": "1.0.0",
            "id": "group_test",
            "title": "group test",
            "theme": "test",
            "map": {"width": 8, "height": 8, "tile_width": 64, "tile_height": 64, "orientation": "orthogonal"},
            "regions": [],
            "paths": [],
            "objects": [
                {
                    "type": "npc",
                    "count": 2,
                    "placement": "center",
                    "label": "mecha",
                    "properties": {
                        "object_key": "floating_mecha",
                        "display_name": "floating mecha",
                        "source_clause": "two friendly mecha",
                        "facing": "faces_south",
                        "footprint": "2x3",
                        "source_canvas": [64, 96],
                        "blocking": False,
                    },
                }
            ],
            "entities": [],
            "constraints": {},
            "seed": 7,
            "tileset_id": "default_rpg_32",
        },
    )
    _write_json(scene / "style_profile.json", {"version": "1.0", "view": "top_down_3_4", "art_style": "pixel_art_64"})
    _write_json(
        scene / "art_request.json",
        {
            "version": "1.0",
            "scene": "group test",
            "tile_size": [64, 64],
            "seed": 7,
            "objects": [
                {
                    "id": "floating_mecha_01",
                    "object_key": "floating_mecha",
                    "display_name": "floating mecha",
                    "category": "npc",
                    "footprint": [2, 3],
                    "source_canvas": [64, 96],
                    "runtime_size": [128, 192],
                    "facing": "faces_south",
                    "anchor": "center",
                },
                {
                    "id": "floating_mecha_02",
                    "object_key": "floating_mecha",
                    "display_name": "floating mecha",
                    "category": "npc",
                    "footprint": [2, 3],
                    "source_canvas": [64, 96],
                    "runtime_size": [128, 192],
                    "facing": "faces_south",
                    "anchor": "center",
                },
            ],
            "generation_targets": [],
        },
    )
    _write_json(
        scene / "entities.json",
        {
            "version": "1.0",
            "scene": "group test",
            "entities": [
                _entity("floating_mecha_01", "floating_mecha", "floating mecha", "npc", [2, 3], [64, 96], "mecha one", "center"),
                _entity("floating_mecha_02", "floating_mecha", "floating mecha", "npc", [2, 3], [64, 96], "mecha two", "center"),
            ],
        },
    )
    _write_json(
        scene / "prompts.json",
        {
            "version": "1.0",
            "prompts": [
                {"target_id": "floating_mecha_01", "body": "friendly mecha one", "negative": ["background"]},
                {"target_id": "floating_mecha_02", "body": "friendly mecha two", "negative": ["background"]},
            ],
            "generation_groups": [
                {
                    "group_id": "floating_mecha_pair",
                    "mode": "sprite_sheet",
                    "slot_size": [64, 96],
                    "gutter": 16,
                    "targets": [
                        {"target_id": "floating_mecha_01", "variant_notes": "first mecha"},
                        {"target_id": "floating_mecha_02", "variant_notes": "second mecha"},
                    ],
                    "bbox_width_tolerance": 12,
                    "bbox_height_tolerance": 12,
                }
            ],
        },
    )

    generated = generate_scene_images(scene, force=True, target="floating_mecha_01")

    assert generated == ["floating_mecha_01", "floating_mecha_02"]
    assert (scene / "images" / "_group_floating_mecha_pair.png").exists()
    assert (scene / "images" / "floating_mecha_01.png").exists()
    assert (scene / "images" / "floating_mecha_02.png").exists()
    metadata = read_json(scene / "images" / "floating_mecha_01.json")
    assert metadata["generation_group"]["group_id"] == "floating_mecha_pair"
