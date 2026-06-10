from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from generator.assets.image_generation import (
    ImageGenerationRequest,
    ImageStyle,
    MockImageGenerator,
    TransparencyMode,
)

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress, record_error


def generate_scene_images(
    scene_dir: str | Path,
    use_gemini: bool = False,
    use_pixai: bool = False,
    force: bool = False,
    variants: int = 1,
    target: str | None = None,
) -> list[str]:
    paths = scene_paths(scene_dir)
    art_request = _read_json(paths.art_request)
    prompts = _read_json(paths.prompts)
    prompt_by_id = {item["target_id"]: item for item in prompts.get("prompts", [])}
    objects = list(art_request.get("objects", [])) + list(art_request.get("generation_targets", []))
    objects = [item for item in objects if not target or item.get("id") == target]
    if target and not objects:
        raise ValueError(f"unknown target_id: {target}")
    paths.images_dir.mkdir(parents=True, exist_ok=True)
    mark_in_progress(paths.root, "6_images", total=len(objects), current_item=target)
    image_generator = None
    generated: list[str] = []

    for obj in objects:
        target_id = str(obj["id"])
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
            image_generator = _create_image_generator(paths.images_dir / "_temp", use_gemini, use_pixai)
        request = _image_request(obj, prompt, art_request)
        response = image_generator.generate(request)
        if not response.success:
            record_error(paths.root, "6_images", target_id, response.error or "image generation failed")
            continue
        _move_if_needed(response.image_path, png_path)
        _write_metadata(json_path, target_id, obj, prompt, response, request, variants)
        if obj.get("asset_role") == "composite_source":
            _slice_composite_source(png_path, obj, paths.images_dir)
        generated.append(target_id)

    mark_completed(paths.root, "6_images")
    return generated


def _image_request(obj: dict[str, Any], prompt: dict[str, Any], art_request: dict[str, Any]) -> ImageGenerationRequest:
    category = str(obj.get("category") or "small_prop")
    description = _build_scene_prompt(obj, prompt, art_request)
    negative = list(prompt.get("negative") or [])
    if category == "text_sign":
        negative.extend(["readable text", "Chinese characters", "letters", "handwriting"])
    transparency = _transparency_for(obj, prompt)
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


def _build_scene_prompt(obj: dict[str, Any], prompt: dict[str, Any], art_request: dict[str, Any]) -> str:
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
        "",
        "Output requirements:",
        "- Pixel art, top-down 3/4 RPG view.",
        "- Use true PNG alpha outside the object; do not draw terrain, floor, or scene content behind it.",
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


def _create_image_generator(output_dir: Path, use_gemini: bool, use_pixai: bool = False):
    if use_gemini and use_pixai:
        raise ValueError("--gemini and --pixai are mutually exclusive")
    if use_pixai:
        from generator.assets.pixai_generator import PixAIImageGenerator

        return PixAIImageGenerator(output_dir)
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
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
