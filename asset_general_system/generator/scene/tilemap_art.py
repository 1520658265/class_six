from __future__ import annotations

import base64
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from generator.export import TiledExporter
from generator.models import MapInfo, TilemapData, TilesetInfo
from generator.models.base import read_json, write_json
from generator.render import PreviewRenderer

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress, utc_now


PIXELLAB_SOURCE_TILE_SIZE = 32
PROJECT_TILE_SIZE = 64
PIXELLAB_DETAIL = "highly detailed"
PIXELLAB_STYLE_SUFFIX = (
    "cute charming RPG pixel art, rich colorful harmonious palette, bright readable colors, "
    "large clear shapes for 32px source tiles, avoid muddy colors, avoid micro-noise, "
    "opaque terrain pixels fill each tile, no labels, no text, no props, no characters"
)

ROLE_CONNECTORS: dict[str, dict[str, str]] = {
    "center": {"n": "same", "e": "same", "s": "same", "w": "same"},
    "center_variant": {"n": "same", "e": "same", "s": "same", "w": "same"},
    "straight_horizontal": {"n": "other", "e": "same", "s": "other", "w": "same"},
    "straight_vertical": {"n": "same", "e": "other", "s": "same", "w": "other"},
    "edge_top": {"n": "other", "e": "same", "s": "same", "w": "same"},
    "edge_bottom": {"n": "same", "e": "same", "s": "other", "w": "same"},
    "edge_left": {"n": "same", "e": "same", "s": "same", "w": "other"},
    "edge_right": {"n": "same", "e": "other", "s": "same", "w": "same"},
    "corner_top_left": {"n": "other", "e": "same", "s": "same", "w": "other"},
    "corner_top_right": {"n": "other", "e": "other", "s": "same", "w": "same"},
    "corner_bottom_left": {"n": "same", "e": "same", "s": "other", "w": "other"},
    "corner_bottom_right": {"n": "same", "e": "other", "s": "other", "w": "same"},
    "curve_top_left": {"n": "other", "e": "same", "s": "same", "w": "other"},
    "curve_top_right": {"n": "other", "e": "other", "s": "same", "w": "same"},
    "curve_bottom_left": {"n": "same", "e": "same", "s": "other", "w": "other"},
    "curve_bottom_right": {"n": "same", "e": "other", "s": "other", "w": "same"},
    "transition_edge_top": {"n": "lower", "e": "upper", "s": "upper", "w": "upper"},
    "transition_edge_bottom": {"n": "upper", "e": "upper", "s": "lower", "w": "upper"},
    "transition_edge_left": {"n": "upper", "e": "upper", "s": "upper", "w": "lower"},
    "transition_edge_right": {"n": "upper", "e": "lower", "s": "upper", "w": "upper"},
    "transition_corner_top_left": {"n": "lower", "e": "upper", "s": "upper", "w": "lower"},
    "transition_corner_top_right": {"n": "lower", "e": "lower", "s": "upper", "w": "upper"},
    "transition_corner_bottom_left": {"n": "upper", "e": "upper", "s": "lower", "w": "lower"},
    "transition_corner_bottom_right": {"n": "upper", "e": "lower", "s": "lower", "w": "upper"},
}

