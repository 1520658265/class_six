from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generator.config import TILE_ID_BY_NAME
from generator.export import GodotExporter
from generator.models import TilemapData
from generator.models.base import read_json, write_json, write_model_json
from generator.render import PreviewRenderer

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress
from .progress import utc_now


@dataclass(frozen=True)
class AssetSource:
    path: Path
    kind: str


def pack_scene(scene_dir: str | Path, force: bool = False, resource_base: str | None = None) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.manifest.exists() and not force:
        return read_json(paths.manifest)
    mark_in_progress(paths.root, "7_pack")
    tilemap = TilemapData.model_validate(read_json(paths.map_data))
    art_request = read_json(paths.art_request)
    entities = read_json(paths.entities) if paths.entities.exists() else {"entities": []}
    entity_by_id = {item.get("target_id"): item for item in entities.get("entities", [])}
    paths.final_dir.mkdir(parents=True, exist_ok=True)
    sprites_dir = paths.final_dir / "sprites"
    sprites_dir.mkdir(parents=True, exist_ok=True)
    tilesets_dir = paths.final_dir / "tilesets"
    tilesets_dir.mkdir(parents=True, exist_ok=True)
    mappings = []

    objects_by_id = {obj.id: obj for obj in tilemap.objects}
    slice_assets = _collect_composite_slice_assets(tilemap)
    uses_full_background = _uses_full_background(paths)
    generated_assets: set[str] = set()
    for request_obj in art_request.get("objects", []):
        target_id = request_obj["id"]
        if _is_base_terrain_covered_by_full_background(uses_full_background, request_obj):
            source = None
            covered_by_full_background = True
        else:
            source = _asset_source(paths, target_id)
            covered_by_full_background = False
        final_name = f"{target_id}.png"
        final_png = sprites_dir / final_name
        status = "covered_by_full_background" if covered_by_full_background else "missing"
        if source:
            shutil.copyfile(source.path, final_png)
            status = "generated"
            generated_assets.add(target_id)
            obj = objects_by_id.get(target_id)
            if obj and not bool(obj.properties.get("is_asset_target")):
                obj.sprite_ref = target_id
                obj.sprite_path = f"sprites/{final_name}"
                text = request_obj.get("text") or entity_by_id.get(target_id, {}).get("text")
                if text is not None:
                    obj.properties["text"] = text
        mappings.append(
            {
                "target_id": target_id,
                "sprite_path": f"images/{final_name}",
                "final_sprite_path": f"sprites/{final_name}",
                "footprint": request_obj.get("footprint"),
                "source_canvas": request_obj.get("source_canvas"),
                "anchor": request_obj.get("anchor"),
                "category": request_obj.get("category"),
                "status": status,
                "asset_source": source.kind if source else None,
            }
        )

    for asset_id, obj in slice_assets.items():
        covered_by_full_background = uses_full_background
        source = None if covered_by_full_background else _asset_source(paths, asset_id)
        final_name = f"{asset_id}.png"
        final_png = sprites_dir / final_name
        status = "covered_by_full_background" if covered_by_full_background else "missing"
        if source:
            shutil.copyfile(source.path, final_png)
            status = "generated"
            generated_assets.add(asset_id)
        mappings.append(
            {
                "target_id": asset_id,
                "sprite_path": f"images/{final_name}",
                "final_sprite_path": f"sprites/{final_name}",
                "footprint": [obj.width, obj.height],
                "source_canvas": list((obj.properties or {}).get("source_canvas") or []),
                "anchor": (obj.properties or {}).get("anchor"),
                "category": "composite_slice",
                "source_generation_id": (obj.properties or {}).get("source_generation_id"),
                "status": status,
                "asset_source": source.kind if source else None,
            }
        )

    for obj in tilemap.objects:
        props = obj.properties or {}
        if bool(props.get("is_asset_target")):
            continue
        if str(props.get("render_mode") or "") == "tile_layer":
            continue
        asset_id = str(props.get("asset_id") or obj.id)
        if asset_id not in generated_assets:
            continue
        obj.sprite_ref = asset_id
        obj.sprite_path = f"sprites/{asset_id}.png"
        text = props.get("text") or entity_by_id.get(asset_id, {}).get("text")
        if text is not None:
            obj.properties["text"] = text

    _apply_generated_base_terrain_tile(paths, tilemap)
    _apply_composite_slices_to_tileset(paths, tilemap, generated_assets)
    background_source = _apply_full_background_image(paths, tilemap)

    manifest = {
        "version": "1.0",
        "scene": art_request.get("description") or paths.root.name,
        "generated_at": utc_now(),
        "mappings": mappings,
        "metadata": {
            "total_objects": len(mappings),
            "generated_count": sum(1 for item in mappings if item["status"] == "generated"),
            "fulfilled_count": sum(1 for item in mappings if _is_fulfilled_mapping(item)),
            "failed_count": sum(1 for item in mappings if not _is_fulfilled_mapping(item)),
            "map_instance_count": sum(1 for obj in tilemap.objects if not bool(obj.properties.get("is_asset_target"))),
            "background_source": background_source,
        },
    }
    write_json(paths.manifest, manifest)
    write_model_json(paths.final_dir / "map_data_applied.json", tilemap)
    GodotExporter().export(tilemap, paths.final_dir, "scene")
    _render_applied_previews(paths.final_dir, tilemap)
    mark_completed(paths.root, "7_pack")
    return manifest


