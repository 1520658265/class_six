from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

from generator.assets.image_generation import ImageGenerationRequest, ImageStyle, MockImageGenerator, TransparencyMode

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress


EXTRACT_METHODS = {"extract_from_concept", "extract_and_cleanup"}
FULL_BACKGROUND_METHODS = {"use_full_concept"}
REGENERATE_METHODS = {"regenerate"}
DEFAULT_TILE_GROUP_SHEET_COLUMNS = 4


def build_background_plan(scene_dir: str | Path, force: bool = False, concept_image: str | Path | None = None) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.background_plan.exists() and not force:
        return _read_json(paths.background_plan)
    mark_in_progress(paths.root, "4_background_plan")
    art_request = _read_json(paths.art_request)
    map_spec = _read_json(paths.map_spec) if paths.map_spec.exists() else {}
    concept_path = Path(concept_image) if concept_image else paths.concept_image
    if concept_image and not concept_path.is_absolute():
        concept_path = paths.root / concept_path
    concept_image = _relative_to_scene(paths.root, concept_path)
    plan = {
        "version": "1.0",
        "kind": "background_plan",
        "scene_id": paths.root.name,
        "concept_image": concept_image,
        "tile_size": art_request.get("tile_size") or [64, 64],
        "map_size": art_request.get("map_size") or [64, 64],
        "image_size": _image_size(concept_path),
        "seed": art_request.get("seed"),
        "background_image": {
            "method": "review_required",
            "status": "pending_review",
            "source_image": concept_image,
            "output_path": "background/background.png",
            "notes": "Use this when the whole concept image should become the map background instead of repeating one extracted terrain tile.",
        },
        "regions": art_request.get("regions") or [],
        "review_items": [],
        "tile_groups": [],
        "background_entities": [],
        "foreground_objects": [],
    }
    for obj in art_request.get("objects", []) or []:
        if not isinstance(obj, dict):
            continue
        if obj.get("asset_role") == "base_terrain" or obj.get("category") == "terrain_tile":
            plan["review_items"].append(_base_terrain_review_item(obj))
        else:
            plan["foreground_objects"].append(
                {
                    "id": obj.get("id"),
                    "category": obj.get("category"),
                    "display_name": obj.get("display_name"),
                    "placement_zone": obj.get("placement_zone"),
                }
            )
    for target in art_request.get("generation_targets", []) or []:
        if isinstance(target, dict) and target.get("asset_role") == "composite_source":
            entity = _background_entity(target, placement=_composite_placement(target, map_spec))
            plan["background_entities"].append(entity)
            plan["review_items"].extend(entity["parts"])
    plan["tile_groups"] = _tile_groups_for_plan(plan, map_spec)
    _attach_suggested_crop_rects(plan)
    _write_json(paths.background_plan, plan)
    mark_completed(paths.root, "4_background_plan")
    return plan


def write_background_review_html(scene_dir: str | Path, force: bool = False) -> Path:
    paths = scene_paths(scene_dir)
    if paths.background_review.exists() and not force:
        return paths.background_review
    plan = _read_json(paths.background_plan)
    _attach_suggested_crop_rects(plan)
    html = _review_html(plan)
    paths.background_review.write_text(html, encoding="utf-8")
    return paths.background_review


def extract_background_tiles(scene_dir: str | Path, force: bool = False, use_gemini: bool = False) -> list[str]:
    paths = scene_paths(scene_dir)
    plan = _read_json(paths.background_plan)
    concept_path = paths.root / str(plan.get("concept_image") or "")
    needs_concept = _plan_needs_concept(plan)
    if needs_concept and not concept_path.exists():
        raise FileNotFoundError(f"concept image not found: {concept_path}")
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("PIL not available for background tile extraction") from exc

    paths.background_tiles_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    if needs_concept:
        with Image.open(concept_path).convert("RGBA") as source:
            written.extend(_extract_full_background(paths, plan, source, force=force))
            written.extend(_extract_reviewed_crops(paths, plan, source, force=force))
    written.extend(_generate_regenerated_tile_groups(paths, plan, force=force, use_gemini=use_gemini))
    return written


def _plan_needs_concept(plan: dict[str, Any]) -> bool:
    background = plan.get("background_image")
    if isinstance(background, dict) and background.get("method") in FULL_BACKGROUND_METHODS:
        return True
    for item in plan.get("review_items", []) or []:
        if isinstance(item, dict) and item.get("method") in EXTRACT_METHODS:
            return True
    return False


def _extract_reviewed_crops(paths, plan: dict[str, Any], source, force: bool = False) -> list[str]:
    from PIL import Image

    written: list[str] = []
    for item in plan.get("review_items", []) or []:
        if not isinstance(item, dict) or item.get("method") not in EXTRACT_METHODS:
            continue
        rect = item.get("crop_rect")
        if not _valid_rect(rect):
            continue
        asset_id = _safe_id(item.get("asset_id") or item.get("id") or "background_tile")
        png_path = paths.background_tiles_dir / f"{asset_id}.png"
        json_path = paths.background_tiles_dir / f"{asset_id}.json"
        if png_path.exists() and json_path.exists() and not force:
            written.append(asset_id)
            continue
        x, y, w, h = [int(v) for v in rect]
        tile = source.crop((x, y, x + w, y + h))
        target_size = item.get("target_size") or plan.get("tile_size") or [64, 64]
        if isinstance(target_size, list) and len(target_size) == 2:
            target = (int(target_size[0]), int(target_size[1]))
            if tile.size != target:
                tile = tile.resize(target, Image.Resampling.NEAREST)
        tile.save(png_path, "PNG")
        tile.close()
        _write_json(
            json_path,
            {
                "asset_id": asset_id,
                "source": "background_plan",
                "method": item.get("method"),
                "concept_image": plan.get("concept_image"),
                "crop_rect": rect,
                "target_size": list(target_size),
                "review_item_id": item.get("id"),
            },
        )
        written.append(asset_id)
    return written


def _extract_full_background(paths, plan: dict[str, Any], source, force: bool = False) -> list[str]:
    background = plan.get("background_image")
    if not isinstance(background, dict) or background.get("method") not in FULL_BACKGROUND_METHODS:
        return []
    output_path = paths.root / str(background.get("output_path") or "background/background.png")
    metadata_path = output_path.with_suffix(".json")
    if output_path.exists() and metadata_path.exists() and not force:
        return ["background_image"]
    target_size = background.get("target_size") or plan.get("image_size")
    image = source.copy()
    if isinstance(target_size, list) and len(target_size) == 2:
        target = (int(target_size[0]), int(target_size[1]))
        if target[0] > 0 and target[1] > 0 and image.size != target:
            image = image.resize(target, Image.Resampling.BICUBIC)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG")
    image.close()
    _write_json(
        metadata_path,
        {
            "asset_id": "background_image",
            "source": "background_plan",
            "method": background.get("method"),
            "concept_image": plan.get("concept_image"),
            "output_path": _relative_to_scene(paths.root, output_path),
            "target_size": list(target_size) if isinstance(target_size, list) else list(source.size),
        },
    )
    return ["background_image"]