PIXELLAB_CASES = {
    "grass_to_dirt_road": {
        "from": "grass_lawn",
        "to": "dirt_road",
        "lower_description": "green grass lawn terrain, high top-down, rich but readable palette, broad leaf clusters",
        "upper_description": "warm brown rural dirt road terrain, high top-down, ochre and amber color variation, compact earth texture with broad readable patches",
        "transition_description": "natural soft grass edge blending into warm brown dirt road, clear terrain boundary, include subtle gravel and compact soil color variety, no road markings",
    },
    "grass_to_plaza": {
        "from": "grass_lawn",
        "to": "plaza_brick",
        "lower_description": "green grass lawn terrain, high top-down, rich greens, clear broad grass texture",
        "upper_description": "warm light stone plaza tile terrain, high top-down, peach beige and tan stones, readable square paving shapes",
        "transition_description": "clean grass border meeting warm colorful stone plaza paving, crisp material boundary, large readable stone and grass shapes",
    },
    "grass_to_running_track": {
        "from": "grass_lawn",
        "to": "running_track",
        "lower_description": "green sports field grass terrain, high top-down, rich greens, broad readable texture",
        "upper_description": "red-orange running track surface terrain, high top-down, saturated red clay and orange highlights, simple readable lane texture, no lane numbers",
        "transition_description": "clean boundary between green grass and red-orange running track surface, colorful sports field terrain transition only, no complete oval track",
    },
    "grass_to_water": {
        "from": "grass_lawn",
        "to": "water",
        "lower_description": "green grass bank terrain, high top-down, vivid greens and broad readable clusters",
        "upper_description": "clear blue water surface terrain, high top-down, cyan and blue ripples with large readable shapes",
        "transition_description": "natural shoreline transition from colorful grass bank to blue water, clean readable water edge, no bridge, no large rocks",
    },
    "wheat_to_dirt_road": {
        "from": "wheat_field",
        "to": "dirt_road",
        "lower_description": "golden wheat field terrain, high top-down, rich yellow and amber crop bands, broad readable wheat clusters, no scarecrow",
        "upper_description": "warm brown rural dirt road terrain, high top-down, ochre and amber color variation, broad readable dirt patches, subtle gravel and straw flecks",
        "transition_description": "clean edge where golden wheat field meets warm brown dirt road, colorful farm terrain transition only, no fences, no tools",
    },
    "wheat_to_running_track": {
        "from": "wheat_field",
        "to": "running_track",
        "lower_description": "golden wheat field terrain, high top-down, rich yellow and amber crop bands, broad readable wheat clusters, no scarecrow",
        "upper_description": "red-orange rural running track surface, high top-down, saturated clay reds and warm ochre highlights, simple broad lane texture, no lane numbers",
        "transition_description": "clean edge where golden wheat field meets red-orange running track surface, colorful readable boundary, no athletes, no props",
    },
    "campus_lawn_to_stone_walkway": {
        "from": "campus_lawn",
        "to": "stone_walkway",
        "lower_description": "campus lawn terrain, high top-down, bright green grass with tiny color accents and broad readable shapes",
        "upper_description": "gray stone campus walkway terrain, high top-down, cool gray stones with blue and violet color variation, clear large paving shapes",
        "transition_description": "clean campus lawn edge meeting gray stone walkway, colorful but readable terrain boundary",
    },
    "campus_lawn_to_brick_walkway": {
        "from": "campus_lawn",
        "to": "brick_walkway",
        "lower_description": "campus lawn terrain, high top-down, bright green grass with small flower color accents and broad readable shapes",
        "upper_description": "warm red brick campus walkway terrain, high top-down, red orange and tan brick pattern, clear large brick shapes",
        "transition_description": "clean campus lawn edge meeting warm red brick walkway, colorful readable material transition",
    },
    "campus_lawn_to_plaza_brick": {
        "from": "campus_lawn",
        "to": "plaza_brick",
        "lower_description": "campus lawn terrain, high top-down, bright green grass with cheerful color accents and broad readable clusters",
        "upper_description": "warm pale stone and light brick campus plaza terrain, high top-down, peach beige tan stones with subtle red brick accents, large paving shapes",
        "transition_description": "clean campus lawn edge meeting warm stone plaza and light brick paving, readable material boundary, shared school-campus palette",
    },
}

PIXELLAB_ROLE_ORDER = [
    "center",
    "transition_edge_top",
    "transition_edge_right",
    "transition_edge_bottom",
    "transition_edge_left",
    "transition_corner_top_left",
    "transition_corner_top_right",
    "transition_corner_bottom_left",
    "transition_corner_bottom_right",
]


def build_tilemap_blueprint(scene_dir: str | Path, force: bool = False) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.tilemap_blueprint.exists() and not force:
        return read_json(paths.tilemap_blueprint)
    if not paths.map_data.exists():
        raise FileNotFoundError(f"map_data.json missing; run scene-map-build first: {paths.map_data}")
    mark_in_progress(paths.root, "tilemap_blueprint")
    map_data = read_json(paths.map_data)
    map_spec = read_json(paths.map_spec)
    width = int(map_data["map"]["width"])
    height = int(map_data["map"]["height"])
    tile_size = [int(map_data["map"]["tile_width"]), int(map_data["map"]["tile_height"])]
    base_material = _base_material(map_spec)
    cells = [
        {
            "x": x,
            "y": y,
            "layer": "terrain",
            "material": base_material,
            "role": "center",
            "reuse": "variant_tile",
            "source_reason": "base_terrain fill",
        }
        for y in range(height)
        for x in range(width)
    ]
    for obj in map_data.get("objects", []):
        props = obj.get("properties") or {}
        if props.get("render_mode") != "tile_layer":
            continue
        material = _material_for_tile_instance(obj)
        role = str(props.get("tile_role") or _role_from_part_key(str(props.get("object_key") or obj.get("id") or "")))
        cells.append(
            {
                "x": int(obj["x"]),
                "y": int(obj["y"]),
                "layer": str(props.get("target_layer") or "path"),
                "material": material,
                "role": role,
                "reuse": "reusable_tile",
                "source_reason": f"{props.get('composite_id')}:{props.get('object_key')}",
                "object_id": obj.get("id"),
                "asset_id": props.get("asset_id"),
                "source_generation_id": props.get("source_generation_id"),
                "connection": _connection_signature(role, material, base_material),
            }
        )

    blueprint = {
        "version": "1.0",
        "kind": "tilemap_blueprint",
        "scene_id": map_spec.get("id") or paths.root.name,
        "map_size": [width, height],
        "tile_size": tile_size,
        "layers": {"cells": cells},
        "materials": _materials_from_cells(cells),
        "adjacency_rules": _adjacency_rules(cells, base_material),
        "generated_at": utc_now(),
    }
    write_json(paths.tilemap_blueprint, blueprint)
    mark_completed(paths.root, "tilemap_blueprint")
    return blueprint


