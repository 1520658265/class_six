from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from generator.models.base import read_json
from generator.scene.background_plan import build_background_plan, extract_background_tiles, write_background_review_html
from generator.scene.cli import main as scene_cli_main
from generator.scene.concept import build_background_concept_prompt, generate_scene_concept
from generator.scene.images import generate_scene_images
from generator.scene.map_build import build_scene_map
from generator.scene.pack import pack_scene
from generator.scene.validation import validate_scene_file
from scene_fixtures import write_rice_scene, write_school_scene


ROOT = Path(__file__).resolve().parents[1]
TEST_WORK = ROOT / "tmp" / "test_scene_pipeline"


def copy_scene(name: str) -> Path:
    scene = TEST_WORK / f"{name}_{os.getpid()}_{uuid.uuid4().hex}"
    return write_school_scene(scene)


def copy_rice_scene(name: str) -> Path:
    scene = TEST_WORK / f"{name}_{os.getpid()}_{uuid.uuid4().hex}"
    return write_rice_scene(scene)


def test_scene_validate_accepts_example():
    scene = copy_scene("validate_accepts_example")

    assert not [issue for issue in validate_scene_file(scene, "spec") if issue.severity == "error"]


def test_scene_validate_rejects_unknown_category():
    scene = copy_scene("rejects_unknown_category")
    spec = read_json(scene / "map_spec.json")
    spec["objects"][0]["type"] = "custom_object"
    (scene / "map_spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

    issues = validate_scene_file(scene, "spec")

    assert any("unknown category" in issue.message for issue in issues)


def test_scene_validate_accepts_tile_groups_and_rejects_bad_refs():
    scene = copy_rice_scene("validate_tile_groups")
    spec = read_json(scene / "map_spec.json")
    spec["tile_groups"] = [
        {
            "group_id": "road_tiles",
            "kind": "material_group",
            "generation_mode": "sprite_sheet",
            "tile_size": [64, 64],
            "members": [
                {"tile_id": "road_center_tile", "role": "center", "source_ref": "road_cross_01:road_center"},
                {"tile_id": "road_top_edge_tile", "role": "edge_top", "source_ref": "road_cross_01:road_edge_top"},
            ],
        }
    ]
    (scene / "map_spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

    assert not [issue for issue in validate_scene_file(scene, "spec") if issue.severity == "error"]

    spec["tile_groups"][0]["members"][0]["source_ref"] = "missing_part"
    (scene / "map_spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    issues = validate_scene_file(scene, "spec")

    assert any("does not reference base terrain or composite part" in issue.message for issue in issues)


def test_scene_map_build_writes_art_request_with_source_canvas():
    scene = copy_scene("map_build_art_request")

    build_scene_map(scene, force=True)
    art_request = read_json(scene / "art_request.json")

    objects = {item["id"]: item for item in art_request["objects"]}
    assert objects["ping_pong_table_01"]["category"] == "large_prop"
    assert objects["ping_pong_table_01"]["footprint"] == [3, 2]
    assert objects["ping_pong_table_01"]["source_canvas"] == [128, 96]
    assert objects["notice_board_01"]["attached_to"] == "school_01"


def test_scene_images_target_and_pack_emit_sprite2d_and_label():
    scene = copy_scene("images_target_pack")
    build_scene_map(scene, force=True)

    generated = generate_scene_images(scene, force=True, target="notice_board_01")
    manifest = pack_scene(scene, force=True)
    tscn = (scene / "final" / "scene.tscn").read_text(encoding="utf-8")

    assert generated == ["notice_board_01"]
    assert (scene / "images" / "notice_board_01.png").exists()
    assert manifest["metadata"]["generated_count"] == 1
    assert 'type="Sprite2D"' in tscn
    assert 'name="TextLabel" type="Label"' in tscn
    assert 'metadata/text = "通知"' in tscn


def test_scene_images_cli_rejects_removed_pixai_backend():
    scene = copy_scene("images_cli_rejects_pixai")
    build_scene_map(scene, force=True)

    try:
        scene_cli_main([
            "scene-images",
            str(scene),
            "--pixai",
            "--target",
            "notice_board_01",
        ])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--pixai should be rejected")


def test_scene_background_concept_plan_review_and_extract():
    scene = copy_rice_scene("background_plan_rice")
    build_scene_map(scene, force=True)

    concept = generate_scene_concept(scene, force=True)
    plan = build_background_plan(scene, force=True)
    html_path = write_background_review_html(scene, force=True)

    assert Path(concept["image"]).exists()
    assert (scene / "background_plan.json").exists()
    assert html_path.exists()
    assert plan["kind"] == "background_plan"
    assert any(item["kind"] == "base_terrain" for item in plan["review_items"])
    assert "Background Tile Review" in html_path.read_text(encoding="utf-8")

    plan["review_items"][0]["method"] = "extract_from_concept"
    plan["review_items"][0]["crop_rect"] = [0, 0, 128, 128]
    (scene / "background_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    written = extract_background_tiles(scene, force=True)

    assert written == [plan["review_items"][0]["asset_id"]]
    assert (scene / "background_tiles" / f"{written[0]}.png").exists()


def test_scene_full_concept_background_covers_background_tiles_and_renders_preview():
    scene = copy_rice_scene("full_concept_background")
    build_scene_map(scene, force=True)
    generate_scene_concept(scene, force=True)
    plan = build_background_plan(scene, force=True)
    plan["background_image"]["method"] = "use_full_concept"
    plan["background_image"]["status"] = "reviewed"
    for item in plan["review_items"]:
        item["method"] = "ignore"
        item["status"] = "reviewed"
    (scene / "background_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    written = extract_background_tiles(scene, force=True)
    generated = generate_scene_images(scene, force=True)
    manifest = pack_scene(scene, force=True)
    applied = read_json(scene / "final" / "map_data_applied.json")
    mappings = {item["target_id"]: item for item in manifest["mappings"]}

    assert written == ["background_image"]
    assert generated == ["scarecrow_01"]
    assert manifest["metadata"]["background_source"] == "background_image"
    assert manifest["metadata"]["failed_count"] == 0
    assert mappings["wheat_field_01"]["status"] == "covered_by_full_background"
    assert mappings["road_cross_01_road_center_01"]["status"] == "covered_by_full_background"
    assert set(applied["layers"]["terrain"]) == {0}
    assert set(applied["layers"]["path"]) == {0}

    from PIL import Image

    with Image.open(scene / "final" / "preview_applied.png").convert("RGB") as preview:
        assert preview.getpixel((10, 10)) != (0, 0, 0)


def test_scene_background_plan_builds_tile_groups():
    scene = copy_rice_scene("background_tile_groups")
    build_scene_map(scene, force=True)

    generate_scene_concept(scene, force=True)
    plan = build_background_plan(scene, force=True)

    groups = {group["group_id"]: group for group in plan["tile_groups"]}
    assert "wheat_field" in groups
    assert "road_cross_01_tiles" in groups
    assert "oval_track_01_tiles" in groups
    assert groups["wheat_field"]["members"][0]["role"] == "center"
    road_roles = {member["role"] for member in groups["road_cross_01_tiles"]["members"]}
    assert {"center", "edge_top", "edge_bottom", "edge_left", "edge_right"} <= road_roles
    assert any(item.get("tile_group_id") == "road_cross_01_tiles" for item in plan["review_items"])


def test_scene_background_assets_regenerate_tile_family_sheet():
    scene = copy_rice_scene("background_tile_family_regenerate")
    build_scene_map(scene, force=True)
    generate_scene_concept(scene, force=True)
    plan = build_background_plan(scene, force=True)

    for item in plan["review_items"]:
        if item.get("composite_id") == "road_cross_01":
            item["method"] = "regenerate"
            item["status"] = "reviewed"
    (scene / "background_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    written = extract_background_tiles(scene, force=True)

    assert "road_cross_01_road_center" in written
    assert "road_cross_01_road_edge_top" in written
    assert (scene / "background_tiles" / "_group_road_cross_01_tiles.png").exists()
    metadata = read_json(scene / "background_tiles" / "road_cross_01_road_center.json")
    assert metadata["source"] == "background_tile_group"
    assert metadata["group_id"] == "road_cross_01_tiles"

    generate_scene_images(scene, force=True, target="scarecrow_01")
    manifest = pack_scene(scene, force=True)
    mappings = {item["target_id"]: item for item in manifest["mappings"]}
    assert mappings["road_cross_01_road_center_01"]["asset_source"] == "background_tiles"


def test_background_concept_prompt_is_tile_extraction_friendly():
    scene = copy_rice_scene("concept_prompt_rice")
    prompt = build_background_concept_prompt(scene)

    assert "Tile extraction requirements:" in prompt
    assert "64x64px crop grid" in prompt
    assert "Do not place important boundaries halfway through a crop cell" in prompt
    assert "road_cross_01:road_center" in prompt
    assert "oval_track_01:track_curve_top_left" in prompt