def _base_terrain_review_item(obj: dict[str, Any]) -> dict[str, Any]:
    source_canvas = obj.get("source_canvas") or [64, 64]
    return {
        "id": str(obj.get("id")),
        "asset_id": str(obj.get("asset_id") or obj.get("id")),
        "kind": "base_terrain",
        "display_name": obj.get("display_name") or obj.get("id"),
        "method": "extract_or_regenerate",
        "status": "pending_review",
        "crop_rect": None,
        "suggested_crop_rect": None,
        "target_size": source_canvas,
        "notes": "Large uniform terrain is often a good extraction candidate if the concept image has a clean patch.",
    }


def _background_entity(target: dict[str, Any], placement: str | None = None) -> dict[str, Any]:
    composite_id = str(target.get("composite_id") or target.get("id"))
    parts = []
    for part in target.get("parts", []) or []:
        if not isinstance(part, dict):
            continue
        key = str(part.get("key"))
        parts.append(
            {
                "id": f"{composite_id}:{key}",
                "asset_id": f"{composite_id}_{key}",
                "kind": "composite_part",
                "composite_id": composite_id,
                "part_key": key,
                "display_name": part.get("display_name") or key,
                "method": "extract_or_regenerate",
                "status": "pending_review",
                "crop_rect": None,
                "suggested_crop_rect": None,
                "target_size": [64, 64],
                "notes": "Use extraction only when this part is clean, grid-aligned, and reusable.",
            }
        )
    return {
        "id": composite_id,
        "source_target_id": target.get("id"),
        "type": target.get("composite_type"),
        "display_name": target.get("display_name"),
        "placement": placement or target.get("placement"),
        "footprint": target.get("footprint"),
        "layout": target.get("layout") or [],
        "parts": parts,
    }


def _tile_groups_for_plan(plan: dict[str, Any], map_spec: dict[str, Any]) -> list[dict[str, Any]]:
    review_items = [item for item in plan.get("review_items", []) or [] if isinstance(item, dict)]
    groups: list[dict[str, Any]] = []
    covered_assets: set[str] = set()
    for group in map_spec.get("tile_groups", []) or []:
        if not isinstance(group, dict):
            continue
        normalized = _normalize_explicit_tile_group(group, plan)
        if normalized["members"]:
            groups.append(normalized)
            covered_assets.update(str(member.get("asset_id") or member.get("tile_id")) for member in normalized["members"])

    for group in _auto_tile_groups(plan, map_spec):
        members = [
            member
            for member in group.get("members", [])
            if str(member.get("asset_id") or member.get("tile_id")) not in covered_assets
        ]
        if not members:
            continue
        group = dict(group)
        group["members"] = members
        groups.append(group)
        covered_assets.update(str(member.get("asset_id") or member.get("tile_id")) for member in members)

    item_by_id = {str(item.get("id")): item for item in review_items}
    item_by_asset = {str(item.get("asset_id")): item for item in review_items}
    for group in groups:
        for member in group.get("members", []) or []:
            if not isinstance(member, dict):
                continue
            item = item_by_id.get(str(member.get("review_item_id"))) or item_by_asset.get(str(member.get("asset_id")))
            if item:
                item["tile_group_id"] = group.get("group_id")
                item["tile_role"] = member.get("role")
    return groups


