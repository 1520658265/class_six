from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from generator.assets.image_generation import (
    ImageGenerationRequest,
    ImageValidation,
    ImageStyle,
    MockImageGenerator,
    TransparencyMode,
)

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress, record_error


def generate_scene_images(
    scene_dir: str | Path,
    use_gemini: bool = False,
    force: bool = False,
    variants: int = 1,
    target: str | None = None,
) -> list[str]:
    paths = scene_paths(scene_dir)
    art_request = _read_json(paths.art_request)
    prompts = _read_json(paths.prompts)
    style_profile = _read_json(paths.style_profile) if paths.style_profile.exists() else {}
    prompt_by_id = {item["target_id"]: item for item in prompts.get("prompts", [])}
    all_objects = list(art_request.get("objects", [])) + list(art_request.get("generation_targets", []))
    objects = list(all_objects)
    if target:
        expanded_targets = _expand_target_with_generation_group(prompts, target)
        objects = [item for item in objects if str(item.get("id")) in expanded_targets]
    if target and not objects:
        raise ValueError(f"unknown target_id: {target}")
    objects = _filter_full_background_covered_objects(paths, objects)
    paths.images_dir.mkdir(parents=True, exist_ok=True)
    mark_in_progress(paths.root, "6_images", total=len(objects), current_item=target)
    image_generator = None
    generated: list[str] = []
    generated_group_ids: set[str] = set()
    grouped_target_ids: set[str] = set()
    object_by_id = {str(item.get("id")): item for item in all_objects if isinstance(item, dict)}
    groups = _generation_groups_for_objects(prompts, object_by_id, {str(item.get("id")) for item in objects})

    for obj in objects:
        target_id = str(obj["id"])
        group = groups.get(target_id)
        if group:
            group_id = str(group["group_id"])
            grouped_target_ids.add(target_id)
            if group_id not in generated_group_ids:
                if image_generator is None:
                    image_generator = _create_image_generator(paths.images_dir / "_temp", use_gemini)
                generated.extend(
                    _generate_sprite_sheet_group(
                        group,
                        object_by_id,
                        prompt_by_id,
                        art_request,
                        style_profile,
                        image_generator,
                        paths.images_dir,
                        variants,
                        force,
                    )
                )
                generated_group_ids.add(group_id)
            continue
        png_path = paths.images_dir / f"{target_id}.png"
        json_path = paths.images_dir / f"{target_id}.json"
        if png_path.exists() and json_path.exists() and not force:
            generated.append(target_id)
            continue
        prompt = prompt_by_id.get(target_id) or _generated_prompt_for(obj)
        if not prompt:
            record_error(paths.root, "6_images", target_id, "missing prompt")
            continue
        if image_generator is None:
            image_generator = _create_image_generator(paths.images_dir / "_temp", use_gemini)
        request = _image_request(obj, prompt, art_request, style_profile)
        response = image_generator.generate(request)
        if not response.success:
            record_error(paths.root, "6_images", target_id, response.error or "image generation failed")
            continue
        response.validation = _validate_scene_asset_image(response.image_path, request)
        _move_if_needed(response.image_path, png_path)
        _write_metadata(json_path, target_id, obj, prompt, response, request, variants)
        if obj.get("asset_role") == "composite_source":
            _slice_composite_source(png_path, obj, paths.images_dir)
        generated.append(target_id)

    mark_completed(paths.root, "6_images")
    return [item for item in generated if item in {str(obj.get("id")) for obj in objects} or item in grouped_target_ids]


def _expand_target_with_generation_group(prompts: dict[str, Any], target: str) -> set[str]:
    for group in prompts.get("generation_groups", []) or []:
        if not isinstance(group, dict):
            continue
        target_ids = {str(item.get("target_id")) for item in group.get("targets", []) if isinstance(item, dict)}
        if target in target_ids:
            return target_ids
    return {target}