def build_tile_family_plan(scene_dir: str | Path, force: bool = False) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.tile_family_plan.exists() and not force:
        return read_json(paths.tile_family_plan)
    blueprint = build_tilemap_blueprint(paths.root, force=False)
    map_spec = read_json(paths.map_spec)
    tile_size = blueprint["tile_size"]
    groups: list[dict[str, Any]] = []
    explicit = _explicit_tile_groups(map_spec)
    if explicit:
        groups.extend(explicit)
    covered_materials = {str(group.get("material")) for group in groups if group.get("material")}
    groups.extend(_groups_from_blueprint(blueprint, map_spec, tile_size, {g["group_id"] for g in groups}, covered_materials))
    groups.extend(_pixellab_transition_groups(blueprint, {g["group_id"] for g in groups}))
    plan = {
        "version": "1.0",
        "kind": "tile_family_plan",
        "scene_id": blueprint["scene_id"],
        "tile_size": tile_size,
        "source_tile_size": [PIXELLAB_SOURCE_TILE_SIZE, PIXELLAB_SOURCE_TILE_SIZE],
        "pixellab_defaults": {
            "source_tile_size": [PIXELLAB_SOURCE_TILE_SIZE, PIXELLAB_SOURCE_TILE_SIZE],
            "target_tile_size": [PROJECT_TILE_SIZE, PROJECT_TILE_SIZE],
            "upscale": "nearest_neighbor",
            "detail": PIXELLAB_DETAIL,
            "style_contract": PIXELLAB_STYLE_SUFFIX,
        },
        "groups": groups,
        "generated_at": utc_now(),
    }
    write_json(paths.tile_family_plan, plan)
    return plan


def generate_pixellab_tilesets(scene_dir: str | Path, run_api: bool = False, force: bool = False, case: str | None = None) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    plan = build_tile_family_plan(paths.root, force=False)
    raw_dir = paths.pixellab_tilesets_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    selected_groups = [
        group for group in plan.get("groups", [])
        if group.get("generation_mode") == "pixellab_tileset" and (case is None or group.get("group_id") == case)
    ]
    manifest = {
        "version": "1.0",
        "kind": "pixellab_tileset_manifest",
        "run_api": run_api,
        "generated_at": utc_now(),
        "groups": [],
    }
    if not run_api:
        for group in selected_groups:
            manifest["groups"].append(
                {
                    "group_id": group["group_id"],
                    "status": "pending_api",
                    "expected_raw_json": f"pixellab_tilesets/raw/{group['group_id']}.json",
                }
            )
        write_json(raw_dir / "manifest.json", manifest)
        return manifest

    client_cls = _pixellab_client_class()
    client = client_cls(timeout=180)
    for group in selected_groups:
        group_id = str(group["group_id"])
        raw_path = raw_dir / f"{group_id}.json"
        if raw_path.exists() and not force:
            status = "exists"
        else:
            response = client.create_tileset(
                lower_description=str(group["pixellab"]["lower_description"]),
                upper_description=str(group["pixellab"]["upper_description"]),
                transition_description=str(group["pixellab"]["transition_description"]),
                tile_size=int(group.get("source_tile_size", [32, 32])[0]),
                transition_size=float(group["pixellab"].get("transition_size", 0.5)),
                view=str(group["pixellab"].get("view", "high top-down")),
                outline=str(group["pixellab"].get("outline", "selective outline")),
                detail=str(group["pixellab"].get("detail", PIXELLAB_DETAIL)),
            )
            write_json(raw_path, response)
            status = "generated"
        manifest["groups"].append({"group_id": group_id, "status": status, "raw_json": f"pixellab_tilesets/raw/{group_id}.json"})
    write_json(raw_dir / "manifest.json", manifest)
    return manifest


