from __future__ import annotations

from pathlib import Path
from random import Random
from typing import Any

from generator.config import DEFAULT_TILESET_ID, THEME_DEFAULT_TERRAIN, TILE_ID_BY_NAME
from generator.models import MapInfo, ObjectData, RegionData, RPGMapSpec, TilemapData, TilesetInfo
from generator.models.base import read_json, write_json, write_model_json
from generator.render import PreviewRenderer

from .art_request import build_scene_art_request
from .constants import CATEGORY_DEFAULTS, FOOTPRINT_RE, SCENE_OBJECT_CATEGORIES
from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress
from .validation import validate_scene_file


def parse_footprint(properties: dict[str, Any], category: str, facing: str | None = None) -> tuple[int, int]:
    explicit = properties.get("footprint")
    if isinstance(explicit, str):
        match = FOOTPRINT_RE.match(explicit)
        if not match:
            raise ValueError(f"invalid footprint: {explicit}")
        return int(match.group(1)), int(match.group(2))
    default = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["small_prop"])
    w, h = default["footprint"]  # type: ignore[index]
    if facing == "north_south" and w > h:
        return int(h), int(w)
    return int(w), int(h)


def parse_blocking(properties: dict[str, Any], category: str) -> bool:
    if isinstance(properties.get("blocking"), bool):
        return bool(properties["blocking"])
    return bool(CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["small_prop"])["blocking"])


def parse_source_canvas(properties: dict[str, Any], category: str, footprint: tuple[int, int], tile_size: tuple[int, int]) -> tuple[int, int]:
    explicit = properties.get("source_canvas")
    if isinstance(explicit, list) and len(explicit) == 2 and all(isinstance(item, int) and item > 0 for item in explicit):
        return int(explicit[0]), int(explicit[1])
    min_w, min_h = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["small_prop"])["source_canvas"]  # type: ignore[index]
    return max(int(min_w), footprint[0] * tile_size[0]), max(int(min_h), footprint[1] * tile_size[1])


def parse_anchor(category: str) -> str:
    return str(CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["small_prop"])["anchor"])


def build_scene_map(scene_dir: str | Path, force: bool = False) -> TilemapData:
    paths = scene_paths(scene_dir)
    if paths.map_data.exists() and paths.art_request.exists() and paths.preview.exists() and not force:
        return TilemapData.model_validate(read_json(paths.map_data))
    errors = [issue for issue in validate_scene_file(paths.root, "spec") if issue.severity == "error"]
    if errors:
        joined = "; ".join(f"{issue.path}: {issue.message}" for issue in errors)
        raise ValueError(f"scene spec validation failed: {joined}")

    spec_data = read_json(paths.map_spec)
    spec = RPGMapSpec.model_validate(spec_data)
    mark_in_progress(paths.root, "2_map")
    tilemap = SceneMapBuilder(spec, spec_data).build()
    renderer = PreviewRenderer()
    renderer.ensure_tileset_png(paths.root / "tilesets" / "default_rpg_32.png", spec.map.tile_width, spec.map.tile_height)
    renderer.render(tilemap, paths.preview)
    write_model_json(paths.map_data, tilemap)
    description = paths.scene_md.read_text(encoding="utf-8") if paths.scene_md.exists() else spec.title
    write_json(paths.art_request, build_scene_art_request(tilemap, spec_data, description))
    mark_completed(paths.root, "2_map")
    return tilemap