def _image_request(obj: dict[str, Any], prompt: dict[str, Any], art_request: dict[str, Any], style_profile: dict[str, Any] | None = None) -> ImageGenerationRequest:
    category = str(obj.get("category") or "small_prop")
    description = _build_scene_prompt(obj, prompt, art_request, style_profile or {})
    negative = list(prompt.get("negative") or [])
    if category == "text_sign":
        negative.extend(["readable text", "Chinese characters", "letters", "handwriting"])
    transparency = _transparency_for(obj, prompt)
    negative.extend(_default_negative_terms(category, transparency))
    return ImageGenerationRequest(
        prompt=description,
        style=ImageStyle.PIXEL_ART,
        size=tuple(obj.get("source_canvas") or (64, 64)),
        seed=int(art_request.get("seed") or 0) + abs(hash(obj["id"])) % 10000,
        transparency=transparency,
        tile_aligned=True,
        tile_size=tuple(art_request.get("tile_size") or (32, 32)),
        negative_prompt=", ".join(str(item) for item in negative),
        metadata={
            "target_id": obj["id"],
            "category": category,
            "footprint": obj.get("footprint"),
            "anchor": obj.get("anchor"),
        },
    )


def _transparency_for(obj: dict[str, Any], prompt: dict[str, Any]) -> TransparencyMode:
    category = str(obj.get("category") or "")
    asset_role = str(obj.get("asset_role") or "")
    target_id = str(obj.get("id") or "")
    body = str(prompt.get("body") or "").lower()
    if category == "terrain_tile" or asset_role == "base_terrain":
        return TransparencyMode.OPAQUE
    if asset_role == "composite_source" or category == "composite_source":
        return TransparencyMode.OPAQUE
    if category == "composite_tile":
        if target_id.endswith("_center_01") or "center tile" in body or "no edge" in body:
            return TransparencyMode.OPAQUE
        return TransparencyMode.REQUIRED
    return TransparencyMode.REQUIRED


def _generation_groups_for_objects(
    prompts: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
    active_ids: set[str],
) -> dict[str, dict[str, Any]]:
    groups_by_target: dict[str, dict[str, Any]] = {}
    for group in prompts.get("generation_groups", []) or []:
        if not isinstance(group, dict):
            continue
        targets = [str(item.get("target_id")) for item in group.get("targets", []) if isinstance(item, dict)]
        if not targets or not any(target_id in active_ids for target_id in targets):
            continue
        missing = [target_id for target_id in targets if target_id not in object_by_id]
        if missing:
            raise ValueError(f"generation group {group.get('group_id')} references unknown targets: {', '.join(missing)}")
        for target_id in targets:
            groups_by_target[target_id] = group
    return groups_by_target