def build_tile_candidates(scene_dir: str | Path, force: bool = False) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.tile_candidates.exists() and not force:
        return read_json(paths.tile_candidates)
    plan = build_tile_family_plan(paths.root, force=False)
    paths.tile_candidates_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for group in plan.get("groups", []):
        if not isinstance(group, dict):
            continue
        mode = group.get("generation_mode")
        if mode == "pixellab_tileset":
            records.extend(_candidates_from_pixellab_group(paths, group, force=force))
        else:
            records.extend(_candidates_from_existing_assets(paths, group, force=force))
    data = {
        "version": "1.0",
        "kind": "tile_candidates",
        "tile_size": plan.get("tile_size") or [64, 64],
        "source_plan": "tile_family_plan.json",
        "generated_at": utc_now(),
        "candidates": records,
    }
    write_json(paths.tile_candidates, data)
    _write_tile_candidate_contact_sheet(paths, records)
    return data


def build_tilemap_mapping(scene_dir: str | Path, force: bool = False) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.tilemap_mapping.exists() and not force:
        return read_json(paths.tilemap_mapping)
    blueprint = build_tilemap_blueprint(paths.root, force=False)
    candidates = build_tile_candidates(paths.root, force=False)
    by_material_role = _candidate_index(candidates.get("candidates", []))
    assignments = []
    missing = []
    tile_ids: dict[str, int] = {}
    next_gid = 1
    for cell in blueprint["layers"]["cells"]:
        candidate = _select_candidate(cell, by_material_role)
        candidate_id = candidate.get("candidate_id") if candidate else None
        if candidate_id and candidate_id not in tile_ids:
            tile_ids[candidate_id] = next_gid
            next_gid += 1
        if not candidate_id and cell.get("layer") != "terrain":
            missing.append({"x": cell["x"], "y": cell["y"], "layer": cell["layer"], "material": cell["material"], "role": cell["role"]})
        assignments.append(
            {
                "x": cell["x"],
                "y": cell["y"],
                "layer": cell["layer"],
                "material": cell["material"],
                "role": cell["role"],
                "candidate_id": candidate_id,
                "gid": tile_ids.get(candidate_id, 0) if candidate_id else 0,
            }
        )
    mapping = {
        "version": "1.0",
        "kind": "tilemap_mapping",
        "source_blueprint": "tilemap_blueprint.json",
        "source_candidates": "tile_candidates.json",
        "map_size": blueprint["map_size"],
        "tile_size": blueprint["tile_size"],
        "tile_ids": tile_ids,
        "assignments": assignments,
        "issues": [{"severity": "warning", "kind": "missing_candidate", **item} for item in missing],
        "generated_at": utc_now(),
    }
    write_json(paths.tilemap_mapping, mapping)
    _render_tilemap_mapping(paths, mapping, candidates)
    return mapping


def export_tilemap_to_tiled(scene_dir: str | Path, force: bool = False) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    mapping = build_tilemap_mapping(paths.root, force=False)
    candidates = build_tile_candidates(paths.root, force=False)
    paths.tiled_dir.mkdir(parents=True, exist_ok=True)
    tileset_path = paths.tiled_dir / "tile_candidates_tileset.png"
    _write_mapping_tileset(tileset_path, mapping, candidates)
    tilemap = _tilemap_from_mapping(mapping, tileset_path)
    tmj_path = paths.tiled_dir / "tilemap_mapping.tmj"
    data = TiledExporter().export(tilemap, tmj_path)
    # Tiled JSON should reference the tileset image relative to the map file.
    data["tilesets"][0]["image"] = "tile_candidates_tileset.png"
    write_json(tmj_path, data)
    return {
        "tmj": str(tmj_path),
        "tileset": str(tileset_path),
        "preview": str(paths.tiled_dir / "tilemap_mapping_preview.png"),
    }


def _base_material(map_spec: dict[str, Any]) -> str:
    base = map_spec.get("base_terrain")
    if isinstance(base, dict):
        return str(base.get("object_key") or base.get("tile") or "base_terrain")
    return str(map_spec.get("theme") or "base_terrain")


def _material_for_tile_instance(obj: dict[str, Any]) -> str:
    props = obj.get("properties") or {}
    composite_type = str(props.get("composite_type") or "")
    composite_id = str(props.get("composite_id") or "")
    object_key = str(props.get("object_key") or obj.get("id") or "")
    if "road" in composite_type or "road" in composite_id or object_key.startswith("road_"):
        return "dirt_road"
    if "track" in composite_type or "track" in composite_id or object_key.startswith("track_"):
        return "running_track"
    if "plaza" in composite_type or "plaza" in composite_id or object_key.startswith("plaza_"):
        return "plaza_brick"
    if "water" in composite_type or object_key.startswith("water_"):
        return "water"
    if "walkway" in composite_type or "walkway" in composite_id or object_key.startswith("walkway_"):
        return "campus_walkway"
    return _normalize_material(composite_type or object_key or "unknown_material")