def _asset_source(paths, asset_id: str) -> AssetSource | None:
    candidates = _asset_source_candidates(asset_id)
    for candidate_id in candidates:
        reviewed = paths.background_tiles_dir / f"{candidate_id}.png"
        if reviewed.exists():
            return AssetSource(reviewed, "background_tiles")
    for candidate_id in candidates:
        generated = paths.images_dir / f"{candidate_id}.png"
        if generated.exists():
            return AssetSource(generated, "images")
    return None


def _asset_source_candidates(asset_id: str) -> list[str]:
    candidates = [asset_id]
    generic_part_id = re.sub(r"_\d{2}$", "", asset_id)
    if generic_part_id != asset_id:
        candidates.append(generic_part_id)
    return candidates


def _is_fulfilled_mapping(item: dict[str, Any]) -> bool:
    return item.get("status") in {"generated", "covered_by_full_background"}


def _is_base_terrain_covered_by_full_background(uses_full_background: bool, request_obj: dict[str, Any]) -> bool:
    if request_obj.get("asset_role") != "base_terrain":
        return False
    return uses_full_background


def _uses_full_background(paths) -> bool:
    plan_path = paths.background_plan
    if not plan_path.exists():
        return False
    try:
        plan = read_json(plan_path)
    except Exception:
        return False
    background = plan.get("background_image")
    return isinstance(background, dict) and background.get("method") == "use_full_concept"


def _relative_to_scene(scene_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(scene_dir)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _apply_full_background_image(paths, tilemap: TilemapData) -> str | None:
    background_plan = paths.background_plan
    if not background_plan.exists():
        return None
    plan = read_json(background_plan)
    background = plan.get("background_image")
    if not isinstance(background, dict) or background.get("method") != "use_full_concept":
        return None
    source = paths.root / str(background.get("output_path") or "background/background.png")
    if not source.exists():
        return None
    final_rel = "background/background.png"
    final_path = paths.final_dir / final_rel
    final_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, final_path)
    tilemap.metadata["background_image"] = {
        "path": final_rel,
        "source": _relative_to_scene(paths.root, source),
        "mode": "full_image",
        "source_size": _image_size(source),
        "target_size": [tilemap.map.width * tilemap.map.tile_width, tilemap.map.height * tilemap.map.tile_height],
    }
    for layer_name in ("terrain", "path", "building", "decoration"):
        if layer_name in tilemap.layers:
            tilemap.layers[layer_name] = [0] * (tilemap.map.width * tilemap.map.height)
    return "background_image"