def _generate_sprite_sheet_group(
    group: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
    prompt_by_id: dict[str, dict[str, Any]],
    art_request: dict[str, Any],
    style_profile: dict[str, Any],
    image_generator,
    images_dir: Path,
    variants: int,
    force: bool,
) -> list[str]:
    group_id = str(group["group_id"])
    target_specs = [item for item in group.get("targets", []) if isinstance(item, dict)]
    target_ids = [str(item["target_id"]) for item in target_specs]
    output_paths = [images_dir / f"{target_id}.png" for target_id in target_ids]
    output_json_paths = [images_dir / f"{target_id}.json" for target_id in target_ids]
    group_png = images_dir / f"_group_{group_id}.png"
    group_json = images_dir / f"_group_{group_id}.json"
    if not force and group_png.exists() and group_json.exists() and all(path.exists() for path in output_paths + output_json_paths):
        return target_ids

    group_request = _sprite_sheet_group_request(group, object_by_id, prompt_by_id, art_request, style_profile)
    response = image_generator.generate(group_request)
    if not response.success:
        raise RuntimeError(response.error or f"generation group failed: {group_id}")
    _move_if_needed(response.image_path, group_png)

    slot_records = _slice_sprite_sheet_group(group_png, group, images_dir)
    validations: dict[str, ImageValidation | None] = {}
    slot_requests: dict[str, ImageGenerationRequest] = {}
    for record in slot_records:
        target_id = str(record["target_id"])
        obj = object_by_id[target_id]
        prompt = prompt_by_id.get(target_id) or _generated_prompt_for(obj) or {"target_id": target_id, "body": obj.get("display_name") or target_id}
        slot_request = _image_request(obj, prompt, art_request, style_profile)
        slot_requests[target_id] = slot_request
        validations[target_id] = _validate_scene_asset_image(str(images_dir / f"{target_id}.png"), slot_request)

    _apply_group_size_warnings(group, images_dir, validations)

    for record in slot_records:
        target_id = str(record["target_id"])
        obj = object_by_id[target_id]
        prompt = prompt_by_id.get(target_id) or _generated_prompt_for(obj) or {"target_id": target_id, "body": obj.get("display_name") or target_id}
        _write_group_member_metadata(
            images_dir / f"{target_id}.json",
            target_id,
            obj,
            prompt,
            response,
            slot_requests[target_id],
            group_request,
            group,
            record,
            validations[target_id],
            variants,
        )

    group_json.write_text(
        json.dumps(
            {
                "group_id": group_id,
                "mode": group.get("mode"),
                "sprite_path": group_png.name,
                "targets": target_ids,
                "slot_size": group.get("slot_size"),
                "gutter": int(group.get("gutter") or 0),
                "direction": group.get("direction") or "horizontal",
                "full_prompt": group_request.prompt,
                "generator": response.model,
                "actual_seed": response.actual_seed,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target_ids


def _sprite_sheet_group_request(
    group: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
    prompt_by_id: dict[str, dict[str, Any]],
    art_request: dict[str, Any],
    style_profile: dict[str, Any],
) -> ImageGenerationRequest:
    slot_w, slot_h = [int(value) for value in group.get("slot_size", [64, 64])]
    gutter = int(group.get("gutter") or 0)
    direction = str(group.get("direction") or "horizontal")
    targets = [item for item in group.get("targets", []) if isinstance(item, dict)]
    count = len(targets)
    if direction == "vertical":
        size = (slot_w, slot_h * count + gutter * max(0, count - 1))
    else:
        size = (slot_w * count + gutter * max(0, count - 1), slot_h)
    prompt = _build_sprite_sheet_group_prompt(group, object_by_id, prompt_by_id, art_request, style_profile, size)
    negative = list(group.get("negative") or [])
    for item in targets:
        target_prompt = prompt_by_id.get(str(item.get("target_id"))) or {}
        negative.extend(target_prompt.get("negative") or [])
    negative.extend(_default_negative_terms("npc", TransparencyMode.REQUIRED))
    return ImageGenerationRequest(
        prompt=prompt,
        style=ImageStyle.PIXEL_ART,
        size=size,
        seed=int(art_request.get("seed") or 0) + abs(hash(str(group.get("group_id")))) % 10000,
        transparency=TransparencyMode.REQUIRED,
        tile_aligned=False,
        tile_size=tuple(art_request.get("tile_size") or (32, 32)),
        negative_prompt=", ".join(str(item) for item in dict.fromkeys(negative)),
        metadata={"target_id": group.get("group_id"), "category": "sprite_sheet_group"},
    )


def _build_sprite_sheet_group_prompt(
    group: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
    prompt_by_id: dict[str, dict[str, Any]],
    art_request: dict[str, Any],
    style_profile: dict[str, Any],
    sheet_size: tuple[int, int],
) -> str:
    slot_w, slot_h = [int(value) for value in group.get("slot_size", [64, 64])]
    gutter = int(group.get("gutter") or 0)
    direction = str(group.get("direction") or "horizontal")
    targets = [item for item in group.get("targets", []) if isinstance(item, dict)]
    slot_lines: list[str] = []
    rects = _sprite_sheet_slot_rects(group)
    for index, item in enumerate(targets):
        target_id = str(item["target_id"])
        obj = object_by_id[target_id]
        prompt = prompt_by_id.get(target_id) or {}
        x, y, w, h = rects[target_id]
        variant = str(item.get("variant_notes") or prompt.get("body") or obj.get("display_name") or target_id)
        slot_lines.append(f"- Slot {index + 1} ({target_id}) rectangle x={x}..{x + w - 1}, y={y}..{y + h - 1}: {variant}")
    body = str(group.get("prompt") or "Create a consistent sprite sheet for these related RPG map objects.")
    scale_lines = []
    if group.get("same_visual_size", True):
        width_tol = int(group.get("bbox_width_tolerance") or 12)
        height_tol = int(group.get("bbox_height_tolerance") or 12)
        scale_lines.extend(
            [
                f"- All listed sprites must share the same visual body scale inside their own {slot_w}x{slot_h} px slots.",
                f"- Their visible alpha silhouette widths should differ by no more than {width_tol} px.",
                f"- Their visible alpha silhouette heights should differ by no more than {height_tol} px.",
                "- Keep head size, torso size, outline thickness, camera angle, and pixel density consistent across all slots.",
                "- Only pose, accent details, and small design differences may vary.",
            ]
        )
    return "\n".join(
        [
            "TASK: Create one sprite sheet containing multiple related transparent RPG map sprites.",
            body,
            "",
            "Sprite sheet contract:",
            f"- Group id: {group.get('group_id')}",
            f"- Sheet canvas: {sheet_size[0]}x{sheet_size[1]} px",
            f"- Layout direction: {direction}",
            f"- Each slot size: {slot_w}x{slot_h} px",
            f"- Gutter between slots: {gutter} px; keep gutters completely empty technical background.",
            "- Do not draw borders, labels, dividers, frames, grid lines, or text.",
            "",
            "Slot definitions:",
            *slot_lines,
            "",
            "Shared style requirements:",
            *_style_prompt_lines(style_profile or {}),
            "",
            "Consistency requirements:",
            *scale_lines,
            _facing_prompt_line(str(object_by_id[str(targets[0]["target_id"])].get("facing") or "")) if targets else "- Orientation: keep a neutral RPG top-down 3/4 view.",
            "- Center each sprite inside its own slot with transparent alpha outside the object after processing.",
            "- Use a tight transparent margin in each slot without touching slot edges.",
            "- Draw each target as a separate sprite inside its own slot; do not let sprites overlap across slots.",
        ]
    )


def _sprite_sheet_slot_rects(group: dict[str, Any]) -> dict[str, tuple[int, int, int, int]]:
    slot_w, slot_h = [int(value) for value in group.get("slot_size", [64, 64])]
    gutter = int(group.get("gutter") or 0)
    direction = str(group.get("direction") or "horizontal")
    rects: dict[str, tuple[int, int, int, int]] = {}
    for index, item in enumerate(group.get("targets", []) or []):
        if not isinstance(item, dict):
            continue
        if direction == "vertical":
            rect = (0, index * (slot_h + gutter), slot_w, slot_h)
        else:
            rect = (index * (slot_w + gutter), 0, slot_w, slot_h)
        rects[str(item["target_id"])] = rect
    return rects


def _default_negative_terms(category: str, transparency: TransparencyMode) -> list[str]:
    terms = ["watermark", "signature", "UI frame", "visible grid"]
    if transparency == TransparencyMode.REQUIRED:
        terms.extend(
            [
                "checkerboard",
                "transparency grid",
                "gray checker pattern",
                "mock transparent background",
                "background panel",
                "square backdrop",
                "colored rectangle behind the object",
                "floor plane behind the object",
                "scene background behind the object",
            ]
        )
    if category == "npc":
        terms.extend(["tiny icon", "small distant character", "cropped body"])
    return terms


def _validate_scene_asset_image(image_path: str | None, request: ImageGenerationRequest) -> ImageValidation | None:
    if not image_path:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        image = Image.open(image_path).convert("RGBA")
    except Exception as exc:
        return ImageValidation(
            passed=False,
            has_transparency=False,
            has_clean_edges=False,
            size_correct=False,
            tile_aligned=False,
            errors=[f"failed to open image: {exc}"],
        )

    errors: list[str] = []
    warnings: list[str] = []
    size_correct = image.size == request.size
    if not size_correct:
        errors.append(f"size mismatch: expected {request.size}, got {image.size}")
    tile_aligned = image.width % request.tile_size[0] == 0 and image.height % request.tile_size[1] == 0
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()
    has_transparency = extrema[0] < 255
    if request.transparency == TransparencyMode.REQUIRED and not has_transparency:
        errors.append("image has no transparent pixels")
    bbox = alpha.getbbox()
    if request.transparency == TransparencyMode.REQUIRED and bbox is None:
        errors.append("image is fully transparent")
    has_clean_edges = True
    if request.transparency == TransparencyMode.REQUIRED and bbox is not None:
        left, top, right, bottom = bbox
        margins = [left, top, image.width - right, image.height - bottom]
        if min(margins) == 0:
            has_clean_edges = False
            warnings.append("non-transparent pixels touch the canvas edge")
        coverage = ((right - left) * (bottom - top)) / float(image.width * image.height)
        category = str((request.metadata or {}).get("category") or "")
        min_coverage = 0.18 if category == "npc" else 0.22
        if coverage < min_coverage:
            warnings.append(f"object bbox coverage is small: {coverage:.1%}")
    fake_background = _fake_background_ratio(image)
    if fake_background > 0.20:
        errors.append(f"fake transparent/checker/background pixels remain: {fake_background:.1%}")
    image.close()
    return ImageValidation(
        passed=not errors,
        has_transparency=has_transparency,
        has_clean_edges=has_clean_edges,
        size_correct=size_correct,
        tile_aligned=tile_aligned,
        errors=errors,
        warnings=warnings,
    )


def _fake_background_ratio(image) -> float:
    total_nontransparent = 0
    fake = 0
    for r, g, b, a in image.getdata():
        if a == 0:
            continue
        total_nontransparent += 1
        is_gray_checker = abs(r - g) <= 4 and abs(g - b) <= 4 and 120 <= r <= 230
        is_chroma = r > 220 and b > 180 and g < 90
        if is_gray_checker or is_chroma:
            fake += 1
    if total_nontransparent == 0:
        return 0.0
    return fake / float(total_nontransparent)


def _build_scene_prompt(obj: dict[str, Any], prompt: dict[str, Any], art_request: dict[str, Any], style_profile: dict[str, Any] | None = None) -> str:
    category = str(obj.get("category") or "small_prop")
    footprint = obj.get("footprint") or [1, 1]
    source_canvas = obj.get("source_canvas") or [64, 64]
    runtime = obj.get("runtime_size") or [footprint[0] * 32, footprint[1] * 32]
    body = str(prompt.get("body") or obj.get("display_name") or obj["id"])
    transparency = _transparency_for(obj, prompt)
    if category == "terrain_tile":
        return _build_terrain_tile_prompt(obj, body, source_canvas, art_request)
    if category == "composite_source":
        return _build_composite_source_prompt(obj, body, source_canvas, art_request)
    if category == "composite_tile":
        return _build_composite_tile_prompt(obj, body, source_canvas, art_request, transparency)
    lines = [
        "TASK: Create one isolated transparent PNG sprite asset for an RPG map object.",
        body,
        "",
        "Asset contract:",
        f"- Target id: {obj['id']}",
        f"- Category: {category}",
        f"- Source canvas: {source_canvas[0]}x{source_canvas[1]} px",
        f"- Footprint in map: {footprint[0]}x{footprint[1]} tiles",
        f"- Runtime size: {runtime[0]}x{runtime[1]} px",
        f"- Tile size: {art_request.get('tile_size', [32, 32])[0]}x{art_request.get('tile_size', [32, 32])[1]} px",
        f"- Anchor: {obj.get('anchor') or 'center'}",
        f"- Facing: {obj.get('facing') or 'unspecified'}",
        "",
        "Shared style requirements:",
        *_style_prompt_lines(style_profile or {}),
        "",
        "Output requirements:",
        "- Pixel art, top-down 3/4 RPG view.",
        _facing_prompt_line(str(obj.get("facing") or "")),
        "- Final processed asset must have transparent alpha outside the object.",
        "- Do not draw checkerboard, transparency preview grid, gray squares, colored backdrop, terrain, floor, sky, or scene content behind it.",
        "- Use a tight transparent margin: keep the object fully visible but large enough to occupy roughly 70-85% of the useful canvas.",
        "- Avoid tiny icon composition; the asset must remain readable at the final map runtime size.",
        "- Draw exactly this object, centered and readable.",
    ]
    if category == "text_sign":
        lines.extend(
            [
                "- This is a blank sign or notice board sprite only.",
                "- Do not render readable text, Chinese characters, Latin letters, handwriting, slogans, or labels.",
            ]
        )
    return "\n".join(lines)


def _style_prompt_lines(style_profile: dict[str, Any]) -> list[str]:
    lines = [
        "- Use a cute, charming visual style with rounded, friendly shapes.",
        "- Use rich, colorful, bright-but-harmonious colors; avoid dull, muddy, monochrome, or overly desaturated palettes.",
    ]
    if style_profile.get("art_style"):
        lines.append(f"- Art style: {style_profile['art_style']}.")
    if style_profile.get("palette_mood"):
        lines.append(f"- Palette/mood: {style_profile['palette_mood']}.")
    if style_profile.get("lighting"):
        lines.append(f"- Lighting: {style_profile['lighting']}.")
    if style_profile.get("atmosphere"):
        lines.append(f"- Atmosphere: {style_profile['atmosphere']}.")
    traits = style_profile.get("visual_traits")
    if isinstance(traits, list) and traits:
        lines.append("- Visual traits: " + ", ".join(str(item) for item in traits) + ".")
    return lines


def _facing_prompt_line(facing: str) -> str:
    if facing == "faces_south" or facing == "faces_player":
        return "- Orientation: must face directly toward the viewer / south side of the map, with the front of the object centered and symmetrical in a top-down 3/4 RPG view."
    if facing == "east_west":
        return "- Orientation: must use an east-west neutral or symmetrical presentation, appropriate for the object's footprint."
    if facing == "north_south":
        return "- Orientation: must align on the north-south map axis."
    return "- Orientation: keep a neutral RPG top-down 3/4 view."


def _build_terrain_tile_prompt(obj: dict[str, Any], body: str, source_canvas: list[int], art_request: dict[str, Any]) -> str:
    tile_size = art_request.get("tile_size", [32, 32])
    return "\n".join(
        [
            "TASK: Create one opaque seamless terrain tile for an RPG tilemap.",
            body,
            "",
            "Asset contract:",
            f"- Target id: {obj['id']}",
            "- Category: terrain_tile",
            f"- Source canvas: {source_canvas[0]}x{source_canvas[1]} px",
            f"- Tile size: {tile_size[0]}x{tile_size[1]} px",
            "",
            "Output requirements:",
            "- Pixel art, top-down 3/4 RPG view.",
            "- Fill the entire canvas edge-to-edge with the terrain texture.",
            "- Seamless/tileable on all four sides.",
            "- Opaque PNG only; no alpha, no empty margin, no object silhouette.",
            "- Draw only the requested base terrain; no roads, tracks, props, buildings, text, sky, or UI frame.",
        ]
    )


def _build_composite_tile_prompt(
    obj: dict[str, Any],
    body: str,
    source_canvas: list[int],
    art_request: dict[str, Any],
    transparency: TransparencyMode,
) -> str:
    tile_size = art_request.get("tile_size", [32, 32])
    lines = [
        "TASK: Create one tile-scale component for a grid-composed RPG tilemap feature.",
        body,
        "",
        "Asset contract:",
        f"- Target id: {obj['id']}",
        "- Category: composite_tile",
        f"- Source canvas: {source_canvas[0]}x{source_canvas[1]} px",
        "- Footprint in map: 1x1 tile",
        f"- Tile size: {tile_size[0]}x{tile_size[1]} px",
        "- This is one reusable tile part, not a whole road, not a whole track, and not a full scene.",
        "",
        "Output requirements:",
        "- Pixel art, top-down 3/4 RPG view.",
        "- Align the road/track geometry exactly to the 32x32 tile grid and tile edges named by this target.",
        "- Keep the shape readable at final 32x32 size.",
    ]
    if transparency == TransparencyMode.OPAQUE:
        lines.extend(
            [
                "- Opaque PNG only; fill the entire tile with the requested road or track surface.",
                "- No alpha or empty margin; do not include terrain border unless explicitly requested.",
            ]
        )
    else:
        lines.extend(
            [
                "- Use real PNG alpha transparency only where the underlying base terrain should remain visible.",
                "- Leave transparent areas as alpha pixels; do not paint filler colors there.",
            ]
        )
    lines.append("- No text, watermark, UI frame, camera perspective scene, or extra objects.")
    return "\n".join(lines)


def _build_composite_source_prompt(obj: dict[str, Any], body: str, source_canvas: list[int], art_request: dict[str, Any]) -> str:
    tile_size = art_request.get("art_tile_size") or art_request.get("tile_size", [64, 64])
    footprint = obj.get("footprint") or [1, 1]
    parts = obj.get("parts") or []
    layout = obj.get("layout") or []
    part_lines = []
    part_by_key = {str(part.get("key")): part for part in parts if isinstance(part, dict)}
    for part in parts:
        if not isinstance(part, dict):
            continue
        part_lines.append(
            f"- {part.get('key')}: {part.get('display_name')}; {part.get('source_clause') or ''}; {dict(part.get('properties') or {}).get('appearance') or ''}"
        )
    layout_lines = []
    for cell in layout:
        if not isinstance(cell, dict):
            continue
        part_key = str(cell.get("part"))
        part = part_by_key.get(part_key, {})
        layout_lines.append(
            f"- grid ({int(cell.get('x', 0))},{int(cell.get('y', 0))}) = {part_key} ({part.get('display_name') or part_key})"
        )
    return "\n".join(
        [
            "TASK: Create one coherent full-source image for a grid-composed RPG tilemap entity.",
            body,
            "",
            "Asset contract:",
            f"- Target id: {obj['id']}",
            f"- Composite id: {obj.get('composite_id')}",
            f"- Composite type: {obj.get('composite_type')}",
            f"- Source canvas: {source_canvas[0]}x{source_canvas[1]} px",
            f"- Entity footprint: {footprint[0]}x{footprint[1]} tiles",
            f"- Art tile grid: {tile_size[0]}x{tile_size[1]} px per tile",
            "- The image will be cut into exact grid tiles after generation.",
            "",
            "Component definitions:",
            *part_lines,
            "",
            "Required grid layout:",
            *layout_lines,
            "",
            "Output requirements:",
            "- Pixel art, top-down 3/4 RPG view.",
            "- Make the whole entity visually coherent across tile boundaries.",
            "- Follow the grid layout exactly; each listed grid cell must contain its specified component.",
            "- Use one consistent palette, lighting, outline thickness, texture scale, and perspective across the whole source image.",
            "- Opaque PNG only; fill the entire canvas with the entity art; no alpha, no empty margin, no UI frame.",
            "- Do not add extra buildings, people, signs, labels, text, sky, camera perspective, or decorative elements outside this entity.",
        ]
    )


def _generated_prompt_for(obj: dict[str, Any]) -> dict[str, Any] | None:
    if obj.get("asset_role") != "composite_source":
        return None
    display_name = obj.get("display_name") or obj.get("id")
    source_clause = obj.get("source_clause") or ""
    return {
        "target_id": obj.get("id"),
        "body": f"{display_name}. {source_clause}",
        "emphasis": ["coherent_source_image", "grid_aligned", "tilemap_entity"],
        "negative": ["text", "watermark", "photorealistic", "separate icons"],
    }


def _filter_full_background_covered_objects(paths, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not _uses_full_background(paths):
        return objects
    covered_roles = {"base_terrain", "composite_source"}
    return [obj for obj in objects if obj.get("asset_role") not in covered_roles]


def _uses_full_background(paths) -> bool:
    if not paths.background_plan.exists():
        return False
    try:
        plan = _read_json(paths.background_plan)
    except Exception:
        return False
    background = plan.get("background_image")
    return isinstance(background, dict) and background.get("method") == "use_full_concept"


def _slice_composite_source(source_png: Path, obj: dict[str, Any], images_dir: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("PIL not available for composite slicing") from exc
    with Image.open(source_png).convert("RGBA") as source:
        for item in obj.get("slice_outputs", []) or []:
            if not isinstance(item, dict):
                continue
            rect = item.get("source_rect") or [0, 0, 64, 64]
            x, y, w, h = [int(value) for value in rect]
            tile = source.crop((x, y, x + w, y + h))
            target_id = str(item["id"])
            target_png = images_dir / f"{target_id}.png"
            target_json = images_dir / f"{target_id}.json"
            tile.save(target_png)
            target_json.write_text(
                json.dumps(
                    {
                        "target_id": target_id,
                        "asset_id": target_id,
                        "sprite_path": f"{target_id}.png",
                        "category": "composite_slice",
                        "source_generation_id": obj.get("id"),
                        "part": item.get("part"),
                        "grid_position": [item.get("x"), item.get("y")],
                        "source_rect": rect,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            tile.close()


def _slice_sprite_sheet_group(group_png: Path, group: dict[str, Any], images_dir: Path) -> list[dict[str, Any]]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("PIL not available for sprite sheet slicing") from exc
    records: list[dict[str, Any]] = []
    rects = _sprite_sheet_slot_rects(group)
    with Image.open(group_png).convert("RGBA") as source:
        for target_id, rect in rects.items():
            x, y, w, h = rect
            sprite = source.crop((x, y, x + w, y + h))
            target_png = images_dir / f"{target_id}.png"
            sprite.save(target_png)
            alpha_bbox = sprite.getchannel("A").getbbox()
            sprite.close()
            records.append(
                {
                    "target_id": target_id,
                    "source_rect": [x, y, w, h],
                    "alpha_bbox": list(alpha_bbox) if alpha_bbox else None,
                }
            )
    return records


def _apply_group_size_warnings(
    group: dict[str, Any],
    images_dir: Path,
    validations: dict[str, ImageValidation | None],
) -> None:
    if not group.get("same_visual_size", True):
        return
    try:
        from PIL import Image
    except ImportError:
        return
    bboxes: dict[str, tuple[int, int, int, int]] = {}
    for item in group.get("targets", []) or []:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id"))
        png_path = images_dir / f"{target_id}.png"
        if not png_path.exists():
            continue
        with Image.open(png_path).convert("RGBA") as img:
            bbox = img.getchannel("A").getbbox()
        if bbox:
            bboxes[target_id] = bbox
    if len(bboxes) < 2:
        return
    widths = {target_id: bbox[2] - bbox[0] for target_id, bbox in bboxes.items()}
    heights = {target_id: bbox[3] - bbox[1] for target_id, bbox in bboxes.items()}
    width_delta = max(widths.values()) - min(widths.values())
    height_delta = max(heights.values()) - min(heights.values())
    width_tolerance = int(group.get("bbox_width_tolerance") or 12)
    height_tolerance = int(group.get("bbox_height_tolerance") or 12)
    warning_parts = []
    if width_delta > width_tolerance:
        warning_parts.append(f"group visual width delta {width_delta}px exceeds tolerance {width_tolerance}px")
    if height_delta > height_tolerance:
        warning_parts.append(f"group visual height delta {height_delta}px exceeds tolerance {height_tolerance}px")
    if not warning_parts:
        return
    detail = "; ".join(warning_parts) + f"; widths={widths}; heights={heights}"
    for target_id, validation in validations.items():
        if validation:
            validation.warnings.append(detail)


def _write_group_member_metadata(
    path: Path,
    target_id: str,
    obj: dict[str, Any],
    prompt: dict[str, Any],
    response,
    request: ImageGenerationRequest,
    group_request: ImageGenerationRequest,
    group: dict[str, Any],
    record: dict[str, Any],
    validation: ImageValidation | None,
    variants: int,
) -> None:
    data = {
        "target_id": target_id,
        "asset_id": target_id,
        "sprite_path": f"{target_id}.png",
        "category": obj.get("category"),
        "footprint": obj.get("footprint"),
        "source_canvas": obj.get("source_canvas"),
        "prompt": prompt,
        "full_prompt": request.prompt,
        "variants_requested": variants,
        "generator": response.model,
        "actual_seed": response.actual_seed,
        "response_metadata": response.metadata,
        "generation_group": {
            "group_id": group.get("group_id"),
            "mode": group.get("mode"),
            "group_sprite_path": f"_group_{group.get('group_id')}.png",
            "source_rect": record.get("source_rect"),
            "alpha_bbox": record.get("alpha_bbox"),
            "group_full_prompt": group_request.prompt,
        },
    }
    if validation:
        data["validation"] = {
            "passed": validation.passed,
            "has_transparency": validation.has_transparency,
            "has_clean_edges": validation.has_clean_edges,
            "size_correct": validation.size_correct,
            "tile_aligned": validation.tile_aligned,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _create_image_generator(output_dir: Path, use_gemini: bool):
    if use_gemini:
        from generator.assets.gemini_generator import GeminiImageGenerator

        return GeminiImageGenerator(output_dir)
    return MockImageGenerator(output_dir)


def _move_if_needed(source: str | None, target: Path) -> None:
    if not source:
        raise ValueError(f"missing generated image path for {target.name}")
    src = Path(source)
    if src.resolve() == target.resolve():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(src), target)
    except PermissionError:
        shutil.copyfile(src, target)
        try:
            os.unlink(src)
        except OSError:
            pass
    sidecar = src.with_suffix(".json")
    if sidecar.exists():
        try:
            sidecar.unlink()
        except OSError:
            pass


def _write_metadata(path: Path, target_id: str, obj: dict[str, Any], prompt: dict[str, Any], response, request: ImageGenerationRequest, variants: int) -> None:
    data = {
        "target_id": target_id,
        "asset_id": target_id,
        "sprite_path": f"{target_id}.png",
        "category": obj.get("category"),
        "footprint": obj.get("footprint"),
        "source_canvas": obj.get("source_canvas"),
        "prompt": prompt,
        "full_prompt": request.prompt,
        "variants_requested": variants,
        "generator": response.model,
        "actual_seed": response.actual_seed,
        "response_metadata": response.metadata,
    }
    if response.validation:
        data["validation"] = {
            "passed": response.validation.passed,
            "has_transparency": response.validation.has_transparency,
            "has_clean_edges": response.validation.has_clean_edges,
            "size_correct": response.validation.size_correct,
            "tile_aligned": response.validation.tile_aligned,
            "errors": response.validation.errors,
            "warnings": response.validation.warnings,
        }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