def _role_from_part_key(part_key: str) -> str:
    for prefix in ("road_", "track_", "plaza_", "walkway_", "water_"):
        if part_key.startswith(prefix):
            part_key = part_key[len(prefix):]
    mapping = {
        "center": "center",
        "variant": "center_variant",
        "edge_top": "edge_top",
        "edge_bottom": "edge_bottom",
        "edge_left": "edge_left",
        "edge_right": "edge_right",
        "corner_top_left": "corner_top_left",
        "corner_top_right": "corner_top_right",
        "corner_bottom_left": "corner_bottom_left",
        "corner_bottom_right": "corner_bottom_right",
        "curve_top_left": "curve_top_left",
        "curve_top_right": "curve_top_right",
        "curve_bottom_left": "curve_bottom_left",
        "curve_bottom_right": "curve_bottom_right",
    }
    return mapping.get(part_key, part_key or "center")


def _connection_signature(role: str, material: str, base_material: str) -> dict[str, str]:
    raw = ROLE_CONNECTORS.get(role, ROLE_CONNECTORS["center"])
    return {
        side: value.replace("same", material).replace("other", base_material).replace("upper", material).replace("lower", base_material)
        for side, value in raw.items()
    }


def _materials_from_cells(cells: list[dict[str, Any]]) -> list[str]:
    return sorted({str(cell["material"]) for cell in cells})


def _adjacency_rules(cells: list[dict[str, Any]], base_material: str) -> list[dict[str, str]]:
    rules = []
    for material in sorted({str(cell["material"]) for cell in cells if cell.get("material") != base_material}):
        rules.append({"from": base_material, "to": material, "transition": f"{base_material}_to_{material}"})
    return rules


def _explicit_tile_groups(map_spec: dict[str, Any]) -> list[dict[str, Any]]:
    groups = []
    for group in map_spec.get("tile_groups", []) or []:
        if not isinstance(group, dict):
            continue
        normalized = dict(group)
        normalized.setdefault("generation_mode", "sprite_sheet")
        normalized.setdefault("members", [])
        normalized.setdefault("material", _material_from_group(normalized))
        base_material = _base_material(map_spec)
        material = str(normalized["material"])
        normalized["members"] = [
            _normalize_explicit_member(member, normalized, material, base_material)
            for member in normalized.get("members", []) or []
            if isinstance(member, dict)
        ]
        groups.append(normalized)
    return groups


def _normalize_explicit_member(member: dict[str, Any], group: dict[str, Any], material: str, base_material: str) -> dict[str, Any]:
    normalized = dict(member)
    role = str(normalized.get("role") or "center")
    normalized.setdefault("material", material)
    normalized.setdefault("connection", _connection_signature(role, material, str(group.get("from") or base_material)))
    return normalized


def _material_from_group(group: dict[str, Any]) -> str:
    explicit = group.get("material") or group.get("to")
    if explicit:
        return _normalize_material(str(explicit))
    group_id = str(group.get("group_id") or "")
    from_group_id = _material_from_text(group_id)
    if from_group_id:
        return from_group_id
    prompt = str(group.get("prompt") or "")
    from_prompt = _material_from_text(prompt)
    if from_prompt:
        return from_prompt
    return _normalize_material(group_id)


def _material_from_text(value: str) -> str | None:
    text = value.lower()
    if "wheat" in text:
        return "wheat_field"
    if "running_track" in text or "track" in text:
        return "running_track"
    if "water" in text or "shore" in text:
        return "water"
    if "plaza" in text:
        return "plaza_brick"
    if "walkway" in text or "stone" in text:
        return "campus_walkway"
    if "road" in text or "dirt" in text:
        return "dirt_road"
    if "lawn" in text or "grass" in text:
        return "campus_lawn"
    return None


def _normalize_material(material: str) -> str:
    value = material.strip()
    aliases = {
        "grass": "grass_lawn",
        "campus_lawn_tiles": "campus_lawn",
        "campus_plaza_tiles": "plaza_brick",
        "plaza_tiles": "plaza_brick",
        "campus_walkway_tiles": "campus_walkway",
        "walkway_tiles": "campus_walkway",
        "stone_walkway_tiles": "stone_walkway",
        "brick_walkway_tiles": "brick_walkway",
        "dirt_road_tiles": "dirt_road",
        "running_track_tiles": "running_track",
        "wheat_field_tiles": "wheat_field",
    }
    return aliases.get(value, value)


def _pixellab_prompt(description: str) -> str:
    text = description.strip()
    if PIXELLAB_STYLE_SUFFIX in text:
        return text
    return f"{text}, {PIXELLAB_STYLE_SUFFIX}"


