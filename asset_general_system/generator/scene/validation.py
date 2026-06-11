from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generator.models.base import read_json

from .constants import (
    ATTACHED_CATEGORIES,
    FACING_VALUES,
    FOOTPRINT_RE,
    OBJECT_KEY_RE,
    SCENE_OBJECT_CATEGORIES,
    TILE_GROUP_KINDS,
    TILE_GROUP_MEMBER_ROLES,
    TILE_GROUP_MODES,
)
from .contracts import scene_paths


@dataclass(frozen=True)
class SceneValidationIssue:
    path: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "message": self.message, "severity": self.severity}


def validate_scene_file(scene_dir: str | Path, stage: str | None = None) -> list[SceneValidationIssue]:
    paths = scene_paths(scene_dir)
    issues: list[SceneValidationIssue] = []

    if stage in (None, "spec", "1_spec"):
        issues.extend(validate_map_spec(paths.map_spec))
    if stage in (None, "style", "3_style") and paths.style_profile.exists():
        issues.extend(validate_schema_file(paths.style_profile, "scene_style_profile.schema.json"))
    if stage in (None, "entities", "4_entities") and paths.entities.exists():
        issues.extend(validate_schema_file(paths.entities, "scene_entities.schema.json"))
        issues.extend(validate_entities_targets(paths.root))
    if stage in (None, "prompts", "5_prompts") and paths.prompts.exists():
        issues.extend(validate_schema_file(paths.prompts, "scene_prompts.schema.json"))
        issues.extend(validate_prompt_targets(paths.root))
        issues.extend(validate_generation_group_targets(paths.root))
        issues.extend(validate_text_sign_prompts(paths.root))
    if stage in (None, "manifest", "pack", "7_pack") and paths.manifest.exists():
        issues.extend(validate_schema_file(paths.manifest, "art_manifest.schema.json"))
    if stage in (None, "tilemap-blueprint", "tilemap_blueprint") and paths.tilemap_blueprint.exists():
        issues.extend(validate_schema_file(paths.tilemap_blueprint, "tilemap_blueprint.schema.json"))
    if stage in (None, "tile-family-plan", "tile_family_plan") and paths.tile_family_plan.exists():
        issues.extend(validate_schema_file(paths.tile_family_plan, "tile_family_plan.schema.json"))
    pixellab_manifest = paths.pixellab_tilesets_dir / "raw" / "manifest.json"
    if stage in (None, "pixellab-tilesets", "pixellab_tilesets", "tileset") and pixellab_manifest.exists():
        issues.extend(validate_schema_file(pixellab_manifest, "pixellab_tileset_manifest.schema.json"))
    if stage in (None, "tile-candidates", "tile_candidates") and paths.tile_candidates.exists():
        issues.extend(validate_schema_file(paths.tile_candidates, "tile_candidates.schema.json"))
    if stage in (None, "tilemap-mapping", "tilemap_mapping") and paths.tilemap_mapping.exists():
        issues.extend(validate_schema_file(paths.tilemap_mapping, "tilemap_mapping.schema.json"))
    return issues


def validate_map_spec(path: Path) -> list[SceneValidationIssue]:
    issues: list[SceneValidationIssue] = []
    if not path.exists():
        return [SceneValidationIssue("map_spec.json", "file does not exist")]
    data = _read_or_issue(path, issues)
    if not isinstance(data, dict):
        return issues
    issues.extend(validate_schema_data(data, "scene_map_spec.schema.json", "map_spec.json"))
    issues.extend(validate_map_spec_semantics(data))
    return issues


