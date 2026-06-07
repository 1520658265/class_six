from __future__ import annotations

from random import Random
from typing import Any

from pydantic import Field

from ..config import BLOCKING_TILE_IDS, PATH_TILE_IDS, THEME_DEFAULT_TERRAIN, TILE_ID_BY_NAME, VERSION
from ..models.base import StrictModel
from ..models.tilemap_data import ObjectData, TilemapData
from .documents import EditorStateDocument, validate_editor_state_document
from .state import SelectionRect


class PartialRegenerationRequest(StrictModel):
    version: str = VERSION
    prompt: str
    seed: int | None = None
    editor_state: EditorStateDocument
    selection: SelectionRect | None = None
    preserve_locked_regions: bool = True


class PartialRegenerationReport(StrictModel):
    version: str = VERSION
    prompt: str
    seed: int
    operation: str
    selection: list[int]
    changed_tiles: int
    skipped_locked_tiles: int
    locked_region_count: int
    validation_passed: bool
    tiled_validation_passed: bool | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class PartialRegenerator:
    def regenerate(self, tilemap: TilemapData, request: PartialRegenerationRequest) -> tuple[TilemapData, PartialRegenerationReport]:
        state_report = validate_editor_state_document(request.editor_state, tilemap)
        if not state_report.passed:
            raise ValueError(f"Invalid editor state: {state_report.model_dump(mode='json')}")

        source = tilemap.model_copy(deep=True)
        result = tilemap.model_copy(deep=True)
        selection = request.selection or request.editor_state.selection
        if selection is None:
            raise ValueError("Partial regeneration requires a selection.")
        selection = selection.clamp(result.map.width, result.map.height)
        if selection is None:
            raise ValueError("Selection does not intersect the map.")

        seed = request.seed
        if seed is None:
            seed = int(result.metadata.get("seed", 0)) + 1
        rng = Random(seed)
        operation = self._classify_prompt(request.prompt)
        locked_regions = request.editor_state.locked_regions_for_runtime() if request.preserve_locked_regions else []
        skipped = self._apply_operation(result, selection, operation, locked_regions, rng)
        skipped += self._repair_key_paths(result, locked_regions)
        self._generate_collision(result)
        if locked_regions:
            self._restore_locked_cells(source, result, locked_regions)

        changed = self._count_changed_tiles(source, result, selection)
        result.metadata["last_partial_regeneration"] = {
            "prompt": request.prompt,
            "seed": seed,
            "operation": operation,
            "selection": selection.bounds,
            "changed_tiles": changed,
            "skipped_locked_tiles": skipped,
        }
        history = list(result.metadata.get("partial_regeneration_history", []))
        history.append(result.metadata["last_partial_regeneration"])
        result.metadata["partial_regeneration_history"] = history[-20:]

        report = PartialRegenerationReport(
            prompt=request.prompt,
            seed=seed,
            operation=operation,
            selection=selection.bounds,
            changed_tiles=changed,
            skipped_locked_tiles=skipped,
            locked_region_count=len(locked_regions),
            validation_passed=False,
            metrics={"map_width": result.map.width, "map_height": result.map.height},
        )
        return result, report

    def _classify_prompt(self, prompt: str) -> str:
        text = prompt.lower()
        keyword_groups = [
            ("market", ("market", "stall", "\u96c6\u5e02", "\u5e02\u573a", "\u644a\u4f4d")),
            ("forest", ("forest", "tree", "trees", "\u68ee\u6797", "\u6811", "\u6811\u6728")),
            ("water", ("water", "river", "pond", "lake", "\u6c34", "\u6cb3", "\u6c60", "\u6e56")),
            ("road", ("road", "path", "dirt", "\u8def", "\u9053\u8def", "\u6ce5\u5df4\u8def")),
            ("playground", ("playground", "\u64cd\u573a")),
            ("snow", ("snow", "\u96ea")),
            ("sand", ("sand", "desert", "\u6c99", "\u6c99\u6f20")),
            ("clear", ("clear", "empty", "clean", "\u6e05\u7406", "\u7a7a\u5730")),
        ]
        for operation, keywords in keyword_groups:
            if any(keyword in text for keyword in keywords):
                return operation
        return "clear"

    def _apply_operation(self, tilemap: TilemapData, selection: SelectionRect, operation: str, locked_regions, rng: Random) -> int:
        if operation == "market":
            return self._apply_market(tilemap, selection, locked_regions, rng)
        if operation == "forest":
            return self._apply_forest(tilemap, selection, locked_regions, rng)
        if operation == "water":
            return self._apply_fill(tilemap, selection, "terrain", TILE_ID_BY_NAME["water"], locked_regions, clear_upper=True)
        if operation == "road":
            return self._apply_road(tilemap, selection, locked_regions)
        if operation == "playground":
            return self._apply_fill(tilemap, selection, "terrain", TILE_ID_BY_NAME["playground"], locked_regions, clear_upper=True)
        if operation == "snow":
            return self._apply_fill(tilemap, selection, "terrain", TILE_ID_BY_NAME["snow"], locked_regions, clear_upper=True)
        if operation == "sand":
            return self._apply_fill(tilemap, selection, "terrain", TILE_ID_BY_NAME["sand"], locked_regions, clear_upper=True)
        return self._apply_clear(tilemap, selection, locked_regions)

    def _apply_market(self, tilemap: TilemapData, selection: SelectionRect, locked_regions, rng: Random) -> int:
        skipped = self._apply_fill(tilemap, selection, "terrain", TILE_ID_BY_NAME["dirt"], locked_regions, clear_upper=True)
        width = tilemap.map.width
        center_x = selection.x + selection.width // 2
        center_y = selection.y + selection.height // 2
        for x in range(selection.x, selection.right):
            skipped += self._set_if_unlocked(tilemap, "path", width, x, center_y, TILE_ID_BY_NAME["dirt_road"], locked_regions)
        for y in range(selection.y, selection.bottom):
            skipped += self._set_if_unlocked(tilemap, "path", width, center_x, y, TILE_ID_BY_NAME["dirt_road"], locked_regions)

        offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, -3), (0, 3)]
        rng.shuffle(offsets)
        start_index = len([obj for obj in tilemap.objects if obj.type == "market_stall"]) + 1
        for index, (dx, dy) in enumerate(offsets[:4], start=start_index):
            x = max(selection.x, min(selection.right - 1, center_x + dx))
            y = max(selection.y, min(selection.bottom - 1, center_y + dy))
            if self._is_locked(x, y, "decoration", locked_regions):
                skipped += 1
                continue
            self._set(tilemap.layers["decoration"], width, x, y, TILE_ID_BY_NAME["market_stall"])
            tilemap.objects.append(
                ObjectData(id=f"partial_market_stall_{index:02d}", type="market_stall", x=x, y=y, properties={"source": "partial_regeneration"})
            )
        return skipped

    def _apply_forest(self, tilemap: TilemapData, selection: SelectionRect, locked_regions, rng: Random) -> int:
        skipped = self._apply_clear(tilemap, selection, locked_regions)
        width = tilemap.map.width
        tree = TILE_ID_BY_NAME["tree"]
        for y in range(selection.y, selection.bottom):
            for x in range(selection.x, selection.right):
                edge = x in {selection.x, selection.right - 1} or y in {selection.y, selection.bottom - 1}
                if edge or rng.random() < 0.28:
                    skipped += self._set_if_unlocked(tilemap, "decoration", width, x, y, tree, locked_regions)
        return skipped

    def _apply_road(self, tilemap: TilemapData, selection: SelectionRect, locked_regions) -> int:
        skipped = 0
        width = tilemap.map.width
        road_y = selection.y + selection.height // 2
        for x in range(selection.x, selection.right):
            skipped += self._set_if_unlocked(tilemap, "path", width, x, road_y, TILE_ID_BY_NAME["dirt_road"], locked_regions)
            skipped += self._set_if_unlocked(tilemap, "decoration", width, x, road_y, 0, locked_regions)
            skipped += self._set_if_unlocked(tilemap, "building", width, x, road_y, 0, locked_regions)
        if selection.height >= 3:
            for x in range(selection.x, selection.right):
                if x % 2 == 0:
                    skipped += self._set_if_unlocked(tilemap, "terrain", width, x, road_y - 1, TILE_ID_BY_NAME["dirt"], locked_regions)
                    skipped += self._set_if_unlocked(tilemap, "terrain", width, x, road_y + 1, TILE_ID_BY_NAME["dirt"], locked_regions)
        return skipped

    def _apply_clear(self, tilemap: TilemapData, selection: SelectionRect, locked_regions) -> int:
        theme = str(tilemap.metadata.get("theme", "forest_village"))
        base_tile = TILE_ID_BY_NAME[THEME_DEFAULT_TERRAIN.get(theme, "grass")]
        return self._apply_fill(tilemap, selection, "terrain", base_tile, locked_regions, clear_upper=True)

    def _apply_fill(self, tilemap: TilemapData, selection: SelectionRect, layer_name: str, tile_id: int, locked_regions, clear_upper: bool) -> int:
        skipped = 0
        width = tilemap.map.width
        for y in range(selection.y, selection.bottom):
            for x in range(selection.x, selection.right):
                skipped += self._set_if_unlocked(tilemap, layer_name, width, x, y, tile_id, locked_regions)
                if clear_upper:
                    for clear_layer in ("path", "building", "decoration"):
                        if clear_layer != layer_name:
                            skipped += self._set_if_unlocked(tilemap, clear_layer, width, x, y, 0, locked_regions)
        return skipped

    def _generate_collision(self, tilemap: TilemapData) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        collision = tilemap.layers["collision"]
        for y in range(height):
            for x in range(width):
                blocked = False
                if self._get(tilemap.layers["terrain"], width, x, y) in BLOCKING_TILE_IDS:
                    blocked = True
                if self._get(tilemap.layers["building"], width, x, y) in BLOCKING_TILE_IDS:
                    blocked = True
                if self._get(tilemap.layers["decoration"], width, x, y) in BLOCKING_TILE_IDS:
                    blocked = True
                if self._get(tilemap.layers["path"], width, x, y) in PATH_TILE_IDS:
                    blocked = False
                self._set(collision, width, x, y, 1 if blocked else 0)
        for obj in tilemap.objects:
            if obj.type == "door":
                self._set(collision, width, obj.x, obj.y, 0)
                if obj.y > 0:
                    self._set(collision, width, obj.x, obj.y - 1, 0)
            if obj.type in {"chest", "market_stall"}:
                self._set(collision, width, obj.x, obj.y, 1)
        for event in tilemap.events:
            if event.type == "player_spawn":
                self._set(collision, width, event.x, event.y, 0)

    def _repair_key_paths(self, tilemap: TilemapData, locked_regions) -> int:
        spawn = next((event for event in tilemap.events if event.type == "player_spawn"), None)
        if not spawn:
            return 0
        skipped = 0
        start = (spawn.x, spawn.y)
        for region in tilemap.regions:
            if region.type == "river":
                continue
            skipped += self._draw_repair_path(tilemap, start, tuple(region.access), locked_regions)
        return skipped

    def _draw_repair_path(self, tilemap: TilemapData, start: tuple[int, int], goal: tuple[int, int], locked_regions) -> int:
        skipped = 0
        width = tilemap.map.width
        x, y = start
        points = [(x, y)]
        while x != goal[0]:
            x += 1 if goal[0] > x else -1
            points.append((x, y))
        while y != goal[1]:
            y += 1 if goal[1] > y else -1
            points.append((x, y))
        for x, y in points:
            terrain = self._get(tilemap.layers["terrain"], width, x, y)
            path_tile = TILE_ID_BY_NAME["bridge"] if terrain == TILE_ID_BY_NAME["water"] else TILE_ID_BY_NAME["dirt_road"]
            skipped += self._set_if_unlocked(tilemap, "path", width, x, y, path_tile, locked_regions)
            skipped += self._set_if_unlocked(tilemap, "decoration", width, x, y, 0, locked_regions)
        return skipped

    def _restore_locked_cells(self, source: TilemapData, result: TilemapData, locked_regions) -> None:
        width = result.map.width
        for layer_name, layer in result.layers.items():
            source_layer = source.layers[layer_name]
            for region in locked_regions:
                if region.layers is not None and layer_name not in region.layers:
                    continue
                for x, y in region.rect.iter_cells():
                    layer[y * width + x] = source_layer[y * width + x]

    def _count_changed_tiles(self, source: TilemapData, result: TilemapData, selection: SelectionRect) -> int:
        changed = 0
        width = result.map.width
        for layer_name, layer in result.layers.items():
            source_layer = source.layers[layer_name]
            for x, y in selection.iter_cells():
                if layer[y * width + x] != source_layer[y * width + x]:
                    changed += 1
        return changed

    def _set_if_unlocked(self, tilemap: TilemapData, layer_name: str, width: int, x: int, y: int, tile_id: int, locked_regions) -> int:
        if self._is_locked(x, y, layer_name, locked_regions):
            return 1
        self._set(tilemap.layers[layer_name], width, x, y, tile_id)
        return 0

    def _is_locked(self, x: int, y: int, layer_name: str, locked_regions) -> bool:
        return any(region.contains(x, y, layer_name) for region in locked_regions)

    def _get(self, layer: list[int], width: int, x: int, y: int) -> int:
        return layer[y * width + x]

    def _set(self, layer: list[int], width: int, x: int, y: int, tile_id: int) -> None:
        layer[y * width + x] = tile_id