def _groups_from_blueprint(
    blueprint: dict[str, Any],
    map_spec: dict[str, Any],
    tile_size: list[int],
    seen: set[str],
    covered_materials: set[str] | None = None,
) -> list[dict[str, Any]]:
    groups = []
    covered = covered_materials or set()
    by_material: dict[str, set[str]] = {}
    for cell in blueprint["layers"]["cells"]:
        by_material.setdefault(str(cell["material"]), set()).add(str(cell["role"]))
    base = _base_material(map_spec)
    for material, roles in sorted(by_material.items()):
        material_name = _normalize_material(material)
        if material_name in covered:
            continue
        if material == base:
            group_id = material
        else:
            group_id = f"{material}_tiles"
        if group_id in seen:
            continue
        groups.append(
            {
                "group_id": group_id,
                "kind": "material_group",
                "generation_mode": "existing_or_placeholder",
                "tile_size": tile_size,
                "material": material_name,
                "members": [
                    {
                        "tile_id": f"{material_name}_{role}",
                        "role": role,
                        "material": material_name,
                        "connection": _connection_signature(role, material_name, base),
                    }
                    for role in sorted(roles)
                ],
            }
        )
    return groups


def _pixellab_transition_groups(blueprint: dict[str, Any], seen: set[str]) -> list[dict[str, Any]]:
    materials = {_normalize_material(str(material)) for material in (blueprint.get("materials") or [])}
    groups = []
    for case_id, spec in PIXELLAB_CASES.items():
        if case_id in seen:
            continue
        if spec["from"] not in materials or spec["to"] not in materials:
            continue
        groups.append(
            {
                "group_id": case_id,
                "kind": "transition_group",
                "generation_mode": "pixellab_tileset",
                "tile_size": blueprint["tile_size"],
                "source_tile_size": [PIXELLAB_SOURCE_TILE_SIZE, PIXELLAB_SOURCE_TILE_SIZE],
                "target_tile_size": [PROJECT_TILE_SIZE, PROJECT_TILE_SIZE],
                "upscale": "nearest_neighbor",
                "from": spec["from"],
                "to": spec["to"],
                "members": [
                    {
                        "tile_id": f"{case_id}_{role}",
                        "role": role,
                        "material": spec["to"],
                        "connection": _connection_signature(role, spec["to"], spec["from"]),
                    }
                    for role in PIXELLAB_ROLE_ORDER
                ],
                "pixellab": {
                    "lower_description": _pixellab_prompt(spec["lower_description"]),
                    "upper_description": _pixellab_prompt(spec["upper_description"]),
                    "transition_description": _pixellab_prompt(spec["transition_description"]),
                    "transition_size": 0.5,
                    "view": "high top-down",
                    "outline": "selective outline",
                    "detail": PIXELLAB_DETAIL,
                },
            }
        )
    return groups


def _pixellab_client_class():
    tools_ai = Path(__file__).resolve().parents[3] / "tools" / "ai"
    if str(tools_ai) not in sys.path:
        sys.path.insert(0, str(tools_ai))
    from pixellab_v2_client import PixelLabV2Client

    return PixelLabV2Client


