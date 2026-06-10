"""
Phase 4 integration tests.

These tests verify that a tilemap can carry externally generated sprite
references through Tiled export and preview rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.export.tiled_exporter import TiledExporter
from generator.models import MapInfo, ObjectData, TilemapData, TilesetInfo
from generator.render.preview_renderer import PreviewRenderer


def create_test_tilemap() -> TilemapData:
    width, height = 32, 32
    size = width * height
    return TilemapData(
        map=MapInfo(width=width, height=height),
        tileset=TilesetInfo(),
        layers={
            "terrain": [1] * size,
            "path": [0] * size,
            "building": [0] * size,
            "decoration": [0] * size,
            "collision": [0] * size,
        },
        metadata={"theme": "forest_village", "seed": 42},
    )


def _create_tilemap_with_external_art_refs() -> TilemapData:
    tilemap = create_test_tilemap()
    tilemap.objects.extend(
        [
            ObjectData(
                id="tree_01",
                type="tree_oak",
                x=5,
                y=5,
                width=1,
                height=2,
                sprite_ref="tree_oak_1000",
                sprite_path="art/objects/tree_oak_1000.png",
            ),
            ObjectData(
                id="rock_01",
                type="rock_small",
                x=10,
                y=10,
                sprite_ref="rock_small_1001",
                sprite_path="art/objects/rock_small_1001.png",
            ),
            ObjectData(
                id="rock_02",
                type="rock_small",
                x=12,
                y=10,
                sprite_ref="rock_small_1001",
                sprite_path="art/objects/rock_small_1001.png",
            ),
            ObjectData(
                id="chest_01",
                type="chest",
                x=20,
                y=15,
                sprite_ref="chest_1002",
                sprite_path="art/objects/chest_1002.png",
            ),
            ObjectData(
                id="unknown_01",
                type="mystery_artifact",
                x=25,
                y=25,
            ),
        ]
    )
    return tilemap


def test_tilemap_can_hold_external_art_references():
    tilemap = _create_tilemap_with_external_art_refs()

    assert len(tilemap.objects) == 5
    assert sum(1 for obj in tilemap.objects if obj.sprite_ref) == 4
    assert next(obj for obj in tilemap.objects if obj.id == "unknown_01").sprite_ref is None


@pytest.fixture
def tilemap() -> TilemapData:
    return _create_tilemap_with_external_art_refs()


def test_tiled_export_contains_sprite_info(tilemap: TilemapData, tmp_path: Path):
    exporter = TiledExporter()
    output_path = tmp_path / "output" / "map.tiled.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = exporter.export(tilemap, output_path)

    objects_layer = next((layer for layer in data["layers"] if layer.get("name") == "objects"), None)

    assert objects_layer is not None
    assert objects_layer["type"] == "objectgroup"
    assert len(objects_layer["objects"]) == len(tilemap.objects)

    tree_obj = next(obj for obj in objects_layer["objects"] if obj["name"] == "tree_01")
    tree_props = {prop["name"]: prop["value"] for prop in tree_obj["properties"]}
    assert "sprite_ref" in tree_props
    assert "sprite_path" in tree_props

    unknown_obj = next(obj for obj in objects_layer["objects"] if obj["name"] == "unknown_01")
    unknown_props = {prop["name"]: prop["value"] for prop in unknown_obj["properties"]}
    assert "sprite_ref" not in unknown_props
    assert "sprite_path" not in unknown_props

    assert tree_obj["width"] == tilemap.map.tile_width
    assert tree_obj["height"] == tilemap.map.tile_height * 2

    with open(output_path, "r", encoding="utf-8") as file:
        loaded = json.load(file)
    assert loaded["type"] == "map"


def test_preview_render_with_sprites(tilemap: TilemapData, tmp_path: Path):
    renderer = PreviewRenderer()
    preview_path = tmp_path / "output" / "preview.png"
    renderer.render(tilemap, preview_path)

    assert preview_path.exists()

    from PIL import Image

    with Image.open(preview_path) as img:
        expected_w = tilemap.map.width * tilemap.map.tile_width
        expected_h = tilemap.map.height * tilemap.map.tile_height
        assert img.size == (expected_w, expected_h)
        pixels = list(img.getdata())

    non_black = sum(1 for pixel in pixels if pixel != (0, 0, 0))
    assert non_black > 0


def test_preview_render_debug_mode(tilemap: TilemapData, tmp_path: Path):
    renderer = PreviewRenderer()
    debug_path = tmp_path / "output" / "preview_debug.png"
    renderer.render(tilemap, debug_path, debug=True)

    assert debug_path.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
