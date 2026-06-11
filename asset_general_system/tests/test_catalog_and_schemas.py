import json
from pathlib import Path

from generator.assets import load_asset_catalog


def test_default_asset_catalog_loads_tiles():
    catalog = load_asset_catalog()

    assert catalog["tileset_id"] == "default_rpg_32"
    names = {tile["name"] for tile in catalog["tiles"]}
    assert {"grass", "water", "dirt_road", "tree", "door"} <= names


def test_protocol_schema_files_exist_and_are_json():
    root = Path(__file__).resolve().parents[1]

    for filename in [
        "rpg_map_spec.schema.json",
        "tilemap_data.schema.json",
        "asset_catalog.schema.json",
        "editor_state.schema.json",
        "scene_map_spec.schema.json",
        "scene_style_profile.schema.json",
        "scene_entities.schema.json",
        "scene_prompts.schema.json",
        "background_plan.schema.json",
        "tilemap_blueprint.schema.json",
        "tile_family_plan.schema.json",
        "pixellab_tileset_manifest.schema.json",
        "tile_candidates.schema.json",
        "tilemap_mapping.schema.json",
        "art_manifest.schema.json",
        "progress.schema.json",
    ]:
        data = json.loads((root / "specs" / filename).read_text(encoding="utf-8"))
        assert data["$schema"].startswith("https://json-schema.org/")
        assert data["type"] == "object"
        assert data["properties"]