def _normalize_explicit_tile_group(group: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    tile_size = _pair(group.get("tile_size")) or _pair(plan.get("tile_size")) or [64, 64]
    normalized = {
        "group_id": str(group.get("group_id")),
        "kind": str(group.get("kind") or "material_group"),
        "generation_mode": "sprite_sheet",
        "tile_size": tile_size,
        "display_name": group.get("display_name") or group.get("group_id"),
        "prompt": group.get("prompt"),
        "members": [],
        "sheet": _sheet_contract(group, tile_size),
        "properties": dict(group.get("properties") or {}),
    }
    if group.get("from") is not None:
        normalized["from"] = group.get("from")
    if group.get("to") is not None:
        normalized["to"] = group.get("to")
    for member in group.get("members", []) or []:
        if not isinstance(member, dict):
            continue
        source_ref = member.get("source_ref")
        asset_id = _asset_id_for_source_ref(plan, source_ref) or member.get("asset_id") or member.get("tile_id")
        review_item_id = _review_item_id_for_source_ref(plan, source_ref, asset_id)
        normalized["members"].append(
            {
                "tile_id": str(member.get("tile_id") or asset_id),
                "asset_id": str(asset_id),
                "role": str(member.get("role") or _role_from_key(str(member.get("tile_id") or ""))),
                "source_ref": source_ref,
                "review_item_id": review_item_id,
                "display_name": member.get("display_name") or _display_name_for_review_item(plan, review_item_id, asset_id),
                "notes": member.get("notes"),
                "properties": dict(member.get("properties") or {}),
            }
        )
    return normalized


def _auto_tile_groups(plan: dict[str, Any], map_spec: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    tile_size = _pair(plan.get("tile_size")) or [64, 64]
    base_terrain = map_spec.get("base_terrain")
    if isinstance(base_terrain, dict):
        object_key = str(base_terrain.get("object_key") or "base_terrain")
        asset_id = f"{object_key}_01"
        review_item = _review_item_by_asset(plan, asset_id)
        groups.append(
            _make_tile_group(
                group_id=object_key,
                kind="material_group",
                tile_size=tile_size,
                display_name=base_terrain.get("display_name") or object_key,
                prompt=base_terrain.get("source_clause") or dict(base_terrain.get("properties") or {}).get("appearance"),
                members=[
                    {
                        "tile_id": asset_id,
                        "asset_id": asset_id,
                        "role": "center",
                        "source_ref": object_key,
                        "review_item_id": review_item.get("id") if review_item else asset_id,
                        "display_name": base_terrain.get("display_name") or object_key,
                        "notes": "Dominant base terrain center tile.",
                        "properties": dict(base_terrain.get("properties") or {}),
                    }
                ],
            )
        )

    for entity in plan.get("background_entities", []) or []:
        if not isinstance(entity, dict):
            continue
        members = []
        for part in entity.get("parts", []) or []:
            if not isinstance(part, dict):
                continue
            part_key = str(part.get("part_key") or "")
            asset_id = str(part.get("asset_id") or f"{entity.get('id')}_{part_key}")
            members.append(
                {
                    "tile_id": asset_id,
                    "asset_id": asset_id,
                    "role": _role_from_key(part_key),
                    "source_ref": f"{entity.get('id')}:{part_key}",
                    "review_item_id": part.get("id"),
                    "display_name": part.get("display_name") or part_key,
                    "notes": part.get("notes"),
                    "properties": {
                        "composite_id": entity.get("id"),
                        "composite_type": entity.get("type"),
                        "part_key": part_key,
                    },
                }
            )
        if members:
            groups.append(
                _make_tile_group(
                    group_id=f"{entity.get('id')}_tiles",
                    kind="material_group",
                    tile_size=tile_size,
                    display_name=entity.get("display_name") or entity.get("id"),
                    prompt=f"{entity.get('display_name') or entity.get('id')} tile family for {entity.get('type') or 'background composite'}",
                    members=members,
                    properties={
                        "composite_id": entity.get("id"),
                        "composite_type": entity.get("type"),
                        "placement": entity.get("placement"),
                        "footprint": entity.get("footprint"),
                    },
                )
            )
    return groups


def _make_tile_group(
    group_id: str,
    kind: str,
    tile_size: list[int],
    display_name: Any,
    prompt: Any,
    members: list[dict[str, Any]],
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    group = {
        "group_id": _safe_id(group_id).lower(),
        "kind": kind,
        "generation_mode": "sprite_sheet",
        "tile_size": tile_size,
        "display_name": display_name,
        "prompt": prompt,
        "members": members,
        "sheet": _sheet_contract({"members": members}, tile_size),
        "properties": properties or {},
    }
    group["sheet"]["columns"] = min(DEFAULT_TILE_GROUP_SHEET_COLUMNS, max(1, len(members)))
    return group


def _sheet_contract(group: dict[str, Any], tile_size: list[int]) -> dict[str, Any]:
    sheet = dict(group.get("sheet") or {})
    count = len([item for item in group.get("members", []) or [] if isinstance(item, dict)])
    columns = int(sheet.get("columns") or min(DEFAULT_TILE_GROUP_SHEET_COLUMNS, max(1, count)))
    return {
        "layout": str(sheet.get("layout") or "grid"),
        "columns": max(1, columns),
        "gutter": int(sheet.get("gutter") or 0),
        "slot_size": tile_size,
    }


def _asset_id_for_source_ref(plan: dict[str, Any], source_ref: Any) -> str | None:
    if source_ref is None:
        return None
    source = str(source_ref)
    for item in plan.get("review_items", []) or []:
        if not isinstance(item, dict):
            continue
        if source in {
            str(item.get("id") or ""),
            str(item.get("asset_id") or ""),
            f"{item.get('composite_id')}:{item.get('part_key')}",
        }:
            return str(item.get("asset_id") or item.get("id"))
    return None


def _review_item_id_for_source_ref(plan: dict[str, Any], source_ref: Any, asset_id: Any) -> str | None:
    if source_ref is not None:
        source = str(source_ref)
    else:
        source = ""
    asset = str(asset_id or "")
    for item in plan.get("review_items", []) or []:
        if not isinstance(item, dict):
            continue
        if source in {
            str(item.get("id") or ""),
            str(item.get("asset_id") or ""),
            f"{item.get('composite_id')}:{item.get('part_key')}",
        } or asset == str(item.get("asset_id") or ""):
            return str(item.get("id") or item.get("asset_id"))
    return None


def _display_name_for_review_item(plan: dict[str, Any], review_item_id: str | None, asset_id: Any) -> str | None:
    for item in plan.get("review_items", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") == str(review_item_id or "") or str(item.get("asset_id") or "") == str(asset_id or ""):
            value = item.get("display_name")
            return str(value) if value is not None else None
    return None


def _review_item_by_asset(plan: dict[str, Any], asset_id: str) -> dict[str, Any] | None:
    for item in plan.get("review_items", []) or []:
        if isinstance(item, dict) and str(item.get("asset_id") or "") == asset_id:
            return item
    return None


def _role_from_key(key: str) -> str:
    normalized = key.lower()
    replacements = {
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
        "straight_horizontal": "straight_horizontal",
        "straight_vertical": "straight_vertical",
    }
    for token, role in replacements.items():
        if token in normalized:
            return role
    return "center"


def _generate_regenerated_tile_groups(paths, plan: dict[str, Any], force: bool = False, use_gemini: bool = False) -> list[str]:
    requested = _regeneration_request_index(plan)
    if not requested:
        return []
    generator = _create_background_image_generator(paths.background_tiles_dir / "_temp", use_gemini)
    written: list[str] = []
    for group in plan.get("tile_groups", []) or []:
        if not isinstance(group, dict) or not _tile_group_requested(group, requested):
            continue
        written.extend(_generate_tile_group_sheet(paths, plan, group, generator, force=force))
    return written


def _regeneration_request_index(plan: dict[str, Any]) -> set[str]:
    requested: set[str] = set()
    for item in plan.get("review_items", []) or []:
        if not isinstance(item, dict) or item.get("method") not in REGENERATE_METHODS:
            continue
        requested.add(str(item.get("id") or ""))
        requested.add(str(item.get("asset_id") or ""))
    return {item for item in requested if item}


def _tile_group_requested(group: dict[str, Any], requested: set[str]) -> bool:
    for member in group.get("members", []) or []:
        if not isinstance(member, dict):
            continue
        if requested & {
            str(member.get("tile_id") or ""),
            str(member.get("asset_id") or ""),
            str(member.get("review_item_id") or ""),
            str(member.get("source_ref") or ""),
        }:
            return True
    return False


def _generate_tile_group_sheet(paths, plan: dict[str, Any], group: dict[str, Any], generator, force: bool = False) -> list[str]:
    group_id = _safe_id(group.get("group_id") or "tile_group")
    members = [member for member in group.get("members", []) or [] if isinstance(member, dict)]
    if not members:
        return []
    sheet_path = paths.background_tiles_dir / f"_group_{group_id}.png"
    sheet_json = paths.background_tiles_dir / f"_group_{group_id}.json"
    output_ids = [str(member.get("asset_id") or member.get("tile_id")) for member in members]
    output_paths = [paths.background_tiles_dir / f"{asset_id}.png" for asset_id in output_ids]
    output_json_paths = [paths.background_tiles_dir / f"{asset_id}.json" for asset_id in output_ids]
    if not force and sheet_path.exists() and sheet_json.exists() and all(path.exists() for path in output_paths + output_json_paths):
        return output_ids

    request, rects = _tile_group_request(plan, group)
    procedural = dict(group.get("properties") or {}).get("generator") == "procedural_tile_family"
    if procedural:
        _generate_procedural_tile_group_sheet(sheet_path, group, members, rects)
        model_name = "procedural_tile_family"
        actual_seed = plan.get("seed")
    else:
        response = generator.generate(request)
        if not response.success:
            raise RuntimeError(response.error or f"tile group generation failed: {group_id}")
        source_path = Path(str(response.image_path))
        if source_path.resolve() != sheet_path.resolve():
            sheet_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(source_path), sheet_path)
            except PermissionError:
                shutil.copyfile(source_path, sheet_path)
                try:
                    source_path.unlink()
                except OSError:
                    pass
        model_name = response.model
        actual_seed = response.actual_seed

    records = _slice_tile_group_sheet(sheet_path, paths.background_tiles_dir, members, rects)
    for record in records:
        asset_id = str(record["asset_id"])
        member = record["member"]
        _write_json(
            paths.background_tiles_dir / f"{asset_id}.json",
            {
                "asset_id": asset_id,
                "source": "background_tile_group",
                "method": "regenerate",
                "group_id": group_id,
                "group_kind": group.get("kind"),
                "role": member.get("role"),
                "tile_id": member.get("tile_id"),
                "review_item_id": member.get("review_item_id"),
                "source_ref": member.get("source_ref"),
                "sheet_path": sheet_path.name,
                "source_rect": record["source_rect"],
                "target_size": group.get("tile_size") or plan.get("tile_size") or [64, 64],
                "prompt": request.prompt,
                "generator": model_name,
                "actual_seed": actual_seed,
            },
        )
    _write_json(
        sheet_json,
        {
            "group_id": group_id,
            "source": "background_tile_group",
            "method": "regenerate",
            "sheet_path": sheet_path.name,
            "tile_size": group.get("tile_size") or plan.get("tile_size") or [64, 64],
            "sheet": group.get("sheet") or {},
            "members": [
                {
                    "asset_id": record["asset_id"],
                    "tile_id": record["member"].get("tile_id"),
                    "role": record["member"].get("role"),
                    "source_rect": record["source_rect"],
                }
                for record in records
            ],
            "prompt": request.prompt,
            "generator": model_name,
            "actual_seed": actual_seed,
        },
    )
    return output_ids


def _tile_group_request(plan: dict[str, Any], group: dict[str, Any]) -> tuple[ImageGenerationRequest, dict[str, list[int]]]:
    tile_w, tile_h = _pair(group.get("tile_size")) or _pair(plan.get("tile_size")) or [64, 64]
    members = [member for member in group.get("members", []) or [] if isinstance(member, dict)]
    sheet = group.get("sheet") if isinstance(group.get("sheet"), dict) else {}
    columns = max(1, int(sheet.get("columns") or min(DEFAULT_TILE_GROUP_SHEET_COLUMNS, len(members) or 1)))
    gutter = max(0, int(sheet.get("gutter") or 0))
    rows = max(1, math.ceil(len(members) / columns))
    width = columns * tile_w + gutter * max(0, columns - 1)
    height = rows * tile_h + gutter * max(0, rows - 1)
    rects: dict[str, list[int]] = {}
    slot_lines: list[str] = []
    for index, member in enumerate(members):
        col = index % columns
        row = index // columns
        x = col * (tile_w + gutter)
        y = row * (tile_h + gutter)
        asset_id = str(member.get("asset_id") or member.get("tile_id"))
        rects[asset_id] = [x, y, tile_w, tile_h]
        slot_lines.append(
            f"- Slot {index + 1} ({asset_id}) rectangle x={x}..{x + tile_w - 1}, y={y}..{y + tile_h - 1}: "
            f"{member.get('role')} tile, {member.get('display_name') or asset_id}. {member.get('notes') or ''}"
        )
    prompt = _tile_group_prompt(plan, group, width, height, tile_w, tile_h, columns, rows, gutter, slot_lines)
    seed = int(_safe_int(plan.get("seed"), 0)) + abs(hash(str(group.get("group_id") or ""))) % 10000
    return (
        ImageGenerationRequest(
            prompt=prompt,
            style=ImageStyle.PIXEL_ART,
            size=(width, height),
            seed=seed,
            transparency=TransparencyMode.OPAQUE,
            tile_aligned=True,
            tile_size=(tile_w, tile_h),
            negative_prompt=", ".join(
                [
                    "visible grid lines",
                    "labels",
                    "text",
                    "watermark",
                    "sprite sheet frame",
                    "UI frame",
                    "transparent gaps",
                    "isolated icons",
                    "floating object shadows",
                    "perspective drift",
                ]
            ),
            metadata={"target_id": group.get("group_id"), "category": "background_tile_group"},
        ),
        rects,
    )


def _tile_group_prompt(
    plan: dict[str, Any],
    group: dict[str, Any],
    width: int,
    height: int,
    tile_w: int,
    tile_h: int,
    columns: int,
    rows: int,
    gutter: int,
    slot_lines: list[str],
) -> str:
    return "\n".join(
        [
            "TASK: Create one cohesive RPG tilemap background tile family as a single sprite sheet.",
            str(group.get("prompt") or group.get("display_name") or group.get("group_id")),
            "",
            "Sprite sheet contract:",
            f"- Group id: {group.get('group_id')}",
            f"- Group kind: {group.get('kind')}",
            f"- Sheet canvas: exactly {width}x{height} px",
            f"- Grid: {columns} columns x {rows} rows",
            f"- Each slot: exactly {tile_w}x{tile_h} px",
            f"- Gutter: {gutter} px; if present, keep it visually empty and not part of any tile.",
            "- Do not draw visible borders, labels, dividers, frames, grid lines, numbers, or text.",
            "- This is an asset catalog sheet, not a map preview. Adjacent slots in this sheet are separate catalog samples, not neighboring map cells.",
            "- Do not draw one continuous road, plaza, path, field, or scene spanning across multiple slots.",
            "- Do not draw black separator lines, shadow seams, crop marks, frame outlines, or any visible slot boundary.",
            "- Every slot must remain visually correct when cropped alone and placed anywhere on a tilemap.",
            "",
            "Slot definitions:",
            *slot_lines,
            "",
            "Tile consistency requirements:",
            "- All slots must share one palette, lighting direction, pixel density, outline weight, and texture scale.",
            "- Fill every tile slot edge-to-edge with opaque terrain pixels; no transparent margins and no icon composition.",
            "- Center, edge, corner, curve, and transition pieces must connect seamlessly to neighboring slots.",
            "- Edge and corner details must continue cleanly into adjacent tiles without abrupt texture scale changes.",
            "- Edge_top means the transition lies inside that single cropped tile, with the outside material at the top edge and the main material below it.",
            "- Edge_bottom means the transition lies inside that single cropped tile, with the main material above and the outside material at the bottom edge.",
            "- Edge_left means the transition lies inside that single cropped tile, with the outside material at the left edge and the main material to the right.",
            "- Edge_right means the transition lies inside that single cropped tile, with the main material to the left and the outside material at the right edge.",
            "- Corner tiles must contain only one corner transition inside their own cropped tile, not a whole rounded rectangle or full path segment.",
            "- Keep top-down RPG tilemap perspective consistent across every slot.",
            "- Use a cute, charming, colorful but harmonious pixel-art style unless the scene style explicitly says otherwise.",
            f"- Scene id: {plan.get('scene_id')}",
        ]
    )


def _slice_tile_group_sheet(sheet_path: Path, output_dir: Path, members: list[dict[str, Any]], rects: dict[str, list[int]]) -> list[dict[str, Any]]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("PIL not available for tile group slicing") from exc
    records: list[dict[str, Any]] = []
    with Image.open(sheet_path).convert("RGBA") as source:
        for member in members:
            asset_id = str(member.get("asset_id") or member.get("tile_id"))
            rect = rects[asset_id]
            x, y, w, h = rect
            tile = source.crop((x, y, x + w, y + h))
            tile.save(output_dir / f"{asset_id}.png", "PNG")
            tile.close()
            records.append({"asset_id": asset_id, "member": member, "source_rect": rect})
    return records


def _generate_procedural_tile_group_sheet(sheet_path: Path, group: dict[str, Any], members: list[dict[str, Any]], rects: dict[str, list[int]]) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("PIL not available for procedural tile family generation") from exc

    tile_size = _pair(group.get("tile_size")) or [64, 64]
    width = max((rect[0] + rect[2] for rect in rects.values()), default=tile_size[0])
    height = max((rect[1] + rect[3] for rect in rects.values()), default=tile_size[1])
    family = _procedural_family(str(group.get("group_id") or ""))
    sheet = Image.new("RGBA", (width, height), family["outside"] + (255,))
    for member in members:
        asset_id = str(member.get("asset_id") or member.get("tile_id"))
        rect = rects[asset_id]
        role = str(member.get("role") or "center")
        tile = _procedural_tile(tile_size[0], tile_size[1], role, family, asset_id)
        sheet.paste(tile, (rect[0], rect[1]))
        tile.close()
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, "PNG")
    sheet.close()


def _procedural_family(group_id: str) -> dict[str, Any]:
    if "plaza" in group_id:
        return {
            "inside": (236, 222, 199),
            "inside_alt": (245, 233, 214),
            "outside": (104, 181, 78),
            "outside_alt": (143, 210, 87),
            "line": (170, 139, 108),
            "accent": (255, 200, 118),
            "shape": "rounded_rect",
            "pattern": "brick",
        }
    if "walkway" in group_id:
        return {
            "inside": (203, 147, 89),
            "inside_alt": (226, 174, 108),
            "outside": (104, 181, 78),
            "outside_alt": (143, 210, 87),
            "line": (139, 97, 62),
            "accent": (241, 200, 126),
            "shape": "straight",
            "pattern": "cobble",
        }
    return {
        "inside": (111, 188, 81),
        "inside_alt": (149, 215, 88),
        "outside": (111, 188, 81),
        "outside_alt": (149, 215, 88),
        "line": (79, 148, 70),
        "accent": (252, 219, 94),
        "shape": "full",
        "pattern": "grass",
    }


def _procedural_tile(width: int, height: int, role: str, family: dict[str, Any], asset_id: str):
    from PIL import Image, ImageDraw

    outside = family["outside"]
    inside = family["inside"]
    tile = Image.new("RGBA", (width, height), outside + (255,))
    draw = ImageDraw.Draw(tile, "RGBA")
    _draw_texture(draw, width, height, outside, family["outside_alt"], family["line"], "grass", seed=asset_id + "_outside")

    mask_box = _inside_mask_box(width, height, role)
    radius = 14 if family.get("shape") == "rounded_rect" else 0
    if mask_box is not None:
        if radius and "corner" in role:
            _draw_corner_inside(draw, width, height, role, family)
        else:
            draw.rounded_rectangle(mask_box, radius=radius, fill=inside + (255,))
            _draw_inside_pattern(draw, mask_box, family, asset_id)
    else:
        draw.rectangle((0, 0, width, height), fill=inside + (255,))
        _draw_inside_pattern(draw, (0, 0, width - 1, height - 1), family, asset_id)

    if family.get("pattern") == "grass":
        _draw_texture(draw, width, height, family["inside"], family["inside_alt"], family["line"], "grass", seed=asset_id)
    return tile


def _inside_mask_box(width: int, height: int, role: str) -> tuple[int, int, int, int] | None:
    margin = max(8, width // 6)
    if role in {"center", "center_variant", "straight_horizontal", "straight_vertical"}:
        return None
    if role in {"edge_top", "transition_edge_top"}:
        return (0, margin, width - 1, height - 1)
    if role in {"edge_bottom", "transition_edge_bottom"}:
        return (0, 0, width - 1, height - margin - 1)
    if role in {"edge_left", "transition_edge_left"}:
        return (margin, 0, width - 1, height - 1)
    if role in {"edge_right", "transition_edge_right"}:
        return (0, 0, width - margin - 1, height - 1)
    if role in {"corner_top_left", "transition_corner_top_left", "curve_top_left"}:
        return (margin, margin, width - 1, height - 1)
    if role in {"corner_top_right", "transition_corner_top_right", "curve_top_right"}:
        return (0, margin, width - margin - 1, height - 1)
    if role in {"corner_bottom_left", "transition_corner_bottom_left", "curve_bottom_left"}:
        return (margin, 0, width - 1, height - margin - 1)
    if role in {"corner_bottom_right", "transition_corner_bottom_right", "curve_bottom_right"}:
        return (0, 0, width - margin - 1, height - margin - 1)
    return None


def _draw_corner_inside(draw, width: int, height: int, role: str, family: dict[str, Any]) -> None:
    margin = max(8, width // 6)
    inside = family["inside"]
    radius = 18
    if "top_left" in role:
        box = (margin, margin, width + radius, height + radius)
    elif "top_right" in role:
        box = (-radius, margin, width - margin - 1, height + radius)
    elif "bottom_left" in role:
        box = (margin, -radius, width + radius, height - margin - 1)
    else:
        box = (-radius, -radius, width - margin - 1, height - margin - 1)
    draw.rounded_rectangle(box, radius=radius, fill=inside + (255,))
    _draw_inside_pattern(draw, (0, 0, width - 1, height - 1), family, f"{role}_corner")


def _draw_inside_pattern(draw, box: tuple[int, int, int, int], family: dict[str, Any], seed: str) -> None:
    x0, y0, x1, y1 = box
    pattern = str(family.get("pattern") or "brick")
    if pattern == "brick":
        brick_w, brick_h = 16, 9
        for y in range(y0 - (y0 % brick_h), y1 + brick_h, brick_h):
            offset = 8 if (y // brick_h) % 2 else 0
            for x in range(x0 - brick_w, x1 + brick_w, brick_w):
                xx = x + offset
                draw.rectangle((xx, y, xx + brick_w - 2, y + brick_h - 2), outline=family["line"] + (95,))
        _draw_texture(draw, x1 - x0 + 1, y1 - y0 + 1, family["inside"], family["inside_alt"], family["accent"], "flecks", seed=seed, offset=(x0, y0))
    elif pattern == "cobble":
        stone_w, stone_h = 18, 13
        for y in range(y0 - (y0 % stone_h), y1 + stone_h, stone_h):
            offset = 9 if (y // stone_h) % 2 else 0
            for x in range(x0 - stone_w, x1 + stone_w, stone_w):
                xx = x + offset
                draw.rounded_rectangle((xx + 1, y + 1, xx + stone_w - 3, y + stone_h - 3), radius=3, fill=family["inside_alt"] + (120,), outline=family["line"] + (100,))


def _draw_texture(draw, width: int, height: int, base: tuple[int, int, int], alt: tuple[int, int, int], line: tuple[int, int, int], kind: str, seed: str, offset: tuple[int, int] = (0, 0)) -> None:
    import hashlib

    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    count = 58 if kind == "grass" else 28
    ox, oy = offset
    for i in range(count):
        a = digest[i % len(digest)]
        b = digest[(i * 7 + 3) % len(digest)]
        x = ox + (a * 37 + i * 11) % max(1, width)
        y = oy + (b * 29 + i * 17) % max(1, height)
        color = alt if i % 4 else line
        if kind == "grass":
            draw.line((x, y, x + 2, y - 3), fill=color + (100,), width=1)
        else:
            draw.rectangle((x, y, x + 1, y + 1), fill=color + (115,))


def _create_background_image_generator(output_dir: Path, use_gemini: bool):
    if use_gemini:
        from generator.assets.gemini_generator import GeminiImageGenerator

        return GeminiImageGenerator(output_dir)
    return MockImageGenerator(output_dir)


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _composite_placement(target: dict[str, Any], map_spec: dict[str, Any]) -> str | None:
    composite_id = str(target.get("composite_id") or target.get("id") or "")
    for comp in map_spec.get("composites", []) or []:
        if isinstance(comp, dict) and str(comp.get("id") or "") == composite_id:
            placement = comp.get("placement")
            return str(placement) if placement else None
    return None


def _attach_suggested_crop_rects(plan: dict[str, Any]) -> None:
    if not _pair(plan.get("image_size")):
        return
    entities = {
        str(entity.get("id")): entity
        for entity in plan.get("background_entities", []) or []
        if isinstance(entity, dict)
    }
    for item in plan.get("review_items", []) or []:
        if not isinstance(item, dict) or _valid_rect(item.get("suggested_crop_rect")):
            continue
        if item.get("kind") == "base_terrain":
            item["suggested_crop_rect"] = _base_suggested_rect(plan, item)
        elif item.get("kind") == "composite_part":
            entity = entities.get(str(item.get("composite_id") or ""))
            item["suggested_crop_rect"] = _composite_suggested_rect(plan, entity, item)


def _base_suggested_rect(plan: dict[str, Any], item: dict[str, Any]) -> list[int] | None:
    image_size = _pair(plan.get("image_size"))
    if not image_size:
        return None
    crop_w, crop_h = _target_size(item, plan)
    return _clamped_rect((image_size[0] - crop_w) / 2, (image_size[1] - crop_h) / 2, crop_w, crop_h, image_size)


def _composite_suggested_rect(plan: dict[str, Any], entity: dict[str, Any] | None, item: dict[str, Any]) -> list[int] | None:
    image_size = _pair(plan.get("image_size"))
    map_size = _pair(plan.get("map_size"))
    if not image_size:
        return None
    crop_w, crop_h = _target_size(item, plan)
    if not entity or not map_size:
        return _fallback_suggested_rect(plan, item)

    placement_region = _region_for_entity(plan, entity)
    footprint = _pair(entity.get("footprint"), fallback=[1, 1]) or [1, 1]
    layout = [cell for cell in entity.get("layout", []) or [] if isinstance(cell, dict)]
    cell = _representative_layout_cell(layout, str(item.get("part_key") or ""))
    if not placement_region or not cell:
        return _fallback_suggested_rect(plan, item)

    bounds = placement_region.get("bounds")
    if not (isinstance(bounds, list) and len(bounds) == 4):
        return _fallback_suggested_rect(plan, item)

    scale_x = image_size[0] / max(1, map_size[0])
    scale_y = image_size[1] / max(1, map_size[1])
    region_x = float(bounds[0]) * scale_x
    region_y = float(bounds[1]) * scale_y
    region_w = float(bounds[2]) * scale_x
    region_h = float(bounds[3]) * scale_y
    cell_w = region_w / max(1, footprint[0])
    cell_h = region_h / max(1, footprint[1])
    comp_w = cell_w * footprint[0]
    comp_h = cell_h * footprint[1]
    origin_x = region_x + (region_w - comp_w) / 2
    origin_y = region_y + (region_h - comp_h) / 2
    center_x = origin_x + (float(cell.get("x", 0)) + 0.5) * cell_w
    center_y = origin_y + (float(cell.get("y", 0)) + 0.5) * cell_h
    return _clamped_rect(center_x - crop_w / 2, center_y - crop_h / 2, crop_w, crop_h, image_size)


def _fallback_suggested_rect(plan: dict[str, Any], item: dict[str, Any]) -> list[int] | None:
    image_size = _pair(plan.get("image_size"))
    if not image_size:
        return None
    crop_w, crop_h = _target_size(item, plan)
    text = f"{item.get('composite_id') or ''} {item.get('id') or ''} {item.get('part_key') or ''}".lower()
    if "top_right" in text or "track" in text:
        return _clamped_rect(image_size[0] * 0.72, image_size[1] * 0.18, crop_w, crop_h, image_size)
    if "bottom_left" in text or "road" in text or "cross" in text:
        return _clamped_rect(image_size[0] * 0.18, image_size[1] * 0.72, crop_w, crop_h, image_size)
    return _clamped_rect((image_size[0] - crop_w) / 2, (image_size[1] - crop_h) / 2, crop_w, crop_h, image_size)


def _target_size(item: dict[str, Any], plan: dict[str, Any]) -> list[int]:
    return _pair(item.get("target_size")) or _pair(plan.get("tile_size")) or [64, 64]


def _pair(value: Any, fallback: list[int] | None = None) -> list[int] | None:
    if isinstance(value, list) and len(value) == 2 and all(isinstance(item, int | float) and int(item) > 0 for item in value):
        return [int(value[0]), int(value[1])]
    return fallback


def _region_for_entity(plan: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any] | None:
    placement = str(entity.get("placement") or "")
    entity_type = str(entity.get("type") or "")
    entity_id = str(entity.get("id") or "")
    for region in plan.get("regions", []) or []:
        if not isinstance(region, dict):
            continue
        region_id = str(region.get("id") or "")
        region_type = str(region.get("type") or "")
        if placement and placement in {region_id, region_type}:
            return region
        if entity_type and (entity_type == region_type or entity_type in region_type or region_type in entity_type):
            return region
        if entity_id and region_id and region_id in entity_id:
            return region
    return None


def _representative_layout_cell(layout: list[dict[str, Any]], part_key: str) -> dict[str, Any] | None:
    candidates = [cell for cell in layout if str(cell.get("part") or "") == part_key]
    if not candidates:
        return None
    max_x = max(int(cell.get("x", 0)) for cell in layout) if layout else 0
    max_y = max(int(cell.get("y", 0)) for cell in layout) if layout else 0
    center_x = max_x / 2
    center_y = max_y / 2
    return min(candidates, key=lambda cell: abs(float(cell.get("x", 0)) - center_x) + abs(float(cell.get("y", 0)) - center_y))


def _clamped_rect(x: float, y: float, width: int, height: int, image_size: list[int]) -> list[int]:
    max_x = max(0, image_size[0] - width)
    max_y = max(0, image_size[1] - height)
    return [
        int(round(max(0, min(max_x, x)))),
        int(round(max(0, min(max_y, y)))),
        int(width),
        int(height),
    ]


def _review_html(plan: dict[str, Any]) -> str:
    plan_json = json.dumps(plan, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("__PLAN_JSON__", plan_json)


def _image_size(path: Path) -> list[int] | None:
    if not path.exists():
        return None
    try:
        from PIL import Image

        with Image.open(path) as image:
            return [image.width, image.height]
    except Exception:
        return None


def _relative_to_scene(scene_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(scene_dir)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _valid_rect(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(item, int | float) and int(item) >= 0 for item in value)
        and int(value[2]) > 0
        and int(value[3]) > 0
    )


def _safe_id(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "background_tile"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Background Tile Review</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f4ed;
      --panel: #fffdf8;
      --ink: #24201a;
      --muted: #70675c;
      --line: #d6c8b5;
      --accent: #256f5d;
      --accent-soft: rgba(37, 111, 93, .16);
      --warn: #9a5c10;
      --bad: #9b2f2f;
      --shadow: rgba(53, 40, 24, .12);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--ink); }
    header {
      min-height: 52px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { font-size: 16px; margin: 0; font-weight: 650; }
    h2 { font-size: 14px; margin: 16px 0 8px; }
    button, select { font: inherit; }
    button {
      min-height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 6px 10px;
      cursor: pointer;
    }
    button:hover { border-color: var(--accent); }
    button.active { background: var(--accent); border-color: var(--accent); color: white; }
    main { display: grid; grid-template-columns: minmax(460px, 1fr) 400px; height: calc(100vh - 52px); }
    .stage { min-width: 0; overflow: auto; padding: 16px; }
    .canvas-wrap {
      width: min(100%, 1024px);
      position: relative;
      border: 1px solid var(--line);
      background: #d8c28a;
      box-shadow: 0 8px 24px var(--shadow);
    }
    canvas { display: block; width: 100%; height: auto; image-rendering: pixelated; }
    aside { border-left: 1px solid var(--line); background: var(--panel); overflow: auto; padding: 12px; }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
    .hint { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .status { min-width: 12em; color: var(--muted); font-size: 12px; text-align: right; }
    .items { display: grid; gap: 8px; margin-top: 10px; }
    .item {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
      padding: 8px;
      cursor: pointer;
    }
    .item.selected { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); background: var(--accent-soft); }
    .item-title { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; font-weight: 650; }
    .item-title span:first-child { overflow-wrap: anywhere; }
    .item-meta { margin-top: 4px; color: var(--muted); font-size: 12px; line-height: 1.35; overflow-wrap: anywhere; }
    .method { color: var(--warn); white-space: nowrap; }
    .method.extract_from_concept, .method.extract_and_cleanup { color: var(--accent); }
    .method.ignore { color: var(--bad); }
    .field { display: grid; gap: 4px; margin-bottom: 10px; }
    textarea {
      width: 100%;
      min-height: 220px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12px;
      line-height: 1.45;
      background: white;
      color: var(--ink);
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; height: auto; }
      aside { border-left: 0; border-top: 1px solid var(--line); }
      .status { text-align: left; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Background Tile Review</h1>
    <div class="row" style="margin:0">
      <span class="status" id="copyStatus">复制后替换 background_plan.json</span>
      <button id="copyBtn">复制 JSON</button>
      <button id="exportBtn">下载 JSON</button>
    </div>
  </header>
  <main>
    <section class="stage" id="stage">
      <div class="canvas-wrap">
        <canvas id="canvas"></canvas>
      </div>
      <p class="hint">选择右侧条目后会自动显示系统建议裁剪框；直接拖拽画布可调整当前条目的 crop_rect。页面不会写回本地文件，确认后复制下方 JSON 并替换 background_plan.json。</p>
    </section>
    <aside>
      <div class="row">
        <button id="fullBackgroundBtn">整图背景</button>
        <button data-method="extract_from_concept">直接裁剪</button>
        <button data-method="extract_and_cleanup">裁后修整</button>
        <button data-method="regenerate">重新生成</button>
        <button data-method="ignore">忽略</button>
      </div>
      <label class="row"><input type="checkbox" id="snap" checked> 吸附网格</label>
      <label class="row">网格
        <select id="gridMode">
          <option value="crop" selected>裁剪格</option>
          <option value="map">地图格</option>
          <option value="none">隐藏</option>
        </select>
      </label>
      <div class="hint" id="gridInfo"></div>
      <div class="hint" id="selectionInfo"></div>
      <div class="items" id="items"></div>
      <h2>导出内容</h2>
      <div class="field">
        <div class="hint">file:// 页面不能稳定静默写盘；使用复制按钮，或在复制失败时手动 Ctrl+C。</div>
        <textarea id="jsonOut" spellcheck="false"></textarea>
      </div>
    </aside>
  </main>
  <script>
    const plan = __PLAN_JSON__;
    const items = plan.review_items || [];
    if (!plan.background_image) {
      plan.background_image = {
        method: 'review_required',
        status: 'pending_review',
        source_image: plan.concept_image,
        output_path: 'background/background.png',
      };
    }
    const methodLabels = {
      extract_or_regenerate: '待确认',
      extract_from_concept: '直接裁剪',
      extract_and_cleanup: '裁后修整',
      regenerate: '重新生成',
      ignore: '忽略',
    };
    let selected = null;
    let image = new Image();
    let dragging = false;
    let dragStart = null;
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const stage = document.getElementById('stage');
    const itemList = document.getElementById('items');
    const jsonOut = document.getElementById('jsonOut');
    const snap = document.getElementById('snap');
    const gridMode = document.getElementById('gridMode');
    const gridInfo = document.getElementById('gridInfo');
    const selectionInfo = document.getElementById('selectionInfo');
    const copyStatus = document.getElementById('copyStatus');

    image.onload = () => {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      plan.image_size = [canvas.width, canvas.height];
      selectItem(items[0] || null, {focus: false});
    };
    image.onerror = () => {
      copyStatus.textContent = '概念图加载失败，请检查 concept_image 路径';
      updateJson();
      renderItems();
    };
    image.src = plan.concept_image;

    function gridStep() {
      if (gridMode.value === 'none' || !canvas.width || !canvas.height) return null;
      if (gridMode.value === 'map') {
        const map = plan.map_size || [64, 64];
        return [canvas.width / map[0], canvas.height / map[1]];
      }
      const tile = plan.tile_size || [64, 64];
      return [Number(tile[0]) || 64, Number(tile[1]) || 64];
    }

    function snapPoint(p) {
      if (!snap.checked) return p;
      const step = gridStep();
      if (!step) return p;
      const [gx, gy] = step;
      return [Math.round(p[0] / gx) * gx, Math.round(p[1] / gy) * gy];
    }

    function canvasPoint(evt) {
      const rect = canvas.getBoundingClientRect();
      return [
        (evt.clientX - rect.left) * canvas.width / rect.width,
        (evt.clientY - rect.top) * canvas.height / rect.height,
      ];
    }

    function rectFromPoints(a, b) {
      const x1 = Math.max(0, Math.min(a[0], b[0]));
      const y1 = Math.max(0, Math.min(a[1], b[1]));
      const x2 = Math.min(canvas.width, Math.max(a[0], b[0]));
      const y2 = Math.min(canvas.height, Math.max(a[1], b[1]));
      return [Math.round(x1), Math.round(y1), Math.round(x2 - x1), Math.round(y2 - y1)];
    }

    function validRect(value) {
      return Array.isArray(value) && value.length === 4 && value.every((item) => Number.isFinite(Number(item))) && Number(value[2]) > 0 && Number(value[3]) > 0;
    }

    function cloneRect(value) {
      return validRect(value) ? value.map((item) => Math.round(Number(item))) : null;
    }

    function defaultRect(item) {
      const target = item?.target_size || plan.tile_size || [64, 64];
      const w = Math.max(1, Math.round(Number(target[0]) || 64));
      const h = Math.max(1, Math.round(Number(target[1]) || 64));
      return [
        Math.max(0, Math.round((canvas.width - w) / 2)),
        Math.max(0, Math.round((canvas.height - h) / 2)),
        Math.min(w, canvas.width || w),
        Math.min(h, canvas.height || h),
      ];
    }

    function ensureCropRect(item) {
      if (!item || validRect(item.crop_rect)) return;
      item.crop_rect = cloneRect(item.suggested_crop_rect) || defaultRect(item);
    }

    function selectItem(item, options = {}) {
      selected = item || null;
      ensureCropRect(selected);
      render();
      if (options.focus !== false) focusSelectedRect();
    }

    function focusSelectedRect() {
      if (!selected || !validRect(selected.crop_rect)) return;
      const r = selected.crop_rect;
      const scale = canvas.clientWidth / Math.max(1, canvas.width);
      stage.scrollTo({
        left: Math.max(0, (r[0] + r[2] / 2) * scale - stage.clientWidth / 2),
        top: Math.max(0, (r[1] + r[3] / 2) * scale - stage.clientHeight / 2),
        behavior: 'smooth',
      });
    }

    function render() {
      if (!canvas.width || !canvas.height) {
        renderItems();
        updateJson();
        return;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      drawGrid();
      for (const item of items) {
        if (!validRect(item.crop_rect)) continue;
        const r = item.crop_rect;
        ctx.save();
        ctx.strokeStyle = item === selected ? '#256f5d' : 'rgba(36,32,26,.55)';
        ctx.lineWidth = item === selected ? 4 : 2;
        ctx.strokeRect(r[0], r[1], r[2], r[3]);
        if (item === selected) {
          ctx.fillStyle = 'rgba(37, 111, 93, .12)';
          ctx.fillRect(r[0], r[1], r[2], r[3]);
        }
        ctx.restore();
      }
      renderItems();
      updateJson();
    }

    function drawGrid() {
      const step = gridStep();
      if (!step) return;
      const [gx, gy] = step;
      ctx.save();
      ctx.strokeStyle = gridMode.value === 'map' ? 'rgba(255,255,255,.16)' : 'rgba(255,255,255,.32)';
      ctx.lineWidth = 1;
      for (let x = 0; x <= canvas.width; x += gx) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y <= canvas.height; y += gy) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }
      ctx.restore();
    }

    function renderItems() {
      itemList.innerHTML = '';
      items.forEach((item) => {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'item' + (item === selected ? ' selected' : '');
        const crop = validRect(item.crop_rect) ? item.crop_rect.join(', ') : '未设置';
        const suggested = validRect(item.suggested_crop_rect) ? item.suggested_crop_rect.join(', ') : '无';
        el.innerHTML = `<div class="item-title"><span>${escapeHtml(item.display_name || item.id)}</span><span class="method ${item.method}">${methodLabels[item.method] || item.method}</span></div><div class="item-meta">${escapeHtml(item.kind || '')} | ${escapeHtml(item.id || '')}<br>crop: ${escapeHtml(crop)}<br>suggested: ${escapeHtml(suggested)}</div>`;
        el.onclick = () => selectItem(item);
        itemList.appendChild(el);
      });
      selectionInfo.textContent = selected ? `当前条目: ${selected.id}` : '没有 review item';
      const step = gridStep();
      gridInfo.textContent = step ? `${gridMode.value === 'map' ? '地图格' : '裁剪格'}: ${round2(step[0])} x ${round2(step[1])} px` : '网格: 隐藏';
      document.querySelectorAll('[data-method]').forEach((button) => {
        button.classList.toggle('active', Boolean(selected && selected.method === button.dataset.method));
      });
    }

    function updateJson() {
      jsonOut.value = JSON.stringify(plan, null, 2);
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
    }

    function round2(value) {
      return Math.round(value * 100) / 100;
    }

    canvas.addEventListener('pointerdown', (evt) => {
      if (!selected) return;
      dragging = true;
      dragStart = snapPoint(canvasPoint(evt));
      canvas.setPointerCapture(evt.pointerId);
    });
    canvas.addEventListener('pointermove', (evt) => {
      if (!dragging || !selected) return;
      const current = snapPoint(canvasPoint(evt));
      selected.crop_rect = rectFromPoints(dragStart, current);
      selected.status = 'reviewed';
      render();
    });
    canvas.addEventListener('pointerup', (evt) => {
      dragging = false;
      try { canvas.releasePointerCapture(evt.pointerId); } catch (err) {}
    });
    window.addEventListener('pointerup', () => { dragging = false; });
    gridMode.addEventListener('change', render);
    snap.addEventListener('change', render);
    document.querySelectorAll('[data-method]').forEach((button) => {
      button.addEventListener('click', () => {
        if (!selected) return;
        selected.method = button.dataset.method;
        selected.status = 'reviewed';
        ensureCropRect(selected);
        render();
      });
    });
    document.getElementById('fullBackgroundBtn').onclick = () => {
      plan.background_image.method = 'use_full_concept';
      plan.background_image.status = 'reviewed';
      plan.background_image.source_image = plan.concept_image;
      plan.background_image.output_path = plan.background_image.output_path || 'background/background.png';
      for (const item of items) {
        if (item.kind === 'base_terrain') {
          item.method = 'ignore';
          item.status = 'reviewed';
        }
      }
      copyStatus.textContent = '已选择整图背景，请复制 JSON';
      render();
    };
    document.getElementById('exportBtn').onclick = () => {
      const blob = new Blob([jsonOut.value + '\\n'], {type: 'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'background_plan.reviewed.json';
      a.click();
      URL.revokeObjectURL(a.href);
    };
    document.getElementById('copyBtn').onclick = async () => {
      updateJson();
      try {
        if (!navigator.clipboard) throw new Error('clipboard unavailable');
        await navigator.clipboard.writeText(jsonOut.value);
        copyStatus.textContent = '已复制，替换 background_plan.json';
      } catch (err) {
        jsonOut.focus();
        jsonOut.select();
        copyStatus.textContent = '浏览器限制复制，已选中 JSON，请按 Ctrl+C';
      }
    };
  </script>
</body>
</html>
"""