def _image_size(path: Path) -> list[int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as image:
            return [int(image.width), int(image.height)]
    except Exception:
        return None


def _apply_generated_base_terrain_tile(paths, tilemap: TilemapData) -> None:
    if _uses_full_background(paths):
        return
    base_terrain = tilemap.metadata.get("base_terrain")
    if not isinstance(base_terrain, dict):
        return
    tile_name = base_terrain.get("tile")
    object_key = base_terrain.get("object_key")
    if not isinstance(tile_name, str) or not isinstance(object_key, str):
        return
    tile_id = TILE_ID_BY_NAME.get(tile_name)
    if not tile_id:
        return
    source = _asset_source(paths, f"{object_key}_01")
    if not source:
        return
    try:
        from PIL import Image
    except ImportError:
        return

    scene_tileset = paths.final_dir / "tilesets" / "scene_tileset.png"
    default_tileset = paths.root / "tilesets" / "default_rpg_32.png"
    PreviewRenderer().ensure_tileset_png(default_tileset, tilemap.map.tile_width, tilemap.map.tile_height)
    base = Image.open(default_tileset).convert("RGBA")
    tile_w = tilemap.map.tile_width
    tile_h = tilemap.map.tile_height
    index = tile_id - 1
    x = (index % tilemap.tileset.columns) * tile_w
    y = (index // tilemap.tileset.columns) * tile_h
    if y + tile_h > base.height:
        rows = (index // tilemap.tileset.columns) + 1
        expanded = Image.new("RGBA", (base.width, rows * tile_h), (0, 0, 0, 0))
        expanded.paste(base, (0, 0))
        base.close()
        base = expanded
    tile = Image.open(source.path).convert("RGBA").resize((tile_w, tile_h), Image.NEAREST)
    base.paste(tile, (x, y), tile)
    base.save(scene_tileset)
    tile.close()
    base.close()
    tilemap.tileset.image = "tilesets/scene_tileset.png"


def _collect_composite_slice_assets(tilemap: TilemapData) -> dict[str, Any]:
    assets: dict[str, Any] = {}
    for obj in tilemap.objects:
        props = obj.properties or {}
        if str(props.get("asset_role") or "") != "composite_slice":
            continue
        asset_id = str(props.get("asset_id") or obj.id)
        assets[asset_id] = obj
    return assets


def _apply_composite_slices_to_tileset(paths, tilemap: TilemapData, generated_assets: set[str]) -> None:
    try:
        from PIL import Image
    except ImportError:
        return

    scene_tileset = paths.final_dir / "tilesets" / "scene_tileset.png"
    if scene_tileset.exists():
        base = Image.open(scene_tileset).convert("RGBA")
    else:
        default_tileset = paths.root / "tilesets" / "default_rpg_32.png"
        PreviewRenderer().ensure_tileset_png(default_tileset, tilemap.map.tile_width, tilemap.map.tile_height)
        base = Image.open(default_tileset).convert("RGBA")

    tile_w = tilemap.map.tile_width
    tile_h = tilemap.map.tile_height
    columns = tilemap.tileset.columns
    next_tile_id = _tileset_capacity(base, columns, tile_w, tile_h) + 1
    asset_to_tile_id: dict[str, int] = {}

    for obj in tilemap.objects:
        props = obj.properties or {}
        if str(props.get("asset_role") or "") != "composite_slice":
            continue
        asset_id = str(props.get("asset_id") or obj.id)
        if asset_id not in generated_assets:
            continue
        if asset_id not in asset_to_tile_id:
            source = _asset_source(paths, asset_id)
            if not source:
                continue
            base, tile_id = _append_tile(base, source.path, next_tile_id, columns, tile_w, tile_h)
            asset_to_tile_id[asset_id] = tile_id
            next_tile_id = tile_id + 1
        layer_name = str(props.get("target_layer") or "path")
        layer = tilemap.layers.get(layer_name)
        if layer is None:
            layer = [0] * (tilemap.map.width * tilemap.map.height)
            tilemap.layers[layer_name] = layer
        layer[obj.y * tilemap.map.width + obj.x] = asset_to_tile_id[asset_id]

    if asset_to_tile_id:
        base.save(scene_tileset)
        tilemap.tileset.image = "tilesets/scene_tileset.png"
        tilemap.tileset.tile_width = tile_w
        tilemap.tileset.tile_height = tile_h
        tilemap.tileset.tile_count = max(tilemap.tileset.tile_count, next_tile_id - 1)
    base.close()


def _tileset_capacity(image, columns: int, tile_w: int, tile_h: int) -> int:
    return max(0, columns * (image.height // tile_h))


def _append_tile(base, source_png: Path, tile_id: int, columns: int, tile_w: int, tile_h: int):
    from PIL import Image

    index = tile_id - 1
    x = (index % columns) * tile_w
    y = (index // columns) * tile_h
    if y + tile_h > base.height:
        rows = (index // columns) + 1
        expanded = Image.new("RGBA", (columns * tile_w, rows * tile_h), (0, 0, 0, 0))
        expanded.paste(base, (0, 0))
        base.close()
        base = expanded
    tile = Image.open(source_png).convert("RGBA").resize((tile_w, tile_h), Image.NEAREST)
    base.paste(tile, (x, y), tile)
    tile.close()
    return base, tile_id


def _render_applied_previews(final_dir: Path, tilemap: TilemapData) -> None:
    renderer = PreviewRenderer()
    original_cwd = Path.cwd()
    try:
        os.chdir(final_dir)
        renderer.render(tilemap, "preview_applied.png")
        renderer.render(tilemap, "preview_applied_debug.png", debug=True)
    finally:
        os.chdir(original_cwd)
