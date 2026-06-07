from __future__ import annotations

import heapq
from random import Random

from ..config import (
    BLOCKING_TILE_IDS,
    DEFAULT_TILESET_ID,
    PATH_TILE_IDS,
    THEME_DEFAULT_TERRAIN,
    TILE_ID_BY_NAME,
)
from ..models import MapInfo, ObjectData, RegionData, RPGMapSpec, TilemapData, TilesetInfo


class MapGenerator:
    def generate(self, spec: RPGMapSpec) -> TilemapData:
        width = spec.map.width
        height = spec.map.height
        rng = Random(spec.seed)
        base_tile = TILE_ID_BY_NAME[THEME_DEFAULT_TERRAIN.get(spec.theme, "grass")]
        layers = {
            "terrain": [base_tile] * (width * height),
            "path": [0] * (width * height),
            "building": [0] * (width * height),
            "decoration": [0] * (width * height),
            "collision": [0] * (width * height),
        }
        tilemap = TilemapData(
            map=MapInfo(
                width=width,
                height=height,
                tile_width=spec.map.tile_width,
                tile_height=spec.map.tile_height,
                orientation=spec.map.orientation,
            ),
            tileset=TilesetInfo(id=spec.tileset_id or DEFAULT_TILESET_ID),
            layers=layers,
            metadata={"theme": spec.theme, "seed": spec.seed, "spec_id": spec.id},
        )

        if spec.theme == "dungeon":
            self._prepare_dungeon(tilemap)
        if spec.theme == "seaside_village":
            self._prepare_seaside(tilemap)
        if spec.theme == "school_campus":
            self._build_school_campus(tilemap, spec, rng)
            return tilemap

        for region in spec.regions:
            self._place_region(tilemap, region, rng)

        self._place_theme_buildings(tilemap, spec, rng)
        self._place_spawn(tilemap, spec)
        self._draw_roads(tilemap, spec)
        self._place_entity_events(tilemap, spec)
        self._place_area_markers(tilemap)
        self._place_objects(tilemap, spec, rng)
        self._generate_collision(tilemap)
        return tilemap

    def _build_school_campus(self, tilemap: TilemapData, spec: RPGMapSpec, rng: Random) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        region_types = {region.type for region in spec.regions}
        school_w, school_h = 16, 9
        school_x = width // 2 - school_w // 2
        school_y = 7
        school_tile = TILE_ID_BY_NAME["school"]
        for y in range(school_y, school_y + school_h):
            for x in range(school_x, school_x + school_w):
                self._set(tilemap.layers["building"], width, x, y, school_tile)
        school_door_x = width // 2
        school_door_y = school_y + school_h
        self._set(tilemap.layers["building"], width, school_door_x, school_y + school_h - 1, TILE_ID_BY_NAME["door"])
        tilemap.objects.append(
            ObjectData(id="school_01_door", type="door", x=school_door_x, y=school_door_y, properties={"region": "school_01"})
        )
        tilemap.regions.append(
            RegionData(
                id="school_01",
                type="school",
                bounds=[school_x, school_y, school_w, school_h],
                center=[width // 2, school_y + school_h // 2],
                access=[school_door_x, school_door_y],
                priority=95,
            )
        )

        road_y = min(height - 10, school_y + school_h + 22)
        playground_access = None
        playground_y = school_y + school_h + 5
        playground_h = 0
        if "playground" in region_types:
            playground_w, playground_h = 30, 12
            playground_x = width // 2 - playground_w // 2
            playground_tile = TILE_ID_BY_NAME["playground"]
            for y in range(playground_y, playground_y + playground_h):
                for x in range(playground_x, playground_x + playground_w):
                    self._set(tilemap.layers["terrain"], width, x, y, playground_tile)
            playground_access = [width // 2, playground_y + playground_h // 2]
            tilemap.regions.append(
                RegionData(
                    id="playground_01",
                    type="playground",
                    bounds=[playground_x, playground_y, playground_w, playground_h],
                    center=playground_access,
                    access=playground_access,
                    priority=90,
                )
            )
            for point in self._manhattan((school_door_x, school_door_y), tuple(playground_access)):
                x, y = point
                self._set(tilemap.layers["path"], width, x, y, TILE_ID_BY_NAME["dirt_road"])

        if "mud_road" in region_types:
            road_y = min(height - 10, (playground_y + playground_h + 5) if playground_h else school_door_y + 12)
            for y in range(road_y, road_y + 2):
                for x in range(width):
                    self._set(tilemap.layers["path"], width, x, y, TILE_ID_BY_NAME["dirt_road"])
            tilemap.regions.append(
                RegionData(
                    id="mud_road_01",
                    type="mud_road",
                    bounds=[0, road_y, width, 2],
                    center=[width // 2, road_y],
                    access=[width // 2, road_y],
                    priority=85,
                )
            )
            source = (playground_access[0], playground_y + playground_h) if playground_access else (school_door_x, school_door_y)
            for point in self._manhattan(source, (source[0], road_y)):
                x, y = point
                self._set(tilemap.layers["path"], width, x, y, TILE_ID_BY_NAME["dirt_road"])

        if "toilet" in region_types:
            toilet_w, toilet_h = 5, 4
            toilet_x = width - toilet_w - 4
            toilet_y = road_y - toilet_h
            toilet_tile = TILE_ID_BY_NAME["toilet"]
            for y in range(toilet_y, toilet_y + toilet_h):
                for x in range(toilet_x, toilet_x + toilet_w):
                    self._set(tilemap.layers["building"], width, x, y, toilet_tile)
            toilet_door_x = toilet_x + toilet_w // 2
            toilet_door_y = road_y
            self._set(tilemap.layers["building"], width, toilet_door_x, toilet_y + toilet_h - 1, TILE_ID_BY_NAME["door"])
            tilemap.objects.append(
                ObjectData(id="toilet_01_door", type="door", x=toilet_door_x, y=toilet_door_y, properties={"region": "toilet_01"})
            )
            tilemap.regions.append(
                RegionData(
                    id="toilet_01",
                    type="toilet",
                    bounds=[toilet_x, toilet_y, toilet_w, toilet_h],
                    center=[toilet_x + toilet_w // 2, toilet_y + toilet_h // 2],
                    access=[toilet_door_x, toilet_door_y],
                    priority=80,
                )
            )
            if "mud_road" not in region_types:
                for point in self._manhattan((school_door_x, school_door_y), (toilet_door_x, toilet_door_y)):
                    x, y = point
                    self._set(tilemap.layers["path"], width, x, y, TILE_ID_BY_NAME["dirt_road"])

        spawn_x, spawn_y = (2, road_y) if "mud_road" in region_types else (school_door_x, school_door_y + 2)
        tilemap.events.append(ObjectData(id="spawn_01", type="player_spawn", x=spawn_x, y=spawn_y, properties={"direction": "right"}))
        self._place_objects(tilemap, spec, rng)
        self._place_entity_events(tilemap, spec)
        self._place_area_markers(tilemap)
        self._generate_collision(tilemap)

    def _place_region(self, tilemap: TilemapData, region, rng: Random) -> None:
        if region.type == "river":
            data = self._draw_river(tilemap, region, rng)
        elif region.type in {"temple", "cabin", "lighthouse"}:
            data = self._draw_building_region(tilemap, region)
        elif region.type in {"market", "hall", "boss_room", "entrance", "campfire", "altar", "ruins", "dock"}:
            data = self._draw_open_region(tilemap, region)
        else:
            data = self._draw_open_region(tilemap, region)
        tilemap.regions.append(data)

    def _prepare_dungeon(self, tilemap: TilemapData) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        wall = TILE_ID_BY_NAME["wall"]
        for x in range(width):
            self._set(tilemap.layers["building"], width, x, 0, wall)
            self._set(tilemap.layers["building"], width, x, height - 1, wall)
        for y in range(height):
            self._set(tilemap.layers["building"], width, 0, y, wall)
            self._set(tilemap.layers["building"], width, width - 1, y, wall)

    def _prepare_seaside(self, tilemap: TilemapData) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        water = TILE_ID_BY_NAME["water"]
        sand = TILE_ID_BY_NAME["sand"]
        for y in range(height):
            for x in range(0, max(5, width // 7)):
                self._set(tilemap.layers["terrain"], width, x, y, water)
            for x in range(max(5, width // 7), max(9, width // 5)):
                self._set(tilemap.layers["terrain"], width, x, y, sand)

    def _draw_river(self, tilemap: TilemapData, region, rng: Random) -> RegionData:
        width, height = tilemap.map.width, tilemap.map.height
        water = TILE_ID_BY_NAME["water"]
        vertical = region.position in {"left", "right", "center", "random", "top_left", "bottom_left", "top_right", "bottom_right"}
        band = max(4, min(width, height) // 12)
        if vertical:
            x = self._anchor_x(region.position, width)
            min_x, max_x = width, 0
            for y in range(height):
                x += rng.choice([-1, 0, 0, 1])
                x = max(2, min(width - band - 2, x))
                for dx in range(band):
                    tx = x + dx
                    self._set(tilemap.layers["terrain"], width, tx, y, water)
                    min_x, max_x = min(min_x, tx), max(max_x, tx)
            bounds = [min_x, 0, max_x - min_x + 1, height]
            center = [min_x + bounds[2] // 2, height // 2]
        else:
            y = self._anchor_y(region.position, height)
            min_y, max_y = height, 0
            for x in range(width):
                y += rng.choice([-1, 0, 0, 1])
                y = max(2, min(height - band - 2, y))
                for dy in range(band):
                    ty = y + dy
                    self._set(tilemap.layers["terrain"], width, x, ty, water)
                    min_y, max_y = min(min_y, ty), max(max_y, ty)
            bounds = [0, min_y, width, max_y - min_y + 1]
            center = [width // 2, min_y + bounds[3] // 2]
        return RegionData(id=region.id, type=region.type, bounds=bounds, center=center, access=center, priority=region.priority)

    def _draw_open_region(self, tilemap: TilemapData, region) -> RegionData:
        width = tilemap.map.width
        bounds = self._bounds_for(tilemap, region.position, region.size, region.type)
        x, y, w, h = bounds
        tile_name = {
            "market": "dirt",
            "hall": "stone_floor",
            "boss_room": "stone_floor",
            "entrance": "stone_floor",
            "campfire": "snow",
            "altar": "sand",
            "ruins": "sand",
            "dock": "dock",
        }.get(region.type, "dirt")
        tile = TILE_ID_BY_NAME[tile_name]
        layer = "path" if region.type == "dock" else "terrain"
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self._set(tilemap.layers[layer], width, xx, yy, tile)
        center = [x + w // 2, y + h // 2]
        return RegionData(id=region.id, type=region.type, bounds=bounds, center=center, access=center, priority=region.priority)

    def _draw_building_region(self, tilemap: TilemapData, region) -> RegionData:
        width = tilemap.map.width
        bounds = self._bounds_for(tilemap, region.position, region.size, region.type)
        x, y, w, h = bounds
        tile_name = {"temple": "temple", "lighthouse": "lighthouse"}.get(region.type, "house")
        tile = TILE_ID_BY_NAME[tile_name]
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self._set(tilemap.layers["building"], width, xx, yy, tile)
        door_x = x + w // 2
        door_y = min(tilemap.map.height - 2, y + h)
        self._set(tilemap.layers["building"], width, door_x, y + h - 1, TILE_ID_BY_NAME["door"])
        tilemap.objects.append(ObjectData(id=f"{region.id}_door", type="door", x=door_x, y=door_y, properties={"region": region.id}))
        access = [door_x, door_y]
        center = [x + w // 2, y + h // 2]
        return RegionData(id=region.id, type=region.type, bounds=bounds, center=center, access=access, priority=region.priority)

    def _place_theme_buildings(self, tilemap: TilemapData, spec: RPGMapSpec, rng: Random) -> None:
        if spec.theme in {"forest_village", "autumn_forest_village", "seaside_village"}:
            market = self._region_by_type(tilemap, "market")
            if market:
                offsets = [(-9, -6), (8, -5), (-10, 7)]
                for i, (dx, dy) in enumerate(offsets, start=1):
                    self._draw_small_house(tilemap, market.access[0] + dx, market.access[1] + dy, f"house_{i:02d}")
        if spec.theme == "snow_camp":
            camp = self._region_by_type(tilemap, "campfire")
            if camp:
                offsets = [(-9, -6), (7, -6), (-1, 8)]
                for i, (dx, dy) in enumerate(offsets, start=1):
                    self._draw_small_house(tilemap, camp.access[0] + dx, camp.access[1] + dy, f"cabin_{i:02d}")

    def _draw_small_house(self, tilemap: TilemapData, x: int, y: int, object_id: str) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        house = TILE_ID_BY_NAME["house"]
        w, h = 4, 4
        x = max(2, min(width - w - 2, x))
        y = max(2, min(height - h - 3, y))
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self._set(tilemap.layers["building"], width, xx, yy, house)
        door_x, door_y = x + w // 2, y + h
        self._set(tilemap.layers["building"], width, door_x, y + h - 1, TILE_ID_BY_NAME["door"])
        tilemap.objects.append(ObjectData(id=f"{object_id}_door", type="door", x=door_x, y=door_y, properties={"region": object_id}))
        tilemap.regions.append(
            RegionData(id=object_id, type="house", bounds=[x, y, w, h], center=[x + w // 2, y + h // 2], access=[door_x, door_y], priority=40)
        )

    def _place_spawn(self, tilemap: TilemapData, spec: RPGMapSpec) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        spawn_entity = next((entity for entity in spec.entities if entity.type == "player_spawn"), None)
        position = spawn_entity.position if spawn_entity and spawn_entity.position else "bottom_center"
        spawn = self._point_for_position(position, width, height)
        if spec.theme == "dungeon":
            entrance = self._region_by_type(tilemap, "entrance")
            spawn = tuple(entrance.access) if entrance else spawn
        spawn_x, spawn_y = spawn
        self._set(tilemap.layers["path"], width, spawn_x, spawn_y, TILE_ID_BY_NAME["dirt_road"])
        tilemap.events.append(ObjectData(id="spawn_01", type="player_spawn", x=spawn_x, y=spawn_y, properties={"direction": "up"}))

    def _place_entity_events(self, tilemap: TilemapData, spec: RPGMapSpec) -> None:
        for entity in spec.entities:
            if entity.type == "player_spawn":
                continue
            target = self._region_for_placement(tilemap, entity.placement)
            if not target:
                continue
            for index in range(entity.count):
                point = self._nearest_open_point(tilemap, target.access[0] + index % 3 - 1, target.access[1] + index // 3 + 1)
                if point:
                    x, y = point
                    tilemap.events.append(
                        ObjectData(
                            id=f"{entity.type}_spawn_{index + 1:02d}",
                            type="npc_spawn",
                            x=x,
                            y=y,
                            properties={"entity_type": entity.type, "region": target.id},
                        )
                    )

    def _place_area_markers(self, tilemap: TilemapData) -> None:
        for region in tilemap.regions:
            tilemap.events.append(
                ObjectData(
                    id=f"{region.id}_marker",
                    type="area_marker",
                    x=region.access[0],
                    y=region.access[1],
                    properties={"region_type": region.type, "region": region.id},
                )
            )

    def _draw_roads(self, tilemap: TilemapData, spec: RPGMapSpec) -> None:
        points = self._path_points(tilemap)
        for path in spec.paths:
            start = points.get(path.from_id)
            end = points.get(path.to)
            if start and end:
                self._draw_path(tilemap, tuple(start), tuple(end))
        spawn = points.get("spawn_01")
        for region in tilemap.regions:
            if spawn and region.type != "river":
                self._draw_path(tilemap, tuple(spawn), tuple(region.access))

    def _path_points(self, tilemap: TilemapData) -> dict[str, list[int]]:
        points = {region.id: region.access for region in tilemap.regions}
        for event in tilemap.events:
            if event.type == "player_spawn":
                points[event.id] = [event.x, event.y]
        return points

    def _draw_path(self, tilemap: TilemapData, start: tuple[int, int], goal: tuple[int, int]) -> None:
        width = tilemap.map.width
        path = self._a_star(tilemap, start, goal)
        for x, y in path:
            terrain = self._get(tilemap.layers["terrain"], width, x, y)
            path_tile = TILE_ID_BY_NAME["bridge"] if terrain == TILE_ID_BY_NAME["water"] else TILE_ID_BY_NAME["dirt_road"]
            self._set(tilemap.layers["path"], width, x, y, path_tile)
            self._set(tilemap.layers["decoration"], width, x, y, 0)

    def _a_star(self, tilemap: TilemapData, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        width, height = tilemap.map.width, tilemap.map.height
        frontier: list[tuple[int, tuple[int, int]]] = [(0, start)]
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        cost_so_far = {start: 0}
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for neighbor in self._neighbors(*current, width, height):
                new_cost = cost_so_far[current] + self._movement_cost(tilemap, neighbor)
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + abs(goal[0] - neighbor[0]) + abs(goal[1] - neighbor[1])
                    heapq.heappush(frontier, (priority, neighbor))
                    came_from[neighbor] = current
        if goal not in came_from:
            return self._manhattan(start, goal)
        current = goal
        path = []
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

    def _movement_cost(self, tilemap: TilemapData, point: tuple[int, int]) -> int:
        x, y = point
        width = tilemap.map.width
        terrain = self._get(tilemap.layers["terrain"], width, x, y)
        building = self._get(tilemap.layers["building"], width, x, y)
        if building in BLOCKING_TILE_IDS:
            return 40
        if terrain == TILE_ID_BY_NAME["water"]:
            return 12
        return 1

    def _place_objects(self, tilemap: TilemapData, spec: RPGMapSpec, rng: Random) -> None:
        for item in spec.objects:
            if item.type in {"tree", "pine", "rock", "mountain"}:
                self._scatter_decoration(tilemap, item.type, item.count, item.placement, rng)
            elif item.type == "market_stall":
                self._place_market_stalls(tilemap, item.count)
            elif item.type == "campfire":
                region = self._region_by_type(tilemap, "campfire")
                if region:
                    x, y = region.access
                    self._set(tilemap.layers["decoration"], tilemap.map.width, x, y, TILE_ID_BY_NAME["campfire"])
                    tilemap.objects.append(ObjectData(id="campfire_01", type="campfire", x=x, y=y))
            elif item.type == "chest":
                self._place_chest(tilemap, item.placement)

    def _scatter_decoration(self, tilemap: TilemapData, object_type: str, count: int, placement: str, rng: Random) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        tile = TILE_ID_BY_NAME[object_type]
        placed = 0
        attempts = max(200, count * 20)
        for _ in range(attempts):
            if placed >= count:
                break
            if placement == "forest_edges":
                edge = rng.choice(["top", "bottom", "left", "right", "field"])
                if edge == "top":
                    x, y = rng.randrange(1, width - 1), rng.randrange(1, max(2, height // 5))
                elif edge == "bottom":
                    x, y = rng.randrange(1, width - 1), rng.randrange(max(2, height - height // 5), height - 1)
                elif edge == "left":
                    x, y = rng.randrange(1, max(2, width // 5)), rng.randrange(1, height - 1)
                elif edge == "right":
                    x, y = rng.randrange(max(2, width - width // 5), width - 1), rng.randrange(1, height - 1)
                else:
                    x, y = rng.randrange(1, width - 1), rng.randrange(1, height - 1)
            elif placement in {"campus_edges", "campus_mountains"}:
                edge = rng.choice(["top", "top", "left", "right"])
                if edge == "top":
                    x, y = rng.randrange(1, width - 1), rng.randrange(1, max(3, height // 5))
                elif edge == "left":
                    x, y = rng.randrange(1, max(3, width // 6)), rng.randrange(1, max(4, height - height // 4))
                else:
                    x, y = rng.randrange(max(3, width - width // 6), width - 1), rng.randrange(1, max(4, height - height // 4))
            else:
                x, y = rng.randrange(1, width - 1), rng.randrange(1, height - 1)
            if self._is_clear_for_decoration(tilemap, x, y):
                self._set(tilemap.layers["decoration"], width, x, y, tile)
                placed += 1

    def _place_market_stalls(self, tilemap: TilemapData, count: int) -> None:
        market = self._region_by_type(tilemap, "market")
        if not market:
            return
        width = tilemap.map.width
        offsets = [(-3, -2), (-1, -2), (1, -2), (3, -2), (-3, 2), (3, 2), (-1, 2), (1, 2)]
        for index, (dx, dy) in enumerate(offsets[:count], start=1):
            x, y = market.access[0] + dx, market.access[1] + dy
            if self._in_bounds(tilemap, x, y) and self._is_clear_for_decoration(tilemap, x, y):
                self._set(tilemap.layers["decoration"], width, x, y, TILE_ID_BY_NAME["market_stall"])
                tilemap.objects.append(ObjectData(id=f"market_stall_{index:02d}", type="market_stall", x=x, y=y, properties={"region": market.id}))

    def _place_chest(self, tilemap: TilemapData, placement: str) -> None:
        target_id = placement.removeprefix("near:")
        region = next((item for item in tilemap.regions if item.id == target_id), None) or self._region_by_type(tilemap, "boss_room")
        if not region:
            return
        x, y = region.access[0] + 2, region.access[1]
        if self._in_bounds(tilemap, x, y):
            self._set(tilemap.layers["decoration"], tilemap.map.width, x, y, TILE_ID_BY_NAME["chest"])
            tilemap.objects.append(ObjectData(id="chest_01", type="chest", x=x, y=y, properties={"region": region.id}))

    def _region_for_placement(self, tilemap: TilemapData, placement: str | None) -> RegionData | None:
        if placement and placement.startswith("near:"):
            target_id = placement.removeprefix("near:")
            return next((region for region in tilemap.regions if region.id == target_id), None)
        for preferred in ("market", "campfire", "hall", "entrance"):
            region = self._region_by_type(tilemap, preferred)
            if region:
                return region
        return tilemap.regions[0] if tilemap.regions else None

    def _nearest_open_point(self, tilemap: TilemapData, x: int, y: int) -> tuple[int, int] | None:
        width = tilemap.map.width
        for radius in range(0, 8):
            for yy in range(y - radius, y + radius + 1):
                for xx in range(x - radius, x + radius + 1):
                    if self._in_bounds(tilemap, xx, yy) and self._is_open_for_event(tilemap, xx, yy):
                        self._set(tilemap.layers["path"], width, xx, yy, TILE_ID_BY_NAME["dirt_road"])
                        return xx, yy
        return None

    def _is_open_for_event(self, tilemap: TilemapData, x: int, y: int) -> bool:
        width = tilemap.map.width
        return (
            self._get(tilemap.layers["terrain"], width, x, y) not in BLOCKING_TILE_IDS
            and self._get(tilemap.layers["building"], width, x, y) == 0
            and self._get(tilemap.layers["decoration"], width, x, y) == 0
        )

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

    def _bounds_for(self, tilemap: TilemapData, position: str, size: str, region_type: str) -> list[int]:
        width, height = tilemap.map.width, tilemap.map.height
        sizes = {
            "small": (max(4, width // 10), max(4, height // 10)),
            "medium": (max(8, width // 5), max(8, height // 5)),
            "large": (max(12, width // 3), max(12, height // 3)),
        }
        w, h = sizes.get(size, sizes["medium"])
        if region_type in {"temple", "cabin", "lighthouse"}:
            w, h = (6, 5) if region_type != "lighthouse" else (4, 7)
        if region_type == "boss_room":
            w, h = max(9, width // 6), max(8, height // 6)
        if region_type == "entrance":
            w, h = 5, 5
        cx, cy = self._point_for_position(position, width, height)
        x = max(1, min(width - w - 2, cx - w // 2))
        y = max(1, min(height - h - 3, cy - h // 2))
        return [x, y, w, h]

    def _point_for_position(self, position: str, width: int, height: int) -> tuple[int, int]:
        x_lookup = {
            "left": width // 5,
            "right": width - width // 5,
            "center": width // 2,
            "top": width // 2,
            "bottom": width // 2,
            "top_left": width // 5,
            "top_right": width - width // 5,
            "bottom_left": width // 5,
            "bottom_right": width - width // 5,
            "bottom_center": width // 2,
            "random": width // 2,
        }
        y_lookup = {
            "left": height // 2,
            "right": height // 2,
            "center": height // 2,
            "top": height // 5,
            "bottom": height - height // 5,
            "top_left": height // 5,
            "top_right": height // 5,
            "bottom_left": height - height // 5,
            "bottom_right": height - height // 5,
            "bottom_center": height - 5,
            "random": height // 2,
        }
        return x_lookup.get(position, width // 2), y_lookup.get(position, height // 2)

    def _anchor_x(self, position: str, width: int) -> int:
        if "right" in position:
            return width - width // 5
        if "center" in position:
            return width // 2
        return max(2, width // 8)

    def _anchor_y(self, position: str, height: int) -> int:
        if "bottom" in position:
            return height - height // 5
        if "center" in position:
            return height // 2
        return max(2, height // 8)

    def _region_by_type(self, tilemap: TilemapData, region_type: str) -> RegionData | None:
        return next((region for region in tilemap.regions if region.type == region_type), None)

    def _is_clear_for_decoration(self, tilemap: TilemapData, x: int, y: int) -> bool:
        width = tilemap.map.width
        return (
            self._in_bounds(tilemap, x, y)
            and self._get(tilemap.layers["terrain"], width, x, y) not in BLOCKING_TILE_IDS
            and self._get(tilemap.layers["path"], width, x, y) == 0
            and self._get(tilemap.layers["building"], width, x, y) == 0
            and self._get(tilemap.layers["decoration"], width, x, y) == 0
        )

    def _neighbors(self, x: int, y: int, width: int, height: int) -> list[tuple[int, int]]:
        points = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [(px, py) for px, py in points if 0 <= px < width and 0 <= py < height]

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

    def _in_bounds(self, tilemap: TilemapData, x: int, y: int) -> bool:
        return 0 <= x < tilemap.map.width and 0 <= y < tilemap.map.height

    def _get(self, layer: list[int], width: int, x: int, y: int) -> int:
        return layer[y * width + x]

    def _set(self, layer: list[int], width: int, x: int, y: int, tile_id: int) -> None:
        layer[y * width + x] = tile_id