def validate_map_spec_semantics(data: dict[str, Any]) -> list[SceneValidationIssue]:
    issues: list[SceneValidationIssue] = []
    regions = {str(region.get("id")) for region in data.get("regions", []) if isinstance(region, dict)}
    object_ids = predicted_object_ids(data)
    base_terrain = data.get("base_terrain")
    if base_terrain is not None:
        if not isinstance(base_terrain, dict):
            issues.append(SceneValidationIssue("base_terrain", "must be an object"))
        else:
            object_key = base_terrain.get("object_key")
            if not isinstance(object_key, str) or not OBJECT_KEY_RE.match(object_key):
                issues.append(SceneValidationIssue("base_terrain.object_key", "must be ASCII snake_case and start with a letter"))
            source_canvas = base_terrain.get("source_canvas")
            if source_canvas is not None and not _is_pair_of_positive_ints(source_canvas):
                issues.append(SceneValidationIssue("base_terrain.source_canvas", "must be [W, H] positive integer array"))

    for index, obj in enumerate(data.get("objects", [])):
        path = f"objects[{index}]"
        if not isinstance(obj, dict):
            issues.append(SceneValidationIssue(path, "object item must be an object"))
            continue
        category = obj.get("type")
        props = obj.get("properties") if isinstance(obj.get("properties"), dict) else {}
        if category not in SCENE_OBJECT_CATEGORIES:
            issues.append(SceneValidationIssue(f"{path}.type", f"unknown category: {category}"))
        object_key = props.get("object_key")
        if not isinstance(object_key, str) or not OBJECT_KEY_RE.match(object_key):
            issues.append(SceneValidationIssue(f"{path}.properties.object_key", "must be ASCII snake_case and start with a letter"))
        footprint = props.get("footprint")
        if footprint is not None and (not isinstance(footprint, str) or not FOOTPRINT_RE.match(footprint)):
            issues.append(SceneValidationIssue(f"{path}.properties.footprint", 'must use "WxH" with positive integers'))
        source_canvas = props.get("source_canvas")
        if source_canvas is not None and not _is_pair_of_positive_ints(source_canvas):
            issues.append(SceneValidationIssue(f"{path}.properties.source_canvas", "must be [W, H] positive integer array"))
        facing = props.get("facing")
        if facing is not None and facing not in FACING_VALUES:
            issues.append(SceneValidationIssue(f"{path}.properties.facing", f"must be one of {sorted(FACING_VALUES)}"))
        if category in ATTACHED_CATEGORIES:
            attached_to = props.get("attached_to")
            if not isinstance(attached_to, str) or not attached_to:
                issues.append(SceneValidationIssue(f"{path}.properties.attached_to", "is required"))
            elif attached_to not in regions and attached_to not in object_ids:
                issues.append(
                    SceneValidationIssue(
                        f"{path}.properties.attached_to",
                        f"does not reference a region id or predictable object id: {attached_to}",
                    )
                )
        if not obj.get("label") and not props.get("display_name"):
            issues.append(SceneValidationIssue(f"{path}.label", "label or properties.display_name is required"))
        if not props.get("source_clause"):
            issues.append(SceneValidationIssue(f"{path}.properties.source_clause", "source_clause is recommended", severity="warning"))
    issues.extend(validate_composites(data, regions))
    issues.extend(validate_tile_groups(data))
    return issues


def validate_composites(data: dict[str, Any], regions: set[str]) -> list[SceneValidationIssue]:
    issues: list[SceneValidationIssue] = []
    for index, comp in enumerate(data.get("composites", []) or []):
        path = f"composites[{index}]"
        if not isinstance(comp, dict):
            issues.append(SceneValidationIssue(path, "composite item must be an object"))
            continue
        placement = comp.get("placement")
        if isinstance(placement, str) and placement not in regions and placement not in {
            "top",
            "center",
            "bottom",
            "left",
            "right",
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
        }:
            issues.append(SceneValidationIssue(f"{path}.placement", f"does not reference a region id or known anchor: {placement}", severity="warning"))
        footprint = comp.get("footprint")
        if not _is_pair_of_positive_ints(footprint):
            issues.append(SceneValidationIssue(f"{path}.footprint", "must be [W, H] positive integer array"))
            width, height = 0, 0
        else:
            width, height = int(footprint[0]), int(footprint[1])
        part_keys = set()
        for part_index, part in enumerate(comp.get("parts", []) or []):
            if not isinstance(part, dict):
                issues.append(SceneValidationIssue(f"{path}.parts[{part_index}]", "part item must be an object"))
                continue
            key = part.get("key")
            if not isinstance(key, str) or not OBJECT_KEY_RE.match(key):
                issues.append(SceneValidationIssue(f"{path}.parts[{part_index}].key", "must be ASCII snake_case and start with a letter"))
            else:
                part_keys.add(key)
            if not _is_pair_of_positive_ints(part.get("source_canvas")):
                issues.append(SceneValidationIssue(f"{path}.parts[{part_index}].source_canvas", "must be [W, H] positive integer array"))
        for cell_index, cell in enumerate(comp.get("layout", []) or []):
            if not isinstance(cell, dict):
                issues.append(SceneValidationIssue(f"{path}.layout[{cell_index}]", "layout cell must be an object"))
                continue
            part = cell.get("part")
            if part not in part_keys:
                issues.append(SceneValidationIssue(f"{path}.layout[{cell_index}].part", f"unknown part: {part}"))
            x, y = cell.get("x"), cell.get("y")
            if not isinstance(x, int) or not isinstance(y, int) or x < 0 or y < 0:
                issues.append(SceneValidationIssue(f"{path}.layout[{cell_index}]", "x and y must be non-negative integers"))
            elif width and height and (x >= width or y >= height):
                issues.append(SceneValidationIssue(f"{path}.layout[{cell_index}]", "cell is outside composite footprint"))
    return issues


