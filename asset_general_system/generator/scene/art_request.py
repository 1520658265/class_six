from __future__ import annotations

from typing import Any

from generator.models import TilemapData

from .constants import CATEGORY_DEFAULTS

DEFAULT_ART_TILE_SIZE = 64


def build_scene_art_request(tilemap: TilemapData, map_spec: dict[str, Any], description: str = "") -> dict[str, Any]:
    tile_w, tile_h = tilemap.map.tile_width, tilemap.map.tile_height
    art_tile_size = int(map_spec.get("art_tile_size") or map_spec.get("asset_tile_size") or max(tile_w, tile_h, DEFAULT_ART_TILE_SIZE))
    art_objects = [
        _object_item(obj, tile_w, tile_h, art_tile_size)
        for obj in tilemap.objects
        if _is_art_request_target(obj)
    ]
    return {
        "version": "1.0",
        "kind": "logical_map_art_request",
        "description": description,
        "theme": str(tilemap.metadata.get("theme", "")),
        "seed": int(tilemap.metadata.get("seed", 0) or 0),
        "map_size": [tilemap.map.width, tilemap.map.height],
        "tile_size": [tile_w, tile_h],
        "art_tile_size": [art_tile_size, art_tile_size],
        "canvas_size": [tilemap.map.width * tile_w, tilemap.map.height * tile_h],
        "tileset": {
            "id": tilemap.tileset.id,
            "image": tilemap.tileset.image,
            "columns": tilemap.tileset.columns,
            "tile_count": tilemap.tileset.tile_count,
        },
        "layers": {
            name: {
                "semantic": name,
                "width": tilemap.map.width,
                "height": tilemap.map.height,
                "visible_by_default": name != "collision",
            }
            for name in ("terrain", "path", "building", "decoration", "collision")
        },
        "generation_targets": _generation_targets(tilemap, map_spec, art_tile_size),
        "regions": [
            {
                "id": region.id,
                "type": region.type,
                "bounds": region.bounds,
                "pixel_bounds": [
                    region.bounds[0] * tile_w,
                    region.bounds[1] * tile_h,
                    region.bounds[2] * tile_w,
                    region.bounds[3] * tile_h,
                ],
                "center": region.center,
                "access": region.access,
                "priority": region.priority,
            }
            for region in tilemap.regions
        ],
        "objects": art_objects,
        "events": [
            {
                "id": event.id,
                "type": event.type,
                "x": event.x,
                "y": event.y,
                "pixel_position": [event.x * tile_w, event.y * tile_h],
                "properties": dict(event.properties or {}),
            }
            for event in tilemap.events
        ],
    }


def _is_art_request_target(obj) -> bool:
    props = dict(obj.properties or {})
    if obj.type == "door":
        return False
    if props.get("is_map_instance") is True:
        return False
    if props.get("is_asset_target") is False:
        return False
    return True


def _object_item(obj, tile_w: int, tile_h: int, art_tile_size: int) -> dict[str, Any]:
    props = dict(obj.properties or {})
    category = str(props.get("category") or obj.type)
    default = CATEGORY_DEFAULTS.get(category, {})
    anchor = str(props.get("anchor") or default.get("anchor") or "center")
    source_canvas = props.get("source_canvas")
    if not isinstance(source_canvas, list):
        source_canvas = [obj.width * tile_w, obj.height * tile_h]
    if category == "terrain_tile":
        source_canvas = [art_tile_size, art_tile_size]
    return {
        "id": obj.id,
        "asset_id": props.get("asset_id") or obj.id,
        "asset_role": props.get("asset_role"),
        "type": obj.type,
        "display_name": str(props.get("display_name") or props.get("label") or obj.type),
        "object_key": props.get("object_key"),
        "category": category,
        "x": obj.x,
        "y": obj.y,
        "footprint": [obj.width, obj.height],
        "pixel_bounds": [obj.x * tile_w, obj.y * tile_h, obj.width * tile_w, obj.height * tile_h],
        "runtime_size": [obj.width * tile_w, obj.height * tile_h],
        "source_canvas": source_canvas,
        "placement_zone": props.get("placement"),
        "relative_position": props.get("source_clause"),
        "facing": props.get("facing"),
        "anchor": anchor,
        "blocking": bool(props.get("blocking", False)),
        "attached_to": props.get("attached_to"),
        "text": props.get("text"),
        "activity": props.get("activity"),
        "source_clause": props.get("source_clause"),
        "properties": props,
    }


def _generation_targets(tilemap: TilemapData, map_spec: dict[str, Any], art_tile_size: int) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for comp in map_spec.get("composites", []) or []:
        if not isinstance(comp, dict):
            continue
        comp_id = str(comp["id"])
        footprint = comp.get("footprint") or [1, 1]
        width, height = int(footprint[0]), int(footprint[1])
        layout = [dict(cell) for cell in comp.get("layout", []) if isinstance(cell, dict)]
        parts = [dict(part) for part in comp.get("parts", []) if isinstance(part, dict)]
        counters: dict[str, int] = {}
        slice_outputs = []
        for cell in layout:
            part = str(cell.get("part"))
            counters[part] = counters.get(part, 0) + 1
            x = int(cell.get("x", 0))
            y = int(cell.get("y", 0))
            slice_outputs.append(
                {
                    "id": f"{comp_id}_{part}_{counters[part]:02d}",
                    "part": part,
                    "x": x,
                    "y": y,
                    "source_rect": [x * art_tile_size, y * art_tile_size, art_tile_size, art_tile_size],
                }
            )
        targets.append(
            {
                "id": f"{comp_id}_source",
                "asset_role": "composite_source",
                "category": "composite_source",
                "composite_id": comp_id,
                "composite_type": comp.get("type"),
                "display_name": comp.get("display_name") or comp_id,
                "source_clause": comp.get("source_clause"),
                "footprint": [width, height],
                "source_canvas": [width * art_tile_size, height * art_tile_size],
                "runtime_size": [width * tilemap.map.tile_width, height * tilemap.map.tile_height],
                "tile_size": [tilemap.map.tile_width, tilemap.map.tile_height],
                "art_tile_size": [art_tile_size, art_tile_size],
                "layout": layout,
                "parts": parts,
                "slice_outputs": slice_outputs,
                "properties": dict(comp.get("properties") or {}),
            }
        )
    return targets