class SceneMapBuilder:
    def __init__(self, spec: RPGMapSpec, raw_spec: dict[str, Any]):
        self.spec = spec
        self.raw_spec = raw_spec
        self.rng = Random(spec.seed)
        self.reserved: list[tuple[int, int, int, int]] = []

    def build(self) -> TilemapData:
        width, height = self.spec.map.width, self.spec.map.height
        base_tile_name = self._base_tile_name()
        base_tile = TILE_ID_BY_NAME.get(base_tile_name, TILE_ID_BY_NAME.get("grass", 1))
        tilemap = TilemapData(
            map=MapInfo(
                width=width,
                height=height,
                tile_width=self.spec.map.tile_width,
                tile_height=self.spec.map.tile_height,
                orientation=self.spec.map.orientation,
            ),
            tileset=TilesetInfo(id=self.spec.tileset_id or DEFAULT_TILESET_ID),
            layers={
                "terrain": [base_tile] * (width * height),
                "path": [0] * (width * height),
                "building": [0] * (width * height),
                "decoration": [0] * (width * height),
                "collision": [0] * (width * height),
            },
            metadata={
                "theme": self.spec.theme,
                "seed": self.spec.seed,
                "spec_id": self.spec.id,
                "base_terrain": self.raw_spec.get("base_terrain"),
            },
        )
        self._place_regions(tilemap)
        self._draw_paths(tilemap)
        self._place_base_terrain_asset(tilemap)
        self._place_composites(tilemap)
        self._place_spawn(tilemap)
        self._place_objects(tilemap)
        self._generate_collision(tilemap)
        return tilemap

    def _base_tile_name(self) -> str:
        base_terrain = self.raw_spec.get("base_terrain")
        if isinstance(base_terrain, dict) and isinstance(base_terrain.get("tile"), str):
            return str(base_terrain["tile"])
        return THEME_DEFAULT_TERRAIN.get(self.spec.theme, "grass")

    def _place_base_terrain_asset(self, tilemap: TilemapData) -> None:
        base_terrain = self.raw_spec.get("base_terrain")
        if not isinstance(base_terrain, dict):
            return
        object_key = str(base_terrain["object_key"])
        source_canvas = base_terrain.get("source_canvas") or [tilemap.map.tile_width, tilemap.map.tile_height]
        props = dict(base_terrain.get("properties") or {})
        props.update(
            {
                "object_key": object_key,
                "display_name": base_terrain.get("display_name") or object_key,
                "category": "terrain_tile",
                "facing": "east_west",
                "footprint": "1x1",
                "source_canvas": list(source_canvas),
                "blocking": False,
                "anchor": "center",
                "placement": "full_map",
                "source_clause": base_terrain.get("source_clause"),
                "asset_role": "base_terrain",
                "asset_id": f"{object_key}_01",
                "is_asset_target": True,
                "is_map_instance": False,
            }
        )
        tilemap.objects.append(
            ObjectData(
                id=f"{object_key}_01",
                type="terrain_tile",
                x=0,
                y=0,
                width=1,
                height=1,
                properties=props,
            )
        )

    def _place_composites(self, tilemap: TilemapData) -> None:
        for comp in self.raw_spec.get("composites", []) or []:
            if not isinstance(comp, dict):
                continue
            footprint = comp.get("footprint") or [1, 1]
            comp_w, comp_h = int(footprint[0]), int(footprint[1])
            origin_x, origin_y = self._composite_origin(tilemap, str(comp.get("placement") or "center"), (comp_w, comp_h))
            part_by_key = {part["key"]: part for part in comp.get("parts", []) if isinstance(part, dict) and "key" in part}
            counters: dict[str, int] = {}
            for cell in comp.get("layout", []) or []:
                if not isinstance(cell, dict):
                    continue
                part_key = str(cell.get("part"))
                part = part_by_key.get(part_key)
                if not part:
                    continue
                counters[part_key] = counters.get(part_key, 0) + 1
                instance_id = f"{comp['id']}_{part_key}_{counters[part_key]:02d}"
                source_canvas = part.get("source_canvas") or [tilemap.map.tile_width, tilemap.map.tile_height]
                props = dict(part.get("properties") or {})
                props.update(
                    {
                        "object_key": part_key,
                        "display_name": part.get("display_name") or part_key,
                        "category": "composite_tile",
                        "composite_id": comp.get("id"),
                        "composite_type": comp.get("type"),
                        "facing": "east_west",
                        "footprint": "1x1",
                        "source_canvas": list(source_canvas),
                        "blocking": bool(part.get("blocking", False)),
                        "anchor": "center",
                        "placement": comp.get("placement"),
                        "source_clause": part.get("source_clause") or comp.get("source_clause"),
                        "asset_role": "composite_slice",
                        "asset_id": instance_id,
                        "source_generation_id": f"{comp['id']}_source",
                        "is_asset_target": False,
                        "is_map_instance": True,
                        "render_mode": "tile_layer",
                        "layout_offset": [int(cell.get("x", 0)), int(cell.get("y", 0))],
                    }
                )
                x = origin_x + int(cell.get("x", 0))
                y = origin_y + int(cell.get("y", 0))
                tilemap.objects.append(
                    ObjectData(
                        id=instance_id,
                        type="composite_tile",
                        x=x,
                        y=y,
                        width=1,
                        height=1,
                        properties=props,
                    )
                )
                self.reserved.append((x, y, 1, 1))

    def _composite_origin(self, tilemap: TilemapData, placement: str, footprint: tuple[int, int]) -> tuple[int, int]:
        region = self._region_by_id_or_type(tilemap, placement)
        if region:
            x = region.bounds[0] + max(0, (region.bounds[2] - footprint[0]) // 2)
            y = region.bounds[1] + max(0, (region.bounds[3] - footprint[1]) // 2)
            return self._clamp(tilemap, x, y, footprint)
        x, y, _, _ = self._bounds_for(placement, "medium")
        return self._clamp(tilemap, x, y, footprint)

    def _place_regions(self, tilemap: TilemapData) -> None:
        for region in self.spec.regions:
            x, y, w, h = self._bounds_for(region.position, region.size)
            access = [x + w // 2, min(tilemap.map.height - 2, y + h)]
            tilemap.regions.append(
                RegionData(
                    id=region.id,
                    type=region.type,
                    bounds=[x, y, w, h],
                    center=[x + w // 2, y + h // 2],
                    access=access,
                    priority=region.priority,
                )
            )

    def _draw_paths(self, tilemap: TilemapData) -> None:
        dirt = TILE_ID_BY_NAME.get("dirt_road", 2)
        points = {region.id: region.access for region in tilemap.regions}
        for path in self.spec.paths:
            start = points.get(path.from_id)
            end = points.get(path.to)
            if not start or not end:
                continue
            for x, y in self._manhattan(tuple(start), tuple(end)):
                self._set(tilemap.layers["path"], tilemap.map.width, x, y, dirt)

    def _place_spawn(self, tilemap: TilemapData) -> None:
        x = tilemap.map.width // 2
        y = max(1, tilemap.map.height - 4)
        tilemap.events.append(ObjectData(id="spawn_01", type="player_spawn", x=x, y=y, properties={"direction": "up"}))

    def _place_objects(self, tilemap: TilemapData) -> None:
        for item in self.spec.objects:
            category = item.type
            if category not in SCENE_OBJECT_CATEGORIES:
                continue
            props = dict(item.properties or {})
            object_key = str(props["object_key"])
            facing = str(props.get("facing") or self._default_facing(category))
            footprint = parse_footprint(props, category, facing)
            blocking = parse_blocking(props, category)
            source_canvas = parse_source_canvas(props, category, footprint, (tilemap.map.tile_width, tilemap.map.tile_height))
            anchor = parse_anchor(category)
            for index in range(1, item.count + 1):
                object_id = f"{object_key}_{index:02d}"
                x, y = self._position_for(tilemap, item.placement or props.get("placement") or "random_walkable", category, footprint, props, index)
                obj_props = dict(props)
                obj_props.update(
                    {
                        "object_key": object_key,
                        "display_name": props.get("display_name") or item.label or object_key,
                        "label": item.label,
                        "category": category,
                        "facing": facing,
                        "footprint": f"{footprint[0]}x{footprint[1]}",
                        "source_canvas": list(source_canvas),
                        "blocking": blocking,
                        "anchor": anchor,
                        "placement": item.placement or props.get("placement") or "random_walkable",
                    }
                )
                tilemap.objects.append(
                    ObjectData(
                        id=object_id,
                        type=category,
                        x=x,
                        y=y,
                        width=footprint[0],
                        height=footprint[1],
                        properties=obj_props,
                    )
                )
                self.reserved.append((x, y, footprint[0], footprint[1]))

    def _position_for(
        self,
        tilemap: TilemapData,
        placement: str,
        category: str,
        footprint: tuple[int, int],
        props: dict[str, Any],
        index: int,
    ) -> tuple[int, int]:
        if category in {"facade_overlay", "text_sign"}:
            return self._attached_position(tilemap, str(props.get("attached_to")), footprint, index)
        if category == "building":
            return self._building_position(tilemap, placement, footprint, index)
        region = self._region_by_id_or_type(tilemap, placement)
        if region:
            return self._position_in_region(tilemap, region, footprint, category, index)
        return self._nearest_clear(tilemap, tilemap.map.width // 2 + index * 2, tilemap.map.height // 2, footprint, allow_path=category == "npc")

    def _attached_position(self, tilemap: TilemapData, attached_to: str, footprint: tuple[int, int], index: int) -> tuple[int, int]:
        region = next((item for item in tilemap.regions if item.id == attached_to), None)
        if region:
            x, y, w, h = region.bounds
            px = x + 1 + ((index - 1) * max(1, footprint[0] + 1)) % max(1, w - footprint[0] - 1)
            py = y + h - footprint[1]
            return self._clamp(tilemap, px, py, footprint)
        obj = next((item for item in tilemap.objects if item.id == attached_to), None)
        if obj:
            px = obj.x + max(0, (obj.width - footprint[0]) // 2)
            py = obj.y + obj.height - footprint[1]
            return self._clamp(tilemap, px, py, footprint)
        return self._nearest_clear(tilemap, tilemap.map.width // 2, tilemap.map.height // 2, footprint)

    def _building_position(self, tilemap: TilemapData, placement: str, footprint: tuple[int, int], index: int) -> tuple[int, int]:
        if "top" in placement or index % 2 == 1:
            x = 3 + (index - 1) * (footprint[0] + 3)
            y = 3
        else:
            x = tilemap.map.width - footprint[0] - 4
            y = 3 + (index - 1) * (footprint[1] + 3)
        return self._nearest_clear(tilemap, x, y, footprint)

    def _position_in_region(self, tilemap: TilemapData, region: RegionData, footprint: tuple[int, int], category: str, index: int) -> tuple[int, int]:
        x, y, w, h = region.bounds
        if category == "small_prop":
            target = (region.access[0] + index % 3 - 1, region.access[1] + index // 3)
        elif category == "thin_prop":
            target = (x + 1 + index * 2 % max(1, w - footprint[0] - 1), y + 1)
        elif category == "npc":
            target = (region.center[0] + index % 3 - 1, region.center[1] + index // 3)
        else:
            target = (
                x + 1 + ((index - 1) * max(2, footprint[0] + 2)) % max(1, w - footprint[0] - 1),
                y + 1 + ((index - 1) * max(2, footprint[0] + 2)) // max(1, w - footprint[0] - 1),
            )
        return self._nearest_clear(tilemap, target[0], target[1], footprint, allow_path=category == "npc")

    def _nearest_clear(self, tilemap: TilemapData, x: int, y: int, footprint: tuple[int, int], allow_path: bool = False) -> tuple[int, int]:
        x, y = self._clamp(tilemap, x, y, footprint)
        for radius in range(0, 16):
            for yy in range(y - radius, y + radius + 1):
                for xx in range(x - radius, x + radius + 1):
                    px, py = self._clamp(tilemap, xx, yy, footprint)
                    if self._is_clear(tilemap, px, py, footprint, allow_path=allow_path):
                        return px, py
        return x, y

    def _is_clear(self, tilemap: TilemapData, x: int, y: int, footprint: tuple[int, int], allow_path: bool = False) -> bool:
        w, h = footprint
        if any(self._overlap((x, y, w, h), rect) for rect in self.reserved):
            return False
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                idx = yy * tilemap.map.width + xx
                if tilemap.layers["building"][idx] != 0 or tilemap.layers["decoration"][idx] != 0:
                    return False
                if not allow_path and tilemap.layers["path"][idx] != 0:
                    return False
        return True

    def _generate_collision(self, tilemap: TilemapData) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        for obj in tilemap.objects:
            if bool(obj.properties.get("blocking")):
                for yy in range(obj.y, min(height, obj.y + obj.height)):
                    for xx in range(obj.x, min(width, obj.x + obj.width)):
                        tilemap.layers["collision"][yy * width + xx] = 1
        for event in tilemap.events:
            if event.type == "player_spawn":
                tilemap.layers["collision"][event.y * width + event.x] = 0

    def _bounds_for(self, position: str, size: str) -> tuple[int, int, int, int]:
        width, height = self.spec.map.width, self.spec.map.height
        sizes = {
            "small": (max(5, width // 10), max(5, height // 10)),
            "medium": (max(8, width // 5), max(8, height // 5)),
            "large": (max(14, width // 3), max(10, height // 4)),
        }
        w, h = sizes.get(size, sizes["medium"])
        anchors = {
            "top": (width // 2, height // 6),
            "center": (width // 2, height // 2),
            "bottom": (width // 2, height - height // 5),
            "left": (width // 5, height // 2),
            "right": (width - width // 5, height // 2),
            "top_left": (width // 5, height // 5),
            "top_right": (width - width // 5, height // 5),
            "bottom_left": (width // 5, height - height // 5),
            "bottom_right": (width - width // 5, height - height // 5),
        }
        cx, cy = anchors.get(position, anchors["center"])
        return max(1, min(width - w - 2, cx - w // 2)), max(1, min(height - h - 2, cy - h // 2)), w, h

    def _region_by_id_or_type(self, tilemap: TilemapData, value: str | None) -> RegionData | None:
        if not value or value in {"random", "random_walkable", "near_path"}:
            return None
        return next((item for item in tilemap.regions if item.id == value or item.type == value), None)

    def _clamp(self, tilemap: TilemapData, x: int, y: int, footprint: tuple[int, int]) -> tuple[int, int]:
        return max(0, min(tilemap.map.width - footprint[0], x)), max(0, min(tilemap.map.height - footprint[1], y))

    def _set(self, layer: list[int], width: int, x: int, y: int, value: int) -> None:
        if 0 <= y < len(layer) // width and 0 <= x < width:
            layer[y * width + x] = value

    def _manhattan(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = start
        path = [(x, y)]
        while x != goal[0]:
            x += 1 if goal[0] > x else -1
            path.append((x, y))
        while y != goal[1]:
            y += 1 if goal[1] > y else -1
            path.append((x, y))
        return path

    def _overlap(self, a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by

    def _default_facing(self, category: str) -> str:
        if category in {"building", "facade_overlay", "text_sign"}:
            return "faces_south"
        return "east_west"