def _candidates_from_pixellab_group(paths, group: dict[str, Any], force: bool = False) -> list[dict[str, Any]]:
    raw_path = paths.pixellab_tilesets_dir / "raw" / f"{group['group_id']}.json"
    if not raw_path.exists():
        return [
            {
                "candidate_id": f"{group['group_id']}_pending",
                "status": "pending_api",
                "source": "pixellab_tileset",
                "group_id": group["group_id"],
                "material": _normalize_material(str(group.get("to") or group.get("material") or group["group_id"])),
                "role": "unknown",
                "missing_raw_json": f"pixellab_tilesets/raw/{group['group_id']}.json",
            }
        ]
    raw = read_json(raw_path)
    images = _decode_images_from_json(raw)
    records = []
    if not images:
        return [
            {
                "candidate_id": f"{group['group_id']}_decode_failed",
                "status": "decode_failed",
                "source": "pixellab_tileset",
                "group_id": group["group_id"],
                "raw_json": str(raw_path.relative_to(paths.root)).replace("\\", "/"),
            }
        ]
    out_dir = paths.tile_candidates_dir / str(group["group_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    members = list(group.get("members") or [])
    source_tile = int((group.get("source_tile_size") or [PIXELLAB_SOURCE_TILE_SIZE, PIXELLAB_SOURCE_TILE_SIZE])[0])
    target_tile = int((group.get("tile_size") or [PROJECT_TILE_SIZE, PROJECT_TILE_SIZE])[0])
    tile_index = 0
    for image_index, (_, image) in enumerate(images):
        for tile in _slice_image_tiles(image, source_tile):
            member = members[tile_index] if tile_index < len(members) else {}
            role = str(member.get("role") or f"tile_{tile_index:02d}")
            material = _normalize_material(str(member.get("material") or group.get("to") or group.get("material") or group["group_id"]))
            candidate_id = str(member.get("tile_id") or f"{group['group_id']}_{tile_index:02d}")
            out_path = out_dir / f"{candidate_id}.png"
            tile.resize((target_tile, target_tile), Image.Resampling.NEAREST).save(out_path)
            records.append(
                {
                    "candidate_id": candidate_id,
                    "status": "ready",
                    "source": "pixellab_tileset",
                    "group_id": group["group_id"],
                    "source_image_index": image_index,
                    "source_rect_index": tile_index,
                    "path": str(out_path.relative_to(paths.root)).replace("\\", "/"),
                    "material": material,
                    "role": role,
                    "reuse": "reusable_tile",
                    "connection": member.get("connection") or _connection_signature(role, material, str(group.get("from") or "base")),
                }
            )
            tile_index += 1
    return records


def _candidates_from_existing_assets(paths, group: dict[str, Any], force: bool = False) -> list[dict[str, Any]]:
    records = []
    out_dir = paths.tile_candidates_dir / str(group["group_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    tile_size = int((group.get("tile_size") or [64, 64])[0])
    group_material = _material_from_group(group)
    for member in group.get("members", []) or []:
        if not isinstance(member, dict):
            continue
        role = str(member.get("role") or "center")
        material = _normalize_material(str(member.get("material") or group_material))
        candidate_id = str(member.get("tile_id") or f"{group['group_id']}_{role}")
        source_ref = _member_source_ref(member)
        source = _resolve_source_asset(paths, source_ref)
        if source:
            out_path = out_dir / f"{candidate_id}.png"
            with Image.open(source).convert("RGBA") as image:
                image.resize((tile_size, tile_size), Image.Resampling.NEAREST).save(out_path)
            status = "ready"
            rel_path = str(out_path.relative_to(paths.root)).replace("\\", "/")
            rel_source = str(source.relative_to(paths.root)).replace("\\", "/")
        else:
            status = "missing_source"
            rel_path = None
            rel_source = None
        records.append(
            {
                "candidate_id": candidate_id,
                "status": status,
                "source": "existing_asset",
                "group_id": group["group_id"],
                "path": rel_path,
                "source_ref": source_ref,
                "source_path": rel_source,
                "material": material,
                "role": role,
                "reuse": "reusable_tile",
                "connection": member.get("connection") or _connection_signature(role, material, str(group.get("from") or "base")),
            }
        )
    return records


def _member_source_ref(member: dict[str, Any]) -> str:
    for key in ("source_ref", "asset_id", "tile_id"):
        value = member.get(key)
        if value:
            return str(value)
    return ""


def _source_ref_candidates(source_ref: str) -> list[str]:
    if not source_ref:
        return []
    normalized = source_ref.strip()
    candidates = [normalized]
    if ":" in normalized:
        left, right = normalized.split(":", 1)
        candidates.append(f"{left}_{right}")
    candidates.append(normalized.replace(":", "_"))
    seen = set()
    deduped = []
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _resolve_source_asset(paths, source_ref: str) -> Path | None:
    for asset_id in _source_ref_candidates(source_ref):
        for folder in (paths.background_tiles_dir, paths.images_dir):
            path = folder / f"{asset_id}.png"
            if path.exists():
                return path
    return None


def _decode_images_from_json(raw: Any) -> list[tuple[str, Image.Image]]:
    images = []
    for field_path, b64 in _iter_b64_fields(raw):
        try:
            image = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
        except Exception:
            continue
        images.append((field_path, image))
    return images


def _iter_b64_fields(value: Any, path: str = ""):
    if isinstance(value, dict):
        if isinstance(value.get("base64"), str):
            yield path or "image", value["base64"]
        for key, child in value.items():
            yield from _iter_b64_fields(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_b64_fields(child, f"{path}[{index}]")


def _slice_image_tiles(image: Image.Image, tile_size: int) -> list[Image.Image]:
    cols = max(1, image.width // tile_size)
    rows = max(1, image.height // tile_size)
    tiles = []
    for y in range(rows):
        for x in range(cols):
            tiles.append(image.crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size)))
    return tiles


def _write_tile_candidate_contact_sheet(paths, records: list[dict[str, Any]]) -> None:
    ready = [record for record in records if record.get("status") == "ready" and record.get("path")]
    if not ready:
        return
    tile_size = 64
    cols = min(8, len(ready))
    rows = (len(ready) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * tile_size, rows * tile_size), (0, 0, 0, 0))
    for index, record in enumerate(ready):
        with Image.open(paths.root / record["path"]).convert("RGBA") as tile:
            sheet.alpha_composite(tile.resize((tile_size, tile_size), Image.Resampling.NEAREST), ((index % cols) * tile_size, (index // cols) * tile_size))
    out = paths.tile_candidates_dir / "contact_sheet.png"
    sheet.save(out)


def _candidate_index(candidates: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        if candidate.get("status") != "ready":
            continue
        index.setdefault((str(candidate.get("material")), str(candidate.get("role"))), []).append(candidate)
    return index


def _select_candidate(cell: dict[str, Any], index: dict[tuple[str, str], list[dict[str, Any]]]) -> dict[str, Any] | None:
    material = str(cell.get("material"))
    role = str(cell.get("role"))
    for key in ((material, role), (material, "center"), (material, "center_variant")):
        items = index.get(key)
        if items:
            return items[0]
    return None


def _render_tilemap_mapping(paths, mapping: dict[str, Any], candidates: dict[str, Any]) -> None:
    preview_path = paths.root / "tilemap_mapping_preview.png"
    tile_size = int((mapping.get("tile_size") or [64, 64])[0])
    width, height = mapping["map_size"]
    image = Image.new("RGBA", (width * tile_size, height * tile_size), (0, 0, 0, 255))
    candidate_by_id = {item["candidate_id"]: item for item in candidates.get("candidates", []) if item.get("status") == "ready"}
    colors: dict[str, tuple[int, int, int, int]] = {}
    for assignment in mapping["assignments"]:
        x, y = int(assignment["x"]), int(assignment["y"])
        candidate = candidate_by_id.get(assignment.get("candidate_id"))
        if candidate and candidate.get("path"):
            with Image.open(paths.root / candidate["path"]).convert("RGBA") as tile:
                image.alpha_composite(tile.resize((tile_size, tile_size), Image.Resampling.NEAREST), (x * tile_size, y * tile_size))
        else:
            material = str(assignment.get("material"))
            colors.setdefault(material, _color_for_material(material))
            tile = Image.new("RGBA", (tile_size, tile_size), colors[material])
            image.alpha_composite(tile, (x * tile_size, y * tile_size))
    image.save(preview_path)


def _color_for_material(material: str) -> tuple[int, int, int, int]:
    palette = {
        "wheat_field": (218, 183, 67, 255),
        "grass_lawn": (88, 166, 83, 255),
        "dirt_road": (185, 139, 80, 255),
        "running_track": (190, 82, 54, 255),
        "plaza_brick": (190, 174, 139, 255),
        "water": (55, 129, 184, 255),
        "campus_walkway": (170, 160, 135, 255),
    }
    return palette.get(material, (120, 120, 120, 255))


def _write_mapping_tileset(path: Path, mapping: dict[str, Any], candidates: dict[str, Any]) -> None:
    tile_size = int((mapping.get("tile_size") or [64, 64])[0])
    tile_ids = mapping.get("tile_ids") or {}
    if not tile_ids:
        Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0)).save(path)
        return
    columns = min(8, max(1, len(tile_ids)))
    rows = (len(tile_ids) + columns - 1) // columns
    image = Image.new("RGBA", (columns * tile_size, rows * tile_size), (0, 0, 0, 0))
    candidate_by_id = {item["candidate_id"]: item for item in candidates.get("candidates", []) if item.get("status") == "ready"}
    for candidate_id, gid in tile_ids.items():
        candidate = candidate_by_id.get(candidate_id)
        if not candidate or not candidate.get("path"):
            continue
        with Image.open(path.parent.parent / candidate["path"]).convert("RGBA") as tile:
            index = int(gid) - 1
            image.alpha_composite(tile.resize((tile_size, tile_size), Image.Resampling.NEAREST), ((index % columns) * tile_size, (index // columns) * tile_size))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _tilemap_from_mapping(mapping: dict[str, Any], tileset_path: Path) -> TilemapData:
    width, height = mapping["map_size"]
    tile_w, tile_h = mapping["tile_size"]
    layers = {name: [0] * (width * height) for name in ("terrain", "path", "building", "decoration", "collision")}
    for assignment in mapping["assignments"]:
        layer_name = str(assignment.get("layer") or "terrain")
        if layer_name not in layers:
            layers[layer_name] = [0] * (width * height)
        layers[layer_name][int(assignment["y"]) * width + int(assignment["x"])] = int(assignment.get("gid") or 0)
    tile_count = max([0, *[int(value) for value in (mapping.get("tile_ids") or {}).values()]])
    columns = min(8, max(1, tile_count))
    tilemap = TilemapData(
        map=MapInfo(width=width, height=height, tile_width=tile_w, tile_height=tile_h),
        tileset=TilesetInfo(
            id="tile_candidates",
            image=str(tileset_path.name),
            tile_width=tile_w,
            tile_height=tile_h,
            columns=columns,
            tile_count=tile_count,
        ),
        layers=layers,
        metadata={"theme": "tilemap_art", "seed": 0},
    )
    PreviewRenderer().render(tilemap, tileset_path.parent / "tilemap_mapping_preview.png")
    return tilemap
