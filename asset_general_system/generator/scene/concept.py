from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import Any

from generator.assets.image_generation import ImageGenerationRequest, ImageStyle, MockImageGenerator, TransparencyMode

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress


def generate_scene_concept(scene_dir: str | Path, use_gemini: bool = False, force: bool = False) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    paths.concept_dir.mkdir(parents=True, exist_ok=True)
    if paths.concept_image.exists() and paths.concept_prompt.exists() and not force:
        return _concept_result(paths.concept_image, paths.concept_prompt, generated=False)

    mark_in_progress(paths.root, "3_concept")
    prompt = build_background_concept_prompt(paths.root)
    paths.concept_prompt.write_text(prompt + "\n", encoding="utf-8")
    if use_gemini:
        generator = _create_concept_generator(paths.concept_dir, use_gemini=True)
        response = generator.generate(
            ImageGenerationRequest(
                prompt=prompt,
                style=ImageStyle.PIXEL_ART,
                size=(1024, 1024),
                transparency=TransparencyMode.OPAQUE,
                tile_aligned=False,
                metadata={"target_id": "background_concept", "category": "concept_preview"},
            )
        )
        if not response.success:
            raise RuntimeError(response.error or "Gemini concept generation failed")
        _move_if_needed(response.image_path, paths.concept_image)
    else:
        _write_mock_concept_image(paths.root, paths.concept_image)
    mark_completed(paths.root, "3_concept")
    return _concept_result(paths.concept_image, paths.concept_prompt, generated=True)


def build_background_concept_prompt(scene_dir: str | Path) -> str:
    paths = scene_paths(scene_dir)
    map_spec = _read_json(paths.map_spec)
    style = _read_json(paths.style_profile) if paths.style_profile.exists() else {}
    base = map_spec.get("base_terrain") or {}
    composites = [item for item in map_spec.get("composites", []) or [] if isinstance(item, dict)]
    base_text = _display(base, "display_name", "object_key", fallback="base terrain")
    crop_tile_size = _crop_tile_size_text(map_spec)
    composite_lines = [
        f"- {_display(item, 'display_name', 'id')}: {item.get('source_clause') or item.get('placement') or item.get('type')}"
        for item in composites
    ]
    reusable_part_lines = _reusable_part_lines(composites)
    object_lines = [
        f"- {_display(item, 'label', 'type')}"
        for item in map_spec.get("objects", []) or []
        if isinstance(item, dict)
    ]
    lines = [
        "Create one top-down 3/4 RPG pixel art background concept image.",
        "This is a layout and mood preview for the background layer only, not final tile assets.",
        "",
        "Base environment:",
        f"- Fill the whole scene with {base_text}.",
        "",
        "Ground/background entities to include:",
        *(composite_lines or ["- No additional ground composites."]),
        "",
        "Do not include foreground entities:",
        *(object_lines or ["- No characters, props, buildings, signs, vehicles, animals, or UI."]),
        "",
        "Composition requirements:",
        "- Keep the scene readable as a tilemap-like top-down composition.",
        "- Keep ground features coherent and spatially clear.",
        "- Do not draw separate asset icons, labels, text, watermark, UI frame, or visible sprite-sheet cells.",
        "",
        "Tile extraction requirements:",
        f"- The image must be suitable for extracting reusable {crop_tile_size} tile assets.",
        f"- Use an invisible {crop_tile_size} crop grid; do not draw the grid lines.",
        "- Align road edges, track edges, curves, terrain borders, and repeated surface modules to this crop grid.",
        "- Do not place important boundaries halfway through a crop cell.",
        "- Keep texture scale, outline thickness, palette, and lighting consistent across repeated modules.",
        "- Leave clean, unobstructed sample areas for every reusable material or composite part.",
        *(reusable_part_lines or ["- Base terrain should have several clean repeated patches with no foreground objects."]),
        "- Avoid diagonal, noisy, or painterly borders unless the corresponding reusable part is explicitly a diagonal or curved tile.",
        "",
        "Style requirements:",
        f"- Art style: {style.get('art_style') or 'pixel_art_32'}.",
        f"- View: {style.get('view') or 'top_down_3_4'}.",
        f"- Palette/mood: {style.get('palette_mood') or map_spec.get('theme') or 'coherent rural palette'}.",
        f"- Lighting: {style.get('lighting') or 'soft daylight'}.",
    ]
    return "\n".join(lines)