def validate_tile_groups(data: dict[str, Any]) -> list[SceneValidationIssue]:
    issues: list[SceneValidationIssue] = []
    base_refs = set()
    base_terrain = data.get("base_terrain")
    if isinstance(base_terrain, dict) and isinstance(base_terrain.get("object_key"), str):
        base_refs.add(str(base_terrain["object_key"]))
        base_refs.add(f"{base_terrain['object_key']}_01")

    composite_refs = set()
    for comp in data.get("composites", []) or []:
        if not isinstance(comp, dict):
            continue
        comp_id = str(comp.get("id") or "")
        if comp_id:
            composite_refs.add(comp_id)
        for part in comp.get("parts", []) or []:
            if not isinstance(part, dict):
                continue
            key = str(part.get("key") or "")
            if key:
                composite_refs.add(key)
                composite_refs.add(f"{comp_id}:{key}")
                composite_refs.add(f"{comp_id}_{key}")

    valid_refs = base_refs | composite_refs
    seen_groups: set[str] = set()
    seen_tiles: set[str] = set()
    for group_index, group in enumerate(data.get("tile_groups", []) or []):
        path = f"tile_groups[{group_index}]"
        if not isinstance(group, dict):
            issues.append(SceneValidationIssue(path, "tile group must be an object"))
            continue
        group_id = group.get("group_id")
        if not isinstance(group_id, str) or not OBJECT_KEY_RE.match(group_id):
            issues.append(SceneValidationIssue(f"{path}.group_id", "must be ASCII snake_case and start with a letter"))
        elif group_id in seen_groups:
            issues.append(SceneValidationIssue(f"{path}.group_id", f"duplicate group_id: {group_id}"))
        else:
            seen_groups.add(group_id)
        if group.get("kind") not in TILE_GROUP_KINDS:
            issues.append(SceneValidationIssue(f"{path}.kind", f"must be one of {sorted(TILE_GROUP_KINDS)}"))
        if group.get("generation_mode") not in TILE_GROUP_MODES:
            issues.append(SceneValidationIssue(f"{path}.generation_mode", "must be sprite_sheet"))
        if not _is_pair_of_positive_ints(group.get("tile_size")):
            issues.append(SceneValidationIssue(f"{path}.tile_size", "must be [W, H] positive integer array"))
        for member_index, member in enumerate(group.get("members", []) or []):
            member_path = f"{path}.members[{member_index}]"
            if not isinstance(member, dict):
                issues.append(SceneValidationIssue(member_path, "member must be an object"))
                continue
            tile_id = member.get("tile_id")
            if not isinstance(tile_id, str) or not OBJECT_KEY_RE.match(tile_id):
                issues.append(SceneValidationIssue(f"{member_path}.tile_id", "must be ASCII snake_case and start with a letter"))
            elif tile_id in seen_tiles:
                issues.append(SceneValidationIssue(f"{member_path}.tile_id", f"duplicate tile_id across tile_groups: {tile_id}"))
            else:
                seen_tiles.add(tile_id)
            role = member.get("role")
            if role not in TILE_GROUP_MEMBER_ROLES:
                issues.append(SceneValidationIssue(f"{member_path}.role", f"unknown tile group role: {role}"))
            source_ref = member.get("source_ref")
            if source_ref is not None and str(source_ref) not in valid_refs:
                issues.append(SceneValidationIssue(f"{member_path}.source_ref", f"does not reference base terrain or composite part: {source_ref}"))
    return issues


