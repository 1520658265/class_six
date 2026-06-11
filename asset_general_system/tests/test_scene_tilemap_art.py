from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from PIL import Image

from generator.models.base import read_json
from generator.scene.map_build import build_scene_map
from generator.scene.tilemap_art import (
    PIXELLAB_DETAIL,
    build_tile_candidates,
    build_tile_family_plan,
    build_tilemap_blueprint,
    build_tilemap_mapping,
    export_tilemap_to_tiled,
    generate_pixellab_tilesets,
)
from generator.scene.validation import validate_scene_file
from scene_fixtures import _write_json, _write_text


ROOT = Path(__file__).resolve().parents[1]
TEST_WORK = ROOT / "tmp" / "test_scene_tilemap_art"


def _scene_dir() -> Path:
    scene = TEST_WORK / f"tilemap_art_{os.getpid()}_{uuid.uuid4().hex}"
    scene.mkdir(parents=True, exist_ok=True)
    return scene


def _write_tile(path: Path, color: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (64, 64), color).save(path)


def _write_scene(scene: Path) -> None:
    _write_text(scene / "scene.md", "campus tilemap art test")
    _write_json(
        scene / "map_spec.json",
        {
            "version": "1.0.0",
            "id": "tilemap_art_test",
            "title": "tilemap art test",
            "theme": "school_campus",
            "art_tile_size": 64,
            "map": {"width": 16, "height": 16, "tile_width": 64, "tile_height": 64, "orientation": "orthogonal"},
            "regions": [],
            "paths": [],
            "objects": [],
            "base_terrain": {
                "object_key": "campus_lawn",
                "display_name": "campus lawn",
                "tile": "grass",
                "source_canvas": [64, 64],
            },
            "composites": [
                {
                    "id": "campus_walkway_01",
                    "type": "campus_walkway",
                    "placement": "center",
                    "display_name": "campus walkway",
                    "footprint": [3, 1],
                    "parts": [
                        {
                            "key": "walkway_edge_left",
                            "display_name": "left edge",
                            "source_canvas": [64, 64],
                            "blocking": False,
                            "properties": {"target_layer": "path", "tile_role": "edge_left"},
                        },
                        {
                            "key": "walkway_center",
                            "display_name": "center",
                            "source_canvas": [64, 64],
                            "blocking": False,
                            "properties": {"target_layer": "path", "tile_role": "center"},
                        },
                        {
                            "key": "walkway_edge_right",
                            "display_name": "right edge",
                            "source_canvas": [64, 64],
                            "blocking": False,
                            "properties": {"target_layer": "path", "tile_role": "edge_right"},
                        },
                    ],
                    "layout": [
                        {"part": "walkway_edge_left", "x": 0, "y": 0},
                        {"part": "walkway_center", "x": 1, "y": 0},
                        {"part": "walkway_edge_right", "x": 2, "y": 0},
                    ],
                    "properties": {"origin": [6, 8]},
                }
            ],
            "tile_groups": [
                {
                    "group_id": "campus_lawn_tiles",
                    "kind": "material_group",
                    "generation_mode": "sprite_sheet",
                    "tile_size": [64, 64],
                    "members": [
                        {"tile_id": "campus_lawn_center", "role": "center", "source_ref": "campus_lawn_01"}
                    ],
                },
                {
                    "group_id": "campus_walkway_tiles",
                    "kind": "material_group",
                    "generation_mode": "sprite_sheet",
                    "tile_size": [64, 64],
                    "members": [
                        {"tile_id": "walkway_edge_left_tile", "role": "edge_left", "source_ref": "campus_walkway_01:walkway_edge_left"},
                        {"tile_id": "walkway_center_tile", "role": "center", "source_ref": "campus_walkway_01:walkway_center"},
                        {"tile_id": "walkway_edge_right_tile", "role": "edge_right", "source_ref": "campus_walkway_01:walkway_edge_right"},
                    ],
                },
            ],
            "entities": [],
            "constraints": {
                "walkable_spawn": True,
                "connect_key_regions": True,
                "no_blocked_doors": True,
                "objects_require_walkable_neighbor": True,
            },
            "seed": 11,
            "tileset_id": "default_rpg_32",
        },
    )


def test_scene_tilemap_art_resolves_source_refs_and_exports_tiled():
    scene = _scene_dir()
    _write_scene(scene)
    build_scene_map(scene, force=True)

    _write_tile(scene / "background_tiles" / "campus_lawn_01.png", (60, 190, 90, 255))
    _write_tile(scene / "background_tiles" / "campus_walkway_01_walkway_edge_left.png", (165, 130, 90, 255))
    _write_tile(scene / "background_tiles" / "campus_walkway_01_walkway_center.png", (185, 150, 105, 255))
    _write_tile(scene / "background_tiles" / "campus_walkway_01_walkway_edge_right.png", (165, 130, 90, 255))

    blueprint = build_tilemap_blueprint(scene, force=True)
    assert "campus_walkway" in blueprint["materials"]

    plan = build_tile_family_plan(scene, force=True)
    assert plan["source_tile_size"] == [32, 32]
    assert plan["pixellab_defaults"]["target_tile_size"] == [64, 64]
    assert plan["pixellab_defaults"]["detail"] == PIXELLAB_DETAIL
    assert "large clear shapes for 32px source tiles" in plan["pixellab_defaults"]["style_contract"]
    assert {group["material"] for group in plan["groups"] if group["kind"] == "material_group"} == {"campus_lawn", "campus_walkway"}

    manifest = generate_pixellab_tilesets(scene, run_api=False, force=True)
    assert manifest["run_api"] is False
    assert not [issue for issue in validate_scene_file(scene, "tilemap-blueprint") if issue.severity == "error"]
    assert not [issue for issue in validate_scene_file(scene, "tile-family-plan") if issue.severity == "error"]
    assert not [issue for issue in validate_scene_file(scene, "pixellab-tilesets") if issue.severity == "error"]

    candidates = build_tile_candidates(scene, force=True)
    by_id = {item["candidate_id"]: item for item in candidates["candidates"]}
    assert by_id["walkway_center_tile"]["status"] == "ready"
    assert by_id["walkway_center_tile"]["source_ref"] == "campus_walkway_01:walkway_center"
    assert by_id["walkway_center_tile"]["source_path"] == "background_tiles/campus_walkway_01_walkway_center.png"
    assert by_id["walkway_center_tile"]["material"] == "campus_walkway"

    mapping = build_tilemap_mapping(scene, force=True)
    assert mapping["tile_ids"]
    assert not mapping["issues"]
    assert (scene / "tilemap_mapping_preview.png").exists()
    assert not [issue for issue in validate_scene_file(scene, "tile-candidates") if issue.severity == "error"]
    assert not [issue for issue in validate_scene_file(scene, "tilemap-mapping") if issue.severity == "error"]

    exported = export_tilemap_to_tiled(scene, force=True)
    tmj = read_json(exported["tmj"])
    assert tmj["tilesets"][0]["image"] == "tile_candidates_tileset.png"
    assert Path(exported["tileset"]).exists()

    path_layer = next(layer for layer in tmj["layers"] if layer["name"] == "path")
    assert max(path_layer["data"]) > 0