def _crop_tile_size_text(map_spec: dict[str, Any]) -> str:
    art_tile_size = map_spec.get("art_tile_size")
    if isinstance(art_tile_size, int) and art_tile_size > 0:
        return f"{art_tile_size}x{art_tile_size}px"
    map_data = map_spec.get("map") or {}
    tile_w = int(map_data.get("tile_width") or 64)
    tile_h = int(map_data.get("tile_height") or tile_w)
    return f"{tile_w}x{tile_h}px"


def _reusable_part_lines(composites: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for comp in composites:
        comp_id = comp.get("id") or comp.get("type") or "composite"
        for part in comp.get("parts", []) or []:
            if not isinstance(part, dict):
                continue
            part_name = _display(part, "display_name", "key", fallback="part")
            part_key = part.get("key") or part_name
            appearance = dict(part.get("properties") or {}).get("appearance")
            detail = f"; {appearance}" if appearance else ""
            lines.append(f"- Provide a clean crop candidate for {comp_id}:{part_key} ({part_name}){detail}.")
    return lines


def _create_concept_generator(output_dir: Path, use_gemini: bool):
    if use_gemini:
        from generator.assets.gemini_generator import GeminiImageGenerator

        return GeminiImageGenerator(output_dir)
    return MockImageGenerator(output_dir)


def _write_mock_concept_image(scene_dir: Path, target: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("PIL not available for mock concept generation") from exc

    paths = scene_paths(scene_dir)
    map_spec = _read_json(paths.map_spec)
    map_data = _read_json(paths.map_data) if paths.map_data.exists() else {}
    size = 1024
    image = Image.new("RGBA", (size, size), (196, 170, 92, 255))
    draw = ImageDraw.Draw(image)
    width = int(map_spec.get("map", {}).get("width", 64))
    height = int(map_spec.get("map", {}).get("height", 64))
    sx = size / max(1, width)
    sy = size / max(1, height)
    for x in range(0, width + 1, max(1, width // 8)):
        draw.line((round(x * sx), 0, round(x * sx), size), fill=(80, 70, 45, 80))
    for y in range(0, height + 1, max(1, height // 8)):
        draw.line((0, round(y * sy), size, round(y * sy)), fill=(80, 70, 45, 80))
    for region in map_data.get("regions", []) or []:
        if not isinstance(region, dict):
            continue
        x, y, w, h = [int(v) for v in region.get("bounds", [0, 0, 1, 1])]
        rect = (x * sx, y * sy, (x + w) * sx, (y + h) * sy)
        draw.rectangle(rect, outline=(120, 52, 42, 255), width=4)
        draw.text((rect[0] + 6, rect[1] + 6), str(region.get("id") or region.get("type")), fill=(40, 34, 24, 255))
    try:
        font = ImageFont.load_default()
        draw.text((20, 20), "Mock background concept", fill=(40, 34, 24, 255), font=font)
    except Exception:
        pass
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, "PNG")
    image.close()


def _move_if_needed(source: str | None, target: Path) -> None:
    if not source:
        raise ValueError("missing generated concept image path")
    src = Path(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == target.resolve():
        return
    try:
        shutil.move(str(src), target)
    except PermissionError:
        shutil.copyfile(src, target)
        try:
            os.unlink(src)
        except OSError:
            pass


def _concept_result(image_path: Path, prompt_path: Path, generated: bool) -> dict[str, Any]:
    return {
        "image": str(image_path),
        "prompt": str(prompt_path),
        "generated": generated,
    }


def _display(data: dict[str, Any], *keys: str, fallback: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return fallback


def _read_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