def predicted_object_ids(map_spec: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    base_terrain = map_spec.get("base_terrain")
    if isinstance(base_terrain, dict):
        object_key = base_terrain.get("object_key")
        if isinstance(object_key, str) and OBJECT_KEY_RE.match(object_key):
            ids.add(f"{object_key}_01")
    for comp in map_spec.get("composites", []) or []:
        if not isinstance(comp, dict):
            continue
        for part in comp.get("parts", []) or []:
            if not isinstance(part, dict):
                continue
            key = part.get("key")
            if isinstance(key, str) and OBJECT_KEY_RE.match(key):
                ids.add(f"{key}_01")
    for obj in map_spec.get("objects", []):
        if not isinstance(obj, dict):
            continue
        props = obj.get("properties") if isinstance(obj.get("properties"), dict) else {}
        object_key = props.get("object_key")
        if not isinstance(object_key, str) or not OBJECT_KEY_RE.match(object_key):
            continue
        count = int(obj.get("count") or 0)
        for index in range(1, count + 1):
            ids.add(f"{object_key}_{index:02d}")
    return ids


def validate_entities_targets(scene_dir: Path) -> list[SceneValidationIssue]:
    paths = scene_paths(scene_dir)
    if not paths.entities.exists() or not paths.art_request.exists():
        return []
    entities = read_json(paths.entities)
    art_request = read_json(paths.art_request)
    target_ids = {
        obj.get("id")
        for obj in art_request.get("objects", [])
        if isinstance(obj, dict)
    }
    issues = []
    for index, entity in enumerate(entities.get("entities", [])):
        target_id = entity.get("target_id")
        if target_id not in target_ids:
            issues.append(SceneValidationIssue(f"entities[{index}].target_id", f"unknown target_id: {target_id}"))
    return issues


def validate_prompt_targets(scene_dir: Path) -> list[SceneValidationIssue]:
    paths = scene_paths(scene_dir)
    if not paths.prompts.exists() or not paths.entities.exists():
        return []
    prompts = read_json(paths.prompts)
    entities = read_json(paths.entities)
    target_ids = {entity.get("target_id") for entity in entities.get("entities", []) if isinstance(entity, dict)}
    issues = []
    for index, prompt in enumerate(prompts.get("prompts", [])):
        target_id = prompt.get("target_id")
        if target_id not in target_ids:
            issues.append(SceneValidationIssue(f"prompts[{index}].target_id", f"unknown target_id: {target_id}"))
    return issues


def validate_generation_group_targets(scene_dir: Path) -> list[SceneValidationIssue]:
    paths = scene_paths(scene_dir)
    if not paths.prompts.exists() or not paths.entities.exists():
        return []
    prompts = read_json(paths.prompts)
    entities = read_json(paths.entities)
    target_ids = {entity.get("target_id") for entity in entities.get("entities", []) if isinstance(entity, dict)}
    issues = []
    for group_index, group in enumerate(prompts.get("generation_groups", []) or []):
        if not isinstance(group, dict):
            continue
        seen = set()
        for target_index, target in enumerate(group.get("targets", []) or []):
            target_id = target.get("target_id") if isinstance(target, dict) else None
            path = f"generation_groups[{group_index}].targets[{target_index}].target_id"
            if target_id not in target_ids:
                issues.append(SceneValidationIssue(path, f"unknown target_id: {target_id}"))
            if target_id in seen:
                issues.append(SceneValidationIssue(path, f"duplicate target_id in group: {target_id}"))
            seen.add(target_id)
    return issues


def validate_text_sign_prompts(scene_dir: Path) -> list[SceneValidationIssue]:
    paths = scene_paths(scene_dir)
    if not paths.prompts.exists() or not paths.art_request.exists():
        return []
    prompts = read_json(paths.prompts)
    art_request = read_json(paths.art_request)
    categories = {
        obj.get("id"): obj.get("category")
        for obj in art_request.get("objects", [])
        if isinstance(obj, dict)
    }
    banned = ("可读文字", "汉字", "中文字", "letters", "readable text", "Chinese characters")
    issues: list[SceneValidationIssue] = []
    for index, prompt in enumerate(prompts.get("prompts", [])):
        if categories.get(prompt.get("target_id")) != "text_sign":
            continue
        body = str(prompt.get("body") or "")
        negative = " ".join(str(item) for item in prompt.get("negative", []))
        if any(token in body for token in banned):
            issues.append(SceneValidationIssue(f"prompts[{index}].body", "text_sign body must not request readable text"))
        if not any(token in negative for token in ("readable text", "Chinese characters", "letters", "text")):
            issues.append(SceneValidationIssue(f"prompts[{index}].negative", "text_sign negative prompt should forbid readable text"))
    return issues


def validate_schema_file(path: Path, schema_name: str) -> list[SceneValidationIssue]:
    issues: list[SceneValidationIssue] = []
    if not path.exists():
        return [SceneValidationIssue(str(path.name), "file does not exist")]
    data = _read_or_issue(path, issues)
    if data is None:
        return issues
    return validate_schema_data(data, schema_name, path.name)


def validate_schema_data(data: Any, schema_name: str, path_prefix: str) -> list[SceneValidationIssue]:
    schema_path = Path(__file__).resolve().parents[2] / "specs" / schema_name
    if not schema_path.exists():
        return [SceneValidationIssue(path_prefix, f"schema does not exist: {schema_name}")]
    try:
        import jsonschema
    except Exception:
        return []
    try:
        schema = read_json(schema_path)
        validator = jsonschema.Draft202012Validator(schema)
        return [
            SceneValidationIssue(
                path=f"{path_prefix}.{'.'.join(str(part) for part in error.absolute_path)}".rstrip("."),
                message=error.message,
            )
            for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path))
        ]
    except Exception as exc:
        return [SceneValidationIssue(path_prefix, f"schema validation failed: {exc}")]


def _read_or_issue(path: Path, issues: list[SceneValidationIssue]) -> Any:
    try:
        return read_json(path)
    except Exception as exc:
        issues.append(SceneValidationIssue(path.name, f"invalid JSON: {exc}"))
        return None


def _is_pair_of_positive_ints(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int) and item > 0 for item in value)
    )
