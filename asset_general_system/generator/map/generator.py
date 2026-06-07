from __future__ import annotations

import heapq
import re
from random import Random

from ..config import (
    BLOCKING_TILE_IDS,
    DEFAULT_TILESET_ID,
    PATH_TILE_IDS,
    THEME_DEFAULT_TERRAIN,
    TILE_ID_BY_NAME,
)
from ..models import MapInfo, ObjectData, RegionData, RPGMapSpec, TilemapData, TilesetInfo


SCHOOL_DETAIL_OBJECT_TYPES = {
    "laundry_line",
    "shop_goods",
    "chimney_smoke",
    "lunch_box_stack",
    "coal_pile",
    "firewood_pile",
    "rice_washing_pool",
    "student_rice_washing",
    "school_sign",
    "school_slogan_banner",
    "rail_bell",
    "olympic_poster",
    "flag_pole",
    "basketball_hoop",
    "horizontal_bar",
    "parallel_bars",
    "ping_pong_table",
    "power_pole_speaker",
    "water_well",
    "student_activity",
    "bicycle",
    "dog",
    "chicken",
}
SCHOOL_OBJECT_META: dict[str, dict[str, object]] = {
    "dormitory": {"display_name": "学生宿舍楼", "zone": "upper_left", "blocking": True, "footprint": (10, 6)},
    "school_shop": {"display_name": "小卖部", "zone": "upper_right", "blocking": True, "footprint": (7, 4)},
    "dining_hall": {"display_name": "蒸饭食堂", "zone": "upper_right", "blocking": True, "footprint": (9, 5)},
    "laundry_line": {"display_name": "晾衣绳", "zone": "dormitory", "blocking": False, "footprint": (4, 1)},
    "shop_goods": {"display_name": "小卖部零食柜台", "zone": "school_shop", "blocking": False, "footprint": (2, 1)},
    "chimney_smoke": {"display_name": "食堂烟囱炊烟", "zone": "dining_hall", "blocking": False, "footprint": (1, 1)},
    "lunch_box_stack": {"display_name": "铝制饭盒堆", "zone": "dining_hall", "blocking": True, "footprint": (1, 1)},
    "coal_pile": {"display_name": "煤堆", "zone": "dining_hall", "blocking": True, "footprint": (1, 1)},
    "firewood_pile": {"display_name": "柴堆", "zone": "dining_hall", "blocking": True, "footprint": (1, 1)},
    "rice_washing_pool": {"display_name": "水泥淘米池", "zone": "dining_hall", "blocking": True, "footprint": (4, 1)},
    "student_rice_washing": {"display_name": "淘米学生", "zone": "rice_washing_pool", "blocking": False, "footprint": (1, 1)},
    "school_sign": {"display_name": "丁埠小学竖排招牌", "zone": "school_facade", "blocking": False, "footprint": (1, 5)},
    "school_slogan_banner": {"display_name": "红漆标语横幅", "zone": "school_facade", "blocking": False, "footprint": (8, 1)},
    "rail_bell": {"display_name": "废弃铁轨上课铃", "zone": "school_facade", "blocking": False, "footprint": (1, 1)},
    "olympic_poster": {"display_name": "北京奥运福娃海报", "zone": "school_facade", "blocking": False, "footprint": (1, 1)},
    "flag_pole": {"display_name": "升旗台和五星红旗", "zone": "school_front", "blocking": True, "footprint": (2, 2)},
    "basketball_hoop": {"display_name": "铁篮球架", "zone": "playground", "blocking": True, "footprint": (1, 2)},
    "horizontal_bar": {"display_name": "单杠", "zone": "playground", "blocking": True, "footprint": (2, 1)},
    "parallel_bars": {"display_name": "双杠", "zone": "playground", "blocking": True, "footprint": (2, 1)},
    "ping_pong_table": {"display_name": "水泥乒乓球台", "zone": "playground", "blocking": True, "footprint": (3, 2)},
    "power_pole_speaker": {"display_name": "木电线杆和高音喇叭", "zone": "playground", "blocking": True, "footprint": (1, 2)},
    "water_well": {"display_name": "压水井", "zone": "playground", "blocking": True, "footprint": (1, 1)},
    "student_activity": {"display_name": "学生课间活动", "zone": "playground", "blocking": False, "footprint": (1, 1)},
    "bicycle": {"display_name": "二八大杠自行车", "zone": "mud_road", "blocking": False, "footprint": (2, 1)},
    "dog": {"display_name": "土黄狗", "zone": "mud_road", "blocking": False, "footprint": (1, 1)},
    "chicken": {"display_name": "散养土鸡", "zone": "mud_road", "blocking": False, "footprint": (1, 1)},
}
SCHOOL_SLOGAN_TEXTS = [
    "好好学习 天天向上",
    "百年大计 教育为本",
    "德智体美劳 全面发展",
    "北京欢迎你 2008",
    "同一个世界 同一个梦想",
]
SCHOOL_ACTIVITY_TEXTS = ["跳皮筋", "滚铁环", "踢毽子", "弹珠"]


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
        self._place_custom_objects(tilemap, spec)
        self._generate_collision(tilemap)
        return tilemap

    def _build_school_campus(self, tilemap: TilemapData, spec: RPGMapSpec, rng: Random) -> None:
        width, height = tilemap.map.width, tilemap.map.height
        region_types = {region.type for region in spec.regions}
        object_types = {item.type for item in spec.objects}
        school_w = min(max(16, width // 4), max(8, width - 12))
        school_h = min(max(9, height // 7), max(5, height // 4))
        school_x = width // 2 - school_w // 2
        school_y = max(4, min(height // 10, height - school_h - 12))
        school_tile = TILE_ID_BY_NAME["school"]
        self._fill_rect(tilemap.layers["building"], width, school_x, school_y, school_w, school_h, school_tile)
        school_door_x = width // 2
        school_door_y = school_y + school_h
        self._set(tilemap.layers["building"], width, school_door_x, school_y + school_h - 1, TILE_ID_BY_NAME["door"])
        tilemap.objects.append(
            ObjectData(
                id="school_01_door",
                type="door",
                x=school_door_x,
                y=school_door_y,
                properties={"region": "school_01", "display_name": "教学楼正门"},
            )
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

        side_regions = self._draw_school_side_buildings(tilemap, object_types, school_x, school_y, school_w, school_h)
        for region in side_regions:
            for point in self._manhattan((school_door_x, school_door_y), tuple(region.access)):
                x, y = point
                if self._in_bounds(tilemap, x, y):
                    self._set(tilemap.layers["path"], width, x, y, TILE_ID_BY_NAME["dirt_road"])

        road_y = min(height - 6, school_y + school_h + max(18, height // 3))
        playground_access = None
        playground_y = min(height - 12, school_y + school_h + max(4, height // 14))
        playground_h = 0
        if "playground" in region_types:
            playground_w = min(max(30, width // 2), width - 8)
            playground_h = min(max(12, height // 5), max(6, height - playground_y - 10))
            playground_x = width // 2 - playground_w // 2
            playground_tile = TILE_ID_BY_NAME["playground"]
            self._fill_rect(tilemap.layers["terrain"], width, playground_x, playground_y, playground_w, playground_h, playground_tile)
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
            road_y = min(height - 4, (playground_y + playground_h + max(4, height // 14)) if playground_h else school_door_y + 12)
            self._fill_rect(tilemap.layers["path"], width, 0, road_y, width, min(3, height - road_y), TILE_ID_BY_NAME["dirt_road"])
            tilemap.regions.append(
                RegionData(
                    id="mud_road_01",
                    type="mud_road",
                    bounds=[0, road_y, width, min(3, height - road_y)],
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
            toilet_w, toilet_h = min(5, max(3, width // 12)), min(4, max(3, height // 16))
            toilet_x = width - toilet_w - 4
            toilet_y = road_y - toilet_h
            toilet_tile = TILE_ID_BY_NAME["toilet"]
            self._fill_rect(tilemap.layers["building"], width, toilet_x, toilet_y, toilet_w, toilet_h, toilet_tile)
            toilet_door_x = toilet_x + toilet_w // 2
            toilet_door_y = road_y
            self._set(tilemap.layers["building"], width, toilet_door_x, toilet_y + toilet_h - 1, TILE_ID_BY_NAME["door"])
            tilemap.objects.append(
                ObjectData(
                    id="toilet_01_door",
                    type="door",
                    x=toilet_door_x,
                    y=toilet_door_y,
                    properties={"region": "toilet_01", "display_name": "旱厕入口"},
                )
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
        self._place_school_detail_objects(tilemap, spec)
        self._place_custom_objects(tilemap, spec)
        self._place_entity_events(tilemap, spec)
        self._place_area_markers(tilemap)
        self._place_school_ground_details(tilemap, spec, rng)
        self._generate_collision(tilemap)

    def _draw_school_side_buildings(
        self,
        tilemap: TilemapData,
        object_types: set[str],
        school_x: int,
        school_y: int,
        school_w: int,
        school_h: int,
    ) -> list[RegionData]:
        width = tilemap.map.width
        regions: list[RegionData] = []

        if "dormitory" in object_types:
            dorm_w, dorm_h = self._school_footprint("dormitory")
            dorm_x = max(2, school_x - dorm_w - max(3, width // 16))
            dorm_y = school_y + 1
            regions.append(self._draw_named_school_building(tilemap, "dormitory", dorm_x, dorm_y, dorm_w, dorm_h))

        right_x = min(width - 4, school_x + school_w + max(3, width // 16))
        shop_region = None
        if "school_shop" in object_types:
            shop_w, shop_h = self._school_footprint("school_shop")
            shop_region = self._draw_named_school_building(tilemap, "school_shop", right_x, school_y + 1, shop_w, shop_h)
            regions.append(shop_region)

        if "dining_hall" in object_types:
            dining_w, dining_h = self._school_footprint("dining_hall")
            dining_y = (shop_region.bounds[1] + shop_region.bounds[3] + 2) if shop_region else school_y + school_h // 2
            regions.append(self._draw_named_school_building(tilemap, "dining_hall", right_x, dining_y, dining_w, dining_h))

        return regions

    def _draw_named_school_building(
        self,
        tilemap: TilemapData,
        object_type: str,
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> RegionData:
        width, height = tilemap.map.width, tilemap.map.height
        x = max(1, min(width - w - 2, x))
        y = max(1, min(height - h - 3, y))
        tile = TILE_ID_BY_NAME["house"]
        self._fill_rect(tilemap.layers["building"], width, x, y, w, h, tile)
        door_x, door_y = x + w // 2, y + h
        self._set(tilemap.layers["building"], width, door_x, y + h - 1, TILE_ID_BY_NAME["door"])

        meta = SCHOOL_OBJECT_META[object_type]
        region_id = f"{object_type}_01"
        tilemap.objects.append(
            ObjectData(
                id=region_id,
                type=object_type,
                x=x,
                y=y,
                width=w,
                height=h,
                properties=self._school_object_properties(object_type, prompt_detail="building_region"),
            )
        )
        tilemap.objects.append(
            ObjectData(
                id=f"{region_id}_door",
                type="door",
                x=door_x,
                y=door_y,
                properties={"region": region_id, "display_name": f"{meta['display_name']}入口"},
            )
        )
        region = RegionData(
            id=region_id,
            type=object_type,
            bounds=[x, y, w, h],
            center=[x + w // 2, y + h // 2],
            access=[door_x, door_y],
            priority=75,
        )
        tilemap.regions.append(region)
        return region

    def _place_school_detail_objects(self, tilemap: TilemapData, spec: RPGMapSpec) -> None:
        spec_by_type = {item.type: item for item in spec.objects if item.type in SCHOOL_DETAIL_OBJECT_TYPES}
        if not spec_by_type:
            return

        school = self._region_by_type(tilemap, "school")
        playground = self._region_by_type(tilemap, "playground")
        mud_road = self._region_by_type(tilemap, "mud_road")
        dormitory = self._region_by_type(tilemap, "dormitory")
        shop = self._region_by_type(tilemap, "school_shop")
        dining = self._region_by_type(tilemap, "dining_hall")
        pool_anchor: tuple[int, int] | None = None

        if dormitory and "laundry_line" in spec_by_type:
            x, y, w, _h = dormitory.bounds
            self._add_school_semantic_object(tilemap, "laundry_line", 1, x + 2, y + 1, width=max(2, min(4, w - 3)))

        if shop and "shop_goods" in spec_by_type:
            x, y, w, h = shop.bounds
            self._add_school_semantic_object(tilemap, "shop_goods", 1, x + max(1, w // 2 - 1), y + max(1, h // 2))

        if dining:
            x, y, w, h = dining.bounds
            if "chimney_smoke" in spec_by_type:
                self._add_school_semantic_object(tilemap, "chimney_smoke", 1, x + w - 2, max(0, y - 1))
            if "lunch_box_stack" in spec_by_type:
                count = spec_by_type["lunch_box_stack"].count
                for index, (dx, dy) in enumerate(self._school_offsets(count, [(-2, 1), (-1, 1), (1, 1), (2, 1)]), start=1):
                    self._add_school_semantic_object(tilemap, "lunch_box_stack", index, dining.access[0] + dx, dining.access[1] + dy)
            if "coal_pile" in spec_by_type:
                self._add_school_semantic_object(tilemap, "coal_pile", 1, x + w + 1, y + 2)
            if "firewood_pile" in spec_by_type:
                self._add_school_semantic_object(tilemap, "firewood_pile", 1, x + w + 1, y + 3)
            if "rice_washing_pool" in spec_by_type:
                pool_w, pool_h = self._school_footprint("rice_washing_pool")
                pool_x = max(1, x - pool_w - 2)
                pool_y = dining.access[1] + 1
                pool_anchor = self._add_school_semantic_object(tilemap, "rice_washing_pool", 1, pool_x, pool_y, width=pool_w, height=pool_h)

        if "student_rice_washing" in spec_by_type:
            anchor = pool_anchor or (dining.access[0] - 4, dining.access[1] + 2) if dining else None
            if anchor:
                count = spec_by_type["student_rice_washing"].count
                for index, (dx, dy) in enumerate(self._school_offsets(count, [(0, 1), (1, 1), (2, 1), (3, 1)]), start=1):
                    self._add_school_semantic_object(tilemap, "student_rice_washing", index, anchor[0] + dx, anchor[1] + dy)

        if school:
            x, y, w, h = school.bounds
            if "school_sign" in spec_by_type:
                sign_h = max(2, min(5, h - 2))
                self._add_school_semantic_object(
                    tilemap,
                    "school_sign",
                    1,
                    x + w // 2,
                    y + max(1, (h - sign_h) // 2),
                    height=sign_h,
                    properties={"text": "丁埠小学"},
                )
            if "school_slogan_banner" in spec_by_type:
                count = spec_by_type["school_slogan_banner"].count
                banner_w = max(4, w - 2)
                available_h = max(1, h - 2)
                for index in range(1, count + 1):
                    banner_y = y + 1 + min(available_h - 1, (index - 1) * max(1, available_h // max(1, count - 1)))
                    text = SCHOOL_SLOGAN_TEXTS[(index - 1) % len(SCHOOL_SLOGAN_TEXTS)]
                    self._add_school_semantic_object(
                        tilemap,
                        "school_slogan_banner",
                        index,
                        x + 1,
                        banner_y,
                        width=banner_w,
                        properties={"text": text},
                    )
            if "rail_bell" in spec_by_type:
                self._add_school_semantic_object(tilemap, "rail_bell", 1, x + w // 2 + 2, y + h - 1)
            if "olympic_poster" in spec_by_type:
                self._add_school_semantic_object(tilemap, "olympic_poster", 1, x + w - 3, y + max(1, h // 2))
            if "flag_pole" in spec_by_type:
                self._add_school_semantic_object(tilemap, "flag_pole", 1, school.access[0] + 3, school.access[1] + 1)

        if playground:
            x, y, w, h = playground.bounds
            playground_positions = {
                "basketball_hoop": (x + 2, y + 2),
                "horizontal_bar": (x + 4, y + h - 3),
                "parallel_bars": (x + 8, y + h - 3),
                "ping_pong_table": (x + w - 7, y + h // 2),
                "power_pole_speaker": (x + w - 3, y + 2),
                "water_well": (x + w - 4, y + h - 3),
            }
            for object_type, (base_x, base_y) in playground_positions.items():
                if object_type in spec_by_type:
                    count = spec_by_type[object_type].count
                    for index, (dx, dy) in enumerate(self._school_offsets(count, [(0, 0), (2, 0), (0, 2), (2, 2)]), start=1):
                        self._add_school_semantic_object(tilemap, object_type, index, base_x + dx, base_y + dy)
            if "student_activity" in spec_by_type:
                count = spec_by_type["student_activity"].count
                activity_offsets = [(-5, 0), (5, 0), (-4, 3), (4, -2), (-7, -2), (7, 2)]
                for index, (dx, dy) in enumerate(self._school_offsets(count, activity_offsets), start=1):
                    activity = SCHOOL_ACTIVITY_TEXTS[(index - 1) % len(SCHOOL_ACTIVITY_TEXTS)]
                    self._add_school_semantic_object(
                        tilemap,
                        "student_activity",
                        index,
                        playground.access[0] + dx,
                        playground.access[1] + dy,
                        properties={"activity": activity},
                    )

        if mud_road:
            x, y, w, h = mud_road.bounds
            road_y = y + min(1, h - 1)
            if "bicycle" in spec_by_type:
                self._add_school_semantic_object(tilemap, "bicycle", 1, max(2, x + 4), road_y)
            if "dog" in spec_by_type:
                count = spec_by_type["dog"].count
                for index, (dx, dy) in enumerate(self._school_offsets(count, [(-4, 0), (4, 1), (10, 0), (-10, 1)]), start=1):
                    self._add_school_semantic_object(tilemap, "dog", index, mud_road.access[0] + dx, road_y + dy)
            if "chicken" in spec_by_type:
                count = spec_by_type["chicken"].count
                for index, (dx, dy) in enumerate(self._school_offsets(count, [(0, 0), (2, 1), (4, 0), (6, 1), (8, 0)]), start=1):
                    self._add_school_semantic_object(tilemap, "chicken", index, min(w - 2, x + w - 12) + dx, road_y + dy)

    def _place_school_ground_details(self, tilemap: TilemapData, spec: RPGMapSpec, rng: Random) -> None:
        prompt = str(spec.title) + " " + " ".join(str(item.label or "") for item in spec.objects)
        detail_counts: dict[str, int] = {}
        mud_road = self._region_by_type(tilemap, "mud_road")
        playground = self._region_by_type(tilemap, "playground")
        school = self._region_by_type(tilemap, "school")

        if mud_road:
            rut_count = max(8, mud_road.bounds[2] // 4)
            puddle_count = max(3, mud_road.bounds[2] // 14)
            detail_counts["mud_rut"] = self._scatter_ground_detail_in_region(tilemap, mud_road, "mud_rut", rut_count, rng, prefer_path=True)
            detail_counts["puddle"] = self._scatter_ground_detail_in_region(tilemap, mud_road, "puddle", puddle_count, rng, prefer_path=True)

        if playground:
            worn_count = max(8, (playground.bounds[2] * playground.bounds[3]) // 42)
            detail_counts["worn_playground"] = self._scatter_ground_detail_in_region(tilemap, playground, "worn_playground", worn_count, rng)

        if school:
            grass_count = max(10, tilemap.map.width // 2)
            flower_count = max(5, tilemap.map.width // 6)
            detail_counts["wild_grass"] = self._scatter_ground_detail_around_region(tilemap, school, "wild_grass", grass_count, rng)
            detail_counts["wild_flower"] = self._scatter_ground_detail_around_region(tilemap, school, "wild_flower", flower_count, rng)

        tilemap.metadata["ground_detail_report"] = {
            "strategy": "semantic_ground_tiles",
            "layer": "decoration",
            "walkable": True,
            "details": {key: value for key, value in detail_counts.items() if value > 0},
        }

    def _scatter_ground_detail_in_region(
        self,
        tilemap: TilemapData,
        region: RegionData,
        tile_name: str,
        count: int,
        rng: Random,
        prefer_path: bool = False,
    ) -> int:
        x, y, w, h = region.bounds
        tile_id = TILE_ID_BY_NAME[tile_name]
        placed = 0
        attempts = max(80, count * 12)
        for _ in range(attempts):
            if placed >= count:
                break
            px = rng.randrange(x, max(x + 1, x + w))
            py = rng.randrange(y, max(y + 1, y + h))
            if self._is_clear_for_ground_detail(tilemap, px, py, allow_path=prefer_path):
                self._set(tilemap.layers["decoration"], tilemap.map.width, px, py, tile_id)
                placed += 1
        return placed

    def _scatter_ground_detail_around_region(
        self,
        tilemap: TilemapData,
        region: RegionData,
        tile_name: str,
        count: int,
        rng: Random,
    ) -> int:
        x, y, w, h = region.bounds
        candidates: list[tuple[int, int]] = []
        margin = 5
        for yy in range(max(1, y - margin), min(tilemap.map.height - 1, y + h + margin)):
            for xx in range(max(1, x - margin), min(tilemap.map.width - 1, x + w + margin)):
                inside = x <= xx < x + w and y <= yy < y + h
                if not inside:
                    candidates.append((xx, yy))
        rng.shuffle(candidates)
        tile_id = TILE_ID_BY_NAME[tile_name]
        placed = 0
        for px, py in candidates:
            if placed >= count:
                break
            if self._is_clear_for_ground_detail(tilemap, px, py, allow_path=False):
                self._set(tilemap.layers["decoration"], tilemap.map.width, px, py, tile_id)
                placed += 1
        return placed

    def _is_clear_for_ground_detail(self, tilemap: TilemapData, x: int, y: int, allow_path: bool = False) -> bool:
        width = tilemap.map.width
        return (
            self._in_bounds(tilemap, x, y)
            and self._get(tilemap.layers["terrain"], width, x, y) not in BLOCKING_TILE_IDS
            and (allow_path or self._get(tilemap.layers["path"], width, x, y) == 0)
            and self._get(tilemap.layers["building"], width, x, y) == 0
            and self._get(tilemap.layers["decoration"], width, x, y) == 0
            and not self._point_inside_object(tilemap, x, y)
        )

    def _point_inside_object(self, tilemap: TilemapData, x: int, y: int) -> bool:
        return any(obj.x <= x < obj.x + obj.width and obj.y <= y < obj.y + obj.height for obj in tilemap.objects)

    def _add_school_semantic_object(
        self,
        tilemap: TilemapData,
        object_type: str,
        index: int,
        x: int,
        y: int,
        width: int | None = None,
        height: int | None = None,
        properties: dict[str, object] | None = None,
    ) -> tuple[int, int]:
        footprint_w, footprint_h = self._school_footprint(object_type)
        footprint_w = width or footprint_w
        footprint_h = height or footprint_h
        x, y = self._clamp_footprint(tilemap, x, y, footprint_w, footprint_h)
        object_properties = self._school_object_properties(object_type)
        if properties:
            object_properties.update(properties)
        tilemap.objects.append(
            ObjectData(
                id=f"{object_type}_{index:02d}",
                type=object_type,
                x=x,
                y=y,
                width=footprint_w,
                height=footprint_h,
                properties=object_properties,
            )
        )
        return x, y

    def _school_object_properties(self, object_type: str, prompt_detail: str | None = None) -> dict[str, object]:
        meta = SCHOOL_OBJECT_META[object_type]
        footprint = meta.get("footprint", (1, 1))
        width, height = footprint if isinstance(footprint, tuple) else (1, 1)
        properties: dict[str, object] = {
            "display_name": str(meta["display_name"]),
            "zone": str(meta["zone"]),
            "blocking": bool(meta["blocking"]),
            "footprint": f"{width}x{height}",
        }
        if prompt_detail:
            properties["prompt_detail"] = prompt_detail
        return properties

    def _school_footprint(self, object_type: str) -> tuple[int, int]:
        footprint = SCHOOL_OBJECT_META[object_type].get("footprint", (1, 1))
        if isinstance(footprint, tuple):
            return int(footprint[0]), int(footprint[1])
        return 1, 1

    def _school_offsets(self, count: int, preferred: list[tuple[int, int]]) -> list[tuple[int, int]]:
        offsets = preferred[:count]
        while len(offsets) < count:
            index = len(offsets)
            offsets.append(((index % 5) * 2, index // 5))
        return offsets

    def _clamp_footprint(self, tilemap: TilemapData, x: int, y: int, w: int, h: int) -> tuple[int, int]:
        max_x = max(0, tilemap.map.width - w)
        max_y = max(0, tilemap.map.height - h)
        return max(0, min(max_x, x)), max(0, min(max_y, y))

    def _fill_rect(self, layer: list[int], map_width: int, x: int, y: int, w: int, h: int, tile_id: int) -> None:
        map_height = len(layer) // map_width if map_width else 0
        for yy in range(max(0, y), min(map_height, y + h)):
            for xx in range(max(0, x), min(map_width, x + w)):
                self._set(layer, map_width, xx, yy, tile_id)

    def _place_custom_objects(self, tilemap: TilemapData, spec: RPGMapSpec) -> None:
        custom_items = [item for item in spec.objects if item.type == "custom_object"]
        if not custom_items:
            return

        sequence = 1
        for item in custom_items:
            label = item.label or str(item.properties.get("display_name") or "自定义元素")
            footprint_w, footprint_h = self._custom_object_footprint(label, item.properties)
            blocking = self._custom_object_blocking(label, item.properties, item.placement)
            for index in range(item.count):
                x, y = self._custom_object_position(tilemap, item.placement, index, footprint_w, footprint_h)
                properties = dict(item.properties)
                properties.update(
                    {
                        "display_name": label,
                        "label": label,
                        "source": str(properties.get("source", "prompt_fallback")),
                        "placement": item.placement,
                        "blocking": blocking,
                        "footprint": f"{footprint_w}x{footprint_h}",
                    }
                )
                tilemap.objects.append(
                    ObjectData(
                        id=f"custom_object_{sequence:02d}",
                        type="custom_object",
                        x=x,
                        y=y,
                        width=footprint_w,
                        height=footprint_h,
                        properties=properties,
                    )
                )
                sequence += 1

    def _custom_object_position(self, tilemap: TilemapData, placement: str, index: int, w: int, h: int) -> tuple[int, int]:
        if placement == "school_facade":
            school = self._region_by_type(tilemap, "school")
            if school:
                x, y, rw, rh = school.bounds
                px = x + 1 + (index * max(1, w + 1)) % max(1, rw - w - 1)
                py = y + 1 + ((index * max(1, w + 1)) // max(1, rw - w - 1)) % max(1, rh - h - 1)
                return self._clamp_footprint(tilemap, px, py, w, h)

        if placement == "school_front":
            school = self._region_by_type(tilemap, "school")
            if school:
                return self._nearest_clear_footprint(tilemap, school.access[0] - 3 + index * 2, school.access[1] + 1, w, h)

        if placement == "campus_edges":
            px = 2 + (index * 3) % max(1, tilemap.map.width - w - 4)
            py = 2 + (index // 6)
            return self._nearest_clear_footprint(tilemap, px, py, w, h)

        target = self._region_for_custom_placement(tilemap, placement)
        if target:
            x, y, rw, rh = target.bounds
            if target.type == "mud_road":
                px = x + 2 + (index * max(2, w + 1)) % max(1, rw - w - 3)
                py = y + min(1, max(0, rh - h))
                return self._clamp_footprint(tilemap, px, py, w, h)
            if target.type == "playground":
                px = x + 2 + (index * max(2, w + 2)) % max(1, rw - w - 4)
                py = y + 2 + ((index * max(2, w + 2)) // max(1, rw - w - 4)) * max(1, h + 1)
                return self._nearest_clear_footprint(tilemap, px, min(y + rh - h - 1, py), w, h)
            return self._nearest_clear_footprint(tilemap, target.access[0] - 2 + index * 2, target.access[1] + 1, w, h)

        return self._nearest_clear_footprint(tilemap, tilemap.map.width // 2 + index * 2, tilemap.map.height // 2, w, h)

    def _region_for_custom_placement(self, tilemap: TilemapData, placement: str) -> RegionData | None:
        if placement.startswith("near:"):
            target_id = placement.removeprefix("near:")
            return next((region for region in tilemap.regions if region.id == target_id), None)
        return self._region_by_type(tilemap, placement)

    def _nearest_clear_footprint(self, tilemap: TilemapData, x: int, y: int, w: int, h: int) -> tuple[int, int]:
        x, y = self._clamp_footprint(tilemap, x, y, w, h)
        for radius in range(0, 10):
            for yy in range(y - radius, y + radius + 1):
                for xx in range(x - radius, x + radius + 1):
                    px, py = self._clamp_footprint(tilemap, xx, yy, w, h)
                    if self._is_clear_footprint(tilemap, px, py, w, h):
                        return px, py
        return x, y

    def _is_clear_footprint(self, tilemap: TilemapData, x: int, y: int, w: int, h: int) -> bool:
        width = tilemap.map.width
        for yy in range(y, min(tilemap.map.height, y + h)):
            for xx in range(x, min(tilemap.map.width, x + w)):
                if self._get(tilemap.layers["terrain"], width, xx, yy) in BLOCKING_TILE_IDS:
                    return False
                if self._get(tilemap.layers["building"], width, xx, yy) != 0:
                    return False
                if self._get(tilemap.layers["decoration"], width, xx, yy) != 0:
                    return False
        return True

    def _custom_object_footprint(self, label: str, properties: dict[str, object]) -> tuple[int, int]:
        explicit = properties.get("footprint")
        if isinstance(explicit, str):
            match = re.match(r"^(\d+)x(\d+)$", explicit)
            if match:
                return max(1, int(match.group(1))), max(1, int(match.group(2)))
        if any(label.endswith(suffix) for suffix in ("广播室", "室", "房", "亭", "棚")):
            return 4, 3
        if any(label.endswith(suffix) for suffix in ("花坛", "池", "台", "桌", "柜", "架")):
            return 2, 1
        if any(label.endswith(suffix) for suffix in ("长椅", "栏杆", "宣传栏", "公告栏")):
            return 2, 1
        return 1, 1

    def _custom_object_blocking(self, label: str, properties: dict[str, object], placement: str) -> bool:
        explicit = properties.get("blocking")
        if isinstance(explicit, bool):
            return explicit
        if placement == "school_facade" or any(label.endswith(suffix) for suffix in ("黑板报", "海报", "标语", "招牌", "告示牌", "牌", "报")):
            return False
        return True

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
            if bool(obj.properties.get("blocking")):
                for yy in range(obj.y, min(height, obj.y + obj.height)):
                    for xx in range(obj.x, min(width, obj.x + obj.width)):
                        self._set(collision, width, xx, yy, 1)
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
